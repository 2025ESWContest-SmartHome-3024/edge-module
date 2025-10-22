"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()


class DeviceClickRequest(BaseModel):
    """기기 클릭 요청."""
    user_id: str = Field(..., description="사용자 ID")
    action: str = Field(..., description="기기 액션 (turn_on, turn_off 등)")


@router.get("/")
async def get_devices():
    """기능: 기기 목록 조회.
    
    args: 없음
    return: 기기 목록, 개수, 소스 (ai_server 또는 local_cache)
    """
    try:
        logger.info("Get device list")
        
        demo_user_id = db.get_demo_user_id()
        demo_user_id_str = str(demo_user_id)
        
        devices = await ai_client.get_user_devices(demo_user_id_str)
        
        if devices:
            db.sync_devices(devices)
            logger.info(f"Fetched {len(devices)} devices from AI Server")
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "source": "ai_server"
            }
        else:
            logger.warning("AI Server failed, using local cache")
            local_devices = db.get_devices()
            
            return {
                "success": True,
                "devices": local_devices,
                "count": len(local_devices),
                "source": "local_cache"
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
        
        # 1단계: 로컬 DB에 클릭 이벤트 기록
        logger.info("Recording device click event in local database")
        # db.record_device_click(user_id, device_id, action)  # 향후 구현
        
        # 2단계: 기기 정보 조회
        devices = db.get_devices()
        device_info = next(
            (d for d in devices if d["device_id"] == device_id),
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
        
        # 3단계: AI Server로 클릭 정보 전송
        try:
            logger.info(
                f"Sending device click to AI Server: "
                f"device_id={device_id}, action={action}"
            )
            click_result = await ai_client.send_device_click(
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                action=action
            )
            logger.info(f"AI Server processed: {click_result.get('message')}")
            
        except Exception as e:
            logger.error(f"Failed to send device click to AI Server: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process device click: {str(e)}"
            )
        
        return {
            "success": True,
            "device_id": device_id,
            "action": action,
            "message": "Device click event saved"
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

