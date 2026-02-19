"""
유틸리티 함수들
"""
import re
from typing import Optional


def extract_video_id(url: str) -> Optional[str]:
    """
    YouTube URL에서 video ID 추출

    지원 형식:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&list=...
    - https://youtu.be/VIDEO_ID
    - https://youtu.be/VIDEO_ID?si=...
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - VIDEO_ID (11자리 ID만 입력한 경우)
    """
    if not url:
        return None

    url = url.strip()

    # 11자리 영상 ID만 입력한 경우
    if re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url

    patterns = [
        # youtu.be 단축 URL (쿼리 파라미터 포함)
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        # youtube.com/watch?v= 형식
        r'youtube\.com\/watch\?.*v=([0-9A-Za-z_-]{11})',
        # youtube.com/embed/ 형식
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        # youtube.com/v/ 형식
        r'youtube\.com\/v\/([0-9A-Za-z_-]{11})',
        # youtube.com/shorts/ 형식
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        # 일반적인 v= 파라미터
        r'[?&]v=([0-9A-Za-z_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def format_timestamp(seconds: float) -> str:
    """
    초를 HH:MM:SS 또는 MM:SS 형식으로 변환

    Args:
        seconds: 초 단위 시간

    Returns:
        형식화된 타임스탬프 문자열
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
