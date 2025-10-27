"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.services.gateway_client import gateway_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()


class DeviceClickRequest(BaseModel):
    """기기 액션 요청."""
    action: str = Field(..., description="액션명")
    value: Optional[str] = Field(None, description="액션 값 (선택사항)")





# ===============================================================================
# 🔄 기기 동기화 엔드포인트
# ===============================================================================

@router.post("/sync")
async def sync_devices_from_gateway():
    """기능: Gateway에서 모든 기기와 액션을 조회해서 로컬 DB에 동기화.
    
    Flow:
    1. Gateway /api/lg/devices에서 기기 목록 조회
    2. 각 기기의 /api/lg/devices/{id}/profile 조회
    3. 기기 정보 + 액션을 로컬 SQLite DB에 저장
    4. 동기화 결과 반환
    
    Returns:
        {
            "success": true,
            "devices_synced": 5,
            "total_actions": 42,
            "timestamp": "2024-01-01T12:00:00"
        }
    """
    try:
        logger.info("\n" + "="*60)
        logger.info("� 기기 동기화 시작 (Gateway → Local DB)")
        logger.info("="*60)
        
        success = await gateway_client.sync_all_devices_to_db()
        
        if success:
            # 동기화된 기기 수 계산
            all_devices = db.get_devices()
            total_devices = len(all_devices)
            total_actions = 0
            
            for device in all_devices:
                actions = db.get_device_actions(device.get("device_id"))
                total_actions += len(actions)
            
            logger.info("="*60)
            logger.info(f"✅ 동기화 완료!")
            logger.info(f"   - 동기화된 기기: {total_devices}개")
            logger.info(f"   - 총 액션: {total_actions}개")
            logger.info("="*60 + "\n")
            
            return {
                "success": True,
                "devices_synced": total_devices,
                "total_actions": total_actions,
                "timestamp": datetime.now().isoformat(),
                "message": f"성공: {total_devices}개 기기, {total_actions}개 액션"
            }
        else:
            logger.error("❌ 동기화 실패")
            return {
                "success": False,
                "message": "Gateway와의 동기화 실패",
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"❌ 동기화 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# ===============================================================================
# 📋 기기 목록 조회 엔드포인트 (로컬 DB)
# ===============================================================================

@router.get("/")
async def get_devices():
    """기능: 로컬 DB에서 기기 목록 + 각 기기의 사용 가능한 액션 조회.
    
    Flow:
    1. SQLite에서 devices 테이블 조회
    2. 각 기기의 device_actions 조회
    3. Frontend 호환 형식으로 응답
    
    Returns:
        {
            "success": true,
            "devices": [
                {
                    "device_id": "1d7c7408...",
                    "name": "거실 에어컨",
                    "device_type": "air_conditioner",
                    "actions": [
                        {
                            "id": 1,
                            "action_type": "operation",
                            "action_name": "POWER_ON_POWER_OFF",
                            "readable": true,
                            "writable": true,
                            "value_type": "enum",
                            "value_range": "[\"POWER_ON\", \"POWER_OFF\"]"
                        }
                    ]
                }
            ],
            "count": 5,
            "source": "local_db"
        }
    """
    try:
        logger.info("� 기기 목록 조회 (Local DB)")
        
        # 1️⃣ 로컬 DB에서 기기 목록 조회
        devices = db.get_devices()
        
        if not devices:
            logger.warning("⚠️  로컬 DB에 기기가 없음. 먼저 동기화 필요")
            return {
                "success": True,
                "devices": [],
                "count": 0,
                "source": "local_db",
                "message": "기기가 없습니다. POST /api/devices/sync를 실행해주세요."
            }
        
        # 2️⃣ 각 기기의 액션 조회
        device_list = []
        for device in devices:
            device_id = device.get("device_id")
            actions = db.get_device_actions(device_id)
            
            device_list.append({
                "device_id": device_id,
                "name": device.get("alias"),
                "device_type": device.get("device_type"),
                "model_name": device.get("model_name"),
                "actions": actions,
                "action_count": len(actions)
            })
        
        logger.info(f"✅ 기기 조회 성공: {len(device_list)}개")
        
        return {
            "success": True,
            "devices": device_list,
            "count": len(device_list),
            "source": "local_db"
        }
    
    except Exception as e:
        logger.error(f"❌ 기기 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# 🎯 기기 제어 엔드포인트
# ===============================================================================

@router.post("/{device_id}/click")
async def handle_device_action(device_id: str, request: DeviceClickRequest):
    """기능: 기기의 특정 액션 실행.
    
    Flow:
    1. 로컬 DB에서 기기 정보 조회
    2. AI-Services로 기기 제어 요청
    3. AI-Services → Gateway → LG ThinQ API
    
    Args:
        device_id: 기기 ID
        request:
            - action: 액션명 (예: "POWER_ON_POWER_OFF", "temperature_18")
            - value: 액션 값 (선택사항)
    
    Returns:
        {
            "success": true,
            "device_id": "1d7c7408...",
            "device_name": "거실 에어컨",
            "action": "POWER_ON_POWER_OFF",
            "message": "제어 성공"
        }
    """
    try:
        action = request.action
        value = request.value
        
        logger.info(f"🎯 기기 제어 요청:")
        logger.info(f"   - 기기 ID: {device_id}")
        logger.info(f"   - 액션: {action}")
        if value:
            logger.info(f"   - 값: {value}")
        
        # 1️⃣ 로컬 DB에서 기기 정보 조회
        device = db.get_device_by_id(device_id)
        if not device:
            logger.warning(f"❌ 기기를 찾을 수 없음: {device_id}")
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        device_name = device.get("alias", device_id)
        device_type = device.get("device_type")
        
        logger.info(f"   - 기기명: {device_name}")
        logger.info(f"   - 기기타입: {device_type}")
        
        # 2️⃣ AI-Services로 기기 제어 요청
        logger.info(f"🚀 AI-Services로 제어 요청 중...")
        
        control_result = await ai_client.send_device_control(
            user_id="default_user",  # 기본 사용자 ID
            device_id=device_id,
            action=action,
            params={"value": value} if value else None
        )
        
        success = control_result.get("success", True)
        message = control_result.get("message", "제어 완료")
        
        logger.info(f"✅ 제어 결과: {message}")
        
        return {
            "success": success,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "action": action,
            "value": value,
            "message": message
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 기기 제어 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "device_id": device_id,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# ℹ️  기기 상세 정보 조회 엔드포인트
# ===============================================================================

@router.get("/{device_id}")
async def get_device_detail(device_id: str):
    """기능: 특정 기기의 상세 정보 + 모든 액션 조회.
    
    Args:
        device_id: 기기 ID
    
    Returns:
        {
            "success": true,
            "device_id": "1d7c7408...",
            "name": "거실 에어컨",
            "device_type": "air_conditioner",
            "model_name": "LG AC 2024",
            "device_profile": {...},
            "actions": [...]
        }
    """
    try:
        logger.info(f"ℹ️  기기 상세 정보 조회: {device_id}")
        
        device = db.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        actions = db.get_device_actions(device_id)
        
        # device_profile은 JSON 문자열이므로 파싱
        device_profile = device.get("device_profile")
        if isinstance(device_profile, str):
            try:
                device_profile = json.loads(device_profile)
            except:
                device_profile = {}
        
        return {
            "success": True,
            "device_id": device_id,
            "name": device.get("alias"),
            "device_type": device.get("device_type"),
            "model_name": device.get("model_name"),
            "device_profile": device_profile,
            "actions": actions,
            "action_count": len(actions)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 기기 정보 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# 📋 기기 프로필 조회 엔드포인트 (사용 가능한 액션)
# ===============================================================================

@router.get("/{device_id}/profile")
async def get_device_profile(device_id: str):
    """기능: 특정 기기의 프로필 조회 (사용 가능한 모든 액션).
    
    Gateway의 /api/lg/devices/{deviceId}/profile에서 조회한 정보를 DB에서 반환합니다.
    
    Args:
        device_id: 기기 ID
    
    Returns:
        {
            "success": true,
            "device_id": "1d7c7408...",
            "name": "거실 공기청정기",
            "device_type": "air_purifier",
            "actions": [
                {
                    "id": 1,
                    "action_type": "operation",
                    "action_name": "POWER_ON",
                    "readable": true,
                    "writable": true,
                    "value_type": "enum",
                    "value_range": "[\"POWER_ON\", \"POWER_OFF\"]"
                },
                ...
            ]
        }
    """
    try:
        logger.info(f"📋 기기 프로필 조회: {device_id}")
        
        device = db.get_device_by_id(device_id)
        if not device:
            logger.warning(f"⚠️  기기를 찾을 수 없습니다: {device_id}")
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        # DB에서 액션 조회
        actions = db.get_device_actions(device_id)
        
        logger.info(f"✅ 프로필 조회 성공: {len(actions)}개 액션")
        
        return {
            "success": True,
            "device_id": device_id,
            "name": device.get("alias"),
            "device_type": device.get("device_type"),
            "actions": actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 프로필 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# 📊 기기 상태 조회 엔드포인트
# ===============================================================================

@router.get("/{device_id}/state")
async def get_device_state(device_id: str):
    """기능: 특정 기기의 실시간 상태 조회.
    
    Gateway를 통해 LG API에서 기기의 현재 상태를 조회합니다.
    
    Args:
        device_id: 기기 ID
    
    Returns:
        {
            "success": true,
            "device_id": "1d7c7408...",
            "name": "거실 에어컨",
            "device_type": "air_conditioner",
            "state": {
                "device_id": "1d7c7408...",
                "type": "aircon",
                "power": "POWER_OFF",
                "mode": "COOL",
                "current_temp": 22,
                "target_temp": 25,
                "wind_strength": "MID"
            },
            "timestamp": "2025-10-27T22:30:45.123456"
        }
    """
    try:
        logger.info(f"📊 기기 상태 조회: {device_id}")
        
        # DB에서 기기 확인
        device = db.get_device_by_id(device_id)
        if not device:
            logger.warning(f"⚠️  기기를 찾을 수 없습니다: {device_id}")
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        # Gateway를 통해 LG API에서 실시간 상태 조회
        from backend.services.gateway_client import gateway_client
        
        state_response = await gateway_client.get_device_state(device_id)
        
        if not state_response or "error" in state_response:
            logger.warning(f"⚠️  Gateway에서 상태 조회 실패: {state_response}")
            return {
                "success": False,
                "device_id": device_id,
                "message": "Gateway에서 상태를 조회할 수 없습니다",
                "error": state_response.get("error") if isinstance(state_response, dict) else str(state_response)
            }
        
        # 응답 구조 정규화
        state_data = state_response
        
        logger.info(f"✅ 상태 조회 성공")
        
        return {
            "success": True,
            "device_id": device_id,
            "name": device.get("alias"),
            "device_type": device.get("device_type"),
            "state": state_data,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 상태 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


from datetime import datetime

