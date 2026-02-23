#!/bin/bash
# Discord 뉴스 → Notion 봇 셋업 스크립트
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==================================="
echo "  Discord News Notion Bot Setup"
echo "==================================="

# 1. venv 생성 (없으면)
echo "[1/3] Python 가상환경 확인..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "  venv 생성 중..."
    python3 -m venv "$PROJECT_DIR/venv"
fi
echo "  ✅ venv 준비됨"

# 2. 패키지 설치
echo "[2/3] 패키지 설치 중..."
source "$PROJECT_DIR/venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$PROJECT_DIR/requirements.txt"
echo "  ✅ 패키지 설치 완료"

# 3. .env 파일 생성 (없으면)
echo "[3/3] 환경변수 파일 확인..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "  ✅ .env 파일 생성됨 → 값을 직접 입력해주세요!"
else
    echo "  .env 이미 존재 (스킵)"
fi

echo ""
echo "==================================="
echo "  ✅ 셋업 완료!"
echo "==================================="
echo ""
echo "📋 다음 단계:"
echo "  1. .env 파일 편집:"
echo "     nano $PROJECT_DIR/.env"
echo ""
echo "  2. 봇 실행:"
echo "     source venv/bin/activate"
echo "     python main.py"
echo ""
echo "  3. Discord 봇 설정 체크리스트:"
echo "     □ Discord Developer Portal → MESSAGE CONTENT INTENT 활성화"
echo "     □ Notion Integration 생성 후 DB에 연결"
echo "     □ .env에 DISCORD_TOKEN, NOTION_API_KEY, NOTION_DATABASE_ID 입력"
