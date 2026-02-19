import axios from 'axios';
import type { ProcessVideoResponse, VideoInfoResponse, ProcessVideoRequest } from '../types';

// 배포 환경에서는 직접 Render 백엔드 호출 (Vercel 프록시 타임아웃 회피)
const getBaseURL = () => {
  // 환경변수로 API URL 설정 가능
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // 프로덕션 환경에서는 직접 Render 백엔드 호출
  if (import.meta.env.PROD) {
    return 'https://youtubesummaryagent.onrender.com/api';
  }
  // 개발 환경에서는 로컬 프록시 사용
  return '/api';
};

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 600000, // 10분 (긴 영상 처리 시간 고려)
  headers: {
    'Content-Type': 'application/json',
  },
});

// 비디오 정보만 가져오기 (빠른 미리보기용)
export const getVideoInfo = async (url: string): Promise<VideoInfoResponse> => {
  const response = await api.post<VideoInfoResponse>('/video-info', { url });
  return response.data;
};

// 전체 처리 (요약 + Notion 저장)
export const processVideo = async (request: ProcessVideoRequest): Promise<ProcessVideoResponse> => {
  const response = await api.post<ProcessVideoResponse>('/process-video', request);
  return response.data;
};

// 빠른 처리 (Notion 저장 없이)
export const processVideoQuick = async (request: ProcessVideoRequest): Promise<ProcessVideoResponse> => {
  const response = await api.post<ProcessVideoResponse>('/process-video-quick', request);
  return response.data;
};

// 관련 동영상 타입
export interface RelatedVideo {
  video_id: string;
  title: string;
  author: string;
  thumbnail_url: string;
  url: string;
}

export interface RelatedVideosResponse {
  success: boolean;
  related_videos: RelatedVideo[];
  error?: string;
}

// 관련 동영상 가져오기
export const getRelatedVideos = async (url: string): Promise<RelatedVideosResponse> => {
  const response = await api.post<RelatedVideosResponse>('/related-videos', { url });
  return response.data;
};

// 요약 내역 타입
export interface SummaryItem {
  id: number;
  video_id: string;
  video_url: string;
  title: string;
  author: string;
  duration: number;
  thumbnail_url: string;
  notion_url: string | null;
  processing_time_ms: number | null;
  created_at: string;
}

export interface SummaryDetail extends SummaryItem {
  structured_summary: Record<string, unknown>;
  timeline: Array<{ time: string; text: string; start: number }>;
  updated_at: string;
}

export interface SummariesResponse {
  success: boolean;
  summaries: SummaryItem[];
  count: number;
  error?: string;
}

export interface SummaryDetailResponse {
  success: boolean;
  summary?: SummaryDetail;
  error?: string;
}

// 요약 내역 목록 가져오기
export const getSummaries = async (days: number = 30, limit: number = 100): Promise<SummariesResponse> => {
  const response = await api.get<SummariesResponse>('/summaries', {
    params: { days, limit }
  });
  return response.data;
};

// 요약 상세 조회 (ID로)
export const getSummaryDetail = async (summaryId: number): Promise<SummaryDetailResponse> => {
  const response = await api.get<SummaryDetailResponse>(`/summaries/${summaryId}`);
  return response.data;
};

// 비디오 ID로 요약 조회
export const getSummaryByVideoId = async (videoId: string): Promise<SummaryDetailResponse> => {
  const response = await api.get<SummaryDetailResponse>(`/summaries/video/${videoId}`);
  return response.data;
};

export default api;
