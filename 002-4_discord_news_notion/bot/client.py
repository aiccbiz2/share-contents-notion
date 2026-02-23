"""
Discord 봇 클라이언트 설정 모듈
"""
import discord
from loguru import logger


def create_client() -> discord.Client:
    """Discord 클라이언트 생성 (필요한 Intents 설정)"""
    intents = discord.Intents.default()
    intents.message_content = True   # URL 텍스트 읽기 필수
    intents.messages = True

    client = discord.Client(intents=intents)
    logger.info("Discord 클라이언트 생성 완료")
    return client
