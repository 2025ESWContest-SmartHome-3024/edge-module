"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트.

⭐ Edge Module의 역할
─────────────────────────────────────────────────────────────

이 API는 Gateway와 직접 통신하지 않습니다.
대신 AI Server가 이 정보를 참고하여 Gateway에 명령합니다.

📊 데이터 흐름:
─────────────────────────────────────────────────────────────

Frontend (기기 클릭)
    ↓
    POST /api/devices/{device_id}/click
Edge Module Backend (클릭 정보 수집)
    ↓
    AI Server (추천 생성)
    │
    ├─→ 추천을 Frontend에 표시
    │
    └─→ 사용자 "적용" 클릭 시
        POST /api/devices/feedback/apply
        Edge Module (피드백 전송)
            ↓
            AI Server (추천 적용 처리)
                ↓
                🔥 Gateway: POST /api/lg/control ← AI Server가 호출
                    ↓
                    기기 제어 완료

⚠️ 중요: Edge Module은 Gateway를 직접 호출하지 않습니다!
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
from datetime import datetime
import pytz

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.core.database import db

logger = logging.getLogger(__name__)

router = APIRouter()
KST = pytz.timezone('Asia/Seoul')


# ============================================================================
# Pydantic 모델
# ============================================================================

class DeviceClickRequest(BaseModel):
    """시선 클릭 요청 (Frontend에서 보냄)."""
    user_id: str = Field(..., description="사용자 ID")
    session_id: str = Field(..., description="세션 ID")
    clicked_device: Dict[str, Any] = Field(..., description="클릭된 기기 정보")


class RecommendationFeedback(BaseModel):
    """✅ 추천 피드백 모델 (필수 정보만)"""
    recommendation_id: str = Field(..., description="추천 ID")
    user_id: str = Field(..., description="사용자 ID")
    session_id: str = Field(..., description="세션 ID")
    accepted: bool = Field(..., description="True = 적용, False = 나중에")


# ============================================================================
# 기기 조회 엔드포인트
# ============================================================================

@router.get("/")
async def get_devices(user_id: str):
    """
    사용자의 기기 목록을 조회합니다.
    
    1️⃣ AI Server에서 기기 목록 조회
    2️⃣ 로컬 DB에 동기화 (캐싱)
    3️⃣ Frontend에 반환
    
    GET /api/devices?user_id=user_001
    
    Returns:
        {
            "success": true,
            "devices": [
                {
                    "device_id": "ac_001",
                    "device_name": "거실 에어컨",
                    "device_type": "airconditioner",
                    "capabilities": ["turn_on", "turn_off", "set_temperature"]
                },
                ...
            ],
            "count": 3,
            "source": "ai_server"  // or "local_cache"
        }
    """
    try:
        logger.info(f"📋 기기 목록 조회 요청: user_id={user_id}")
        
        # 1️⃣ AI Server에서 기기 목록 조회
        devices = await ai_client.get_user_devices(user_id)
        
        if devices:
            # 2️⃣ 로컬 DB에 동기화
            local_user_id = db.get_or_create_user(user_id)
            db.sync_devices(local_user_id, devices)
            
            logger.info(f"✅ AI Server에서 {len(devices)}개 기기 조회 + 로컬 동기화")
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "source": "ai_server"
            }
        else:
            # AI Server 실패 시 로컬 DB에서 가져오기
            logger.warning("⚠️ AI Server 실패, 로컬 캐시 사용")
            local_user_id = db.get_or_create_user(user_id)
            local_devices = db.get_user_devices(local_user_id)
            
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


# ============================================================================
# 기기 클릭 엔드포인트
# ============================================================================

