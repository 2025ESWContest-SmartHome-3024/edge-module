#!/usr/bin/env python3
"""테스트용 Mock 데이터 생성 스크립트."""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import json
from datetime import datetime, timedelta
import pytz

from backend.core.database import db
from backend.core.config import settings

KST = pytz.timezone('Asia/Seoul')


def create_mock_devices():
    """기능: Mock 기기 목록 생성.
    
    args: 없음
    return: 기기 목록
    """
    devices = [
        {
            "device_id": "ac_001",
            "device_name": "거실 에어컨",
            "device_type": "airconditioner",
            "capabilities": ["turn_on", "turn_off", "set_temperature", "set_mode"]
        },
        {
            "device_id": "light_001",
            "device_name": "거실 조명",
            "device_type": "light",
            "capabilities": ["turn_on", "turn_off", "set_brightness"]
        },
        {
            "device_id": "tv_001",
            "device_name": "TV",
            "device_type": "tv",
            "capabilities": ["turn_on", "turn_off", "volume_up", "volume_down", "change_channel"]
        },
        {
            "device_id": "fan_001",
            "device_name": "선풍기",
            "device_type": "fan",
            "capabilities": ["turn_on", "turn_off", "set_speed"]
        },
        {
            "device_id": "door_001",
            "device_name": "현관 스마트락",
            "device_type": "door_lock",
            "capabilities": ["lock", "unlock"]
        }
    ]
    return devices


def create_mock_recommendations():
    """기능: Mock 추천 메시지 목록 생성.
    
    args: 없음
    return: 추천 메시지 목록
    """
    recommendations = [
        {
            "recommendation_id": "rec_001",
            "title": "에어컨 켜시겠어요?",
            "contents": "현재 실내 온도가 28도로 높습니다. 에어컨을 켜시겠어요?",
            "device_id": "ac_001",
            "action": "turn_on",
            "confidence": 0.95
        },
        {
            "recommendation_id": "rec_002",
            "title": "조명을 켜시겠어요?",
            "contents": "주변이 어두워졌습니다. 거실 조명을 켜시겠어요?",
            "device_id": "light_001",
            "action": "turn_on",
            "confidence": 0.88
        },
        {
            "recommendation_id": "rec_003",
            "title": "TV 음량 조정",
            "contents": "TV 음량이 너무 큽니다. 줄여드릴까요?",
            "device_id": "tv_001",
            "action": "volume_down",
            "confidence": 0.82
        },
        {
            "recommendation_id": "rec_004",
            "title": "선풍기 켜기",
            "contents": "공기 흐름이 필요합니다. 선풍기를 켜시겠어요?",
            "device_id": "fan_001",
            "action": "turn_on",
            "confidence": 0.90
        },
        {
            "recommendation_id": "rec_005",
            "title": "문 잠금 확인",
            "contents": "현관 스마트락이 잠겨있지 않습니다. 잠그시겠어요?",
            "device_id": "door_001",
            "action": "lock",
            "confidence": 0.98
        }
    ]
    return recommendations


def create_mock_calibration_data():
    """기능: Mock 보정 데이터 생성.
    
    args: 없음
    return: 보정 데이터 (features 리스트)
    """
    # 실제 보정에서는 얼굴 특징이 저장되지만,
    # Mock 데이터로는 더미 값 사용
    calibration_data = {
        "method": "nine_point",
        "points": 9,
        "timestamp": datetime.now(KST).isoformat(),
        "accuracy": 0.92,
        "features_sample": [
            [0.123, 0.456, 0.789, 0.234, 0.567],  # Point 1
            [0.234, 0.567, 0.890, 0.345, 0.678],  # Point 2
            [0.345, 0.678, 0.901, 0.456, 0.789],  # Point 3
            [0.456, 0.789, 0.012, 0.567, 0.890],  # Point 4
            [0.567, 0.890, 0.123, 0.678, 0.901],  # Point 5
            [0.678, 0.901, 0.234, 0.789, 0.012],  # Point 6
            [0.789, 0.012, 0.345, 0.890, 0.123],  # Point 7
            [0.890, 0.123, 0.456, 0.901, 0.234],  # Point 8
            [0.901, 0.234, 0.567, 0.012, 0.345],  # Point 9
        ]
    }
    return calibration_data


