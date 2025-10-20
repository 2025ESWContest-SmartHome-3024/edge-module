"""백엔드 서버 설정."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정."""
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # 시선 추적 설정
    camera_index: int = 0
    model_name: str = "ridge"
    filter_method: str = "kalman"
    screen_width: int = 1920
    screen_height: int = 1080
    
    # 캘리브레이션 설정
    calibration_dir: Path = Path.home() / ".gazehome" / "calibrations"
    
    # CORS 설정 (프로덕션 환경에서는 조정 필요)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://raspberrypi.local:3000",
    ]
    
    # 스마트 홈 통합 설정
    home_assistant_url: str = ""
    home_assistant_token: str = ""
    mqtt_broker: str = ""
    mqtt_port: int = 1883
    
    @property
    def screen_size(self) -> Tuple[int, int]:
        """화면 크기를 튜플로 반환합니다."""
        return (self.screen_width, self.screen_height)
    
    class Config:
        """Pydantic 설정."""
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
