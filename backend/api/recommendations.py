"""AI 기반 디바이스 제어 추천을 위한 REST API 엔드포인트."""
from __future__ import annotations

import random
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client

router = APIRouter()
logger = logging.getLogger(__name__)


class Recommendation(BaseModel):
    """AI에서 생성한 디바이스 제어 추천."""
    id: str
    title: str
    description: str
    device_id: str
    device_name: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str
    priority: int = Field(ge=1, le=5, description="우선순위 1-5, 5가 가장 높음")
    timestamp: str


class RecommendationRequest(BaseModel):
    """AI Server에서 보내는 추천 요청."""
    title: str = Field(..., description="추천 제목")
    contents: str = Field(..., description="추천 내용")


class RecommendationResponse(BaseModel):
    """사용자 피드백 응답."""
    message: str = "추천 문구 유저 피드백"
    confirm: str = Field(..., description="YES 또는 NO")


# Mock 추천 데이터 (Fallback용)
# AI 서버가 응답하지 않을 때만 사용합니다.
# 프로덕션: AI 서버의 GET /api/gaze/recommendations/{user_id}에서 조회
MOCK_RECOMMENDATIONS = [
    {
        "title": "에어컨 온도 조절",
        "description": "현재 실내 온도가 높습니다. 에어컨 온도를 낮추는 것을 추천합니다.",
        "device_id": "ac_001",
        "device_name": "거실 에어컨",
        "action": "set_temperature",
        "params": {"temperature": 23},
        "reason": "실내 온도 26°C로 권장 온도(24°C)보다 높음",
        "priority": 4
    },
    {
        "title": "공기청정기 모드 변경",
        "description": "미세먼지 농도가 보통입니다. 자동 모드로 전환하여 에너지를 절약하세요.",
        "device_id": "purifier_001",
        "device_name": "침실 공기청정기",
        "action": "set_mode",
        "params": {"mode": "auto"},
        "reason": "현재 PM2.5: 12μg/m³ (보통), 강풍 모드 불필요",
        "priority": 2
    },
    {
        "title": "조명 밝기 조절",
        "description": "저녁 시간입니다. 편안한 조명으로 밝기를 낮추는 것을 추천합니다.",
        "device_id": "light_001",
        "device_name": "거실 조명",
        "action": "set_brightness",
        "params": {"brightness": 50},
        "reason": "오후 8시 이후 권장 밝기: 50-60%",
        "priority": 3
    },
    {
        "title": "외출 모드 활성화",
        "description": "1시간 이상 집을 비우셨습니다. 외출 모드를 활성화하여 에너지를 절약하세요.",
        "device_id": "ac_001",
        "device_name": "거실 에어컨",
        "action": "turn_off",
        "params": {},
        "reason": "1시간 이상 움직임 감지 없음",
        "priority": 5
    }
]


@router.post("", response_model=RecommendationResponse)
async def receive_recommendation(request: RecommendationRequest):
    """
    AI Server로부터 사용자에게 보낼 추천을 받습니다.
    
    API 문서:
    - Request Method: POST
    - URL: /api/recommendations
    - Body:
        {
            "title": "에어컨 킬까요?",
            "contents": "현재 온도가 25도이므로 에어컨을 키시는 것을 추천드립니다."
        }
    - Response (200):
        {
            "message": "추천 문구 유저 피드백",
            "confirm": "YES" or "NO"
        }
    
    Args:
        request: AI Server에서 보낸 추천
    
    Returns:
        사용자 피드백
    """
    try:
        logger.info(f"AI Server로부터 추천 수신: {request.title}")
        logger.info(f"추천 내용: {request.contents}")
        
        # TODO: 프론트엔드에 추천 표시
        # 사용자가 YES 또는 NO를 선택할 때까지 대기
        # WebSocket을 통해 실시간으로 업데이트
        
        # 지금은 예시로 YES 반환
        confirm = "YES"
        
        logger.info(f"사용자 피드백: {confirm}")
        
        return RecommendationResponse(
            message="추천 문구 유저 피드백",
            confirm=confirm
        )
        
    except Exception as e:
        logger.error(f"추천 처리 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"추천 처리 실패: {str(e)}"
        )


