"""
Discord 이벤트 핸들러 테스트 - _build_reply 함수
TDD: 먼저 실패하는 테스트를 작성하고, 구현 후 통과시킨다.
"""
import pytest

from bot.events import _build_reply
from services.analyzer import AnalysisResult


# --- _build_reply() 테스트 ---


def test_build_reply_news_url():
    """일반 뉴스 URL → 📰 이모지 사용"""
    result = AnalysisResult(
        url="https://www.nytimes.com/article",
        notion_url="https://www.notion.so/abc",
    )
    reply = _build_reply(result, elapsed=10.0)
    assert "\U0001f4f0" in reply  # 📰
    assert "\U0001f534" not in reply  # 🔴 should NOT appear


def test_build_reply_reddit_url():
    """Reddit URL → 🔴 이모지 사용"""
    result = AnalysisResult(
        url="https://www.reddit.com/r/Python/comments/abc/title",
        notion_url="https://www.notion.so/abc",
    )
    reply = _build_reply(result, elapsed=10.0)
    assert "\U0001f534" in reply  # 🔴
    assert "\U0001f4f0" not in reply  # 📰 should NOT appear


def test_build_reply_with_notion_url():
    """Notion URL이 있으면 'Notion에서 보기' 링크 포함"""
    result = AnalysisResult(
        url="https://www.nytimes.com/article",
        notion_url="https://www.notion.so/abc",
    )
    reply = _build_reply(result, elapsed=10.0)
    assert "Notion에서 보기" in reply
    assert "https://www.notion.so/abc" in reply


def test_build_reply_without_notion_url():
    """Notion URL이 없으면 'URL을 가져오지 못했습니다' 메시지 포함"""
    result = AnalysisResult(
        url="https://www.nytimes.com/article",
        notion_url="",
    )
    reply = _build_reply(result, elapsed=10.0)
    assert "URL을 가져오지 못했습니다" in reply


def test_build_reply_elapsed_time():
    """elapsed=45.7 → '46초 소요' (반올림)"""
    result = AnalysisResult(
        url="https://www.nytimes.com/article",
        notion_url="https://www.notion.so/abc",
    )
    reply = _build_reply(result, elapsed=45.7)
    assert "46초 소요" in reply
