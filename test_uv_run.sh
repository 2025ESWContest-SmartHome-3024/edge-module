#!/bin/bash
# uv run 테스트 스크립트
# mediapipe-rpi4가 설치된 venv에서 uv run이 작동하는지 확인

echo "🧪 uv run 테스트 중..."
echo ""

cd ~/edge-module

# 1. venv 존재 확인
if [ ! -d ".venv" ]; then
    echo "❌ .venv 디렉토리가 없습니다"
    exit 1
fi

# 2. mediapipe-rpi4 설치 확인
echo "1. mediapipe-rpi4 설치 확인:"
.venv/bin/pip list | grep mediapipe || echo "❌ mediapipe-rpi4가 설치되지 않았습니다"
echo ""

# 3. uv run으로 mediapipe import 테스트
echo "2. uv run으로 mediapipe import 테스트:"
uv run python -c "import mediapipe; print(f'✅ MediaPipe {mediapipe.__version__}')" 2>&1
echo ""

# 4. 직접 venv python으로 테스트
echo "3. venv python으로 직접 테스트:"
.venv/bin/python -c "import mediapipe; print(f'✅ MediaPipe {mediapipe.__version__}')" 2>&1
echo ""

# 5. uv run으로 백엔드 import 테스트
echo "4. uv run으로 백엔드 import 테스트:"
uv run python -c "from backend.core.gaze_tracker import WebGazeTracker; print('✅ GazeTracker import 성공')" 2>&1
echo ""

# 6. 결론
echo "=================================="
echo "테스트 완료"
echo "=================================="
echo ""
echo "만약 'uv run'에서 오류가 발생하면:"
echo "  → source .venv/bin/activate 후 python 직접 실행"
echo ""
echo "정상 작동하면:"
echo "  → uv run run.py 사용 가능 ✅"
echo ""
