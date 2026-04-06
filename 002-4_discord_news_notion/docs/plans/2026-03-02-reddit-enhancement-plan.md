# 002-4 Reddit Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 002-4 Discord News Analyzer에 Reddit URL 지원 추가 — .json 엔드포인트로 본문+상위 댓글+메타데이터 추출 후 3관점 분석 Notion 저장

**Architecture:** Reddit URL 감지 시 .json 엔드포인트에서 구조화된 데이터를 먼저 추출하고, 추출된 텍스트를 Claude CLI 프롬프트에 직접 삽입하여 Notion에 저장한다. 기존 뉴스 파이프라인과 분기하되 동일한 analyzer → Notion 흐름을 공유한다.

**Tech Stack:** Python 3, requests (기존 의존성), Reddit .json API (인증 불필요)

**Design Doc:** `docs/plans/2026-03-02-reddit-enhancement-design.md`

---

## Task 1: Reddit Fetcher 모듈 생성

**Files:**
- Create: `services/reddit_fetcher.py`

**Step 1: RedditFetcher 클래스 작성**

```python
"""
Reddit .json 엔드포인트를 사용한 게시물+댓글 추출 모듈.
API 인증 불필요. requests만 사용.
"""
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import requests
from loguru import logger

USER_AGENT = "002-4-discord-news-bot/1.0"
MAX_COMMENTS = 20


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
    external_url: str
    subreddit: str          # "r/python"
    author: str
    score: int
    num_comments: int
    created_utc: datetime
    post_type: str          # "text" | "link" | "image" | "video"
    permalink: str
    top_comments: list[Comment] = field(default_factory=list)

    def to_analysis_text(self) -> str:
        """Claude에 전달할 분석용 텍스트 조합"""
        lines = [
            f"[Reddit 게시물]",
            f"서브레딧: {self.subreddit}",
            f"제목: {self.title}",
            f"작성자: u/{self.author}",
            f"작성일: {self.created_utc.strftime('%Y-%m-%d %H:%M UTC')}",
            f"추천수: {self.score:,} | 댓글수: {self.num_comments:,}",
            f"게시물 유형: {self.post_type}",
        ]

        if self.selftext:
            lines.append(f"\n[본문]\n{self.selftext}")

        if self.external_url:
            lines.append(f"\n[외부 링크]\n{self.external_url}")

        if self.top_comments:
            lines.append(f"\n[상위 {len(self.top_comments)}개 댓글 반응]")
            for i, c in enumerate(self.top_comments, 1):
                prefix = "  └ " if c.depth > 0 else ""
                lines.append(
                    f"{prefix}{i}. u/{c.author} (↑{c.score:,}): {c.body}"
                )

        return "\n".join(lines)


class RedditFetcher:
    """Reddit .json 엔드포인트로 게시물+댓글 추출"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch(self, url: str) -> RedditPost:
        json_url = self._to_json_url(url)
        logger.info(f"Reddit .json 요청: {json_url}")

        resp = self._request_with_retry(json_url)
        data = resp.json()

        post_data = data[0]["data"]["children"][0]["data"]
        comments_data = data[1]["data"]["children"] if len(data) > 1 else []

        post = self._parse_post(post_data)
        post.top_comments = self._parse_comments(comments_data)

        logger.info(
            f"Reddit 추출 완료 | {post.subreddit} | "
            f"댓글 {len(post.top_comments)}개 | "
            f"본문 {len(post.selftext)}자"
        )
        return post

    def _to_json_url(self, url: str) -> str:
        """Reddit URL을 .json 엔드포인트로 변환"""
        parsed = urlparse(url)

        # old.reddit.com, m.reddit.com → www.reddit.com
        host = parsed.netloc.lower()
        host = re.sub(r"^(old|m|new)\.", "www.", host)
        if not host.startswith("www."):
            host = "www." + host

        # 경로에서 쿼리/앵커 제거, .json 추가
        path = parsed.path.rstrip("/")
        if not path.endswith(".json"):
            path += ".json"

        return urlunparse(("https", host, path, "", "sort=top&limit=100", ""))

    def _request_with_retry(self, url: str) -> requests.Response:
        """429 레이트리밋 시 30초 대기 후 1회 재시도"""
        resp = self.session.get(url, timeout=30)

        if resp.status_code == 429:
            logger.warning("Reddit 429 레이트리밋 — 30초 대기 후 재시도")
            time.sleep(30)
            resp = self.session.get(url, timeout=30)

        resp.raise_for_status()
        return resp

    def _parse_post(self, data: dict) -> RedditPost:
        """게시물 JSON → RedditPost"""
        # 게시물 유형 판별
        if data.get("is_self"):
            post_type = "text"
        elif data.get("is_video"):
            post_type = "video"
        elif data.get("post_hint") == "image" or data.get("url", "").endswith(
            (".jpg", ".png", ".gif", ".webp")
        ):
            post_type = "image"
        else:
            post_type = "link"

        external_url = ""
        if post_type != "text":
            external_url = data.get("url", "")

        return RedditPost(
            title=data.get("title", ""),
            selftext=data.get("selftext", ""),
            external_url=external_url,
            subreddit=f"r/{data.get('subreddit', 'unknown')}",
            author=data.get("author", "[deleted]"),
            score=data.get("score", 0),
            num_comments=data.get("num_comments", 0),
            created_utc=datetime.fromtimestamp(
                data.get("created_utc", 0), tz=timezone.utc
            ),
            post_type=post_type,
            permalink=f"https://www.reddit.com{data.get('permalink', '')}",
            top_comments=[],
        )

    def _parse_comments(
        self, children: list, depth: int = 0
    ) -> list[Comment]:
        """댓글 트리에서 상위 N개 추출 (depth 0-1만)"""
        comments = []
        for child in children:
            if child.get("kind") != "t1":
                continue
            if len(comments) >= MAX_COMMENTS:
                break

            cdata = child["data"]
            body = cdata.get("body", "").strip()
            if not body or body == "[deleted]" or body == "[removed]":
                continue

            comments.append(
                Comment(
                    author=cdata.get("author", "[deleted]"),
                    body=body[:500],  # 댓글 500자 제한
                    score=cdata.get("score", 0),
                    depth=depth,
                )
            )

            # depth 1까지만 (핵심 대댓글)
            if depth < 1:
                replies = cdata.get("replies")
                if isinstance(replies, dict):
                    reply_children = (
                        replies.get("data", {}).get("children", [])
                    )
                    comments.extend(
                        self._parse_comments(reply_children, depth + 1)
                    )

            if len(comments) >= MAX_COMMENTS:
                break

        return comments[:MAX_COMMENTS]
```

