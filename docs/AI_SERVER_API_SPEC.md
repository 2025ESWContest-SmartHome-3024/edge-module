# 🔗 Edge Module ↔ AI Server API 명세서

**최종 버전**: v2.0  
**작성일**: 2025-10-22  
**상태**: ✅ 완료 및 구현됨

---

## 📋 API 구조 개요

```
┌─────────────────────┐
│   프론트엔드         │
│  (React + Vite)     │
└──────────┬──────────┘
           │
           ↓ WebSocket
    ┌──────────────────┐
    │  Edge Module     │ (8080)
    │  Backend(FastAPI)│
    └──────┬───────────┘
           │
           ↓ HTTP
    ┌──────────────────┐
    │  AI Server       │ (사용자 비공개)
    │ (Recommendation) │
    └──────┬───────────┘
           │
           ↓ HTTP
    ┌──────────────────┐
    │  Gateway         │
    │ (LG IoT API)     │
    └──────────────────┘
```

---

## 📤 1️⃣ Edge Module → AI Server

### 1-1. 기기 목록 조회

```
GET /api/gaze/devices?user_id=user_001
```

**요청:**
- Method: `GET`
- Query: `user_id=user_001`

**응답 (200):**
```json
{
  "devices": [
    {
      "deviceId": "9c4d22060d9f029ded2657da2ecbddad0d37b3f8fdde1292758d296fa258ee2c",
      "deviceInfo": {
        "deviceType": "DEVICE_AIR_PURIFIER",
        "modelName": "LG Air Purifier X200",
        "alias": "공기청정기",
        "reportable": true
      }
    },
    {
      "deviceId": "7a1c...",
      "deviceInfo": {
        "deviceType": "DEVICE_DRYER",
        "modelName": "LG Dryer Z100",
        "alias": "건조기",
        "reportable": true
      }
    },
    {
      "deviceId": "5d3e...",
      "deviceInfo": {
        "deviceType": "DEVICE_AIR_CONDITIONER",
        "modelName": "LG AC Pro",
        "alias": "에어컨",
        "reportable": true
      }
    }
  ]
}
```

---

### 1-2. 기기 클릭 이벤트 전송 (추천 수신)

```
POST /api/gaze/click
```

**요청:**
```json
{
  "user_id": "user_001",
  "device_id": "9c4d22060d9f029...",
  "device_name": "공기청정기",
  "device_type": "air_purifier",
  "timestamp": "2025-10-22T15:30:45+09:00"
}
```

**응답 (200):**
```json
{
  "status": "success",
  "recommendation": {
    "recommendation_id": "rec_abc123",
    "title": "공기청정기 킬까요?",
    "contents": "현재 실내 공기질이 나쁜 상태이므로 공기청정기를 켜시는 것을 추천드립니다.",
    "confidence": 0.95
  },
  "message": "클릭 이벤트 처리됨"
}
```

---

### 1-3. 사용자 등록

```
POST /api/users/register
```

**요청:**
```json
{
  "user_id": "user_001",
  "username": "사용자",
  "has_calibration": true,
  "timestamp": "2025-10-22T15:30:45+09:00"
}
```

**응답 (200):**
```json
{
  "status": "success",
  "user_id": "user_001",
  "message": "사용자 등록 완료"
}
```

---

### 1-4. 추천 피드백 전송

```
POST /api/gaze/feedback
```

**요청:**
```json
{
  "recommendation_id": "rec_abc123",
  "user_id": "user_001",
  "accepted": true,
  "timestamp": "2025-10-22T15:31:00+09:00"
}
```

**응답 (200):**
```json
{
  "status": "success",
  "message": "피드백이 저장되었습니다"
}
```

---

## 📥 2️⃣ AI Server → Edge Module

### 2-1. 추천 수신 및 피드백 제출

```
POST /api/recommendations
```

**요청 (AI Server → Edge Module):**
```json
{
  "recommendation_id": "rec_xyz789",
  "title": "에어컨 킬까요?",
  "contents": "현재 온도가 28도로 높습니다. 에어컨을 켜시기를 추천합니다.",
  "user_id": "user_001"
}
```

**응답 (Edge Module → AI Server):**
```json
{
  "message": "추천 문구 유저 피드백",
  "confirm": "YES"
}
```

---

### 2-2. 프론트엔드 피드백 제출

```
POST /api/recommendations/feedback
```

**요청 (프론트엔드 → Edge Module):**
```json
{
  "recommendation_id": "rec_xyz789",
  "user_id": "user_001",
  "accepted": true
}
```

**응답 (Edge Module → 프론트엔드):**
```json
{
  "success": true,
  "message": "피드백이 전송되었습니다"
}
```

---

## 🔄 통신 흐름

### 시나리오: 사용자가 공기청정기를 응시하여 제어

```
1. 프론트엔드: WebSocket 시선 좌표 수집
   └─> GazeCursor 표시, DeviceCard 감지

2. 사용자: 2초 응시 또는 깜빡임 감지
   └─> handleToggle() 호출

3. DeviceCard: POST /api/devices/{device_id}/click
   └─> Edge Module Backend 수신

4. Edge Module: POST /api/gaze/click (AI Server에 전송)
   ├─ 요청: device_id, device_name, user_id 등
   └─ 응답: recommendation (title, contents, confidence)

5. Edge Module: recommendation을 custom event로 프론트엔드 전송
   └─> RecommendationModal 표시

6. 사용자: YES/NO 선택 (RecommendationModal에서)
   └─> 깜빡임 또는 클릭

7. 프론트엔드: POST /api/recommendations/feedback
   ├─ 요청: recommendation_id, accepted
   └─ 응답: success

8. Edge Module: POST /api/gaze/feedback (AI Server에 전송)
   ├─ 요청: recommendation_id, user_id, accepted
   └─ 응답: success

9. AI Server (백그라운드): Gateway에 기기 제어 명령 전송
   └─> 실제 LG 기기 제어
```

