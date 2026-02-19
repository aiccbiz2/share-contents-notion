"""
섹션 분류 Chain (LangChain 1.x 호환)
- 범용 회의록 스타일 영상 요약
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from app.config import settings
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


# Pydantic 모델로 출력 스키마 정의 (새로운 범용 구조)
class MainTopic(BaseModel):
    """주요 내용 요약 항목"""
    title: str = Field(description="주제 제목")
    content: str = Field(description="해당 주제의 핵심 내용을 설명형으로 상세히 정리")


class OptionalSection(BaseModel):
    """선택적 섹션 항목"""
    title: str = Field(description="섹션 제목")
    content: str = Field(description="섹션 내용")


# ========================================
# 계층화된 구조 모델 (2단계 재구성용)
# ========================================
class SubTopic(BaseModel):
    """하위 주제 항목"""
    title: str = Field(description="하위 주제 제목")
    content: str = Field(description="해당 하위 주제의 상세 내용")


class HierarchicalSection(BaseModel):
    """계층화된 대주제 섹션"""
    section_title: str = Field(description="대주제 섹션 제목 (예: AI 기초, 컨텍스트 윈도우 등)")
    section_summary: str = Field(description="이 섹션의 핵심 내용 요약 (2-3문장)")
    subtopics: List[SubTopic] = Field(description="이 섹션에 속하는 하위 주제들")


class HierarchicalSummary(BaseModel):
    """계층화된 영상 요약 결과"""
    overview: str = Field(description="영상 개요 - 전체 주제, 목적, 핵심 메시지를 한 문단으로 요약")
    sections: List[HierarchicalSection] = Field(
        description="계층화된 대주제 섹션들 (5-10개 권장)"
    )
    key_insights: str = Field(description="핵심 인사이트/결론 - 영상의 핵심 결론, 교훈, 메시지")
    key_terms: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="핵심 용어 정리 (용어: 정의 형태)"
    )
    optional_sections: Optional[List[OptionalSection]] = Field(
        default=None,
        description="선택적 섹션 - 등장인물/화자, 절차요약, 논쟁점, 기술정보 등 (필요시만)"
    )


class StructuredSummary(BaseModel):
    """범용 회의록 스타일 요약 결과"""
    overview: str = Field(description="영상 개요 - 전체 주제, 목적, 핵심 메시지를 한 문단으로 요약")
    main_topics: List[MainTopic] = Field(
        description="주요 내용 요약 - 주제별로 구조화된 회의록 방식 정제 요약"
    )
    key_insights: str = Field(description="핵심 인사이트/결론 - 영상의 핵심 결론, 교훈, 메시지")
    optional_sections: Optional[List[OptionalSection]] = Field(
        default=None,
        description="선택적 섹션 - 등장인물/화자, 절차요약, 논쟁점, 기술정보 등 (필요시만)"
    )


class SectioningChain:
    """범용 회의록 스타일 영상 요약 Chain"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
            max_tokens=8000,
            api_key=settings.OPENAI_API_KEY
        )

        # JSON 출력 파서 설정
        self.parser = JsonOutputParser(pydantic_object=StructuredSummary)

        # 청크 요약용 간단한 파서
        self.chunk_parser = JsonOutputParser()

        # ========================================
        # STEP 1: 청크별 정제 (Chunk Reconstruction)
        # ========================================
        # "요약" 단어 사용 금지 - "정제된 재구성"으로 대체
        chunk_template = """당신은 텍스트 정제 및 구조화 전문가입니다.

아래는 긴 영상의 일부분(청크 {chunk_index}/{total_chunks}) 자막입니다.
이 자막을 **원본 내용을 100% 보존**하면서 정제된 구조로 재구성해주세요.

## 자막 내용:
{chunk_content}

## ⚠️ 가장 중요한 규칙 (절대 준수):
1. **"요약"하지 마세요** - 내용을 압축하거나 줄이지 마세요
2. **중요도 판단 금지** - 어떤 내용이 더 중요한지 스스로 판단하지 마세요
3. **누락 금지** - 단 하나의 의미 단위도 임의 삭제하지 마세요
4. **사소한 잡담/감탄사만 제거** - 내용적 정보는 100% 보존

## 재구성 규칙:
1. 원문의 **모든 의미 단위**를 빠짐없이 별도 주제로 분리
2. 각 주제는 title(제목)과 content(상세 내용)로 구성
3. content는 원문 내용을 명확한 문장으로 재정리 (압축 금지)
4. 인터뷰/대담이면 각 질문-답변을 별도 주제로 분리
5. 주제 수는 의미 단위에 따라 자동 결정 (최소 {min_topics_per_chunk}개)
6. 숫자, 통계, 구체적 사례, 인용문은 반드시 포함

## 압축 비율 제어:
- 출력 텍스트는 입력 텍스트 대비 **70% 이상 유지** 권장
- 정보 손실 없이 문장만 정제하세요

## JSON 출력 형식:
{{
    "topics": [
        {{
            "title": "주제 제목",
            "content": "해당 주제의 상세 내용 (원문 정보 100% 보존)"
        }}
    ],
    "chunk_overview": "이 부분의 핵심 내용 한 문단 정리"
}}

JSON만 출력하세요:"""

        self.chunk_prompt = ChatPromptTemplate.from_template(chunk_template)
        self.chunk_chain = self.chunk_prompt | self.llm | self.chunk_parser

        # ========================================
        # STEP 2 & 3: 중복 제거 + 전체 통합
        # ========================================
        merge_template = """당신은 텍스트 통합 및 구조화 전문가입니다.

아래는 긴 영상을 여러 청크로 나누어 정제한 결과입니다.
이 결과들을 **정보 손실 없이** 하나의 완성된 구조로 통합해주세요.

## 청크별 정제 결과:
{chunk_results}

## 영상 메타데이터:
- 자막 총 길이: {subtitle_length}자 (이 길이의 **70% 이상** 정보 보존 필수)
- 자막 항목 수: {subtitle_count}개
- 청크 수: {total_chunks}개

## 출력 형식 지침:
{format_instructions}

## ⚠️ 가장 중요한 규칙 (절대 준수):
1. **"요약"하지 마세요** - 청크 결과를 압축하거나 줄이지 마세요
2. **중요도 판단 금지** - 어떤 주제가 더 중요한지 스스로 판단하지 마세요
3. **누락 금지** - 청크에서 추출된 단 하나의 주제도 임의 삭제하지 마세요
4. **중복만 병합** - 완전히 동일한 내용만 병합, 유사하면 모두 보존

## 통합 규칙:
1. overview: 영상 전체의 주제와 목적을 명확하게 기술 (3-5문장)
2. main_topics:
   - 청크에서 추출된 **모든 주제**를 포함
   - 완전히 동일한 내용만 병합 (유사하면 별도 유지)
   - 각 topic의 content는 원본 그대로 유지 (줄이지 말 것)
   - 주제 수는 의미 단위에 따라 자동 결정
3. key_insights: 영상의 핵심 결론과 메시지 (3-5문장)
4. optional_sections: 필요시만 작성

## 분량 검증:
- 입력 청크 결과 총 분량: {chunk_results_length}자
- 출력 main_topics 총 분량: 입력의 **70% 이상** 필수
- 주제 수가 줄어들어도 괜찮지만, 정보량이 줄어들면 안 됩니다

## 중요:
- 청크 분석에서 추출된 내용을 절대 누락하지 마세요
- "요약"이라는 명목으로 정보를 삭제하지 마세요
- 반드시 유효한 JSON만 출력하세요
- 한국어로 작성하세요

JSON만 출력:"""

        self.merge_prompt = ChatPromptTemplate.from_template(merge_template)
        self.merge_chain = self.merge_prompt | self.llm | self.parser

        # ========================================
        # STEP 3: 계층화 (Hierarchization)
        # - 평탄한 main_topics를 계층 구조로 재구성
        # ========================================
        self.hierarchical_parser = JsonOutputParser(pydantic_object=HierarchicalSummary)

        hierarchize_template = """당신은 텍스트 구조화 전문가입니다.

아래는 영상에서 추출된 주요 내용 목록입니다.
이 내용들을 **정보 손실 없이** 계층적 구조로 재구성해주세요.

## 입력된 주요 내용 (총 {topic_count}개):
{topics_text}

## 영상 개요:
{overview}

## 핵심 인사이트:
{key_insights}

## ⚠️ 가장 중요한 규칙 (절대 준수):
1. **모든 주제 보존 필수** - 입력된 {topic_count}개 주제가 모두 출력에 포함되어야 합니다
2. **내용 삭제 금지** - 각 주제의 content를 요약하거나 줄이지 마세요
3. **그룹화만 수행** - 비슷한 주제를 대주제 아래로 묶는 작업만 수행
4. **임의 판단 금지** - 중요도를 판단하여 제외하지 마세요

## 계층화 규칙:
1. 5-10개의 대주제(section)로 그룹화
2. 각 대주제 아래에 관련 하위 주제(subtopics) 배치
3. 대주제명은 하위 주제들의 공통 테마를 반영
4. 각 대주제에 section_summary 작성 (2-3문장)
5. 하위 주제의 title과 content는 원본 그대로 유지

## 대주제 예시 (영상 내용에 맞게 조정):
- AI 기초 개념
- 핵심 기술 요소
- 실무 적용 방법
- 도구 및 프레임워크
- 학습 로드맵
등 (영상 내용에 따라 달라짐)

## 출력 형식:
{format_instructions}

## 검증 체크리스트:
- [ ] 입력 주제 수({topic_count}개) = 출력 subtopics 총합
- [ ] 각 subtopic의 content가 원본과 동일
- [ ] 모든 대주제에 최소 1개 이상의 subtopic 존재

## 핵심 용어 (key_terms):
영상에서 등장한 중요한 전문 용어나 개념이 있다면 key_terms에 정리해주세요.
형식: [{{"term": "용어", "definition": "정의"}}]

JSON만 출력하세요:"""

        self.hierarchize_prompt = ChatPromptTemplate.from_template(hierarchize_template)
        self.hierarchize_chain = self.hierarchize_prompt | self.llm | self.hierarchical_parser

        # 범용 회의록 스타일 프롬프트
        template = """당신은 YouTube 영상 분석 및 요약 전문가입니다.

아래 영상 자막을 정확하게 이해하고, 다음 구조에 따라 요약하세요.
영상 형식(인터뷰, 강의, 토론, 정보 영상, 드라마·영화 등)에 관계없이 적용되는 범용 구조입니다.

## ⚠️ 중요 메타데이터:
- 자막 총 길이: {subtitle_length}자
- 자막 항목 수: {subtitle_count}개
- 필수 main_topics 수: 최소 {min_topics}개 이상
- 필수 main_topics 총 글자 수: 최소 {min_content_length}자 이상 (자막 길이의 약 15%)
- 각 topic의 content: 평균 {avg_content_per_topic}자 이상 권장

## 영상 자막 내용:
{full_content}

## 출력 형식 지침:
{format_instructions}

## 요약 출력 구조:

### 1) 영상 개요 (overview)
- 영상의 전체 주제, 목적, 핵심 메시지를 한 문단으로 명확하게 요약
- 영상의 형식(인터뷰/토론/정보/서사/튜토리얼 등)을 자연스럽게 설명
- 불필요한 장면 묘사·감정 표현은 배제하고, 본질적인 주제 중심으로 기술
- 3-5문장으로 작성

### 2) 주요 내용 요약 (main_topics) - 가장 중요한 섹션 ⚠️ 최소 {min_topics}개 필수
회의록 방식 정제 요약으로 작성합니다.

**정제 규칙:**
- 원문의 의미와 정보는 임의 삭제 없이 최대한 보존
- 질문·답변 형식, 감탄사, 잡담, 반복 표현은 제거
- 영상 속 내용의 논리 구조와 흐름을 유지하면서 명확한 문장으로 재정리
- 영상 형식에 관계없이 '주제별·내용 단위별'로 구조화
- 필요 시 주제 제목을 새로 붙여도 됨(의미 기반으로)

**작성 형식:**
각 항목은 title(주제 제목)과 content(상세 내용)로 구성합니다.
- content는 해당 주제에서 다루어진 핵심 내용 전체를 설명형으로 명확하게 정리
- 의견 차이·논쟁·배경 맥락이 있었다면 포함
- 인터뷰 내용이라도 Q/A 흐름을 제거하고 순수 내용 중심으로 정제
- 중요한 내용은 절대 누락하지 말고, 주제가 많아지더라도 모두 포함

**🚨🚨🚨 절대 준수 사항 (이 기준 미달 시 출력 거부) 🚨🚨🚨**

📊 수량 기준:
- main_topics 최소 개수: {min_topics}개 이상 필수
- 인터뷰/대담 영상: 질문마다 별도 주제로 분리하여 더 많이 작성

📏 분량 기준 (가장 중요!):
- main_topics 전체 content 합계: 최소 {min_content_length}자 이상 (자막의 약 15%)
- 각 topic의 content 길이: 평균 {avg_content_per_topic}자 이상
- content는 절대 1-2문장으로 끝내지 말고, 해당 주제의 모든 세부 내용을 상세히 서술

⚠️ 주의사항:
- {min_topics}개 미만 또는 총 {min_content_length}자 미만이면 중요 내용 누락 확정
- 주제가 많아도 괜찮습니다. 부족한 것보다 많은 것이 훨씬 낫습니다
- "요약"이라는 명목으로 압축하지 마세요. 정보를 최대한 보존하세요

**작성 예시:**
- title: "AI와 창작의 미래"
  content: "AI는 인간의 창작 능력을 확장하는 도구가 되어야 한다는 점이 강조되었다. 특정 작가 스타일을 무단으로 사용하거나 동의 없이 창작물을 학습·생성하는 문제에 대한 우려가 존재한다. 특히 유명 작가나 아티스트의 고유한 스타일을 AI가 복제하는 것에 대한 윤리적 논쟁이 활발하다. 미래에는 창작자 동의 기반의 수익 공유 모델이 등장할 수 있으며, 단순 '모방'과 '참조' 사이 구분을 명확히 해야 한다고 언급되었다. 또한 AI 도구를 활용한 새로운 형태의 창작이 가능해지면서, 기존 저작권 체계의 재정립이 필요하다는 의견도 제시되었다."

### 3) 핵심 인사이트 / 결론 (key_insights)
- 영상에서 전달하고자 하는 핵심 결론, 교훈, 메시지를 명확하게 요약
- 정보/기술 영상은 핵심 배움·통찰을, 서사 영상은 주제적 의미나 메시지를 정리
- 전체 내용의 압축된 요체로 마무리
- 3-5문장으로 작성

### 4) 선택적 섹션 (optional_sections) - 필요할 때만 작성
아래 항목은 영상에 해당 요소가 있을 때만 포함합니다. 필요 없는 경우 null 또는 빈 배열로 설정합니다.

가능한 선택적 섹션:
- "등장인물·화자 구성": 주요 등장인물이나 화자 정보
- "절차 요약 / 실습 단계 정리": How-to나 튜토리얼 영상의 단계별 정리
- "주요 논쟁점 / 문제 제기 / 해결 논리": 영상에서 다룬 논쟁과 해결 방향
- "기술·정보 요소 정리": 기술적 세부사항이나 정보 정리

## 작성 스타일 규칙:
- 문장은 간결하되 충분히 설명적이어야 합니다
- 원문을 임의로 압축하거나 누락하지 말고, 정확성과 명료성을 최우선으로 합니다
- 영상의 감정·톤·잡음은 제거하고, 컨텐츠의 본질적 의미만 전달하도록 정제합니다
- 전체는 '보고서/회의록 스타일'로 일관되게 작성합니다

## ⚠️ 절대 누락 금지 (가장 중요한 규칙):
- 영상에서 언급된 모든 주요 내용, 주장, 사례, 인물, 기능, 개념을 반드시 포함하세요
- "요약"이라는 명목으로 중요한 정보를 생략하거나 압축하지 마세요
- 영상이 길더라도 모든 핵심 논점을 빠짐없이 main_topics에 포함해야 합니다
- 인터뷰/대담 영상의 경우, 언급된 모든 주제와 질문에 대한 답변을 포함하세요
- 숫자, 통계, 구체적 사례, 인용문 등 구체적인 정보는 특히 누락하지 마세요
- 불확실하면 포함하세요. 누락보다 포함이 낫습니다

## 중요:
- 반드시 유효한 JSON만 출력하세요
- 마크다운 코드 블록을 사용하지 마세요
- 추가 설명 없이 JSON만 출력하세요
- 모든 내용은 한국어로 작성하세요"""

        self.prompt = ChatPromptTemplate.from_template(template)

        # LangChain 1.x LCEL 방식
        self.chain = self.prompt | self.llm | self.parser

        logger.info("범용 회의록 스타일 요약 Chain 초기화 완료")

    def _calculate_min_topics(self, subtitle_length: int, subtitle_count: int) -> int:
        """
        자막 길이에 따른 최소 주제 수 계산

        Args:
            subtitle_length: 자막 총 문자 수
            subtitle_count: 자막 항목 수

        Returns:
            최소 main_topics 수
        """
        # 기본 기준: 자막 길이 기반
        if subtitle_length < 10000:
            min_topics = 5
        elif subtitle_length < 20000:
            min_topics = 10
        elif subtitle_length < 40000:
            min_topics = 15
        else:
            min_topics = 20

        # 항목 수가 많으면 (인터뷰/대담 가능성) 더 많은 주제 요구
        if subtitle_count > 500:
            min_topics = max(min_topics, 15)
        if subtitle_count > 800:
            min_topics = max(min_topics, 20)

        return min_topics

    def analyze_video(self, timeline: List[Dict], retry_count: int = 0) -> Dict:
        """
        범용 회의록 스타일 영상 분석 (청크 기반 처리)

        Args:
            timeline: 타임라인 데이터 리스트
            retry_count: 재시도 횟수 (내부 사용)

        Returns:
            구조화된 요약 결과 딕셔너리
        """
        try:
            # 메타데이터 계산
            full_content = self._timeline_to_text(timeline)
            subtitle_length = len(full_content)
            subtitle_count = len(timeline)
            min_topics = self._calculate_min_topics(subtitle_length, subtitle_count)

            logger.info(
                f"청크 기반 분석 시작: {subtitle_length}자, {subtitle_count}개 항목 | "
                f"목표: 최소 {min_topics}개 주제"
            )

            # 청크 기반 처리 (100개 항목씩)
            CHUNK_SIZE = 100
            MIN_TOPICS_PER_CHUNK = 3

            # 타임라인을 청크로 분할
            chunks = []
            for i in range(0, len(timeline), CHUNK_SIZE):
                chunk = timeline[i:i + CHUNK_SIZE]
                chunks.append(chunk)

            total_chunks = len(chunks)
            logger.info(f"총 {total_chunks}개 청크로 분할 (청크당 {CHUNK_SIZE}개 항목)")

            # 각 청크 분석
            all_chunk_results = []
            for idx, chunk in enumerate(chunks):
                chunk_content = self._timeline_to_text(chunk)
                logger.info(f"청크 {idx + 1}/{total_chunks} 분석 중... ({len(chunk)}개 항목, {len(chunk_content)}자)")

                try:
                    chunk_result = self.chunk_chain.invoke({
                        "chunk_index": idx + 1,
                        "total_chunks": total_chunks,
                        "chunk_content": chunk_content,
                        "min_topics_per_chunk": MIN_TOPICS_PER_CHUNK
                    })

                    topics = chunk_result.get("topics", [])
                    chunk_summary = chunk_result.get("chunk_summary", "")
                    logger.info(f"청크 {idx + 1} 완료: {len(topics)}개 주제 추출")

                    all_chunk_results.append({
                        "chunk_index": idx + 1,
                        "topics": topics,
                        "summary": chunk_summary
                    })

                except Exception as e:
                    logger.warning(f"청크 {idx + 1} 분석 실패: {e}")
                    continue

            # 청크 결과가 없으면 기본 요약 반환
            if not all_chunk_results:
                logger.error("모든 청크 분석 실패")
                return self._create_default_summary(timeline)

            # 총 추출된 주제 수 계산
            total_topics = sum(len(r.get("topics", [])) for r in all_chunk_results)
            logger.info(f"청크 분석 완료: 총 {total_topics}개 주제 추출됨")

            # 청크 결과 병합
            merged_result = self._merge_chunk_results(
                all_chunk_results,
                subtitle_length,
                subtitle_count,
                min_topics
            )

            # 병합 결과 검증
            main_topics = merged_result.get('main_topics', [])
            merged_topic_count = len(main_topics)
            merged_content_length = sum(len(t.get('content', '')) for t in main_topics)

            logger.info(
                f"병합 완료: {merged_topic_count}개 주제, 총 {merged_content_length}자"
            )

            # 계층화 단계 (주제가 많을 때만 실행)
            if merged_topic_count >= 10:
                logger.info("계층화 단계 시작...")
                hierarchical_result = self._hierarchize_topics(merged_result)

                if hierarchical_result:
                    # 계층화 성공: 섹션 수와 총 subtopic 수 확인
                    sections = hierarchical_result.get('sections', [])
                    total_subtopics = sum(len(s.get('subtopics', [])) for s in sections)
                    logger.info(
                        f"계층화 완료: {len(sections)}개 섹션, 총 {total_subtopics}개 하위 주제"
                    )
                    return hierarchical_result
                else:
                    logger.warning("계층화 실패, 병합 결과 반환")
                    return merged_result
            else:
                logger.info(f"주제 수가 적음({merged_topic_count}개), 계층화 건너뜀")
                return merged_result

        except Exception as e:
            logger.error(f"영상 분석 실패: {e}", exc_info=True)
            return self._create_default_summary(timeline)

    def _merge_chunk_results(
        self,
        chunk_results: List[Dict],
        subtitle_length: int,
        subtitle_count: int,
        min_topics: int
    ) -> Dict:
        """
        청크 결과를 병합하여 최종 요약 생성

        Args:
            chunk_results: 청크별 분석 결과 리스트
            subtitle_length: 전체 자막 길이
            subtitle_count: 전체 자막 항목 수
            min_topics: 최소 주제 수

        Returns:
            병합된 최종 요약
        """
        try:
            # 청크 결과를 텍스트로 포맷
            chunk_results_text = ""
            for cr in chunk_results:
                chunk_results_text += f"\n### 청크 {cr['chunk_index']} 분석 결과:\n"
                chunk_results_text += f"요약: {cr.get('summary', '')}\n"
                chunk_results_text += "주제들:\n"
                for topic in cr.get("topics", []):
                    title = topic.get("title", "")
                    content = topic.get("content", "")
                    chunk_results_text += f"- {title}: {content}\n"

            chunk_results_length = len(chunk_results_text)
            logger.info(f"병합 요청: {len(chunk_results)}개 청크 결과 ({chunk_results_length}자)")

            # 병합 LLM 호출
            format_instructions = self.parser.get_format_instructions()
            result = self.merge_chain.invoke({
                "chunk_results": chunk_results_text,
                "subtitle_length": subtitle_length,
                "subtitle_count": subtitle_count,
                "total_chunks": len(chunk_results),
                "chunk_results_length": chunk_results_length,
                "format_instructions": format_instructions
            })

            if not result or "overview" not in result:
                logger.warning("병합 실패: 유효한 결과를 받지 못함, 직접 병합 시도")
                return self._direct_merge_chunks(chunk_results)

            return result

        except Exception as e:
            logger.error(f"병합 실패: {e}")
            return self._direct_merge_chunks(chunk_results)

    def _direct_merge_chunks(self, chunk_results: List[Dict]) -> Dict:
        """
        LLM 없이 직접 청크 결과 병합 (폴백)

        Args:
            chunk_results: 청크별 분석 결과

        Returns:
            직접 병합된 결과
        """
        all_topics = []
        all_summaries = []

        for cr in chunk_results:
            all_summaries.append(cr.get("summary", ""))
            for topic in cr.get("topics", []):
                all_topics.append({
                    "title": topic.get("title", ""),
                    "content": topic.get("content", "")
                })

        return {
            "overview": " ".join(all_summaries[:3]) if all_summaries else "영상 요약",
            "main_topics": all_topics,
            "key_insights": all_summaries[-1] if all_summaries else "영상 내용을 참고해주세요.",
            "optional_sections": None
        }

    def _hierarchize_topics(self, merged_result: Dict) -> Optional[Dict]:
        """
        평탄한 main_topics를 계층 구조로 재구성

        Args:
            merged_result: 병합된 결과 (overview, main_topics, key_insights 포함)

        Returns:
            계층화된 결과 또는 None (실패 시)
        """
        try:
            main_topics = merged_result.get('main_topics', [])
            overview = merged_result.get('overview', '')
            key_insights = merged_result.get('key_insights', '')
            optional_sections = merged_result.get('optional_sections')

            if not main_topics:
                logger.warning("계층화할 주제가 없습니다")
                return None

            topic_count = len(main_topics)

            # 주제들을 텍스트로 변환
            topics_text = ""
            for i, topic in enumerate(main_topics, 1):
                title = topic.get('title', '')
                content = topic.get('content', '')
                topics_text += f"{i}. {title}\n   내용: {content}\n\n"

            logger.info(f"계층화 요청: {topic_count}개 주제, {len(topics_text)}자")

            # 계층화 체인 호출
            format_instructions = self.hierarchical_parser.get_format_instructions()
            result = self.hierarchize_chain.invoke({
                "topic_count": topic_count,
                "topics_text": topics_text,
                "overview": overview,
                "key_insights": key_insights,
                "format_instructions": format_instructions
            })

            if not result or "sections" not in result:
                logger.warning("계층화 실패: 유효한 결과를 받지 못함")
                return None

            # 결과 검증: 모든 주제가 포함되었는지 확인
            sections = result.get('sections', [])
            total_subtopics = sum(len(s.get('subtopics', [])) for s in sections)

            if total_subtopics < topic_count * 0.8:
                logger.warning(
                    f"계층화 검증 실패: 입력 {topic_count}개 vs 출력 {total_subtopics}개 "
                    f"(80% 미만 보존)"
                )
                # 검증 실패해도 결과 반환 (경고만 출력)

            # optional_sections 보존
            if optional_sections:
                result['optional_sections'] = optional_sections

            return result

        except Exception as e:
            logger.error(f"계층화 실패: {e}")
            return None

    def _timeline_to_text(self, timeline: List[Dict]) -> str:
        """
        타임라인을 텍스트로 변환

        Args:
            timeline: 타임라인 데이터

        Returns:
            변환된 텍스트
        """
        lines = []
        for item in timeline:
            time = item.get("time", "00:00")
            text = item.get("text", "")
            lines.append(f"[{time}] {text}")

        return "\n".join(lines)

    def _timeline_to_text_sampled(self, timeline: List[Dict], max_chars: int = None) -> str:
        """
        타임라인을 텍스트로 변환 (제한 없이 전체 사용)

        Args:
            timeline: 타임라인 데이터
            max_chars: 최대 문자 수 (None이면 제한 없음)

        Returns:
            변환된 텍스트
        """
        # 전체 텍스트 생성 - 제한 없이 모든 자막 사용
        full_text = self._timeline_to_text(timeline)
        logger.info(f"자막 전체 사용: {len(full_text)} 문자, {len(timeline)}개 항목")
        return full_text

    def _create_default_summary(self, timeline: List[Dict]) -> Dict:
        """
        기본 요약 생성 (LLM 실패 시 대체)

        Args:
            timeline: 타임라인 데이터

        Returns:
            기본 요약 데이터
        """
        return {
            "overview": "영상 분석을 자동으로 수행할 수 없습니다.",
            "main_topics": [
                {"title": "전체 내용", "content": "자막 원본을 참고해주세요."}
            ],
            "key_insights": "영상 내용을 직접 확인해주세요.",
            "optional_sections": None
        }

    def classify_sections_with_summary(self, timeline: List[Dict]) -> Dict:
        """
        범용 회의록 스타일 영상 분석 (기존 인터페이스 호환)

        Args:
            timeline: 타임라인 데이터

        Returns:
            sections (호환용) + structured_summary + full_summary
        """
        try:
            # 범용 구조 기반 분석
            structured_data = self.analyze_video(timeline)

            # 전체 요약 문자열 생성 (개요 + 결론)
            full_summary = self._generate_full_summary_from_structure(structured_data)

            # 기존 sections 형식으로 변환 (호환성 유지)
            sections = self._convert_to_sections_format(structured_data)

            return {
                "sections": sections,
                "structured_summary": structured_data,
                "full_summary": full_summary
            }

        except Exception as e:
            logger.error(f"영상 분석 실패: {e}")
            return {
                "sections": [],
                "structured_summary": None,
                "full_summary": "요약 생성 실패"
            }

    def _generate_full_summary_from_structure(self, structured_data: Dict) -> str:
        """
        구조화된 데이터에서 전체 요약 문자열 생성

        Args:
            structured_data: 범용 구조 데이터

        Returns:
            전체 요약 문자열
        """
        parts = []

        # 개요
        overview = structured_data.get("overview", "")
        if overview:
            parts.append(overview)

        # 주요 내용에서 상위 3개만 추출
        main_topics = structured_data.get("main_topics", [])
        if main_topics:
            topic_summaries = []
            for topic in main_topics[:3]:
                title = topic.get("title", "")
                content = topic.get("content", "")
                if title and content:
                    topic_summaries.append(f"{title}: {content}")
            if topic_summaries:
                parts.append("\n".join(topic_summaries))

        # 핵심 인사이트
        key_insights = structured_data.get("key_insights", "")
        if key_insights:
            parts.append(key_insights)

        return "\n\n".join(parts) if parts else "요약 없음"

    def _convert_to_sections_format(self, structured_data: Dict) -> List[Dict]:
        """
        범용 구조 데이터를 기존 sections 형식으로 변환

        Args:
            structured_data: 범용 구조 데이터

        Returns:
            기존 sections 형식 리스트
        """
        sections = []

        # main_topics를 sections로 변환
        main_topics = structured_data.get("main_topics", [])
        for i, topic in enumerate(main_topics):
            section = {
                "title": topic.get("title", f"주제 {i+1}"),
                "start_time": "",
                "end_time": "",
                "summary": topic.get("content", ""),
                "key_points": []
            }
            sections.append(section)

        return sections

    # 기존 메서드 호환성 유지
    def classify_sections(self, timeline: List[Dict]) -> Dict:
        """기존 인터페이스 호환 - analyze_video 호출"""
        result = self.analyze_video(timeline)
        return {"sections": self._convert_to_sections_format(result)}
