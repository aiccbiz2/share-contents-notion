"""
LangChain Agent - YouTube Summary Agent
"""
from app.services.youtube_service import YouTubeService
from app.services.translation_chain import TranslationChain
from app.services.sectioning_chain import SectioningChain
from app.services.notion_service import NotionService
from app.utils.helpers import extract_video_id
from app.config import settings
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class YouTubeSummaryAgent:
    """
    YouTube 영상 요약 Agent

    파이프라인:
    1. YouTube 자막 추출 (또는 Whisper API)
    2. 번역 및 정제
    3. 타임라인 생성
    4. 섹션 분류
    5. Notion 전송 (TODO)
    """

    def __init__(self):
        self.youtube_service = YouTubeService()
        self.translation_chain = TranslationChain()
        self.sectioning_chain = SectioningChain()

        # Notion 서비스 초기화 (설정이 있는 경우에만)
        self.notion_service = None
        if settings.NOTION_API_KEY and settings.NOTION_PARENT_PAGE_ID:
            self.notion_service = NotionService(
                api_key=settings.NOTION_API_KEY,
                parent_page_id=settings.NOTION_PARENT_PAGE_ID
            )
            logger.info("Notion 서비스 연결됨")

    def process_video(self, url: str) -> Dict:
        """
        YouTube 영상 전체 처리 파이프라인

        Args:
            url: YouTube URL

        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"영상 처리 시작: {url}")

            # 1단계: 비디오 정보 및 자막 추출
            video_id = extract_video_id(url)
            if not video_id:
                raise ValueError("유효하지 않은 YouTube URL입니다.")

            logger.info("1/5: 비디오 정보 가져오는 중...")
            video_info = self.youtube_service.get_video_info(url)

            logger.info("2/5: 자막 추출 중...")
            transcript_result = self.youtube_service.get_transcript(video_id)

            if not transcript_result["success"]:
                # TODO: Whisper API 사용
                raise ValueError(f"자막 추출 실패: {transcript_result['error']}")

            # 타임라인 형식으로 변환
            timeline = self.youtube_service.format_timeline(transcript_result["data"])
            source_lang = transcript_result["language"]

            logger.info(f"자막 추출 완료 - 언어: {source_lang}, 항목 수: {len(timeline)}")

            # 3단계: 번역 및 정제
            logger.info("3/5: 번역 및 정제 중...")
            if source_lang != "ko":
                # 한국어가 아니면 번역
                translated_timeline = self.translation_chain.translate_timeline_chunked(
                    timeline,
                    source_lang="영어" if source_lang == "en" else source_lang,
                    chunk_size=20
                )
                logger.info("번역 및 정제 완료")
            else:
                # 한국어는 번역 불필요 - 원본 그대로 사용 (항목 손실 방지)
                translated_timeline = timeline
                logger.info(f"한국어 자막 - 번역 건너뜀, 원본 유지 ({len(timeline)}개 항목)")

            # 4단계: 표준 구조 틀 기반 영상 분석
            logger.info("4/5: 표준 구조 틀 기반 영상 분석 중...")
            sections_data = self.sectioning_chain.classify_sections_with_summary(
                translated_timeline
            )

            structured_summary = sections_data.get("structured_summary", {})
            core_topics_count = len(structured_summary.get("core_topics", [])) if structured_summary else 0
            logger.info(f"영상 분석 완료 - 핵심 논점: {core_topics_count}개")

            # 5단계: Notion 페이지 생성
            notion_url = None
            if self.notion_service:
                logger.info("5/5: Notion 페이지 생성 중...")
                notion_data = {
                    "video_info": {**video_info, "url": url},
                    "full_summary": sections_data.get("full_summary", ""),
                    "structured_summary": structured_summary,
                    "sections": sections_data.get("sections", []),
                    "timeline": translated_timeline,
                    "language": source_lang,
                    "source": transcript_result["source"]
                }
                notion_result = self.notion_service.create_summary_page(notion_data)
                if notion_result.get("success"):
                    notion_url = notion_result.get("url")
                    logger.info(f"Notion 페이지 생성 완료: {notion_url}")
                else:
                    logger.warning(f"Notion 페이지 생성 실패: {notion_result.get('error')}")
            else:
                logger.info("5/5: Notion 설정 없음 - 건너뜀")

            # 결과 반환
            result = {
                "success": True,
                "video_info": video_info,
                "timeline": translated_timeline,
                "sections": sections_data.get("sections", []),
                "structured_summary": structured_summary,
                "full_summary": sections_data.get("full_summary", ""),
                "notion_url": notion_url,
                "language": source_lang,
                "source": transcript_result["source"],
                "message": "영상 처리 완료!" + (f" Notion: {notion_url}" if notion_url else "")
            }

            logger.info("영상 처리 완료!")
            return result

        except Exception as e:
            logger.error(f"영상 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"영상 처리 중 오류 발생: {str(e)}"
            }

    def process_video_quick(self, url: str, max_items: int = 50) -> Dict:
        """
        빠른 처리 (테스트용 - 제한된 항목만 처리)

        Args:
            url: YouTube URL
            max_items: 처리할 최대 항목 수

        Returns:
            처리 결과
        """
        try:
            # 기본 처리
            result = self.process_video(url)

            if result.get("success"):
                # 타임라인과 섹션 제한
                result["timeline"] = result["timeline"][:max_items]
                result["message"] = f"빠른 처리 완료 (처음 {max_items}개 항목만 처리)"

            return result

        except Exception as e:
            logger.error(f"빠른 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
