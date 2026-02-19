"""
API 라우트 정의
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from app.models.schemas import (
    VideoURLRequest,
    VideoInfo,
    TranscriptItem,
    ErrorResponse,
    StatusResponse
)
from app.services.youtube_service import YouTubeService
from app.services import database_service as db
from app.utils.helpers import extract_video_id
from typing import Dict, List, Optional
import logging
import time

logger = logging.getLogger(__name__)  # v1.2 - Force reload

router = APIRouter(prefix="/api", tags=["youtube"])

# YouTube 서비스 인스턴스
youtube_service = YouTubeService()


@router.post("/extract-transcript")
async def extract_transcript(request: VideoURLRequest):
    """
    YouTube 영상에서 자막 추출

    Args:
        request: VideoURLRequest (url 포함)

    Returns:
        자막 데이터 및 비디오 정보
    """
    try:
        # URL에서 video_id 추출
        video_id = extract_video_id(request.url)
        if not video_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 YouTube URL입니다.")

        # 비디오 정보 가져오기
        video_info = youtube_service.get_video_info(request.url)

        # 자막 추출
        transcript_result = youtube_service.get_transcript(video_id)

        if not transcript_result["success"]:
            return {
                "success": False,
                "error": transcript_result["error"],
                "video_info": video_info,
                "message": "자막을 찾을 수 없습니다. Whisper API를 사용해야 합니다."
            }

        # 타임라인 형식으로 변환
        timeline = youtube_service.format_timeline(transcript_result["data"])

        return {
            "success": True,
            "video_info": video_info,
            "timeline": timeline,
            "language": transcript_result["language"],
            "source": transcript_result["source"],
            "total_items": len(timeline)
        }

    except Exception as e:
        logger.error(f"자막 추출 실패: {e}")
        raise HTTPException(status_code=500, detail=f"자막 추출 중 오류 발생: {str(e)}")


@router.post("/video-info")
async def get_video_info(request: VideoURLRequest):
    """
    YouTube 영상 기본 정보 가져오기

    Args:
        request: VideoURLRequest (url 포함)

    Returns:
        비디오 정보 (success, video_info 포함)
    """
    try:
        print(f"[DEBUG] Received URL: {request.url}")
        logger.info(f"Received URL: {request.url}")
        video_info = youtube_service.get_video_info(request.url)
        print(f"[DEBUG] Video info: {video_info}")
        logger.info(f"Video info: {video_info}")
        return {
            "success": True,
            "video_info": video_info
        }

    except Exception as e:
        print(f"[ERROR] 비디오 정보 가져오기 실패: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"비디오 정보 가져오기 실패: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"비디오 정보 가져오기 실패: {str(e)}"
        }


@router.post("/process-video")
async def process_video(request: VideoURLRequest, background_tasks: BackgroundTasks):
    """
    YouTube 영상 전체 처리 파이프라인 (LangChain Agent 사용)

    Args:
        request: VideoURLRequest (url 포함)
        background_tasks: 백그라운드 작업

    Returns:
        처리 완료된 결과
    """
    try:
        from app.services.langchain_agent import YouTubeSummaryAgent

        # 처리 시간 측정 시작
        start_time = time.time()

        # LangChain Agent 생성 및 실행
        agent = YouTubeSummaryAgent()
        result = agent.process_video(request.url)

        # 처리 시간 측정 완료
        processing_time_ms = int((time.time() - start_time) * 1000)

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "영상 처리 실패")
            )

        # DB에 요약 결과 저장
        try:
            video_info = result.get("video_info", {})
            video_id = extract_video_id(request.url)
            db.save_summary(
                video_id=video_id,
                video_url=request.url,
                title=video_info.get("title", "Unknown"),
                author=video_info.get("author", "Unknown"),
                duration=video_info.get("length", 0),
                notion_url=result.get("notion_url"),
                structured_summary=result.get("structured_summary", {}),
                timeline=result.get("timeline", []),
                processing_time_ms=processing_time_ms
            )
            logger.info(f"요약 결과 DB 저장 완료: {video_id}")
        except Exception as db_error:
            logger.warning(f"요약 결과 DB 저장 실패 (처리는 성공): {db_error}")

        # 처리 시간을 결과에 추가
        result["processing_time_ms"] = processing_time_ms

        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"비디오 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"비디오 처리 중 오류 발생: {str(e)}")


@router.post("/process-video-quick")
async def process_video_quick(request: VideoURLRequest):
    """
    YouTube 영상 빠른 처리 (테스트용 - 처음 50개 항목만)

    Args:
        request: VideoURLRequest (url 포함)

    Returns:
        처리 완료된 결과
    """
    try:
        from app.services.langchain_agent import YouTubeSummaryAgent

        agent = YouTubeSummaryAgent()
        result = agent.process_video_quick(request.url, max_items=50)

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "영상 처리 실패")
            )

        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"비디오 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"비디오 처리 중 오류 발생: {str(e)}")


@router.post("/related-videos")
async def get_related_videos(request: VideoURLRequest):
    """
    관련 동영상 가져오기 (최대 3개)

    Args:
        request: VideoURLRequest (url 포함)

    Returns:
        관련 동영상 리스트
    """
    try:
        related = youtube_service.get_related_videos(request.url, max_results=3)
        return {
            "success": True,
            "related_videos": related
        }

    except Exception as e:
        logger.error(f"관련 동영상 가져오기 실패: {e}")
        return {
            "success": False,
            "related_videos": [],
            "error": str(e)
        }


# ===== 요약 내역 API =====

@router.get("/summaries")
async def get_summaries(
    days: int = Query(default=30, ge=1, le=365, description="조회할 기간 (일)"),
    limit: int = Query(default=100, ge=1, le=500, description="최대 조회 개수")
):
    """
    최근 N일 내의 요약 내역 목록 조회

    Args:
        days: 조회할 기간 (기본 30일)
        limit: 최대 조회 개수 (기본 100개)

    Returns:
        요약 목록
    """
    try:
        summaries = db.get_recent_summaries(days=days, limit=limit)
        return {
            "success": True,
            "summaries": summaries,
            "count": len(summaries)
        }

    except Exception as e:
        logger.error(f"요약 내역 조회 실패: {e}")
        return {
            "success": False,
            "summaries": [],
            "error": str(e)
        }


@router.get("/summaries/{summary_id}")
async def get_summary_detail(summary_id: int):
    """
    요약 상세 조회 (ID로)

    Args:
        summary_id: 요약 레코드 ID

    Returns:
        요약 상세 정보
    """
    try:
        summary = db.get_summary_by_id(summary_id)
        if summary:
            return {
                "success": True,
                "summary": summary
            }
        else:
            raise HTTPException(status_code=404, detail="요약을 찾을 수 없습니다.")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"요약 상세 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/summaries/video/{video_id}")
async def get_summary_by_video(video_id: str):
    """
    비디오 ID로 요약 조회

    Args:
        video_id: YouTube 비디오 ID

    Returns:
        요약 상세 정보
    """
    try:
        summary = db.get_summary_by_video_id(video_id)
        if summary:
            return {
                "success": True,
                "summary": summary
            }
        else:
            return {
                "success": False,
                "error": "해당 비디오의 요약이 없습니다."
            }

    except Exception as e:
        logger.error(f"비디오 요약 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/summaries/cleanup")
async def cleanup_old_summaries(
    days: int = Query(default=30, ge=1, le=365, description="보관 기간 (일)")
):
    """
    오래된 요약 삭제 (관리자용)

    Args:
        days: 보관 기간 (기본 30일)

    Returns:
        삭제된 레코드 수
    """
    try:
        deleted_count = db.delete_old_summaries(days=days)
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"{deleted_count}개의 오래된 요약이 삭제되었습니다."
        }

    except Exception as e:
        logger.error(f"요약 삭제 실패: {e}")
        return {
            "success": False,
            "error": str(e)
        }
