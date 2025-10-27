"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# 기기별 액션 매핑: "toggle" → 기기별 구체적 액션 변환
# ============================================================================
DEVICE_ACTION_MAPPING = {
    "aircon": {
        "toggle_on": "aircon_on",
        "toggle_off": "aircon_off",
        "toggle": None  # 상태에 따라 동적 결정
    },
    "airpurifier": {
        "toggle_on": "turn_on",
        "toggle_off": "turn_off",
        "toggle": None
    },
    "air_purifier": {
        "toggle_on": "turn_on",
        "toggle_off": "turn_off",
        "toggle": None
    },
    "dryer": {
        "toggle_on": "dryer_start",
        "toggle_off": "dryer_stop",
        "toggle": None
    }
}

# Mock 기기 데이터 (테스트용)
# 지원되는 기기: 공기청정기, 건조기, 에어컨
MOCK_DEVICES = [
    {
        "device_id": "airpurifier_living_room",
        "name": "거실 공기청정기",
        "device_type": "airpurifier",
        "state": "on",
        "metadata": {
            "mode": "auto",
            "pm25": 45,
            "status": "on"
        }
    },
    {
        "device_id": "dryer_laundry",
        "name": "세탁실 건조기",
        "device_type": "dryer",
        "state": "off",
        "metadata": {
            "time_remaining": 45,
            "temperature": 70,
            "status": "off"
        }
    },
    {
        "device_id": "aircon_living_room",
        "name": "거실 에어컨",
        "device_type": "aircon",
        "state": "on",
        "metadata": {
            "current_temp": 26,
            "target_temp": 24,
            "mode": "cool",
            "status": "on"
        }
    }
]


class DeviceClickRequest(BaseModel):
    """기기 클릭 요청."""
    user_id: str = Field(..., description="사용자 ID")
    action: str = Field(..., description="기기 액션 (turn_on, turn_off 등)")


def format_gateway_device(device: Dict[str, Any]) -> Dict[str, Any]:
    """기능: Gateway 기기 형식을 Frontend 호환 형식으로 변환.
    
    Gateway 응답: {deviceId, deviceInfo: {alias, deviceType, status}}
    Frontend 기대: {device_id, name, device_type, state}
    
    args: device (Gateway 형식)
    return: 변환된 기기 정보
    """
    # Gateway 형식 처리
    if isinstance(device, dict):
        device_id = device.get("deviceId") or device.get("device_id")
        device_info = device.get("deviceInfo", {}) or device.get("info", {})
        
        # 1️⃣ 기기 아이디
        if not device_id:
            logger.warning(f"Device missing deviceId: {device}")
            return None
        
        # 2️⃣ 기기명
        name = device_info.get("alias") or device.get("name") or device.get("device_name", "Unknown")
        
        # 3️⃣ 기기 타입
        device_type = (device_info.get("deviceType") or 
                      device.get("type") or 
                      device.get("device_type", "unknown")).lower()
        
        # 정규화: "air_purifier" → "airpurifier"
        device_type = device_type.replace("_", "")
        
        # 4️⃣ 기기 상태 (on/off)
        status = device.get("status") or device_info.get("status", "offline")
        state = "on" if str(status).lower() in ["on", "true", "1"] else "off"
        
        return {
            "device_id": device_id,
            "name": name,
            "device_type": device_type,
            "state": state,
            "source": "gateway_sync"
        }
    
    return None


def convert_toggle_action(device_type: str, current_state: str, action: str) -> str:
    """기능: "toggle" 액션을 기기별 구체적 액션으로 변환.
    
    args: device_type (aircon, airpurifier 등), current_state (on/off), action ("toggle" 등)
    return: 변환된 액션 (aircon_on, aircon_off 등)
    """
    # action이 이미 구체적이면 그대로 반환
    if action not in ["toggle", "turn_on", "turn_off", "toggle_on", "toggle_off"]:
        logger.info(f"Action is already specific: {action}")
        return action
    
    # 기기 타입별 매핑 테이블에서 찾기
    device_type_lower = device_type.lower().replace("_", "")
    
    if device_type_lower not in DEVICE_ACTION_MAPPING:
        logger.warning(f"Unknown device type: {device_type}. Using action as-is: {action}")
        return action
    
    mapping = DEVICE_ACTION_MAPPING[device_type_lower]
    
    # "toggle"인 경우 현재 상태에 따라 결정
    if action == "toggle":
        if current_state == "on":
            mapped_action = mapping.get("toggle_off", "turn_off")
        else:
            mapped_action = mapping.get("toggle_on", "turn_on")
    else:
        # "turn_on" → "toggle_on", "turn_off" → "toggle_off"로 정규화
        normalized_action = f"toggle_{action.split('_')[-1]}"
        mapped_action = mapping.get(normalized_action, action)
    
    logger.info(f"Action mapping: {device_type}({current_state}) + {action} → {mapped_action}")
    
    return mapped_action


