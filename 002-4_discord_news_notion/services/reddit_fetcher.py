"""
Reddit URL → 게시물 + 댓글 추출 모듈
Reddit .json 엔드포인트를 사용하여 게시물 본문, 상위 댓글, 메타데이터를 추출합니다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import requests
from loguru import logger


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

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
    external_url: str        # 링크 게시물의 외부 URL
    subreddit: str           # "r/python"
    author: str
    score: int               # upvotes
    num_comments: int
    created_utc: datetime
    post_type: str           # "text" | "link" | "image" | "video"
    permalink: str           # Reddit 원본 URL
    top_comments: list[Comment] = field(default_factory=list)

    def to_analysis_text(self) -> str:
        """Claude에 전달할 분석용 텍스트 조합."""
        lines: list[str] = []

        # 헤더
        lines.append("[Reddit 게시물]")
        lines.append(f"서브레딧: {self.subreddit}")
        lines.append(f"제목: {self.title}")
        lines.append(f"작성자: u/{self.author}")
        lines.append(
            f"작성일: {self.created_utc.strftime('%Y-%m-%d %H:%M')} UTC"
        )
        lines.append(
            f"추천수: {self.score:,} | 댓글수: {self.num_comments:,}"
        )
        lines.append(f"게시물 유형: {self.post_type}")
        lines.append("")

        # 본문
        if self.selftext:
            lines.append("[본문]")
            lines.append(self.selftext)
            lines.append("")

        # 외부 링크
        if self.external_url and self.post_type != "text":
            lines.append(f"[외부 링크] {self.external_url}")
            lines.append("")

        # 댓글
        if self.top_comments:
            lines.append(f"[상위 {len(self.top_comments)}개 댓글 반응]")
            idx = 1
            for comment in self.top_comments:
                prefix = f"  \u2514 " if comment.depth > 0 else ""
                lines.append(
                    f"{prefix}{idx}. u/{comment.author} "
                    f"(\u2191{comment.score:,}): \"{comment.body}\""
                )
                idx += 1

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# RedditFetcher
# ---------------------------------------------------------------------------

# 호스트 정규화 매핑
_HOST_MAP = {
    "old.reddit.com": "www.reddit.com",
    "m.reddit.com": "www.reddit.com",
    "new.reddit.com": "www.reddit.com",
}

MAX_COMMENTS = 20
MAX_COMMENT_BODY_LEN = 500
MAX_COMMENT_DEPTH = 1
USER_AGENT = "002-4-discord-news-bot/1.0"


class RedditFetcher:
    """Reddit .json 엔드포인트에서 게시물 + 댓글을 추출하는 클래스."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def fetch(self, url: str) -> RedditPost:
        """
        Reddit URL → RedditPost 객체 반환.

        1. URL 정규화 + .json 변환
        2. HTTP 요청 (429 시 30초 대기 1회 재시도)
        3. 게시물 + 댓글 파싱
        """
        json_url = self._to_json_url(url)
        logger.info(f"Reddit 게시물 가져오기: {json_url}")

        response = self._request_with_retry(json_url)
        data = response.json()

        # Reddit .json: [0]=게시물, [1]=댓글
        post_data = data[0]["data"]["children"][0]["data"]
        comment_children = data[1]["data"]["children"]

        post = self._parse_post(post_data)
        post.top_comments = self._parse_comments(comment_children)

        logger.info(
            f"Reddit 게시물 파싱 완료: {post.title} | "
            f"댓글 {len(post.top_comments)}개"
        )
        return post

    # ------------------------------------------------------------------
    # URL 정규화
    # ------------------------------------------------------------------

    def _to_json_url(self, url: str) -> str:
        """
        URL 정규화 + .json 변환.
        - old/m/new.reddit.com → www.reddit.com
        - 쿼리파라미터/앵커 제거
        - 경로 끝에 .json 추가
        """
        parsed = urlparse(url)

        # 호스트 정규화
        netloc = parsed.netloc.lower()
        netloc = _HOST_MAP.get(netloc, netloc)

        # 쿼리/앵커 제거, 경로 정리
        path = parsed.path.rstrip("/")
        if not path.endswith(".json"):
            path += "/.json"

        return urlunparse((parsed.scheme, netloc, path, "", "sort=top&limit=100", ""))

    # ------------------------------------------------------------------
    # HTTP 요청
    # ------------------------------------------------------------------

    def _request_with_retry(self, url: str) -> requests.Response:
        """
        GET 요청. 429 시 30초 대기 후 1회 재시도.
        그 외 에러는 raise_for_status().
        """
        response = self._session.get(url, timeout=15)

        if response.status_code == 429:
            logger.warning("Reddit 429 레이트리밋. 30초 대기 후 재시도...")
            time.sleep(30)
            response = self._session.get(url, timeout=15)

        response.raise_for_status()
        return response

    # ------------------------------------------------------------------
    # 파싱
    # ------------------------------------------------------------------

    def _parse_post(self, data: dict) -> RedditPost:
        """게시물 data dict → RedditPost."""
        post_type = self._determine_post_type(data)

        # external_url: 텍스트 게시물이 아닌 경우의 URL
        external_url = ""
        if not data.get("is_self", False):
            external_url = data.get("url", "")

        return RedditPost(
            title=data.get("title", ""),
            selftext=data.get("selftext", ""),
            external_url=external_url,
            subreddit=f"r/{data.get('subreddit', '')}",
            author=data.get("author", ""),
            score=data.get("score", 0),
            num_comments=data.get("num_comments", 0),
            created_utc=datetime.fromtimestamp(
                data.get("created_utc", 0), tz=timezone.utc
            ),
            post_type=post_type,
            permalink=data.get("permalink", ""),
        )

    @staticmethod
    def _determine_post_type(data: dict) -> str:
        """게시물 유형 판별: text / link / image / video."""
        if data.get("is_self", False):
            return "text"
        if data.get("is_video", False):
            return "video"

        post_hint = data.get("post_hint", "")
        if post_hint == "image":
            return "image"

        domain = data.get("domain", "")
        if domain in ("i.redd.it", "i.imgur.com"):
            return "image"
        if domain in ("v.redd.it", "youtube.com", "youtu.be"):
            return "video"

        return "link"

    def _parse_comments(
        self,
        children: list,
        depth: int = 0,
    ) -> list[Comment]:
        """
        댓글 children 리스트 → Comment 리스트.
        - score 기준 상위 MAX_COMMENTS 개만
        - depth 0 (최상위) + depth 1 (대댓글)까지만
        - [deleted]/[removed] 스킵
        - body 500자 제한
        """
        comments: list[Comment] = []
        self._collect_comments(children, depth, comments)

        # score 기준 정렬 후 상위 N개
        comments.sort(key=lambda c: c.score, reverse=True)
        return comments[:MAX_COMMENTS]

    def _collect_comments(
        self,
        children: list,
        depth: int,
        result: list[Comment],
    ) -> None:
        """재귀적으로 댓글 수집 (depth <= MAX_COMMENT_DEPTH)."""
        if depth > MAX_COMMENT_DEPTH:
            return

        for child in children:
            if child.get("kind") != "t1":
                continue

            data = child.get("data", {})
            author = data.get("author", "")
            body = data.get("body", "")

            # 삭제/제거 댓글 스킵
            if author in ("[deleted]", "[removed]"):
                continue
            if body in ("[deleted]", "[removed]"):
                continue

            # body 길이 제한
            if len(body) > MAX_COMMENT_BODY_LEN:
                body = body[:MAX_COMMENT_BODY_LEN]

            result.append(
                Comment(
                    author=author,
                    body=body,
                    score=data.get("score", 0),
                    depth=depth,
                )
            )

            # 대댓글 재귀 탐색
            replies = data.get("replies")
            if isinstance(replies, dict):
                reply_children = (
                    replies.get("data", {}).get("children", [])
                )
                self._collect_comments(reply_children, depth + 1, result)
