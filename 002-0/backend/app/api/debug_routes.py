"""
디버깅용 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from datetime import datetime
import logging
import os

router = APIRouter(prefix="/debug", tags=["debug"])
logger = logging.getLogger(__name__)


@router.get("/logs")
async def get_logs(lines: int = 100, log_type: str = "app"):
    """
    로그 파일 내용 조회

    Args:
        lines: 조회할 라인 수 (기본: 100, 최대: 1000)
        log_type: 로그 타입 ("app" 또는 "error")

    Returns:
        로그 내용
    """
    try:
        # 라인 수 제한
        lines = min(lines, 1000)

        # 로그 디렉토리
        log_dir = Path(__file__).parent.parent.parent / "logs"

        if not log_dir.exists():
            return {
                "success": False,
                "message": "로그 디렉토리가 존재하지 않습니다.",
                "logs": []
            }

        # 오늘 날짜의 로그 파일
        today = datetime.now().strftime("%Y%m%d")

        if log_type == "error":
            log_file = log_dir / f"error_{today}.log"
        else:
            log_file = log_dir / f"app_{today}.log"

        if not log_file.exists():
            return {
                "success": False,
                "message": f"로그 파일이 존재하지 않습니다: {log_file.name}",
                "logs": []
            }

        # 파일 읽기
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "success": True,
            "log_file": log_file.name,
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
            "logs": [line.strip() for line in recent_lines]
        }

    except Exception as e:
        logger.error(f"로그 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")


@router.get("/logs/list")
async def list_log_files():
    """
    사용 가능한 로그 파일 목록 조회

    Returns:
        로그 파일 목록
    """
    try:
        log_dir = Path(__file__).parent.parent.parent / "logs"

        if not log_dir.exists():
            return {
                "success": False,
                "message": "로그 디렉토리가 존재하지 않습니다.",
                "files": []
            }

        # 로그 파일 목록
        log_files = []
        for file in sorted(log_dir.glob("*.log"), reverse=True):
            stat = file.stat()
            log_files.append({
                "name": file.name,
                "size": f"{stat.st_size / 1024:.2f} KB",
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

        return {
            "success": True,
            "total_files": len(log_files),
            "files": log_files
        }

    except Exception as e:
        logger.error(f"로그 파일 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"로그 파일 목록 조회 실패: {str(e)}")


@router.get("/system-info")
async def get_system_info():
    """
    시스템 정보 조회

    Returns:
        시스템 정보
    """
    try:
        import sys
        import platform
        from app.config import settings

        return {
            "success": True,
            "system": {
                "platform": platform.platform(),
                "python_version": sys.version,
                "working_directory": os.getcwd(),
            },
            "config": {
                "backend_host": settings.BACKEND_HOST,
                "backend_port": settings.BACKEND_PORT,
                "frontend_url": settings.FRONTEND_URL,
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "notion_api_key_configured": bool(settings.NOTION_API_KEY),
            },
            "paths": {
                "log_directory": str(Path(__file__).parent.parent.parent / "logs"),
                "temp_audio_directory": "temp_audio",
            }
        }

    except Exception as e:
        logger.error(f"시스템 정보 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"시스템 정보 조회 실패: {str(e)}")


@router.post("/test-youtube")
async def test_youtube_connection(url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"):
    """
    YouTube 연결 테스트

    Args:
        url: 테스트할 YouTube URL

    Returns:
        연결 테스트 결과
    """
    try:
        from app.services.youtube_service import YouTubeService
        from app.utils.helpers import extract_video_id

        youtube_service = YouTubeService()

        # Video ID 추출
        video_id = extract_video_id(url)

        result = {
            "success": True,
            "url": url,
            "video_id": video_id,
            "tests": {}
        }

        # 1. 영상 정보 가져오기 테스트
        try:
            video_info = youtube_service.get_video_info(url)
            result["tests"]["video_info"] = {
                "status": "success",
                "data": video_info
            }
        except Exception as e:
            result["tests"]["video_info"] = {
                "status": "failed",
                "error": str(e)
            }

        # 2. 자막 추출 테스트
        try:
            transcript = youtube_service.get_transcript(video_id)
            result["tests"]["transcript"] = {
                "status": "success" if transcript["success"] else "no_transcript",
                "language": transcript.get("language"),
                "source": transcript.get("source"),
                "item_count": len(transcript.get("data", [])) if transcript.get("data") else 0
            }
        except Exception as e:
            result["tests"]["transcript"] = {
                "status": "failed",
                "error": str(e)
            }

        return result

    except Exception as e:
        logger.error(f"YouTube 연결 테스트 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"YouTube 연결 테스트 실패: {str(e)}")


@router.post("/test-openai")
async def test_openai_connection():
    """
    OpenAI API 연결 테스트

    Returns:
        연결 테스트 결과
    """
    try:
        from openai import OpenAI
        from app.config import settings

        if not settings.OPENAI_API_KEY:
            return {
                "success": False,
                "error": "OpenAI API 키가 설정되지 않았습니다."
            }

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # 간단한 테스트 요청
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello'"}
            ],
            max_tokens=10
        )

        return {
            "success": True,
            "message": "OpenAI API 연결 성공",
            "test_response": response.choices[0].message.content,
            "model": response.model
        }

    except Exception as e:
        logger.error(f"OpenAI 연결 테스트 실패: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health-detailed")
async def detailed_health_check():
    """
    상세 헬스 체크

    Returns:
        시스템 각 컴포넌트의 상태
    """
    try:
        from app.config import settings
        import psutil

        # CPU 및 메모리 사용량
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "api_server": "healthy",
                "openai_configured": bool(settings.OPENAI_API_KEY),
                "notion_configured": bool(settings.NOTION_API_KEY),
            },
            "resources": {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "memory_available": f"{memory.available / (1024**3):.2f} GB"
            }
        }

    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
