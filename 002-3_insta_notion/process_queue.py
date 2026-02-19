import logging
import logging.handlers
import os
import re
import subprocess

import requests
import yaml

import convert_content
import db_helper
import extract_instagram

# 설정 로드
CONFIG_PATH = os.path.expanduser("~/.insta-notion-pipeline/config.yaml")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# 로깅 설정
log_dir = os.path.expanduser(config["logging"]["log_dir"])
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("processor")
logger.setLevel(getattr(logging, config["logging"]["log_level"]))
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(log_dir, "processor.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())

# DB 초기화
db_helper.init_db()

TEMP_DIR = os.path.expanduser("~/.insta-notion-pipeline/temp")
MAX_BATCH = config["queue"]["max_batch_size"]
MAX_RETRIES = config["queue"]["max_retries"]
PIPELINE_DIR = os.path.expanduser("~/.insta-notion-pipeline")

# Discord 알림 설정
BOT_TOKEN = config["discord"]["bot_token"]
CHANNEL_ID = config["discord"]["notification_channel_id"]
DISCORD_API = "https://discord.com/api/v10"


def discord_msg(content):
    """디스코드 채널에 메시지 전송"""
    try:
        requests.post(
            f"{DISCORD_API}/channels/{CHANNEL_ID}/messages",
            headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"},
            json={"content": content},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Discord message failed: {e}")


def build_prompt(convert_result, url):
    """Claude CLI에 전달할 프롬프트 생성"""
    post_type = convert_result["post_type"]
    username = convert_result["username"]
    posted_at = convert_result["posted_at"]
    caption = convert_result["caption"]
    hashtags = convert_result["hashtags"]
    extracted_texts = convert_result["extracted_texts"]
    location = convert_result.get("location", "")
    media_count = convert_result.get("media_count", 0)

    parts = [
        f"다음 인스타그램 포스트를 정리해서 노션에 저장해줘.\n",
        f"포스트 유형: {post_type}",
        f"작성자: @{username}",
        f"게시일: {posted_at}",
        f"원본 URL: {url}",
        f"미디어 수: {media_count}장",
    ]

    if location:
        parts.append(f"위치: {location}")

    if caption:
        parts.append(f"\n[캡션]\n{caption}")

    if hashtags:
        parts.append(f"\n[해시태그]\n{' '.join('#' + tag for tag in hashtags)}")

    if extracted_texts:
        parts.append(f"\n[이미지/영상에서 추출한 텍스트]")
        for text in extracted_texts:
            parts.append(text)

    return "\n".join(parts)


def cleanup_media(media_files):
    """임시 미디어 파일 삭제"""
    for f in media_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception as e:
            logger.warning(f"Failed to remove {f}: {e}")


def process_item(item):
    """단일 큐 항목 처리: Instagram 추출 → 텍스트 변환 → Claude CLI → 노션 저장"""
    item_id = item["id"]
    shortcode = item["shortcode"]
    url = item["instagram_url"]

    logger.info(f"Processing: {shortcode} ({url})")
    discord_msg(f"**[1/3] Instagram 콘텐츠 추출 중...** `{shortcode}`\n{url}")

    # Step 1: Instagram 콘텐츠 추출
    extract_result = extract_instagram.extract(
        shortcode=shortcode,
        config=config,
        temp_dir=TEMP_DIR,
    )

    if not extract_result["success"]:
        logger.error(f"Instagram extraction failed for {shortcode}: {extract_result['error']}")
        db_helper.set_failed(item_id, extract_result["error"], max_retries=MAX_RETRIES)
        discord_msg(f"**[실패] 추출 실패** `{shortcode}`\n`{extract_result['error'][:200]}`")
        return False

    post_type = extract_result["post_type"]
    media_files = extract_result.get("media_files", [])
    discord_msg(f"**[2/3] 추출 완료** ({post_type}, 미디어 {len(media_files)}개) → 텍스트 변환 중...")

    # Step 2: 미디어 → 텍스트 변환
    convert_result = convert_content.convert(extract_result, config)

    # Step 3: Claude CLI 호출
    prompt = build_prompt(convert_result, url)

    try:
        proc = subprocess.run(
            ["claude", "-p", "--dangerously-skip-permissions", prompt],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=PIPELINE_DIR,
        )

        if proc.returncode != 0:
            error_msg = proc.stderr or f"Claude CLI exit code: {proc.returncode}"
            logger.error(f"Claude CLI failed for {shortcode}: {error_msg}")
            db_helper.set_failed(item_id, error_msg, max_retries=MAX_RETRIES)
            return False

        logger.info(f"Claude CLI success for {shortcode}")
        logger.info(f"Claude CLI stdout (first 500 chars): {proc.stdout[:500]}")

    except subprocess.TimeoutExpired:
        logger.error(f"Claude CLI timeout for {shortcode}")
        db_helper.set_failed(item_id, "Claude CLI timeout (600s)", max_retries=MAX_RETRIES)
        return False
    except Exception as e:
        logger.error(f"Claude CLI error for {shortcode}: {e}")
        db_helper.set_failed(item_id, str(e), max_retries=MAX_RETRIES)
        return False

    # Step 4: 완료 처리
    db_helper.set_completed(item_id)

    # 노션 URL 추출
    notion_url = ""
    if proc.stdout:
        match = re.search(r'https://www\.notion\.so/[^\s\)]+', proc.stdout)
        if match:
            notion_url = match.group(0)

    if notion_url:
        discord_msg(f"**[3/3] 완료!** `{shortcode}`\n{notion_url}")
    else:
        discord_msg(f"**[3/3] 완료!** `{shortcode}` → 노션에 저장됨")

    # 임시 미디어 파일 삭제
    cleanup_media(media_files)

    logger.info(f"Completed: {shortcode}")
    return True


def main():
    pending = db_helper.get_pending(limit=MAX_BATCH)

    if not pending:
        logger.info("No pending items. Exiting.")
        return

    logger.info(f"Processing {len(pending)} items")

    completed = 0
    failed = 0

    for item in pending:
        db_helper.set_processing(item["id"])
        if process_item(item):
            completed += 1
        else:
            failed += 1

    logger.info(f"Done. Completed: {completed}, Failed: {failed}")


if __name__ == "__main__":
    main()
