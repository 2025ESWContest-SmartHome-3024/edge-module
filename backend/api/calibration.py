"""웹 기반 캘리브레이션 REST API 엔드포인트."""
from __future__ import annotations

import asyncio
import time
from typing import List, Tuple, Optional
from enum import Enum

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.database import db


router = APIRouter()


class CalibrationMethod(str, Enum):
    """캘리브레이션 방식."""
    FIVE_POINT = "five_point"
    NINE_POINT = "nine_point"


class CalibrationStatus(str, Enum):
    """캘리브레이션 상태."""
    IDLE = "idle"
    WAITING_FOR_FACE = "waiting_for_face"
    COUNTDOWN = "countdown"
    PULSING = "pulsing"
    CAPTURING = "capturing"
    TRAINING = "training"
    COMPLETED = "completed"
    ERROR = "error"


class CalibrationPoint(BaseModel):
    """단일 캘리브레이션 포인트 좌표."""
    x: int
    y: int
    index: int
    total: int


class CalibrationStartRequest(BaseModel):
    """캘리브레이션 시작 요청."""
    method: CalibrationMethod = Field(default=CalibrationMethod.FIVE_POINT)
    screen_width: int = Field(default=1920)
    screen_height: int = Field(default=1080)
    margin_ratio: float = Field(default=0.10, ge=0.05, le=0.2)


class CalibrationStartResponse(BaseModel):
    """캘리브레이션 시작 응답."""
    session_id: str
    method: CalibrationMethod
    points: List[CalibrationPoint]
    total_points: int


class CalibrationStateResponse(BaseModel):
    """현재 캘리브레이션 상태."""
    session_id: str
    status: CalibrationStatus
    current_point: Optional[CalibrationPoint] = None
    progress: float = Field(ge=0.0, le=1.0)
    message: str
    face_detected: bool = False
    features_collected: int = 0


class CalibrationCollectRequest(BaseModel):
    """현재 포인트에 대한 캘리브레이션 데이터 수집 요청."""
    session_id: str
    features: List[float]
    point_x: int
    point_y: int


class CalibrationCompleteRequest(BaseModel):
    """캘리브레이션 완료 및 훈련 요청."""
    session_id: str
    save_path: Optional[str] = None
    username: Optional[str] = None  # 사용자 이름 추가


class CalibrationCompleteResponse(BaseModel):
    """캘리브레이션 완료 응답."""
    success: bool
    message: str
    save_path: Optional[str] = None
    accuracy: Optional[float] = None


# 전역 캘리브레이션 세션
calibration_sessions = {}


