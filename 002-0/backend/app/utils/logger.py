"""
로깅 설정 유틸리티
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 로그 디렉토리 생성
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 로그 포맷
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "app", level: int = logging.INFO) -> logging.Logger:
    """
    로거 설정 및 반환

    Args:
        name: 로거 이름
        level: 로그 레벨

    Returns:
        설정된 로거 인스턴스
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 기존 핸들러 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)

    # 파일 핸들러 (일반 로그)
    today = datetime.now().strftime("%Y%m%d")
    info_log_file = LOG_DIR / f"app_{today}.log"
    file_handler = RotatingFileHandler(
        info_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    file_handler.setFormatter(file_formatter)

    # 에러 로그 파일 핸들러
    error_log_file = LOG_DIR / f"error_{today}.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    로거 가져오기

    Args:
        name: 로거 이름

    Returns:
        로거 인스턴스
    """
    return logging.getLogger(name)


# 디버그 로그 헬퍼
def log_request(logger: logging.Logger, endpoint: str, data: dict):
    """API 요청 로그"""
    logger.info(f"=== API Request to {endpoint} ===")
    logger.info(f"Data: {data}")


def log_response(logger: logging.Logger, endpoint: str, status_code: int, response: dict):
    """API 응답 로그"""
    logger.info(f"=== API Response from {endpoint} ===")
    logger.info(f"Status: {status_code}")
    logger.info(f"Response: {response}")


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """에러 로그"""
    logger.error(f"=== Error occurred ===")
    if context:
        logger.error(f"Context: {context}")
    logger.error(f"Error Type: {type(error).__name__}")
    logger.error(f"Error Message: {str(error)}")
    logger.error(f"Traceback:", exc_info=True)
