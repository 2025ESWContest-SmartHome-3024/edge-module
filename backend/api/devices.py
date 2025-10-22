"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import pytz
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.ai_client import ai_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()
KST = pytz.timezone('Asia/Seoul')


class DeviceClickRequest(BaseModel):
    """기기 클릭 요청."""
    user_id: str
    action: str
    params: Optional[Dict[str, Any]] = None


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
            logger.info(f"Fetched {len(devices)} devices")
            
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
        logger.error(f"Failed to get devices: {e}")
        return {
            "success": False,
            "devices": [],
            "count": 0,
            "error": str(e)
        }


@router.post("/{device_id}/click")
async def handle_device_click(device_id: str, request: DeviceClickRequest):
    """기능: 기기 클릭 감지 및 액션 정보 저장.
    
    args: device_id (path), user_id, action, params (body)
    return: 성공 여부, device_id, action, 메시지
    """
    try:
        user_id = request.user_id
        action = request.action
        params = request.params or {}
        
        if not user_id:
            logger.warning("Missing user_id in click event")
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if not action:
            logger.warning("Missing action in click event")
            raise HTTPException(status_code=400, detail="action is required")
        
        logger.info(
            f"Device click detected: device_id={device_id}, "
            f"user_id={user_id}, action={action}, params={params}"
        )
        
        # DB에 기기 클릭 이벤트 기록 (향후 analytics 용도)
        # db.record_device_click(user_id, device_id, action)
        
        return {
            "success": True,
            "device_id": device_id,
            "action": action,
            "params": params,
            "message": "Device click event saved"
        }
    
    except HTTPException as e:
        logger.error(f"Validation error: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Failed to process click event: {e}")
        return {
            "success": False,
            "device_id": device_id,
            "message": str(e)
        }

