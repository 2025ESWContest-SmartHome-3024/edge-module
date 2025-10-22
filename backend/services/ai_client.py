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
    """AI 서버와의 HTTP 통신을 담당하는 클라이언트.
    
    역할:
    1️⃣ 기기 제어 명령 전송 (send_device_control)
    2️⃣ 추천 피드백 전송 (send_recommendation_feedback)
    3️⃣ 기기 목록 조회 (get_user_devices)
    4️⃣ 사용자 등록 (register_user_async)
    
    주의: 추천은 AI Server에서 자동으로 옴 (요청 불필요)
    """
    
    def __init__(self):
        """AI 서버 클라이언트 초기화."""
        self.base_url = settings.ai_server_url.rstrip('/')
        self.timeout = settings.ai_request_timeout
        self.max_retries = settings.ai_max_retries
        
        logger.info(f"✅ AIServiceClient 초기화: {self.base_url}")
        logger.info(f"   - 타임아웃: {self.timeout}초")
        logger.info(f"   - 최대 재시도: {self.max_retries}회")
    
    # =========================================================================
    # 1️⃣ 기기 제어 명령 전송
    # =========================================================================
    
    async def send_device_control(
        self,
        user_id: str,
        device_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        기기 제어 명령을 AI Server로 전송합니다.
        
        Args:
            user_id: 사용자 ID
            device_id: 기기 ID (예: "ac_001")
            action: 제어 액션 (예: "turn_on", "turn_off", "temp_25")
            params: 추가 파라미터 (선택사항)
        
        Returns:
            제어 결과:
            {
                "success": true,
                "message": "기기 제어 완료",
                "device_id": "ac_001",
                "action": "turn_on"
            }
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
                logger.info(
                    f"📤 [1️⃣ 기기 제어] AI Server로 전송: POST {url}\n"
                    f"   - device_id: {device_id}\n"
                    f"   - action: {action}\n"
                    f"   - params: {params}"
                )
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(
                    f"✅ [기기 제어 완료]\n"
                    f"   - device_id: {device_id}\n"
                    f"   - action: {action}\n"
                    f"   - message: {result.get('message')}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"❌ 기기 제어 실패: {e}")
            return {
                "success": False,
                "message": f"기기 제어 실패: {str(e)}",
                "device_id": device_id,
                "action": action
            }
    
    # =========================================================================
    # 2️⃣ 기기 목록 조회
    # =========================================================================
    
    async def get_user_devices(self, user_id: str) -> list[Dict[str, Any]]:
        """
        사용자의 기기 목록을 AI 서버에서 조회합니다.
        
        AI Server는 LG Gateway의 /api/lg/devices에서 조회한 기기 목록을 반환합니다.
        
        Args:
            user_id: 사용자 ID
        
        Returns:
            기기 목록 (LG Gateway 형식):
            [
                {
                    "deviceId": "9c4d22060d9f...",
                    "deviceInfo": {
                        "deviceType": "DEVICE_AIR_PURIFIER",
                        "modelName": "LG Air Purifier",
                        "alias": "공기청정기",
                        "reportable": true
                    }
                }
            ]
        """
        url = f"{self.base_url}/api/gaze/devices"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"📤 AI 서버 기기 목록 요청: GET {url}")
                
                response = await client.get(
                    url,
                    params={"user_id": user_id},
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                
                # ✅ AI Server 응답 형식에 따라 유연하게 처리
                devices = []
                
                # 방법 1: {"devices": [...]} - 권장
                if isinstance(result, dict) and "devices" in result:
                    devices = result.get("devices", [])
                
                # 방법 2: 배열 직접 반환
                elif isinstance(result, list):
                    devices = result
                    logger.warning("⚠️ AI Server가 배열을 직접 반환함 (권장: {\"devices\": [...]} 형식)")
                
                logger.info(f"✅ AI 서버에서 {len(devices)}개 기기 조회됨")
                
                return devices
                
        except Exception as e:
            logger.warning(f"❌ AI 서버 기기 목록 조회 실패: {e}")
            return []
    
    # =========================================================================
    # 3️⃣ 사용자 등록
    # =========================================================================
    
    async def register_user_async(
        self, 
        user_id: str,
        username: str,
        has_calibration: bool,
    ) -> Dict[str, Any]:
        """
        사용자를 AI 서버에 등록합니다 (비동기).
        
        이 메서드는 로그인 응답을 지연시키지 않도록 비동기 백그라운드 작업으로 실행됩니다.
        
        Args:
            user_id: 로컬 SQLite의 사용자 ID
            username: 사용자명
            has_calibration: 캘리브레이션 여부
        
        Returns:
            AI 서버의 응답
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
                logger.info(f"📤 AI 서버 사용자 등록: POST {url} (username={username})")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"✅ AI 서버 사용자 등록 성공: {username}")
                
                return result
                
        except Exception as e:
            logger.warning(f"⚠️ AI 서버 사용자 등록 실패 (비동기): {e}")
            return {
                "success": False,
                "message": f"AI 서버 등록 실패: {str(e)}"
            }
    
    # =========================================================================
    # 2️⃣ 추천 피드백 전송 (YES/NO)
    # =========================================================================
    
    async def send_recommendation_feedback(
        self,
        recommendation_id: str,
        user_id: str,
        accepted: bool
    ) -> Dict[str, Any]:
        """
        추천 피드백 (YES/NO)을 AI Server로 전송합니다.
        Args:
            recommendation_id: 추천 ID
            user_id: 사용자 ID
            accepted: True(YES) 또는 False(NO)
        
        Returns:
            결과:
            {
                "status": "success",
                "message": "피드백이 저장되었습니다"
            }
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
                logger.info(
                    f"📤 [2️⃣ 추천 피드백] AI Server로 전송: POST {url}\n"
                    f"   - recommendation_id: {recommendation_id}\n"
                    f"   - accepted: {accepted} ({'YES' if accepted else 'NO'})"
                )
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(
                    f"✅ [피드백 저장 완료]\n"
                    f"   - accepted: {accepted} ({'YES' if accepted else 'NO'})"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"❌ 피드백 전송 실패: {e}")
            return {
                "success": False,
                "message": f"피드백 전송 실패: {str(e)}"
            }
    
    # =========================================================================
    # Fallback
    # =========================================================================
    
    @staticmethod
    def _get_fallback_response(request: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI 서버 통신 실패 시 기본 응답을 반환합니다.
        
        Args:
            request: 원본 요청 정보
        
        Returns:
            기본 응답 (click_id + 기본 추천)
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