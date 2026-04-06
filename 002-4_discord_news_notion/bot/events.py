"""
Discord 이벤트 핸들러 - 핵심 트리거 모듈

[동작 흐름]
유저가 디스코드 채널에 URL 붙여넣기
    → on_message 이벤트 발생
    → URL 감지 (YouTube/Instagram 제외)
    → 뉴스 vs 일반 URL 분류
    → Claude CLI가 URL 직접 읽기 + 분석 + Notion 저장 (MCP + WebFetch)
    → 완료 메시지 회신
"""
import asyncio
import time

import discord
from loguru import logger

import config
from services.analyzer import NewsAnalyzer
from utils.url_detector import extract_urls, filter_valid_urls, is_reddit_url

# 서비스 인스턴스 (모듈 로딩 시 1회만 생성)
analyzer = NewsAnalyzer()


def register_events(client: discord.Client):
    """Discord 클라이언트에 이벤트 핸들러 등록"""

    _scan_lock = asyncio.Lock()

    async def scan_missed_messages():
        """재연결 시 놓친 메시지 스캔 (슬립 복구 대응)"""
        async with _scan_lock:
            await client.wait_until_ready()

            channel_ids = config.DISCORD_CHANNEL_IDS
            if not channel_ids:
                return

            for channel_id in channel_ids:
                channel = client.get_channel(channel_id)
                if not channel:
                    continue

                enqueued = 0
                try:
                    async for message in channel.history(limit=50):
                        if message.author.bot:
                            continue
                        # 봇이 이미 리액션한 메시지는 스킵 (✅, ❌, ⏳)
                        already_processed = False
                        for reaction in message.reactions:
                            if reaction.me:
                                already_processed = True
                                break
                        if already_processed:
                            continue

                        # 일반 + Forward 메시지 모두에서 URL 추출
                        scan_sources = [message.content or ""]
                        if hasattr(message, "message_snapshots") and message.message_snapshots:
                            for snapshot in message.message_snapshots:
                                if hasattr(snapshot, "content") and snapshot.content:
                                    scan_sources.append(snapshot.content)
                        for embed in message.embeds:
                            if embed.url:
                                scan_sources.append(embed.url)
                            if embed.description:
                                scan_sources.append(embed.description)

                        all_urls = extract_urls(" ".join(scan_sources))
                        if not all_urls:
                            continue
                        valid_urls = filter_valid_urls(all_urls)
                        if not valid_urls:
                            continue

                        logger.info(f"[Scan] 놓친 URL 발견: {valid_urls} from {message.author}")

                        # on_message 로직 재사용: 이벤트를 다시 디스패치
                        await client.on_message(message)
                        enqueued += 1

                    if enqueued > 0:
                        logger.info(f"[Scan] 놓친 메시지 {enqueued}건 처리 시작")
                    else:
                        logger.info("[Scan] 놓친 URL 없음")
                except Exception as e:
                    logger.error(f"[Scan] History scan error: {e}")

    @client.event
    async def on_ready():
        logger.info(f"봇 로그인 성공: {client.user} (ID: {client.user.id})")
        if config.DISCORD_CHANNEL_IDS:
            logger.info(f"감지 채널: {config.DISCORD_CHANNEL_IDS}")
        else:
            logger.info("감지 채널: 서버 전체")
        # 재연결 시에도 놓친 메시지 스캔 (슬립 복구 대응)
        client.loop.create_task(scan_missed_messages())

    @client.event
    async def on_message(message: discord.Message):
        # ── 기본 필터 ──────────────────────────────────────
        if message.author.bot:
            return

        if config.DISCORD_CHANNEL_IDS and message.channel.id not in config.DISCORD_CHANNEL_IDS:
            return

        # ── URL 감지 (YouTube/Instagram 제외) ──────────────
        # 일반 메시지 + Forward(전달) 메시지 모두에서 URL 추출
        text_sources = [message.content]
        # Forward된 메시지: message_snapshots에 원본 content가 들어있음
        if hasattr(message, "message_snapshots") and message.message_snapshots:
            for snapshot in message.message_snapshots:
                if hasattr(snapshot, "content") and snapshot.content:
                    text_sources.append(snapshot.content)
        # embeds에 URL이 포함된 경우도 처리
        for embed in message.embeds:
            if embed.url:
                text_sources.append(embed.url)
            if embed.description:
                text_sources.append(embed.description)

        combined_text = " ".join(text_sources)
        all_urls = extract_urls(combined_text)
        if not all_urls:
            return

        valid_urls = filter_valid_urls(all_urls)
        if not valid_urls:
            return

        logger.info(
            f"{'='*50}\n"
            f"🔗 URL 감지 | "
            f"채널: #{message.channel.name} | "
            f"유저: {message.author.name} | "
            f"URL 수: {len(valid_urls)} | "
            f"URL: {valid_urls}"
        )

        # ── 처리 시작: 상태 메시지 전송 ──────────────────────
        await message.add_reaction("⏳")
        total_urls = len(valid_urls)
        status_msg = await message.reply(
            f"**처리 시작** — {total_urls}건의 URL을 분석합니다...",
            mention_author=False,
        )

        # ── URL별 파이프라인 실행 ──────────────────────────
        success_count = 0
        for idx, url in enumerate(valid_urls, 1):
            pipeline_start = time.time()
            short_url = url[:60] + ("..." if len(url) > 60 else "")
            try:
                logger.info(f"[{idx}/{total_urls}] 📌 파이프라인 시작: {url}")

                # ── Step 1: Claude CLI로 URL 읽기 + 분석 + Notion 저장
                url_emoji = "🔴" if is_reddit_url(url) else "📰"
                await status_msg.edit(
                    content=f"**[{idx}/{total_urls}]** {url_emoji} `{short_url}`\n"
                    f"▸ Claude CLI 분석 + Notion 저장 중... (1~3분 소요)"
                )
                logger.info(f"[{idx}] Claude CLI 분석 + Notion 저장 중...")
                result = await asyncio.to_thread(
                    analyzer.analyze_and_save, url, str(message.author)
                )
                elapsed = time.time() - pipeline_start
                logger.info(f"[{idx}] 분석 완료 ({elapsed:.1f}초)")

                # ── Step 2: 완료 회신 ─────────────────────
                logger.info(f"[{idx}] 디스코드 회신 중...")
                reply_text = _build_reply(result, elapsed)
                await status_msg.edit(content=reply_text)
                success_count += 1

                logger.info(
                    f"[{idx}] ✅ 파이프라인 완료 | "
                    f"총 {elapsed:.1f}초 | "
                    f"Notion: {result.notion_url or 'URL 없음'}"
                )

                # 다음 URL이 있으면 새 상태 메시지 생성
                if idx < total_urls:
                    status_msg = await message.reply(
                        f"**다음 URL 처리 중** ({idx + 1}/{total_urls})...",
                        mention_author=False,
                    )

            except Exception as e:
                elapsed = time.time() - pipeline_start
                logger.error(
                    f"[{idx}] ❌ 파이프라인 실패 ({elapsed:.1f}초) | "
                    f"URL: {url} | 에러: {e}",
                    exc_info=True,
                )
                user_msg = _friendly_error(e)
                await status_msg.edit(
                    content=f"❌ **분석 실패** — `{short_url}`\n{user_msg}\n"
                    f"⏱ {elapsed:.0f}초 소요"
                )

                # 다음 URL이 있으면 새 상태 메시지 생성
                if idx < total_urls:
                    status_msg = await message.reply(
                        f"**다음 URL 처리 중** ({idx + 1}/{total_urls})...",
                        mention_author=False,
                    )

        # ── 처리 완료 표시 ─────────────────────────────────
        await message.remove_reaction("⏳", client.user)
        if success_count > 0:
            await message.add_reaction("✅")
        else:
            await message.add_reaction("❌")
        logger.info(f"{'='*50}")