@router.get("/")
async def get_devices():
    """기능: 기기 목록 조회 (Gateway 형식 → Frontend 호환 형식 변환).
    
    AI-Services를 통해 Gateway의 LG 기기 목록을 조회하여
    Frontend 호환 형식으로 변환하여 반환합니다.
    
    Flow:
    1. AI-Services에 기기 목록 요청
    2. AI-Services → Gateway → LG 기기 조회
    3. Gateway 응답: {deviceId, deviceInfo: {alias, deviceType}}
    4. Backend 변환: {device_id, name, device_type, state}
    5. Frontend 응답
    
    args: 없음
    return: 변환된 기기 목록, 개수, 동기화 상태
    """
    try:
        logger.info("📋 기기 목록 조회 (AI-Services → Gateway → Frontend 형식 변환)")
        
        # 1️⃣ AI-Services/Gateway에서 기기 목록 조회
        try:
            logger.info("🔍 AI-Services를 통해 Gateway 기기 목록 조회 중...")
            devices = await ai_client.get_user_devices("default_user")
            
            if devices:
                logger.info(f"✅ AI-Services에서 {len(devices)}개 기기 조회 완료")
                logger.info(f"📌 Gateway 응답 형식: {type(devices[0]) if devices else 'empty'}")
                
                # 로컬 데이터베이스에 동기화 (필요시)
                db.sync_devices(devices)
            else:
                logger.warning("⚠️  AI-Services에서 기기를 반환하지 않음")
                
        except Exception as e:
            logger.error(f"❌ AI-Services 기기 조회 실패: {e}")
            logger.info("   로컬 Mock 기기 데이터로 대체")
            devices = MOCK_DEVICES
        
        # 2️⃣ 기기 형식 변환: Gateway 형식 → Frontend 호환 형식
        formatted_devices = []
        for device in devices:
            try:
                converted = format_gateway_device(device)
                if converted:
                    formatted_devices.append(converted)
            except Exception as e:
                logger.warning(f"⚠️  기기 변환 실패: {device} - {e}")
        
        # 3️⃣ 변환 실패 시 MOCK_DEVICES 사용
        if not formatted_devices:
            logger.warning("⚠️  기기 변환 실패. MOCK_DEVICES 사용")
            formatted_devices = MOCK_DEVICES
        
        logger.info(f"✅ 최종 반환: {len(formatted_devices)}개 기기 (형식: Frontend 호환)")
        logger.info(f"   기기: {[d.get('name') for d in formatted_devices]}")
        
        return {
            "success": True,
            "devices": formatted_devices,
            "count": len(formatted_devices),
            "source": "gateway_sync"
        }
    
    except Exception as e:
        logger.error(f"Failed to get devices: {e}", exc_info=True)
        return {
            "success": False,
            "devices": [],
            "count": 0,
            "error": str(e),
            "source": "error"
        }


@router.post("/{device_id}/click")
async def handle_device_click(device_id: str, request: DeviceClickRequest):
    """기능: 기기 클릭 이벤트를 처리하고 기기 제어.
    
    1. Frontend에서 기기 클릭 (user_id, action)
    2. Backend가 기기 정보 조회
    3. 액션 매핑: "toggle" → 기기별 구체적 액션 변환
    4. AI Server로 기기 제어 명령 전송
    5. AI-Services → Gateway → LG 기기 제어
    6. 결과 반환
    
    args: device_id (path), user_id, action (body)
    return: 성공 여부, device_id, action, 메시지, 기기명, 기기타입
    """
    try:
        user_id = request.user_id or "default_user"
        action = request.action or "toggle"
        
        logger.info(
            f"🎯 기기 제어 요청: device_id={device_id}, "
            f"user_id={user_id}, action={action}"
        )
        
        # 1️⃣ 기기 정보 조회 (현재 상태 확인용)
        device_info = next(
            (d for d in MOCK_DEVICES if d["device_id"] == device_id),
            None
        )
        
        if not device_info:
            logger.warning(f"❌ Device not found: {device_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Device not found: {device_id}"
            )
        
        device_name = device_info.get("name") or device_info.get("device_name", device_id)
        device_type = device_info.get("device_type", "unknown")
        current_state = device_info.get("state", "off")
        
        logger.info(
            f"📍 기기 정보: name={device_name}, type={device_type}, state={current_state}"
        )
        
        # 2️⃣ 액션 매핑: "toggle" → 기기별 구체적 액션 변환
        mapped_action = convert_toggle_action(device_type, current_state, action)
        
        logger.info(f"🔄 액션 매핑: {action} → {mapped_action}")
        
        # 3️⃣ AI Server의 기기 제어 엔드포인트 호출
        # POST /api/lg/control
        #   ↓
        # AI-Server (Gateway 클라이언트)
        #   ↓
        # Gateway (/api/lg/control)
        #   ↓
        # LG ThinQ API
        try:
            logger.info(f"🚀 AI Server로 기기 제어 명령 전송:")
            logger.info(f"  - 기기: {device_id}")
            logger.info(f"  - 기기명: {device_name}")
            logger.info(f"  - 기기타입: {device_type}")
            logger.info(f"  - 원본 액션: {action}")
            logger.info(f"  - 변환된 액션: {mapped_action}")
            
            # AI Server로 변환된 액션 전송
            control_result = await ai_client.send_device_control(
                user_id=user_id,
                device_id=device_id,
                action=mapped_action,  # ← 변환된 액션 사용
                params={}
            )
            
            # AI Server 응답 형식: {"success": bool, "message": "..."}
            success = control_result.get("success", True)
            message = control_result.get("message", f"기기 {mapped_action} 완료")
            
            logger.info(f"✅ 기기 제어 완료: {device_name}")
            logger.info(f"   응답: {message}")
            
        except Exception as e:
            logger.error(f"❌ 기기 제어 실패: {e}", exc_info=True)
            success = False
            message = f"기기 제어 실패: {str(e)}"
            control_result = {"success": False, "message": message}
        
        # 4️⃣ Frontend 응답 형식
        response_data = {
            "success": success,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "action": mapped_action,  # ← 변환된 액션 반환
            "message": message,
            "result": {}
        }
        
        logger.info(f"📤 응답 전송: {response_data}")
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 기기 제어 중 예기치 않은 오류: {e}", exc_info=True)
        return {
            "success": False,
            "device_id": device_id,
            "message": f"오류: {str(e)}"
        }

