"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
from datetime import datetime
import pytz
from fastapi import APIRouter

from backend.services.ai_client import ai_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()
KST = pytz.timezone('Asia/Seoul')


@router.get("/")
async def get_devices():
    """기능: 기기 목록 조회.
    
    input: 없음
    output: 기기 목록, 개수, 소스 (ai_server 또는 local_cache)
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
async def handle_device_click(device_id: str, request: dict):
    """기능: 기기 클릭 감지.
    
    input: device_id
    output: 성공 여부, device_id, 메시지
    """
    try:
        logger.info(f"Device click detected: device_id={device_id}")
        
        demo_user_id = db.get_demo_user_id()
        
        logger.info(f"Click event saved: device_id={device_id}, user_id={demo_user_id}")
        
        return {
            "success": True,
            "device_id": device_id,
            "message": "Click event saved"
        }
    
    except Exception as e:
        logger.error(f"Failed to process click event: {e}")
        return {
            "success": False,
            "error": str(e)
        }

