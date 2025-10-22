"""MQTT를 통한 추천 통신 엔드포인트."""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.mqtt_client import mqtt_client

router = APIRouter()
logger = logging.getLogger(__name__)

# 현재 표시 중인 추천 저장 (Frontend에서 피드백할 때 사용)
current_recommendation = None


# ============================================================================
# 웹소켓/SSE 같은 실시간 통신으로 Frontend에 추천 푸시
# (별도로 websocket.py에서 처리)
# ============================================================================

def set_current_recommendation(recommendation: dict):
    """기능: 현재 표시 중인 추천 저장.
    
    args: recommendation (title, content 포함)
    return: None
    """
    global current_recommendation
    current_recommendation = recommendation
    logger.info(f"Current recommendation updated: {recommendation.get('title')}")


def get_current_recommendation() -> dict:
    """기능: 현재 표시 중인 추천 조회.
    
    args: None
    return: 추천 정보
    """
    return current_recommendation


# ============================================================================
# Frontend → Backend: 사용자 응답 전송 (YES/NO)
# ============================================================================

class RecommendationFeedbackRequest(BaseModel):
    """Frontend에서 보내는 사용자 응답."""
    title: str = Field(..., description="추천 제목")
    confirm: bool = Field(..., description="YES(true) / NO(false)")


@router.post("/feedback")
async def submit_recommendation_feedback(feedback: RecommendationFeedbackRequest):
    """기능: 사용자의 추천 응답을 MQTT로 AI Server로 전송.
    
    args: title, confirm
    return: message
    """
    try:
        if not feedback.title:
            logger.warning("Missing title in feedback")
            raise HTTPException(status_code=400, detail="title required")
        
        logger.info(
            f"User feedback: title={feedback.title}, confirm={feedback.confirm}"
        )
        
        # MQTT로 피드백 발행
        success = mqtt_client.publish_feedback(
            title=feedback.title,
            confirm=feedback.confirm
        )
        
        if not success:
            logger.warning("Failed to publish feedback via MQTT")
            raise HTTPException(
                status_code=500,
                detail="Failed to send feedback"
            )
        
        return {
            "message": "[EDGE] 추천 명령어 응답 발행 완료"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_recommendation_feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )

