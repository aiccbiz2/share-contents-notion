"""
URL Detector 테스트 — Reddit URL 감지 기능
TDD: 먼저 실패하는 테스트를 작성하고, 구현 후 통과시킨다.
"""
import pytest

from utils.url_detector import (
    EXCLUDED_DOMAINS,
    filter_valid_urls,
    is_reddit_url,
)


# --- is_reddit_url() 테스트 ---

def test_is_reddit_url_www():
    """www.reddit.com → True (www. 제거 후 reddit.com 매칭)"""
    assert is_reddit_url("https://www.reddit.com/r/Python/comments/abc/") is True


def test_is_reddit_url_old():
    """old.reddit.com → True (REDDIT_DOMAINS에 직접 포함)"""
    assert is_reddit_url("https://old.reddit.com/r/Python/comments/abc/") is True


def test_is_reddit_url_new():
    """new.reddit.com → True (REDDIT_DOMAINS에 직접 포함)"""
    assert is_reddit_url("https://new.reddit.com/r/Python/comments/abc/") is True


def test_is_reddit_url_mobile():
    """m.reddit.com → True (endswith('.reddit.com') 매칭)"""
    assert is_reddit_url("https://m.reddit.com/r/Python/comments/abc/") is True


def test_is_reddit_url_bare():
    """reddit.com (www 없이) → True"""
    assert is_reddit_url("https://reddit.com/r/Python/comments/abc/") is True


def test_is_reddit_url_not_reddit():
    """nytimes.com → False"""
    assert is_reddit_url("https://www.nytimes.com/article") is False


def test_is_reddit_url_youtube():
    """youtube.com → False"""
    assert is_reddit_url("https://youtube.com/watch?v=abc") is False


# --- filter_valid_urls()와의 통합 테스트 ---

def test_reddit_url_not_excluded():
    """Reddit URL은 EXCLUDED_DOMAINS에 없으므로 filter_valid_urls를 통과해야 함"""
    urls = ["https://www.reddit.com/r/Python/comments/abc/"]
    result = filter_valid_urls(urls)
    assert result == urls
    # 추가 확인: reddit.com이 EXCLUDED_DOMAINS에 없는지 직접 검증
    assert "reddit.com" not in EXCLUDED_DOMAINS


def test_filter_still_excludes_youtube():
    """YouTube URL은 여전히 필터링되어야 함"""
    urls = ["https://youtube.com/watch?v=abc"]
    result = filter_valid_urls(urls)
    assert result == []
