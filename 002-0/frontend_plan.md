# Frontend 개발 계획서

## YouTube Summary Agent - Frontend

**버전**: v1.0.0
**작성일**: 2025-12-02
**작성자**: Claude

---

## 1. 기술 스택

### 1.1 Core
- **React 18** - UI 라이브러리
- **TypeScript** - 타입 안전성
- **Vite** - 빌드 도구 (빠른 개발 환경)

### 1.2 Styling
- **Tailwind CSS** - 유틸리티 기반 CSS
- **Headless UI** - 접근성 지원 컴포넌트

### 1.3 State Management
- **React Query (TanStack Query)** - 서버 상태 관리
- **Zustand** - 클라이언트 상태 관리 (필요시)

### 1.4 기타
- **Axios** - HTTP 클라이언트
- **React Router** - 라우팅 (필요시)

---

## 2. 프로젝트 구조

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── components/          # 재사용 컴포넌트
│   │   ├── common/          # 공통 UI 컴포넌트
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Loading.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── Accordion.tsx
│   │   ├── VideoInput/      # URL 입력 영역
│   │   │   └── VideoInput.tsx
│   │   ├── VideoInfo/       # 영상 정보 표시
│   │   │   └── VideoInfoCard.tsx
│   │   ├── Summary/         # 요약 결과 표시
│   │   │   ├── SummarySection.tsx
│   │   │   ├── OverviewCard.tsx
│   │   │   ├── SectionList.tsx
│   │   │   ├── SubtopicItem.tsx
│   │   │   ├── KeyTerms.tsx
│   │   │   └── KeyInsights.tsx
│   │   └── Timeline/        # 타임라인 표시
│   │       ├── TimelineView.tsx
│   │       └── TimelineItem.tsx
│   ├── hooks/               # 커스텀 훅
│   │   ├── useVideoProcess.ts
│   │   └── useVideoInfo.ts
│   ├── services/            # API 서비스
│   │   └── api.ts
│   ├── types/               # TypeScript 타입
│   │   └── index.ts
│   ├── utils/               # 유틸리티 함수
│   │   └── formatters.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

---

## 3. 페이지 레이아웃 설계

### 3.1 전체 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│                         Header                               │
│              YouTube Summary Agent                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               URL 입력 영역                          │    │
│  │  ┌─────────────────────────────────────────┐ ┌────┐ │    │
│  │  │ https://www.youtube.com/watch?v=...     │ │처리│ │    │
│  │  └─────────────────────────────────────────┘ └────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               처리 상태 표시 (로딩 시)               │    │
│  │  ─────────────────────────────────  60%              │    │
│  │  "자막 번역 중... (3/5)"                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               영상 정보 카드                         │    │
│  │  ┌──────────┐  제목: ...                            │    │
│  │  │ 썸네일   │  채널: ...                            │    │
│  │  │          │  재생시간: ...                        │    │
│  │  └──────────┘  [Notion에서 보기] [YouTube 열기]     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               탭 네비게이션                          │    │
│  │  [ 요약 ]  [ 타임라인 ]                              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               요약 영역                              │    │
│  │                                                      │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │ 영상 개요                                      │  │    │
│  │  │ ...                                            │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                      │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │ ▼ 섹션 1: 대주제 제목                         │  │    │
│  │  │    섹션 요약...                                │  │    │
│  │  │    ├─ 소주제 1                                │  │    │
│  │  │    │    내용...                               │  │    │
│  │  │    └─ 소주제 2                                │  │    │
│  │  │         내용...                               │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                      │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │ 핵심 용어                                      │  │    │
│  │  │ 용어1 | 용어2 | 용어3 | ...                   │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                      │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │ 핵심 인사이트                                  │  │    │
│  │  │ ...                                            │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                         Footer                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 타임라인 탭 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 검색: [________________] 총 1505개 항목                │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 00:00  자막 내용...                                    │  │
│  │ 00:15  자막 내용...                                    │  │
│  │ 00:32  자막 내용...                                    │  │
│  │ ...                                                    │  │
│  │ (무한 스크롤 또는 페이지네이션)                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 컴포넌트 상세 설계

