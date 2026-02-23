"""
URL → 기사 본문 on-demand 추출 모듈
유저가 디스코드에 공유한 URL에서 기사 내용을 가져옵니다.
"""
from dataclasses import dataclass, field
from urllib.parse import urlparse

from loguru import logger

# newspaper3k import (설치 여부 체크)
try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    logger.warning("newspaper3k가 설치되지 않았습니다. BeautifulSoup fallback을 사용합니다.")

import requests
from bs4 import BeautifulSoup


@dataclass
class ArticleData:
    title: str
    content: str
    url: str
    source: str
    published_date: str = ""
    is_partial: bool = False   # 본문 추출 실패 시 True (제목만 있는 경우)


class ArticleFetcher:
    """URL에서 기사 본문을 추출하는 클래스"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def fetch(self, url: str) -> ArticleData:
        """
        URL에서 기사 본문 추출.
        1차: newspaper3k / 2차: BeautifulSoup / 3차: 제목만 반환
        """
        source = self._extract_source(url)
        logger.info(f"📥 본문 추출 시작 | URL: {url} | 출처: {source}")

        # 1차: newspaper3k
        np_result = None
        if NEWSPAPER_AVAILABLE:
            np_result = self._fetch_with_newspaper(url, source)
            if np_result:
                logger.info(
                    f"✅ [newspaper3k] 추출 성공 | "
                    f"제목: {np_result.title[:50]} | "
                    f"본문: {len(np_result.content)}자 | "
                    f"partial: {np_result.is_partial}"
                )
                # 본문이 충분하면 바로 반환, 부족하면 BS4로 재시도
                if not np_result.is_partial:
                    return np_result
                logger.info("⚠️ [newspaper3k] 본문 부족, BeautifulSoup으로 재시도")
            else:
                logger.info("⚠️ [newspaper3k] 추출 실패, BeautifulSoup으로 재시도")

        # 2차: BeautifulSoup fallback
        bs_result = self._fetch_with_bs4(url, source)
        if bs_result:
            logger.info(
                f"✅ [BeautifulSoup] 추출 성공 | "
                f"제목: {bs_result.title[:50]} | "
                f"본문: {len(bs_result.content)}자 | "
                f"partial: {bs_result.is_partial}"
            )
            # BS4가 더 나은 결과면 BS4 사용, 아니면 newspaper3k 결과 사용
            if np_result and len(np_result.content) >= len(bs_result.content):
                return np_result
            return bs_result

        # newspaper3k 결과가 있으면 (본문 부족해도) 사용
        if np_result:
            return np_result

        # 3차: 최소 정보만 반환
        logger.warning(f"❌ 본문 추출 실패, 제목만 반환: {url}")
        return ArticleData(
            title=url,
            content="",
            url=url,
            source=source,
            is_partial=True,
        )

    def _fetch_with_newspaper(self, url: str, source: str) -> ArticleData | None:
        try:
            article = Article(url, language="ko")
            article.download()
            article.parse()

            if not article.title:
                return None

            content = article.text or ""
            published = (
                article.publish_date.strftime("%Y-%m-%d")
                if article.publish_date
                else ""
            )

            return ArticleData(
                title=article.title,
                content=content[:4000],  # 최대 4000자
                url=url,
                source=source,
                published_date=published,
                is_partial=len(content) < 100,
            )
        except Exception as e:
            logger.debug(f"newspaper3k 실패: {e}")
            return None

    def _fetch_with_bs4(self, url: str, source: str) -> ArticleData | None:
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # 제목 추출 (우선순위: og:title > h1 > title tag)
            title = ""
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content", "")
            if not title:
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else ""
            if not title:
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else url

            # 본문 추출 (article > main > p 태그 순)
            content = ""
            article_tag = soup.find("article") or soup.find("main")
            if article_tag:
                paragraphs = article_tag.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs)
            if not content:
                paragraphs = soup.find_all("p")
                content = " ".join(p.get_text(strip=True) for p in paragraphs[:30])

            if not title:
                return None

            return ArticleData(
                title=title,
                content=content[:4000],
                url=url,
                source=source,
                is_partial=len(content) < 100,
            )
        except Exception as e:
            logger.debug(f"BeautifulSoup 실패: {e}")
            return None

    @staticmethod
    def _extract_source(url: str) -> str:
        """URL에서 언론사 도메인 추출"""
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"
