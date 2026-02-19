"""
FastAPI 메인 애플리케이션
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import routes
from app.api import debug_routes
from app.utils.logger import setup_logger

# 로깅 설정
logger = setup_logger("app", level=logging.INFO)

# FastAPI 앱 생성
app = FastAPI(
    title="YouTube Summary Agent",
    description="YouTube 영상을 자동으로 요약하고 Notion에 저장하는 API",
    version="1.0.0"
)

# CORS 설정 - 배포 환경 지원
allowed_origins = [settings.FRONTEND_URL, "http://localhost:3000"]
if settings.ALLOWED_ORIGINS:
    allowed_origins.extend([o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(routes.router)
app.include_router(debug_routes.router)  # 디버그 라우터 추가

logger.info("YouTube Summary Agent API 시작됨 v1.1")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "YouTube Summary Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "openai_api_key_configured": bool(settings.OPENAI_API_KEY)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
