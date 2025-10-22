# AI Server API 변경 영향도 종합 분석

## 📋 요약

백엔드의 모든 파일을 분석하여 AI Server API 변경 시 **어떤 파일이 변경되고 어떤 파일은 변경되지 않는지** 명확히 분류했습니다.

---

## 🔴 API 변경 영향 있는 파일 (변경 필요)

### 1. **ai_client.py** - ⭐⭐⭐⭐⭐ 높음

| 항목            | 상태   | 설명                                   |
| --------------- | ------ | -------------------------------------- |
| **API 호출**    | ✅ 있음 | 4개 메서드에서 AI Server 호출          |
| **영향도**      | 🔴 높음 | URL, 요청/응답 데이터 변경 가능성 높음 |
| **수정 난이도** | 🟡 중간 | 4개 메서드만 수정하면 됨               |

**AI Server 호출:**
```python
# 1. send_device_click()
url = f"{self.base_url}/api/gaze/click"

# 2. get_user_devices()
url = f"{self.base_url}/api/gaze/devices/{user_id}"

# 3. register_user_async()
url = f"{self.base_url}/api/users/register"

# 4. send_recommendation_feedback()
url = f"{self.base_url}/api/recommendations/feedback"
```

**변경 시나리오:**
```
변경 전: POST /api/gaze/click
변경 후: POST /v2/events/click
결과:   ai_client.py의 1줄 수정
```

**수정 범위:**
```python
# 변경 전
async def send_device_click(self, ...):
    url = f"{self.base_url}/api/gaze/click"  # ← 이 줄

# 변경 후
async def send_device_click(self, ...):
    url = f"{self.base_url}/v2/events/click"  # ← 변경
```

---

### 2. **devices.py** - 🟡 중간

| 항목              | 상태   | 설명                       |
| ----------------- | ------ | -------------------------- |
| **직접 API 호출** | ❌ 없음 | ai_client을 통해 간접 호출 |
| **영향도**        | 🟡 중간 | ai_client 변경에 영향 받음 |
| **수정 난이도**   | 🟢 쉬움 | 데이터 처리 로직만 조정    |

**ai_client 호출:**
```python
# get_devices()
devices = await ai_client.get_user_devices(user_id)
# → ai_client가 반환하는 데이터 형식이 변하면 영향

# handle_device_click()
ai_response = await ai_client.send_device_click(gaze_click_request)
# → ai_client가 반환하는 응답 형식이 변하면 영향
```

**변경 시나리오:**
```
AI Server 응답 형식 변경:
  {"devices": [...]}  →  {"data": [...]}
  
영향:
  devices.py의 데이터 처리 로직 수정 필요
  (현재 코드는 이미 유연하게 처리 중)
```

**현재 유연한 처리:**
```python
if "devices" in result:
    devices = result.get("devices", [])
elif "data" in result:
    devices = result.get("data", [])
elif isinstance(result, list):
    devices = result
# → 이미 여러 형식을 지원하므로 많은 변경 불필요
```

---

### 3. **recommendations.py** - 🟡 중간

| 항목              | 상태   | 설명                       |
| ----------------- | ------ | -------------------------- |
| **직접 API 호출** | ❌ 없음 | ai_client을 통해 간접 호출 |
| **영향도**        | 🟡 중간 | ai_client 변경에 영향 받음 |
| **수정 난이도**   | 🟢 쉬움 | 데이터 구조 일치만 확인    |

**ai_client 호출:**
```python
# send_feedback_to_ai_server()
result = await ai_client.send_recommendation_feedback(
    recommendation_id=recommendation_id,
    user_id=user_id,
    accepted=accepted
)

# submit_user_feedback()
result = await ai_client.send_recommendation_feedback(
    recommendation_id=feedback.recommendation_id,
    user_id=feedback.user_id,
    accepted=feedback.accepted
)
```

**변경 시나리오:**
```
AI Server 피드백 API 변경:
  - 요청 형식: accepted → user_choice (YES/NO)
  - 응답 형식: success → status

영향:
  recommendations.py의 요청/응답 처리 로직 수정
```

