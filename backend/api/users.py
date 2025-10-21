"""사용자 관리 API 엔드포인트."""
from __future__ import annotations

from typing import List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import db


router = APIRouter()


class LoginRequest(BaseModel):
    """사용자 로그인 요청."""
    username: str


class LoginResponse(BaseModel):
    """사용자 로그인 응답."""
    success: bool
    username: str
    has_calibration: bool
    calibration_file: str | None = None
    message: str


class UserStatsResponse(BaseModel):
    """사용자 통계 응답."""
    username: str
    created_at: str | None
    last_login: str | None
    calibration_count: int
    login_count: int


@router.post("/login", response_model=LoginResponse)
async def login_user(request: LoginRequest):
    """사용자 로그인 및 캘리브레이션 데이터 확인.
    
    Args:
        request: 로그인 요청 정보
        
    Returns:
        로그인 응답 정보 (사용자명, 캘리브레이션 여부 등)
    """
    username = request.username.strip()
    
    if not username:
        raise HTTPException(status_code=400, detail="사용자명은 비워둘 수 없습니다")
    
    # 1️⃣ 로그인 기록 (로컬 SQLite)
    db.record_login(username)
    
    # 2️⃣ 사용자가 캘리브레이션을 가지고 있는지 확인
    has_calibration = db.has_calibration(username)
    calibration_file = db.get_latest_calibration(username) if has_calibration else None
    
    # 3️⃣ 캘리브레이션이 있으면 백엔드에서 로드
    if has_calibration and calibration_file:
        try:
            from backend.api.main import gaze_tracker
            from backend.core.config import settings
            from pathlib import Path
            
            if gaze_tracker is not None:
                # 전체 경로 구성
                full_path = str(settings.calibration_dir / calibration_file)
                
                # 파일 존재 확인
                if Path(full_path).exists():
                    gaze_tracker.load_calibration(full_path)
                    print(f"[User API] {username}의 캘리브레이션 로드됨: {full_path}")
                else:
                    print(f"[User API] 캘리브레이션 파일을 찾을 수 없음: {full_path}")
        except Exception as e:
            print(f"[User API] {username}의 캘리브레이션 로드 실패: {e}")
            import traceback
            traceback.print_exc()
    
    # 4️⃣ AI Server에 사용자 정보 전송 (비동기, 오류 무시)
    try:
        from backend.services.ai_client import ai_client
        import asyncio
        
        # user_id 가져오기
        user_id = db.get_or_create_user(username)
        
        # 비동기 백그라운드 작업으로 실행 (로그인 응답을 지연시키지 않음)
        asyncio.create_task(
            ai_client.register_user_async(
                user_id=str(user_id),  # ← AI Server에 user_id 전달
                username=username,
                has_calibration=has_calibration
            )
        )
        print(f"[User API] AI Server 등록 요청 발송됨 (user_id={user_id})")
    except Exception as e:
        print(f"[User API] AI Server 사용자 등록 실패 (로컬만 사용): {e}")
    
    print(f"[User API] 로그인: {username}, 캘리브레이션 여부: {has_calibration}")
    
    return LoginResponse(
        success=True,
        username=username,
        has_calibration=has_calibration,
        calibration_file=calibration_file,
        message=f"환영합니다, {username}님!"
    )


@router.get("/stats/{username}", response_model=UserStatsResponse)
async def get_user_stats(username: str):
    """특정 사용자의 통계를 가져옵니다.
    
    Args:
        username: 사용자명
        
    Returns:
        사용자 통계 정보
    """
    stats = db.get_user_stats(username)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
    
    return UserStatsResponse(
        username=stats['username'],
        created_at=stats.get('created_at'),
        last_login=stats.get('last_login'),
        calibration_count=stats.get('calibration_count', 0),
        login_count=stats.get('login_count', 0)
    )


@router.get("/list")
async def list_users():
    """모든 사용자를 나열합니다.
    
    Returns:
        사용자 목록 및 총 개수
    """
    users = db.get_all_users()
    return {
        "users": users,
        "total": len(users)
    }


@router.get("/calibrations/{username}")
async def get_user_calibrations(username: str):
    """사용자의 모든 캘리브레이션을 가져옵니다.
    
    Args:
        username: 사용자명
        
    Returns:
        사용자의 캘리브레이션 목록 및 총 개수
    """
    calibrations = db.get_user_calibrations(username)
    return {
        "username": username,
        "calibrations": calibrations,
        "total": len(calibrations)
    }
