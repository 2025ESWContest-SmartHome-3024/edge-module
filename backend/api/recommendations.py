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
# Receive Recommendation
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
# Receive Recommendation Endpoint
# ============================================================================

@router.post("", response_model=RecommendationResponse)
async def receive_recommendation(request: RecommendationRequest):
    """기능: AI Server로부터 추천을 수신 (자동 호출).
    
    args: recommendation_id, title, contents, user_id
    return: message, confirm
    """
    try:
        logger.info(f"Receive recommendation: {request.recommendation_id}")
        logger.info(f"Title: {request.title}")
        
        logger.info(f"Recommendation saved for frontend")
        
        return RecommendationResponse(
            message="추천 문구 유저 피드백",
            confirm="YES"
        )
        
    except Exception as e:
        logger.error(f"Failed to process recommendation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process recommendation: {str(e)}"
        )

# ============================================================================
# Submit User Feedback
# ============================================================================

class UserFeedbackRequest(BaseModel):
    """프론트엔드에서 보내는 사용자 피드백."""
    recommendation_id: str
    user_id: str
    accepted: bool
    device_id: Optional[str] = None
    action: Optional[str] = None


@router.post("/feedback")
async def submit_user_feedback(feedback: UserFeedbackRequest):
    """기능: 프론트엔드에서 사용자 피드백(YES/NO) 제출.
    
    args: recommendation_id, user_id, accepted, device_id, action
    return: success, message
    """
    try:
        logger.info(f"User feedback received: accepted={feedback.accepted}")
        
        feedback_result = await ai_client.send_recommendation_feedback(
            recommendation_id=feedback.recommendation_id,
            user_id=feedback.user_id,
            accepted=feedback.accepted
        )
        
        if feedback.accepted and hasattr(feedback, 'device_id') and hasattr(feedback, 'action'):
            logger.info(f"Execute device control: device_id={feedback.device_id}, action={feedback.action}")
            control_result = await ai_client.send_device_control(
                user_id=feedback.user_id,
                device_id=feedback.device_id,
                action=feedback.action
            )
            logger.info(f"Device control completed: {control_result.get('message')}")
        
        return {
            "success": True,
            "message": "Feedback saved"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )

