// API 응답 타입 정의

export interface VideoInfo {
  video_id: string;
  title: string;
  author: string;
  length: number;
  url: string;
  thumbnail_url?: string;
}

export interface TimelineItem {
  time: string;
  text: string;
  start?: number;
}

export interface Subtopic {
  // API returns 'title' and 'content'
  title?: string;
  content?: string;
  // Legacy fields for backward compatibility
  subtopic_title?: string;
  summary?: string;
  key_points?: string[];
  timestamp_range?: string;
}

export interface Section {
  section_title: string;
  subtopics: Subtopic[];
}

export interface KeyTerm {
  term: string;
  definition: string;
}

export interface KeyInsight {
  insight: string;
  importance: string;
}

export interface StructuredSummary {
  overview: string;
  sections: Section[];
  key_terms: KeyTerm[];
  // key_insights can be either an array of KeyInsight objects or a string from API
  key_insights: KeyInsight[] | string;
}

export interface ProcessVideoResponse {
  success: boolean;
  video_info: VideoInfo;
  timeline: TimelineItem[];
  structured_summary: StructuredSummary;
  notion_url?: string;
  error?: string;
}

export interface VideoInfoResponse {
  success: boolean;
  video_info?: VideoInfo;
  error?: string;
}

// Request types
export interface ProcessVideoRequest {
  url: string;
}

// UI State types
export type ProcessingStatus = 'idle' | 'loading' | 'success' | 'error';

export interface AppState {
  url: string;
  status: ProcessingStatus;
  result: ProcessVideoResponse | null;
  error: string | null;
}
