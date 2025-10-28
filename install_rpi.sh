#!/bin/bash
# 라즈베리파이 GazeHome 자동 설치 스크립트
# 사용법: curl -sSL https://raw.githubusercontent.com/ESWC-AIRIS/edge-module/develop/install_rpi.sh | bash

set -e  # 오류 발생 시 중단

echo "=================================="
echo "🍓 GazeHome 라즈베리파이 설치"
echo "=================================="
echo ""

# 1. 시스템 패키지 업데이트
echo "📦 시스템 패키지 업데이트 중..."
sudo apt update

# 2. 필수 시스템 패키지 설치
echo "📦 필수 패키지 설치 중..."

# 기본 패키지 (필수)
sudo apt install -y git python3-pip python3-venv python3-dev \
  ffmpeg python3-opencv python3-numpy \
  libxcb-shm0 libsdl2-2.0-0 libxv1 libtheora0 \
  libva-drm2 libva-x11-2 libvdpau1 libharfbuzz0b \
  libbluray2 libatlas-base-dev libgtk-3-0

# 선택적 패키지 (설치 가능한 것만)
echo "📦 선택적 의존성 설치 중..."
for pkg in libcdio-paranoia-dev libhdf5-dev libdc1394-dev libopenexr-dev; do
    if apt-cache show "$pkg" &>/dev/null; then
        sudo apt install -y "$pkg" || echo "⚠️  $pkg 설치 실패 (무시)"
    else
        echo "ℹ️  $pkg: 패키지를 찾을 수 없음 (선택사항)"
    fi
done

# 3. Rust 설치 확인
if ! command -v rustc &> /dev/null; then
    echo "🦀 Rust 설치 중..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
else
    echo "✅ Rust 이미 설치됨"
fi

# 4. uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo "📦 uv 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # PATH 추가
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "✅ uv 이미 설치됨"
fi

# 5. 프로젝트 클론
if [ -d "$HOME/edge-module" ]; then
    echo "📂 edge-module 디렉토리가 이미 존재합니다"
    read -p "덮어쓰시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/edge-module"
    else
        echo "❌ 설치 취소됨"
        exit 1
    fi
fi

echo "📥 프로젝트 클론 중..."
cd ~
git clone https://github.com/ESWC-AIRIS/edge-module.git
cd edge-module
git checkout develop

# 6. Virtual Environment 생성
echo "🐍 Python 가상 환경 생성 중..."
export PATH="$HOME/.local/bin:$PATH"
uv venv --python 3.11 --system-site-packages

# venv 생성 확인
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ venv 생성 실패. pip를 사용한 기본 venv로 전환합니다..."
    python3 -m venv .venv --system-site-packages
fi

# 7. 환경 활성화 및 의존성 설치
echo "📦 의존성 설치 중..."
source .venv/bin/activate

# MediaPipe-RPI4 설치 (venv 내부에서)
echo "📦 MediaPipe-RPI4 설치 중..."
if [ -f ".venv/bin/pip" ]; then
    .venv/bin/pip install mediapipe-rpi4
else
    pip install mediapipe-rpi4
fi

# 나머지 의존성 설치
echo "📦 프로젝트 의존성 설치 중..."
if command -v uv &> /dev/null; then
    uv sync || pip install -r requirements.txt
else
    echo "⚠️  uv를 찾을 수 없습니다. requirements.txt로 설치합니다..."
    pip install -r requirements.txt
fi

# 8. Node.js 설치 확인
if ! command -v node &> /dev/null; then
    echo "📦 Node.js 설치 중..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    echo "✅ Node.js 이미 설치됨"
fi

# 9. 프론트엔드 의존성 설치
echo "📦 프론트엔드 의존성 설치 중..."
cd frontend
npm install

# 10. 설정 파일 생성
echo "⚙️  설정 파일 생성 중..."
cd ..
mkdir -p ~/.gazehome/calibrations

cat > backend/.env << 'EOF'
AI_SERVER_URL=http://34.227.8.172:8000
AI_REQUEST_TIMEOUT=60
AI_MAX_RETRIES=3
GATEWAY_URL=http://34.227.8.172:8001
GATEWAY_DEVICES_ENDPOINT=http://34.227.8.172:8001/api/lg/devices
DATABASE_PATH=/home/$USER/.gazehome/calibrations/gazehome.db
CALIBRATION_DIR=/home/$USER/.gazehome/calibrations
HOST=0.0.0.0
PORT=8000
EOF

# 11. 검증
echo ""
echo "🧪 설치 검증 중..."
source .venv/bin/activate
python -c "import mediapipe; print('✅ MediaPipe:', mediapipe.__version__)" || echo "❌ MediaPipe 실패"
python -c "import cv2; print('✅ OpenCV:', cv2.__version__)" || echo "❌ OpenCV 실패"
python -c "import fastapi; print('✅ FastAPI')" || echo "❌ FastAPI 실패"
python -c "import numpy; print('✅ NumPy')" || echo "❌ NumPy 실패"

echo ""
echo "=================================="
echo "✅ 설치 완료!"
echo "=================================="
echo ""
echo "다음 단계:"
echo ""
echo "1. 백엔드 실행 (두 가지 방법):"
echo "   # 방법 1: uv run 사용"
echo "   cd ~/edge-module"
echo "   uv run run.py"
echo ""
echo "   # 방법 2: venv 직접 사용"
echo "   cd ~/edge-module"
echo "   source .venv/bin/activate"
echo "   python backend/run.py"
echo ""
echo "2. 프론트엔드 실행 (새 터미널):"
echo "   cd ~/edge-module/frontend"
echo "   npm run build"
echo "   npx serve -s dist -l 5173 --host 0.0.0.0"
echo ""
echo "3. 브라우저 접속:"
echo "   http://raspberrypi.local:5173"
echo ""
echo "=================================="
