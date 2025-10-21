"""AI Server와 추천 통신을 위한 REST API 엔드포인트."""
from __future__ import annotations

import logging
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
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


# 전역 변수: 현재 대기 중인 추천
current_recommendation: dict | None = None
user_response_event = asyncio.Event()
user_response: str = "NO"


@router.post("", response_model=RecommendationResponse)
async def receive_recommendation(request: RecommendationRequest, background_tasks: BackgroundTasks):
    """
    AI Server로부터 사용자에게 보낼 추천을 받습니다.
    
    API 문서:
    - Request Method: POST
    - URL: /api/recommendations
    - Body:
        {
            "recommendation_id": "rec_abc123",
            "title": "에어컨 킬까요?",
            "contents": "현재 온도가 25도이므로 에어컨을 키시는 것을 추천드립니다.",
            "user_id": "user_001"
        }
    - Response (200):
        {
            "message": "추천 문구 유저 피드백",
            "confirm": "YES" or "NO"
        }
    
    Args:
        request: AI Server에서 보낸 추천
        background_tasks: 백그라운드 작업
    
    Returns:
        사용자 피드백
    """
    global current_recommendation, user_response
    
    try:
        logger.info(f"📩 AI Server로부터 추천 수신")
        logger.info(f"   - recommendation_id: {request.recommendation_id}")
        logger.info(f"   - 제목: {request.title}")
        logger.info(f"   - 내용: {request.contents}")
        logger.info(f"   - user_id: {request.user_id}")
        
        # 현재 추천 저장
        current_recommendation = {
            "recommendation_id": request.recommendation_id,
            "title": request.title,
            "contents": request.contents,
            "user_id": request.user_id
        }
        
        # TODO: WebSocket을 통해 프론트엔드에 추천 전달
        # 사용자가 YES 또는 NO를 선택할 때까지 대기
        
        # 임시: 자동으로 YES 반환 (실제로는 사용자 입력 대기)
        confirm = "YES"
        accepted = confirm == "YES"
        
        logger.info(f"✅ 사용자 피드백: {confirm}")
        
        # 백그라운드에서 AI Server로 피드백 전송
        background_tasks.add_task(
            send_feedback_to_ai_server,
            request.recommendation_id,
            request.user_id,
            accepted
        )
        
        return RecommendationResponse(
            message="추천 문구 유저 피드백",
            confirm=confirm
        )
        
    except Exception as e:
        logger.error(f"❌ 추천 처리 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"추천 처리 실패: {str(e)}"
        )


# ============================================================================
# 📤 Edge Module → AI Server: 피드백 전송
# ============================================================================

async def send_feedback_to_ai_server(
    recommendation_id: str,
    user_id: str,
    accepted: bool
):
    """
    사용자 피드백을 AI Server로 전송합니다 (백그라운드 작업).
    
    Args:
        recommendation_id: 추천 ID
        user_id: 사용자 ID
        accepted: True(YES) 또는 False(NO)
    """
    try:
        logger.info(f"🔄 AI Server로 피드백 전송 시작...")
        
        result = await ai_client.send_recommendation_feedback(
            recommendation_id=recommendation_id,
            user_id=user_id,
            accepted=accepted
        )
        
        if result.get("success", True):
            logger.info(f"✅ AI Server 피드백 전송 완료")
        else:
            logger.warning(f"⚠️ AI Server 피드백 전송 실패: {result.get('message')}")
            
    except Exception as e:
        logger.error(f"❌ AI Server 피드백 전송 오류: {e}")


# ============================================================================
# 🎯 프론트엔드용 엔드포인트 (선택사항)
# ============================================================================

class UserFeedbackRequest(BaseModel):
    """프론트엔드에서 보내는 사용자 피드백."""
    recommendation_id: str
    user_id: str
    accepted: bool  # True(YES), False(NO)


@router.post("/feedback")
async def submit_user_feedback(feedback: UserFeedbackRequest):
    """
    프론트엔드에서 사용자 피드백을 직접 제출할 수 있는 엔드포인트.
    
    Args:
        feedback: 사용자 피드백
    
    Returns:
        처리 결과
    """
    try:
        logger.info(f"📥 프론트엔드로부터 피드백 수신: {feedback.accepted}")
        
        # AI Server로 피드백 전송
        result = await ai_client.send_recommendation_feedback(
            recommendation_id=feedback.recommendation_id,
            user_id=feedback.user_id,
            accepted=feedback.accepted
        )
        
        return {
            "success": True,
            "message": "피드백이 전송되었습니다",
            "ai_server_response": result
        }
        
    except Exception as e:
        logger.error(f"❌ 피드백 제출 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"피드백 제출 실패: {str(e)}"
        )

