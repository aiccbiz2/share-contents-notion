# 002-4 Reddit 보완 설계

## 개요

002-4 Discord News Analyzer에 Reddit URL 지원을 추가한다.
Reddit `.json` 엔드포인트로 본문+상위 10-20개 댓글+메타데이터를 추출하고,
기존 3관점 분석 포맷으로 Notion에 저장한다.

## 접근법

**Reddit `.json` 엔드포인트 방식** 채택.
- API 인증 불필요 (즉시 시작 가능)
- 구조화된 JSON 데이터 → 메타데이터 정확
- 나중에 PRAW 전환 용이 (fetcher만 교체)

## 데이터 흐름

```
Discord에 Reddit URL 공유
    ↓
url_detector.py: is_reddit_url() 감지
    ↓
reddit_fetcher.py: URL + ".json" 호출
    → 본문 (title, selftext, external_url)
    → 메타데이터 (subreddit, upvotes, 댓글수, 작성자, 작성일)
    → 상위 10-20개 댓글 (sort=top)
    → 텍스트로 조합
    ↓
analyzer.py: Reddit이면 reddit_analysis 프롬프트 사용
    → Claude CLI (-p prompt --allowedTools mcp__notion__*)
    → 외부 링크 게시물이면 WebFetch도 허용
    ↓
Notion 저장 (기존 DB, 3관점 포맷)
    → 언론사 = "r/{subreddit명}"
    ↓
Discord 응답 (⏳ → ✅)
```

## 변경 파일

| 파일 | 변경 |
|------|------|
| `services/reddit_fetcher.py` | 신규 — .json 호출, 본문+댓글+메타 추출 |
| `prompts/reddit_analysis.py` | 신규 — Reddit 전용 프롬프트 |
| `utils/url_detector.py` | 수정 — is_reddit_url() 추가 |
| `services/analyzer.py` | 수정 — Reddit 분기 로직 |
| `bot/events.py` | 수정 — Reddit URL 피드백 메시지 |

## reddit_fetcher.py 설계

```python
@dataclass
class Comment:
    author: str
    body: str
    score: int
    depth: int  # 0=최상위, 1=대댓글

@dataclass
class RedditPost:
    title: str
    selftext: str
    external_url: str       # 링크 게시물의 외부 URL
    subreddit: str          # "r/python"
    author: str
    score: int              # upvotes
    num_comments: int
    created_utc: datetime
    post_type: str          # "text" | "link" | "image" | "video"
    permalink: str          # Reddit 원본 URL
    top_comments: list[Comment]

    def to_analysis_text(self) -> str:
        """Claude에 전달할 분석용 텍스트 조합"""
```

### URL 정규화

- `old.reddit.com` → `www.reddit.com`
- `m.reddit.com` → `www.reddit.com`
- 쿼리파라미터/앵커 제거 후 `.json` 추가
- User-Agent 헤더 필수

### .json 응답 구조

Reddit `.json`은 2개 배열 반환:
- `[0]`: 게시물 데이터
- `[1]`: 댓글 트리 (재귀 구조)

댓글은 `score` 기준 정렬 후 상위 10-20개만 추출.
depth=0 (최상위) + depth=1 (핵심 대댓글)까지만.

## reddit_analysis.py 프롬프트 설계

### Notion 속성

| 속성 | 값 |
|------|-----|
| Name | 게시물 제목 (한국어 번역) |
| URL | Reddit 원본 URL |
| 언론사 | r/{subreddit명} |
| 저장일 | 오늘 날짜 |
| 공유자 | Discord 사용자명 |
| Tag | 3-5개 자동 태그 |

### Notion 블록 구조

1. Bookmark (Reddit URL)
2. Divider
3. Callout: 한줄 요약 + 메타 (⬆️ 2,340 · 💬 456 · r/technology)
4. Divider
5. **[Version 1] 정리형** — H1
   - 핵심 내용 (H2) — 3-5 bullets, 각 2-3문장 (간결한 서술형)
   - 시사점 (H2) — 3-5 bullets, 각 2-3문장
   - 비판적 관점 (H2) — 3-5 bullets, 각 2-3문장
   - 커뮤니티 반응 (H2) — 2-3 bullets, 댓글에서 나온 주요 의견/인사이트
6. Divider
7. **[Version 2] 설명형** — H1
   - 핵심 내용 (H2) — 3-5 bullets, 각 3-5문장 (깊은 배경/분석)
   - 시사점 (H2) — 3-5 bullets, 각 3-5문장
   - 비판적 관점 (H2) — 3-5 bullets, 각 3-5문장
   - 커뮤니티 반응 (H2) — 3-5 bullets, 댓글 인용 포함

### 작성 스타일

- **간결한 서술형**: 핵심만 담되 맥락은 살린다. 축약 금지.
- **`**키워드** — 2-3문장 설명`** 형식
- 구체적 숫자/날짜/이름/회사명 반드시 포함
- 사실과 해석을 구분
- 댓글 인용 시 "u/username이 지적한 바와 같이..." 허용
- 모든 내용 한국어로 작성 (영어 원문은 번역)

## url_detector.py 변경

```python
REDDIT_DOMAINS = {"reddit.com", "old.reddit.com", "new.reddit.com"}

def is_reddit_url(url: str) -> bool:
    domain = get_domain(url)
    return any(domain == rd or domain.endswith("." + rd) for rd in REDDIT_DOMAINS)
```

## analyzer.py 분기 로직

```python
from utils.url_detector import is_reddit_url
from services.reddit_fetcher import RedditFetcher
from prompts.reddit_analysis import build_reddit_prompt

reddit_fetcher = RedditFetcher()

def analyze_and_save(self, url, shared_by=""):
    if is_reddit_url(url):
        post = reddit_fetcher.fetch(url)
        source = post.subreddit
        prompt = build_reddit_prompt(post, database_id, shared_by)
        allowed_tools = "mcp__notion__*"
        # 외부 링크 게시물이면 WebFetch도 허용
        if post.post_type == "link" and post.external_url:
            allowed_tools = "mcp__notion__*,WebFetch"
    else:
        source = self._extract_source(url)
        prompt = build_news_prompt(url, source, database_id, shared_by)
        allowed_tools = "mcp__notion__*,WebFetch"
```

## 에러 처리

- Reddit .json 429 (레이트리밋): 30초 대기 후 1회 재시도
- Reddit .json 403/404: 에러 메시지 반환, Discord에 알림
- JSON 파싱 실패: fallback으로 WebFetch 시도 (기존 뉴스 파이프라인)