**Step 2: 수동 테스트**

Run: `cd "/Users/hh/Library/CloudStorage/GoogleDrive-davidlikessangria@gmail.com/My Drive/Python/002_Share_Contents_notion/002-4_discord_news_notion" && python3 -c "
from services.reddit_fetcher import RedditFetcher
f = RedditFetcher()
post = f.fetch('https://www.reddit.com/r/Python/comments/1j0wh1k/what_are_your_thoughts_on_uv/')
print(post.to_analysis_text()[:2000])
print(f'\n--- 댓글 {len(post.top_comments)}개 추출됨 ---')
"`

Expected: 게시물 제목, 본문, 상위 댓글이 출력됨

---

## Task 2: Reddit 분석 프롬프트 생성

**Files:**
- Create: `prompts/reddit_analysis.py`

**Step 1: Reddit 전용 프롬프트 작성**

```python
"""
Reddit 게시물 분석 + Notion 저장 프롬프트.
기존 뉴스 3관점 분석과 동일 구조 + 커뮤니티 반응 섹션 추가.
"""


def build_reddit_prompt(
    post,  # RedditPost
    database_id: str,
    shared_by: str = "",
) -> str:
    analysis_text = post.to_analysis_text()

    # 외부 링크 게시물이면 WebFetch 지시 추가
    webfetch_instruction = ""
    if post.post_type == "link" and post.external_url:
        webfetch_instruction = f"""
## 외부 링크 분석
이 게시물은 외부 링크를 공유한 것입니다. 아래 URL을 WebFetch로 읽고 분석에 포함하세요:
{post.external_url}
"""

    return f"""아래 Reddit 게시물과 커뮤니티 댓글 반응을 분석하여 Notion에 저장하세요. 한국어로 작성합니다.

## Reddit 게시물 데이터

{analysis_text}
{webfetch_instruction}
## Notion 데이터베이스 ID
{database_id}

## Notion 페이지 속성 (Properties)
- Name (Title): 게시물 핵심 주제를 한국어로 (단순 번역이 아닌 핵심 메시지가 드러나도록)
- URL (URL): {post.permalink}
- 언론사 (Select): {post.subreddit}
- 저장일 (Date): 오늘 날짜
- 공유자 (Rich text): {shared_by or "Discord Bot"}
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

핵심만 간결하게, 하지만 맥락은 살리는 서술형 요약. 축약하지 말고 2-3문장으로 충분히 설명.

### 5. 핵심 내용 — Heading 2: "핵심 내용"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 2~3문장으로 핵심 사실과 맥락을 간결하게 설명. 구체적 수치·이름·날짜 포함.

### 6. 시사점 — Heading 2: "시사점"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 2~3문장으로 왜 중요한지, 어떤 영향이 있는지 설명.

### 7. 비판적 관점 — Heading 2: "비판적 관점"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — 2~3문장으로 반론·리스크·한계를 근거와 함께 제시.

### 8. 커뮤니티 반응 — Heading 2: "💬 커뮤니티 반응"
- 2~3개 bulleted_list_item
- 댓글에서 나온 주요 의견, 반론, 인사이트를 간결하게 정리
- "u/username이 지적한 바와 같이..." 형태의 인용 허용
- 추천수가 높은 댓글의 의견을 우선 반영

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
- 각 항목 형식: **굵은 키워드** — "이 사건으로 인해 [누가] [어떤 영향]을 받으며, 그 결과 어떤 변화가 예상되는지"를 3~5문장 서술형으로 설명
- 업계 트렌드, 경쟁 구도, 구조적 영향을 분석

### 12. 비판적 관점 — Heading 2: "비판적 관점"
- 3~5개 bulleted_list_item
- 각 항목 형식: **굵은 키워드** — "~라고 하지만, 실제로는 ~" 또는 "~을 간과하고 있다. 왜냐하면 ~" 구조로 3~5문장 서술형 논리적 반론 제시

### 13. 커뮤니티 반응 — Heading 2: "💬 커뮤니티 반응"
- 3~5개 bulleted_list_item
- 각 댓글 의견에 대해 맥락과 함께 2~3문장으로 서술
- u/username 인용 포함, 추천수 높은 의견 우선
- 서로 상반된 의견이 있다면 대조하여 정리

## 작성 원칙
- 모든 bullet은 **굵은 키워드** — 설명 형식 통일
- 정리형: 2~3문장 간결한 서술형 (핵심만, 하지만 맥락은 살린다. 축약 금지!)
- 설명형: 3~5문장 충분한 서술형
- 게시물 속 구체적 수치·날짜·이름 등 팩트 반드시 포함
- 사실(게시물 내용)과 해석(시사점·비판)을 구분
- 영어 원문은 한국어로 번역하여 작성
- 도구 호출 확인 메시지 없이 바로 실행

## 완료 후
생성된 Notion 페이지 URL을 마지막 줄에 출력하세요.
형식: NOTION_URL: https://www.notion.so/...
"""
```

