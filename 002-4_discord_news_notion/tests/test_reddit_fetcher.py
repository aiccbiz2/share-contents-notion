"""
Reddit Fetcher 모듈 테스트
TDD: 먼저 실패하는 테스트를 작성한 후 구현.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from services.reddit_fetcher import RedditFetcher, RedditPost, Comment


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_comment_child(author="user1", body="Hello", score=100, depth=0,
                        replies=None):
    """Reddit .json 포맷의 댓글 child dict 생성 헬퍼."""
    child = {
        "kind": "t1",
        "data": {
            "author": author,
            "body": body,
            "score": score,
            "depth": depth,
            "replies": "",
        },
    }
    if replies:
        child["data"]["replies"] = {
            "data": {
                "children": replies,
            }
        }
    return child


def _make_post_data(
    title="Test Post",
    selftext="This is a text post.",
    url="https://www.reddit.com/r/Python/comments/abc123/test_post/",
    subreddit="Python",
    author="testuser",
    score=1234,
    num_comments=56,
    created_utc=1709280000.0,  # 2024-03-01 12:00:00 UTC
    is_self=True,
    post_hint=None,
    permalink="/r/Python/comments/abc123/test_post/",
    domain="self.Python",
    is_video=False,
):
    """Reddit .json 포맷의 게시물 data dict 생성 헬퍼."""
    d = {
        "title": title,
        "selftext": selftext,
        "url": url,
        "subreddit": subreddit,
        "author": author,
        "score": score,
        "num_comments": num_comments,
        "created_utc": created_utc,
        "is_self": is_self,
        "permalink": permalink,
        "domain": domain,
        "is_video": is_video,
    }
    if post_hint:
        d["post_hint"] = post_hint
    return d


def _make_full_json_response(post_data, comment_children):
    """Reddit .json 전체 응답 구조 생성."""
    return [
        {
            "data": {
                "children": [
                    {"data": post_data}
                ]
            }
        },
        {
            "data": {
                "children": comment_children,
            }
        },
    ]


@pytest.fixture
def fetcher():
    return RedditFetcher()


# ===========================================================================
# 1-4: URL 정규화 테스트
# ===========================================================================

class TestToJsonUrl:
    def test_to_json_url_standard(self, fetcher):
        """표준 www.reddit.com URL → .json 변환."""
        url = "https://www.reddit.com/r/Python/comments/abc123/title/"
        result = fetcher._to_json_url(url)
        assert result == "https://www.reddit.com/r/Python/comments/abc123/title/.json?sort=top&limit=100"

    def test_to_json_url_old_reddit(self, fetcher):
        """old.reddit.com → www.reddit.com 변환 후 .json 추가."""
        url = "https://old.reddit.com/r/Python/comments/abc123/title/"
        result = fetcher._to_json_url(url)
        assert result == "https://www.reddit.com/r/Python/comments/abc123/title/.json?sort=top&limit=100"

    def test_to_json_url_mobile(self, fetcher):
        """m.reddit.com → www.reddit.com 변환 후 .json 추가."""
        url = "https://m.reddit.com/r/Python/comments/abc123/title/"
        result = fetcher._to_json_url(url)
        assert result == "https://www.reddit.com/r/Python/comments/abc123/title/.json?sort=top&limit=100"

    def test_to_json_url_strips_query(self, fetcher):
        """쿼리 파라미터와 앵커 제거 후 .json 추가."""
        url = "https://www.reddit.com/r/Python/comments/abc123/title/?ref=share&utm_source=reddit#top"
        result = fetcher._to_json_url(url)
        assert result == "https://www.reddit.com/r/Python/comments/abc123/title/.json?sort=top&limit=100"


# ===========================================================================
# 5-7: 게시물 파싱 테스트
# ===========================================================================

class TestParsePost:
    def test_parse_post_text(self, fetcher):
        """텍스트 게시물 (is_self=True) → post_type='text', selftext 채워짐."""
        data = _make_post_data(is_self=True, selftext="Body content here")
        post = fetcher._parse_post(data)

        assert isinstance(post, RedditPost)
        assert post.post_type == "text"
        assert post.selftext == "Body content here"
        assert post.title == "Test Post"
        assert post.subreddit == "r/Python"
        assert post.author == "testuser"
        assert post.score == 1234
        assert post.num_comments == 56
        assert isinstance(post.created_utc, datetime)

    def test_parse_post_link(self, fetcher):
        """링크 게시물 → post_type='link', external_url 채워짐."""
        data = _make_post_data(
            is_self=False,
            selftext="",
            url="https://example.com/article",
            domain="example.com",
            post_hint="link",
        )
        post = fetcher._parse_post(data)

        assert post.post_type == "link"
        assert post.external_url == "https://example.com/article"
        assert post.selftext == ""

    def test_parse_post_image(self, fetcher):
        """이미지 게시물 → post_type='image'."""
        data = _make_post_data(
            is_self=False,
            selftext="",
            url="https://i.redd.it/abc123.jpg",
            domain="i.redd.it",
            post_hint="image",
        )
        post = fetcher._parse_post(data)

        assert post.post_type == "image"


# ===========================================================================
# 8-12: 댓글 파싱 테스트
# ===========================================================================

class TestParseComments:
    def test_parse_comments_basic(self, fetcher):
        """기본 댓글 3개 파싱 → author, body, score, depth 정확."""
        children = [
            _make_comment_child("alice", "First!", 50, 0),
            _make_comment_child("bob", "Second!", 30, 0),
            _make_comment_child("charlie", "Third!", 10, 0),
        ]
        comments = fetcher._parse_comments(children)

        assert len(comments) == 3
        assert comments[0].author == "alice"
        assert comments[0].body == "First!"
        assert comments[0].score == 50
        assert comments[0].depth == 0

    def test_parse_comments_skip_deleted(self, fetcher):
        """[deleted]와 [removed] 댓글은 건너뜀."""
        children = [
            _make_comment_child("[deleted]", "[deleted]", 0, 0),
            _make_comment_child("[removed]", "[removed]", 0, 0),
            _make_comment_child("real_user", "Real comment", 100, 0),
        ]
        comments = fetcher._parse_comments(children)

        assert len(comments) == 1
        assert comments[0].author == "real_user"

    def test_parse_comments_max_limit(self, fetcher):
        """20개 초과 댓글 → 상위 20개만 반환."""
        children = [
            _make_comment_child(f"user{i}", f"Comment {i}", 100 - i, 0)
            for i in range(30)
        ]
        comments = fetcher._parse_comments(children)

        assert len(comments) == 20

    def test_parse_comments_with_replies(self, fetcher):
        """중첩 대댓글 → depth=1 포함."""
        reply = _make_comment_child("replier", "Reply!", 50, 1)
        parent = _make_comment_child("parent_user", "Parent!", 200, 0,
                                     replies=[reply])
        comments = fetcher._parse_comments([parent])

        assert len(comments) == 2
        depths = [c.depth for c in comments]
        assert 0 in depths
        assert 1 in depths
        reply_comment = [c for c in comments if c.depth == 1][0]
        assert reply_comment.author == "replier"

    def test_parse_comments_body_truncation(self, fetcher):
        """600자 body → 500자로 잘림."""
        long_body = "A" * 600
        children = [_make_comment_child("user", long_body, 10, 0)]
        comments = fetcher._parse_comments(children)

        assert len(comments[0].body) == 500


# ===========================================================================
# 13: to_analysis_text 테스트
# ===========================================================================

class TestToAnalysisText:
    def test_to_analysis_text(self):
        """RedditPost.to_analysis_text() → 포맷 검증."""
        post = RedditPost(
            title="OpenAI releases new model",
            selftext="This is the post body about the new model.",
            external_url="",
            subreddit="r/technology",
            author="user123",
            score=2340,
            num_comments=456,
            created_utc=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
            post_type="text",
            permalink="/r/technology/comments/xyz/openai_releases_new_model/",
            top_comments=[
                Comment(author="commenter1", body="Great news!", score=890, depth=0),
                Comment(author="replier", body="I agree!", score=123, depth=1),
                Comment(author="commenter2", body="Interesting.", score=654, depth=0),
            ],
        )

        text = post.to_analysis_text()

        # 핵심 섹션 존재 확인
        assert "[Reddit" in text  # 헤더
        assert "r/technology" in text
        assert "OpenAI releases new model" in text
        assert "u/user123" in text
        assert "2,340" in text  # 콤마 포맷
        assert "456" in text
        assert "text" in text
        assert "This is the post body" in text

        # 댓글 섹션
        assert "u/commenter1" in text
        assert "890" in text
        assert "u/replier" in text
        assert "u/commenter2" in text


# ===========================================================================
# 14-15: fetch 통합 테스트 (HTTP mocking)
# ===========================================================================

class TestFetch:
    def test_fetch_success(self, fetcher):
        """전체 .json 응답 mock → 올바른 RedditPost 반환."""
        post_data = _make_post_data()
        comment_children = [
            _make_comment_child("alice", "Great post!", 200, 0),
            _make_comment_child("bob", "Thanks!", 100, 0),
        ]
        json_response = _make_full_json_response(post_data, comment_children)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json_response
        mock_response.raise_for_status.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        fetcher._session = mock_session

        result = fetcher.fetch("https://www.reddit.com/r/Python/comments/abc123/test_post/")

        assert isinstance(result, RedditPost)
        assert result.title == "Test Post"
        assert result.subreddit == "r/Python"
        assert len(result.top_comments) == 2
        assert result.top_comments[0].author == "alice"

    def test_fetch_retry_on_429(self, fetcher):
        """첫 요청 429 → 30초 대기 후 재시도 → 두 번째 200 성공."""
        post_data = _make_post_data()
        json_response = _make_full_json_response(post_data, [])

        # 첫 번째 응답: 429
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        # 두 번째 응답: 200
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = json_response
        mock_response_200.raise_for_status.return_value = None

        mock_session = MagicMock()
        mock_session.get.side_effect = [mock_response_429, mock_response_200]
        fetcher._session = mock_session

        with patch("services.reddit_fetcher.time.sleep") as mock_sleep:
            result = fetcher.fetch("https://www.reddit.com/r/Python/comments/abc123/test_post/")

        assert isinstance(result, RedditPost)
        assert result.title == "Test Post"
        mock_sleep.assert_called_once_with(30)
        assert mock_session.get.call_count == 2
