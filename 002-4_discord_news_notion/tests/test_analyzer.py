"""
NewsAnalyzer Reddit 분기 로직 테스트
TDD: Red → Green 순서로 진행
"""
import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.analyzer import AnalysisResult, NewsAnalyzer
from services.reddit_fetcher import RedditPost


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analyzer():
    return NewsAnalyzer()


@pytest.fixture
def reddit_post_text():
    """post_type='text' 인 RedditPost fixture"""
    return RedditPost(
        title="Test Reddit Post",
        selftext="This is a test post body",
        external_url="",
        subreddit="r/python",
        author="testuser",
        score=1500,
        num_comments=200,
        created_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
        post_type="text",
        permalink="https://www.reddit.com/r/python/comments/abc123/test/",
        top_comments=[],
    )


@pytest.fixture
def reddit_post_link():
    """post_type='link' + external_url 있는 RedditPost fixture"""
    return RedditPost(
        title="Test Link Post",
        selftext="",
        external_url="https://example.com/article",
        subreddit="r/technology",
        author="linkuser",
        score=3000,
        num_comments=500,
        created_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
        post_type="link",
        permalink="https://www.reddit.com/r/technology/comments/def456/link/",
        top_comments=[],
    )


# ---------------------------------------------------------------------------
# Test 1: Reddit URL → Reddit 파이프라인 라우팅
# ---------------------------------------------------------------------------

@patch("services.analyzer.reddit_fetcher")
@patch.object(NewsAnalyzer, "_run_claude")
@patch("services.analyzer.is_reddit_url", return_value=True)
def test_analyze_reddit_url_routes_to_reddit_pipeline(
    mock_is_reddit, mock_run_claude, mock_fetcher, analyzer, reddit_post_text
):
    """Reddit URL이면 reddit_fetcher.fetch()가 호출되고,
    _run_claude에 전달된 prompt에 'Reddit'이 포함되어야 한다."""
    mock_fetcher.fetch.return_value = reddit_post_text
    mock_run_claude.return_value = AnalysisResult(
        url="https://reddit.com/r/python/comments/abc123/test/",
        notion_url="https://www.notion.so/abc",
    )

    result = analyzer.analyze_and_save(
        "https://reddit.com/r/python/comments/abc123/test/",
        shared_by="tester",
    )

    # reddit_fetcher.fetch() 호출됨
    mock_fetcher.fetch.assert_called_once_with(
        "https://reddit.com/r/python/comments/abc123/test/"
    )
    # _run_claude 호출됨
    mock_run_claude.assert_called_once()
    # prompt에 "Reddit" 포함
    call_args = mock_run_claude.call_args
    prompt_arg = call_args[0][1]  # (url, prompt, allowed_tools)
    assert "Reddit" in prompt_arg


# ---------------------------------------------------------------------------
# Test 2: 뉴스 URL → 뉴스 파이프라인 라우팅
# ---------------------------------------------------------------------------

@patch("services.analyzer.reddit_fetcher")
@patch.object(NewsAnalyzer, "_run_claude")
@patch("services.analyzer.is_reddit_url", return_value=False)
def test_analyze_news_url_routes_to_news_pipeline(
    mock_is_reddit, mock_run_claude, mock_fetcher, analyzer
):
    """비-Reddit URL이면 reddit_fetcher.fetch()는 호출되지 않고,
    _run_claude가 WebFetch 포함 allowed_tools로 호출되어야 한다."""
    mock_run_claude.return_value = AnalysisResult(
        url="https://techcrunch.com/article/123",
        notion_url="https://www.notion.so/def",
    )

    result = analyzer.analyze_and_save(
        "https://techcrunch.com/article/123",
        shared_by="tester",
    )

    # reddit_fetcher.fetch()는 호출 안 됨
    mock_fetcher.fetch.assert_not_called()
    # _run_claude 호출됨
    mock_run_claude.assert_called_once()
    # allowed_tools에 WebFetch 포함
    call_args = mock_run_claude.call_args
    allowed_tools_arg = call_args[0][2]  # (url, prompt, allowed_tools)
    assert allowed_tools_arg == "mcp__notion__*,WebFetch"


# ---------------------------------------------------------------------------
# Test 3: Reddit link post → WebFetch 포함
# ---------------------------------------------------------------------------

@patch("services.analyzer.reddit_fetcher")
@patch.object(NewsAnalyzer, "_run_claude")
@patch("services.analyzer.is_reddit_url", return_value=True)
def test_analyze_reddit_link_post_allows_webfetch(
    mock_is_reddit, mock_run_claude, mock_fetcher, analyzer, reddit_post_link
):
    """Reddit link 게시물 (external_url 있음)이면
    _run_claude에 'mcp__notion__*,WebFetch' 전달."""
    mock_fetcher.fetch.return_value = reddit_post_link
    mock_run_claude.return_value = AnalysisResult(
        url="https://reddit.com/r/technology/comments/def456/link/",
        notion_url="https://www.notion.so/ghi",
    )

    analyzer.analyze_and_save(
        "https://reddit.com/r/technology/comments/def456/link/"
    )

    call_args = mock_run_claude.call_args
    allowed_tools_arg = call_args[0][2]
    assert allowed_tools_arg == "mcp__notion__*,WebFetch"


