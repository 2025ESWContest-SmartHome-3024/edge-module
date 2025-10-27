"""AI-Services 추천 수신 및 Frontend 브로드캐스트 엔드포인트."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

# 현재 표시 중인 추천 저장 (Frontend에서 피드백할 때 사용)
current_recommendation: Optional[Dict[str, Any]] = None
# 최근 추천 ID와 응답 추적
pending_responses: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# 추천 상태 관리
# ============================================================================

def set_current_recommendation(recommendation: Dict[str, Any]) -> None:
    """현재 표시 중인 추천 저장.
    
    Args:
        recommendation (dict): 추천 정보 (title, contents, device_control 등 포함)
    """
    global current_recommendation
    current_recommendation = recommendation
    logger.info(f"[Recommendations] 📌 현재 추천 저장: {recommendation.get('title')}")


def get_current_recommendation() -> Optional[Dict[str, Any]]:
    """현재 표시 중인 추천 조회.
    
    Returns:
        dict: 추천 정보 또는 None
    """
    return current_recommendation


async def broadcast_recommendation_to_frontend(recommendation: Dict[str, Any]) -> bool:
    """모든 연결된 WebSocket 클라이언트에게 추천 브로드캐스트.
    
    Args:
        recommendation (dict): 추천 정보
        
    Returns:
        bool: 브로드캐스트 성공 여부
    """
    try:
        from backend.api.websocket import manager
        
        message = {
            "type": "recommendation",
            "data": recommendation
        }
        
        # 브로드캐스트 실행
        await manager.broadcast(message)
        
        logger.info(f"[Recommendations] 📢 추천 브로드캐스트: {len(manager.active_connections)}개 클라이언트")
        logger.info(f"  - 제목: {recommendation.get('title')}")
        logger.info(f"  - ID: {recommendation.get('recommendation_id')}")
        
        return True
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 브로드캐스트 실패: {e}")
        return False


# ============================================================================
# Pydantic Models
# ============================================================================

class DeviceControl(BaseModel):
    """기기 제어 정보"""
    device_id: Optional[str] = Field(None, description="기기 ID")
    device_type: Optional[str] = Field(None, description="기기 타입")
    device_name: Optional[str] = Field(None, description="기기명")
    action: Optional[str] = Field(None, description="제어 액션")
    params: Optional[Dict[str, Any]] = Field(None, description="추가 파라미터")


class AIRecommendationRequest(BaseModel):
    """AI-Services에서 Edge-Module로 보내는 추천 요청."""
    title: str = Field(..., description="추천 제목")
    contents: str = Field(..., description="추천 내용")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    device_control: Optional[DeviceControl] = Field(None, description="기기 제어 정보")
    priority: Optional[int] = Field(3, description="우선순위 (1-5)")


class RecommendationFeedbackRequest(BaseModel):
    """Frontend에서 보내는 사용자 응답."""
    recommendation_id: str = Field(..., description="추천 ID")
    user_id: str = Field(..., description="사용자 ID")
    accepted: bool = Field(..., description="YES(true) / NO(false)")


# ============================================================================
# API Endpoints: AI-Services ← → Edge-Module ← → Frontend
# ============================================================================

@router.post("/")
async def receive_recommendation(request: AIRecommendationRequest):
    """AI-Services에서 추천을 수신하고 Frontend로 브로드캐스트.
    
    Flow:
    1. AI-Services가 Edge-Module의 /api/recommendations/ 으로 POST
    2. Edge-Module이 WebSocket을 통해 모든 Frontend 클라이언트에게 브로드캐스트
    3. Frontend에서 사용자 응답 대기
    
    Args:
        request (AIRecommendationRequest): AI-Services의 추천 요청
        
    Returns:
        dict: 추천 ID 및 성공/실패 상태
    """
    try:
        # 추천 ID 생성 (UUID 사용)
        recommendation_id = f"rec_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"[Recommendations] 📥 AI-Services에서 추천 수신:")
        logger.info(f"  - ID: {recommendation_id}")
        logger.info(f"  - 제목: {request.title}")
        logger.info(f"  - 내용: {request.contents[:100]}..." if len(request.contents) > 100 else f"  - 내용: {request.contents}")
        logger.info(f"  - 우선순위: {request.priority}")
        
        if request.device_control:
            logger.info(f"  - 기기 제어:")
            logger.info(f"    - 기기: {request.device_control.device_name} ({request.device_control.device_id})")
            logger.info(f"    - 액션: {request.device_control.action}")
        
        # 추천 객체 생성
        recommendation = {
            "recommendation_id": recommendation_id,
            "title": request.title,
            "description": request.contents,  # Frontend 호환성
            "contents": request.contents,
            "user_id": request.user_id,
            "priority": request.priority,
            "device_id": request.device_control.device_id if request.device_control else None,
            "device_name": request.device_control.device_name if request.device_control else None,
            "action": request.device_control.action if request.device_control else None,
            "params": request.device_control.params if request.device_control else {},
            "device_control": request.device_control.dict() if request.device_control else None,
            "source": "ai_service",
            "timestamp": datetime.now().isoformat(),
            "reason": request.contents  # Frontend RecommendationModal 호환성
        }
        
        # 현재 추천 저장
        set_current_recommendation(recommendation)
        
        # 보류 중인 응답 추적
        pending_responses[recommendation_id] = {
            "timestamp": time.time(),
            "accepted": None,
            "user_responded": False
        }
        
        logger.info(f"[Recommendations] 📝 대기 응답 추적 시작: {recommendation_id}")
        
        # Frontend에 브로드캐스트
        broadcast_success = await broadcast_recommendation_to_frontend(recommendation)
        
        if not broadcast_success:
            logger.warning(f"[Recommendations] ⚠️  브로드캐스트 실패 (클라이언트 없음 가능)")
        
        return {
            "success": True,
            "message": "추천을 Frontend에 전달했습니다",
            "recommendation_id": recommendation_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 추천 수신 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"추천 수신 실패: {str(e)}"
        )


@router.post("/feedback")
async def submit_recommendation_feedback(feedback: RecommendationFeedbackRequest):
    """Frontend의 사용자 응답을 기록 및 AI-Services에 피드백.
    
    Flow:
    1. Frontend가 사용자의 YES/NO 응답을 전송
    2. Edge-Module이 응답을 기록
    3. Edge-Module이 AI-Services에 피드백 전송 (향후 학습용)
    
    Args:
        feedback (RecommendationFeedbackRequest): 사용자 응답
        
    Returns:
        dict: 피드백 기록 결과
    """
    try:
        if not feedback.recommendation_id:
            logger.warning("❌ recommendation_id 누락")
            raise HTTPException(status_code=400, detail="recommendation_id 필수")
        
        if not feedback.user_id:
            logger.warning("❌ user_id 누락")
            raise HTTPException(status_code=400, detail="user_id 필수")
        
        response_text = "승인(YES)" if feedback.accepted else "거절(NO)"
        
        logger.info(f"[Recommendations] 📨 사용자 응답 기록:")
        logger.info(f"  - ID: {feedback.recommendation_id}")
        logger.info(f"  - 사용자: {feedback.user_id}")
        logger.info(f"  - 응답: {response_text}")
        
        # 응답 추적 업데이트
        if feedback.recommendation_id in pending_responses:
            pending_responses[feedback.recommendation_id]["accepted"] = feedback.accepted
            pending_responses[feedback.recommendation_id]["user_responded"] = True
            pending_responses[feedback.recommendation_id]["response_time"] = time.time()
            
            logger.info(f"[Recommendations] ✅ 응답 추적 업데이트: {feedback.recommendation_id}")
        
        # 향후: AI-Services에 피드백 전송 가능
        # await ai_client.send_feedback(feedback_data)
        
        return {
            "success": True,
            "message": f"피드백이 기록되었습니다: {response_text}",
            "recommendation_id": feedback.recommendation_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 피드백 기록 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"피드백 기록 실패: {str(e)}"
        )


@router.get("/pending")
async def get_pending_recommendation():
    """대기 중인 추천 조회.
    
    Frontend가 연결되지 않았을 때 사용하거나, 
    현재 표시 중인 추천을 다시 조회할 때 사용.
    
    Returns:
        dict: 대기 중인 추천 정보 또는 없음 메시지
    """
    try:
        pending = get_current_recommendation()
        
        if pending:
            logger.info(f"[Recommendations] 📋 대기 중인 추천 조회: {pending.get('recommendation_id')}")
            return {
                "success": True,
                "recommendation": pending
            }
        else:
            logger.info(f"[Recommendations] ℹ️ 대기 중인 추천 없음")
            return {
                "success": False,
                "message": "대기 중인 추천이 없습니다"
            }
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 추천 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"추천 조회 실패: {str(e)}"
        )


@router.get("/responses/{recommendation_id}")
async def get_recommendation_response(recommendation_id: str):
    """특정 추천에 대한 사용자 응답 조회 (Polling용).
    
    Frontend가 WebSocket이 아닌 HTTP 폴링으로 응답을 확인할 때 사용.
    
    Args:
        recommendation_id (str): 추천 ID
        
    Returns:
        dict: 사용자 응답 정보 (대기 중, 승인, 거절)
    """
    try:
        if recommendation_id not in pending_responses:
            return {
                "success": False,
                "message": "해당 추천을 찾을 수 없습니다"
            }
        
        response_info = pending_responses[recommendation_id]
        
        status = "pending"  # 기본값: 대기 중
        if response_info["user_responded"]:
            status = "accepted" if response_info["accepted"] else "rejected"
        
        logger.info(f"[Recommendations] 🔍 응답 상태 조회: {recommendation_id} → {status}")
        
        return {
            "success": True,
            "recommendation_id": recommendation_id,
            "status": status,
            "accepted": response_info["accepted"],
            "timestamp": response_info["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 응답 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"응답 조회 실패: {str(e)}"
        )

