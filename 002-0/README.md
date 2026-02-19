# YouTube Summary Agent

YouTube 영상을 자동으로 요약하고 Notion에 저장하는 LangChain 기반 Agent

## 🎯 프로젝트 개요

YouTube URL을 입력하면 자동으로:
1. 자막 추출 (자막 없으면 Whisper API로 음성→텍스트 변환)
2. 한국어 번역 및 정제
3. 타임라인별 전체 내용 생성
4. 주제별 섹션 분류 및 요약
5. Notion 페이지로 전송

## 🏗️ 기술 스택

### Backend
- **FastAPI** - REST API 서버
- **Python 3.12** - 백엔드 언어
- **LangChain** - Agent 및 Chain 오케스트레이션
- **OpenAI GPT-4o-mini** - 번역, 정제, 섹션 분류
- **OpenAI Whisper API** - 음성→텍스트 (자막 없을 때)

### 데이터 소스 & 통합
- **YouTube Transcript API** - 자막 추출
- **PyTube** - 오디오 다운로드 (Whisper 사용 시)
- **Notion API** - 결과 전송

### Frontend (TODO)
- **React** - 사용자 인터페이스
- **Axios** - Backend API 통신

## 📁 디렉토리 구조

```
C:\Users\asus\Documents\003. YouTubeSummaryAgent\
│
├── backend/                           # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py                   # FastAPI 앱
│   │   ├── config.py                 # 환경 설정
│   │   ├── models/
│   │   │   └── schemas.py            # 데이터 모델
│   │   ├── api/
│   │   │   └── routes.py             # API 엔드포인트
│   │   ├── services/
│   │   │   ├── youtube_service.py    # YouTube 처리
│   │   │   ├── langchain_agent.py    # LangChain Agent
│   │   │   ├── translation_chain.py  # 번역 Chain
│   │   │   └── sectioning_chain.py   # 섹션 분류 Chain
│   │   └── utils/
│   │       └── helpers.py            # 유틸리티 함수
│   ├── .venv/                        # Python 가상환경
│   ├── requirements.txt              # Python 패키지
│   └── .env                          # 환경 변수
│
├── shared/                            # 공통 리소스
│   └── prompts/
│       ├── translation_prompt.txt    # 번역 프롬프트
│       └── sectioning_prompt.txt     # 섹션 분류 프롬프트
│
└── README.md
```

## ⚙️ 설치 방법

### 1. Backend 설정

#### 1.1 Python 가상환경 생성 및 활성화

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux
```

#### 1.2 패키지 설치

```bash
pip install -r requirements.txt
```

#### 1.3 환경 변수 설정

`.env` 파일에 API 키를 설정합니다:

```env
OPENAI_API_KEY=your_openai_api_key_here

# Notion API (선택)
NOTION_API_KEY=
NOTION_DATABASE_ID=

# Server Config
BACKEND_HOST=localhost
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
```

### 2. Backend 서버 실행

```bash
cd backend
python -m uvicorn app.main:app --host localhost --port 8000 --reload
```

서버가 실행되면 다음 주소에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Node.js 설치 (Frontend 개발 시 필요)

#### Windows

1. [Node.js 공식 사이트](https://nodejs.org/) 방문
2. **LTS 버전** 다운로드 (권장: v20.x 이상)
3. 설치 프로그램 실행 (기본 설정 유지)
4. 설치 확인:

```bash
node --version
npm --version
```

#### Mac (Homebrew 사용)

```bash
brew install node
```

#### Linux (Ubuntu/Debian)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

## 🚀 API 사용법

### 1. 영상 정보 가져오기

```bash
curl -X POST "http://localhost:8000/api/video-info" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### 2. 자막 추출

```bash
curl -X POST "http://localhost:8000/api/extract-transcript" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### 3. 전체 처리 (자막 → 번역 → 섹션 분류)

```bash
curl -X POST "http://localhost:8000/api/process-video" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### 4. 빠른 처리 (테스트용 - 처음 50개 항목만)

