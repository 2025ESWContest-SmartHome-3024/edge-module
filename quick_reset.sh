#!/bin/bash
# 빠른 테스트 재시작 스크립트

set -e

echo "🔄 테스트 환경 재설정 중..."

# 1. 보정 데이터 초기화
echo "🗑️  보정 데이터 초기화..."
uv run reset_calibration.py

# 2. 프론트엔드 빌드
echo "🏗️  프론트엔드 빌드..."
cd frontend
npm run build
cd ..

echo ""
echo "✅ 재설정 완료!"
echo ""
echo "다음 명령으로 서버를 실행하세요:"
echo "  uv run run.py"
echo ""
echo "브라우저 접속:"
echo "  http://raspberrypi.local:5173"
echo "  또는"
echo "  cd frontend && npx serve -s dist -l 5173"
echo ""
