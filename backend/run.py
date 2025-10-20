#!/usr/bin/env python3
"""EyeTrax 백엔드 서버를 실행합니다."""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from backend.core.config import settings

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════╗
║   EyeTrax 스마트 홈 백엔드 서버         ║
╚══════════════════════════════════════════╝

서버: http://{settings.host}:{settings.port}
API 문서: http://{settings.host}:{settings.port}/docs
WebSocket: ws://{settings.host}:{settings.port}/ws/gaze

중지하려면 Ctrl+C를 누르세요
""")
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info"
    )