---

## Task 3: URL Detector에 Reddit 감지 추가

**Files:**
- Modify: `utils/url_detector.py:7-21`

**Step 1: Reddit 도메인 및 감지 함수 추가**

`url_detector.py`의 기존 코드에 추가:

```python
# 기존 EXCLUDED_DOMAINS 아래에 추가 (line 21 이후)

# Reddit 도메인 (전용 파이프라인 적용)
REDDIT_DOMAINS = {"reddit.com", "old.reddit.com", "new.reddit.com"}


def is_reddit_url(url: str) -> bool:
    """Reddit URL 여부 판단"""
    domain = get_domain(url)
    for rd in REDDIT_DOMAINS:
        if domain == rd or domain.endswith("." + rd):
            return True
    return False
```

---

## Task 4: Analyzer에 Reddit 분기 로직 추가

**Files:**
- Modify: `services/analyzer.py:1-10` (import 추가)
- Modify: `services/analyzer.py:34-50` (analyze_and_save 메서드 분기)

**Step 1: import 추가**

`analyzer.py` 상단에 추가:

```python
from utils.url_detector import is_reddit_url
from services.reddit_fetcher import RedditFetcher
from prompts.reddit_analysis import build_reddit_prompt

reddit_fetcher = RedditFetcher()
```

