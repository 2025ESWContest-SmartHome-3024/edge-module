"""사용자 및 캘리브레이션 관리를 위한 SQLite 데이터베이스."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from backend.core.config import settings


class Database:
    """사용자 관리를 위한 간단한 SQLite 데이터베이스."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """데이터베이스 초기화.
        
        Args:
            db_path: 데이터베이스 파일 경로 (기본값: ~/.eyetrax/calibrations/eyetrax.db)
        """
        if db_path is None:
            db_path = settings.calibration_dir / "eyetrax.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 데이터베이스 초기화
        self._init_db()
    
    def _init_db(self):
        """테이블이 없으면 생성합니다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 사용자 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # 캘리브레이션 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    calibration_file TEXT NOT NULL,
                    screen_width INTEGER,
                    screen_height INTEGER,
                    method TEXT,
                    samples_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 로그인 기록 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            conn.commit()
            print(f"[Database] 초기화됨: {self.db_path}")
    
    def get_or_create_user(self, username: str) -> int:
        """사용자 ID를 가져오거나 없으면 생성합니다.
        
        Args:
            username: 사용자명
            
        Returns:
            사용자 ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 기존 사용자 조회
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                user_id = result[0]
                # 마지막 로그인 시간 업데이트
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now(), user_id)
                )
            else:
                # 새로운 사용자 생성
                cursor.execute(
                    "INSERT INTO users (username, last_login) VALUES (?, ?)",
                    (username, datetime.now())
                )
                user_id = cursor.lastrowid
                print(f"[Database] 새로운 사용자 생성: {username} (ID: {user_id})")
            
            conn.commit()
            return user_id
    
    def record_login(self, username: str):
        """로그인 이벤트를 기록합니다.
        
        Args:
            username: 사용자명
        """
        user_id = self.get_or_create_user(username)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO login_history (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
    
    def add_calibration(
        self,
        username: str,
        calibration_file: str,
        screen_width: int,
        screen_height: int,
        method: str = "nine_point",
        samples_count: int = 0
    ):
        """새로운 캘리브레이션을 기록합니다.
        
        Args:
            username: 사용자명
            calibration_file: 캘리브레이션 파일 경로
            screen_width: 화면 너비
            screen_height: 화면 높이
            method: 캘리브레이션 방식 (기본값: nine_point)
            samples_count: 샘플 수 (기본값: 0)
        """
        user_id = self.get_or_create_user(username)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO calibrations 
                (user_id, calibration_file, screen_width, screen_height, method, samples_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, calibration_file, screen_width, screen_height, method, samples_count)
            )
            conn.commit()
            print(f"[Database] {username}의 캘리브레이션 기록됨: {calibration_file}")
    
    def get_user_calibrations(self, username: str) -> List[Dict]:
        """사용자의 모든 캘리브레이션을 가져옵니다.
        
        Args:
            username: 사용자명
            
        Returns:
            캘리브레이션 정보 딕셔너리 목록
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT c.* FROM calibrations c
                JOIN users u ON c.user_id = u.id
                WHERE u.username = ?
                ORDER BY c.created_at DESC
                """,
                (username,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def has_calibration(self, username: str) -> bool:
        """사용자가 캘리브레이션을 가지고 있는지 확인합니다.
        
        Args:
            username: 사용자명
            
        Returns:
            캘리브레이션 유무
        """
        calibrations = self.get_user_calibrations(username)
        return len(calibrations) > 0
    
    def get_latest_calibration(self, username: str) -> Optional[str]:
        """사용자의 최신 캘리브레이션 파일을 가져옵니다.
        
        Args:
            username: 사용자명
            
        Returns:
            최신 캘리브레이션 파일 경로 또는 None
        """
        calibrations = self.get_user_calibrations(username)
        if calibrations:
            return calibrations[0]['calibration_file']
        return None
    
    def get_user_stats(self, username: str) -> Dict:
        """사용자의 통계를 가져옵니다.
        
        Args:
            username: 사용자명
            
        Returns:
            사용자 통계 정보
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 사용자 정보 조회
            cursor.execute(
                """
                SELECT 
                    u.id,
                    u.username,
                    u.created_at,
                    u.last_login,
                    COUNT(DISTINCT c.id) as calibration_count,
                    COUNT(DISTINCT l.id) as login_count
                FROM users u
                LEFT JOIN calibrations c ON u.id = c.user_id
                LEFT JOIN login_history l ON u.id = l.user_id
                WHERE u.username = ?
                GROUP BY u.id
                """,
                (username,)
            )
            
            result = cursor.fetchone()
            if result:
                return {
                    "user_id": result[0],
                    "username": result[1],
                    "created_at": result[2],
                    "last_login": result[3],
                    "calibration_count": result[4],
                    "login_count": result[5]
                }
            return {}
    
    def get_all_users(self) -> List[Dict]:
        """모든 사용자를 가져옵니다.
        
        Returns:
            사용자 정보 딕셔너리 목록 (최근 로그인 순)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT 
                    u.*,
                    COUNT(c.id) as calibration_count
                FROM users u
                LEFT JOIN calibrations c ON u.id = c.user_id
                GROUP BY u.id
                ORDER BY u.last_login DESC
                """
            )
            
            return [dict(row) for row in cursor.fetchall()]


# 전역 데이터베이스 인스턴스
db = Database()
