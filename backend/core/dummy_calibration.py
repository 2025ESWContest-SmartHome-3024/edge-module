"""더미 보정 파일(pickle) 생성 - 보정 과정 건너뛰기용."""
from __future__ import annotations

import pickle
import logging
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class DummyCalibrationModel:
    """더미 보정 모델 - Ridge 회귀 모델 형식."""
    
    def __init__(self):
        """더미 보정 모델 초기화.
        
        Ridge 회귀 모델의 필수 속성:
        - coef_: 회귀 계수 (shape: [2, feature_dim])
        - intercept_: 절편 (shape: [2])
        - feature_dim: 특징 차원 수
        """
        # GazeEstimator의 특징 크기 (face landmarks + eye region features)
        # 기본값: 예측 가능한 크기 (학습되지 않은 더미 값)
        self.feature_dim = 12  # 시선 추정에 필요한 특징 차원
        
        # Ridge 회귀 계수 (2D 시선 좌표)
        self.coef_ = np.random.randn(2, self.feature_dim) * 0.01
        
        # 절편 (화면 중앙 근처의 기본값)
        self.intercept_ = np.array([400.0, 240.0])  # 화면 중앙 (800x480 기준)
        
        # 모델 메타데이터
        self.model_type = "ridge"
        self.created_timestamp = None
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """더미 예측.
        
        args: X (특징 배열)
        return: 시선 좌표 예측값
        """
        # 간단한 선형 회귀: y = X @ coef_.T + intercept_
        return X @ self.coef_.T + self.intercept_


def create_dummy_calibration(save_path: Optional[Path] = None) -> Path:
    """더미 보정 파일 생성.
    
    args: save_path (선택사항, 기본값: ~/.gazehome/calibrations/default.pkl)
    return: 저장된 파일 경로
    """
    from backend.core.config import settings
    
    if save_path is None:
        save_path = settings.calibration_dir / "default.pkl"
    
    # 디렉토리 생성
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 더미 모델 생성
    dummy_model = DummyCalibrationModel()
    
    # pickle 파일로 저장
    with open(save_path, 'wb') as f:
        pickle.dump(dummy_model, f)
    
    logger.info(f"[DummyCalibration] ✅ 더미 보정 파일 생성: {save_path}")
    logger.info(f"[DummyCalibration]    - 특징 차원: {dummy_model.feature_dim}")
    logger.info(f"[DummyCalibration]    - 기본 시선 좌표: {dummy_model.intercept_}")
    
    return save_path
