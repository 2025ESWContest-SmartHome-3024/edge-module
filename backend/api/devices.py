"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock 기기 데이터 (테스트용)
# 지원되는 기기: 공기청정기, 건조기, 에어컨
MOCK_DEVICES = [
    {
        "device_id": "airpurifier_living_room",
        "device_name": "거실 공기청정기",
        "device_type": "airpurifier",
        "metadata": {
            "mode": "auto",
            "pm25": 45,
            "status": "on"
        }
    },
    {
        "device_id": "dryer_laundry",
        "device_name": "세탁실 건조기",
        "device_type": "dryer",
        "metadata": {
            "time_remaining": 45,
            "temperature": 70,
            "status": "off"
        }
    },
    {
        "device_id": "aircon_living_room",
        "device_name": "거실 에어컨",
        "device_type": "aircon",
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


@router.get("/")
async def get_devices():
    """기능: 기기 목록 조회 (AI-Services Gateway와 동기화).
    
    AI-Services를 통해 Gateway의 LG 기기 목록을 조회하여
    호환되는 형식으로 반환합니다.
    
    args: 없음
    return: 기기 목록, 개수, 동기화 상태
    """
    try:
        logger.info("📋 기기 목록 조회 (AI-Services → Gateway)")
        
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
        
        # 2️⃣ 반환 형식 준비
        # AI-Services는 Gateway 형식 그대로 반환하므로 필요한 경우만 변환
        formatted_devices = devices if devices else MOCK_DEVICES
        
        logger.info(f"✅ 최종 반환: {len(formatted_devices)}개 기기")
        
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
    3. AI Server로 추천 요청 (선택적)
    4. 기기 제어 실행
    5. 추천이 있으면 WebSocket으로 푸시
    
    args: device_id (path), user_id, action (body)
    return: 성공 여부, device_id, action, 메시지, recommendation (optional)
    """
    try:
        user_id = request.user_id or "default_user"
        action = request.action or "toggle"
        
        logger.info(
            f"Device click received: device_id={device_id}, "
            f"user_id={user_id}, action={action}"
        )
        
        logger.info(
            f"Device click detected: device_id={device_id}, "
            f"user_id={user_id}, action={action}"
        )
        
        # 기기 정보 조회
        device_info = next(
            (d for d in MOCK_DEVICES if d["device_id"] == device_id),
            None
        )
        
        if not device_info:
            logger.warning(f"Device not found: {device_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Device not found: {device_id}"
            )
        
        device_name = device_info.get("device_name", device_id)
        device_type = device_info.get("device_type", "unknown")
        
        logger.info(
            f"Device click processed: {device_name} ({device_type}) - {action}"
        )
        
        # ✅ AI Server의 기기 제어 엔드포인트 호출
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
            logger.info(f"  - 액션: {action}")
            
            control_result = await ai_client.send_device_control(
                user_id=user_id,
                device_id=device_id,
                action=action,
                params={}
            )
            
            # AI Server 응답 형식: {"message": "..."}
            success = control_result.get("success", True)
            message = control_result.get("message", f"기기 {action} 완료")
            
            logger.info(f"✅ 기기 제어 완료: {device_name}")
            logger.info(f"   응답: {message}")
            
        except Exception as e:
            logger.error(f"❌ 기기 제어 실패: {e}", exc_info=True)
            success = False
            message = f"기기 제어 실패: {str(e)}"
            control_result = {"success": False, "message": message}
        
        # Frontend 응답 형식
        response_data = {
            "success": success,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "action": action,
            "message": message,
            "result": {}  # 추천은 별도로 처리됨
        }
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in handle_device_click: {e}", exc_info=True)
        return {
            "success": False,
            "device_id": device_id,
            "message": str(e)
        }