### 4.1 VideoInput 컴포넌트

```typescript
interface VideoInputProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
}

// 기능:
// - YouTube URL 입력
// - URL 유효성 검증 (클라이언트 측)
// - 처리 버튼 (로딩 중 비활성화)
// - 붙여넣기 시 자동 감지
```

### 4.2 ProcessingStatus 컴포넌트

```typescript
interface ProcessingStatusProps {
  status: 'idle' | 'loading' | 'success' | 'error';
  progress?: number;        // 0-100
  currentStep?: string;     // "자막 추출 중...", "번역 중..."
  estimatedTime?: number;   // 예상 남은 시간 (초)
}

// 기능:
// - 프로그레스 바 표시
// - 현재 처리 단계 표시
// - 예상 시간 표시 (향후)
```

### 4.3 VideoInfoCard 컴포넌트

```typescript
interface VideoInfo {
  video_id: string;
  title: string;
  author: string;
  length: number;    // 초
  url: string;
}

interface VideoInfoCardProps {
  videoInfo: VideoInfo;
  notionUrl?: string;
}

// 기능:
// - 영상 썸네일 표시 (YouTube API)
// - 영상 제목/채널명/재생시간 표시
// - YouTube 링크 버튼
// - Notion 페이지 링크 버튼 (있을 경우)
```

### 4.4 SummarySection 컴포넌트

```typescript
interface Section {
  section_title: string;
  section_summary: string;
  subtopics: {
    title: string;
    content: string;
  }[];
}

interface StructuredSummary {
  overview: string;
  sections: Section[];
  key_insights: string;
  key_terms: string[];
}

interface SummarySectionProps {
  summary: StructuredSummary;
}

// 기능:
// - 영상 개요 표시
// - 섹션별 아코디언 (접기/펼치기)
// - 소주제 계층 구조 표시
// - 핵심 용어 태그 형태 표시
// - 핵심 인사이트 하이라이트
```

### 4.5 TimelineView 컴포넌트

```typescript
interface TimelineItem {
  time: string;    // "00:00" 형식
  text: string;
  start: number;   // 초
}

interface TimelineViewProps {
  timeline: TimelineItem[];
}

// 기능:
// - 가상화 리스트 (react-window 사용 - 성능)
// - 검색 필터
// - 타임스탬프 클릭 시 복사 또는 YouTube로 이동
// - 무한 스크롤
```

---

## 5. API 인터페이스

### 5.1 타입 정의 (types/index.ts)

```typescript
// API 요청
export interface VideoRequest {
  url: string;
}

// API 응답
export interface VideoInfoResponse {
  video_id: string;
  title: string;
  author: string;
  length: number;
  url: string;
}

export interface TimelineItem {
  time: string;
  text: string;
  start: number;
}

export interface Subtopic {
  title: string;
  content: string;
}

export interface Section {
  section_title: string;
  section_summary: string;
  subtopics: Subtopic[];
}

export interface StructuredSummary {
  overview: string;
  sections: Section[];
  key_insights: string;
  key_terms: string[];
}

export interface ProcessVideoResponse {
  success: boolean;
  video_info: VideoInfoResponse;
  timeline: TimelineItem[];
  structured_summary: StructuredSummary;
  full_summary: string;
  notion_url: string | null;
  language: string;
  source: string;
  message: string;
}
```

### 5.2 API 서비스 (services/api.ts)

```typescript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const videoService = {
  // 영상 정보만 조회
  getVideoInfo: async (url: string) => {
    const response = await api.post('/api/video-info', { url });
    return response.data;
  },

  // 전체 처리 (요약 포함)
  processVideo: async (url: string) => {
    const response = await api.post('/api/process-video', { url });
    return response.data;
  },

  // 빠른 처리 (테스트용)
  processVideoQuick: async (url: string) => {
    const response = await api.post('/api/process-video-quick', { url });
    return response.data;
  },
};
```

---

## 6. 상태 관리

### 6.1 React Query 사용

