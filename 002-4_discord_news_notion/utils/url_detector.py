"""
URL 감지 및 분류 모듈
- YouTube/Instagram은 다른 봇(002-1, 002-3)이 처리하므로 제외
- 나머지 URL은 모두 허용
- 뉴스 vs 일반 URL 분류
"""
import re
from urllib.parse import urlparse

# URL 추출 정규식
URL_PATTERN = re.compile(
    r"https?://"                   # http:// or https://
    r"(?:[-\w.]|(?:%[\da-fA-F]{2}))+"  # domain
    r"(?:/[^\s]*)?"               # path (optional)
)

# 다른 봇이 처리하는 도메인 (002-4에서 제외)
EXCLUDED_DOMAINS = {
    "youtube.com", "youtu.be",         # 002-1
    "instagram.com", "instagr.am",     # 002-3
}

# 뉴스 도메인 (뉴스 3관점 분석 적용)
NEWS_DOMAINS = {
    # 국내
    "chosun.com", "joins.com", "hani.co.kr", "yna.co.kr",
    "mk.co.kr", "hankyung.com", "donga.com", "joongang.co.kr",
    "news.yna.co.kr", "news.naver.com", "news.daum.net",
    "bbc.co.kr", "zdnet.co.kr", "etnews.com", "dt.co.kr",
    "business.joins.com", "news1.kr", "newsis.com",
    "sedaily.com", "mt.co.kr", "edaily.co.kr",
    # 해외
    "nytimes.com", "bloomberg.com", "reuters.com",
    "techcrunch.com", "wsj.com", "theguardian.com",
    "ft.com", "economist.com", "wired.com",
    "apnews.com", "washingtonpost.com", "bbc.com",
    "cnn.com", "forbes.com", "businessinsider.com",
    "theverge.com", "arstechnica.com",
}

# 뉴스성 URL 경로 키워드
NEWS_PATH_KEYWORDS = [
    "/article", "/news", "/story", "/post",
    "/read", "/view", "/detail",
]


def extract_urls(text: str) -> list[str]:
    """메시지 텍스트에서 모든 URL 추출"""
    return URL_PATTERN.findall(text)


def get_domain(url: str) -> str:
    """URL에서 도메인 추출 (www. 제거)"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _is_excluded(domain: str) -> bool:
    """다른 봇이 처리하는 URL인지 확인"""
    for ed in EXCLUDED_DOMAINS:
        if domain == ed or domain.endswith("." + ed):
            return True
    return False


def is_news_url(url: str) -> bool:
    """뉴스 URL 여부 판단 (3관점 분석 적용 대상)"""
    domain = get_domain(url)

    # 뉴스 도메인 화이트리스트
    for nd in NEWS_DOMAINS:
        if domain == nd or domain.endswith("." + nd):
            return True

    # URL 경로에 뉴스 키워드 포함
    return any(kw in url.lower() for kw in NEWS_PATH_KEYWORDS)


def filter_valid_urls(urls: list[str]) -> list[str]:
    """URL 목록에서 처리 대상만 필터링 (YouTube/Instagram 제외, 중복 제거)"""
    seen = set()
    result = []
    for url in urls:
        domain = get_domain(url)
        if url not in seen and domain and not _is_excluded(domain):
            seen.add(url)
            result.append(url)
    return result
