#!/bin/bash
# 라즈베리파이 빠른 업데이트 & 재시작 스크립트

set -e  # 오류 발생 시 중단

echo "🔄 GazeHome 업데이트 중..."

# 1. 최신 코드 가져오기
echo "📥 Git Pull..."
git pull origin develop

# 2. 의존성 업데이트 (선택사항 - 주석 해제하여 사용)
# echo "📦 의존성 업데이트..."
# uv sync
# cd frontend && npm install && cd ..

# 3. 프론트엔드 빌드
echo "🏗️  프론트엔드 빌드..."
cd frontend
npm run build
cd ..

echo ""
echo "✅ 업데이트 완료!"
echo ""
echo "다음 명령으로 서버를 실행하세요:"
echo "  백엔드:      uv run run.py"
echo "  프론트엔드:  cd frontend && npx serve -s dist -l 5173"
echo ""
