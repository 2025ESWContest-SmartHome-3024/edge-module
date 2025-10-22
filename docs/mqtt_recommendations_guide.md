# MQTT 기반 추천 시스템 아키텍처

## 📋 개요

추천 시스템을 **MQTT**로 구현하여 실시간성을 높이고, 기기 제어는 **REST API**로 유지합니다.

```
AI Server (MQTT Publisher)
    ↓ (MQTT gaze/recommendations/receive)
    ├─ title: "에어컨 킬까요?"
    └─ content: "실내 온도가 26도..."

Edge Module (MQTT Subscriber)
    ↓ (WebSocket broadcast)
    
Frontend (WebSocket Listener)
    ↓ (추천 모달 표시)
    ├─ YES 클릭
    └─ NO 클릭

Frontend → Edge (REST POST /api/recommendations/feedback)
    ├─ title: "에어컨 킬까요?"
    └─ confirm: true/false

Edge (MQTT Publisher)
    ↓ (MQTT gaze/recommendations/feedback)

AI Server (MQTT Subscriber)
    ↓ (피드백 수신 및 처리)
```

---

## 🏗️ 구현 구조

### 1️⃣ **Backend: MQTT 클라이언트 (`backend/services/mqtt_client.py`)**

```python
# MQTT 클라이언트 초기화
mqtt_client = MQTTClient()

# MQTT 브로커 연결
mqtt_client.connect()

# 추천 수신 콜백 등록
mqtt_client.on_recommendations_receive(callback_function)

# 피드백 발행
mqtt_client.publish_feedback(title="...", confirm=True)
```

**Topics:**
- `gaze/recommendations/receive`: AI → Edge (추천 수신)
- `gaze/recommendations/feedback`: Edge → AI (피드백 전송)

---

### 2️⃣ **Backend: MQTT 콜백 (`backend/api/main.py`)**

```python
def _on_recommendation_received(recommendation: dict):
    """MQTT에서 추천을 수신했을 때 호출."""
    # 현재 추천 저장
    recommendations.set_current_recommendation(recommendation)
    
    # Frontend에 WebSocket으로 푸시
    await websocket.manager.broadcast({
        "type": "recommendation",
        "title": recommendation.get("title"),
        "content": recommendation.get("content")
    })
```

**Flow:**
1. MQTT에서 추천 메시지 수신
2. 현재 추천 저장 (나중에 조회 가능)
3. 모든 WebSocket 클라이언트에 브로드캐스트

---

### 3️⃣ **Frontend: WebSocket 메시지 처리 (`HomePage.jsx`)**

```jsx
// WebSocket 메시지 수신
ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'recommendation') {
        // 추천 모달 표시
        setRecommendations([{
            title: data.title,
            description: data.content,
            ...
        }])
        setShowRecommendations(true)
    }
}
```

---

### 4️⃣ **Frontend: 피드백 전송 (`RecommendationModal.jsx`)**

```jsx
// MQTT 추천에 대해서만 피드백 전송
if (topRecommendation.id.startsWith('rec_mqtt')) {
    await fetch('/api/recommendations/feedback', {
        method: 'POST',
        body: JSON.stringify({
            title: topRecommendation.title,
            confirm: true  // YES/NO
        })
    })
}
```

---

### 5️⃣ **Backend: 피드백 엔드포인트 (`backend/api/recommendations.py`)**

```python
@router.post("/feedback")
async def submit_recommendation_feedback(feedback: RecommendationFeedbackRequest):
    """Frontend의 피드백을 MQTT로 AI Server에 발행."""
    
    # MQTT로 피드백 발행
    mqtt_client.publish_feedback(
        title=feedback.title,
        confirm=feedback.confirm
    )
    
    return {"message": "[EDGE] 추천 명령어 응답 발행 완료"}
```

---

## 🔧 설정 방법

### 1. `.env` 파일 설정

```bash
# MQTT Broker 설정
MQTT_BROKER=mqtt.example.com    # MQTT 브로커 주소
MQTT_PORT=1883                  # MQTT 포트 (기본값: 1883)
```