**현재 처리:**
```python
# 요청
result = await ai_client.send_recommendation_feedback(
    recommendation_id=recommendation_id,
    user_id=user_id,
    accepted=accepted  # ← 이 인터페이스 유지 필요
)

# 응답
if result.get("success", True):  # ← "success" 키 필요
    logger.info("✅ AI Server 피드백 전송 완료")
```

---

### 4. **users.py** - 🟡 중간

| 항목              | 상태   | 설명                       |
| ----------------- | ------ | -------------------------- |
| **직접 API 호출** | ❌ 없음 | ai_client을 통해 간접 호출 |
| **영향도**        | 🟡 중간 | ai_client 변경에 영향 받음 |
| **수정 난이도**   | 🟢 쉬움 | 사용자 등록 로직만 조정    |

**ai_client 호출:**
```python
# login_user()
asyncio.create_task(
    ai_client.register_user_async(
        user_id=str(user_id),
        username=username,
        has_calibration=has_calibration
    )
)
```

**변경 시나리오:**
```
AI Server 사용자 등록 API 변경:
  - 요청 필드: user_id, username → userId, userName
  - 응답 필드: success → status

영향:
  users.py는 영향 최소 (비동기 백그라운드 작업이라 오류 무시)
```

---

## 🟢 API 변경 영향 없는 파일 (변경 불필요)

### 1. **database.py** - ✅ 없음

| 항목               | 상태   | 설명          |
| ------------------ | ------ | ------------- |
| **외부 API 호출**  | ❌ 없음 | SQLite만 사용 |
| **AI Server 의존** | ❌ 없음 | 완전 독립     |
| **영향도**         | 🟢 없음 | 0%            |

**코드:**
```python
# SQLite 연산만 수행
with sqlite3.connect(self.db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(...)  # ← 로컬 DB만 접근
    conn.commit()

# AI Server 호출 없음 ✅
```

**결론:**
```
✅ database.py는 AI Server 변경에 영향 받지 않음
```

---

### 2. **gaze_tracker.py** - ✅ 없음

| 항목               | 상태   | 설명                      |
| ------------------ | ------ | ------------------------- |
| **외부 API 호출**  | ❌ 없음 | 카메라 + 로컬 모델만 사용 |
| **AI Server 의존** | ❌ 없음 | 완전 독립                 |
| **영향도**         | 🟢 없음 | 0%                        |

**코드:**
```python
# 시선 추적 연산만 수행
features, blink_detected = self.gaze_estimator.extract_features(frame)
gaze_point = self.gaze_estimator.predict(np.array([features]))[0]
x_pred, y_pred = self.smoother.step(x, y)

# AI Server 호출 없음 ✅
```

**결론:**
```
✅ gaze_tracker.py는 AI Server 변경에 영향 받지 않음
```

---

### 3. **calibration.py** - ✅ 없음

| 항목               | 상태   | 설명                      |
| ------------------ | ------ | ------------------------- |
| **외부 API 호출**  | ❌ 없음 | 로컬 파일 I/O + 모델 학습 |
| **AI Server 의존** | ❌ 없음 | 완전 독립                 |
| **영향도**         | 🟢 없음 | 0%                        |

**코드:**
```python
# 로컬 캘리브레이션 처리만 수행
session.collected_features  # ← 로컬 저장
session.collected_targets   # ← 로컬 저장

# Ridge 모델 학습 (로컬)
model.fit(X, y)  # ← 로컬 연산

# AI Server 호출 없음 ✅
```

**결론:**
```
✅ calibration.py는 AI Server 변경에 영향 받지 않음
```

---

### 4. **settings.py** - ✅ 없음

| 항목               | 상태   | 설명             |
| ------------------ | ------ | ---------------- |
| **외부 API 호출**  | ❌ 없음 | 필터 상태 조회만 |
| **AI Server 의존** | ❌ 없음 | 로컬 상태만 반환 |
| **영향도**         | 🟢 없음 | 0%               |

**코드:**
```python
# 로컬 필터 상태만 반환
filter_method = gaze_tracker.filter_method
return FilterStatusResponse(
    filter_method=filter_method,
    active=gaze_tracker.smoother is not None
)

# AI Server 호출 없음 ✅
```

**결론:**
```
✅ settings.py는 AI Server 변경에 영향 받지 않음
```