```bash
curl -X POST "http://localhost:8000/api/process-video-quick" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

## 📊 API 응답 예시

### 성공 응답

```json
{
  "success": true,
  "video_info": {
    "video_id": "dQw4w9WgXcQ",
    "title": "영상 제목",
    "author": "채널명",
    "length": 212,
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  },
  "timeline": [
    {
      "time": "00:00",
      "text": "안녕하세요...",
      "start": 0.0,
      "duration": 2.5
    }
  ],
  "sections": [
    {
      "title": "인트로 및 주제 소개",
      "start_time": "00:00",
      "end_time": "02:30",
      "summary": "영상의 목적과 주요 주제를 소개합니다...",
      "key_points": ["주제 1", "주제 2"]
    }
  ],
  "full_summary": "전체 요약 내용...",
  "notion_url": null,
  "language": "ko",
  "source": "youtube",
  "message": "영상 처리 완료!"
}
```

## 📋 구현 현황

### ✅ 완료
- [x] Phase 1: 환경 설정
  - [x] 프로젝트 폴더 구조
  - [x] Python 가상환경
  - [x] API 키 설정
  - [x] FastAPI 기본 앱
- [x] Phase 2: YouTube 자막 추출
  - [x] YouTube Transcript API 연동
  - [x] 우선순위 기반 자막 추출 (한국어 > 영어)
  - [x] 타임라인 포맷팅
- [x] Phase 4: LangChain Agent
  - [x] Agent 기본 구조
  - [x] 파이프라인 오케스트레이션
- [x] Phase 5: 번역 Chain
  - [x] GPT-4o-mini 번역 Chain
  - [x] 청크 단위 번역 (긴 영상 대응)
- [x] Phase 6: 섹션 분류 Chain
  - [x] 주제별 섹션 자동 분류
  - [x] 섹션별 요약 생성

### 🔄 진행 중
- [ ] Phase 3: Whisper API 연동
  - 자막 없는 영상 처리
- [ ] Phase 7: Notion API 연동
  - Notion 페이지 자동 생성
- [ ] Phase 8: React Frontend
  - URL 입력 UI
  - 진행 상태 표시
  - 결과 표시 (타임라인 / 섹션)

### 📝 TODO
- [ ] Phase 9: 통합 테스트
- [ ] Phase 10: 배포 준비
- [ ] 에러 핸들링 강화
- [ ] 로깅 시스템 구축
- [ ] 캐싱 최적화

## 🐛 트러블슈팅

### 1. YouTube 자막 추출 실패

**문제**: `HTTP Error 400: Bad Request`

**해결방법**:
- YouTube URL이 올바른지 확인
- 영상이 공개 상태인지 확인
- 나이 제한이 없는 영상 사용
- 최신 YouTube 영상으로 테스트

### 2. OpenAI API 에러

**문제**: `AuthenticationError: Invalid API key`

**해결방법**:
- `.env` 파일의 API 키 확인
- API 키가 올바르게 설정되었는지 확인
- OpenAI 대시보드에서 API 키 유효성 확인

### 3. 패키지 설치 오류

**문제**: `ERROR: Could not find a version that satisfies the requirement`

**해결방법**:
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 패키지 재설치
pip install -r requirements.txt --no-cache-dir
```

## 💡 사용 팁

### 1. 긴 영상 처리
- 긴 영상(1시간 이상)은 처리 시간이 오래 걸립니다 (5-10분)
- `/api/process-video-quick` 엔드포인트로 빠르게 테스트

### 2. 번역 품질 개선
- `shared/prompts/translation_prompt.txt` 수정
- 프롬프트 엔지니어링으로 번역 스타일 조정

### 3. 섹션 분류 조정
- `shared/prompts/sectioning_prompt.txt` 수정
- 섹션 개수, 요약 길이 등 조정 가능

## 🔐 보안 주의사항

- `.env` 파일을 절대 Git에 커밋하지 마세요
- API 키를 코드에 하드코딩하지 마세요
- 프로덕션 환경에서는 HTTPS 사용

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 로그 파일 확인 (콘솔 출력)
2. FastAPI Swagger UI에서 API 테스트: http://localhost:8000/docs
3. 환경 변수 설정 확인

## 📄 라이선스

MIT License

## 👤 개발자

프로젝트 관리자: 정지우

---

**현재 버전**: v1.0.0 (Backend MVP 완성)
**마지막 업데이트**: 2025-11-26
