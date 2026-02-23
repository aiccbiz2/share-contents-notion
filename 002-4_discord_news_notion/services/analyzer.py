"""
Claude CLI 기반 분석 + Notion 저장 모듈 (MCP 방식)
- Claude CLI가 WebFetch로 URL을 직접 읽고 분석
- --output-format stream-json으로 중간 과정 실시간 로그
"""
import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from loguru import logger

import config

# MCP 설정 파일 경로 (프로젝트 루트의 mcp_config.json)
MCP_CONFIG_PATH = str(Path(__file__).parent.parent / "mcp_config.json")
from prompts.news_analysis import build_news_prompt


@dataclass
class AnalysisResult:
    url: str
    notion_url: str


class NewsAnalyzer:
    """Claude CLI로 URL 읽기 + 분석 + Notion 저장을 수행하는 분석기"""

    def analyze_and_save(
        self,
        url: str,
        shared_by: str = "",
    ) -> AnalysisResult:
        """
        URL을 Claude CLI에 전달하여 직접 읽고 분석 후 Notion에 저장.
        모든 URL에 뉴스 3관점 분석 적용. 최대 3회 재시도.
        """
        source = self._extract_source(url)

        prompt = build_news_prompt(
            url=url,
            source=source,
            database_id=config.NOTION_DATABASE_ID,
            shared_by=shared_by,
        )

        logger.info(
            f"🤖 Claude CLI 분석 준비 | "
            f"URL: {url} | "
            f"프롬프트: {len(prompt)}자"
        )

        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                logger.info(
                    f"🚀 Claude CLI 실행 (시도 {attempt}/3) | "
                    f"타임아웃: {config.CLAUDE_TIMEOUT}초"
                )
                start_time = time.time()

                # Claude CLI가 구독 모드로 동작하도록 불필요한 환경변수 제거
                env = {
                    k: v for k, v in os.environ.items()
                    if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")
                }

                proc = subprocess.Popen(
                    [
                        config.CLAUDE_CLI_PATH,
                        "-p", prompt,
                        "--allowedTools", "mcp__notion__*,WebFetch",
                        "--mcp-config", MCP_CONFIG_PATH,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                )

                # 타임아웃 타이머
                timed_out = False
                def _kill():
                    nonlocal timed_out
                    timed_out = True
                    proc.kill()
                timer = threading.Timer(config.CLAUDE_TIMEOUT, _kill)
                timer.start()

                try:
                    result_text, stderr_output = proc.communicate()
                except:
                    proc.kill()
                    result_text, stderr_output = proc.communicate()
                finally:
                    timer.cancel()

                if timed_out:
                    raise subprocess.TimeoutExpired(
                        config.CLAUDE_CLI_PATH, config.CLAUDE_TIMEOUT
                    )

                elapsed = time.time() - start_time

                if proc.returncode != 0:
                    error_msg = stderr_output.strip() or result_text[:300] or f"exit code: {proc.returncode}"
                    logger.error(
                        f"❌ Claude CLI 비정상 종료 | "
                        f"코드: {proc.returncode} | "
                        f"소요: {elapsed:.1f}초 | "
                        f"stderr: {(stderr_output or '(empty)')[:200]}"
                    )
                    raise RuntimeError(f"Claude CLI 오류: {error_msg[:300]}")

                logger.info(
                    f"📝 Claude CLI 응답 완료 | "
                    f"소요: {elapsed:.1f}초 | "
                    f"응답: {len(result_text)}자"
                )

                notion_url = self._parse_notion_url(result_text)
                if notion_url:
                    logger.info(f"✅ Notion 페이지 생성 완료 | URL: {notion_url}")
                else:
                    logger.warning(
                        f"⚠️ Notion URL 파싱 실패 | "
                        f"응답 끝 200자: ...{result_text[-200:]}"
                    )

                return AnalysisResult(
                    url=url,
                    notion_url=notion_url,
                )

            except subprocess.TimeoutExpired:
                last_error = RuntimeError(
                    f"Claude CLI 타임아웃 ({config.CLAUDE_TIMEOUT}초)"
                )
                logger.warning(f"⏰ Claude CLI 타임아웃 (시도 {attempt}/3)")

            except Exception as e:
                last_error = e
                logger.warning(f"❌ Claude CLI 실패 (시도 {attempt}/3): {e}")

        raise RuntimeError(f"AI 분석 실패 (3회 시도): {last_error}") from last_error

    @staticmethod
    def _log_stream_event(event: dict):
        """stream-json 이벤트를 읽기 쉬운 로그로 출력"""
        etype = event.get("type", "")

        if etype == "system":
            logger.info(f"  [Claude] 시스템 초기화...")

        elif etype == "assistant":
            # assistant 메시지 시작 (tool_use 포함 가능)
            msg = event.get("message", {})
            content = msg.get("content", [])
            for block in content:
                if block.get("type") == "tool_use":
                    tool = block.get("name", "unknown")
                    logger.info(f"  [Claude] 🔧 도구 호출: {tool}")
                elif block.get("type") == "text":
                    text = block.get("text", "")
                    if text.strip():
                        logger.info(f"  [Claude] 💬 {text[:150]}")

        elif etype == "content_block_start":
            cb = event.get("content_block", {})
            if cb.get("type") == "tool_use":
                tool = cb.get("name", "unknown")
                logger.info(f"  [Claude] 🔧 도구 호출 시작: {tool}")

        elif etype == "result":
            cost = event.get("cost_usd", 0)
            duration = event.get("duration_ms", 0)
            turns = event.get("num_turns", 0)
            logger.info(
                f"  [Claude] ✅ 완료 | "
                f"턴: {turns} | "
                f"소요: {duration/1000:.0f}초 | "
                f"비용: ${cost:.4f}"
            )

    @staticmethod
    def _parse_notion_url(text: str) -> str:
        """Claude 응답에서 Notion URL 추출"""
        match = re.search(r"NOTION_URL:\s*(https://www\.notion\.so/\S+)", text)
        if match:
            return match.group(1)

        match = re.search(r"https://www\.notion\.so/[^\s\)]+", text)
        if match:
            return match.group(0)

        return ""

    @staticmethod
    def _extract_source(url: str) -> str:
        """URL에서 도메인 추출"""
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"
