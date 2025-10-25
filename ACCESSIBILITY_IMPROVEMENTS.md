# GazeHome 접근성 개선 방안

> **프로젝트 개요**: 시선(Eye Gaze)으로만 스마트홈 기기를 제어하는 거동이 불편한 사용자를 위한 시스템

## 🎯 현황 분석

현재 GazeHome은 **기본적인 시선 추적 및 제어 기능**을 갖추고 있지만, 
**실제 거동 불편 사용자의 다양한 요구사항**을 충족시키기 위해 개선이 필요합니다.

---

## 📋 개선사항 (우선순위별)

### ⭐⭐⭐ **필수 개선 (Priority 1: 접근성 핵심)**

#### 1. **시선 위치 정확도 개선**

**현황:**
- Ridge 모델 사용 (선형 회귀)
- 고정 캘리브레이션 포인트만 지원 (5/9포인트)
- 얼굴 회전/각도 변화에 민감

**개선안:**
```python
# 1) 적응형 캘리브레이션 (사용자가 자주 보는 영역 중심)
class AdaptiveCalibration:
    """
    사용자 거동에 맞는 동적 캘리브레이션
    - 실제 사용 패턴 기반 캘리브레이션 포인트 재조정
    - 하루 중 조명/시간 변화 대응
    - 머리 기울임각 보정 (Head Pose Estimation)
    """
    def recalibrate_on_drift(self):
        """시선 드리프트 감지 시 자동 재캘리브레이션"""
        pass
```

```python
# 2) 머리 자세 보정 (Head Pose + Gaze)
# 현재: gaze.py에서 yaw, pitch, roll 계산하지만 활용 안 함
features = np.concatenate([features, [yaw, pitch, roll]])  # 이미 포함됨!

# 활용 방안:
class HeadPoseCompensation:
    def predict_gaze_with_head_pose(self, features, head_pose):
        """
        머리 기울임을 고려한 시선 예측
        - 사용자가 누워있거나 옆으로 누워있을 때 정확도 향상
        - 휠체어 사용자의 다양한 자세 대응
        """
        yaw, pitch, roll = head_pose
        # head_pose 정규화하여 모델 입력에 포함
        pass
```

**파일 수정:**
- `edge-module/model/models/ridge.py` - 머리 자세 가중치 추가
- `edge-module/backend/core/gaze_tracker.py` - 어댑티브 캘리브레이션 로직

**효과:**
- ✅ 정확도 +15-25% (거동 불편 사용자의 다양한 자세 대응)
- ✅ 캘리브레이션 시간 단축 (자동 재조정)

---

#### 2. **긴급 상황 대응 기능**

**현황:**
- 눈깜빡임으로만 제어 (좋음)
- **헬프 신호/긴급 모드 없음** ❌

**개선안:**
```jsx
// frontend/src/components/EmergencyMode.jsx
function EmergencyMode() {
    const [isEmergencyMode, setIsEmergencyMode] = useState(false);
    
    // 방법 1: 연속 깜빡임 (5회 이상, 2초 내) → 긴급 모드
    if (blink_count >= 5 && duration <= 2000) {
        setIsEmergencyMode(true);
        // 알림 전송
        notify({
            type: 'emergency',
            user_id: currentUser,
            timestamp: Date.now(),
            location: 'home'
        });
    }
    
    // 방법 2: 깜빡임 안 함 (30초+) → 자동 SOS
    // (사용자가 응답 불가 상태)
}
```

**백엔드 로직:**
```python
# backend/api/emergency.py
@router.post("/emergency")
async def trigger_emergency():
    """긴급 모드 활성화"""
    # 1. 보호자에게 알림 전송 (Notification API)
    # 2. 음성 알림 시작 (TTS)
    # 3. 병원/경찰 연락 정보 표시
    pass

@router.get("/emergency/help-options")
async def get_help_options():
    """
    긴급 상황 옵션:
    - 보호자 호출
    - 음성으로 "도움말" 읽어주기
    - 응급실 연락처
    - 침대 콜벨 활성화
    """
    return {
        "options": [
            {"label": "📞 보호자 전화", "action": "call_guardian"},
            {"label": "🚑 응급차 호출", "action": "call_emergency"},
            {"label": "🔊 도움 요청", "action": "voice_help"},
        ]
    }
```

**파일 생성:**
- `edge-module/backend/api/emergency.py` (새로운 엔드포인트)
- `edge-module/frontend/src/components/EmergencyMode.jsx` (새로운 컴포넌트)

