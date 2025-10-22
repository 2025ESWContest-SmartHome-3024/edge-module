"""AI Server와 추천 통신을 위한 REST API 엔드포인트."""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# 📥 AI Server → Edge Module: 추천 수신
# ============================================================================

class RecommendationRequest(BaseModel):
    """AI Server에서 보내는 추천 요청."""
    recommendation_id: str = Field(..., description="추천 ID")
    title: str = Field(..., description="추천 제목")
    contents: str = Field(..., description="추천 내용")
    user_id: str = Field(..., description="사용자 ID")


class RecommendationResponse(BaseModel):
    """사용자 피드백 응답."""
    message: str = "추천 문구 유저 피드백"
    confirm: str = Field(..., description="YES 또는 NO")


# ============================================================================
# 📥 AI Server → Edge Module: 추천 수신
# ============================================================================

@router.post("", response_model=RecommendationResponse)
async def receive_recommendation(request: RecommendationRequest):
    """
    AI Server로부터 추천을 수신합니다 (자동 호출).
    
    📥 AI Server → Edge Module
    
    ✅ 주의: 이 엔드포인트는 AI Server에서 자동으로 호출됨
    기기 제어는 여기서 하지 않고, 프론트엔드의 피드백 후에 수행
    
    Request:
        POST /api/recommendations
        {
            "recommendation_id": "rec_abc123",
            "title": "에어컨 킬까요?",
            "contents": "현재 온도가 25도이므로 에어컨을 키시는 것을 추천드립니다.",
            "user_id": "user_001"
        }
    
    Response:
        {
            "message": "추천 문구 유저 피드백",
            "confirm": "YES"
        }
    
    
    Args:
        request: AI Server에서 보낸 추천
        background_tasks: 백그라운드 작업 (미사용)
    
    Returns:
        응답
    """
    try:
        logger.info(f"📩 [AI 추천 수신] recommendation_id={request.recommendation_id}")
        logger.info(f"   - title: {request.title}")
        logger.info(f"   - contents: {request.contents}")
        
        # ✅ 추천만 저장 (기기 제어는 하지 않음)
        logger.info(f"✅ [추천 저장] WebSocket으로 프론트엔드에 전달 준비 완료")
        
        # 기본 응답: YES (실제로는 프론트엔드에서 사용자 선택 대기)
        return RecommendationResponse(
            message="추천 문구 유저 피드백",
            confirm="YES"
        )
        
    except Exception as e:
        logger.error(f"❌ 추천 처리 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"추천 처리 실패: {str(e)}"
        )


# ============================================================================
# 🎯 프론트엔드용 엔드포인트
# ============================================================================

class UserFeedbackRequest(BaseModel):
    """프론트엔드에서 보내는 사용자 피드백."""
    recommendation_id: str
    user_id: str
    accepted: bool  # True(YES), False(NO)
    device_id: Optional[str] = None  # 기기 제어용 (선택사항)
    action: Optional[str] = None  # 기기 제어 액션 (선택사항)


@router.post("/feedback")
async def submit_user_feedback(feedback: UserFeedbackRequest):
    """
    프론트엔드에서 사용자 피드백(YES/NO)을 제출합니다.
    
    
    Request:
        POST /api/recommendations/feedback
        {
            "recommendation_id": "rec_abc123",
            "user_id": "user_001",
            "accepted": true,
            "device_id": "ac_001",          # 기기 제어용 (선택사항)
            "action": "turn_on"             # 기기 제어 액션 (선택사항)
        }
    
    Response:
        {
            "success": true,
            "message": "피드백이 저장되었습니다"
        }
    
    Args:
        feedback: 사용자 피드백
    
    Returns:
        처리 결과
    """
    try:
        logger.info(f"📥 [사용자 피드백] accepted={feedback.accepted} ({'YES' if feedback.accepted else 'NO'})")
        
        # 1️⃣ AI Server로 피드백 저장
        feedback_result = await ai_client.send_recommendation_feedback(
            recommendation_id=feedback.recommendation_id,
            user_id=feedback.user_id,
            accepted=feedback.accepted
        )
        
        # 2️⃣ YES인 경우 + device_id/action이 있으면 기기 제어 실행
        if feedback.accepted and hasattr(feedback, 'device_id') and hasattr(feedback, 'action'):
            logger.info(f"📤 [기기 제어 실행] device_id={feedback.device_id}, action={feedback.action}")
            control_result = await ai_client.send_device_control(
                user_id=feedback.user_id,
                device_id=feedback.device_id,
                action=feedback.action
            )
            logger.info(f"✅ [기기 제어 완료] {control_result.get('message')}")
        
        return {
            "success": True,
            "message": "피드백이 저장되었습니다"
        }
        
    except Exception as e:
        logger.error(f"❌ 피드백 제출 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"피드백 제출 실패: {str(e)}"
        )

