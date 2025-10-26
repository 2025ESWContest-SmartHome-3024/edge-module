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
        
        AI Server의 /api/lg/control 엔드포인트 호출
        → Gateway의 /api/lg/control 호출
        → LG ThinQ API 제어
        
        args: user_id, device_id, action, params
        return: 제어 결과 (message)
        
        응답 형식:
        {
            "message": "[GATEWAY] 스마트 기기(공기청정기) 제어 완료"
        }
        """
        url = f"{self.base_url}/api/lg/control"
        
        # AI-Services의 /api/lg/control 엔드포인트 요청 형식
        # (Gateway와 동일한 형식)
        payload = {
            "device_id": device_id,
            "action": action
        }
        
        try:
            logger.info(f"🚀 AI Server로 기기 제어 요청:")
            logger.info(f"  - URL: {url}")
            logger.info(f"  - 기기: {device_id}")
            logger.info(f"  - 액션: {action}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                message = result.get("message", "기기 제어 완료")
                
                logger.info(f"✅ 기기 제어 성공: {message}")
                logger.info(f"   AI-Server → Gateway → LG Device 제어 완료")
                
                return {
                    "success": True,
                    "message": message,
                    "device_id": device_id,
                    "action": action
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ AI Server 기기 제어 실패:")
            logger.error(f"   Status: {e.response.status_code}")
            logger.error(f"   Detail: {e.response.text}")
            return {
                "success": False,
                "message": f"기기 제어 실패: {e.response.text}",
                "device_id": device_id,
                "action": action
            }
        except httpx.TimeoutException:
            logger.error(f"❌ AI Server 통신 타임아웃: {device_id}")
            return {
                "success": False,
                "message": f"AI Server 통신 타임아웃 ({self.timeout}초)",
                "device_id": device_id,
                "action": action
            }
        except Exception as e:
            logger.error(f"❌ 기기 제어 중 오류: {e}")
            return {
                "success": False,
                "message": f"기기 제어 실패: {str(e)}",
                "device_id": device_id,
                "action": action
            }
    
    # =========================================================================
    # Get User Devices
    # =========================================================================
    
    async def get_user_devices(self, user_id: str) -> list[Dict[str, Any]]:
        """기능: AI Server를 통해 Gateway의 기기 목록을 조회.
        
        AI Server의 /api/lg/devices 엔드포인트를 통해
        Gateway의 LG 기기 목록을 조회합니다.
        
        args: user_id
        return: 기기 목록 (LG Gateway 형식)
        """
        # AI-Services에서 Gateway를 통해 기기를 조회
        # /api/lg/devices 엔드포인트 사용
        url = f"{self.base_url}/api/lg/devices"
        
        try:
            logger.info(f"🔍 AI Server를 통해 기기 목록 조회:")
            logger.info(f"  - URL: {url}")
            logger.info(f"  - 사용자: {user_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                
                # AI Server의 응답 형식: { "response": [...] } 또는 [...]
                devices = []
                
                if isinstance(result, dict) and "response" in result:
                    # AI-Services → Gateway 응답 형식
                    devices = result.get("response", [])
                elif isinstance(result, dict) and "devices" in result:
                    # 호환성 형식
                    devices = result.get("devices", [])
                elif isinstance(result, list):
                    # 직접 배열 형식
                    devices = result
                    logger.warning("⚠️  AI Server가 직접 배열 형식 반환 (권장: {\"response\": [...]} 형식)")
                
                logger.info(f"✅ AI Server에서 {len(devices)}개 기기 조회 완료")
                
                return devices
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ AI Server 기기 조회 실패:")
            logger.error(f"   Status: {e.response.status_code}")
            logger.error(f"   Detail: {e.response.text}")
            return []
        except httpx.TimeoutException:
            logger.error(f"❌ AI Server 통신 타임아웃: {user_id}")
            return []
        except Exception as e:
            logger.error(f"❌ 기기 조회 중 오류: {e}")
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
        
        args: user_id, username, has_calibration
        return: AI Server 응답 (success, message)
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
    # AI Recommendation
    # =========================================================================
    
    async def send_recommendation(
        self,
        title: str,
        contents: str
    ) -> Dict[str, Any]:
        """기능: AI 추천을 하드웨어(Frontend)에 전송.
        
        AI Service가 생성한 추천을 사용자에게 보여주고 확인 대기.
        사용자가 YES 선택시 기기 제어 정보 포함.
        
        args: title (추천 제목), contents (추천 내용)
        return: 응답 (message, confirm: YES/NO, device_control)
        """
        url = f"{self.base_url}/api/recommendations"
        
        payload = {
            "title": title,
            "contents": contents
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Send recommendation: title={title}")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                
                # 응답 형식 검증
                confirm = result.get("confirm", "NO")
                device_control = result.get("device_control")
                
                logger.info(f"Recommendation response: confirm={confirm}")
                
                if confirm == "YES" and device_control:
                    logger.info(f"User confirmed recommendation, device_control: {device_control}")
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to send recommendation: {e}")
            return {
                "success": False,
                "message": f"Failed to send recommendation: {str(e)}",
                "confirm": "NO"
            }
    
    # =========================================================================
    # Device Click Event
    # =========================================================================
    
    async def send_device_click(
        self,
        user_id: str,
        device_id: str,
        device_name: str,
        device_type: str,
        action: str
    ) -> Dict[str, Any]:
        """기능: 기기 클릭 이벤트를 AI Server로 전송.
        
        args: user_id, device_id, device_name, device_type, action
        return: 결과 (success, message, recommendation)
        """
        url = f"{self.base_url}/api/gaze/click"
        
        payload = {
            "user_id": user_id,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "action": action,
            "timestamp": datetime.now(KST).isoformat()
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    f"Send device click: user_id={user_id}, device_id={device_id}, "
                    f"action={action}"
                )
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Device click processed: {device_id}, action: {action}")
                
                return result
                
        except Exception as e:
            logger.warning(f"Failed to send device click: {e}")
            return {
                "success": False,
                "message": f"Failed to send device click: {str(e)}"
            }
    
    # =========================================================================
    # Fallback Response
    # =========================================================================
    
    @staticmethod
    def _get_fallback_response(request: Dict[str, Any]) -> Dict[str, Any]:
        """기능: AI Server 오류 시 기본 응답 반환.
        
        args: request (원본 요청)
        return: 기본 응답
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