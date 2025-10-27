"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.services.gateway_client import gateway_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# 기기별 액션 매핑: "toggle" → 기기별 구체적 액션 변환
# Gateway 실제 device_type과 매핑됨
# ============================================================================
DEVICE_ACTION_MAPPING = {
    "aircon": {
        "toggle_on": "aircon_on",
        "toggle_off": "aircon_off",
        "toggle": None  # 상태에 따라 동적 결정
    },
    "airconditioner": {  # ← air_conditioner 정규화
        "toggle_on": "aircon_on",
        "toggle_off": "aircon_off",
        "toggle": None
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

# Mock 기기 데이터 (Gateway의 실제 기기 ID 사용)
# 지원되는 기기: 공기청정기, 건조기, 에어컨
# Gateway에서 조회하는 실제 device_id: b403_*_001
MOCK_DEVICES = [
    {
        "device_id": "b403_air_purifier_001",
        "name": "거실 공기청정기",
        "device_type": "air_purifier",
        "state": "on",
        "metadata": {
            "mode": "auto",
            "pm25": 45,
            "status": "on"
        }
    },
    {
        "device_id": "b403_dryer_001",
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
        "device_id": "b403_ac_001",
        "name": "거실 에어컨",
        "device_type": "air_conditioner",
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
        
        # 정규화: "air_purifier" → "airpurifier", "air_conditioner" → "airconditioner"
        device_type = device_type.replace("_", "")
        
        # "airconditioner" → "aircon" 호환성 매핑
        if device_type == "airconditioner":
            device_type = "airconditioner"  # DEVICE_ACTION_MAPPING에 airconditioner 추가됨
        
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
    """기능: Gateway에서 기기 목록을 직접 조회.
    
    ✅ 기기 목록 조회: Gateway 직접 (로컬 네트워크)
    
    Flow:
    1. Edge-Module이 Gateway에 기기 목록 요청 (직접)
    2. Gateway에서 LG ThinQ 기기 조회
    3. Frontend 호환 형식으로 변환하여 반환
    
    args: 없음
    return: Gateway 기기 목록 (Frontend 호환 형식)
    """
    try:
        logger.info("📋 기기 목록 조회 (Gateway 직접 조회)")
        
        # ✅ Gateway에서 직접 기기 목록 조회
        gateway_response = await gateway_client.get_devices()
        
        if gateway_response.get("success"):
            devices = gateway_response.get("devices", [])
            logger.info(f"✅ Gateway에서 {len(devices)}개 기기 조회 성공")
            logger.info(f"   기기: {[d.get('name') for d in devices]}")
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "source": "gateway"
            }
        else:
            logger.warning("⚠️  Gateway 기기 조회 실패, MOCK_DEVICES 사용")
            
            return {
                "success": False,
                "devices": MOCK_DEVICES,
                "count": len(MOCK_DEVICES),
                "source": "mock_fallback",
                "error": "Gateway 통신 실패"
            }
    
    except Exception as e:
        logger.error(f"❌ 기기 조회 중 오류: {e}", exc_info=True)
        
        return {
            "success": False,
            "devices": MOCK_DEVICES,
            "count": len(MOCK_DEVICES),
            "source": "mock_fallback",
            "error": str(e)
        }


@router.post("/{device_id}/click")
async def handle_device_click(device_id: str, request: DeviceClickRequest):
    """기능: 기기 클릭 이벤트를 처리하고 기기 제어.
    
    ✅ 기기 정보: Gateway에서 직접 조회
    ✅ 기기 제어: AI-Services 경유
    
    Flow:
    1. Gateway에서 기기 목록 조회 (현재 상태 확인)
    2. 액션 매핑: "toggle" → 기기별 구체적 액션
    3. AI-Services로 기기 제어 요청
    4. AI-Services → Gateway → LG ThinQ API
    
    args: device_id (path), user_id, action (body)
    return: 성공 여부, device_id, action, 메시지
    """
    try:
        user_id = request.user_id or "default_user"
        action = request.action or "toggle"
        
        logger.info(
            f"🎯 기기 제어 요청: device_id={device_id}, "
            f"user_id={user_id}, action={action}"
        )
        
        # 1️⃣ Gateway에서 실시간 기기 정보 조회
        logger.info(f"🔍 Gateway에서 기기 정보 조회 중: {device_id}")
        
        gateway_response = await gateway_client.get_devices()
        
        if not gateway_response.get("success"):
            # Gateway 실패 시 MOCK_DEVICES 사용
            logger.warning("⚠️  Gateway 조회 실패, MOCK_DEVICES 사용")
            devices = MOCK_DEVICES
        else:
            devices = gateway_response.get("devices", [])
        
        # 기기 찾기
        device_info = next(
            (d for d in devices if d.get("device_id") == device_id),
            None
        )
        
        if not device_info:
            logger.warning(f"❌ 기기를 찾을 수 없음: {device_id}")
            raise HTTPException(
                status_code=404,
                detail=f"기기를 찾을 수 없습니다: {device_id}"
            )
        
        device_name = device_info.get("name", device_id)
        device_type = device_info.get("device_type", "unknown")
        current_state = device_info.get("state", "off")
        
        logger.info(
            f"📍 기기 정보: 이름={device_name}, 타입={device_type}, 상태={current_state}"
        )
        
        # 2️⃣ 액션 매핑: "toggle" → 기기별 구체적 액션 변환
        mapped_action = convert_toggle_action(device_type, current_state, action)
        logger.info(f"🔄 액션 매핑: {action} → {mapped_action}")
        
        # 3️⃣ AI-Services로 기기 제어 요청 (기기 제어는 반드시 AI-Services 경유)
        try:
            logger.info(f"🚀 AI-Services로 기기 제어 요청:")
            logger.info(f"   - 기기 ID: {device_id}")
            logger.info(f"   - 기기명: {device_name}")
            logger.info(f"   - 기기 타입: {device_type}")
            logger.info(f"   - 액션: {mapped_action}")
            
            # AI-Services POST /api/lg/control
            control_result = await ai_client.send_device_control(
                device_id=device_id,
                action=mapped_action
            )
            
            success = control_result.get("success", True)
            message = control_result.get("message", f"기기 제어 완료: {mapped_action}")
            
            logger.info(f"✅ AI-Services 제어 성공: {message}")
            
        except Exception as e:
            logger.error(f"❌ AI-Services 제어 실패: {e}")
            success = False
            message = f"제어 실패: {str(e)}"
        
        # 4️⃣ 응답
        return {
            "success": success,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "action": mapped_action,
            "message": message
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 기기 제어 중 예기치 않은 오류: {e}", exc_info=True)
        return {
            "success": False,
            "device_id": device_id,
            "message": f"오류: {str(e)}"
        }

