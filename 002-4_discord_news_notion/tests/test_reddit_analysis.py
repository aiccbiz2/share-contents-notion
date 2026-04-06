"""
Reddit 분석 프롬프트 테스트
TDD: 먼저 실패하는 테스트를 작성한 후 구현.
"""
import pytest
from datetime import datetime, timezone

from services.reddit_fetcher import RedditPost, Comment
from prompts.reddit_analysis import build_reddit_prompt


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_post(
    title="OpenAI releases new model",
    selftext="This is the post body about the new model.",
    external_url="",
    subreddit="r/technology",
    author="user123",
    score=2340,
    num_comments=456,
    created_utc=None,
    post_type="text",
    permalink="/r/technology/comments/xyz/openai_releases_new_model/",
    top_comments=None,
) -> RedditPost:
    """테스트용 RedditPost 헬퍼."""
    if created_utc is None:
        created_utc = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    if top_comments is None:
        top_comments = [
            Comment(author="commenter1", body="Great news!", score=890, depth=0),
            Comment(author="commenter2", body="Interesting.", score=654, depth=0),
        ]
    return RedditPost(
        title=title,
        selftext=selftext,
        external_url=external_url,
        subreddit=subreddit,
        author=author,
        score=score,
        num_comments=num_comments,
        created_utc=created_utc,
        post_type=post_type,
        permalink=permalink,
        top_comments=top_comments,
    )


DATABASE_ID = "test-database-id-12345"


# ===========================================================================
# 1. 기본 프롬프트 구조 테스트
# ===========================================================================

class TestBuildRedditPromptBasic:
    def test_build_reddit_prompt_basic(self):
        """RedditPost를 넣고 프롬프트 문자열 반환 확인. 필수 섹션 포함 여부."""
        post = _make_post()
        prompt = build_reddit_prompt(post, DATABASE_ID, shared_by="TestUser")

        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # 필수 섹션 포함 여부
        assert "Reddit 게시물" in prompt
        assert DATABASE_ID in prompt
        assert post.permalink in prompt
        assert post.subreddit in prompt
        assert "정리형" in prompt
        assert "설명형" in prompt
        assert "커뮤니티 반응" in prompt
        assert "NOTION_URL" in prompt
        assert "TestUser" in prompt


# ===========================================================================
# 2. 링크 게시물 → WebFetch 지시 포함
# ===========================================================================

class TestBuildRedditPromptLinkPost:
    def test_build_reddit_prompt_link_post(self):
        """post_type='link'이고 external_url이 있으면 'WebFetch' 지시 포함."""
        post = _make_post(
            post_type="link",
            external_url="https://example.com/article",
        )
        prompt = build_reddit_prompt(post, DATABASE_ID, shared_by="TestUser")

        assert "WebFetch" in prompt
        assert "https://example.com/article" in prompt


# ===========================================================================
# 3. 텍스트 게시물 → WebFetch 없음
# ===========================================================================

class TestBuildRedditPromptTextPost:
    def test_build_reddit_prompt_text_post_no_webfetch(self):
        """post_type='text'이면 'WebFetch'가 프롬프트에 없음."""
        post = _make_post(post_type="text", external_url="")
        prompt = build_reddit_prompt(post, DATABASE_ID, shared_by="TestUser")

        assert "WebFetch" not in prompt


# ===========================================================================
# 4. shared_by 기본값
# ===========================================================================

class TestBuildRedditPromptDefaultSharedBy:
    def test_build_reddit_prompt_default_shared_by(self):
        """shared_by='' → 'Discord Bot' 포함."""
        post = _make_post()
        prompt = build_reddit_prompt(post, DATABASE_ID, shared_by="")

        assert "Discord Bot" in prompt


# ===========================================================================
# 5. Callout 메타 정보 (콤마 포맷)
# ===========================================================================

class TestBuildRedditPromptMetaInCallout:
    def test_build_reddit_prompt_meta_in_callout(self):
        """프롬프트에 score와 num_comments가 콤마 포맷으로 포함."""
        post = _make_post(score=2340, num_comments=456)
        prompt = build_reddit_prompt(post, DATABASE_ID, shared_by="TestUser")

        assert "2,340" in prompt
        assert "456" in prompt


# ===========================================================================
# 6. 작성 스타일 지시 포함
# ===========================================================================

class TestBuildRedditPromptWritingStyle:
    def test_build_reddit_prompt_writing_style(self):
        """'축약 금지' 또는 '간결한 서술형' 관련 지시 포함, '2~3문장' 또는 '2-3문장' 포함."""
        post = _make_post()
        prompt = build_reddit_prompt(post, DATABASE_ID, shared_by="TestUser")

        # 간결한 서술형 관련 지시
        assert "간결한 서술형" in prompt or "축약 금지" in prompt

        # 2~3문장 또는 2-3문장 표현 포함
        assert "2~3문장" in prompt or "2-3문장" in prompt
