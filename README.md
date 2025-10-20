# GazeHome - 시선 추적 기반 스마트홈 통합 플랫폼

시선(아이 가제) 추적 기술을 활용한 웹 기반 스마트홈 제어 시스템입니다.

## 주요 기능

- **시선 추적**: MediaPipe를 통한 실시간 시선 감지
- **캘리브레이션**: 9포인트/5포인트 웹 기반 캘리브레이션
- **스마트홈 제어**: 시선 hovering을 통한 직관적인 기기 제어
- **AI 추천**: 사용자 행동 기반 스마트 추천
- **실시간 스트리밍**: WebSocket을 통한 30-60 FPS 시선 데이터 전송

## 시스템 구조

### 백엔드
- **FastAPI**: 고성능 API 서버
- **WebSocket**: 실시간 시선 데이터 스트리밍
- **SQLite**: 사용자 및 캘리브레이션 데이터 관리

### 시선 추적 모델
- **MediaPipe**: 얼굴 특징점 감지 (468개 포인트)
- **scikit-learn**: 시선 위치 예측 모델 (Ridge, SVR, ElasticNet)
- **필터**: Kalman, KDE, NoOp

### 프론트엔드
- **React 18**: 현대적인 UI 프레임워크
- **Framer Motion**: 부드러운 애니메이션
- **Vite**: 빠른 개발 서버 및 빌드

## 설치

### 요구사항
- Python 3.9+
- Node.js 18+ (프론트엔드)
- 웹캠

### 설치 방법

```bash
# 프로젝트 디렉토리로 이동
cd edge-module

# 백엔드 설치 (선택사항)
uv sync

# 프론트엔드 설치
cd frontend
npm install
```

## 실행

### 백엔드 서버
```bash
uv run run.py
```

서버는 `http://0.0.0.0:8000`에서 실행됩니다.

### 프론트엔드 개발 서버
```bash
cd frontend
npm run dev
```

프론트엔드는 `http://localhost:5173`에서 실행됩니다.

## 사용법

1. 브라우저에서 프론트엔드 접속
2. 사용자명 입력 후 로그인
3. 캘리브레이션 수행 (9포인트)
4. 홈 화면에서 시선으로 기기 제어

## API 문서

실행 중인 서버의 `/docs` 또는 `/redoc` 에서 Swagger UI 또는 ReDoc 확인 가능

## 라이센스

MIT License

## 저자

- Chenkai Zhang (ck-zhang)
- Contributors
