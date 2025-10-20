"""AI 기반 디바이스 제어 추천을 위한 REST API 엔드포인트."""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter()


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


# Mock 추천 데이터
# 프로덕션 환경에서는 ML 모델 또는 규칙 기반 AI를 사용합니다
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


@router.get("", response_model=list[Recommendation])
async def get_recommendations(limit: int = 5):
    """AI 기반 디바이스 제어 추천을 가져옵니다.
    
    Args:
        limit: 반환할 최대 추천 수
        
    Returns:
        추천 목록
    """
    # 프로덕션 환경에서는:
    # 1. 센서 데이터 수집 (온도, 습도, PM2.5 등)
    # 2. 현재 디바이스 상태 확인
    # 3. 사용자 선호도 및 히스토리 확인
    # 4. ML 모델 또는 규칙 기반 시스템 실행
    # 5. 개인화된 추천 생성
    
    # 현재는 mock 데이터 반환
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
    # 프로덕션 환경에서는 피드백을 데이터베이스에 저장하고 모델 훈련에 사용합니다
    print(f"[Recommendations] 피드백 수신됨: {feedback}")
    
    return {
        "success": True,
        "message": "피드백을 수신했습니다",
        "recommendation_id": feedback.recommendation_id,
        "accepted": feedback.accepted
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