**효과:**
- ✅ 위급상황 대응 시간 단축
- ✅ 사용자 안전 보장

---

#### 3. **음성 피드백 (TTS) 및 오디오 안내**

**현황:**
- 시각적 피드백만 있음
- 음성 안내 없음 ❌

**개선안:**
```jsx
// frontend/src/hooks/useSpeechFeedback.js
function useSpeechFeedback() {
    const speak = (text, options = {}) => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ko-KR';
        utterance.rate = options.rate || 1;
        utterance.volume = options.volume || 1;
        
        window.speechSynthesis.speak(utterance);
    };
    
    return { speak };
}

// 사용 예:
// 1. 페이지 진입: "홈 화면에 접속했습니다"
// 2. 기기 하이라이트: "거실 에어컨이 선택되었습니다"
// 3. 제어 완료: "에어컨을 켰습니다"
// 4. 오류: "시선 인식이 불가합니다. 다시 보정해주세요"
```

**설정 패널:**
```jsx
// frontend/src/pages/SettingsPage.jsx (새로운 페이지)
function SettingsPage() {
    const [ttsEnabled, setTtsEnabled] = useState(true);
    const [ttsRate, setTtsRate] = useState(1);  // 말하기 속도
    const [ttsVolume, setTtsVolume] = useState(1);  // 음량
    
    return (
        <div className="settings-panel">
            <h3>음성 안내</h3>
            <Toggle label="음성 피드백 활성화" />
            <Slider label="말하기 속도" min={0.5} max={2} step={0.1} />
            <Slider label="음량" min={0} max={1} step={0.1} />
            <Button onClick={() => speak("테스트")}>테스트 음성</Button>
        </div>
    );
}
```

**파일 생성/수정:**
- `edge-module/frontend/src/hooks/useSpeechFeedback.js` (새로운 훅)
- `edge-module/frontend/src/pages/SettingsPage.jsx` (새로운 페이지)
- `edge-module/frontend/src/pages/HomePage.jsx` (음성 피드백 통합)

**효과:**
- ✅ 시각 장애 사용자도 사용 가능
- ✅ 음성 가이드로 학습곡선 단축

---

#### 4. **호버 시간 (Dwell Time) 커스터마이징**

**현황:**
```jsx
// HomePage.jsx에서 하드코딩된 값
const DWELL_TIME = 2000;  // 2초로 고정
```

**문제점:**
- 모든 사용자에게 동일 (비효율적)
- 손 떨림 있는 사용자: 2초로도 부족
- 빠른 반응 사용자: 2초는 너무 김

**개선안:**
```jsx
// frontend/src/contexts/UserPreferencesContext.jsx
const UserPreferencesContext = createContext();

function useUserPreferences() {
    const [preferences, setPreferences] = useState({
        dwellTime: 2000,           // 기본값
        debounceTime: 500,         // 떨림 필터
        gazeSmoothing: 'medium',   // low/medium/high
        confirmationMode: 'dwell', // dwell/double-blink/voice
    });
    
    // 사용자 행동 분석 후 자동 조정
    const autoAdjustDwellTime = (clickAccuracy) => {
        if (clickAccuracy < 0.8) {
            setPreferences(prev => ({
                ...prev,
                dwellTime: Math.min(3500, prev.dwellTime + 250)
            }));
        }
    };
    
    return { preferences, autoAdjustDwellTime };
}
```

**파일 수정:**
- `edge-module/frontend/src/contexts/UserPreferencesContext.jsx` (새로운 컨텍스트)
- `edge-module/frontend/src/pages/SettingsPage.jsx` (설정 UI)
- `edge-module/frontend/src/components/DeviceCard.jsx` (동적 dwell time 적용)

**효과:**
- ✅ 사용자별 맞춤 경험
- ✅ 학습 알고리즘으로 시간 경과에 따라 개선

---

### ⭐⭐ **권장 개선 (Priority 2: 사용자 경험 향상)**

#### 5. **시선 인식 가능성 표시 및 재보정 유도**

**현황:**
```jsx
// GazeCursor에서 calibrated 상태만 표시
const [calibrated, setCalibrated] = useState(true);  // true/false만 있음
```