**Step 2: analyze_and_save 메서드에 Reddit 분기 추가**

기존 `analyze_and_save` 메서드의 prompt 생성 부분을 분기:

```python
def analyze_and_save(self, url: str, shared_by: str = "") -> AnalysisResult:
    # Reddit URL 분기
    if is_reddit_url(url):
        return self._analyze_reddit(url, shared_by)

    # 기존 뉴스 분석 (변경 없음)
    source = self._extract_source(url)
    prompt = build_news_prompt(...)
    ...  # 기존 코드 그대로
```

새 메서드 추가:

```python
def _analyze_reddit(self, url: str, shared_by: str = "") -> AnalysisResult:
    """Reddit URL 전용 분석 파이프라인"""
    # Step 1: Reddit .json으로 데이터 추출
    post = reddit_fetcher.fetch(url)
    logger.info(
        f"🔴 Reddit 게시물 추출 | {post.subreddit} | "
        f"⬆️{post.score:,} · 💬{post.num_comments:,}"
    )

    # Step 2: 프롬프트 생성
    prompt = build_reddit_prompt(
        post=post,
        database_id=config.NOTION_DATABASE_ID,
        shared_by=shared_by,
    )

    # Step 3: allowedTools 결정
    allowed_tools = "mcp__notion__*"
    if post.post_type == "link" and post.external_url:
        allowed_tools = "mcp__notion__*,WebFetch"

    logger.info(
        f"🤖 Claude CLI Reddit 분석 준비 | "
        f"프롬프트: {len(prompt)}자 | "
        f"allowedTools: {allowed_tools}"
    )

    # Step 4: Claude CLI 실행 (기존 _run_claude 로직 재사용)
    return self._run_claude(url, prompt, allowed_tools)
```

**Step 3: _run_claude 공통 메서드 추출**

기존 `analyze_and_save`의 Claude CLI 실행 부분을 `_run_claude`로 추출하여 뉴스/Reddit 공통 사용:

