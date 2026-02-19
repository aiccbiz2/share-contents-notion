import json
import logging
import logging.handlers
import os
import subprocess
import sys

import requests
import yaml

import db_helper
import extract_transcript

# 설정 로드
CONFIG_PATH = os.path.expanduser("~/.agent-ref-pipeline/config.yaml")

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

TEMP_DIR = os.path.expanduser("~/.agent-ref-pipeline/temp")
MAX_BATCH = config["queue"]["max_batch_size"]
MAX_RETRIES = config["queue"]["max_retries"]
LANGUAGES = config["transcript"]["languages"]
PIPELINE_DIR = os.path.expanduser("~/.agent-ref-pipeline")

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


def process_item(item):
    """단일 큐 항목 처리: 자막 추출 → Claude CLI → 결과 저장"""
    item_id = item["id"]
    video_id = item["video_id"]
    url = item["youtube_url"]

    logger.info(f"Processing: {video_id} ({url})")
    discord_msg(f"**[1/3] 자막 추출 중...** `{video_id}`\n{url}")

    # Step 1: 자막 추출
    result = extract_transcript.extract(
        video_id=video_id,
        languages=LANGUAGES,
        temp_dir=TEMP_DIR,
    )

    if not result["success"]:
        logger.error(f"Transcript extraction failed for {video_id}: {result['error']}")
        db_helper.set_failed(item_id, result["error"], max_retries=MAX_RETRIES)
        discord_msg(f"**[실패] 자막 추출 실패** `{video_id}`\n`{result['error'][:200]}`")
        return False

    transcript_text = result["text"]
    file_path = result["file_path"]
    discord_msg(f"**[2/3] 자막 추출 완료** ({len(transcript_text):,}자) → 노션 저장 중...")

    # Step 2: Claude CLI 호출
    prompt = (
        f"다음 YouTube 영상 자막을 정리해서 노션에 저장해줘.\n"
        f"영상 제목: {video_id}\n"
        f"영상 URL: {url}\n\n"
        f"[자막 텍스트]\n{transcript_text}"
    )

    try:
        proc = subprocess.run(
            ["claude", "-p", "--dangerously-skip-permissions", prompt],
            capture_output=True,
            text=True,
            timeout=600,  # 10분 타임아웃
            cwd=PIPELINE_DIR,
        )

        if proc.returncode != 0:
            error_msg = proc.stderr or f"Claude CLI exit code: {proc.returncode}"
            logger.error(f"Claude CLI failed for {video_id}: {error_msg}")
            db_helper.set_failed(item_id, error_msg, max_retries=MAX_RETRIES)
            return False

        logger.info(f"Claude CLI success for {video_id}")
        logger.info(f"Claude CLI stdout (first 500 chars): {proc.stdout[:500]}")
        if proc.stderr:
            logger.warning(f"Claude CLI stderr: {proc.stderr[:300]}")

    except subprocess.TimeoutExpired:
        logger.error(f"Claude CLI timeout for {video_id}")
        db_helper.set_failed(item_id, "Claude CLI timeout (300s)", max_retries=MAX_RETRIES)
        return False
    except Exception as e:
        logger.error(f"Claude CLI error for {video_id}: {e}")
        db_helper.set_failed(item_id, str(e), max_retries=MAX_RETRIES)
        return False

    # Step 3: 완료 처리
    db_helper.set_completed(item_id)

    # Claude CLI 출력에서 노션 URL 추출
    notion_url = ""
    if proc.stdout:
        import re
        match = re.search(r'https://www\.notion\.so/[^\s\)]+', proc.stdout)
        if match:
            notion_url = match.group(0)

    # 완료 알림
    if notion_url:
        discord_msg(f"**[3/3] 완료!** `{video_id}`\n{notion_url}")
    else:
        discord_msg(f"**[3/3] 완료!** `{video_id}` → 노션에 저장됨")

    # temp 자막 파일 삭제
    if os.path.exists(file_path):
        os.remove(file_path)

    logger.info(f"Completed: {video_id}")
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