**개선안:**
```jsx
// backend/api/settings.py
@router.get("/tracker-info")
async def get_tracker_info():
    """
    현재 응답:
    - calibrated: true/false (이진)
    
    개선: 상세 정보 추가
    """
    return {
        "calibrated": state["calibrated"],
        "quality_score": 0.95,        # 0-1 범위 (정확도)
        "face_detected": True,        # 얼굴 감지 여부
        "face_position": "center",    # center/left/right/top/bottom
        "lighting_quality": "good",   # poor/fair/good (조명 품질)
        "head_pose": {                # 머리 자세
            "yaw": 5.2,
            "pitch": -2.1,
            "roll": 1.3
        },
        "last_calibration": "2025-10-23T10:00:00Z",
        "recalibration_needed": False  # 자동 감지
    }
```

**프론트엔드 피드백:**
```jsx
function CalibratonStatus() {
    if (quality_score < 0.7) {
        return (
            <Alert severity="warning">
                시선 인식 정확도가 낮습니다 (품질: {quality_score}%)
                {lighting_quality === 'poor' && "💡 조명을 밝혀주세요"}
                {face_position === 'left' && "📍 정면을 보고 있어주세요"}
                <Button onClick={recalibrate}>재보정 시작</Button>
            </Alert>
        );
    }
}
```

**파일 수정:**
- `edge-module/backend/api/settings.py` (상세 정보 추가)
- `edge-module/frontend/src/components/CalibrationStatus.jsx` (새로운 컴포넌트)

---

#### 6. **기기 그룹 제어 및 매크로 기능**

**현황:**
- 개별 기기만 제어 가능
- 여러 기기를 한 번에 제어 못함 (예: 취침 모드 = 조명+에어컨+TV 끄기)

**개선안:**
```jsx
// frontend/src/components/DeviceGroups.jsx
function DeviceGroups() {
    const groups = [
        {
            id: 'sleep_mode',
            label: '🛏️ 취침 모드',
            devices: ['light_bedroom', 'ac_living_room', 'tv_living_room'],
            actions: ['turn_off', 'turn_off', 'turn_off'],
            icon: '🛏️'
        },
        {
            id: 'movie_mode',
            label: '🎬 영화 모드',
            devices: ['light_living_room', 'ac_living_room'],
            actions: ['dim_to_20%', 'set_temperature_20'],
            icon: '🎬'
        }
    ];
    
    return (
        <div className="device-groups">
            {groups.map(group => (
                <button key={group.id} className="group-button">
                    {group.icon} {group.label}
                    {/* 한 번의 시선 고정으로 모든 기기 제어 */}
                </button>
            ))}
        </div>
    );
}
```

**백엔드:**
```python
# backend/api/devices.py
@router.post("/groups/{group_id}/execute")
async def execute_group(group_id: str):
    """기기 그룹 매크로 실행"""
    group = await db.get_device_group(group_id)
    for device_id, action in zip(group['devices'], group['actions']):
        await control_device(device_id, action)
    
    return {"status": "success", "executed": len(group['devices'])}
```

**파일 생성/수정:**
- `edge-module/backend/api/device_groups.py` (새로운 엔드포인트)
- `edge-module/frontend/src/components/DeviceGroups.jsx` (새로운 컴포넌트)

---

#### 7. **탭 네비게이션 개선 (키보드/음성 대응)**

**현황:**
- 순수 시선 기반 UI
- 마우스/키보드 입력 지원 없음

**개선안:**
```jsx
// frontend/src/components/GazeNavigation.jsx
function useGazeNavigation() {
    const [focusedElement, setFocusedElement] = useState(null);
    const [focusableElements, setFocusableElements] = useState([]);
    
    // 1. Tab 키로 요소 이동 (기기 간 전환)
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Tab') {
                const nextIndex = (currentIndex + 1) % focusableElements.length;
                setFocusedElement(focusableElements[nextIndex]);
            }
            if (e.key === 'Enter') {
                focusedElement?.click();  // Enter로 선택
            }
        };
        
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [focusedElement]);
    
    return { focusedElement };
}
```

**음성 명령:**
```jsx
function useVoiceCommands() {
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'ko-KR';
    
    recognition.onresult = (event) => {
        const command = event.results[0][0].transcript;
        
        if (command.includes('켜')) {
            turnOn(currentDevice);
        } else if (command.includes('꺼')) {
            turnOff(currentDevice);
        } else if (command.includes('밝게')) {
            brightness.increase();
        } else if (command.includes('어둡게')) {
            brightness.decrease();
        }
    };
    
    return { startListening: () => recognition.start() };
}
```

**파일 생성:**
- `edge-module/frontend/src/hooks/useVoiceCommands.js` (새로운 훅)
- `edge-module/frontend/src/hooks/useGazeNavigation.js` (개선)