---

### 5. **websocket.py** - ✅ 없음

| 항목               | 상태   | 설명                       |
| ------------------ | ------ | -------------------------- |
| **외부 API 호출**  | ❌ 없음 | WebSocket 스트리밍만       |
| **AI Server 의존** | ❌ 없음 | 로컬 시선 추적 결과만 전송 |
| **영향도**         | 🟢 없음 | 0%                         |

**코드:**
```python
# 로컬 시선 데이터만 스트리밍
state = gaze_tracker.get_current_state()
message = {
    "gaze": state["gaze"],
    "blink": state["blink"]
}
await websocket.send_json(message)

# AI Server 호출 없음 ✅
```

**결론:**
```
✅ websocket.py는 AI Server 변경에 영향 받지 않음
```

---

### 6. **config.py** - ✅ 없음

| 항목               | 상태   | 설명                             |
| ------------------ | ------ | -------------------------------- |
| **외부 API 호출**  | ❌ 없음 | 설정 값만 정의                   |
| **AI Server 의존** | ❌ 없음 | 환경변수 읽기만                  |
| **영향도**         | 🟢 없음 | 0% (주소 변경은 환경변수로 처리) |

**코드:**
```python
class Settings(BaseSettings):
    ai_server_url: str = os.getenv("AI_SERVER_URL", "http://34.227.8.172:8000")
    # ← 환경변수로 관리되므로 코드 변경 불필요
```

**결론:**
```
✅ config.py는 코드 변경 불필요 (환경변수로 관리)
```

---

### 7. **main.py** - ✅ 없음

| 항목               | 상태   | 설명                  |
| ------------------ | ------ | --------------------- |
| **외부 API 호출**  | ❌ 없음 | 라우터 등록만         |
| **AI Server 의존** | ❌ 없음 | gaze_tracker 초기화만 |
| **영향도**         | 🟢 없음 | 0%                    |

**코드:**
```python
# 라우터 포함
app.include_router(devices.router, prefix="/api/devices")
app.include_router(recommendations.router, prefix="/api/recommendations")

# 시선 추적기 초기화
gaze_tracker = WebGazeTracker(...)

# AI Server 호출 없음 ✅
```

**결론:**
```
✅ main.py는 AI Server 변경에 영향 받지 않음
```

---

## 📊 전체 영향도 분석 표

| 파일                   | 직접 호출 | 간접 호출   | AI Server 영향    | 수정 필요 | 난이도 |
| ---------------------- | --------- | ----------- | ----------------- | --------- | ------ |
| **ai_client.py**       | ✅ 4곳     | -           | 🔴 매우 높음       | ✅ 필요    | 🟡 중간 |
| **devices.py**         | ❌         | ✅ ai_client | 🟡 중간            | ⚠️ 가능    | 🟢 쉬움 |
| **recommendations.py** | ❌         | ✅ ai_client | 🟡 중간            | ⚠️ 가능    | 🟢 쉬움 |
| **users.py**           | ❌         | ✅ ai_client | 🟡 중간            | ⚠️ 가능    | 🟢 쉬움 |
| **database.py**        | ❌         | ❌           | 🟢 없음            | ❌ 불필요  | N/A    |
| **gaze_tracker.py**    | ❌         | ❌           | 🟢 없음            | ❌ 불필요  | N/A    |
| **calibration.py**     | ❌         | ❌           | 🟢 없음            | ❌ 불필요  | N/A    |
| **settings.py**        | ❌         | ❌           | 🟢 없음            | ❌ 불필요  | N/A    |
| **websocket.py**       | ❌         | ❌           | 🟢 없음            | ❌ 불필요  | N/A    |
| **config.py**          | ❌         | ❌           | 🟢 없음 (환경변수) | ❌ 불필요  | N/A    |
| **main.py**            | ❌         | ❌           | 🟢 없음            | ❌ 불필요  | N/A    |

---

## 📁 Database 구조

### SQLite 데이터베이스: `~/.gazehome/calibrations/gazehome.db`

