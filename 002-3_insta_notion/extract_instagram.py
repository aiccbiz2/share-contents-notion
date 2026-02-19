import json
import logging
import os

from instagrapi import Client

logger = logging.getLogger("processor")


def _get_client(config):
    """instagrapi Client 생성 (세션 재사용)"""
    cl = Client()
    session_path = os.path.expanduser(config["instagram"]["session_path"])

    if os.path.exists(session_path):
        cl.load_settings(session_path)
        cl.login(config["instagram"]["username"], config["instagram"]["password"])
    else:
        cl.login(config["instagram"]["username"], config["instagram"]["password"])
        cl.dump_settings(session_path)

    return cl


def extract(shortcode, config, temp_dir=None):
    """
    Instagram 포스트에서 메타데이터 + 미디어 다운로드

    Returns:
        {
            "success": bool,
            "post_type": "image" | "carousel" | "reel" | "video",
            "caption": str,
            "hashtags": [str],
            "username": str,
            "posted_at": str,
            "media_files": [str],
            "media_count": int,
            "location": str | None,
            "error": str | None,
        }
    """
    if temp_dir is None:
        temp_dir = os.path.expanduser("~/.insta-notion-pipeline/temp")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        cl = _get_client(config)
        media_pk = cl.media_pk_from_code(shortcode)
        media = cl.media_info(media_pk)
    except Exception as e:
        return {"success": False, "error": f"Instagram API error: {e}"}

    # 포스트 유형 판별
    # media_type: 1=Photo, 2=Video, 8=Album
    media_type = media.media_type
    if media_type == 1:
        post_type = "image"
    elif media_type == 2:
        post_type = "reel" if media.product_type == "clips" else "video"
    elif media_type == 8:
        post_type = "carousel"
    else:
        post_type = "unknown"

    # 캡션 + 해시태그
    caption = media.caption_text or ""
    hashtags = [tag.strip("#") for tag in caption.split() if tag.startswith("#")]

    # 미디어 다운로드
    media_files = []
    try:
        if media_type == 1:
            # 단일 이미지
            path = cl.photo_download(media_pk, folder=temp_dir)
            media_files.append(str(path))

        elif media_type == 2:
            # 영상 (릴스 포함)
            path = cl.video_download(media_pk, folder=temp_dir)
            media_files.append(str(path))

        elif media_type == 8:
            # 캐러셀 (앨범)
            paths = cl.album_download(media_pk, folder=temp_dir)
            media_files.extend([str(p) for p in paths])

    except Exception as e:
        logger.warning(f"Media download failed for {shortcode}: {e}")
        # 미디어 다운로드 실패해도 캡션은 추출 가능하므로 계속 진행

    # 위치 정보
    location = None
    if media.location:
        location = media.location.name

    return {
        "success": True,
        "post_type": post_type,
        "caption": caption,
        "hashtags": hashtags,
        "username": media.user.username,
        "posted_at": media.taken_at.isoformat() if media.taken_at else "",
        "media_files": media_files,
        "media_count": len(media_files),
        "location": location,
        "error": None,
    }