---

## 📊 기기 제어 액션 매핑

### 공기청정기 (DEVICE_AIR_PURIFIER)
| 액션       | 설명           |
| ---------- | -------------- |
| `clean`    | 청정 모드 시작 |
| `auto`     | 자동 모드      |
| `turn_on`  | 전원 켜기      |
| `turn_off` | 전원 끄기      |

### 건조기 (DEVICE_DRYER)
| 액션          | 설명           |
| ------------- | -------------- |
| `dryer_on`    | 건조기 시작    |
| `dryer_off`   | 건조기 종료    |
| `dryer_start` | 건조 작업 시작 |
| `dryer_stop`  | 건조 작업 중지 |

### 에어컨 (DEVICE_AIR_CONDITIONER)
| 액션         | 설명                    |
| ------------ | ----------------------- |
| `aircon_on`  | 에어컨 켜기             |
| `aircon_off` | 에어컨 끄기             |
| `temp_{n}`   | 온도 설정 (예: temp_25) |

---

## 🛠️ Edge Module 구현 상세

### ai_client.py

**클래스**: `AIServiceClient`

**주요 메서드:**

1. `send_device_click(gaze_click_request)`
   - AI Server에 기기 클릭 이벤트 전송
   - 추천을 응답으로 받음

2. `get_user_devices(user_id)`
   - AI Server에서 기기 목록 조회
   - 기기명, 타입, 상태 포함

3. `register_user_async(user_id, username, has_calibration)`
   - 사용자를 AI Server에 등록 (비동기)
   - 로그인 응답 지연 없음

4. `send_recommendation_feedback(recommendation_id, user_id, accepted)`
   - 사용자 피드백을 AI Server로 전송
   - 추천 수락/거절 정보 포함

---

### devices.py

**엔드포인트:**

1. `GET /api/devices`
   - 기기 목록 조회
   - AI Server에서 조회 후 로컬 캐시에 동기화

2. `POST /api/devices/{device_id}/click`
   - 기기 클릭 처리
   - AI Server에 전송 및 추천 수신
   - 프론트엔드에 recommendation 반환

---

### recommendations.py

**엔드포인트:**

1. `POST /api/recommendations`
   - AI Server에서 추천 수신
   - 프론트엔드에 전달
   - 피드백을 AI Server로 백그라운드 전송

2. `POST /api/recommendations/feedback`
   - 프론트엔드에서 사용자 피드백 수신
   - AI Server로 피드백 전송

---

## ✅ 에러 처리

### 재시도 정책 (Exponential Backoff)

```python
max_retries = 3
wait_time = 2^attempt
```

- 1차 실패 → 1초 대기
- 2차 실패 → 2초 대기
- 3차 실패 → Fallback 응답

### Fallback 응답

AI Server 통신 실패 시:

```json
{
  "status": "fallback",
  "recommendation": {
    "recommendation_id": "rec_fallback_...",
    "title": "기본 제어",
    "contents": "AI Server 연결 오류로 기본 토글 동작 제안",
    "confidence": 0.5
  }
}
```

---

## 📝 로깅 형식

### 정보 레벨 (INFO)

```
📤 AI 서버 기기 목록 요청: GET /api/gaze/devices
✅ AI 서버에서 3개 기기 조회됨
📩 AI Server로부터 추천 수신
   - recommendation_id: rec_abc123
   - 제목: 에어컨 킬까요?
```

### 경고 레벨 (WARNING)

```
⏱️ AI 서버 타임아웃 (시도 1/3)
⚠️ AI Server 실패, 로컬 캐시 사용
```

### 에러 레벨 (ERROR)

```
❌ AI 서버 통신 실패: Connection refused
❌ AI 서버 기기 목록 조회 실패: Timeout
```

---

## 🧪 테스트 가능한 시나리오

### 1. 기기 목록 조회
```bash
curl -X GET "http://localhost:8080/api/devices"
```

### 2. 기기 클릭 (추천 수신)
```bash
curl -X POST "http://localhost:8080/api/devices/9c4d22.../click" \
  -H "Content-Type: application/json" \
  -d '{"command": "toggle"}'
```

### 3. 피드백 제출
```bash
curl -X POST "http://localhost:8080/api/recommendations/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_id": "rec_abc123",
    "user_id": "user_001",
    "accepted": true
  }'
```

---

## 🔐 보안 고려사항

- ✅ user_id 검증 (현재: 데모 단일 사용자)
- ✅ 타임스탬프 포함 (ISO 8601 형식)
- ✅ HTTPS 권장 (프로덕션 환경)
- ⚠️ API 키 인증 (미구현 - AI Server 담당)

---

## 📞 지원 및 문의

**개발자**: ESWC-AIRIS  
**저장소**: https://github.com/ESWC-AIRIS/edge-module  
**브랜치**: `develop-ai-server`