#### 테이블 1: **users** (사용자 관리)

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 자동 증가 ID
    username TEXT UNIQUE NOT NULL,              -- 사용자명 (고유)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 생성 시간
    last_login TIMESTAMP                        -- 마지막 로그인 시간
);
```

**용도:**
- 사용자 식별
- 로그인 기록
- 사용자별 캘리브레이션 추적

**예시 데이터:**
```
id | username | created_at           | last_login
---+----------+----------------------+----------------------
1  | alice    | 2024-10-21 10:00:00 | 2024-10-22 14:30:00
2  | bob      | 2024-10-20 09:15:00 | 2024-10-22 09:00:00
```

**AI Server API 변경 영향:** ❌ 없음 (로컬 DB)

---

#### 테이블 2: **calibrations** (캘리브레이션 기록)

```sql
CREATE TABLE IF NOT EXISTS calibrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 자동 증가 ID
    user_id INTEGER NOT NULL,                  -- 사용자 ID (Foreign Key)
    calibration_file TEXT NOT NULL,            -- 캘리브레이션 파일명 (*.pkl)
    screen_width INTEGER,                      -- 화면 너비
    screen_height INTEGER,                     -- 화면 높이
    method TEXT,                               -- 캘리브레이션 방식 (9-point)
    samples_count INTEGER,                     -- 수집된 샘플 수
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 생성 시간
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**용도:**
- 사용자별 캘리브레이션 이력 관리
- 최신 캘리브레이션 파일 추적
- 캘리브레이션 통계

**예시 데이터:**
```
id | user_id | calibration_file | screen_width | screen_height | method     | samples_count | created_at
---+---------+------------------+--------------+---------------+------------+---------------+---------------------
1  | 1       | alice.pkl        | 1024         | 600           | nine_point | 45            | 2024-10-21 11:00:00
2  | 1       | alice_v2.pkl     | 1024         | 600           | nine_point | 48            | 2024-10-22 14:00:00
3  | 2       | bob.pkl          | 1024         | 600           | nine_point | 42            | 2024-10-21 10:30:00
```

**AI Server API 변경 영향:** ❌ 없음 (로컬 DB)

---

#### 테이블 3: **devices** (기기 목록 캐시)

```sql
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 자동 증가 ID
    user_id INTEGER NOT NULL,                  -- 사용자 ID (Foreign Key)
    device_id TEXT NOT NULL,                   -- AI Server의 기기 ID
    device_name TEXT NOT NULL,                 -- 기기 이름
    device_type TEXT,                          -- 기기 타입
    capabilities TEXT,                         -- 기기 기능 (JSON 배열)
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 마지막 동기화 시간
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, device_id)                -- 사용자당 기기는 유일
);
```

**용도:**
- AI Server에서 조회한 기기 목록 로컬 캐싱
- 오프라인 모드 지원 (AI Server 다운 시에도 기기 조회 가능)
- 기기별 기능 저장

**예시 데이터:**
```
id | user_id | device_id | device_name  | device_type    | capabilities                            | last_synced
---+---------+-----------+--------------+----------------+----------------------------------------+---------------------
1  | 1       | ac_001    | 거실 에어컨  | airconditioner | ["turn_on","turn_off","set_temp"]      | 2024-10-22 14:30:00
2  | 1       | light_01  | 거실 조명    | light          | ["turn_on","turn_off","brightness"]    | 2024-10-22 14:30:00
3  | 2       | ac_002    | 침실 에어컨  | airconditioner | ["turn_on","turn_off","set_temp"]      | 2024-10-22 14:00:00
```

**AI Server API 변경 영향:** 
```
⚠️ 간접 영향 (API 응답 형식 변경 시)

변경 전 응답: {"device_id": "ac_001", "device_name": "..."}
변경 후 응답: {"id": "ac_001", "name": "..."}

영향: devices.py의 데이터 처리 로직 수정 필요
      → database.py 자체는 변경 불필요
```

---

#### 테이블 4: **login_history** (로그인 기록)

