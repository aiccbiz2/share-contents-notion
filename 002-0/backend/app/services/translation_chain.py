"""
번역 및 정제 Chain (LangChain 1.x 호환)
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from typing import List, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 프롬프트 파일 경로 (절대 경로)
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "shared" / "prompts"


class TranslationChain:
    """번역 및 정제 Chain"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.OPENAI_API_KEY
        )

        # Prompt 템플릿 로드 (절대 경로 사용)
        prompt_file = PROMPTS_DIR / "translation_prompt.txt"
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()
            logger.info(f"프롬프트 파일 로드 성공: {prompt_file}")
        except FileNotFoundError:
            logger.warning(f"프롬프트 파일 없음, 기본 템플릿 사용: {prompt_file}")
            # 파일 읽기 실패 시 기본 템플릿 사용
            template = """당신은 전문 번역가입니다.

다음 텍스트를 한국어로 자연스럽게 번역하고 정제해주세요.

원본 언어: {source_lang}
원본 텍스트:
{text}

번역 규칙:
1. 자연스러운 한국어 표현 사용
2. 불필요한 반복 제거
3. 문장 구조 개선
4. 전문 용어는 영문 병기

번역 결과만 반환해주세요:
"""

        self.prompt = PromptTemplate(
            input_variables=["text", "source_lang"],
            template=template
        )

        # LangChain 1.x LCEL 방식
        self.chain = self.prompt | self.llm | StrOutputParser()

    def translate_text(self, text: str, source_lang: str = "영어") -> str:
        """
        텍스트 번역 및 정제

        Args:
            text: 원본 텍스트
            source_lang: 원본 언어

        Returns:
            번역된 텍스트
        """
        try:
            if source_lang == "ko" or source_lang == "한국어":
                # 한국어는 정제만 수행
                result = self.chain.invoke({"text": text, "source_lang": "한국어 (정제만 필요)"})
            else:
                result = self.chain.invoke({"text": text, "source_lang": source_lang})

            return result.strip()

        except Exception as e:
            logger.error(f"번역 실패: {e}")
            # 번역 실패 시 원본 반환
            return text

    def translate_timeline(self, timeline: List[Dict], source_lang: str = "영어") -> List[Dict]:
        """
        타임라인 전체 번역

        Args:
            timeline: 타임라인 데이터 리스트
            source_lang: 원본 언어

        Returns:
            번역된 타임라인
        """
        translated_timeline = []

        try:
            # 배치 처리를 위해 모든 텍스트 결합
            texts = [item["text"] for item in timeline]
            combined_text = "\n---\n".join(texts)

            # 번역
            translated_combined = self.translate_text(combined_text, source_lang)
            translated_texts = translated_combined.split("\n---\n")

            # 타임라인에 적용
            for item, translated_text in zip(timeline, translated_texts):
                translated_item = item.copy()
                translated_item["text"] = translated_text.strip()
                translated_timeline.append(translated_item)

            return translated_timeline

        except Exception as e:
            logger.error(f"타임라인 번역 실패: {e}")
            # 실패 시 원본 반환
            return timeline

    def translate_timeline_chunked(
        self,
        timeline: List[Dict],
        source_lang: str = "영어",
        chunk_size: int = 20
    ) -> List[Dict]:
        """
        타임라인을 청크 단위로 번역 (긴 영상 대응)

        Args:
            timeline: 타임라인 데이터 리스트
            source_lang: 원본 언어
            chunk_size: 청크 크기 (한 번에 처리할 항목 수)

        Returns:
            번역된 타임라인
        """
        translated_timeline = []
        total_chunks = (len(timeline) + chunk_size - 1) // chunk_size

        try:
            # 청크 단위로 처리
            for i in range(0, len(timeline), chunk_size):
                chunk = timeline[i:i + chunk_size]
                chunk_num = i // chunk_size + 1

                # 청크 번역
                texts = [item["text"] for item in chunk]
                combined_text = "\n---\n".join(texts)

                translated_combined = self.translate_text(combined_text, source_lang)
                translated_texts = translated_combined.split("\n---\n")

                # 항목 수 일치 확인
                if len(translated_texts) != len(chunk):
                    logger.warning(
                        f"청크 {chunk_num}: 항목 수 불일치 "
                        f"(원본 {len(chunk)}개, 번역 {len(translated_texts)}개) - 개별 번역 시도"
                    )
                    # 항목 수 불일치 시 개별 항목 번역 시도
                    for item in chunk:
                        try:
                            translated_text = self.translate_text(item["text"], source_lang)
                            translated_item = item.copy()
                            translated_item["text"] = translated_text.strip()
                            translated_timeline.append(translated_item)
                        except Exception as e:
                            logger.warning(f"개별 번역 실패: {e} - 원본 유지")
                            translated_timeline.append(item.copy())
                else:
                    # 정상: 결과 적용
                    for item, translated_text in zip(chunk, translated_texts):
                        translated_item = item.copy()
                        translated_item["text"] = translated_text.strip()
                        translated_timeline.append(translated_item)

                logger.info(f"청크 {chunk_num}/{total_chunks} 번역 완료 ({len(chunk)}개 항목)")

            logger.info(f"번역 완료: 원본 {len(timeline)}개 → 결과 {len(translated_timeline)}개 항목")
            return translated_timeline

        except Exception as e:
            logger.error(f"청크 번역 실패: {e}")
            return timeline
