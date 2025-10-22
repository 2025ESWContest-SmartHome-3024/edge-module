"""AI 서버와의 HTTP 통신을 담당하는 클라이언트."""
from __future__ import annotations

import logging
import asyncio
import httpx
import pytz
from typing import Dict, Any, Optional
from datetime import datetime

from backend.core.config import settings

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


class AIServiceClient:
    """AI Server HTTP 클라이언트."""
    
    def __init__(self):
        """AI Server 클라이언트 초기화."""
        self.base_url = settings.ai_server_url.rstrip('/')
        self.timeout = settings.ai_request_timeout
        self.max_retries = settings.ai_max_retries
        
        logger.info(f"AIServiceClient initialized: {self.base_url}")
    
    # =========================================================================
    # Device Control
    # =========================================================================
    
    async def send_device_control(
        self,
        user_id: str,
        device_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """기능: 기기 제어 명령을 AI Server로 전송.
        
        input: user_id, device_id, action, params
        output: 제어 결과 (success, message, device_id, action)
        """
        url = f"{self.base_url}/api/lg/control"
        
        payload = {
            "user_id": user_id,
            "device_id": device_id,
            "action": action,
            "params": params or {},
            "timestamp": datetime.now(KST).isoformat()
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Send device control: {device_id}, action: {action}")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Device control success: {device_id}, action: {action}")
                
                return result
                
        except Exception as e:
            logger.error(f"Device control failed: {e}")
            return {
                "success": False,
                "message": f"Device control failed: {str(e)}",
                "device_id": device_id,
                "action": action
            }
    
    # =========================================================================
    # Get User Devices
    # =========================================================================
    
    async def get_user_devices(self, user_id: str) -> list[Dict[str, Any]]:
        """기능: 사용자의 기기 목록을 AI Server에서 조회.
        
        input: user_id
        output: 기기 목록 (LG Gateway 형식)
        """
        url = f"{self.base_url}/api/gaze/devices"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Get user devices: user_id={user_id}")
                
                response = await client.get(
                    url,
                    params={"user_id": user_id},
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                
                devices = []
                
                if isinstance(result, dict) and "devices" in result:
                    devices = result.get("devices", [])
                
                elif isinstance(result, list):
                    devices = result
                    logger.warning("AI Server returned array directly (recommended: {\"devices\": [...]} format)")
                
                logger.info(f"Fetched {len(devices)} devices from AI Server")
                
                return devices
                
        except Exception as e:
            logger.warning(f"Failed to get user devices: {e}")
            return []
    
    # =========================================================================
    # Register User
    # =========================================================================
    
    async def register_user_async(
        self, 
        user_id: str,
        username: str,
        has_calibration: bool,
    ) -> Dict[str, Any]:
        """기능: 사용자를 AI Server에 등록 (비동기 백그라운드).
        
        input: user_id, username, has_calibration
        output: AI Server 응답 (success, message)
        """
        url = f"{self.base_url}/api/users/register"
        
        payload = {
            "user_id": user_id,     
            "username": username,
            "has_calibration": has_calibration,
            "timestamp": datetime.now(KST).isoformat()
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Register user with AI Server: {username}")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"User registration success: {username}")
                
                return result
                
        except Exception as e:
            logger.warning(f"User registration failed (async): {e}")
            return {
                "success": False,
                "message": f"User registration failed: {str(e)}"
            }
    
    # =========================================================================
    # Recommendation Feedback
    # =========================================================================
    
    async def send_recommendation_feedback(
        self,
        recommendation_id: str,
        user_id: str,
        accepted: bool
    ) -> Dict[str, Any]:
        """기능: 추천 피드백 (YES/NO)을 AI Server로 전송.
        
        input: recommendation_id, user_id, accepted
        output: 결과 (status, message)
        """
        url = f"{self.base_url}/api/gaze/feedback"
        
        payload = {
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "accepted": accepted,
            "timestamp": datetime.now(KST).isoformat()
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Send recommendation feedback: {recommendation_id}, accepted={accepted}")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Recommendation feedback sent: accepted={accepted}")
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to send recommendation feedback: {e}")
            return {
                "success": False,
                "message": f"Feedback failed: {str(e)}"
            }
    
    # =========================================================================
    # Fallback Response
    # =========================================================================
    
    @staticmethod
    def _get_fallback_response(request: Dict[str, Any]) -> Dict[str, Any]:
        """기능: AI Server 오류 시 기본 응답 반환.
        
        input: request (원본 요청)
        output: 기본 응답
        """
        device_info = request.get("clicked_device", {})
        
        return {
            "status": "fallback",
            "click_id": f"click_fallback_{request.get('session_id')}",
            "recommendation": {
                "recommendation_id": f"rec_fallback_{datetime.now(KST).timestamp()}",
                "device_id": device_info.get("device_id"),
                "device_name": device_info.get("name"),
                "action": "toggle",
                "params": {},
                "reason": "AI 서버 연결 오류로 기본 토글 동작 제안",
                "confidence": 0.5
            },
            "message": "AI 서버 오류로 Fallback 응답 제공"
        }


# 전역 클라이언트 인스턴스
ai_client = AIServiceClient()