---

### ⭐ **부가 개선 (Priority 3: 장기 유지보수)**

#### 8. **개인화된 대시보드**

```jsx
// frontend/src/pages/DashboardCustomization.jsx
function DashboardCustomization() {
    // 사용자가 자주 사용하는 기기 상단 배치
    // 최근 사용 기기 하이라이트
    // 주 시간대별 자동 정렬 (아침: 조명, 저녁: 에어컨)
}
```

#### 9. **캘리브레이션 개선 (사용성)**

```jsx
// frontend/src/pages/CalibrationPage.jsx 개선사항:
// - 3포인트 캘리브레이션 (간단한 모드) 추가
// - 실시간 정확도 시각화
// - 캘리브레이션 팁 영상
```

#### 10. **사용 통계 및 피드백**

```python
# backend/api/analytics.py
@router.get("/user/usage-stats")
async def get_usage_stats():
    """
    사용 패턴 분석:
    - 가장 자주 제어하는 기기
    - 시간대별 사용 패턴
    - 평균 반응 시간
    - 캘리브레이션 정확도 추이
    """
    return {
        "most_used_devices": [...],
        "peak_hours": [...],
        "accuracy_trend": [...]
    }
```

---

## 🔧 구현 우선순위 로드맵

```
Phase 1 (1-2주): 필수 기능
├─ 긴급 SOS 모드 (Safety)
├─ 음성 피드백 TTS (Accessibility)
└─ 호버 시간 커스터마이징 (UX)

Phase 2 (2-3주): 사용성 향상
├─ 머리 자세 보정 (Accuracy)
├─ 시선 품질 상세 정보 (Feedback)
└─ 기기 그룹/매크로 (Convenience)

Phase 3 (3-4주): 장기 개선
├─ 음성/키보드 명령어 (Accessibility)
├─ 개인화 대시보드 (UX)
└─ 통계 및 학습 (Analytics)
```

---

## 💡 구현 팁

### 1. **테스트 방법론**
```python
# 실제 사용자(거동 불편) 테스트 체크리스트
- [ ] 팔 움직임 제약: 어깨 이동만으로 사용 가능?
- [ ] 시선 안정성: 손 떨림 있는 사용자도 정확히 선택?
- [ ] 긍정급강 인지: 기능 실행 확인 용이?
- [ ] 에러 복구: 잘못 선택 시 되돌리기 가능?
```

### 2. **성능 고려사항**
```
라즈베리파이 4에서 추가 기능 성능 영향:

음성 피드백: +0ms (브라우저 네이티브 Web Speech API)
머리 자세 보정: +10-15ms (이미 계산됨, 활용만)
기기 그룹: +50ms (DB 쿼리)

총 추가 레이턴시: ~50-60ms → 여전히 반응적 ✅
```

---

## 📚 관련 표준 및 가이드

- **WCAG 2.1 (Web Content Accessibility Guidelines)**
  - Level AA 준수 권장
  - 키보드 네비게이션, 음성 피드백 포함

- **접근성 관련 한국 표준**
  - 웹 접근성 지침 2.2 (국가 표준)
  - 정보통신 기술 접근성 표준

---

## 🚀 예상 효과

| 개선사항               | 사용성 | 정확도 | 안전성 |
| ---------------------- | ------ | ------ | ------ |
| 시선 정확도 개선       | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐⭐  | ⭐⭐⭐    |
| 음성 피드백            | ⭐⭐⭐⭐⭐  | ⭐⭐     | ⭐⭐⭐    |
| 긴급 SOS               | ⭐⭐⭐    | ⭐      | ⭐⭐⭐⭐⭐  |
| 호버 시간 커스터마이징 | ⭐⭐⭐⭐   | ⭐⭐⭐    | ⭐⭐     |
| 기기 그룹 제어         | ⭐⭐⭐⭐   | ⭐⭐⭐    | ⭐⭐     |

---

## ✅ 체크리스트

개선사항 구현 시 확인 사항:

- [ ] 모든 기능이 시선만으로 조작 가능한가?
- [ ] 마우스 또는 터치스크린이 필요하지 않은가?
- [ ] 음성 피드백이 명확한가?
- [ ] 오류 발생 시 복구 방법이 명확한가?
- [ ] 긴급 상황 대응이 5초 이내인가?
- [ ] 라즈베리파이 4에서 레이턴시 < 100ms인가?
- [ ] 실제 거동 불편 사용자 테스트를 거쳤는가? ⭐ **중요**

