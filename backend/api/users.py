"""사용자 관리 API 엔드포인트 (데모용 간소화)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.database import db


router = APIRouter()


class LoginResponse(BaseModel):
    """사용자 로그인 응답."""
    success: bool
    username: str
    has_calibration: bool
    calibration_file: str | None = None
    message: str


@router.post("/login", response_model=LoginResponse)
async def login_user():
    """데모 사용자 로그인.
    
    Returns:
        로그인 응답 정보
    """
    try:
        # 데모는 항상 같은 사용자
        username = db.DEFAULT_USERNAME
        
        # ✅ 캘리브레이션 확인
        has_calibration = db.has_calibration()
        calibration_file = db.get_latest_calibration() if has_calibration else None
        
        # ✅ 캘리브레이션이 있으면 백엔드에서 로드
        if has_calibration and calibration_file:
            try:
                from backend.api.main import gaze_tracker
                from pathlib import Path
                
                if gaze_tracker is not None:
                    if Path(calibration_file).exists():
                        gaze_tracker.load_calibration(calibration_file)
                        print(f"[User API] 캘리브레이션 로드됨: {calibration_file}")
            except Exception as e:
                print(f"[User API] 캘리브레이션 로드 실패: {e}")
        
        # ✅ AI Server에 사용자 정보 전송 (백그라운드, 오류 무시)
        try:
            from backend.services.ai_client import ai_client
            import asyncio
            from backend.core.config import settings
            
            user_id = db.get_demo_user_id()
            
            # AI Server URL 체크 (유효한 URL인지 확인)
            if settings.ai_server_url and settings.ai_server_url != "":
                try:
                    # 백그라운드 작업으로 AI Server 등록 (로그인 응답 지연 없음)
                    asyncio.create_task(
                        ai_client.register_user_async(
                            user_id=str(user_id),
                            username=username,
                            has_calibration=has_calibration
                        )
                    )
                    print(f"[User API] AI Server 등록 요청 발송됨 (user_id={user_id})")
                except RuntimeError as e:
                    # Event loop 없음 (FastAPI 외부에서 호출 시)
                    print(f"[User API] 백그라운드 작업 생성 불가 (FastAPI 컨텍스트 필요): {e}")
            else:
                print("[User API] AI Server URL 미설정 - 로컬 모드")
                
        except Exception as e:
            print(f"[User API] AI Server 등록 준비 실패 (로컬만 사용): {e}")
        
        print(f"[User API] 로그인: {username}, 캘리브레이션: {has_calibration}")
        
        return LoginResponse(
            success=True,
            username=username,
            has_calibration=has_calibration,
            calibration_file=calibration_file,
            message=f"환영합니다, {username}님!"
        )
        
    except Exception as e:
        print(f"[User API] 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        
        # 오류 발생 시에도 로컬 로그인은 성공하도록
        try:
            username = db.DEFAULT_USERNAME
            return LoginResponse(
                success=True,
                username=username,
                has_calibration=False,
                calibration_file=None,
                message=f"환영합니다, {username}님!"
            )
        except Exception as fallback_error:
            print(f"[User API] 폴백 로그인도 실패: {fallback_error}")
            raise