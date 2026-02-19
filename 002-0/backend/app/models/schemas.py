"""
Pydantic 데이터 모델 정의
"""
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any


class VideoURLRequest(BaseModel):
    """비디오 URL 요청 모델"""
    url: str = Field(..., description="YouTube 비디오 URL")


class TranscriptItem(BaseModel):
    """자막 항목 모델"""
    time: str = Field(..., description="타임스탬프 (MM:SS)")
    text: str = Field(..., description="자막 텍스트")
    start: float = Field(..., description="시작 시간 (초)")
    duration: Optional[float] = Field(None, description="지속 시간 (초)")


class VideoInfo(BaseModel):
    """비디오 정보 모델"""
    video_id: str
    title: str
    author: str
    length: int  # 초 단위
    url: str


class SectionInfo(BaseModel):
    """섹션 정보 모델"""
    title: str = Field(..., description="섹션 제목")
    start_time: str = Field(..., description="시작 시간 (MM:SS)")
    end_time: str = Field(..., description="종료 시간 (MM:SS)")
    summary: str = Field(..., description="섹션 요약")
    key_points: List[str] = Field(..., description="핵심 포인트")


class ProcessVideoResponse(BaseModel):
    """비디오 처리 응답 모델"""
    video_info: VideoInfo
    timeline: List[TranscriptItem]
    sections: List[SectionInfo]
    notion_url: Optional[str] = None
    language: str
    source: str  # "youtube" 또는 "whisper"


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str
    detail: Optional[str] = None


class StatusResponse(BaseModel):
    """상태 응답 모델"""
    status: str
    message: Optional[str] = None
    progress: Optional[int] = None  # 0-100
