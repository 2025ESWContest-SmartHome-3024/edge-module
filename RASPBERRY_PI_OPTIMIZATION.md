# 라즈베리파이 최적화 설정 가이드

## 📊 선택된 구성

### 시선 추적 모델: **Ridge** ✅
```
특징: 선형 회귀 + L2 정규화
장점:
  ✅ 매우 가볍고 빠름 (CPU 사용량 최소)
  ✅ 메모리 효율적 (라즈베리파이에 최적)
  ✅ 학습 시간 빠름
  ✅ 충분한 정확도 제공
  ✅ Pickle 직렬화 매우 빠름

비교:
  - ElasticNet: Ridge보다 조금 무거움
  - SVR: 계산 복잡도 중간, 메모리 더 사용
  - TinyMLP: 신경망으로 가장 무거움 (라즈베리파이 부적합)
```

### 필터 방식: **NoOp** ✅
```
특징: 필터링 없음 (아무 작업도 하지 않음)
장점:
  ✅ CPU 부하 제로 (가장 빠름)
  ✅ 지연 없음 (실시간 응답성 우수)
  ✅ 메모리 사용 없음
  ✅ 안정적이고 예측 가능

비교:
  - Kalman: 상태 예측으로 정확하지만 CPU 부하 높음
           라즈베리파이에서 튜닝 어려움 + 지연 발생
  - KDE: 커널 밀도 추정으로 메모리 많이 사용
         라즈베리파이에 부담스러움
```

---

## 🔧 설정 파일

### backend/core/config.py
```python
model_name: str = "ridge"      # 라즈베리파이 최적화
filter_method: str = "noop"    # 필터링 비활성화
```

### backend/.env.example
```bash
MODEL_NAME=ridge
FILTER_METHOD=noop
```

---

## 📈 성능 비교

| 항목              | Ridge + NoOp  | Ridge + Kalman  | ElasticNet + Kalman |
| ----------------- | ------------- | --------------- | ------------------- |
| 모델 크기         | 매우 작음     | 매우 작음       | 작음                |
| 예측 속도         | ⚡⚡⚡ 매우 빠름 | ⚡ 느림 (Kalman) | ⚡ 느림              |
| CPU 사용          | 매우 낮음     | 높음            | 중간                |
| 메모리            | 매우 낮음     | 낮음            | 낮음                |
| 정확도            | 양호          | 좋음            | 좋음                |
| 라즈베리파이 적합 | ✅ 최고        | ⚠️ 한계          | ⚠️ 보통              |

---

## 🚀 실행 방법

```bash
# 백엔드 시작
uv run backend/run.py

# 또는 환경 변수로 설정
export MODEL_NAME=ridge
export FILTER_METHOD=noop
uv run backend/run.py
```

**서버 시작 시 출력:**
```
╔══════════════════════════════════════════╗
║   GazeHome 스마트 홈 백엔드 서버         ║
║   (라즈베리파이 최적화 설정)             ║
╚══════════════════════════════════════════╝

설정:
  - 시선 추적 모델: ridge (가볍고 빠름)
  - 필터: noop (CPU 부하 최소화)
```

---

## 💡 왜 이 조합을 선택했나?

### Ridge + NoOp = 최고의 라즈베리파이 성능 조합

**라즈베리파이의 제약:**
- CPU: ARM Cortex-A72 (싱글 코어 성능 제한)
- RAM: 4GB (라즈베리파이 4B 기준)
- 전력 소비 제한
- 발열 관리 필요

**이 조합의 장점:**
1. **Ridge**: 모든 모델 중 가장 가벼움
   - 선형 모델이라 계산 간단
   - 학습 및 예측 시간 최소
   
2. **NoOp**: 필터링 오버헤드 제거
   - Kalman 필터 튜닝의 복잡성 제거
   - 실시간 응답성 보장

**결과:**
- 💨 빠른 응답 시간 (지연 최소화)
- 🔋 낮은 전력 소비
- 🌡️ 발열 최소화
- ✅ 안정적인 실행

---

## 📋 다른 옵션 선택 시

### ElasticNet 사용하고 싶다면:
```python
model_name: str = "elastic_net"
filter_method: str = "noop"  # 반드시 noop 사용!
```

### KDE 필터 시도:
```python
model_name: str = "ridge"
filter_method: str = "kde"
# ⚠️ 주의: 메모리 사용 증가, CPU 부하 증가
```

### Kalman 필터 시도:
```python
model_name: str = "ridge"
filter_method: str = "kalman"
# ⚠️ 주의: 라즈베리파이에서 튜닝 어려움, 지연 발생
```

---

## 🔍 성능 모니터링

라즈베리파이에서 성능을 모니터링하려면:

```bash
# CPU 사용률 확인
top

# 메모리 사용률 확인
free -h

# 프로세스별 사용률
htop
```

---

## ✨ 최종 체크리스트

- ✅ 모델: Ridge (선택됨)
- ✅ 필터: NoOp (선택됨)
- ✅ Kalman 튜닝 제거 (CalibrationPage.jsx 수정됨)
- ✅ 설정 파일 업데이트 (config.py, .env.example)
- ✅ 서버 메시지 개선 (run.py)

모든 설정이 완료되었습니다! 🎉
