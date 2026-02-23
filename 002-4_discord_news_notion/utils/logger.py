"""
로거 설정 모듈
loguru 기반으로 콘솔 + 파일 동시 출력
"""
import sys
from loguru import logger

def setup_logger():
    logger.remove()  # 기본 핸들러 제거

    # 콘솔 출력 (컬러)
    logger.add(
        sys.stdout,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level="INFO",
    )

    # 파일 출력 (7일 보관, 로테이션 10MB)
    logger.add(
        "logs/bot.log",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        level="DEBUG",
    )

    return logger


# 모듈 레벨에서 기본 설정
setup_logger()
