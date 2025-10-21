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
    """
    기기 목록을 조회합니다 (데모는 1명 사용자).
    
    Returns:
        {
            "success": true,
            "devices": [...],
            "count": 3,
            "source": "ai_server"
        }
    """
    try:
        logger.info("📋 기기 목록 조회")
        
        demo_user_id = db.get_demo_user_id()
        demo_user_id_str = str(demo_user_id)
        
        devices = await ai_client.get_user_devices(demo_user_id_str)
        
        if devices:
            db.sync_devices(devices)
            logger.info(f"✅ {len(devices)}개 기기 조회")
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "source": "ai_server"
            }
        else:
            logger.warning("⚠️ AI Server 실패, 로컬 캐시 사용")
            local_devices = db.get_devices()
            
            return {
                "success": True,
                "devices": local_devices,
                "count": len(local_devices),
                "source": "local_cache"
            }
    
    except Exception as e:
        logger.error(f"❌ 기기 목록 조회 실패: {e}")
        return {
            "success": False,
            "devices": [],
            "count": 0,
            "error": str(e)
        }


@router.post("/{device_id}/click")
async def handle_device_click(device_id: str, request: dict):
    """
    기기 제어 (gaze click 감지).
    
    POST /api/devices/{device_id}/click
    Body: {"command": "turn_on"}
    """
    try:
        logger.info(f"🎯 기기 제어: {device_id}")
        
        demo_user_id = db.get_demo_user_id()
        
        # ai_client.send_device_click 메서드의 올바른 시그니처
        # 전체 gaze_click_request Dict를 전달해야 함
        gaze_click_request = {
            "user_id": str(demo_user_id),
            "session_id": f"session_{device_id}_{datetime.now(KST).timestamp()}",
            "clicked_device": {
                "device_id": device_id,
                "name": device_id,
                "type": "unknown"
            },
            "timestamp": datetime.now(KST).isoformat(),
            "context": {
                "command": request.get("command", "toggle")
            }
        }
        
        result = await ai_client.send_device_click(gaze_click_request)
        
        logger.info(f"✅ 기기 제어 신호 전송 완료")
        
        return {
            "success": True,
            "device_id": device_id,
            "result": result
        }
    
    except Exception as e:
        logger.error(f"❌ 기기 제어 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }

