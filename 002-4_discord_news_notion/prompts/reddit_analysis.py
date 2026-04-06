"""
Reddit 게시물 전용 AI 분석 + Notion 저장 프롬프트 (MCP 방식)
Claude CLI가 Reddit 게시물과 커뮤니티 댓글을 분석하여 3관점 + 커뮤니티 반응 섹션으로 Notion에 저장.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.reddit_fetcher import RedditPost


def build_reddit_prompt(post: RedditPost, database_id: str, shared_by: str = "") -> str:
    """
    RedditPost 객체를 받아 Claude CLI용 분석 프롬프트 문자열을 반환한다.

    Args:
        post: RedditPost 데이터클래스 인스턴스
        database_id: Notion 데이터베이스 ID
        shared_by: 공유자 이름 (빈 문자열이면 "Discord Bot")

    Returns:
        Claude CLI에 전달할 프롬프트 문자열
    """
    display_shared_by = shared_by or "Discord Bot"

    # 외부 링크 분석 섹션 (조건부)
    external_link_section = ""
    if post.post_type == "link" and post.external_url:
        external_link_section = f"""
## 외부 링크 분석
이 게시물은 외부 링크를 공유한 것입니다. WebFetch로 아래 URL을 읽고 내용을 함께 분석하세요.
- 외부 URL: {post.external_url}
"""

    return f"""아래 Reddit 게시물과 커뮤니티 댓글 반응을 분석하여 Notion에 저장하세요. 한국어로 작성합니다.

## Reddit 게시물 데이터
{post.to_analysis_text()}
{external_link_section}
## Notion 데이터베이스 ID
{database_id}

## Notion 페이지 속성 (Properties)
- Name (Title): 게시물 핵심 주제를 한국어로 (핵심 메시지가 드러나도록)
- URL (URL): {post.permalink}
- 언론사 (Select): {post.subreddit}
- 저장일 (Date): 오늘 날짜
- 공유자 (Rich text): {display_shared_by}
- Tag (Multi-select): 관련 태그 3~5개

## Notion 페이지 본문 (Blocks) — 아래 순서대로 정확히 작성

본문은 **[Version 1] 정리형**과 **[Version 2] 설명형** 두 버전을 순서대로 모두 작성한다.

### 1. 원문 링크
- bookmark 블록으로 Reddit 원본 URL 삽입: {post.permalink}

### 2. Divider

### 3. 한 줄 요약 — Callout (💡, blue_background)
- 전체 내용을 한 문장으로 압축 (50자 이내)
- 메타 정보 포함: ⬆️ {post.score:,} · 💬 {post.num_comments:,} · {post.subreddit}

### 4. Divider

---

## [Version 1] 정리형 — Heading 1: "📋 정리형"

간결하고 빠르게 훑을 수 있는 버전. 각 bullet은 2~3문장 간결한 서술형 (축약 금지!).

### 5. 핵심 내용 — Heading 2: "핵심 내용"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 2~3문장 간결한 서술형으로 핵심 팩트 요약 (수치·기업명·날짜 포함)

### 6. 시사점 — Heading 2: "시사점"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 2~3문장 간결한 서술형으로 영향·변화 요약

### 7. 비판적 관점 — Heading 2: "비판적 관점"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 2~3문장 간결한 서술형으로 반론·리스크 요약

### 8. 💬 커뮤니티 반응 — Heading 2: "💬 커뮤니티 반응"
- 2~3개 bulleted_list_item
- 댓글 주요 의견 정리, u/username 인용 허용
- 각 항목: 핵심 의견 요약 + 대표 댓글 인용

### 9. Divider

---

## [Version 2] 설명형 — Heading 1: "📖 설명형"

맥락과 인과관계가 드러나는 서술형 분석. 게시물 전문을 읽지 않아도 흐름과 의미를 이해할 수 있도록 충분히 설명.

### 10. 핵심 내용 — Heading 2: "핵심 내용"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드(2~4단어)** — 배경, 구체적 수치·날짜·기업명·인물·금액 등을 포함해 3~5문장 서술형으로 설명
- "왜 발생했는지 → 무엇이 일어났는지 → 어떤 의미인지"가 드러나도록 작성

### 11. 시사점 — Heading 2: "시사점"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 3~5문장 서술형으로 업계 트렌드, 경쟁 구도, 소비자·정책·투자 환경 변화 등 구조적 영향 분석

### 12. 비판적 관점 — Heading 2: "비판적 관점"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 3~5문장 서술형으로 논리적 반론 제시

### 13. 💬 커뮤니티 반응 — Heading 2: "💬 커뮤니티 반응"
- 3~5개 bulleted_list_item
- 댓글 인용 포함, u/username 인용 허용
- 각 항목: 의견 흐름 분석 + 대표 댓글 직접 인용

## 작성 원칙
- 모든 bullet은 **굵은 키워드** — 설명 형식 통일
- 정리형: 2~3문장 간결한 서술형 (축약 금지!)
- 설명형: 3~5문장 충분한 서술형
- 게시물 속 구체적 수치·날짜·기업명 등 팩트 반드시 포함
- 사실(게시물 내용)과 해석(시사점·비판)을 구분
- 도구 호출 확인 없이 바로 실행

## 완료 후
생성된 Notion 페이지 URL을 마지막 줄에 출력하세요.
형식: NOTION_URL: https://www.notion.so/...
"""
