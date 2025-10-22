# AI Server ↔ Edge Module API 명세서

## 📋 목차
1. [API 개요](#api-개요)
2. [API 목록](#api-목록)
3. [상세 API 명세](#상세-api-명세)
4. [통신 흐름도](#통신-흐름도)
5. [환경 설정](#환경-설정)
6. [오류 처리](#오류-처리)
7. [API 통계](#api-통계)

---

## API 개요

### 목적
Edge Module의 Backend가 AI Server와 통신하여 다음 기능을 수행합니다:
- 사용자의 시선 추적 기반 기기 클릭 이벤트 전송
- AI Server로부터 기기 제어 추천 받기
- 기기 목록 동기화
- 사용자 정보 등록
- 사용자 피드백 전송

### 통신 특징
- **비동기 통신**: `asyncio` + `httpx` 기반
- **자동 재시도**: 최대 3회 (Exponential Backoff)
- **타임아웃**: 10초
- **Fallback 지원**: AI Server 실패 시에도 기본 추천 제공

---

## API 목록

| 순번 | API 이름              | Method | Endpoint                        | 용도                          | 중요도 |
| ---- | --------------------- | ------ | ------------------------------- | ----------------------------- | ------ |
| 1️⃣    | 기기 클릭 이벤트 전송 | POST   | `/api/gaze/click`               | 시선 클릭 시 AI Server에 전달 | 🔴 핵심 |
| 2️⃣    | 기기 목록 조회        | GET    | `/api/gaze/devices/{user_id}`   | 사용자 기기 목록 조회         | 🟡 중요 |
| 3️⃣    | 사용자 등록           | POST   | `/api/users/register`           | 사용자 정보 등록 (백그라운드) | 🟡 선택 |
| 4️⃣    | 추천 피드백 전송      | POST   | `/api/recommendations/feedback` | YES/NO 피드백 전송            | 🟡 중요 |

---

## 상세 API 명세

### 1️⃣ 기기 클릭 이벤트 전송

**개요**
- **설명**: 사용자가 시선으로 기기를 클릭하면 AI Server에 전달, 응답에 추천 포함
- **통신 방식**: Edge Module → AI Server
- **Method**: POST
- **Endpoint**: `{AI_SERVER_URL}/api/gaze/click`
- **상태 코드**: 200 (성공), 500 (실패), 408 (타임아웃)

**Request Body**

```json
{
  "user_id": "1",
  "session_id": "session_xyz_1729443600",
  "clicked_device": {
    "device_id": "ac_001",
    "name": "거실 에어컨",
    "type": "airconditioner"
  },
  "timestamp": "2024-10-21T10:30:00+09:00",
  "context": {
    "command": "toggle"
  }
}
```

| Field                      | Type   | 필수 | 설명                                    |
| -------------------------- | ------ | ---- | --------------------------------------- |
| `user_id`                  | string | O    | 사용자 ID                               |
| `session_id`               | string | O    | 세션 ID (추적용)                        |
| `clicked_device`           | object | O    | 클릭된 기기 정보                        |
| `clicked_device.device_id` | string | O    | 기기 ID                                 |
| `clicked_device.name`      | string | O    | 기기명                                  |
| `clicked_device.type`      | string | O    | 기기 타입 (airconditioner, light, etc.) |
| `timestamp`                | string | O    | ISO 8601 타임스탬프                     |
| `context.command`          | string | X    | 명령어 (toggle, turn_on, turn_off 등)   |

**Response Body (성공)**

```json
{
  "status": "success",
  "click_id": "click_abc123",
  "recommendation": {
    "recommendation_id": "rec_abc123",
    "action": "turn_on",
    "device_id": "ac_001",
    "device_name": "거실 에어컨",
    "reason": "현재 온도가 28도로 높습니다",
    "confidence": 0.95
  },
  "message": "클릭 이벤트 저장 및 추천 생성됨"
}
```

| Field                              | Type   | 설명                     |
| ---------------------------------- | ------ | ------------------------ |
| `status`                           | string | 상태 (success, fallback) |
| `click_id`                         | string | 클릭 이벤트 ID           |
| `recommendation`                   | object | 추천 정보                |
| `recommendation.recommendation_id` | string | 추천 ID                  |
| `recommendation.action`            | string | 실행할 액션              |
| `recommendation.device_id`         | string | 대상 기기 ID             |
| `recommendation.device_name`       | string | 대상 기기명              |
| `recommendation.reason`            | string | 추천 이유                |
| `recommendation.confidence`        | number | 신뢰도 (0.0~1.0)         |
| `message`                          | string | 메시지                   |

**Response Body (Fallback - AI Server 실패)**

```json
{
  "status": "fallback",
  "click_id": "click_fallback_session_xyz_1729443600",
  "recommendation": {
    "recommendation_id": "rec_fallback_1729443602.123456",
    "device_id": "ac_001",
    "device_name": "거실 에어컨",
    "action": "toggle",
    "params": {},
    "reason": "AI 서버 연결 오류로 기본 토글 동작 제안",
    "confidence": 0.5
  },
  "message": "AI 서버 오류로 Fallback 응답 제공"
}
```

**구현 코드** (Backend: `devices.py`)

```python
gaze_click_request = {
    "user_id": str(demo_user_id),
    "session_id": f"session_{device_id}_{datetime.now(KST).timestamp()}",
    "clicked_device": {
        "device_id": device_id,
        "name": device_id,
        "type": "unknown"
    },
    "timestamp": datetime.now(KST).isoformat(),
    "context": {"command": "toggle"}
}
result = await ai_client.send_device_click(gaze_click_request)
```

---

### 2️⃣ 기기 목록 조회

**개요**
- **설명**: 사용자의 기기 목록을 AI Server에서 조회
- **통신 방식**: Edge Module → AI Server
- **Method**: GET
- **Endpoint**: `{AI_SERVER_URL}/api/gaze/devices/{user_id}`
- **상태 코드**: 200 (성공), 404 (사용자 없음), 500 (서버 오류)

**Request Parameters**

| Parameter | Type   | 위치 | 필수 | 설명      |
| --------- | ------ | ---- | ---- | --------- |
| `user_id` | string | path | O    | 사용자 ID |

**Response Body (성공)**

```json
{
  "devices": [
    {
      "device_id": "ac_001",
      "device_name": "거실 에어컨",
      "device_type": "airconditioner",
      "capabilities": ["turn_on", "turn_off", "set_temperature"]
    },
    {
      "device_id": "light_001",
      "device_name": "침실 조명",
      "device_type": "light",
      "capabilities": ["turn_on", "turn_off", "set_brightness"]
    }
  ],
  "count": 2
}
```

| Field                    | Type   | 설명               |
| ------------------------ | ------ | ------------------ |
| `devices`                | array  | 기기 목록          |
| `devices[].device_id`    | string | 기기 ID            |
| `devices[].device_name`  | string | 기기명             |
| `devices[].device_type`  | string | 기기 타입          |
| `devices[].capabilities` | array  | 가능한 명령어 목록 |
| `count`                  | number | 기기 개수          |

**구현 코드** (Backend: `devices.py`)

```python
devices = await ai_client.get_user_devices(demo_user_id_str)

if devices:
    db.sync_devices(devices)
    return {
        "success": True,
        "devices": devices,
        "count": len(devices),
        "source": "ai_server"
    }
else:
    local_devices = db.get_devices()
    return {
        "success": True,
        "devices": local_devices,
        "count": len(local_devices),
        "source": "local_cache"
    }
```

---

### 3️⃣ 사용자 등록

**개요**
- **설명**: 로그인 시 Edge Module의 사용자 정보를 AI Server에 등록 (백그라운드)
- **통신 방식**: Edge Module → AI Server
- **Method**: POST
- **Endpoint**: `{AI_SERVER_URL}/api/users/register`
- **상태 코드**: 200 (성공), 400 (잘못된 요청), 500 (서버 오류)
- **비동기**: 백그라운드 작업 (응답 지연 없음)

**Request Body**

```json
{
  "user_id": "1",
  "username": "demo_user",
  "has_calibration": true,
  "timestamp": "2024-10-21T10:30:00+09:00"
}
```

| Field             | Type    | 필수 | 설명                   |
| ----------------- | ------- | ---- | ---------------------- |
| `user_id`         | string  | O    | 로컬 SQLite 사용자 ID  |
| `username`        | string  | O    | 사용자명               |
| `has_calibration` | boolean | O    | 캘리브레이션 완료 여부 |
| `timestamp`       | string  | O    | ISO 8601 타임스탬프    |

**Response Body (성공)**

```json
{
  "success": true,
  "user_id": "1",
  "message": "사용자가 등록되었습니다"
}
```

| Field     | Type    | 설명             |
| --------- | ------- | ---------------- |
| `success` | boolean | 등록 성공 여부   |
| `user_id` | string  | 등록된 사용자 ID |
| `message` | string  | 메시지           |

**구현 코드** (Backend: `users.py`)

```python
try:
    asyncio.create_task(
        ai_client.register_user_async(
            user_id=str(user_id),
            username=username,
            has_calibration=has_calibration
        )
    )
except Exception as e:
    logger.warning(f"[User API] AI Server 등록 실패 (로컬만 사용): {e}")
    # 계속 진행 - 로그인 성공
```

---

### 4️⃣ 추천 피드백 전송

**개요**
- **설명**: AI Server에서 받은 추천 문구에 대해 사용자의 YES/NO 피드백 전송
- **통신 방식**: Edge Module → AI Server
- **Method**: POST
- **Endpoint**: `{AI_SERVER_URL}/api/recommendations/feedback`
- **상태 코드**: 200 (성공), 400 (잘못된 요청), 500 (서버 오류)

**Request Body**

```json
{
  "recommendation_id": "rec_abc123",
  "user_id": "1",
  "accepted": true,
  "timestamp": "2024-10-21T10:30:00+09:00"
}
```

| Field               | Type    | 필수 | 설명                             |
| ------------------- | ------- | ---- | -------------------------------- |
| `recommendation_id` | string  | O    | 추천 ID                          |
| `user_id`           | string  | O    | 사용자 ID                        |
| `accepted`          | boolean | O    | 수락 여부 (true: YES, false: NO) |
| `timestamp`         | string  | O    | ISO 8601 타임스탬프              |

**Response Body (성공)**

```json
{
  "success": true,
  "recommendation_id": "rec_abc123",
  "message": "피드백이 저장되었습니다"
}
```

| Field               | Type    | 설명                  |
| ------------------- | ------- | --------------------- |
| `success`           | boolean | 피드백 저장 성공 여부 |
| `recommendation_id` | string  | 추천 ID               |
| `message`           | string  | 메시지                |

**구현 코드** (Backend: `recommendations.py`)

```python
await ai_client.send_recommendation_feedback(
    recommendation_id=recommendation_id,
    user_id=user_id,
    accepted=accepted
)
```

---

## 통신 흐름도

### 전체 시스템 흐름

```
┌─────────────┐         ┌──────────────┐         ┌───────────────┐
│   Frontend  │         │ Edge Module  │         │   AI Server   │
│  (3000)     │         │   (8080)     │         │    (8000)     │
└─────────────┘         └──────────────┘         └───────────────┘
      │                        │                        │
      ├─ 로그인 ───────────────→ │                        │
      │                        ├─ POST /api/users/register──→ │
      │                        │←─ 응답 (백그라운드) ────── │
      │                        │                        │
      │←─ 로그인 응답 ────────│                        │
      │                        │                        │
      ├─ 기기 목록 조회────────→ │                        │
      │                        ├─ GET /api/gaze/devices/{user_id}──→ │
      │                        │←─ 기기 목록 ──────────── │
      │←─ 기기 목록 ─────────│                        │
      │                        │                        │
      ├─ 기기 카드 클릭────────→ │                        │
      │                        ├─ POST /api/gaze/click ──→ │
      │                        │                        │ (AI 처리)
      │                        │←─ 추천 포함 응답 ───── │
      │←─ 추천 모달 표시───────│                        │
      │                        │                        │
      ├─ YES/NO 선택──────────→ │                        │
      │                        ├─ POST /api/recommendations/feedback──→ │
      │                        │←─ 피드백 저장 응답─── │
      │←─ 완료 ──────────────│                        │
```

### 상세 기기 클릭 흐름

```
사용자 시선 클릭
         ↓
Frontend: DeviceCard onClick
         ↓
POST /api/devices/{device_id}/click
         ↓
Backend: devices.py - handle_device_click()
         ↓
AI Server로 전송: POST /api/gaze/click
         ↓
      ┌─ AI Server 응답? ─┬─ Success → 추천 포함
      │                  └─ Fail/Timeout → Fallback
      │
      ├─ Response 반환
      │
Frontend: 추천 모달 표시
         ↓
사용자: YES/NO 선택
         ↓
POST /api/recommendations/feedback
         ↓
Backend로 전송 → AI Server로 전송
         ↓
완료
```

---

## 환경 설정

### Backend 설정 (`backend/core/config.py`)

```python
# AI 서버 설정
ai_server_url: str = os.getenv("AI_SERVER_URL", "http://34.227.8.172:8000")
ai_request_timeout: int = int(os.getenv("AI_REQUEST_TIMEOUT", "10"))
ai_max_retries: int = int(os.getenv("AI_MAX_RETRIES", "3"))
```

### 환경 변수 (`.env` 파일)

```bash
# AI Server 설정
AI_SERVER_URL=http://34.227.8.172:8000
AI_REQUEST_TIMEOUT=10
AI_MAX_RETRIES=3
```

### Frontend 설정 (`frontend/vite.config.js`)

```javascript
server: {
    port: 3000,
    proxy: {
        '/api': {
            target: 'http://127.0.0.1:8080',
            changeOrigin: true,
        },
        '/ws': {
            target: 'ws://127.0.0.1:8080',
            ws: true,
        },
    },
}
```

---

## 오류 처리

### 재시도 로직 (Exponential Backoff)

```
시도 1: 즉시 전송
   ↓ (실패)
시도 2: 2초 대기 후 전송
   ↓ (실패)
시도 3: 4초 대기 후 전송
   ↓ (실패)
Fallback 응답 반환
```

### Fallback 응답 예시

```json
{
  "status": "fallback",
  "click_id": "click_fallback_session_xyz_1729443600",
  "recommendation": {
    "recommendation_id": "rec_fallback_1729443602.123456",
    "device_id": "ac_001",
    "device_name": "거실 에어컨",
    "action": "toggle",
    "params": {},
    "reason": "AI 서버 연결 오류로 기본 토글 동작 제안",
    "confidence": 0.5
  },
  "message": "AI 서버 오류로 Fallback 응답 제공"
}
```

### 오류 시나리오

| 상황                | 처리 방식                      |
| ------------------- | ------------------------------ |
| AI Server 타임아웃  | 3회 재시도 후 Fallback         |
| AI Server 연결 실패 | 3회 재시도 후 Fallback         |
| AI Server HTTP 오류 | 3회 재시도 후 Fallback         |
| 사용자 등록 실패    | 로컬 로그인만 진행 (오류 무시) |
| 추천 피드백 실패    | 로컬 저장만 진행 (오류 무시)   |

---

## API 통계

### 통신 량

| API                             | 통신 횟수       | 재시도  | 타임아웃 | 중요도              |
| ------------------------------- | --------------- | ------- | -------- | ------------------- |
| `/api/gaze/click`               | 사용자 클릭마다 | O (3회) | 10초     | 🔴 핵심              |
| `/api/gaze/devices/{user_id}`   | 로그인마다      | X       | 10초     | 🟡 중요              |
| `/api/users/register`           | 로그인마다      | X       | 10초     | 🟡 선택 (백그라운드) |
| `/api/recommendations/feedback` | YES/NO 선택마다 | X       | 10초     | 🟡 중요              |

### 성능 예상

| 항목                       | 시간                             |
| -------------------------- | -------------------------------- |
| 기기 클릭 → AI 응답        | 0.5 ~ 2초 (네트워크에 따라)      |
| 로그인 → 기기 목록 조회    | 0.5 ~ 2초                        |
| AI Server 실패 시 Fallback | 최대 7초 (3회 재시도: 1 + 2 + 4) |

---

## 구현 체크리스트

- [x] 1️⃣ 기기 클릭 이벤트 전송 (`ai_client.py` - `send_device_click()`)
- [x] 2️⃣ 기기 목록 조회 (`ai_client.py` - `get_user_devices()`)
- [x] 3️⃣ 사용자 등록 (`ai_client.py` - `register_user_async()`)
- [x] 4️⃣ 추천 피드백 전송 (`ai_client.py` - `send_recommendation_feedback()`)
- [x] Fallback 응답 처리 (`ai_client.py` - `_get_fallback_response()`)
- [x] 자동 재시도 로직 (`ai_client.py` - 모든 메서드)
- [x] 오류 처리 (`ai_client.py` - try-except)

---

## 참고 자료

- **Backend 구현**: `/edge-module/backend/services/ai_client.py`
- **API 엔드포인트**: `/edge-module/backend/api/devices.py`, `users.py`, `recommendations.py`
- **Frontend 호출**: `/edge-module/frontend/src/pages/HomePage.jsx`, `DeviceCard.jsx`
- **환경 설정**: `/edge-module/backend/core/config.py`