# ---------------------------------------------------------------------------
# Test 4: Reddit text post → WebFetch 없음
# ---------------------------------------------------------------------------

@patch("services.analyzer.reddit_fetcher")
@patch.object(NewsAnalyzer, "_run_claude")
@patch("services.analyzer.is_reddit_url", return_value=True)
def test_analyze_reddit_text_post_no_webfetch(
    mock_is_reddit, mock_run_claude, mock_fetcher, analyzer, reddit_post_text
):
    """Reddit text 게시물이면
    _run_claude에 'mcp__notion__*' (WebFetch 없음) 전달."""
    mock_fetcher.fetch.return_value = reddit_post_text
    mock_run_claude.return_value = AnalysisResult(
        url="https://reddit.com/r/python/comments/abc123/test/",
        notion_url="https://www.notion.so/jkl",
    )

    analyzer.analyze_and_save(
        "https://reddit.com/r/python/comments/abc123/test/"
    )

    call_args = mock_run_claude.call_args
    allowed_tools_arg = call_args[0][2]
    assert allowed_tools_arg == "mcp__notion__*"


# ---------------------------------------------------------------------------
# Test 5: _run_claude 성공 시 AnalysisResult 반환
# ---------------------------------------------------------------------------

@patch("services.analyzer.config")
@patch("subprocess.Popen")
def test_run_claude_success(mock_popen, mock_config, analyzer):
    """subprocess 성공 시 NOTION_URL 파싱 + AnalysisResult 반환"""
    mock_config.CLAUDE_CLI_PATH = "/usr/bin/claude"
    mock_config.CLAUDE_TIMEOUT = 300

    proc_mock = MagicMock()
    proc_mock.communicate.return_value = (
        "분석 완료\nNOTION_URL: https://www.notion.so/abc123",
        "",
    )
    proc_mock.returncode = 0
    mock_popen.return_value = proc_mock

    result = analyzer._run_claude(
        url="https://example.com",
        prompt="test prompt",
        allowed_tools="mcp__notion__*,WebFetch",
    )

    assert isinstance(result, AnalysisResult)
    assert result.url == "https://example.com"
    assert result.notion_url == "https://www.notion.so/abc123"


# ---------------------------------------------------------------------------
# Test 6: _run_claude 첫 시도 실패 → 두 번째 성공 (재시도)
# ---------------------------------------------------------------------------

@patch("services.analyzer.config")
@patch("subprocess.Popen")
def test_run_claude_retry_on_failure(mock_popen, mock_config, analyzer):
    """첫 시도 실패, 두 번째 성공 → 재시도 동작 확인 (2회 호출)"""
    mock_config.CLAUDE_CLI_PATH = "/usr/bin/claude"
    mock_config.CLAUDE_TIMEOUT = 300

    # 첫 번째: returncode=1 (실패), 두 번째: 성공
    proc_fail = MagicMock()
    proc_fail.communicate.return_value = ("error output", "some error")
    proc_fail.returncode = 1

    proc_success = MagicMock()
    proc_success.communicate.return_value = (
        "OK\nNOTION_URL: https://www.notion.so/retry-ok",
        "",
    )
    proc_success.returncode = 0

    mock_popen.side_effect = [proc_fail, proc_success]

    result = analyzer._run_claude(
        url="https://example.com",
        prompt="test prompt",
        allowed_tools="mcp__notion__*",
    )

    assert mock_popen.call_count == 2
    assert result.notion_url == "https://www.notion.so/retry-ok"


# ---------------------------------------------------------------------------
# Test 7: _run_claude 타임아웃 → 3회 모두 실패 → RuntimeError
# ---------------------------------------------------------------------------

@patch("services.analyzer.config")
@patch("subprocess.Popen")
def test_run_claude_timeout(mock_popen, mock_config, analyzer):
    """3회 모두 타임아웃 → RuntimeError 발생"""
    mock_config.CLAUDE_CLI_PATH = "/usr/bin/claude"
    mock_config.CLAUDE_TIMEOUT = 1  # 극단적으로 짧게

    # communicate에서 예외 발생 시뮬레이션
    proc_mock = MagicMock()
    proc_mock.communicate.side_effect = subprocess.TimeoutExpired(
        cmd="/usr/bin/claude", timeout=1
    )
    proc_mock.kill.return_value = None
    mock_popen.return_value = proc_mock

    with pytest.raises(RuntimeError, match="AI 분석 실패"):
        analyzer._run_claude(
            url="https://example.com",
            prompt="test prompt",
            allowed_tools="mcp__notion__*",
        )

    assert mock_popen.call_count == 3
