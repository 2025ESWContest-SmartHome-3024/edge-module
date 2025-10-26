"""사용자 관리 API 엔드포인트."""
from __future__ import annotations

import logging
from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    """사용자 로그인 요청."""
    pass  # 데모 모드: 추가 데이터 없음


class LoginResponse(BaseModel):
    """사용자 로그인 응답."""
    success: bool
    username: str
    has_calibration: bool
    calibration_file: str | None = None
    message: str


@router.post("/login", response_model=LoginResponse)
async def login_user(request: LoginRequest = None):
    """기능: 데모 사용자 로그인.
    
    args: 없음
    return: success, username, has_calibration, calibration_file, message
    """
    try:
        username = db.DEFAULT_USERNAME
        
        has_calibration = db.has_calibration()
        calibration_file = db.get_latest_calibration() if has_calibration else None
        
        if has_calibration and calibration_file:
            try:
                from backend.api.main import gaze_tracker
                from pathlib import Path
                
                if gaze_tracker is not None:
                    if Path(calibration_file).exists():
                        gaze_tracker.load_calibration(calibration_file)
                        logger.info(f"Calibration loaded: {calibration_file}")
            except Exception as e:
                logger.error(f"Failed to load calibration: {e}")
        
        try:
            from backend.services.ai_client import ai_client
            import asyncio
            from backend.core.config import settings
            
            user_id = db.get_demo_user_id()
            
            if settings.ai_server_url and settings.ai_server_url != "":
                try:
                    asyncio.create_task(
                        ai_client.register_user_async(
                            user_id=str(user_id),
                            username=username,
                            has_calibration=has_calibration
                        )
                    )
                    logger.info(f"User registration request sent (user_id={user_id})")
                except RuntimeError as e:
                    logger.error(f"Background task creation failed: {e}")
            else:
                logger.info("AI Server URL not set - local mode")
                
        except Exception as e:
            logger.error(f"User registration preparation failed: {e}")
        
        logger.info(f"Login: {username}, has_calibration: {has_calibration}")
        
        return LoginResponse(
            success=True,
            username=username,
            has_calibration=has_calibration,
            calibration_file=calibration_file,
            message=f"Welcome, {username}!"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            username = db.DEFAULT_USERNAME
            return LoginResponse(
                success=True,
                username=username,
                has_calibration=False,
                calibration_file=None,
                message=f"Welcome, {username}!"
            )
        except Exception as fallback_error:
            logger.error(f"Fallback login also failed: {fallback_error}")
            raise