"""Gaze tracking wrapper for web application."""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from model.gaze import GazeEstimator
from model.filters import NoSmoother


class WebGazeTracker:
    """Async wrapper for gaze estimation suitable for web streaming."""
    
    def __init__(
        self,
        camera_index: int = 0,
        model_name: str = "ridge",
        filter_method: str = "noop",
        screen_size: Tuple[int, int] = (1024, 600)
    ):
        self.camera_index = camera_index
        self.model_name = model_name
        self.filter_method = filter_method
        self.screen_size = screen_size
        
        self.gaze_estimator = GazeEstimator(model_name=model_name)
        self.cap: Optional[cv2.VideoCapture] = None
        self.smoother = None
        self.is_running = False
        self.current_gaze: Optional[Tuple[int, int]] = None
        self.raw_gaze: Optional[Tuple[int, int]] = None
        self.current_blink = False
        self.calibrated = False
        self._lock = asyncio.Lock()
        
        # 👁️ 눈깜빡임 추적 (1초 이상 = 클릭 인식)
        self.blink_start_time: Optional[float] = None
        self.blink_duration: float = 0.0
        self.prolonged_blink_triggered: bool = False
        self.PROLONGED_BLINK_DURATION = 1.0  # 👁️ 1초 이상 눈깜빡임 = 클릭
        
    async def initialize(self):
        """Initialize camera and smoother.
        
        ⭐ 간소화된 설정:
        - 모델: Ridge 회귀 (가볍고 빠름)
        - 필터: NoOp (필터링 비활성화)
        - 화면: 1024x600 (라즈베리파이 최적화)
        """
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")
        
        # ⭐ 간소화: NoOp 필터만 사용 (필터링 비활성화)
        self.smoother = NoSmoother()
        print(f"[GazeTracker] Initialized with NoOp filter (no smoothing)")

            
    def load_calibration(self, model_path: str):
        """Load pre-trained calibration model."""
        self.gaze_estimator.load_model(model_path)
        self.calibrated = True
        
    def save_calibration(self, model_path: str):
        """Save current calibration model."""
        self.gaze_estimator.save_model(model_path)
    
    # ⭐ Kalman 필터 튜닝 제거됨 (NoOp 필터 사용)
    # tune_kalman_filter(), get_kalman_params(), set_kalman_measurement_noise() 
    # 메서드들은 필터링이 비활성화되어 있으므로 필요 없음
    
    async def start_tracking(self):
        """Start continuous gaze tracking."""
        self.is_running = True
        while self.is_running:
            await self._process_frame()
            await asyncio.sleep(0.016)  # ~60 FPS
            
    async def _process_frame(self):
        """Process single frame for gaze estimation."""
        if self.cap is None:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            return
            
        # Extract features and detect blink
        features, blink_detected = self.gaze_estimator.extract_features(frame)
        
        async with self._lock:
            # 👁️ 눈깜빡임 추적 로직
            if blink_detected:
                # 눈깜빡임 시작
                if self.blink_start_time is None:
                    self.blink_start_time = time.time()
                    self.prolonged_blink_triggered = False
                    print("[GazeTracker] Blink detected - starting timer")
                
                # 눈깜빡임 지속 시간 계산
                self.blink_duration = time.time() - self.blink_start_time
                
                # 0.5초 이상 눈깜빡임 감지
                if self.blink_duration >= self.PROLONGED_BLINK_DURATION and not self.prolonged_blink_triggered:
                    self.prolonged_blink_triggered = True
                    print(f"[GazeTracker] PROLONGED BLINK DETECTED: {self.blink_duration:.2f}s - Click triggered!")
            else:
                # 눈깜빡임 종료
                if self.blink_start_time is not None:
                    self.blink_duration = time.time() - self.blink_start_time
                    print(f"[GazeTracker] Blink ended: duration {self.blink_duration:.2f}s (threshold: {self.PROLONGED_BLINK_DURATION}s)")
                
                self.blink_start_time = None
                self.prolonged_blink_triggered = False
            
            self.current_blink = blink_detected
            
            if features is not None and not blink_detected and self.calibrated:
                # Predict gaze point
                gaze_point = self.gaze_estimator.predict(np.array([features]))[0]
                x, y = map(int, gaze_point)
                self.raw_gaze = (x, y)
                
                # Apply smoothing
                x_pred, y_pred = self.smoother.step(x, y)
                self.current_gaze = (x_pred, y_pred)
            elif self.current_gaze is None:
                # Initialize with screen center if no gaze yet
                self.current_gaze = (self.screen_size[0] // 2, self.screen_size[1] // 2)
                self.raw_gaze = self.current_gaze
                
    def get_current_state(self) -> dict:
        """Get current gaze state (thread-safe, non-blocking).
        
        Returns:
            dict: {
                gaze: (x, y),
                raw_gaze: (x, y),
                blink: bool,
                blink_duration: float (초),
                prolonged_blink: bool (0.5초 이상),
                calibrated: bool,
                timestamp: float
            }
        """
        return {
            "gaze": self.current_gaze,
            "raw_gaze": self.raw_gaze,
            "blink": self.current_blink,
            "blink_duration": self.blink_duration,
            "prolonged_blink": self.prolonged_blink_triggered,  # 👁️ 0.5초 이상 눈깜빡임 = 클릭
            "calibrated": self.calibrated,
            "timestamp": time.time()
        }
            
    async def stop_tracking(self):
        """Stop gaze tracking and release resources."""
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            
    def __del__(self):
        """Cleanup on deletion."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
