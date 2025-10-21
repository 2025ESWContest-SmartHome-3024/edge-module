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
    port: int = 8080
    reload: bool = False
    
    # 시선 추적 설정
    camera_index: int = 0
    model_name: str = "ridge"  # 라즈베리파이 최적화: Ridge (가볍고 빠름)
    filter_method: str = "noop"  # 라즈베리파이 최적화: NoOp (필터링 비활성화)
    screen_width: int = 1024
    screen_height: int = 600
    
    # 캘리브레이션 설정(사용자 보정 데이터가 어디에 저장될지를 결정)
    calibration_dir: Path = Path.home() / ".gazehome" / "calibrations"
    
    # CORS 설정 (프로덕션 환경에서는 조정 필요)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://raspberrypi.local:3000",
        "http://raspberrypi.local:5173",
    ]
    
    # AI 서버 설정
    ai_server_url: str = os.getenv("AI_SERVER_URL", "http://34.227.8.172:8000")
    ai_request_timeout: int = int(os.getenv("AI_REQUEST_TIMEOUT", "10")) # 응답 대기 시간 (초과하면 재시도)
    ai_max_retries: int = int(os.getenv("AI_MAX_RETRIES", "3")) # 최대 재시도 횟수

    
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