@router.post("/{device_id}/click")
async def handle_device_click(device_id: str, request: DeviceClickRequest):
    """
    기기를 시선으로 클릭했을 때 호출됩니다.
    
    POST /api/devices/{device_id}/click
    {
        "user_id": "1",
        "session_id": "session_xyz_1729443600",
        "clicked_device": {
            "device_id": "ac_001",
            "device_name": "에어컨",
            "device_type": "airconditioner"
        }
    }
    
    동작:
    1️⃣ AI Server에 클릭 이벤트 전송
    2️⃣ AI Server가 응답에 추천을 포함해서 반환
    3️⃣ 응답의 추천을 Frontend로 반환
    
    Returns:
        {
            "success": true,
            "recommendation": {...},
            "recommendation_id": "rec_abc123",
            "session_id": "session_xyz_1729443600"
        }
    """
    try:
        gaze_click_request = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "clicked_device": request.clicked_device,
            "timestamp": datetime.now(KST).isoformat(),
            "context": {}
        }
        
        logger.info(
            f"📍 기기 클릭: {request.clicked_device.get('device_name')} (user_id={request.user_id})"
        )
        
        # ✅ AI Server로 전송 (응답에 추천 포함)
        ai_response = await ai_client.send_device_click(gaze_click_request)
        
        # 응답에서 추천 꺼내기
        recommendation = ai_response.get("recommendation", {})
        
        logger.info(
            f"✅ 추천 수신됨: {recommendation.get('recommendation_id')}"
        )
        
        return {
            "success": True,
            "recommendation": recommendation,
            "recommendation_id": recommendation.get("recommendation_id"),
            "session_id": request.session_id,
            "status": ai_response.get("status")
        }
    
    except Exception as e:
        logger.error(f"❌ 기기 클릭 처리 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# 추천 피드백 엔드포인트
# ============================================================================

@router.post("/feedback/apply")
async def apply_recommendation(feedback: RecommendationFeedback):
    """
    추천을 적용합니다 (사용자가 "적용하기" 클릭).
    
    POST /api/devices/feedback/apply
    {
        "recommendation_id": "rec_abc123",
        "user_id": "1",
        "session_id": "session_xyz_1729443600",
        "accepted": true
    }
    
    Returns:
        {
            "success": true,
            "message": "추천이 적용되었습니다"
        }
    """
    try:
        logger.info(
            f"🚀 추천 적용\n"
            f"   - recommendation_id: {feedback.recommendation_id}\n"
            f"   - user_id: {feedback.user_id}"
        )
        
        # ✅ 피드백만 전송 (비동기)
        feedback_data = {
            "recommendation_id": feedback.recommendation_id,
            "user_id": feedback.user_id,
            "session_id": feedback.session_id,
            "accepted": True
        }
        
        asyncio.create_task(
            ai_client.send_feedback(feedback_data)
        )
        
        logger.info(f"✅ 피드백 전송 (백그라운드): {feedback.recommendation_id}")
        
        return {
            "success": True,
            "message": "추천이 적용되었습니다",
            "recommendation_id": feedback.recommendation_id
        }
    
    except Exception as e:
        logger.error(f"❌ 추천 적용 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/feedback/reject")
async def reject_recommendation(feedback: RecommendationFeedback):
    """
    추천을 거절합니다 (사용자가 "나중에" 클릭).
    
    POST /api/devices/feedback/reject
    {
        "recommendation_id": "rec_abc123",
        "user_id": "1",
        "session_id": "session_xyz_1729443600",
        "accepted": false
    }
    
    Returns:
        {
            "success": true,
            "message": "나중에 보기 - 피드백 전송됨"
        }
    """
    try:
        logger.info(
            f"⏰ 추천 거절: {feedback.recommendation_id}"
        )
        
        # ✅ 피드백만 전송 (비동기)
        feedback_data = {
            "recommendation_id": feedback.recommendation_id,
            "user_id": feedback.user_id,
            "session_id": feedback.session_id,
            "accepted": False
        }
        
        asyncio.create_task(
            ai_client.send_feedback(feedback_data)
        )
        
        logger.info(f"✅ 피드백 전송 (백그라운드): {feedback.recommendation_id}")
        
        return {
            "success": True,
            "message": "나중에 보기 - 피드백 전송됨",
            "recommendation_id": feedback.recommendation_id
        }
    
    except Exception as e:
        logger.error(f"❌ 추천 거절 처리 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }
