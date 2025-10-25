# AI-Services / Gateway / Edge-Module 통합 가이드

## 🏗️ 아키텍처 개요

```
┌─────────────────┐
│   Frontend      │
│  (React+Vite)   │
└────────┬────────┘
         │ WebSocket /ws/gaze
         │ HTTP /api/recommendations/feedback
         │
┌────────▼────────────────────────────────────┐
│        Edge-Module Backend (FastAPI)         │
│   (Raspberry Pi, 시선 추적 + 웹소켓)        │
│                                              │
│  - /ws/gaze: 시선 스트림 + 추천 푸시         │
│  - /api/devices/{id}/click: 기기 클릭       │
│  - /api/recommendations/feedback: 피드백    │
└────────┬──────────────────────────────────┬─┘
         │ HTTP /api/gaze/click             │
         │ (device click 이벤트)            │ (향후)
         │                                   │
    ┌────▼────────────────────┐   ┌────────▼─────────┐
    │  AI-Services (AWS EC2)   │   │  Gateway (LG API)  │
    │  (추천 생성)              │   │  (기기 제어)        │
    │                          │   │                   │
    │ POST /api/recommendations│   │ POST /api/lg/control
    │ GET /api/lg/devices      │   │ GET /api/lg/devices
    └────────┬─────────────────┘   └──────┬────────────┘
             │                            │
             └────────────────────────────┘ HTTP
                 (AI Service ↔ Gateway 통신)
```

## 📋 통신 흐름 상세

### 1️⃣ **기기 클릭 이벤트 처리**

```
Frontend (기기 카드 클릭)
    │
    ├─→ POST /api/devices/{device_id}/click
    │   Payload: { user_id, action }
    │
Backend (Edge-Module)
    │
    ├─→ 기기 정보 로컬 조회
    │
    ├─→ POST http://AI_SERVICE/api/gaze/click
    │   Payload: { user_id, device_id, device_name, device_type, action }
    │
    └─→ AI-Services (처리)
        │
        ├─→ Gemini AI로 추천 생성
        ├─→ Gateway에서 기기 상태 조회
        ├─→ 반환: { title, contents, device_control, confirm }
        │
        └─→ Backend로 응답
            │
            └─→ WebSocket으로 Frontend에 푸시
                {
                  type: "recommendation",
                  data: {
                    recommendation_id,
                    title,
                    contents,
                    device_control,
                    source: "device_click"
                  }
                }
```

### 2️⃣ **추천 수락/거절 처리**

```
Frontend (YES/NO 응답)
    │
    ├─→ WebSocket으로 recommendation 메시지 전송
    │   또는 POST /api/recommendations/feedback
    │
Backend
    ├─→ confirm 값 저장
    │
    └─→ YES인 경우:
        ├─→ device_control 정보 확인
        └─→ (향후) 자동 기기 제어 또는 확인
```

## 🔌 API 엔드포인트 정리

### Edge-Module (Backend)

| Method | Endpoint                        | 설명               | Request                     | Response                          |
| ------ | ------------------------------- | ------------------ | --------------------------- | --------------------------------- |
| GET    | `/api/devices`                  | 기기 목록 조회     | -                           | devices[]                         |
| POST   | `/api/devices/{id}/click`       | 기기 클릭 이벤트   | {user_id, action}           | {success, device_id, device_name} |
| POST   | `/api/recommendations/push`     | AI 추천 푸시       | {title, contents}           | {success}                         |
| POST   | `/api/recommendations/feedback` | 추천 피드백        | {rec_id, user_id, accepted} | {success}                         |
| WS     | `/ws/gaze`                      | 시선 + 추천 스트림 | -                           | {type, data}                      |

### AI-Services

| Method | Endpoint               | 설명                       | Request             | Response                           |
| ------ | ---------------------- | -------------------------- | ------------------- | ---------------------------------- |
| POST   | `/api/recommendations` | 추천 생성 및 하드웨어 전송 | {title, contents}   | {message, confirm, device_control} |
| GET    | `/api/lg/devices`      | (Gateway 조회)             | -                   | devices[]                          |
| POST   | `/api/lg/control`      | (Gateway 기기 제어)        | {device_id, action} | control result                     |

### Gateway (LG ThinQ API)

| Method | Endpoint                       | 설명         | Request             | Response       |
| ------ | ------------------------------ | ------------ | ------------------- | -------------- |
| GET    | `/api/lg/devices`              | LG 기기 목록 | -                   | devices[]      |
| GET    | `/api/lg/devices/{id}/profile` | 기기 프로필  | -                   | device profile |
| POST   | `/api/lg/control`              | 기기 제어    | {device_id, action} | {result}       |

## 📊 데이터 형식 정의

### Recommendation 객체

```json
{
  "recommendation_id": "rec_click_1729789234567",
  "title": "에어컨 켤까요?",
  "contents": "현재 온도가 26도이므로 에어컨을 켜시는 것을 추천드립니다.",
  "device_control": {
    "device_id": "aircon_living_room",
    "device_type": "air_conditioner",
    "action": "aircon_on",
    "device_alias": "거실 에어컨"
  },
  "confirm": "PENDING",
  "source": "device_click"
}
```

### Device Click Event

```json
{
  "user_id": "user_001",
  "device_id": "airpurifier_living_room",
  "device_name": "거실 공기청정기",
  "device_type": "airpurifier",
  "action": "turn_on",
  "timestamp": "2024-10-25T14:30:00+09:00"
}
```

### Device Control Info

```json
{
  "device_id": "b403d82eb13e-...",
  "action": "turn_on",
  "command": {
    "airPurifierOperation": {
      "airPurifierOperationMode": "POWER_ON"
    }
  }
}
```

## ✅ 테스트 시나리오

### 시나리오 1: 기기 클릭 → 추천 생성 → 자동 제어

```bash
# 1. Frontend에서 기기 클릭
curl -X POST http://localhost:8000/api/devices/airpurifier_living_room/click \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "action": "turn_on"}'

# 2. Backend가 AI Service 호출
# POST http://34.227.8.172:8000/api/gaze/click
# { user_id, device_id, device_name, device_type, action }

# 3. AI Service가 추천 생성 및 하드웨어 전송
# POST http://localhost:8080/api/recommendations
# { title, contents }

# 4. Frontend가 WebSocket으로 추천 수신
# ws://localhost:8000/ws/gaze
# { type: "recommendation", data: {...} }

# 5. Frontend에서 YES 선택
# POST http://localhost:8000/api/recommendations/feedback
# { recommendation_id, user_id, accepted: true }
```

### 시나리오 2: AI Service의 자동 추천

```bash
# AI Service가 자동으로 추천 생성
# POST http://localhost:8000/api/recommendations/push
# { title, contents, user_id }

# Backend가 Frontend로 WebSocket 푸시
# ws://localhost:8000/ws/gaze
# { type: "recommendation", data: {...} }
```

## 🔧 환경 변수 설정

### Edge-Module (.env)

```env
# AI Service 설정
AI_SERVER_URL=http://34.227.8.172:8000
AI_REQUEST_TIMEOUT=10
AI_MAX_RETRIES=3
```

### AI-Services (.env)

```env
# Gateway 설정
GATEWAY_URL=http://localhost:9000

# 하드웨어 (Edge-Module Backend) 설정
HARDWARE_URL=http://localhost:8000
```

### Gateway (.env)

```env
# (Gateway는 .env 파일 없음, 직접 하드코딩)
# AI_SERVICE_URL = "http://localhost:8000"
```

## 🐛 트러블슈팅

### 1. 기기 클릭 후 추천이 안 나타남

**확인 사항:**
- [ ] WebSocket 연결 확인: `ws://localhost:8000/ws/gaze` 연결 상태
- [ ] AI Service 가용성: `curl http://34.227.8.172:8000/health`
- [ ] Backend 로그 확인: `POST /api/gaze/click` 호출 기록
- [ ] 방화벽/네트워크: Edge-Module ↔ AI Service 통신 가능 여부

**해결:**
```bash
# 1. WebSocket 디버깅
# Frontend 콘솔에서 ws.onmessage 로그 확인

# 2. AI Service 디버그 로그
# docker logs <ai-services-container> | grep "Device click"

# 3. Backend 디버그 로그
# tail -f /path/to/backend.log
```

### 2. AI Service에서 Gateway 연결 실패

**확인 사항:**
- [ ] Gateway 가용성: `curl http://localhost:9000/health`
- [ ] Gateway 기기 목록: `curl http://localhost:9000/api/lg/devices`
- [ ] 환경 변수: `GATEWAY_URL` 올바른지 확인

**해결:**
```bash
# 1. Gateway 상태 확인
curl http://localhost:9000/health

# 2. LG 기기 목록 확인
curl http://localhost:9000/api/lg/devices

# 3. AI Service 환경 변수 확인
docker exec <ai-services-container> printenv | grep GATEWAY
```

### 3. 기기 제어가 작동하지 않음

**확인 사항:**
- [ ] 기기 ID 정확성: 기기 목록에 있는지 확인
- [ ] 액션 값 유효성: "turn_on", "turn_off", "aircon_on" 등 확인
- [ ] Gateway → LG API 연결: LG ThinQ 계정 설정

**해결:**
```bash
# 1. 기기 목록 재조회
curl http://localhost:9000/api/lg/devices

# 2. 특정 기기 상태 확인
curl http://localhost:9000/api/lg/devices/{device_id}/state

# 3. 수동 제어 테스트
curl -X POST http://localhost:9000/api/lg/control \
  -H "Content-Type: application/json" \
  -d '{"device_id": "...", "action": "turn_on"}'
```

## 📝 구현 체크리스트

### Backend (Edge-Module)

- [x] AI Service 추천 API 호출 메서드 추가 (`send_recommendation`)
- [x] Device click 시 AI Service 호출 (`send_device_click`)
- [x] WebSocket으로 추천 브로드캐스트 (`broadcast_recommendation`)
- [x] 추천 피드백 수신 및 처리 (`/api/recommendations/feedback`)
- [ ] 사용자 응답에 따른 자동 기기 제어 (YES 선택 시)
- [ ] 추천 피드백을 데이터베이스에 저장

### Frontend (React)

- [ ] WebSocket에서 추천 메시지 수신 및 표시
- [ ] 사용자 YES/NO 응답 처리
- [ ] 추천 피드백 전송 (`/api/recommendations/feedback`)
- [ ] 기기 제어 완료 후 상태 업데이트

### AI-Services

- [x] 기본 추천 API 엔드포인트 구현
- [x] Gemini AI 기반 추천 생성
- [x] Gateway 연동 (기기 조회, 기기 제어)
- [x] 하드웨어(Backend) 통신
- [ ] 사용자별 맞춤형 추천 로직 고도화
- [ ] 추천 히스토리 저장 및 분석

### Gateway

- [x] LG ThinQ API 통합
- [x] 기기 목록 조회
- [x] 기기 제어 엔드포인트
- [ ] WebSocket 추천 푸시 (선택사항)
- [ ] 기기 상태 실시간 업데이트

## 🚀 배포 가이드

### 로컬 환경 (개발)

```bash
# 1. Edge-Module Backend 시작
cd edge-module/backend
python run.py

# 2. AI-Services 시작
cd ai-services
python main.py

# 3. Gateway 시작 (Docker)
cd gateway
docker-compose up

# 4. Frontend 시작
cd edge-module/frontend
npm run dev
```

### 프로덕션 환경 (AWS)

- Edge-Module: 라즈베리파이 4 (로컬)
- AI-Services: AWS EC2 (34.227.8.172:8000)
- Gateway: AWS EC2 또는 라즈베리파이
- Frontend: 라즈베리파이 또는 별도 서버

**주의:**
- `AI_SERVER_URL` 환경 변수가 올바른지 확인
- CORS 설정 확인
- 방화벽 포트 개방 확인
