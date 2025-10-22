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
    
    기능:
    - 기기 클릭 이벤트를 AI 서버로 전송
    - AI 서버의 응답에서 추천 받기 
    - 사용자 피드백을 AI 서버로 전송
    - 자동 재시도 + 타임아웃 처리
    - Fallback 추천 제공
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
    # 1️⃣ 기기 클릭 이벤트 전송 (추천은 응답에 포함)
    # =========================================================================
    
    async def send_device_click(
        self, 
        gaze_click_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        기기 클릭 이벤트를 AI 서버로 전송합니다.
        
        ⭐ AI Server는 LG Gateway를 통해 기기를 제어하고,
           추천 메시지를 반환합니다.
        
        Args:
            gaze_click_request: {
                "user_id": "user_001",
                "device_id": "b403...",
                "device_name": "에어컨",
                "device_type": "air_conditioner",
                "timestamp": "2024-10-21T10:30:00+09:00"
            }
        
        Returns:
            AI 서버 응답:
            {
                "status": "success",
                "recommendation": {
                    "recommendation_id": "rec_abc123",
                    "title": "에어컨 킬까요?",
                    "contents": "현재 온도가 25도이므로...",
                    "confidence": 0.95
                },
                "message": "클릭 이벤트 처리됨"
            }
        """
        url = f"{self.base_url}/api/gaze/click"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(
                        f"📤 AI 서버 클릭 이벤트 전송: POST {url}\n"
                        f"   - session_id: {gaze_click_request.get('session_id')}\n"
                        f"   - device: {gaze_click_request.get('clicked_device', {}).get('name')}\n"
                        f"   - 시도: {attempt + 1}/{self.max_retries}"
                    )
                    
                    response = await client.post(
                        url,
                        json=gaze_click_request,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    response.raise_for_status()
                    
                    result = response.json()
                    logger.info(
                        f"✅ AI 서버 응답 성공\n"
                        f"   - click_id: {result.get('click_id')}\n"
                        f"   - 추천: {result.get('recommendation', {}).get('recommendation_id')}"
                    )
                    
                    return result
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ AI 서버 타임아웃 (시도 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"   {wait_time}초 대기 후 재시도...")
                    await asyncio.sleep(wait_time)
                continue
                
            except httpx.HTTPError as e:
                logger.warning(f"🔴 AI 서버 HTTP 오류 (시도 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"   {wait_time}초 대기 후 재시도...")
                    await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                logger.error(f"❌ AI 서버 통신 오류: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
        
        # 모든 재시도 실패 시 Fallback 반환
        logger.warning("⚠️ AI 서버 통신 실패, Fallback 추천 사용")
        return self._get_fallback_response(gaze_click_request)
    
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
    # 4️⃣ 추천 문구 피드백 전송 (새로운 기능)
    # =========================================================================
    
    async def send_recommendation_feedback(
        self,
        recommendation_id: str,
        user_id: str,
        accepted: bool
    ) -> Dict[str, Any]:
        """
        사용자 피드백을 AI Server로 전송합니다.
        
        동작 흐름:
        1. AI Server → Edge Module: 추천 제목 + 내용 수신 (POST /api/recommendations)
        2. 사용자: YES/NO 선택 (프론트엔드)
        3. Edge Module → AI Server: 피드백 전송 (이 메서드)
        
        Args:
            recommendation_id: 추천 ID
            user_id: 사용자 ID
            accepted: True(YES) 또는 False(NO)
        
        Returns:
            AI 서버의 응답:
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
                    f"📤 AI 서버 피드백 전송: POST {url}\n"
                    f"   - recommendation_id: {recommendation_id}\n"
                    f"   - user_id: {user_id}\n"
                    f"   - accepted: {accepted}"
                )
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(
                    f"✅ AI 서버 피드백 전송 성공\n"
                    f"   - accepted: {accepted}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"❌ AI 서버 피드백 전송 실패: {e}")
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