def _friendly_error(e: Exception) -> str:
    """내부 에러를 사용자 친화적 메시지로 변환"""
    msg = str(e).lower()
    if "timeout" in msg or "타임아웃" in msg:
        return "AI 분석 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
    if "json" in msg or "파싱" in msg:
        return "AI 응답을 처리하는 데 실패했습니다. 다시 시도해주세요."
    if "notion" in msg or "api" in msg:
        return "Notion 저장 중 오류가 발생했습니다. 관리자에게 문의해주세요."
    if "connection" in msg or "connect" in msg:
        return "네트워크 연결에 실패했습니다. 잠시 후 다시 시도해주세요."
    if "credit" in msg or "balance" in msg:
        return "AI 서비스 크레딧이 부족합니다. 관리자에게 문의해주세요."
    return "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


def _build_reply(result, elapsed: float = 0) -> str:
    """디스코드 회신 메시지 포맷팅"""
    emoji = "🔴" if is_reddit_url(result.url) else "📰"
    lines = [
        f"## {emoji} 분석 완료",
        f"> ⏱ {elapsed:.0f}초 소요",
    ]

    if result.notion_url:
        lines.append(f"📓 [**Notion에서 보기**]({result.notion_url})")
    else:
        lines.append("📓 Notion 저장 완료 (URL을 가져오지 못했습니다)")

    return "\n".join(lines)
