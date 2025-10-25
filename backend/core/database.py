"""데모용 간소화된 SQLite 데이터베이스."""
from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import json

from backend.core.config import settings

logger = logging.getLogger(__name__)


class Database:
    """데모용 간단한 SQLite 데이터베이스 (1명 사용자 가정)."""
    
    # 🎯 고정된 데모 사용자
    DEFAULT_USERNAME = "demo_user"
    
    def __init__(self, db_path: Optional[Path] = None):
        """기능: 데이터베이스 초기화.
        
        args: db_path (선택사항, 기본값: ~/.gazehome/calibrations/gazehome.db)
        return: 없음
        """
        if db_path is None:
            db_path = settings.calibration_dir / "gazehome.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 데이터베이스 초기화
        self._init_db()
    
    def _init_db(self):
        """기능: 테이블 생성.
        
        args: 없음
        return: 없음
        """
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
            
            # ✅ 기기 테이블 (MongoDB 스키마 동기화)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    device_id TEXT NOT NULL UNIQUE,
                    device_type TEXT,
                    alias TEXT NOT NULL,
                    supported_actions TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, device_id)
                )
            """)
            
            conn.commit()
            logger.info(f"[Database] 초기화됨: {self.db_path}")
            
            # 데모 사용자 생성
            self._init_demo_user()
    
    def _init_demo_user(self):
        """기능: 데모 사용자 생성.
        
        args: 없음
        return: 없음
        """
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
                logger.info(f"[Database] 데모 사용자 생성: {self.DEFAULT_USERNAME}")
    
    def get_demo_user_id(self) -> int:
        """기능: 데모 사용자 ID 조회.
        
        args: 없음
        return: 데모 사용자 ID
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
        """기능: 캘리브레이션 저장.
        
        args: calibration_file, method
        return: 없음
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
            logger.info(f"[Database] 캘리브레이션 저장됨: {calibration_file}")
    
    def get_calibrations(self) -> List[Dict]:
        """기능: 캘리브레이션 목록 조회.
        
        args: 없음
        return: 캘리브레이션 정보 딕셔너리 목록
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
        """기능: 캘리브레이션 존재 확인.
        
        args: 없음
        return: 캘리브레이션 유무
        """
        calibrations = self.get_calibrations()
        return len(calibrations) > 0
    
    def get_latest_calibration(self) -> Optional[str]:
        """기능: 최신 캘리브레이션 파일 조회.
        
        args: 없음
        return: 최신 캘리브레이션 파일 경로 또는 None
        """
        calibrations = self.get_calibrations()
        if calibrations:
            return calibrations[0]['calibration_file']
        return None
    
    # =========================================================================
    # 기기 관리 (AI Server 동기화)
    # =========================================================================
    
    def sync_devices(self, devices: List[Dict]):
        """기능: 기기 목록 동기화 (MongoDB와 동일한 필드명 사용).
        
        AI-Services MongoDB의 user_devices 컬렉션과 동일하게 동기화합니다.
        
        args: devices (AI Server에서 가져온 기기 목록)
              예: [
                    {
                      "device_id": "b403_air_purifier_001",
                      "device_type": "air_purifier",
                      "alias": "거실 공기청정기",
                      "supported_actions": ["turn_on", "turn_off", "clean", "auto"],
                      "is_active": true
                    }
                  ]
        return: 없음
        """
        # MongoDB의 user_id와 동일하게 사용 (문자열)
        user_id = "default_user"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for device in devices:
                # ✅ MongoDB supported_actions → JSON 문자열 변환
                supported_actions_json = json.dumps(device.get("supported_actions", []))
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO devices 
                    (user_id, device_id, device_type, alias, supported_actions, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,  # ✅ 문자열 "default_user"
                        device.get("device_id"),
                        device.get("device_type"),
                        device.get("alias"),  # ✅ device_name → alias (MongoDB 필드명)
                        supported_actions_json,  # ✅ capabilities → supported_actions (MongoDB 필드명)
                        device.get("is_active", True),  # ✅ is_active 필드 추가
                        datetime.utcnow().isoformat()  # ✅ 동기화 시간 기록
                    )
                )
            
            conn.commit()
            logger.info(f"[Database] {len(devices)}개 기기 동기화됨 (MongoDB 스키마)")
    
    def get_devices(self) -> List[Dict]:
        """기능: 기기 목록 조회 (MongoDB 스키마 호환).
        
        args: 없음
        return: 기기 목록 (MongoDB 필드명 사용)
                예: [
                      {
                        "id": 1,
                        "user_id": "default_user",
                        "device_id": "b403_air_purifier_001",
                        "device_type": "air_purifier",
                        "alias": "거실 공기청정기",
                        "supported_actions": ["turn_on", "turn_off", "clean", "auto"],
                        "is_active": True
                      }
                    ]
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM devices
                WHERE is_active = 1
                ORDER BY id DESC
                """
            )
            
            devices = []
            for row in cursor.fetchall():
                device = dict(row)
                try:
                    # ✅ supported_actions JSON 파싱
                    device["supported_actions"] = json.loads(device.get("supported_actions", "[]"))
                except (json.JSONDecodeError, TypeError):
                    device["supported_actions"] = []
                devices.append(device)
            
            logger.info(f"[Database] {len(devices)}개 활성 기기 조회됨")
            return devices


# 전역 데이터베이스 인스턴스
db = Database()