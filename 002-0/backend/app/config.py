"""
환경 설정 관리
"""
from pydantic_settings import BaseSettings
from pydantic import ValidationError
from typing import Optional
from pathlib import Path
import sys


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # OpenAI API
    OPENAI_API_KEY: str = ""

    # YouTube Data API v3
    YOUTUBE_API_KEY: Optional[str] = None

    # Supadata API (클라우드 환경 자막 추출용)
    SUPADATA_API_KEY: Optional[str] = None

    # PostgreSQL Database (Supabase)
    DATABASE_URL: Optional[str] = None

    # Notion API
    NOTION_API_KEY: Optional[str] = None
    NOTION_PARENT_PAGE_ID: Optional[str] = None

    # Server Config
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    # 배포 환경에서 허용할 추가 Origins (콤마로 구분)
    ALLOWED_ORIGINS: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # 중요: 시스템 환경 변수도 읽도록 설정 (Render 등 배포 환경)
        extra = "ignore"


# 설정 인스턴스 생성
def _load_settings() -> Settings:
    """설정 로드 및 검증"""
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        print(f"[안내] .env 파일이 없습니다: {env_path}")
        print("[안내] 시스템 환경 변수에서 설정을 읽습니다.")

    try:
        _settings = Settings()

        if not _settings.OPENAI_API_KEY:
            print("[경고] OPENAI_API_KEY가 설정되지 않았습니다.")
            print("[안내] 환경 변수 또는 .env 파일에 OPENAI_API_KEY를 설정해주세요.")
        else:
            print(f"[확인] OPENAI_API_KEY 로드됨 (길이: {len(_settings.OPENAI_API_KEY)})")

        if _settings.ALLOWED_ORIGINS:
            print(f"[확인] ALLOWED_ORIGINS: {_settings.ALLOWED_ORIGINS}")

        return _settings

    except ValidationError as e:
        print(f"[에러] 환경 설정 로드 실패: {e}")
        print("[안내] 환경 변수 설정을 확인해주세요.")
        sys.exit(1)


settings = _load_settings()
