"""Gaze tracking wrapper for web application."""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from eyetrax.gaze import GazeEstimator
from eyetrax.filters import KalmanSmoother, KDESmoother, NoSmoother, make_kalman


class WebGazeTracker:
    """Async wrapper for gaze estimation suitable for web streaming."""
    
    def __init__(
        self,
        camera_index: int = 0,
        model_name: str = "ridge",
        filter_method: str = "kalman",
        screen_size: Tuple[int, int] = (1920, 1080)
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
        
    async def initialize(self):
        """Initialize camera and smoother."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")
        
        # Initialize smoother
        sw, sh = self.screen_size
        if self.filter_method == "kalman":
            kalman = make_kalman()
            self.smoother = KalmanSmoother(kalman)
            print(f"[GazeTracker] Initialized Kalman filter")
        elif self.filter_method == "kde":
            self.smoother = KDESmoother(sw, sh, confidence=0.95)
            print(f"[GazeTracker] Initialized KDE filter")
        else:
            self.smoother = NoSmoother()
            print(f"[GazeTracker] No smoothing filter")
            
    def load_calibration(self, model_path: str):
        """Load pre-trained calibration model."""
        self.gaze_estimator.load_model(model_path)
        self.calibrated = True
        
    def save_calibration(self, model_path: str):
        """Save current calibration model."""
        self.gaze_estimator.save_model(model_path)
    
    def tune_kalman_filter(self) -> bool:
        """
        Tune Kalman filter using calibrated model.
        
        Returns:
            True if tuning succeeded, False otherwise
        """
        if not self.calibrated:
            print("[GazeTracker] Cannot tune Kalman: model not calibrated")
            return False
        
        if not isinstance(self.smoother, KalmanSmoother):
            print("[GazeTracker] Cannot tune: not using Kalman filter")
            return False
        
        print("[GazeTracker] Starting Kalman filter tuning...")
        try:
            # Use the tune method from KalmanSmoother
            # This will temporarily show points on screen and collect variance data
            self.smoother.tune(
                self.gaze_estimator,
                capture=self.cap,
                camera_index=self.camera_index
            )
            print("[GazeTracker] Kalman filter tuning completed")
            return True
        except Exception as e:
            print(f"[GazeTracker] Kalman tuning failed: {e}")
            return False
    
    def get_kalman_params(self) -> dict:
        """Get current Kalman filter parameters."""
        if not isinstance(self.smoother, KalmanSmoother):
            return {"error": "Not using Kalman filter"}
        
        kf = self.smoother.kf
        return {
            "measurement_noise_cov": kf.measurementNoiseCov.tolist(),
            "process_noise_cov": kf.processNoiseCov.tolist(),
            "error_cov_post": kf.errorCovPost.tolist()
        }
    
    def set_kalman_measurement_noise(self, variance: float):
        """
        Adjust Kalman filter measurement noise covariance.
        
        Args:
            variance: Measurement noise variance (higher = more smoothing, more lag)
        """
        if not isinstance(self.smoother, KalmanSmoother):
            print("[GazeTracker] Not using Kalman filter")
            return
        
        self.smoother.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * variance
        print(f"[GazeTracker] Set Kalman measurement noise to {variance}")
        
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
        """Get current gaze state (thread-safe, non-blocking)."""
        return {
            "gaze": self.current_gaze,
            "raw_gaze": self.raw_gaze,
            "blink": self.current_blink,
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
