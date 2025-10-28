#!/usr/bin/env python3
"""
테스트용 더미 데이터 생성 스크립트

기능:
1. 더미 사용자 생성
2. 더미 보정 데이터 생성
3. 테스트를 위해 바로 홈 UI로 이동 가능하도록 설정
"""

import sqlite3
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

# 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent  # edge-module 루트
DB_PATH = Path.home() / ".gazehome" / "calibrations" / "gazehome.db"
CALIB_DATA_DIR = Path.home() / ".gazehome" / "calibrations"

print(f"📁 프로젝트 경로: {PROJECT_ROOT}")
print(f"💾 DB 경로: {DB_PATH}")
print(f"📊 보정 데이터 경로: {CALIB_DATA_DIR}")


def create_dummy_user():
    """더미 사용자 생성"""
    print("\n" + "="*60)
    print("👤 더미 사용자 생성")
    print("="*60)
    
    # DB 초기화
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 테이블 생성 (backend/core/database.py의 스키마와 동일)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    """)
    
    # 캘리브레이션 테이블 생성
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
    
    # 더미 사용자 생성 (한 명)
    username = "demo_user"
    
    cursor.execute("""
        INSERT OR IGNORE INTO users 
        (username)
        VALUES (?)
    """, (username,))
    
    # 생성된 유저의 ID 조회
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()[0]
    
    # 보정 파일 경로 설정 (실제 pickle 파일 경로)
    calib_file = str(CALIB_DATA_DIR / "calibration_model.pkl")
    
    # calibrations 테이블에 등록
    cursor.execute("""
        INSERT INTO calibrations
        (user_id, calibration_file, method)
        VALUES (?, ?, ?)
    """, (user_id, calib_file, "ridge"))
    
    print(f"  ✅ 생성: {username} (ID: {user_id})")
    print(f"     - 보정 파일: {calib_file}")
    
    conn.commit()
    conn.close()
    print(f"\n✅ 사용자 DB 생성 완료: {DB_PATH}")
    
    return user_id


def create_dummy_calibration_data():
    """더미 보정 데이터 생성"""
    print("\n" + "="*60)
    print("📊 더미 보정 데이터 생성")
    print("="*60)
    
    CALIB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 더미 보정 모델 생성 (Ridge Regression)
    # 실제로는 9개 포인트에서 수집한 486차원 특징 데이터를 학습한 모델
    
    # sklearn Ridge 모델처럼 보이는 더미 데이터 생성
    calibration_data = {
        "model_type": "Ridge",
        "coefficients": np.random.randn(486, 2),  # 486차원 입력, 2차원 출력 (x, y)
        "intercept": np.array([0.0, 0.0]),
        "alpha": 1.0,
        "samples_count": 9,  # 9개 포인트
        "created_at": datetime.now().isoformat(),
        "notes": "테스트용 더미 보정 데이터"
    }
    
    model_path = CALIB_DATA_DIR / "calibration_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(calibration_data, f)
    
    print(f"  ✅ 생성: {model_path}")
    print(f"     - 모델 타입: {calibration_data['model_type']}")
    print(f"     - 입출력: {calibration_data['coefficients'].shape}")
    print(f"     - 포인트 개수: {calibration_data['samples_count']}")
    
    print(f"\n✅ 보정 데이터 생성 완료: {CALIB_DATA_DIR}")


def create_dummy_devices_db():
    """더미 기기 정보 DB 생성"""
    print("\n" + "="*60)
    print("🏠 더미 기기 정보 생성")
    print("="*60)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # devices 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL UNIQUE,
            device_type TEXT NOT NULL,
            alias TEXT NOT NULL,
            model_name TEXT,
            reportable BOOLEAN DEFAULT 1,
            device_profile TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # device_actions 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            action_type TEXT,
            action_name TEXT NOT NULL,
            readable INTEGER,
            writable INTEGER,
            value_type TEXT,
            value_range TEXT,
            created_at TEXT,
            FOREIGN KEY(device_id) REFERENCES devices(device_id)
        )
    """)
    
    # 더미 기기 생성
    dummy_devices = [
        ("device_purifier_001", "거실 공기청정기", "air_purifier", "LG AP2024"),
        ("device_aircon_001", "거실 에어컨", "air_conditioner", "LG AC2024"),
    ]
    
    now = datetime.now().isoformat()
    
    for device_id, alias, device_type, model_name in dummy_devices:
        cursor.execute("""
            INSERT OR REPLACE INTO devices
            (device_id, device_type, alias, model_name, reportable, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (device_id, device_type, alias, model_name, 1, now, now))
        print(f"  ✅ 기기: {alias} ({device_id})")
    
    # 더미 액션 생성
    dummy_actions = [
        # 공기청정기 액션
        ("device_purifier_001", "operation", "purifier_on", 1, 1, "enum", '["purifier_on"]'),
        ("device_purifier_001", "operation", "purifier_off", 1, 1, "enum", '["purifier_off"]'),
        ("device_purifier_001", "wind_strength", "wind_low", 1, 1, "enum", '["wind_low"]'),
        ("device_purifier_001", "wind_strength", "wind_mid", 1, 1, "enum", '["wind_mid"]'),
        ("device_purifier_001", "wind_strength", "wind_high", 1, 1, "enum", '["wind_high"]'),
        ("device_purifier_001", "operation_mode", "circulator", 1, 1, "enum", '["circulator"]'),
        ("device_purifier_001", "operation_mode", "clean", 1, 1, "enum", '["clean"]'),
        ("device_purifier_001", "operation_mode", "auto", 1, 1, "enum", '["auto"]'),
        
        # 에어컨 액션
        ("device_aircon_001", "operation", "aircon_on", 1, 1, "enum", '["aircon_on"]'),
        ("device_aircon_001", "operation", "aircon_off", 1, 1, "enum", '["aircon_off"]'),
        ("device_aircon_001", "wind_strength", "aircon_wind_low", 1, 1, "enum", '["aircon_wind_low"]'),
        ("device_aircon_001", "wind_strength", "aircon_wind_mid", 1, 1, "enum", '["aircon_wind_mid"]'),
        ("device_aircon_001", "wind_strength", "aircon_wind_high", 1, 1, "enum", '["aircon_wind_high"]'),
        ("device_aircon_001", "temperature", "temp_25", 1, 1, "int", "25"),
        ("device_aircon_001", "temperature", "temp_26", 1, 1, "int", "26"),
        ("device_aircon_001", "temperature", "temp_27", 1, 1, "int", "27"),
    ]
    
    for device_id, action_type, action_name, readable, writable, value_type, value_range in dummy_actions:
        cursor.execute("""
            INSERT INTO device_actions
            (device_id, action_type, action_name, readable, writable, value_type, value_range, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (device_id, action_type, action_name, readable, writable, value_type, value_range, now))
    
    print(f"  ✅ 생성된 액션: {len(dummy_actions)}개")
    
    conn.commit()
    conn.close()
    print(f"\n✅ 기기 DB 생성 완료")


def main():
    """메인 함수"""
    print("\n" + "="*60)
    print("🚀 테스트 데이터 생성 시작")
    print("="*60)
    
    try:
        user_id = create_dummy_user()
        create_dummy_calibration_data()
        create_dummy_devices_db()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 데이터 생성 완료!")
        print("="*60)
        print("\n📝 생성된 사용자:")
        print(f"  - demo_user (ID: {user_id})")
        print("\n🏠 생성된 기기:")
        print("  - device_purifier_001: 거실 공기청정기")
        print("  - device_aircon_001: 거실 에어컨")
        print("\n🎯 사용 방법:")
        print("  1. 백엔드 서버 시작 (python run.py)")
        print("  2. 프론트엔드 접속 (http://localhost:3000)")
        print("  3. 자동으로 demo_user로 로그인")
        print("  4. 보정 완료 상태이므로 바로 홈 UI에서 기기 제어 가능")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