### 2. 패키지 설치

```bash
# pyproject.toml에 이미 추가됨
uv pip install paho-mqtt
```

### 3. Backend 시작

```bash
# MQTT 클라이언트가 자동으로 연결됨
cd edge-module
python backend/run.py
```

---

## 📊 Message Format

### AI → Edge (MQTT Publish)

**Topic:** `gaze/recommendations/receive`

```json
{
  "title": "에어컨 킬까요?",
  "content": "실내 온도가 26도까지 올라갔습니다. 에어컨을 켜서 온도를 낮추는 것을 추천합니다."
}
```

### Edge → AI (MQTT Publish)

**Topic:** `gaze/recommendations/feedback`

```json
{
  "title": "에어컨 킬까요?",
  "confirm": true
}
```

---

## 🔄 전체 흐름

```
1️⃣ AI Server가 MQTT로 추천 발행
   └─ Topic: gaze/recommendations/receive
   └─ Payload: {title, content}

2️⃣ Edge가 MQTT 메시지 수신
   └─ _on_recommendation_received() 콜백 실행
   └─ 현재 추천 저장

3️⃣ Edge가 모든 WebSocket 클라이언트에 브로드캐스트
   └─ Message: {type: "recommendation", title, content}

4️⃣ Frontend가 WebSocket에서 추천 수신
   └─ 추천 모달 표시

5️⃣ 사용자가 YES/NO 선택
   └─ Frontend → Edge REST POST
   └─ Body: {title, confirm}

6️⃣ Edge가 피드백을 MQTT로 AI Server에 발행
   └─ Topic: gaze/recommendations/feedback
   └─ Payload: {title, confirm}

7️⃣ AI Server가 MQTT에서 피드백 수신
   └─ 확인 완료 ✅
```

---

## 📁 파일 구조

```
backend/
├── api/
│   ├── main.py              # MQTT 클라이언트 초기화, 콜백 등록
│   └── recommendations.py   # 피드백 엔드포인트
└── services/
    └── mqtt_client.py       # MQTT 클라이언트 구현

frontend/
└── src/
    ├── pages/
    │   └── HomePage.jsx     # WebSocket에서 추천 수신
    └── components/
        └── RecommendationModal.jsx  # 피드백 전송
```

---

## ✅ 테스트 방법

### MQTT Broker가 없는 경우

`.env`에서 `MQTT_BROKER`를 비워두면:

```bash
MQTT_BROKER=
```

MQTT 클라이언트가 자동으로 비활성화되고, 경고만 기록됩니다.

### MQTT Broker가 있는 경우

`test_mqtt_recommendations.py`로 테스트:

```bash
cd examples/
python test_mqtt_recommendations.py
```

---

## 🚀 장점

| 항목            | REST      | MQTT              |
| --------------- | --------- | ----------------- |
| **실시간성**    | ~200ms    | ~100ms            |
| **지연**        | 높음      | 낮음              |
| **데이터 손실** | 없음      | QoS 선택 가능     |
| **확장성**      | 중간      | 높음              |
| **여러 구독자** | 폴링 필요 | 자동 브로드캐스트 |

---

## 📝 참고사항

1. **기기 제어는 REST API 유지**
   - 요청-응답 구조 필요 (상태 확인)
   - HTTP Status Code로 명확한 에러 처리
   - 테스트 용이 (Postman, curl)

2. **추천은 MQTT 사용**
   - 실시간 push 가능
   - 경량 프로토콜
   - 한 메시지로 여러 클라이언트에 전송

3. **Mock 데이터 제거됨**
   - 실제 AI Server MQTT 메시지 사용
   - 추천은 이제 MQTT로만 수신 가능

---

## 🔗 관련 파일

- `backend/services/mqtt_client.py` - MQTT 클라이언트 구현
- `backend/api/main.py` - MQTT 초기화 및 콜백
- `backend/api/recommendations.py` - 피드백 엔드포인트
- `frontend/src/pages/HomePage.jsx` - WebSocket 추천 수신
- `frontend/src/components/RecommendationModal.jsx` - 피드백 전송