@router.get("", response_model=list[Recommendation])
async def get_recommendations(limit: int = 5):
    """AI 기반 디바이스 제어 추천을 가져옵니다.
    
    프로덕션: AI 서버에서 현재 상황에 맞는 추천을 조회합니다.
    
    Args:
        limit: 반환할 최대 추천 수
        
    Returns:
        추천 목록
    """
    try:
        # TODO: JWT 토큰에서 user_id, session_id 추출
        user_id = "user_001"
        session_id = "session_xyz"
        
        # AI 서버에서 추천 조회
        ai_recommendations = await ai_client.get_recommendations(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        if ai_recommendations:
            # AI 서버에서 받은 추천을 변환
            recommendations = []
            for idx, rec in enumerate(ai_recommendations):
                recommendations.append(Recommendation(
                    id=f"rec_{idx}_{int(datetime.now().timestamp())}",
                    title=rec.get("title", "추천"),
                    description=rec.get("reason", ""),
                    device_id=rec.get("device_id", ""),
                    device_name=rec.get("device_name", ""),
                    action=rec.get("action", ""),
                    params=rec.get("params", {}),
                    reason=rec.get("reason", ""),
                    priority=rec.get("priority", 3),
                    timestamp=datetime.now().isoformat()
                ))
            
            logger.info(f"AI 서버에서 {len(recommendations)}개 추천 조회됨")
            return recommendations
        else:
            # AI 서버 실패 시 Mock 데이터 사용
            logger.warning("AI 서버 추천 실패, Mock 데이터 사용")
            return get_mock_recommendations(limit)
            
    except Exception as e:
        logger.error(f"추천 조회 실패: {e}, Mock 데이터 사용")
        return get_mock_recommendations(limit)


def get_mock_recommendations(limit: int) -> list[Recommendation]:
    """Mock 추천 데이터 반환."""
    recommendations = []
    
    # 데모 목적으로 무작위로 추천 선택
    selected = random.sample(MOCK_RECOMMENDATIONS, min(limit, len(MOCK_RECOMMENDATIONS)))
    
    for idx, rec in enumerate(selected):
        recommendations.append(Recommendation(
            id=f"rec_{idx}_{int(datetime.now().timestamp())}",
            title=rec["title"],
            description=rec["description"],
            device_id=rec["device_id"],
            device_name=rec["device_name"],
            action=rec["action"],
            params=rec["params"],
            reason=rec["reason"],
            priority=rec["priority"],
            timestamp=datetime.now().isoformat()
        ))
    
    # 우선순위로 정렬 (높은 순서 먼저)
    recommendations.sort(key=lambda x: x.priority, reverse=True)
    
    return recommendations


@router.get("/device/{device_id}", response_model=list[Recommendation])
async def get_device_recommendations(device_id: str):
    """특정 디바이스에 대한 추천을 가져옵니다.
    
    Args:
        device_id: 디바이스 ID
        
    Returns:
        해당 디바이스의 추천 목록
    """
    recommendations = []
    
    for idx, rec in enumerate(MOCK_RECOMMENDATIONS):
        if rec["device_id"] == device_id:
            recommendations.append(Recommendation(
                id=f"rec_{device_id}_{idx}_{int(datetime.now().timestamp())}",
                title=rec["title"],
                description=rec["description"],
                device_id=rec["device_id"],
                device_name=rec["device_name"],
                action=rec["action"],
                params=rec["params"],
                reason=rec["reason"],
                priority=rec["priority"],
                timestamp=datetime.now().isoformat()
            ))
    
    return recommendations


class RecommendationFeedback(BaseModel):
    """추천에 대한 사용자 피드백."""
    recommendation_id: str
    accepted: bool
    rating: int | None = Field(None, ge=1, le=5, description="선택사항 평가 1-5")
    comment: str | None = None


@router.post("/feedback")
async def submit_feedback(feedback: RecommendationFeedback):
    """추천에 대한 피드백을 제출합니다.
    
    이는 시간이 지남에 따라 AI가 사용자 선호도를 학습하는 데 도움이 됩니다.
    
    Args:
        feedback: 피드백 정보
        
    Returns:
        피드백 수신 결과
    """
    try:
        # AI 서버로 피드백 전송
        ai_response = await ai_client.send_feedback({
            "recommendation_id": feedback.recommendation_id,
            "accepted": feedback.accepted,
            "rating": feedback.rating,
            "comment": feedback.comment,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"피드백 AI 서버로 전송됨: {feedback.recommendation_id}")
        
        return {
            "success": True,
            "message": "피드백을 수신했습니다",
            "recommendation_id": feedback.recommendation_id,
            "accepted": feedback.accepted
        }
        
    except Exception as e:
        logger.error(f"피드백 전송 실패: {e}")
        return {
            "success": False,
            "message": f"피드백 처리 중 오류 발생: {str(e)}",
            "recommendation_id": feedback.recommendation_id
        }


class SensorData(BaseModel):
    """상황 인식 추천을 위한 현재 센서 데이터."""
    temperature: float | None = None
    humidity: float | None = None
    pm25: float | None = None
    pm10: float | None = None
    co2: float | None = None
    light_level: float | None = None
    noise_level: float | None = None
    motion_detected: bool = False


@router.post("/context")
async def update_context(sensor_data: SensorData):
    """환경 컨텍스트를 업데이트하여 더 나은 추천을 제공합니다.
    
    이 엔드포인트는 상황 인식 추천을 제공하기 위한 센서 데이터를 수신합니다.
    
    Args:
        sensor_data: 센서 데이터
        
    Returns:
        컨텍스트 업데이트 결과
    """
    # In production, store sensor data and use for real-time recommendation generation
    print(f"[Recommendations] Context updated: {sensor_data}")
    
    return {
        "success": True,
        "message": "Context updated",
        "timestamp": datetime.now().isoformat()
    }
