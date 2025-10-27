"""Gateway와의 직접 통신을 담당하는 클라이언트."""
from __future__ import annotations

import logging
import httpx
from typing import Dict, Any, List, Optional

from backend.core.config import settings

logger = logging.getLogger(__name__)


class GatewayClient:
    """Gateway 직접 통신 클라이언트.
    
    ✅ 기기 목록: Gateway에서 직접 조회
    ❌ 기기 제어: AI-Services 경유
    """
    
    def __init__(self):
        """Gateway 클라이언트 초기화."""
        self.gateway_url = settings.gateway_url.rstrip('/')
        self.devices_endpoint = settings.gateway_devices_endpoint.rstrip('/')
        self.timeout = settings.gateway_request_timeout
        logger.info(f"✅ GatewayClient 초기화: {self.gateway_url}")
    
    async def get_devices(self) -> Dict[str, Any]:
        """Gateway에서 기기 목록 조회 (직접).
        
        Edge-Module이 Gateway에서 직접 기기 목록을 조회합니다.
        
        Returns:
            기기 목록 (표준화된 형식)
            {
                "success": True,
                "devices": [
                    {
                        "device_id": "1d7c7408c31fbaf9ce2ea8634e2eda53f517d835a61440a4f75c5426eadc054a",
                        "name": "거실 공기청정기",
                        "device_type": "air_purifier",
                        "state": "on",
                        "supported_actions": ["turn_on", "turn_off", "clean", "auto"]
                    }
                ],
                "count": 1
            }
        """
        for attempt in range(3):
            try:
                logger.info(f"🔍 Gateway에서 기기 목록 조회 (시도 {attempt + 1}/3)")
                logger.info(f"   - URL: {self.devices_endpoint}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        self.devices_endpoint,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Gateway 응답 형식: {"response": [...]}
                        devices_raw = result.get("response", [])
                        
                        # 표준화된 형식으로 변환
                        devices = []
                        for device in devices_raw:
                            try:
                                device_info = device.get("deviceInfo", {})
                                
                                formatted_device = {
                                    "device_id": device.get("deviceId"),
                                    "name": device_info.get("alias", "Unknown Device"),
                                    "device_type": device_info.get("deviceType", "unknown").lower(),
                                    "state": self._normalize_state(device.get("status", "offline")),
                                    "supported_actions": device_info.get("supportedActions", [])
                                }
                                
                                devices.append(formatted_device)
                                logger.debug(f"  ✓ {formatted_device['name']} ({formatted_device['device_id']})")
                                
                            except Exception as e:
                                logger.warning(f"  ⚠️  기기 변환 실패: {device} - {e}")
                                continue
                        
                        logger.info(f"✅ Gateway 기기 조회 성공: {len(devices)}개 기기")
                        
                        return {
                            "success": True,
                            "devices": devices,
                            "count": len(devices),
                            "source": "gateway"
                        }
                    
                    else:
                        logger.warning(f"⚠️  Gateway 응답 에러: status={response.status_code}")
                        logger.warning(f"   - Response: {response.text[:200]}")
                        
            except httpx.TimeoutException:
                logger.warning(f"⏱️  Gateway 요청 타임아웃 (시도 {attempt + 1}/3)")
            except httpx.RequestError as e:
                logger.warning(f"❌ Gateway 통신 에러: {e} (시도 {attempt + 1}/3)")
            except Exception as e:
                logger.warning(f"❌ 예상치 못한 에러: {e} (시도 {attempt + 1}/3)")
        
        logger.error(f"❌ Gateway 기기 조회 최종 실패")
        return {
            "success": False,
            "devices": [],
            "count": 0,
            "source": "gateway_failed"
        }
    
    @staticmethod
    def _normalize_state(status: str) -> str:
        """상태 정규화 (on/off).
        
        Gateway 응답을 on/off로 통일합니다.
        """
        status_lower = str(status).lower()
        
        if status_lower in ["on", "true", "1", "active", "running"]:
            return "on"
        elif status_lower in ["off", "false", "0", "inactive", "stopped", "offline"]:
            return "off"
        else:
            return "offline"


# 전역 Gateway 클라이언트 인스턴스
gateway_client = GatewayClient()
