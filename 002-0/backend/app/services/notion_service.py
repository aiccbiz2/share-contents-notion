"""
Notion 페이지 생성 서비스
"""
from notion_client import Client
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotionService:
    """Notion API 연동 서비스"""

    def __init__(self, api_key: str, parent_page_id: str):
        """
        Args:
            api_key: Notion Integration API Key
            parent_page_id: 부모 페이지 ID (하위에 페이지 생성)
        """
        self.client = Client(auth=api_key)
        self.parent_page_id = parent_page_id
        logger.info("Notion 서비스 초기화 완료")

    def create_summary_page(self, data: Dict) -> Dict:
        """
        YouTube 영상 요약 페이지 생성 (범용 회의록 스타일)

        Args:
            data: 영상 처리 결과 데이터
                - video_info: 영상 정보 (title, author, length, url)
                - full_summary: 전체 요약
                - structured_summary: 범용 구조 데이터
                - timeline: 자막 타임라인
                - language: 원본 언어
                - source: 추출 방식

        Returns:
            생성된 페이지 정보 (id, url)
        """
        try:
            video_info = data.get("video_info", {})
            structured_summary = data.get("structured_summary", {})
            timeline = data.get("timeline", [])
            language = data.get("language", "unknown")
            source = data.get("source", "unknown")

            # 페이지 제목 생성: YYYYMMDD_동영상제목
            today = datetime.now().strftime("%Y%m%d")
            video_title = video_info.get("title", "제목 없음")
            page_title = f"{today}_{video_title}"

            # 추출 방식 텍스트
            source_text = "동영상 자막 추출" if source == "youtube" else "동영상 음성 텍스트 변환 (Whisper)"

            # 원본 언어 텍스트
            lang_map = {"ko": "한국어", "en": "영어", "ja": "일본어", "zh": "중국어"}
            lang_text = lang_map.get(language, language)

            # 번역 여부
            translated = "번역됨 (한국어)" if language != "ko" else "원본 (한국어)"

            # 영상 길이 포맷 (length 또는 duration 키 사용)
            duration = video_info.get("length") or video_info.get("duration", 0)
            duration_text = self._format_duration(duration)

            # 채널명 (author 또는 channel 키 사용)
            channel = video_info.get("author") or video_info.get("channel", "알 수 없음")

            # 페이지 콘텐츠 블록 생성 (자막 원본 제외)
            children = self._build_structured_page_content(
                video_info=video_info,
                channel=channel,
                source_text=source_text,
                lang_text=lang_text,
                translated=translated,
                duration_text=duration_text,
                structured_summary=structured_summary,
                timeline=[]  # 자막은 나중에 별도로 추가
            )

            # Notion API 블록 제한: 한 번에 100개까지만 가능
            MAX_BLOCKS_PER_REQUEST = 100

            if len(children) <= MAX_BLOCKS_PER_REQUEST:
                # 100개 이하: 한 번에 생성
                new_page = self.client.pages.create(
                    parent={"page_id": self.parent_page_id},
                    properties={
                        "title": {
                            "title": [
                                {
                                    "type": "text",
                                    "text": {"content": page_title}
                                }
                            ]
                        }
                    },
                    children=children
                )
            else:
                # 100개 초과: 나눠서 생성
                first_batch = children[:MAX_BLOCKS_PER_REQUEST]
                remaining_batches = [
                    children[i:i + MAX_BLOCKS_PER_REQUEST]
                    for i in range(MAX_BLOCKS_PER_REQUEST, len(children), MAX_BLOCKS_PER_REQUEST)
                ]

                # 첫 번째 배치로 페이지 생성
                new_page = self.client.pages.create(
                    parent={"page_id": self.parent_page_id},
                    properties={
                        "title": {
                            "title": [
                                {
                                    "type": "text",
                                    "text": {"content": page_title}
                                }
                            ]
                        }
                    },
                    children=first_batch
                )

                page_id = new_page["id"]

                # 나머지 배치 추가
                for batch_idx, batch in enumerate(remaining_batches):
                    try:
                        self.client.blocks.children.append(
                            block_id=page_id,
                            children=batch
                        )
                        logger.info(f"블록 배치 {batch_idx + 2} 추가 완료 ({len(batch)}개)")
                    except Exception as batch_error:
                        logger.warning(f"블록 배치 {batch_idx + 2} 추가 실패: {batch_error}")

            page_id = new_page["id"]

            # 자막 원본 섹션 별도 추가 (1000개 블록 제한 우회)
            if timeline:
                self._add_timeline_section(page_id, timeline)

            result = {
                "success": True,
                "page_id": new_page["id"],
                "url": new_page["url"],
                "title": page_title
            }

            logger.info(f"Notion 페이지 생성 완료: {page_title} (총 {len(children)}개 블록)")
            return result

        except Exception as e:
            logger.error(f"Notion 페이지 생성 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_structured_page_content(
        self,
        video_info: Dict,
        channel: str,
        source_text: str,
        lang_text: str,
        translated: str,
        duration_text: str,
        structured_summary: Dict,
        timeline: List[Dict]
    ) -> List[Dict]:
        """범용 회의록 스타일 페이지 콘텐츠 블록 생성"""
        blocks = []

        # === 기본 정보 섹션 ===
        blocks.append(self._heading2("📋 기본 정보"))

        # 영상 URL (북마크)
        url = video_info.get("url", "")
        if url:
            blocks.append({
                "object": "block",
                "type": "bookmark",
                "bookmark": {"url": url}
            })

            # YouTube 영상 임베딩 (바로 재생 가능)
            blocks.append({
                "object": "block",
                "type": "video",
                "video": {
                    "type": "external",
                    "external": {"url": url}
                }
            })

        # 기본 정보
        blocks.append(self._bullet(f"📺 채널: {channel}"))
        blocks.append(self._bullet(f"⏱️ 영상 길이: {duration_text}"))
        blocks.append(self._bullet(f"🗓️ 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
        blocks.append(self._bullet(f"📝 추출 방식: {source_text}"))
        blocks.append(self._bullet(f"🌐 원본 언어: {lang_text}"))
        blocks.append(self._bullet(f"🔄 번역 여부: {translated}"))

        blocks.append(self._divider())

        # === 1) 영상 개요 ===
        blocks.append(self._heading2("📌 영상 개요"))
        overview = structured_summary.get("overview", "") if structured_summary else ""
        if overview:
            blocks.append(self._paragraph(overview))
        else:
            blocks.append(self._paragraph("개요 없음"))

        blocks.append(self._divider())

        # === 2) 주요 내용 요약 ===
        blocks.append(self._heading2("📑 주요 내용 요약"))

        # 계층 구조(sections) 확인 - 새로운 형식
        sections = structured_summary.get("sections", []) if structured_summary else []

        if sections:
            # 계층 구조 형식으로 렌더링
            for i, section in enumerate(sections, 1):
                section_title = section.get("section_title", f"섹션 {i}")
                section_summary = section.get("section_summary", "")
                subtopics = section.get("subtopics", [])

                # 대주제 (Heading 2)
                blocks.append(self._heading2(f"{i}. {section_title}"))

                # 섹션 요약 (있는 경우)
                if section_summary:
                    blocks.append(self._paragraph(section_summary))

                # 하위 주제들
                for j, subtopic in enumerate(subtopics, 1):
                    sub_title = subtopic.get("title", f"하위 주제 {j}")
                    sub_content = subtopic.get("content", "")

                    # 하위 주제 제목 (Heading 3)
                    blocks.append(self._heading3(f"{i}.{j} {sub_title}"))

                    if sub_content:
                        blocks.extend(self._split_long_paragraph(sub_content))

                blocks.append(self._divider())
        else:
            # 기존 평탄 구조(main_topics) 형식으로 렌더링 (하위 호환성)
            main_topics = structured_summary.get("main_topics", []) if structured_summary else []
            if main_topics:
                for i, topic in enumerate(main_topics, 1):
                    title = topic.get("title", "주제")
                    content = topic.get("content", "")
                    # 제목을 Heading 3으로 표시
                    blocks.append(self._heading3(f"{i}. {title}"))
                    if content:
                        # 긴 내용은 여러 문단으로 나눠서 표시
                        blocks.extend(self._split_long_paragraph(content))
            else:
                blocks.append(self._paragraph("주요 내용 없음"))

        # 주요 내용 요약 후 항상 구분선 추가
        blocks.append(self._divider())

        # === 핵심 용어 정리 (있는 경우만) ===
        key_terms = structured_summary.get("key_terms", []) if structured_summary else []
        if key_terms:
            blocks.append(self._heading2("📚 핵심 용어 정리"))
            for term_item in key_terms:
                term = term_item.get("term", "")
                definition = term_item.get("definition", "")
                if term:
                    blocks.append(self._bullet(f"**{term}**: {definition}"))
            blocks.append(self._divider())

        # === 3) 핵심 인사이트 / 결론 ===
        blocks.append(self._heading2("💡 핵심 인사이트 / 결론"))
        key_insights = structured_summary.get("key_insights", "") if structured_summary else ""
        if key_insights:
            blocks.append(self._paragraph(key_insights))
        else:
            blocks.append(self._paragraph("핵심 인사이트 없음"))

        blocks.append(self._divider())

        # === 4) 선택적 섹션 (있는 경우만) ===
        optional_sections = structured_summary.get("optional_sections", []) if structured_summary else []
        if optional_sections:
            blocks.append(self._heading2("📎 추가 정보"))
            for section in optional_sections:
                section_title = section.get("title", "")
                section_content = section.get("content", "")
                if section_title:
                    blocks.append(self._bullet(f"▶ {section_title}"))
                if section_content:
                    blocks.append(self._paragraph(f"   {section_content}"))
            blocks.append(self._divider())

        # 자막 원본은 별도 메서드(_add_timeline_section)에서 추가됨
        # (1000개 블록 제한 우회를 위해 개별 API 호출로 처리)

        return blocks

    def _split_long_paragraph(self, text: str, max_length: int = 1800) -> List[Dict]:
        """긴 텍스트를 여러 문단으로 분할"""
        if len(text) <= max_length:
            return [self._paragraph(text)]

        paragraphs = []
        sentences = text.replace('. ', '.|').split('|')
        current_para = ""

        for sentence in sentences:
            if len(current_para) + len(sentence) <= max_length:
                current_para += sentence
            else:
                if current_para:
                    paragraphs.append(self._paragraph(current_para.strip()))
                current_para = sentence

        if current_para:
            paragraphs.append(self._paragraph(current_para.strip()))

        return paragraphs if paragraphs else [self._paragraph(text[:max_length] + "...")]

    def _heading2(self, text: str) -> Dict:
        """Heading 2 블록"""
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    def _heading3(self, text: str) -> Dict:
        """Heading 3 블록"""
        if len(text) > 2000:
            text = text[:1997] + "..."
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    def _paragraph(self, text: str) -> Dict:
        """Paragraph 블록"""
        # Notion API 텍스트 길이 제한 (2000자)
        if len(text) > 2000:
            text = text[:1997] + "..."
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    def _bullet(self, text: str) -> Dict:
        """Bullet list item 블록"""
        if len(text) > 2000:
            text = text[:1997] + "..."
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    def _toggle(self, title: str, children: List[Dict]) -> Dict:
        """Toggle 블록"""
        if len(title) > 2000:
            title = title[:1997] + "..."
        return {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": title}}],
                "children": children
            }
        }

    def _divider(self) -> Dict:
        """Divider 블록"""
        return {
            "object": "block",
            "type": "divider",
            "divider": {}
        }

    def _format_duration(self, seconds: int) -> str:
        """초를 시:분:초 형식으로 변환"""
        if not seconds:
            return "알 수 없음"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}시간 {minutes}분 {secs}초"
        elif minutes > 0:
            return f"{minutes}분 {secs}초"
        else:
            return f"{secs}초"

    def _chunk_timeline(self, timeline: List[Dict], chunk_size: int = 50) -> List[List[Dict]]:
        """타임라인을 청크로 분할"""
        chunks = []
        for i in range(0, len(timeline), chunk_size):
            chunks.append(timeline[i:i + chunk_size])
        return chunks

    def _add_timeline_section(self, page_id: str, timeline: List[Dict]) -> None:
        """
        자막 원본 섹션을 별도로 추가 (1000개 블록 제한 우회)

        각 토글을 개별 API 호출로 추가하여 한 요청당 블록 수를 최소화
        """
        try:
            # 자막 원본 헤더 추가
            self.client.blocks.children.append(
                block_id=page_id,
                children=[self._heading2("📜 자막 원본")]
            )

            # 자막을 50개씩 청크로 분할
            timeline_chunks = self._chunk_timeline(timeline, chunk_size=50)
            total_chunks = len(timeline_chunks)

            # 각 토글을 개별적으로 추가 (API 제한 우회)
            for i, chunk in enumerate(timeline_chunks):
                toggle_title = f"📄 자막 파트 {i + 1} ({len(chunk)}개 항목)"
                toggle_children = []

                for item in chunk:
                    time = item.get("time", "00:00")
                    text = item.get("text", "")
                    toggle_children.append(self._paragraph(f"[{time}] {text}"))

                toggle_block = self._toggle(toggle_title, toggle_children)

                try:
                    self.client.blocks.children.append(
                        block_id=page_id,
                        children=[toggle_block]
                    )
                except Exception as toggle_error:
                    logger.warning(f"자막 토글 {i + 1} 추가 실패: {toggle_error}")
                    continue

            logger.info(f"자막 원본 추가 완료: {total_chunks}개 토글")

        except Exception as e:
            logger.warning(f"자막 원본 섹션 추가 실패: {e}")
