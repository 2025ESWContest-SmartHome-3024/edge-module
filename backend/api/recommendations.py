"""HTTP를 통한 추천 통신 엔드포인트."""
from __future__ import annotations

import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client

router = APIRouter()
logger = logging.getLogger(__name__)

# 현재 표시 중인 추천 저장 (Frontend에서 피드백할 때 사용)
current_recommendation = None


# ============================================================================
# 추천 상태 관리
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


async def broadcast_recommendation(recommendation: dict):
    """기능: 모든 연결된 WebSocket 클라이언트에게 추천 브로드캐스트.
    
    WebSocket /ws/gaze를 통해 모든 클라이언트에 추천 전송.
    
    args: recommendation
    return: None
    """
    try:
        # websocket.py의 manager를 사용하여 브로드캐스트
        from backend.api.websocket import manager
        
        message = {
            "type": "recommendation",
            "data": recommendation
        }
        
        await manager.broadcast(message)
        logger.info(f"Recommendation broadcasted to {len(manager.active_connections)} clients")
        
    except Exception as e:
        logger.error(f"Failed to broadcast recommendation: {e}")


# ============================================================================
# Recommendation Models
# ============================================================================

class AIRecommendationRequest(BaseModel):
    """AI Service에서 Backend를 거쳐 Frontend로 보낼 추천."""
    title: str = Field(..., description="추천 제목")
    contents: str = Field(..., description="추천 내용")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    device_control: Optional[dict] = Field(None, description="기기 제어 정보")


# ============================================================================
# API Endpoints: Recommendation Endpoints
# ============================================================================

@router.post("/push")
async def push_recommendation(request: AIRecommendationRequest):
    """기능: AI Service에서 생성한 추천을 Frontend로 푸시.
    
    AI Service의 /api/recommendations 응답을 
    Backend가 받아 Frontend에 WebSocket으로 전달.
    
    args: title, contents, user_id
    return: 브로드캐스트 결과
    """
    try:
        logger.info(f"Pushing recommendation from AI Service: {request.title}")
        
        recommendation = {
            "recommendation_id": f"rec_ai_{int(time.time() * 1000)}",
            "title": request.title,
            "contents": request.contents,
            "user_id": request.user_id,
            "device_control": request.device_control,
            "source": "ai_service"
        }
        
        # 현재 추천 저장
        set_current_recommendation(recommendation)
        
        # 모든 클라이언트에 브로드캐스트
        await broadcast_recommendation(recommendation)
        
        return {
            "success": True,
            "message": "Recommendation pushed to clients",
            "recommendation_id": recommendation["recommendation_id"]
        }
        
    except Exception as e:
        logger.error(f"Failed to push recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Frontend → Backend: 사용자 응답 전송 (YES/NO)
# ============================================================================

class RecommendationFeedbackRequest(BaseModel):
    """Frontend에서 보내는 사용자 응답."""
    recommendation_id: str = Field(..., description="추천 ID")
    user_id: str = Field(..., description="사용자 ID")
    accepted: bool = Field(..., description="YES(true) / NO(false)")


@router.post("/feedback")
async def submit_recommendation_feedback(feedback: RecommendationFeedbackRequest):
    """기능: 사용자의 추천 응답을 기록.
    
    args: recommendation_id, user_id, accepted
    return: message
    """
    try:
        if not feedback.recommendation_id:
            logger.warning("Missing recommendation_id in feedback")
            raise HTTPException(status_code=400, detail="recommendation_id required")
        
        if not feedback.user_id:
            logger.warning("Missing user_id in feedback")
            raise HTTPException(status_code=400, detail="user_id required")
        
        logger.info(
            f"User feedback recorded: "
            f"rec_id={feedback.recommendation_id}, "
            f"user_id={feedback.user_id}, "
            f"accepted={feedback.accepted}"
        )
        
        # TODO: 피드백을 데이터베이스에 저장 (향후 분석 용도)
        # await db.save_recommendation_feedback(feedback)
        
        return {
            "success": True,
            "message": "Feedback recorded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_recommendation_feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )

