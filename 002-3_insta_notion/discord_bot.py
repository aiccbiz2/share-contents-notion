import asyncio
import glob
import json
import logging
import logging.handlers
import os
import re
import sys

import discord
import yaml

import db_helper

# 설정 로드
CONFIG_PATH = os.path.expanduser("~/.insta-notion-pipeline/config.yaml")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# 로깅 설정
log_dir = os.path.expanduser(config["logging"]["log_dir"])
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("discord_bot")
logger.setLevel(getattr(logging, config["logging"]["log_level"]))
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(log_dir, "discord_bot.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())

# Instagram URL 정규식
INSTAGRAM_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?'
    r'(?:instagram\.com|instagr\.am)'
    r'/(?:p|reel|reels|tv|stories/[^/]+)'
    r'/([A-Za-z0-9_-]+)'
)

CHANNEL_IDS = [int(cid) for cid in config["discord"]["channel_ids"]]
NOTIFICATION_CHANNEL_ID = int(config["discord"].get("notification_channel_id", 0))
TEMP_DIR = os.path.expanduser("~/.insta-notion-pipeline/temp")

# DB 초기화
db_helper.init_db()

# Discord Client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
_notification_task_started = False


def extract_shortcodes(text):
    """텍스트에서 Instagram shortcode들을 추출"""
    matches = INSTAGRAM_PATTERN.findall(text)
    return [m for m in matches if m]


def reconstruct_url(shortcode):
    return f"https://www.instagram.com/p/{shortcode}/"


async def scan_missed_messages():
    """봇이 오프라인이었던 동안 놓친 메시지를 스캔하여 큐에 추가"""
    await client.wait_until_ready()

    for channel_id in CHANNEL_IDS:
        channel = client.get_channel(channel_id)
        if not channel:
            continue

        enqueued = 0
        try:
            async for message in channel.history(limit=200):
                if message.author == client.user:
                    continue
                if not message.content:
                    continue

                shortcodes = extract_shortcodes(message.content)
                for sc in shortcodes:
                    if db_helper.is_duplicate(sc):
                        continue
                    url = reconstruct_url(sc)
                    if db_helper.enqueue(url=url, shortcode=sc, message_id=str(message.id), user=str(message.author)):
                        enqueued += 1
                        logger.info(f"[Scan] Enqueued missed: {sc} from {message.author}")

            if enqueued > 0:
                await channel.send(f"**오프라인 동안 놓친 URL {enqueued}건을 큐에 추가했습니다.**")
                logger.info(f"[Scan] Total enqueued from history: {enqueued}")
            else:
                logger.info("[Scan] No missed URLs found")
        except Exception as e:
            logger.error(f"[Scan] History scan error: {e}")


@client.event
async def on_ready():
    global _notification_task_started
    logger.info(f"Bot logged in as {client.user}")
    if not _notification_task_started:
        _notification_task_started = True
        client.loop.create_task(check_notifications())
        client.loop.create_task(scan_missed_messages())


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id not in CHANNEL_IDS:
        return

    logger.info(f"Message from {message.author} in #{message.channel.name}: {message.content[:100]!r}")

    if not message.content:
        logger.warning("Empty message content")
        return

    shortcodes = extract_shortcodes(message.content)
    if not shortcodes:
        logger.info("No Instagram URLs found in message")
        return

    enqueued = 0
    skipped = 0

    for sc in shortcodes:
        if db_helper.is_duplicate(sc):
            skipped += 1
            continue

        url = reconstruct_url(sc)
        success = db_helper.enqueue(
            url=url,
            shortcode=sc,
            message_id=str(message.id),
            user=str(message.author),
        )
        if success:
            enqueued += 1
            logger.info(f"Enqueued: {sc} from {message.author}")
        else:
            skipped += 1

    try:
        if enqueued > 0:
            await message.add_reaction("\u2705")
            await message.channel.send(
                f"**큐에 추가됨** ({enqueued}건) - 다음 처리 주기에 자동 실행됩니다."
            )
        elif skipped > 0:
            await message.add_reaction("\u23ed\ufe0f")
            await message.channel.send(f"이미 처리된 포스트입니다. ({skipped}건 스킵)")
    except Exception as e:
        logger.error(f"Failed to send status: {e}")


async def check_notifications():
    """60초마다 완료 알림 파일 확인 → 디스코드 알림 전송"""
    await client.wait_until_ready()

    if not NOTIFICATION_CHANNEL_ID:
        return

    while not client.is_closed():
        try:
            channel = client.get_channel(NOTIFICATION_CHANNEL_ID)
            if not channel:
                logger.warning(f"Notification channel {NOTIFICATION_CHANNEL_ID} not found, retrying later")
                await asyncio.sleep(60)
                continue

            pattern = os.path.join(TEMP_DIR, "notify_*.json")
            for filepath in glob.glob(pattern):
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    status = data.get("status", "unknown")
                    title = data.get("title", "Unknown")
                    url = data.get("url", "")

                    if status == "completed":
                        msg = f"\u2705 **처리 완료:** [{title}]({url})\n노션에 저장되었습니다."
                    else:
                        msg = f"\u274c **처리 실패:** [{title}]({url})"

                    await channel.send(msg)
                    os.remove(filepath)
                    logger.info(f"Notification sent for {data.get('shortcode')}")
                except discord.Forbidden:
                    logger.error(f"No permission to send to channel {NOTIFICATION_CHANNEL_ID}")
                    os.remove(filepath)
                except Exception as e:
                    logger.error(f"Notification error for {filepath}: {e}")
        except Exception as e:
            logger.error(f"Notification loop error: {e}")

        await asyncio.sleep(60)


if __name__ == "__main__":
    token = config["discord"]["bot_token"]
    if token == "YOUR_BOT_TOKEN":
        print("ERROR: config.yaml에서 bot_token을 설정하세요.")
        sys.exit(1)
    client.run(token)