class CalibrationSession:
    """단일 캘리브레이션 세션을 관리합니다."""
    
    def __init__(
        self,
        session_id: str,
        method: CalibrationMethod,
        screen_width: int,
        screen_height: int,
        margin_ratio: float = 0.10
    ):
        """캘리브레이션 세션 초기화.
        
        Args:
            session_id: 세션 ID
            method: 캘리브레이션 방식
            screen_width: 화면 너비
            screen_height: 화면 높이
            margin_ratio: 여백 비율 (기본값: 0.10)
        """
        self.session_id = session_id
        self.method = method
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.margin_ratio = margin_ratio
        
        self.status = CalibrationStatus.IDLE
        self.current_point_index = 0
        self.features_collected = 0
        self.face_detected = False
        self.message = "캘리브레이션 초기화됨"
        
        # 캘리브레이션 포인트 생성
        self.points = self._generate_points()
        self.collected_features: List[List[float]] = []
        self.collected_targets: List[List[int]] = []
        
    def _generate_points(self) -> List[CalibrationPoint]:
        """방식에 따라 캘리브레이션 포인트를 생성합니다.
        
        Returns:
            캘리브레이션 포인트 목록
        """
        if self.method == CalibrationMethod.FIVE_POINT:
            # 중심 + 4개 모서리
            order = [(1, 1), (0, 0), (2, 0), (0, 2), (2, 2)]
        else:  # NINE_POINT
            # 3x3 그리드
            order = [
                (1, 1),  # 중심
                (0, 0), (0, 1), (0, 2),  # 상단 줄
                (1, 0), (1, 2),  # 중간 측면
                (2, 0), (2, 1), (2, 2),  # 하단 줄
            ]
        
        points = self._compute_grid_points(order)
        return [
            CalibrationPoint(x=x, y=y, index=i, total=len(points))
            for i, (x, y) in enumerate(points)
        ]
    
    def _compute_grid_points(self, order: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """그리드 (행, 열) 인덱스를 절대 픽셀 위치로 변환합니다.
        
        Args:
            order: (행, 열) 튜플 목록
            
        Returns:
            (x, y) 픽셀 좌표 목록
        """
        if not order:
            return []
        
        max_r = max(r for r, _ in order)
        max_c = max(c for _, c in order)
        
        # 더 큰 margin 사용 (특히 하단을 위해)
        mx = int(self.screen_width * self.margin_ratio)
        my_top = int(self.screen_height * self.margin_ratio)
        my_bottom = int(self.screen_height * 0.15)  # 하단 margin을 15%로 증가 (status bar 고려)
        
        gw = self.screen_width - 2 * mx
        gh = self.screen_height - my_top - my_bottom
        
        step_x = 0 if max_c == 0 else gw / max_c
        step_y = 0 if max_r == 0 else gh / max_r
        
        return [
            (mx + int(c * step_x), my_top + int(r * step_y))
            for r, c in order
        ]
    
    def get_current_point(self) -> Optional[CalibrationPoint]:
        """Get current calibration point."""
        if 0 <= self.current_point_index < len(self.points):
            return self.points[self.current_point_index]
        return None
    
    def add_sample(self, features: List[float], target: Tuple[int, int]):
        """Add a calibration sample."""
        self.collected_features.append(features)
        self.collected_targets.append([target[0], target[1]])
        self.features_collected += 1
    
    def next_point(self) -> bool:
        """Move to next calibration point. Returns False if all done."""
        self.current_point_index += 1
        self.features_collected = 0
        return self.current_point_index < len(self.points)
    
    def get_progress(self) -> float:
        """Get calibration progress (0.0 to 1.0)."""
        if not self.points:
            return 0.0
        return self.current_point_index / len(self.points)
    
    def get_state(self) -> dict:
        """Get current state as dict."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_point": self.get_current_point(),
            "progress": self.get_progress(),
            "message": self.message,
            "face_detected": self.face_detected,
            "features_collected": self.features_collected
        }


@router.post("/start", response_model=CalibrationStartResponse)
async def start_calibration(request: CalibrationStartRequest):
    """
    Start a new calibration session.
    
    Returns calibration points and session ID.
    """
    # Generate unique session ID
    session_id = f"calib_{int(time.time() * 1000)}"
    
    # Create calibration session
    session = CalibrationSession(
        session_id=session_id,
        method=request.method,
        screen_width=request.screen_width,
        screen_height=request.screen_height,
        margin_ratio=request.margin_ratio
    )
    
    # Store session
    calibration_sessions[session_id] = session
    
    # Clean up old sessions (keep only last 10)
    if len(calibration_sessions) > 10:
        oldest_keys = sorted(calibration_sessions.keys())[:len(calibration_sessions) - 10]
        for key in oldest_keys:
            del calibration_sessions[key]
    
    print(f"[Calibration] Started session {session_id} with {len(session.points)} points")
    
    return CalibrationStartResponse(
        session_id=session_id,
        method=request.method,
        points=session.points,
        total_points=len(session.points)
    )


@router.get("/state/{session_id}", response_model=CalibrationStateResponse)
async def get_calibration_state(session_id: str):
    """
    Get current calibration state.
    """
    if session_id not in calibration_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    session = calibration_sessions[session_id]
    state = session.get_state()
    
    return CalibrationStateResponse(**state)


@router.post("/collect")
async def collect_calibration_data(request: CalibrationCollectRequest):
    """
    Collect calibration data for the current point.
    
    Called when frontend detects face features and wants to submit them.
    """
    if request.session_id not in calibration_sessions:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
    
    session = calibration_sessions[request.session_id]
    
    # 유효한 포인트인지 검증
    current_point = session.get_current_point()
    if current_point is None:
        raise HTTPException(status_code=400, detail="현재 캘리브레이션 포인트가 없습니다")
    
    # 포인트 좌표 일치 확인
    if current_point.x != request.point_x or current_point.y != request.point_y:
        raise HTTPException(
            status_code=400,
            detail=f"포인트 불일치: 예상 ({current_point.x}, {current_point.y}), 받은 ({request.point_x}, {request.point_y})"
        )
    
    # 샘플 추가
    session.add_sample(request.features, (request.point_x, request.point_y))
    session.status = CalibrationStatus.CAPTURING
    session.message = f"포인트 {current_point.index + 1}에서 {session.features_collected}개 샘플 수집됨"
    
    print(f"[Calibration] 세션 {request.session_id}: 포인트 ({request.point_x}, {request.point_y})에 대한 샘플 수집됨")
    
    return {
        "success": True,
        "features_collected": session.features_collected,
        "message": session.message
    }


@router.post("/next-point")
async def next_calibration_point(session_id: str):
    """다음 캘리브레이션 포인트로 이동합니다.
    
    Args:
        session_id: 캘리브레이션 세션 ID
        
    Returns:
        다음 포인트 정보
    """
    if session_id not in calibration_sessions:
        raise HTTPException(status_code=404, detail=f"세션 {session_id}을 찾을 수 없습니다")
    
    session = calibration_sessions[session_id]
    
    has_next = session.next_point()
    
    if has_next:
        current = session.get_current_point()
        session.status = CalibrationStatus.PULSING
        session.message = f"포인트 {current.index + 1}/{len(session.points)}로 이동 중"
        print(f"[Calibration] 세션 {session_id}: 포인트 {current.index + 1}로 이동")
    else:
        session.status = CalibrationStatus.COMPLETED
        session.message = "모든 포인트 수집됨. 훈련 준비 완료."
        print(f"[Calibration] 세션 {session_id}: 모든 포인트 수집됨")
    
    return {
        "success": True,
        "has_next": has_next,
        "current_point": session.get_current_point(),
        "status": session.status.value,
        "message": session.message
    }


@router.post("/complete", response_model=CalibrationCompleteResponse)
async def complete_calibration(request: CalibrationCompleteRequest):
    """캘리브레이션을 완료하고 모델을 훈련합니다.
    
    Args:
        request: 캘리브레이션 완료 요청
        
    Returns:
        캘리브레이션 완료 응답
    """
    if request.session_id not in calibration_sessions:
        raise HTTPException(status_code=404, detail=f"세션 {request.session_id}을 찾을 수 없습니다")
    
    session = calibration_sessions[request.session_id]
    
    # 데이터가 있는지 검증
    if not session.collected_features or not session.collected_targets:
        raise HTTPException(status_code=400, detail="수집된 캘리브레이션 데이터가 없습니다")
    
    if len(session.collected_features) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"불충분한 데이터: 최소 5개 샘플 필요, {len(session.collected_features)}개 획득"
        )
    
    try:
        session.status = CalibrationStatus.TRAINING
        session.message = "모델 훈련 중..."
        
        # 시선 추적기 획득
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
        
        # numpy 배열로 변환
        features_array = np.array(session.collected_features)
        targets_array = np.array(session.collected_targets)
        
        print(f"[Calibration] {len(features_array)}개 샘플로 훈련 중")
        
        # 모델 훈련
        gaze_tracker.gaze_estimator.train(features_array, targets_array)
        gaze_tracker.calibrated = True
        
        # 요청에서 사용자명 받기 또는 기본값 사용
        username = request.username if request.username else "default"
        
        # 경로가 제공되면 저장
        save_path = request.save_path
        if save_path is None:
            # 기본 저장 경로 - 사용자명 사용
            settings.calibration_dir.mkdir(parents=True, exist_ok=True)
            save_path = str(settings.calibration_dir / f"{username}.pkl")
        
        gaze_tracker.save_calibration(save_path)
        
        # 데이터베이스에 캘리브레이션 기록
        db.add_calibration(
            username=username,
            calibration_file=f"{username}.pkl",
            screen_width=session.screen_width,
            screen_height=session.screen_height,
            method=session.method.value,
            samples_count=len(session.collected_features)
        )
        
        session.status = CalibrationStatus.COMPLETED
        session.message = "캘리브레이션 완료됨"
        
        print(f"[Calibration] 세션 {request.session_id}: 훈련 완료, 저장 위치: {save_path}")
        print(f"[Calibration] 사용자 {username}를 위해 데이터베이스에 기록됨")
        
        # 세션 정리
        del calibration_sessions[request.session_id]
        
        return CalibrationCompleteResponse(
            success=True,
            message="캘리브레이션 완료 및 모델 저장됨",
            save_path=save_path,
            accuracy=None  # TODO: 검증 정확도 계산
        )
        
    except Exception as e:
        session.status = CalibrationStatus.ERROR
        session.message = f"훈련 실패: {str(e)}"
        print(f"[Calibration] 세션 {request.session_id}: 훈련 실패 - {e}")
        
        return CalibrationCompleteResponse(
            success=False,
            message=f"캘리브레이션 실패: {str(e)}",
            save_path=None,
            accuracy=None
        )


@router.delete("/cancel/{session_id}")
async def cancel_calibration(session_id: str):
    """캘리브레이션 세션을 취소합니다.
    
    Args:
        session_id: 캘리브레이션 세션 ID
        
    Returns:
        취소 결과
    """
    if session_id not in calibration_sessions:
        raise HTTPException(status_code=404, detail=f"세션 {session_id}을 찾을 수 없습니다")
    
    session = calibration_sessions[session_id]
    session.status = CalibrationStatus.IDLE
    del calibration_sessions[session_id]
    
    return {
        "success": True,
        "message": f"캘리브레이션 세션 {session_id} 취소됨"
    }


@router.post("/tune-kalman")
async def tune_kalman_filter():
    """캘리브레이션 후 Kalman 필터를 미세 조정합니다.
    
    3개의 추가 포인트를 표시하고 분산 데이터를 수집합니다.
    
    Returns:
        튜닝 결과
    """
    from backend.api.main import gaze_tracker
    
    if gaze_tracker is None:
        raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
    
    if not gaze_tracker.calibrated:
        raise HTTPException(status_code=400, detail="먼저 모델을 캘리브레이션해야 합니다")
    
    try:
        print("[Calibration API] Kalman 필터 튜닝 시작...")
        success = gaze_tracker.tune_kalman_filter()
        
        if success:
            return {
                "success": True,
                "message": "Kalman 필터 튜닝 성공"
            }
        else:
            return {
                "success": False,
                "message": "Kalman 튜닝 실패 또는 적용 불가능"
            }
    except Exception as e:
        print(f"[Calibration API] Kalman 튜닝 오류: {e}")
        raise HTTPException(status_code=500, detail=f"튜닝 실패: {str(e)}")


class UpdateKalmanVarianceRequest(BaseModel):
    """Kalman 필터 분산 업데이트 요청."""
    variance_x: float
    variance_y: float


@router.post("/update-kalman-variance")
async def update_kalman_variance(request: UpdateKalmanVarianceRequest):
    """웹 UI 튜닝에서 Kalman 필터 측정 잡음 공분산을 업데이트합니다.
    
    Args:
        request: 분산 업데이트 요청
        
    Returns:
        업데이트 결과
    """
    from backend.api.main import gaze_tracker
    
    if gaze_tracker is None:
        raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
    
    if not gaze_tracker.calibrated:
        raise HTTPException(status_code=400, detail="먼저 모델을 캘리브레이션해야 합니다")
    
    try:
        from model.filters import KalmanSmoother
        
        if not isinstance(gaze_tracker.smoother, KalmanSmoother):
            return {
                "success": False,
                "message": "Kalman 필터를 사용하지 않습니다"
            }
        
        # 측정 잡음 공분산 업데이트
        variance_matrix = np.array([
            [request.variance_x, 0],
            [0, request.variance_y]
        ], dtype=np.float32)
        
        gaze_tracker.smoother.kf.measurementNoiseCov = variance_matrix
        
        print(f"[Calibration API] Kalman 분산 업데이트됨: X={request.variance_x:.2f}, Y={request.variance_y:.2f}")
        
        return {
            "success": True,
            "message": "Kalman 필터 분산 업데이트됨",
            "variance_x": request.variance_x,
            "variance_y": request.variance_y
        }
        
    except Exception as e:
        print(f"[Calibration API] Kalman 분산 업데이트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"업데이트 실패: {str(e)}")


@router.get("/list")
async def list_calibration_files():
    """사용 가능한 캘리브레이션 파일을 나열합니다.
    
    Returns:
        캘리브레이션 파일 목록 및 디렉토리
    """
    calib_dir = settings.calibration_dir
    
    if not calib_dir.exists():
        return {
            "calibrations": [],
            "directory": str(calib_dir)
        }
    
    calibration_files = []
    for file_path in calib_dir.glob("*.pkl"):
        calibration_files.append({
            "name": file_path.name,
            "path": str(file_path),
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        })
    
    # 수정된 시간으로 정렬 (최신순)
    calibration_files.sort(key=lambda x: x["modified"], reverse=True)
    
    return {
        "calibrations": calibration_files,
        "directory": str(calib_dir)
    }