```sql
CREATE TABLE IF NOT EXISTS login_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 자동 증가 ID
    user_id INTEGER NOT NULL,                  -- 사용자 ID (Foreign Key)
    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 로그인 시간
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**용도:**
- 사용자 로그인 이력 추적
- 사용 통계 생성
- 사용자별 활동도 분석

**예시 데이터:**
```
id | user_id | login_at
---+---------+---------------------
1  | 1       | 2024-10-22 09:00:00
2  | 1       | 2024-10-22 14:30:00
3  | 2       | 2024-10-22 14:00:00
4  | 1       | 2024-10-23 08:30:00
```

**AI Server API 변경 영향:** ❌ 없음 (로컬 DB)

---

## 🔗 데이터베이스 관계도

```
┌─────────────────────────────────────────────────────────┐
│                     USERS (사용자)                      │
│  id(PK) │ username │ created_at │ last_login            │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Foreign Key (user_id)
                     │
         ┌───────────┴───────────┬──────────────┐
         │                       │              │
┌────────▼──────────────┐  ┌─────▼──────────────┐  ┌─────▼──────────────┐
│  CALIBRATIONS         │  │  DEVICES           │  │  LOGIN_HISTORY     │
│  (캘리브레이션)       │  │  (기기 목록 캐시)  │  │  (로그인 기록)     │
│────────────────────┤  │────────────────────┤  │────────────────────┤
│ id(PK)             │  │ id(PK)             │  │ id(PK)             │
│ user_id(FK)        │  │ user_id(FK)        │  │ user_id(FK)        │
│ calibration_file   │  │ device_id          │  │ login_at           │
│ screen_width       │  │ device_name        │  │                    │
│ screen_height      │  │ device_type        │  │                    │
│ method             │  │ capabilities(JSON) │  │                    │
│ samples_count      │  │ last_synced        │  │                    │
│ created_at         │  │                    │  │                    │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```

---

## 📝 Database 사용 패턴

### 사용자 로그인 흐름

```python
# 1. 사용자 로그인
username = "alice"

# 2. 사용자 ID 가져오기/생성
user_id = db.get_or_create_user(username)
# → users 테이블 조회/삽입
# → user_id = 1

# 3. 로그인 기록
db.record_login(username)
# → login_history 테이블에 레코드 삽입

# 4. 캘리브레이션 확인
has_calibration = db.has_calibration(username)
calibration_file = db.get_latest_calibration(username)
# → calibrations 테이블 조회
# → has_calibration = True, calibration_file = "alice.pkl"

# 5. 기기 동기화 (AI Server에서 가져온 기기)
devices = [{"device_id": "ac_001", "device_name": "에어컨", ...}]
db.sync_devices(user_id, devices)
# → devices 테이블에 삽입/업데이트

# 6. 기기 조회 (오프라인 시에도 사용 가능)
local_devices = db.get_user_devices(user_id)
# → devices 테이블 조회
```

---

## 🎯 AI Server API 변경에 따른 Database 영향도

### 시나리오 1: 기기 API 응답 형식 변경

**변경 전:**
```json
{
  "devices": [
    {
      "device_id": "ac_001",
      "device_name": "에어컨",
      "device_type": "airconditioner",
      "capabilities": ["turn_on", "turn_off"]
    }
  ]
}
```

**변경 후:**
```json
{
  "data": [
    {
      "id": "ac_001",
      "name": "에어컨",
      "type": "airconditioner",
      "features": ["turn_on", "turn_off"]
    }
  ]
}
```

**영향:**

| 계층           | 파일           | 변경 필요 | 설명                                          |
| -------------- | -------------- | --------- | --------------------------------------------- |
| AI Server 통신 | `ai_client.py` | ✅ 필요    | API 응답 형식에 맞게 데이터 변환              |
| API 계층       | `devices.py`   | ⚠️ 가능    | ai_client에서 일관된 형식으로 변환하면 불필요 |
| 데이터베이스   | `database.py`  | ❌ 불필요  | 입력 데이터만 같은 형식이면 OK                |

**데이터베이스 스키마 변경:** ❌ 없음 (devices 테이블 구조 유지)

---

### 시나리오 2: 새로운 필드 추가

**변경 전:**
```json
{
  "device_id": "ac_001",
  "device_name": "에어컨",
  "device_type": "airconditioner"
}
```

**변경 후:**
```json
{
  "device_id": "ac_001",
  "device_name": "에어컨",
  "device_type": "airconditioner",
  "manufacturer": "LG",      // ← 새 필드
  "model": "AC-001"          // ← 새 필드
}
```

**영향:**

| 계층           | 변경 필요                              |
| -------------- | -------------------------------------- |
| `ai_client.py` | ❌ 불필요 (추가 필드는 무시)            |
| `devices.py`   | ❌ 불필요 (필드는 통과)                 |
| `database.py`  | ⚠️ 가능 (capabilities JSON에 저장 가능) |

**데이터베이스 스키마 변경:** ❌ 불필요 (JSON 필드에 저장 가능)

---

### 시나리오 3: 기기 데이터 구조 크게 변경

**변경 전:**
```json
{
  "device_id": "ac_001",
  "device_name": "에어컨",
  "capabilities": ["turn_on", "turn_off"]
}
```

**변경 후:**
```json
{
  "device_id": "ac_001",
  "device_name": "에어컨",
  "properties": {
    "is_connected": true,
    "battery": 85,
    "signal_strength": -45
  }
}
```

**영향:**

| 계층           | 변경 필요 | 이유                          |
| -------------- | --------- | ----------------------------- |
| `ai_client.py` | ✅ 필요    | API 응답 파싱 수정            |
| `devices.py`   | ✅ 필요    | 새로운 필드 처리              |
| `database.py`  | ❌ 불필요  | JSON 필드에 새 구조 저장 가능 |

**데이터베이스 스키마 변경:** ❌ 불필요 (capabilities 필드를 properties로 활용 가능)

---

## 🎓 Database 설계 특징

### ✅ 유연성

```sql
-- capabilities 필드가 JSON이므로 
-- 다양한 기기 기능을 저장 가능
capabilities TEXT  -- JSON 배열로 저장