```python
def _run_claude(self, url: str, prompt: str, allowed_tools: str) -> AnalysisResult:
    """Claude CLI 실행 공통 로직 (뉴스/Reddit 공유)"""
    last_error = None
    for attempt in range(1, 4):
        try:
            logger.info(f"🚀 Claude CLI 실행 (시도 {attempt}/3)")
            start_time = time.time()

            env = {
                k: v for k, v in os.environ.items()
                if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")
            }

            proc = subprocess.Popen(
                [
                    config.CLAUDE_CLI_PATH,
                    "-p", prompt,
                    "--allowedTools", allowed_tools,
                    "--mcp-config", MCP_CONFIG_PATH,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )

            timed_out = False
            def _kill():
                nonlocal timed_out
                timed_out = True
                proc.kill()
            timer = threading.Timer(config.CLAUDE_TIMEOUT, _kill)
            timer.start()

            try:
                result_text, stderr_output = proc.communicate()
            except:
                proc.kill()
                result_text, stderr_output = proc.communicate()
            finally:
                timer.cancel()

            if timed_out:
                raise subprocess.TimeoutExpired(
                    config.CLAUDE_CLI_PATH, config.CLAUDE_TIMEOUT
                )

            elapsed = time.time() - start_time

            if proc.returncode != 0:
                error_msg = stderr_output.strip() or result_text[:300] or f"exit code: {proc.returncode}"
                raise RuntimeError(f"Claude CLI 오류: {error_msg[:300]}")

            logger.info(f"📝 Claude CLI 응답 완료 | 소요: {elapsed:.1f}초")

            notion_url = self._parse_notion_url(result_text)
            if notion_url:
                logger.info(f"✅ Notion 페이지 생성 완료 | URL: {notion_url}")
            else:
                logger.warning(f"⚠️ Notion URL 파싱 실패")

            return AnalysisResult(url=url, notion_url=notion_url)

        except subprocess.TimeoutExpired:
            last_error = RuntimeError(f"Claude CLI 타임아웃 ({config.CLAUDE_TIMEOUT}초)")
            logger.warning(f"⏰ 타임아웃 (시도 {attempt}/3)")
        except Exception as e:
            last_error = e
            logger.warning(f"❌ 실패 (시도 {attempt}/3): {e}")

    raise RuntimeError(f"AI 분석 실패 (3회 시도): {last_error}") from last_error
```

---

## Task 5: Discord 이벤트 핸들러 Reddit 메시지 대응

**Files:**
- Modify: `bot/events.py:19-20` (import 추가)
- Modify: `bot/events.py:136-138` (상태 메시지)
- Modify: `bot/events.py:211-224` (_build_reply)

**Step 1: import 추가**

```python
from utils.url_detector import extract_urls, filter_valid_urls, is_reddit_url
```

**Step 2: 상태 메시지에서 Reddit 구분 표시**

`events.py` line 136-138 수정:

```python
# Reddit 여부에 따라 이모지 변경
url_emoji = "🔴" if is_reddit_url(url) else "📰"
await status_msg.edit(
    content=f"**[{idx}/{total_urls}]** {url_emoji} `{short_url}`\n"
    f"▸ Claude CLI 분석 + Notion 저장 중... (1~3분 소요)"
)
```

**Step 3: 완료 메시지에서 Reddit 구분**

`_build_reply` 수정:

```python
def _build_reply(result, elapsed: float = 0) -> str:
    emoji = "🔴" if "reddit.com" in result.url else "📰"
    lines = [
        f"## {emoji} 분석 완료",
        f"> ⏱ {elapsed:.0f}초 소요",
    ]
    if result.notion_url:
        lines.append(f"📓 [**Notion에서 보기**]({result.notion_url})")
    else:
        lines.append("📓 Notion 저장 완료 (URL을 가져오지 못했습니다)")
    return "\n".join(lines)
```

---

## Task 6: 통합 수동 테스트

**Step 1: Reddit fetcher 단독 테스트**

Run: `python3 -c "from services.reddit_fetcher import RedditFetcher; f = RedditFetcher(); p = f.fetch('https://www.reddit.com/r/Python/comments/1j0wh1k/what_are_your_thoughts_on_uv/'); print(p.to_analysis_text()[:1500])"`

Expected: 게시물 제목, 본문, 댓글 출력

**Step 2: Discord 봇 실행 테스트**

Run: `python3 main.py`

테스트: Discord 채널에 Reddit URL 하나 붙여넣기
Expected:
1. ⏳ 리액션 추가
2. 🔴 상태 메시지 표시
3. Claude CLI 분석 실행
4. Notion 페이지 생성
5. ✅ 리액션으로 변경 + Notion 링크 회신

**Step 3: 엣지 케이스 테스트**

- `old.reddit.com` URL
- 외부 링크 게시물 (image/video/link)
- 삭제된 게시물 (404 처리 확인)
- 뉴스 URL과 Reddit URL 동시 전송 (각각 올바른 파이프라인 실행 확인)