def save_mock_data():
    """기능: Mock 데이터를 데이터베이스에 저장.
    
    args: 없음
    return: 없음
    """
    try:
        print("\n" + "="*60)
        print("테스트용 Mock 데이터 생성 시작")
        print("="*60)
        
        # 1. 기기 목록 동기화
        print("\n[1/4] 기기 목록 동기화 중...")
        devices = create_mock_devices()
        db.sync_devices(devices)
        print(f"✅ {len(devices)}개 기기 저장됨")
        for device in devices:
            print(f"   - {device['device_name']} ({device['device_id']})")
        
        # 2. 캘리브레이션 데이터 저장
        print("\n[2/4] 캘리브레이션 데이터 저장 중...")
        calibration_data = create_mock_calibration_data()
        
        # Mock 캘리브레이션 파일 경로
        calibration_dir = settings.calibration_dir
        calibration_dir.mkdir(parents=True, exist_ok=True)
        calibration_file = calibration_dir / "mock_calibration.pkl"
        
        # JSON으로 저장 (실제는 pickle이지만, Mock용으로 JSON 사용)
        calibration_json_file = calibration_dir / "mock_calibration.json"
        with open(calibration_json_file, "w") as f:
            json.dump(calibration_data, f, indent=2)
        
        db.add_calibration(str(calibration_json_file), method="nine_point")
        print(f"✅ 캘리브레이션 데이터 저장됨")
        print(f"   - 파일: {calibration_json_file}")
        print(f"   - 정확도: {calibration_data['accuracy']}")
        
        # 3. 추천 메시지 정보 (DB에는 저장하지 않음, 참고용)
        print("\n[3/4] Mock 추천 메시지 목록:")
        recommendations = create_mock_recommendations()
        for rec in recommendations:
            print(f"   - {rec['recommendation_id']}: {rec['title']}")
        
        # 4. 데이터베이스 상태 확인
        print("\n[4/4] 데이터베이스 상태 확인:")
        
        user_id = db.get_demo_user_id()
        print(f"   - 사용자 ID: {user_id}")
        
        stored_devices = db.get_devices()
        print(f"   - 저장된 기기 수: {len(stored_devices)}")
        
        has_cal = db.has_calibration()
        print(f"   - 캘리브레이션 여부: {has_cal}")
        
        if has_cal:
            latest_cal = db.get_latest_calibration()
            print(f"   - 최신 캘리브레이션: {latest_cal}")
        
        print("\n" + "="*60)
        print("✅ Mock 데이터 생성 완료!")
        print("="*60)
        
        print("\n📋 테스트 정보:")
        print(f"   User ID: {user_id}")
        print(f"   DB Path: {db.db_path}")
        print(f"   Calibration Dir: {settings.calibration_dir}")
        
        print("\n🧪 Postman 테스트 시:") 
        print(f"   POST /api/users/login")
        print(f"   GET /api/devices")
        print(f"   POST /api/devices/{{device_id}}/click")
        print(f"   POST /api/recommendations (아래 중 선택)")
        for rec in recommendations[:2]:
            print(f"      - {rec['recommendation_id']}: {rec['title']}")
        print(f"   POST /api/recommendations/feedback")
        
        print("\n💾 생성된 파일:")
        print(f"   - {calibration_json_file}")
        
        return {
            "user_id": user_id,
            "devices": stored_devices,
            "has_calibration": has_cal,
            "recommendations": recommendations
        }
        
    except Exception as e:
        print(f"\n❌ Mock 데이터 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = save_mock_data()
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
