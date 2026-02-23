"""
전체 설정값 관리 모듈
.env 파일에서 환경변수를 읽어옵니다.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Discord ──────────────────────────────────────────────
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# 빈 문자열이면 전체 채널 감지, 있으면 해당 채널만 감지
_channel_ids_raw = os.getenv("DISCORD_CHANNEL_IDS", "")
DISCORD_CHANNEL_IDS: list = (
    [int(cid.strip()) for cid in _channel_ids_raw.split(",") if cid.strip()]
    if _channel_ids_raw.strip()
    else []
)

# ─── Claude CLI ───────────────────────────────────────────
CLAUDE_CLI_PATH: str = os.getenv("CLAUDE_CLI_PATH", "/opt/homebrew/bin/claude")
CLAUDE_TIMEOUT: int = int(os.getenv("CLAUDE_TIMEOUT", "300"))

# ─── Notion ───────────────────────────────────────────────
# MCP 방식: Claude CLI가 직접 Notion에 저장. API Key 불필요.
NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")

# ─── 기타 ─────────────────────────────────────────────────
MAX_CONTENT_LENGTH: int = 4000


def validate():
    """필수 환경변수 누락 여부 확인"""
    required = {
        "DISCORD_TOKEN": DISCORD_TOKEN,
        "NOTION_DATABASE_ID": NOTION_DATABASE_ID,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise EnvironmentError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}")
