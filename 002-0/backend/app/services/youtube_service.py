"""
YouTube 자막 추출 서비스
"""
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from typing import Dict, List, Optional
import os
import logging
import requests
from app.utils.helpers import extract_video_id, format_timestamp
from app.config import settings
from pytubefix import YouTube
import yt_dlp

logger = logging.getLogger(__name__)

# youtube-transcript-api 인스턴스
ytt_api = YouTubeTranscriptApi()


class YouTubeService:
    """YouTube 영상 처리 서비스"""

    def __init__(self):
        self.temp_audio_dir = "temp_audio"
        os.makedirs(self.temp_audio_dir, exist_ok=True)

    def get_video_info(self, url: str) -> Dict:
        """
        YouTube 영상 기본 정보 가져오기

        1순위: YouTube Data API v3 (배포 환경에서 안정적)
        2순위: pytubefix (로컬 환경)
        3순위: yt-dlp (fallback)

        Args:
            url: YouTube URL

        Returns:
            영상 정보 딕셔너리
        """
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("유효하지 않은 YouTube URL입니다.")

        logger.info(f"영상 정보 가져오기 시작: {video_id}")

        # 1순위: YouTube Data API v3 사용 (배포 환경에서 봇 감지 회피)
        if settings.YOUTUBE_API_KEY:
            try:
                logger.info("YouTube Data API v3로 영상 정보 가져오기 시도")
                api_url = "https://www.googleapis.com/youtube/v3/videos"
                params = {
                    "part": "snippet,contentDetails",
                    "id": video_id,
                    "key": settings.YOUTUBE_API_KEY
                }
                response = requests.get(api_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if data.get("items"):
                    item = data["items"][0]
                    snippet = item.get("snippet", {})
                    content_details = item.get("contentDetails", {})

                    # ISO 8601 duration을 초로 변환 (PT1H2M3S -> 3723)
                    duration_str = content_details.get("duration", "PT0S")
                    duration_seconds = self._parse_iso8601_duration(duration_str)

                    result = {
                        "video_id": video_id,
                        "title": snippet.get("title", "Unknown"),
                        "author": snippet.get("channelTitle", "Unknown"),
                        "length": duration_seconds,
                        "url": url,
                        "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url")
                    }
                    logger.info(f"YouTube Data API 성공: {result['title']}")
                    return result
                else:
                    logger.warning("YouTube Data API: 영상을 찾을 수 없음")
            except Exception as api_error:
                logger.warning(f"YouTube Data API 실패: {api_error}, pytubefix로 재시도")

        # 2순위: pytubefix 사용
        try:
            logger.info("pytubefix로 영상 정보 가져오기 시도")
            yt = YouTube(url)
            result = {
                "video_id": video_id,
                "title": yt.title,
                "author": yt.author,
                "length": yt.length,
                "url": url
            }
            logger.info(f"pytubefix 성공: {yt.title}")
            return result
        except Exception as pytubefix_error:
            logger.warning(f"pytubefix 실패: {pytubefix_error}, yt-dlp로 재시도")

        # 3순위: yt-dlp 사용 (fallback)
        try:
            logger.info("yt-dlp로 영상 정보 가져오기 시도")
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            result = {
                "video_id": video_id,
                "title": info.get('title', 'Unknown'),
                "author": info.get('uploader', 'Unknown'),
                "length": info.get('duration', 0),
                "url": url
            }
            logger.info(f"yt-dlp 성공: {info.get('title')}")
            return result
        except Exception as yt_dlp_error:
            logger.error(f"yt-dlp도 실패: {yt_dlp_error}")
            raise ValueError(f"영상 정보를 가져올 수 없습니다: {yt_dlp_error}")

    def _parse_iso8601_duration(self, duration: str) -> int:
        """
        ISO 8601 duration을 초로 변환
        예: PT1H2M3S -> 3723초
        """
        import re
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def get_transcript(self, video_id: str) -> Dict:
        """
        YouTube 자막 추출 (우선순위: 한국어 > 영어 > 기타)

        1순위: Supadata API (클라우드 환경에서 안정적, IP 차단 회피)
        2순위: YouTube Data API v3
        3순위: youtube-transcript-api (로컬 환경)

        Args:
            video_id: YouTube 비디오 ID

        Returns:
            자막 데이터 딕셔너리
            {
                "data": [{"text": "...", "start": 0.0, "duration": 2.5}, ...],
                "language": "ko" 또는 "en" 등,
                "source": "youtube"
            }
        """
        # 1순위: Supadata API 사용 (클라우드 환경에서 IP 차단 회피)
        if settings.SUPADATA_API_KEY:
            try:
                result = self._get_transcript_supadata(video_id)
                if result.get("success"):
                    return result
                logger.warning(f"Supadata API 자막 실패: {result.get('error')}, YouTube Data API로 재시도")
            except Exception as supadata_error:
                logger.warning(f"Supadata API 자막 실패: {supadata_error}, YouTube Data API로 재시도")

        # 2순위: YouTube Data API v3 사용
        if settings.YOUTUBE_API_KEY:
            try:
                result = self._get_transcript_api(video_id)
                if result.get("success"):
                    return result
                logger.warning(f"YouTube Data API 자막 실패: {result.get('error')}, youtube-transcript-api로 재시도")
            except Exception as api_error:
                logger.warning(f"YouTube Data API 자막 실패: {api_error}, youtube-transcript-api로 재시도")

        # 3순위: youtube-transcript-api 사용 (fallback)
        return self._get_transcript_scraping(video_id)

    def _get_transcript_supadata(self, video_id: str) -> Dict:
        """Supadata API를 사용하여 자막 가져오기 (클라우드 환경에서 IP 차단 회피)"""
        logger.info(f"Supadata API로 자막 추출 시도: {video_id}")

        supadata_url = "https://api.supadata.ai/v1/youtube/transcript"
        headers = {
            "x-api-key": settings.SUPADATA_API_KEY
        }
        params = {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "text": "false"  # 타임스탬프 포함된 상세 데이터 요청
        }

        try:
            response = requests.get(supadata_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Supadata API 응답 처리
            # 응답 형식: {"content": [{"text": "...", "offset": 0, "duration": 2500}, ...], "lang": "ko"}
            content = data.get("content", [])
            lang = data.get("lang", "unknown")

            if not content:
                logger.warning("Supadata API: 자막 데이터 없음")
                return {
                    "data": None,
                    "language": None,
                    "source": None,
                    "success": False,
                    "error": "자막 없음"
                }

            # Supadata 형식을 내부 형식으로 변환
            transcript_data = []
            for item in content:
                transcript_data.append({
                    "text": item.get("text", "").strip(),
                    "start": item.get("offset", 0) / 1000,  # ms -> seconds
                    "duration": item.get("duration", 0) / 1000  # ms -> seconds
                })

            logger.info(f"Supadata API 자막 추출 성공: {lang}, {len(transcript_data)}개 항목")
            return {
                "data": transcript_data,
                "language": lang,
                "source": "supadata",
                "success": True
            }

        except requests.exceptions.HTTPError as e:
            error_msg = f"Supadata API HTTP 오류: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text}"
            logger.warning(error_msg)
            return {
                "data": None,
                "language": None,
                "source": None,
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            logger.warning(f"Supadata API 오류: {e}")
            return {
                "data": None,
                "language": None,
                "source": None,
                "success": False,
                "error": str(e)
            }

    def _get_transcript_api(self, video_id: str) -> Dict:
        """YouTube Data API v3를 사용하여 자막 가져오기"""
        # 1. 사용 가능한 자막 목록 가져오기
        captions_url = "https://www.googleapis.com/youtube/v3/captions"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "key": settings.YOUTUBE_API_KEY
        }
        response = requests.get(captions_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        captions = data.get("items", [])
        if not captions:
            return {
                "data": None,
                "language": None,
                "source": None,
                "success": False,
                "error": "자막 없음"
            }

        # 언어 우선순위로 자막 선택
        preferred_langs = ['ko', 'en']
        selected_caption = None
        selected_lang = None

        for lang in preferred_langs:
            for caption in captions:
                caption_lang = caption.get("snippet", {}).get("language", "")
                if caption_lang == lang:
                    selected_caption = caption
                    selected_lang = lang
                    break
            if selected_caption:
                break

        # 우선순위 언어 없으면 첫 번째 자막 사용
        if not selected_caption and captions:
            selected_caption = captions[0]
            selected_lang = selected_caption.get("snippet", {}).get("language", "unknown")

        logger.info(f"YouTube API 자막 선택: {selected_lang}")

        # 2. 자막 내용 가져오기 (timedtext API 사용)
        # YouTube Data API의 captions.download는 OAuth가 필요하므로 timedtext 사용
        timedtext_url = f"https://www.youtube.com/api/timedtext"
        timedtext_params = {
            "v": video_id,
            "lang": selected_lang,
            "fmt": "json3"
        }

        try:
            tt_response = requests.get(timedtext_url, params=timedtext_params, timeout=10)
            tt_response.raise_for_status()
            tt_data = tt_response.json()

            events = tt_data.get("events", [])
            transcript_data = []

            for event in events:
                if "segs" in event:
                    text = "".join(seg.get("utf8", "") for seg in event.get("segs", []))
                    if text.strip():
                        transcript_data.append({
                            "text": text.strip(),
                            "start": event.get("tStartMs", 0) / 1000,
                            "duration": event.get("dDurationMs", 0) / 1000
                        })

            if transcript_data:
                logger.info(f"YouTube API 자막 추출 성공: {selected_lang}, {len(transcript_data)}개 항목")
                return {
                    "data": transcript_data,
                    "language": selected_lang,
                    "source": "youtube_api",
                    "success": True
                }
        except Exception as e:
            logger.warning(f"timedtext API 실패: {e}")

        return {
            "data": None,
            "language": None,
            "source": None,
            "success": False,
            "error": "자막 다운로드 실패"
        }

    def _get_transcript_scraping(self, video_id: str) -> Dict:
        """youtube-transcript-api를 사용하여 자막 가져오기 (fallback)"""
        try:
            # 사용 가능한 자막 목록 가져오기
            transcript_list = ytt_api.list(video_id)
            available_langs = [t.language_code for t in transcript_list]
            logger.info(f"사용 가능한 자막: {available_langs}")

            # 언어 우선순위
            preferred_langs = ['ko', 'en']
            selected_lang = None

            # 우선순위대로 자막 찾기
            for lang in preferred_langs:
                if lang in available_langs:
                    selected_lang = lang
                    break

            # 우선순위 언어 없으면 첫 번째 언어 사용
            if not selected_lang and available_langs:
                selected_lang = available_langs[0]

            if not selected_lang:
                return {
                    "data": None,
                    "language": None,
                    "source": None,
                    "success": False,
                    "error": "자막 없음 - Whisper API 필요"
                }

            # 자막 가져오기
            transcript = ytt_api.fetch(video_id, languages=[selected_lang])

            # snippets를 dict 리스트로 변환
            data = [
                {
                    "text": snippet.text,
                    "start": snippet.start,
                    "duration": snippet.duration
                }
                for snippet in transcript.snippets
            ]

            logger.info(f"자막 추출 성공: {selected_lang}, {len(data)}개 항목")
            return {
                "data": data,
                "language": selected_lang,
                "source": "youtube",
                "success": True
            }

        except TranscriptsDisabled:
            logger.warning(f"비디오 {video_id}의 자막이 비활성화되어 있습니다.")
            return {
                "data": None,
                "language": None,
                "source": None,
                "success": False,
                "error": "자막 비활성화"
            }
        except NoTranscriptFound:
            logger.warning(f"비디오 {video_id}에 자막이 없습니다.")
            return {
                "data": None,
                "language": None,
                "source": None,
                "success": False,
                "error": "자막 없음 - Whisper API 필요"
            }
        except Exception as e:
            logger.error(f"자막 추출 실패: {e}")
            return {
                "data": None,
                "language": None,
                "source": None,
                "success": False,
                "error": str(e)
            }

    def download_audio(self, url: str, video_id: str) -> Optional[str]:
        """
        YouTube 오디오 다운로드 (Whisper 사용 시)

        Args:
            url: YouTube URL
            video_id: 비디오 ID

        Returns:
            다운로드된 오디오 파일 경로 또는 None
        """
        try:
            audio_path = os.path.join(self.temp_audio_dir, f"{video_id}.mp3")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            logger.info(f"오디오 다운로드 완료: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"오디오 다운로드 실패: {e}")
            return None

    def format_timeline(self, transcript_data: List[Dict]) -> List[Dict]:
        """
        자막 데이터를 타임라인 형식으로 변환

        Args:
            transcript_data: 자막 데이터 리스트

        Returns:
            타임라인 형식의 데이터
            [{"time": "00:00", "text": "...", "start": 0.0}, ...]
        """
        timeline = []
        for item in transcript_data:
            timeline.append({
                "time": format_timestamp(item["start"]),
                "text": item["text"].strip(),
                "start": item["start"],
                "duration": item.get("duration", 0)
            })
        return timeline

    def cleanup_audio_file(self, audio_path: str):
        """
        임시 오디오 파일 삭제

        Args:
            audio_path: 오디오 파일 경로
        """
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"임시 파일 삭제: {audio_path}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {e}")

    def get_related_videos(self, url: str, max_results: int = 3) -> List[Dict]:
        """
        관련 동영상 가져오기 (YouTube Data API 기반)

        1순위: YouTube Data API v3 (배포 환경에서 안정적)
        2순위: yt-dlp (fallback)

        Args:
            url: YouTube URL
            max_results: 최대 결과 개수 (기본값: 3)

        Returns:
            관련 동영상 리스트
            [{"video_id": "...", "title": "...", "author": "...", "thumbnail_url": "...", "url": "..."}, ...]
        """
        try:
            video_id = extract_video_id(url)
            if not video_id:
                logger.warning("유효하지 않은 URL로 관련 동영상 검색 시도")
                return []

            logger.info(f"관련 동영상 검색 시작: {video_id}")

            # 1순위: YouTube Data API v3 사용
            if settings.YOUTUBE_API_KEY:
                try:
                    return self._get_related_videos_api(video_id, max_results)
                except Exception as api_error:
                    logger.warning(f"YouTube Data API 관련 동영상 검색 실패: {api_error}, yt-dlp로 재시도")

            # 2순위: yt-dlp 사용 (fallback)
            return self._get_related_videos_ytdlp(url, video_id, max_results)

        except Exception as e:
            logger.error(f"관련 동영상 검색 실패: {e}")
            return []

    def _get_related_videos_api(self, video_id: str, max_results: int) -> List[Dict]:
        """YouTube Data API v3를 사용하여 관련 동영상 검색"""
        # 먼저 현재 영상 정보 가져오기
        api_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "id": video_id,
            "key": settings.YOUTUBE_API_KEY
        }
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("items"):
            return []

        video_info = data["items"][0]["snippet"]
        video_title = video_info.get("title", "")
        channel_title = video_info.get("channelTitle", "")

        # 검색어 생성
        title_words = video_title.split()[:4]
        search_query = ' '.join(title_words)
        if channel_title:
            search_query = f"{search_query} {channel_title}"

        logger.info(f"YouTube API 검색 쿼리: {search_query}")

        # YouTube 검색 API 호출
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet",
            "q": search_query,
            "type": "video",
            "maxResults": max_results + 5,  # 현재 영상 제외를 위해 여유롭게
            "key": settings.YOUTUBE_API_KEY
        }
        search_response = requests.get(search_url, params=search_params, timeout=10)
        search_response.raise_for_status()
        search_data = search_response.json()

        related_videos = []
        for item in search_data.get("items", []):
            item_video_id = item.get("id", {}).get("videoId", "")

            # 현재 비디오 제외
            if item_video_id == video_id:
                continue

            # 중복 방지
            if any(v['video_id'] == item_video_id for v in related_videos):
                continue

            snippet = item.get("snippet", {})
            related_videos.append({
                'video_id': item_video_id,
                'title': snippet.get('title', 'Unknown'),
                'author': snippet.get('channelTitle', 'Unknown'),
                'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url',
                    f"https://img.youtube.com/vi/{item_video_id}/hqdefault.jpg"),
                'url': f"https://www.youtube.com/watch?v={item_video_id}"
            })

            if len(related_videos) >= max_results:
                break

        logger.info(f"YouTube API로 관련 동영상 {len(related_videos)}개 찾음")
        return related_videos

    def _get_related_videos_ytdlp(self, url: str, video_id: str, max_results: int) -> List[Dict]:
        """yt-dlp를 사용하여 관련 동영상 검색 (fallback)"""
        # 먼저 현재 영상 정보 가져오기
        ydl_opts_info = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)

        video_title = info.get('title', '')
        channel_name = info.get('uploader', info.get('channel', ''))

        if not video_title:
            logger.warning("영상 제목을 가져올 수 없음")
            return []

        # 검색어 생성
        title_words = video_title.split()[:4]
        search_query = ' '.join(title_words)
        if channel_name:
            search_query = f"{search_query} {channel_name}"

        logger.info(f"yt-dlp 검색 쿼리: {search_query}")

        # YouTube 검색 수행
        search_url = f"ytsearch{max_results + 5}:{search_query}"

        ydl_opts_search = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
            'extract_flat': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            search_results = ydl.extract_info(search_url, download=False)

        related_videos = []

        if search_results and 'entries' in search_results:
            for entry in search_results['entries']:
                if not entry:
                    continue

                entry_id = entry.get('id', '')

                if entry_id == video_id:
                    continue

                if any(v['video_id'] == entry_id for v in related_videos):
                    continue

                related_videos.append({
                    'video_id': entry_id,
                    'title': entry.get('title', 'Unknown'),
                    'author': entry.get('uploader', entry.get('channel', 'Unknown')),
                    'thumbnail_url': entry.get('thumbnail', f"https://img.youtube.com/vi/{entry_id}/hqdefault.jpg"),
                    'url': f"https://www.youtube.com/watch?v={entry_id}"
                })

                if len(related_videos) >= max_results:
                    break

        logger.info(f"yt-dlp로 관련 동영상 {len(related_videos)}개 찾음")
        return related_videos[:max_results]