```typescript
// hooks/useVideoProcess.ts
import { useMutation } from '@tanstack/react-query';
import { videoService } from '../services/api';

export const useVideoProcess = () => {
  return useMutation({
    mutationFn: (url: string) => videoService.processVideo(url),
    onSuccess: (data) => {
      console.log('처리 완료:', data);
    },
    onError: (error) => {
      console.error('처리 실패:', error);
    },
  });
};
```

---

## 7. 개발 단계

### Phase 1: 기본 구조 (1일)
- [ ] Vite + React + TypeScript 프로젝트 생성
- [ ] Tailwind CSS 설정
- [ ] 기본 폴더 구조 생성
- [ ] API 서비스 설정

### Phase 2: 핵심 컴포넌트 (2일)
- [ ] VideoInput 컴포넌트
- [ ] VideoInfoCard 컴포넌트
- [ ] Loading/ProgressBar 컴포넌트
- [ ] 기본 레이아웃 완성

### Phase 3: 요약 표시 (2일)
- [ ] OverviewCard 컴포넌트
- [ ] SectionList 컴포넌트 (아코디언)
- [ ] SubtopicItem 컴포넌트
- [ ] KeyTerms/KeyInsights 컴포넌트

### Phase 4: 타임라인 (1일)
- [ ] TimelineView 컴포넌트
- [ ] 가상화 리스트 적용
- [ ] 검색 기능

### Phase 5: 마무리 (1일)
- [ ] 에러 처리 UI
- [ ] 반응형 디자인
- [ ] 테스트 및 버그 수정

---

## 8. 디자인 가이드라인

### 8.1 색상 팔레트

```css
/* Primary */
--primary-500: #3B82F6;     /* 메인 파란색 */
--primary-600: #2563EB;     /* 호버 */

/* Neutral */
--gray-50: #F9FAFB;         /* 배경 */
--gray-100: #F3F4F6;        /* 카드 배경 */
--gray-700: #374151;        /* 텍스트 */
--gray-900: #111827;        /* 제목 */

/* Accent */
--green-500: #10B981;       /* 성공 */
--red-500: #EF4444;         /* 에러 */
--yellow-500: #F59E0B;      /* 경고 */
```

### 8.2 타이포그래피

```css
/* 제목 */
.heading-1: 2rem (32px), font-bold
.heading-2: 1.5rem (24px), font-semibold
.heading-3: 1.25rem (20px), font-semibold

/* 본문 */
.body-large: 1.125rem (18px)
.body-normal: 1rem (16px)
.body-small: 0.875rem (14px)
```

### 8.3 간격

```css
/* Tailwind 기준 */
p-4: 1rem (16px)    /* 카드 패딩 */
gap-4: 1rem (16px)  /* 요소 간격 */
mb-6: 1.5rem (24px) /* 섹션 마진 */
```

---

## 9. 성능 최적화

### 9.1 코드 분할
- React.lazy를 사용한 컴포넌트 지연 로딩
- 타임라인 탭은 별도 청크로 분리

### 9.2 가상화
- 1000개 이상의 타임라인 항목은 react-window 사용
- 윈도우 크기: 20-30개 항목

### 9.3 메모이제이션
- useMemo: 필터링된 타임라인 목록
- useCallback: 이벤트 핸들러

---

## 10. 향후 확장 계획

### v1.1 (향후)
- [ ] 실시간 진행 상태 (WebSocket/SSE)
- [ ] 처리 이력 저장 (localStorage)
- [ ] 다크 모드 지원

### v1.2 (향후)
- [ ] 북마크 기능
- [ ] 요약 결과 내보내기 (PDF, Markdown)
- [ ] 공유 링크 생성

---

## 11. 실행 명령어

```bash
# 프로젝트 생성
npm create vite@latest frontend -- --template react-ts
cd frontend

# 의존성 설치
npm install
npm install -D tailwindcss postcss autoprefixer
npm install @tanstack/react-query axios
npm install @headlessui/react @heroicons/react
npm install react-window  # 가상화 리스트

# Tailwind 초기화
npx tailwindcss init -p

# 개발 서버 실행
npm run dev
```

---

**문서 끝**
