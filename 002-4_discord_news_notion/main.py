"""
Discord 뉴스 → Notion 자동 분석 봇 진입점
"""
import os
import sys

from loguru import logger

import utils.logger  # noqa: F401 — 커스텀 로거 설정 적용
import config
from bot.client import create_client
from bot.events import register_events


def main():
    # 필수 환경변수 검증
    try:
        config.validate()
    except EnvironmentError as e:
        logger.critical(f"환경변수 오류: {e}")
        logger.critical(".env 파일을 확인해주세요 (.env.example 참고)")
        sys.exit(1)

    # Claude CLI 경로 확인
    if not os.path.exists(config.CLAUDE_CLI_PATH):
        logger.critical(
            f"Claude CLI를 찾을 수 없습니다: {config.CLAUDE_CLI_PATH}\n"
            f"설치 확인: which claude\n"
            f"또는 .env의 CLAUDE_CLI_PATH 수정"
        )
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("📰 Discord News → Notion Bot 시작")
    logger.info(f"Claude CLI: {config.CLAUDE_CLI_PATH}")
    logger.info(f"감지 채널: {config.DISCORD_CHANNEL_IDS or '전체'}")
    logger.info("=" * 50)

    client = create_client()
    register_events(client)

    client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
