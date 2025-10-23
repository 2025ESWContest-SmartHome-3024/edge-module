"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock 기기 데이터 (테스트용)
MOCK_DEVICES = [
    {
        "device_id": "ac_living_room",
        "device_name": "거실 에어컨",
        "device_type": "air_conditioner",
        "metadata": {
            "current_temp": 26,
            "target_temp": 24,
            "mode": "cool",
            "status": "on"
        }
    },
    {
        "device_id": "light_bedroom",
        "device_name": "침실 조명",
        "device_type": "light",
        "metadata": {
            "brightness": 80,
            "color_temp": "warm",
            "status": "on"
        }
    },
    {
        "device_id": "fan_kitchen",
        "device_name": "주방 환풍기",
        "device_type": "fan",
        "metadata": {
            "speed": 2,
            "status": "off"
        }
    },
    {
        "device_id": "tv_living_room",
        "device_name": "거실 TV",
        "device_type": "tv",
        "metadata": {
            "channel": 10,
            "volume": 20,
            "status": "off"
        }
    },
    {
        "device_id": "refrigerator",
        "device_name": "냉장고",
        "device_type": "refrigerator",
        "metadata": {
            "temp": 4,
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
    """기능: 기기 목록 조회.
    
    args: 없음
    return: 기기 목록, 개수, 소스 (ai_server 또는 mock)
    """
    try:
        logger.info("Get device list")
        
        # 테스트 환경: Mock 데이터 반환
        logger.info(f"Returning {len(MOCK_DEVICES)} mock devices for testing")
        
        return {
            "success": True,
            "devices": MOCK_DEVICES,
            "count": len(MOCK_DEVICES),
            "source": "mock"
        }
    
    except Exception as e:
        logger.error(f"Failed to get devices: {e}", exc_info=True)
        return {
            "success": False,
            "devices": [],
            "count": 0,
            "error": str(e)
        }


@router.post("/{device_id}/click")
async def handle_device_click(device_id: str, request: DeviceClickRequest):
    """기능: 기기 클릭 이벤트 기록 및 AI Server로 전송.
    
    args: device_id (path), user_id, action (body)
    return: 성공 여부, device_id, action, 메시지
    """
    try:
        user_id = request.user_id
        action = request.action
        
        if not user_id:
            logger.warning("Missing user_id in click event")
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if not action:
            logger.warning("Missing action in click event")
            raise HTTPException(status_code=400, detail="action is required")
        
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
        
        return {
            "success": True,
            "device_id": device_id,
            "device_name": device_name,
            "action": action,
            "message": f"Device click event processed: {device_name} {action}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in handle_device_click: {e}", exc_info=True)
        return {
            "success": False,
            "device_id": device_id,
            "message": str(e)
        }