-- 예시:
-- ["turn_on", "turn_off", "set_temperature"]
-- ["turn_on", "turn_off", "brightness", "color"]
-- ["open", "close", "lock", "unlock"]
```

### ✅ 확장성

```sql
-- 새로운 필드가 필요하면 마이그레이션 가능
ALTER TABLE devices ADD COLUMN manufacturer TEXT;
ALTER TABLE devices ADD COLUMN last_command_at TIMESTAMP;
```

### ✅ 독립성

```python
# Database는 AI Server와 완전히 독립적
# AI Server가 다운되어도 로컬 DB는 계속 작동
db.get_user_devices(user_id)  # ← 캐시된 데이터 반환
```

---

## 📊 종합 결론

### AI Server API 변경 영향도 정리

```
┌────────────────────────────────────────────────────────────┐
│            AI Server API 변경                              │
└────────────────────┬───────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
   🔴 변경 필요             🟢 변경 불필요
   (4개 파일)              (7개 파일)
   
   ┌─────────────────┐    ┌──────────────────┐
   │ ai_client.py    │    │ database.py      │
   │ devices.py      │    │ gaze_tracker.py  │
   │ recommendations.│    │ calibration.py   │
   │ users.py        │    │ settings.py      │
   │                 │    │ websocket.py     │
   │                 │    │ config.py        │
   │                 │    │ main.py          │
   └─────────────────┘    └──────────────────┘

Database 영향도:
────────────────
❌ database.py 코드 변경 불필요
❌ database.py 스키마 변경 불필요
✅ 로컬 DB는 AI Server 변경에 100% 독립적
```

---

## 📌 최종 요약

| 항목                         | 현황                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------------------------------- |
| **AI Server 직접 호출 파일** | ai_client.py (1개)                                                                                |
| **AI Server 간접 호출 파일** | devices.py, recommendations.py, users.py (3개)                                                    |
| **AI Server 비의존 파일**    | database.py, gaze_tracker.py, calibration.py, settings.py, websocket.py, config.py, main.py (7개) |
| **Database 변경 필요**       | ❌ 없음                                                                                            |
| **Database 스키마 변경**     | ❌ 없음                                                                                            |
| **Database 영향도**          | 🟢 0%                                                                                              |

**결론:**
```
✅ AI Server API 변경 → ai_client.py 수정
⚠️ 간접적으로 devices.py, recommendations.py, users.py 가능 수정
❌ database.py는 절대 변경 불필요
✅ 데이터베이스 스키마는 변경 불필요
```
