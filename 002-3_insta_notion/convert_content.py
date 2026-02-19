import base64
import logging
import os
import subprocess

logger = logging.getLogger("processor")


def _is_image(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")


def _is_video(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return ext in (".mp4", ".mov", ".avi", ".mkv", ".webm")


def _get_media_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    type_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return type_map.get(ext, "image/jpeg")


def extract_text_from_image(image_path, config):
    """Claude Vision API로 이미지에서 텍스트 추출"""
    import anthropic

    try:
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        client = anthropic.Anthropic()
        message = client.messages.create(
            model=config.get("vision", {}).get("model", "claude-sonnet-4-5-20250929"),
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _get_media_type(image_path),
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "이 인스타그램 이미지를 분석해줘.\n"
                            "1. 이미지에 포함된 모든 텍스트를 그대로 추출\n"
                            "2. 이미지의 시각적 내용 설명\n"
                            "3. 핵심 내용 요약 (2-3줄)\n\n"
                            "한국어로 답변해줘. 텍스트가 없으면 시각적 설명과 요약만 제공해줘."
                        ),
                    },
                ],
            }],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Vision API error for {image_path}: {e}")
        return f"[이미지 텍스트 추출 실패: {e}]"


def extract_text_from_video(video_path, config):
    """ffmpeg로 오디오 추출 → Whisper로 음성 변환"""
    audio_path = video_path.rsplit(".", 1)[0] + ".mp3"

    try:
        # 오디오 추출
        proc = subprocess.run(
            ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", "-y", audio_path],
            capture_output=True,
            timeout=120,
        )
        if proc.returncode != 0:
            logger.warning(f"ffmpeg failed: {proc.stderr[:200]}")
            return "[오디오 추출 실패]"

        # 오디오 파일 크기 확인 (빈 오디오 처리)
        if os.path.getsize(audio_path) < 1000:
            return "[음성 없는 영상]"

        # Whisper 변환
        import whisper
        whisper_model = config.get("whisper", {}).get("model", "small")
        whisper_lang = config.get("whisper", {}).get("language", "ko")

        model = whisper.load_model(whisper_model)
        result = model.transcribe(audio_path, language=whisper_lang)

        return result["text"]

    except Exception as e:
        logger.error(f"Whisper error for {video_path}: {e}")
        return f"[음성 변환 실패: {e}]"
    finally:
        # 임시 오디오 파일 삭제
        if os.path.exists(audio_path):
            os.remove(audio_path)


def convert(extract_result, config):
    """
    추출된 미디어를 텍스트로 변환

    Returns:
        {
            "success": bool,
            "extracted_texts": [str],    # 각 미디어에서 추출한 텍스트
            "caption": str,
            "hashtags": [str],
            "post_type": str,
            "username": str,
            "posted_at": str,
            "media_count": int,
            "location": str | None,
        }
    """
    media_files = extract_result.get("media_files", [])
    extracted_texts = []

    for i, file_path in enumerate(media_files):
        if not os.path.exists(file_path):
            continue

        if _is_image(file_path):
            label = f"[슬라이드 {i+1}]" if len(media_files) > 1 else "[이미지]"
            text = extract_text_from_image(file_path, config)
            extracted_texts.append(f"{label}\n{text}")

        elif _is_video(file_path):
            text = extract_text_from_video(file_path, config)
            extracted_texts.append(f"[영상 음성]\n{text}")

    return {
        "success": True,
        "extracted_texts": extracted_texts,
        "caption": extract_result.get("caption", ""),
        "hashtags": extract_result.get("hashtags", []),
        "post_type": extract_result.get("post_type", "unknown"),
        "username": extract_result.get("username", ""),
        "posted_at": extract_result.get("posted_at", ""),
        "media_count": extract_result.get("media_count", 0),
        "location": extract_result.get("location"),
    }
