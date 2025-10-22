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
# Receive Recommendation (AI Server → Backend)
# ============================================================================

class RecommendationRequest(BaseModel):
    """AI Server에서 보내는 추천 요청."""
    recommendation_id: str = Field(..., description="추천 ID")
    title: str = Field(..., description="추천 제목")
    contents: str = Field(..., description="추천 내용")
    user_id: str = Field(..., description="사용자 ID")
    device_id: Optional[str] = Field(None, description="기기 ID")
    action: Optional[str] = Field(None, description="제안 액션")
    confidence: Optional[float] = Field(None, description="신뢰도 (0-1)")


# ============================================================================
# Receive Recommendation Endpoint
# ============================================================================

@router.post("")
async def receive_recommendation(request: RecommendationRequest):
    """기능: AI Server로부터 추천을 수신 (자동 호출).
    
    args: recommendation_id, title, contents, user_id, device_id, action, confidence
    return: success, message
    """
    try:
        logger.info(
            f"Receive recommendation: recommendation_id={request.recommendation_id}, "
            f"title={request.title}"
        )
        logger.info(
            f"Device: {request.device_id}, Action: {request.action}, "
            f"Confidence: {request.confidence}"
        )
        
        if not request.recommendation_id:
            logger.warning("Missing recommendation_id")
            raise HTTPException(status_code=400, detail="recommendation_id required")
        
        if not request.user_id:
            logger.warning("Missing user_id")
            raise HTTPException(status_code=400, detail="user_id required")
        
        logger.info("Recommendation saved, waiting for user feedback")
        
        return {
            "success": True,
            "message": "Recommendation received and saved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process recommendation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process recommendation: {str(e)}"
        )

# ============================================================================
# Submit User Feedback (Frontend → Backend)
# ============================================================================

class UserFeedbackRequest(BaseModel):
    """프론트엔드에서 보내는 사용자 피드백."""
    recommendation_id: str = Field(..., description="추천 ID")
    user_id: str = Field(..., description="사용자 ID")
    accepted: bool = Field(..., description="YES(True) / NO(False)")
    device_id: Optional[str] = Field(None, description="기기 ID")
    action: Optional[str] = Field(None, description="제어 액션")


# ============================================================================
# Submit User Feedback Endpoint
# ============================================================================

@router.post("/feedback")
async def submit_user_feedback(feedback: UserFeedbackRequest):
    """기능: 프론트엔드에서 사용자 피드백(YES/NO) 제출.
    
    args: recommendation_id, user_id, accepted, device_id, action
    return: success, message
    """
    try:
        logger.info(
            f"User feedback: recommendation_id={feedback.recommendation_id}, "
            f"accepted={feedback.accepted}"
        )
        
        # 입력값 검증
        if not feedback.recommendation_id:
            logger.warning("Missing recommendation_id in feedback")
            raise HTTPException(status_code=400, detail="recommendation_id required")
        
        if not feedback.user_id:
            logger.warning("Missing user_id in feedback")
            raise HTTPException(status_code=400, detail="user_id required")
        
        # 1단계: AI Server에 피드백 저장
        try:
            logger.info(f"Sending feedback to AI Server...")
            feedback_result = await ai_client.send_recommendation_feedback(
                recommendation_id=feedback.recommendation_id,
                user_id=feedback.user_id,
                accepted=feedback.accepted
            )
            
            if not feedback_result.get("success", False):
                logger.error(f"AI Server feedback failed: {feedback_result.get('message')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save feedback: {feedback_result.get('message')}"
                )
            
            logger.info(f"Feedback saved to AI Server successfully")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send feedback to AI Server: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save feedback: {str(e)}"
            )
        
        # 2단계: YES인 경우 기기 제어 실행
        if feedback.accepted:
            if not feedback.device_id or not feedback.action:
                logger.warning(
                    f"Accepted feedback but missing device_id or action: "
                    f"device_id={feedback.device_id}, action={feedback.action}"
                )
                raise HTTPException(
                    status_code=400,
                    detail="device_id and action required when accepted=true"
                )
            
            try:
                logger.info(
                    f"Execute device control: device_id={feedback.device_id}, "
                    f"action={feedback.action}"
                )
                control_result = await ai_client.send_device_control(
                    user_id=feedback.user_id,
                    device_id=feedback.device_id,
                    action=feedback.action
                )
                
                if not control_result.get("success", False):
                    logger.error(
                        f"Device control failed: {control_result.get('message')}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to execute device control: {control_result.get('message')}"
                    )
                
                logger.info(
                    f"Device control completed: {control_result.get('message')}"
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to execute device control: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to execute device control: {str(e)}"
                )
        else:
            logger.info("Feedback rejected (user selected NO)")
        
        return {
            "success": True,
            "message": "Feedback saved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_user_feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )

