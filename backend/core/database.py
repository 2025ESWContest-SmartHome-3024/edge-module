"""데모용 간소화된 SQLite 데이터베이스."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
import json

from backend.core.config import settings


class Database:
    """데모용 간단한 SQLite 데이터베이스 (1명 사용자 가정)."""
    
    # 🎯 고정된 데모 사용자
    DEFAULT_USERNAME = "demo_user"
    
    def __init__(self, db_path: Optional[Path] = None):
        """데이터베이스 초기화.
        
        Args:
            db_path: 데이터베이스 파일 경로 (기본값: ~/.gazehome/calibrations/gazehome.db)
        """
        if db_path is None:
            db_path = settings.calibration_dir / "gazehome.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 데이터베이스 초기화
        self._init_db()
    
    def _init_db(self):
        """테이블 생성 (데모용 간소화)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ✅ 사용자 테이블 (간소화: username, id만)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL
                )
            """)
            
            # ✅ 캘리브레이션 테이블 (간소화: 필드 최소화)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    calibration_file TEXT NOT NULL,
                    method TEXT DEFAULT 'nine_point',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # ✅ 기기 테이블 (간소화: capabilities만 JSON)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    device_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    device_type TEXT,
                    capabilities TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, device_id)
                )
            """)
            
            conn.commit()
            print(f"[Database] 초기화됨: {self.db_path}")
            
            # 데모 사용자 생성
            self._init_demo_user()
    
    def _init_demo_user(self):
        """데모용 기본 사용자 생성."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 이미 존재하는지 확인
            cursor.execute("SELECT id FROM users WHERE username = ?", (self.DEFAULT_USERNAME,))
            result = cursor.fetchone()
            
            if not result:
                cursor.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    (self.DEFAULT_USERNAME,)
                )
                conn.commit()
                print(f"[Database] 데모 사용자 생성: {self.DEFAULT_USERNAME}")
    
    def get_demo_user_id(self) -> int:
        """데모 사용자 ID를 가져옵니다.
        
        Returns:
            데모 사용자 ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (self.DEFAULT_USERNAME,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # 없으면 생성
            cursor.execute("INSERT INTO users (username) VALUES (?)", (self.DEFAULT_USERNAME,))
            conn.commit()
            return cursor.lastrowid
    
    # =========================================================================
    # 캘리브레이션 관리
    # =========================================================================
    
    def add_calibration(
        self,
        calibration_file: str,
        method: str = "nine_point"
    ):
        """새로운 캘리브레이션을 기록합니다 (데모는 항상 1명 사용자).
        
        Args:
            calibration_file: 캘리브레이션 파일 경로
            method: 캘리브레이션 방식 (기본값: nine_point)
        """
        user_id = self.get_demo_user_id()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO calibrations (user_id, calibration_file, method)
                VALUES (?, ?, ?)
                """,
                (user_id, calibration_file, method)
            )
            conn.commit()
            print(f"[Database] 캘리브레이션 저장됨: {calibration_file}")
    
    def get_calibrations(self) -> List[Dict]:
        """모든 캘리브레이션을 가져옵니다 (데모는 1명).
        
        Returns:
            캘리브레이션 정보 딕셔너리 목록
        """
        user_id = self.get_demo_user_id()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM calibrations
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def has_calibration(self) -> bool:
        """캘리브레이션이 있는지 확인합니다.
        
        Returns:
            캘리브레이션 유무
        """
        calibrations = self.get_calibrations()
        return len(calibrations) > 0
    
    def get_latest_calibration(self) -> Optional[str]:
        """최신 캘리브레이션 파일을 가져옵니다.
        
        Returns:
            최신 캘리브레이션 파일 경로 또는 None
        """
        calibrations = self.get_calibrations()
        if calibrations:
            return calibrations[0]['calibration_file']
        return None
    
    # =========================================================================
    # 기기 관리 (AI Server 동기화)
    # =========================================================================
    
    def sync_devices(self, devices: List[Dict]):
        """AI Server에서 가져온 기기 목록을 로컬 DB에 동기화합니다 (데모는 1명).
        
        Args:
            devices: AI Server에서 가져온 기기 목록
                [{
                    "device_id": "ac_001",
                    "device_name": "에어컨",
                    "device_type": "airconditioner",
                    "capabilities": ["turn_on", "turn_off", ...]
                }, ...]
        """
        user_id = self.get_demo_user_id()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for device in devices:
                capabilities_json = json.dumps(device.get("capabilities", []))
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO devices 
                    (user_id, device_id, device_name, device_type, capabilities)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        device.get("device_id"),
                        device.get("device_name"),
                        device.get("device_type"),
                        capabilities_json
                    )
                )
            
            conn.commit()
            print(f"[Database] {len(devices)}개 기기 동기화됨")
    
    def get_devices(self) -> List[Dict]:
        """기기 목록을 로컬 DB에서 가져옵니다 (데모는 1명).
        
        Returns:
            기기 목록
        """
        user_id = self.get_demo_user_id()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM devices
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,)
            )
            
            devices = []
            for row in cursor.fetchall():
                device = dict(row)
                try:
                    device["capabilities"] = json.loads(device.get("capabilities", "[]"))
                except:
                    device["capabilities"] = []
                devices.append(device)
            
            return devices


# 전역 데이터베이스 인스턴스
db = Database()