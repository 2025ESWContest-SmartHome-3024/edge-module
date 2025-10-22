#!/usr/bin/env python3
"""데이터베이스 상태 조회 유틸리티."""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from backend.core.database import db
from backend.core.config import settings


def display_db_status():
    """기능: 데이터베이스 상태 조회 및 표시.
    
    args: 없음
    return: 없음
    """
    try:
        print("\n" + "="*70)
        print("📊 데이터베이스 상태 조회")
        print("="*70)
        
        # 1. 기본 정보
        print("\n[기본 정보]")
        print(f"  DB 파일: {db.db_path}")
        print(f"  DB 크기: {db.db_path.stat().st_size} bytes")
        
        # 2. 사용자 정보
        print("\n[사용자 정보]")
        user_id = db.get_demo_user_id()
        print(f"  User ID: {user_id}")
        print(f"  Username: {db.DEFAULT_USERNAME}")
        
        # 3. 기기 정보
        print("\n[기기 목록]")
        devices = db.get_devices()
        print(f"  총 기기 수: {len(devices)}")
        for device in devices:
            print(f"\n  📱 {device['device_name']} ({device['device_id']})")
            print(f"     - Type: {device['device_type']}")
            print(f"     - Capabilities: {device['capabilities']}")
        
        # 4. 캘리브레이션 정보
        print("\n[캘리브레이션 정보]")
        has_cal = db.has_calibration()
        print(f"  캘리브레이션 존재: {'✅ Yes' if has_cal else '❌ No'}")
        
        if has_cal:
            calibrations = db.get_calibrations()
            print(f"  총 캘리브레이션 수: {len(calibrations)}")
            for cal in calibrations:
                print(f"\n  📝 Calibration #{cal['id']}")
                print(f"     - File: {cal['calibration_file']}")
                print(f"     - Method: {cal['method']}")
                print(f"     - Created: {cal['created_at']}")
        
        # 5. Raw SQL 쿼리로 테이블 정보 확인
        print("\n[테이블 정보]")
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # Users 테이블
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"  Users 테이블: {user_count}명")
            
            # Devices 테이블
            cursor.execute("SELECT COUNT(*) FROM devices")
            device_count = cursor.fetchone()[0]
            print(f"  Devices 테이블: {device_count}개")
            
            # Calibrations 테이블
            cursor.execute("SELECT COUNT(*) FROM calibrations")
            cal_count = cursor.fetchone()[0]
            print(f"  Calibrations 테이블: {cal_count}개")
        
        print("\n" + "="*70)
        print("✅ 데이터베이스 조회 완료")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()


def display_test_commands():
    """기능: 테스트용 Postman 명령어 표시.
    
    args: 없음
    return: 없음
    """
    print("\n" + "="*70)
    print("🧪 Postman 테스트 명령어")
    print("="*70)
    
    user_id = db.get_demo_user_id()
    
    print("\n[1] 사용자 로그인")
    print("  Method: POST")
    print("  URL: http://localhost:8080/api/users/login")
    print("  Body: {}")
    
    print("\n[2] 기기 목록 조회")
    print("  Method: GET")
    print("  URL: http://localhost:8080/api/devices")
    
    print("\n[3] 기기 클릭")
    print("  Method: POST")
    print("  URL: http://localhost:8080/api/devices/ac_001/click")
    print(f"  Body: {{'user_id': '{user_id}'}}")
    
    print("\n[4] 추천 수신")
    print("  Method: POST")
    print("  URL: http://localhost:8080/api/recommendations")
    print(f"""  Body: {{
    "recommendation_id": "rec_001",
    "title": "에어컨 켜시겠어요?",
    "contents": "현재 실내 온도가 28도로 높습니다.",
    "user_id": "{user_id}"
  }}""")
    
    print("\n[5] 피드백 제출 (YES)")
    print("  Method: POST")
    print("  URL: http://localhost:8080/api/recommendations/feedback")
    print(f"""  Body: {{
    "recommendation_id": "rec_001",
    "user_id": "{user_id}",
    "accepted": true,
    "device_id": "ac_001",
    "action": "turn_on"
  }}""")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    display_db_status()
    display_test_commands()
