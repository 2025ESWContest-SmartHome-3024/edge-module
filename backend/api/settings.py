"""시선 추적 필터 설정 및 Kalman 튜닝을 위한 API 엔드포인트."""
from __future__ import annotations

from typing import Optional, Annotated

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field


router = APIRouter()


class FilterSettings(BaseModel):
    """시선 필터 설정."""
    filter_method: str = Field(description="필터 방식: 'kalman', 'kde', 또는 'none'")
    kalman_measurement_noise: Optional[float] = Field(
        default=None,
        description="Kalman 측정 잡음 분산 (0.1-10.0, 높을수록 더 매끄럽지만 지연 증가)"
    )


class FilterStatusResponse(BaseModel):
    """현재 필터 상태."""
    filter_method: str
    active: bool
    kalman_params: Optional[dict] = None
    message: str


@router.get("/filter", response_model=FilterStatusResponse)
async def get_filter_status():
    """현재 필터 설정 및 상태를 가져옵니다.
    
    Returns:
        필터 상태 정보
    """
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
        
        filter_method = gaze_tracker.filter_method
        kalman_params = None
        
        if filter_method == "kalman":
            kalman_params = gaze_tracker.get_kalman_params()
        
        return FilterStatusResponse(
            filter_method=filter_method,
            active=gaze_tracker.smoother is not None,
            kalman_params=kalman_params,
            message=f"{filter_method} 필터 사용 중"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/filter/tune-kalman")
async def tune_kalman_filter():
    """현재 캘리브레이션을 사용하여 Kalman 필터를 튜닝합니다.
    
    화면에 3개의 포인트를 표시하고 분산 데이터를 수집합니다.
    캘리브레이션된 모델이 필요합니다.
    
    Returns:
        튜닝 결과
    """
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
        
        if not gaze_tracker.calibrated:
            raise HTTPException(status_code=400, detail="튜닝 전에 모델을 캘리브레이션해야 합니다")
        
        if gaze_tracker.filter_method != "kalman":
            raise HTTPException(status_code=400, detail="Kalman 필터를 사용하지 않습니다")
        
        success = gaze_tracker.tune_kalman_filter()
        
        if success:
            params = gaze_tracker.get_kalman_params()
            return {
                "success": True,
                "message": "Kalman 필터 튜닝 성공",
                "params": params
            }
        else:
            return {
                "success": False,
                "message": "Kalman 튜닝 실패"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"튜닝 실패: {str(e)}")


@router.post("/filter/set-kalman-noise")
async def set_kalman_noise(variance: Annotated[float, Body(ge=0.01, le=100.0)]):
    """Kalman 필터 측정 잡음 분산을 수동으로 설정합니다.
    
    Args:
        variance: 측정 잡음 분산
            - 낮음 (0.1-1.0): 적게 매끄럽고, 반응성 높음, 더 많은 지터
            - 중간 (1.0-5.0): 균형잡힌 매끄러움
            - 높음 (5.0-100.0): 많은 매끄러움, 더 부드러운 커서, 더 많은 지연
    
    Returns:
        설정 결과
    """
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
        
        if gaze_tracker.filter_method != "kalman":
            raise HTTPException(status_code=400, detail="Kalman 필터를 사용하지 않습니다")
        
        gaze_tracker.set_kalman_measurement_noise(variance)
        params = gaze_tracker.get_kalman_params()
        
        return {
            "success": True,
            "message": f"Kalman 측정 잡음을 {variance}로 설정했습니다",
            "params": params
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracker-info")
async def get_tracker_info():
    """포괄적인 추적기 정보를 가져옵니다.
    
    Returns:
        추적기 정보
    """
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
        
        state = gaze_tracker.get_current_state()
        
        return {
            "camera_index": gaze_tracker.camera_index,
            "model_name": gaze_tracker.model_name,
            "filter_method": gaze_tracker.filter_method,
            "screen_size": gaze_tracker.screen_size,
            "calibrated": state["calibrated"],
            "is_running": gaze_tracker.is_running,
            "current_gaze": state["gaze"],
            "raw_gaze": state["raw_gaze"],
            "blink": state["blink"],
            "timestamp": state["timestamp"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

