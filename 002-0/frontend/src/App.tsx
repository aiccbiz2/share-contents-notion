import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Sparkles, Clock, CheckCircle, AlertCircle, X, ExternalLink, Copy, Search, FileText, Lightbulb, BookOpen, ChevronDown, ChevronUp, ArrowUp } from 'lucide-react';
import { processVideo, getVideoInfo, type SummaryDetail } from './services/api';
import type { ProcessVideoResponse, VideoInfo, ProcessingStatus, StructuredSummary } from './types';

// Components (기존 컴포넌트 대신 인라인으로 다크테마 적용)
import RelatedVideosSection from './components/RelatedVideos/RelatedVideosSection';
import HistorySection from './components/History/HistorySection';

// 로딩 단계 정의
interface LoadingStep {
  id: string;
  label: string;
  percentage: number;
}

const LOADING_STEPS: LoadingStep[] = [
  { id: 'start', label: '시작', percentage: 0 },
  { id: 'extract', label: '자막 추출', percentage: 25 },
  { id: 'analyze', label: 'AI 분석', percentage: 50 },
  { id: 'summarize', label: '요약 생성', percentage: 75 },
  { id: 'complete', label: '완료', percentage: 100 },
];

// 밀리초를 hh:mm:ss 형식으로 변환
function formatElapsedTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}시간 ${minutes}분 ${seconds}초`;
  }
  if (minutes > 0) {
    return `${minutes}분 ${seconds}초`;
  }
  return `${seconds}초`;
}

// 초를 mm:ss 형식으로 변환
function formatDuration(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function App() {
  const [url, setUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [result, setResult] = useState<ProcessVideoResponse | null>(null);
  const [status, setStatus] = useState<ProcessingStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'timeline'>('summary');
  const [timelineSearch, setTimelineSearch] = useState('');
  const [copied, setCopied] = useState(false);
  const [currentElapsed, setCurrentElapsed] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [expandedSections, setExpandedSections] = useState<Set<number> | 'all'>('all');

  // 실시간 경과 시간 업데이트 및 단계 진행
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (status === 'loading' && startTime) {
      interval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setCurrentElapsed(elapsed);

        // 시간 기반 단계 진행 (대략적인 시뮬레이션)
        // 0: 시작, 1: 자막 추출, 2: AI 분석, 3: 요약 생성, 4: 완료
        if (elapsed < 2) {
          setCurrentStep(0); // 시작
        } else if (elapsed < 7) {
          setCurrentStep(1); // 자막 추출
        } else if (elapsed < 17) {
          setCurrentStep(2); // AI 분석
        } else {
          setCurrentStep(3); // 요약 생성
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [status, startTime]);

  // 비디오 정보 미리보기
  const previewMutation = useMutation({
    mutationFn: getVideoInfo,
    onSuccess: (data) => {
      if (data.success && data.video_info) {
        setVideoInfo(data.video_info);
        setError(null);
      } else {
        setError(data.error || '영상 정보를 가져올 수 없습니다.');
      }
    },
    onError: (err: Error) => {
      setError(err.message || '영상 정보 로드 실패');
    },
  });

  // 전체 처리
  const processMutation = useMutation({
    mutationFn: processVideo,
    onMutate: () => {
      setStatus('loading');
      setError(null);
      setStartTime(Date.now());
      setElapsedTime(null);
      setCurrentElapsed(0);
    },
    onSuccess: (data) => {
      const endTime = Date.now();
      if (startTime) {
        setElapsedTime(endTime - startTime);
      }
      setStartTime(null);
      if (data.success) {
        setResult(data);
        setStatus('success');
        setVideoInfo(data.video_info);
      } else {
        setError(data.error || '처리 중 오류가 발생했습니다.');
        setStatus('error');
      }
    },
    onError: (err: Error) => {
      const endTime = Date.now();
      if (startTime) {
        setElapsedTime(endTime - startTime);
      }
      setStartTime(null);
      setError(err.message || '요청 처리 실패');
      setStatus('error');
    },
  });

  const handlePreview = () => {
    if (!url.trim()) {
      setError('YouTube URL을 입력해주세요.');
      return;
    }
    previewMutation.mutate(url);
  };

  const handleProcess = () => {
    if (!url.trim()) {
      setError('YouTube URL을 입력해주세요.');
      return;
    }
    processMutation.mutate({ url });
  };

  const handleReset = () => {
    setUrl('');
    setVideoInfo(null);
    setResult(null);
    setStatus('idle');
    setError(null);
    setStartTime(null);
    setElapsedTime(null);
    setCurrentElapsed(0);
    setCurrentStep(0);
    setExpandedSections('all');
  };

  // 섹션 토글 함수
  const toggleSection = (index: number, totalSections: number) => {
    setExpandedSections(prev => {
      // 'all' 상태에서 하나를 닫을 때: 모든 인덱스를 Set에 넣고 해당 인덱스만 제거
      if (prev === 'all') {
        const newSet = new Set<number>();
        for (let i = 0; i < totalSections; i++) {
          if (i !== index) newSet.add(i);
        }
        return newSet;
      }

      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  // 히스토리에서 요약 선택 시
  const handleSelectFromHistory = (summary: SummaryDetail) => {
    const historyResult: ProcessVideoResponse = {
      success: true,
      video_info: {
        video_id: summary.video_id,
        title: summary.title,
        author: summary.author,
        length: summary.duration,
        url: summary.video_url,
      },
      timeline: summary.timeline,
      structured_summary: summary.structured_summary as ProcessVideoResponse['structured_summary'],
      notion_url: summary.notion_url || undefined,
    };

    setUrl(summary.video_url);
    setResult(historyResult);
    setStatus('success');
    setVideoInfo(historyResult.video_info);
    setElapsedTime(summary.processing_time_ms);
    setError(null);
  };

  const handleCopyUrl = async (notionUrl: string) => {
    await navigator.clipboard.writeText(notionUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // 타임라인 필터링
  const filteredTimeline = result?.timeline?.filter(item =>
    item.text.toLowerCase().includes(timelineSearch.toLowerCase())
  ) || [];

  const isLoading = previewMutation.isPending || status === 'loading';

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-zinc-100 relative overflow-hidden">
      {/* Floating Glow Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-pink-500/20 rounded-full blur-[120px] animate-pulse-glow" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-rose-500/20 rounded-full blur-[120px] animate-pulse-glow" />
      </div>

      {/* Header */}
      <header className="relative z-10 py-8 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-center gap-3 mb-2"
          >
            <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-rose-500 rounded-xl flex items-center justify-center">
              <Play className="w-5 h-5 text-white" fill="white" />
            </div>
            <h1 className="text-2xl font-bold">
              <span className="bg-gradient-to-r from-pink-500 to-rose-500 bg-clip-text text-transparent">
                YouTube Summary
              </span>
            </h1>
          </motion.div>
          <p className="text-zinc-500 text-sm">&nbsp;</p>
        </div>
      </header>

      <main className="relative z-10 max-w-4xl mx-auto px-4 pb-12">
        {/* URL Input Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6">
            <p className="text-white text-center text-sm mb-4">
              YouTube 영상 URL을 입력하면 영상의 주요 내용을 AI가 요약해줍니다.
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 relative group">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="YouTube URL을 입력하세요"
                  disabled={isLoading}
                  className="w-full bg-zinc-800/50 border border-zinc-700 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-pink-500/50 focus:ring-2 focus:ring-pink-500/20 transition-all disabled:opacity-50"
                  onKeyDown={(e) => e.key === 'Enter' && handleProcess()}
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handlePreview}
                  disabled={isLoading || !url.trim()}
                  className="px-4 py-3 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-xl text-zinc-300 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Clock className="w-4 h-4" />
                  <span className="hidden sm:inline">미리보기</span>
                </button>
                <button
                  onClick={handleProcess}
                  disabled={isLoading || !url.trim()}
                  className="px-6 py-3 bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 rounded-xl text-white font-medium transition-all disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-pink-500/25"
                >
                  <Sparkles className="w-4 h-4" />
                  요약 시작
                </button>
                {result && (
                  <button
                    onClick={handleReset}
                    className="px-4 py-3 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-xl text-zinc-300 font-medium transition-all flex items-center gap-2"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* History Section */}
        <HistorySection onSelectSummary={handleSelectFromHistory} />

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3"
            >
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <span className="text-red-400 flex-1">{error}</span>
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Video Info Preview (before processing) */}
        <AnimatePresence>
          {videoInfo && !result && status !== 'loading' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mb-6 bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6"
            >
              <div className="flex flex-col sm:flex-row gap-4">
                <img
                  src={`https://img.youtube.com/vi/${videoInfo.video_id}/mqdefault.jpg`}
                  alt={videoInfo.title}
                  className="w-full sm:w-48 rounded-xl object-cover aspect-video"
                />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-zinc-100 mb-2 line-clamp-2">
                    {videoInfo.title}
                  </h3>
                  <p className="text-zinc-400 text-sm mb-2">{videoInfo.author}</p>
                  <p className="text-zinc-500 text-sm flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    {formatDuration(videoInfo.length)}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading State - 단계별 프로그레스 */}
        <AnimatePresence>
          {status === 'loading' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="mb-6 bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-8"
            >
              <div className="text-center mb-6">
                <div className="w-16 h-16 mx-auto mb-4 relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-pink-500 to-rose-500 rounded-full animate-ping opacity-25" />
                  <div className="relative w-full h-full bg-gradient-to-r from-pink-500 to-rose-500 rounded-full flex items-center justify-center">
                    <Sparkles className="w-8 h-8 text-white animate-pulse" />
                  </div>
                </div>
                <h3 className="text-lg font-semibold text-zinc-100 mb-1">
                  {LOADING_STEPS[currentStep].label} 중...
                </h3>
                <p className="text-zinc-500 text-sm">
                  AI가 영상 내용을 요약하는 중입니다
                </p>
              </div>

              {/* 단계별 스텝 인디케이터 (점과 선) */}
              <div className="mb-8">
                <div className="flex items-center justify-between relative">
                  {/* 배경 선 */}
                  <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-zinc-700 -translate-y-1/2" />
                  {/* 진행 선 */}
                  <motion.div
                    className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-pink-500 to-rose-500 -translate-y-1/2"
                    initial={{ width: '0%' }}
                    animate={{ width: `${(currentStep / (LOADING_STEPS.length - 1)) * 100}%` }}
                    transition={{ duration: 0.5 }}
                  />

                  {/* 각 단계 점 */}
                  {LOADING_STEPS.map((step, index) => (
                    <div key={step.id} className="relative z-10 flex flex-col items-center">
                      {/* 점 */}
                      <div className={`w-4 h-4 rounded-full border-2 transition-all ${
                        index < currentStep
                          ? 'bg-gradient-to-r from-pink-500 to-rose-500 border-pink-500'
                          : index === currentStep
                          ? 'bg-gradient-to-r from-pink-500 to-rose-500 border-pink-500 animate-pulse ring-4 ring-pink-500/30'
                          : 'bg-zinc-800 border-zinc-600'
                      }`}>
                        {index < currentStep && (
                          <CheckCircle className="w-3 h-3 text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                        )}
                      </div>
                      {/* 라벨 */}
                      <span className={`absolute top-6 text-xs whitespace-nowrap transition-colors ${
                        index <= currentStep ? 'text-zinc-100' : 'text-zinc-500'
                      }`}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 퍼센트 및 경과 시간 */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-zinc-400">
                  <Clock className="w-4 h-4" />
                  <span className="font-mono">{formatElapsedTime(currentElapsed * 1000)}</span>
                </div>
                <div className="text-pink-400 font-semibold">
                  {LOADING_STEPS[currentStep].percentage}%
                </div>
              </div>

              {/* 전체 프로그레스 바 */}
              <div className="mt-3 w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-pink-500 to-rose-500"
                  initial={{ width: '0%' }}
                  animate={{ width: `${LOADING_STEPS[currentStep].percentage}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {result && status === 'success' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Success Banner */}
              {elapsedTime && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-center gap-3"
                >
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <span className="text-emerald-400">
                    요약 완료! 총 소요 시간: <span className="font-semibold">{formatElapsedTime(elapsedTime)}</span>
                  </span>
                </motion.div>
              )}

              {/* Video Info Card */}
              <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6">
                <div className="flex flex-col sm:flex-row gap-4">
                  <img
                    src={`https://img.youtube.com/vi/${result.video_info.video_id}/mqdefault.jpg`}
                    alt={result.video_info.title}
                    className="w-full sm:w-48 rounded-xl object-cover aspect-video"
                  />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-zinc-100 mb-2 line-clamp-2">
                      {result.video_info.title}
                    </h3>
                    <p className="text-zinc-400 text-sm mb-2">{result.video_info.author}</p>
                    <p className="text-zinc-500 text-sm flex items-center gap-2 mb-4">
                      <Clock className="w-4 h-4" />
                      {formatDuration(result.video_info.length)}
                    </p>
                    {result.notion_url && (
                      <div className="flex gap-2">
                        <a
                          href={result.notion_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-zinc-300 text-sm transition-colors"
                        >
                          <ExternalLink className="w-4 h-4" />
                          Notion에서 보기
                        </a>
                        <button
                          onClick={() => handleCopyUrl(result.notion_url!)}
                          className={`inline-flex items-center gap-2 px-4 py-2 border rounded-lg text-sm transition-colors ${
                            copied
                              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                              : 'bg-zinc-800 hover:bg-zinc-700 border-zinc-700 text-zinc-300'
                          }`}
                        >
                          <Copy className="w-4 h-4" />
                          {copied ? '복사됨!' : 'URL 복사'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Tab Navigation */}
              <div className="flex gap-2 p-1 bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl">
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all ${
                    activeTab === 'summary'
                      ? 'bg-gradient-to-r from-pink-500 to-rose-500 text-white shadow-lg'
                      : 'text-zinc-400 hover:text-zinc-300'
                  }`}
                >
                  요약
                </button>
                <button
                  onClick={() => setActiveTab('timeline')}
                  className={`flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all ${
                    activeTab === 'timeline'
                      ? 'bg-gradient-to-r from-pink-500 to-rose-500 text-white shadow-lg'
                      : 'text-zinc-400 hover:text-zinc-300'
                  }`}
                >
                  타임라인
                </button>
              </div>

              {/* Tab Content */}
              <AnimatePresence mode="wait">
                {activeTab === 'summary' ? (
                  <motion.div
                    key="summary"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6 space-y-6"
                  >
                    {/* Overview - 개요 */}
                    {result.structured_summary?.overview && (
                      <div>
                        <h4 className="text-lg font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                          <FileText className="w-5 h-5 text-pink-500" />
                          영상 개요
                        </h4>
                        <p className="text-zinc-300 leading-relaxed">
                          {result.structured_summary.overview}
                        </p>
                      </div>
                    )}

                    {/* Sections - 섹션별 내용 (신규 형식) */}
                    {result.structured_summary?.sections && result.structured_summary.sections.length > 0 && (
                      <div>
                        <h4 className="text-lg font-semibold text-zinc-100 mb-4 flex items-center gap-2">
                          <BookOpen className="w-5 h-5 text-rose-500" />
                          주요 내용 요약
                        </h4>
                        <div className="space-y-3">
                          {result.structured_summary.sections.map((section, sectionIndex) => (
                            <div key={sectionIndex} className="border border-zinc-700/50 rounded-xl overflow-hidden">
                              {/* Section Header - 접이식 */}
                              <button
                                onClick={() => toggleSection(sectionIndex, result.structured_summary.sections.length)}
                                className="w-full bg-zinc-800/50 hover:bg-zinc-800/70 p-4 flex items-center justify-between transition-colors"
                              >
                                <span className="font-medium text-zinc-100 flex items-center gap-2">
                                  <span className="text-pink-400">{sectionIndex + 1}.</span>
                                  {section.section_title}
                                </span>
                                {expandedSections === 'all' || expandedSections.has(sectionIndex) ? (
                                  <ChevronUp className="w-5 h-5 text-zinc-400" />
                                ) : (
                                  <ChevronDown className="w-5 h-5 text-zinc-400" />
                                )}
                              </button>

                              {/* Section Content */}
                              <AnimatePresence>
                                {(expandedSections === 'all' || expandedSections.has(sectionIndex)) && (
                                  <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-hidden"
                                  >
                                    <div className="p-4 space-y-3 bg-zinc-900/30">
                                      {section.subtopics && section.subtopics.length > 0 ? (
                                        section.subtopics.map((subtopic, subIndex) => (
                                          <div key={subIndex} className="bg-zinc-800/30 rounded-lg p-3 border-l-2 border-pink-500/50">
                                            {(subtopic.title || subtopic.subtopic_title) && (
                                              <h6 className="font-medium text-zinc-200 mb-1 text-sm">
                                                {subtopic.title || subtopic.subtopic_title}
                                              </h6>
                                            )}
                                            <p className="text-zinc-400 text-sm leading-relaxed">
                                              {subtopic.content || subtopic.summary || ''}
                                            </p>
                                            {subtopic.key_points && subtopic.key_points.length > 0 && (
                                              <ul className="mt-2 space-y-1">
                                                {subtopic.key_points.map((point, pointIndex) => (
                                                  <li key={pointIndex} className="text-zinc-400 text-xs flex items-start gap-2">
                                                    <span className="text-pink-400 mt-0.5">•</span>
                                                    <span>{point}</span>
                                                  </li>
                                                ))}
                                              </ul>
                                            )}
                                          </div>
                                        ))
                                      ) : (
                                        <p className="text-zinc-500 text-sm">세부 내용이 없습니다.</p>
                                      )}
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Main Topics - 레거시 형식 (sections가 없을 때) */}
                    {(!result.structured_summary?.sections || result.structured_summary.sections.length === 0) &&
                     (result.structured_summary as Record<string, unknown>)?.main_topics &&
                     Array.isArray((result.structured_summary as Record<string, unknown>).main_topics) &&
                     ((result.structured_summary as Record<string, unknown>).main_topics as Array<{title?: string; content?: string}>).length > 0 && (
                      <div>
                        <h4 className="text-lg font-semibold text-zinc-100 mb-4 flex items-center gap-2">
                          <BookOpen className="w-5 h-5 text-rose-500" />
                          주요 내용 요약
                        </h4>
                        <div className="space-y-3">
                          {((result.structured_summary as Record<string, unknown>).main_topics as Array<{title?: string; content?: string}>).map((topic, topicIndex) => (
                            <div key={topicIndex} className="border border-zinc-700/50 rounded-xl overflow-hidden">
                              {/* Topic Header - 접이식 */}
                              <button
                                onClick={() => toggleSection(topicIndex, ((result.structured_summary as Record<string, unknown>).main_topics as Array<unknown>).length)}
                                className="w-full bg-zinc-800/50 hover:bg-zinc-800/70 p-4 flex items-center justify-between transition-colors"
                              >
                                <span className="font-medium text-zinc-100 flex items-center gap-2">
                                  <span className="text-pink-400">{topicIndex + 1}.</span>
                                  {topic.title}
                                </span>
                                {expandedSections === 'all' || expandedSections.has(topicIndex) ? (
                                  <ChevronUp className="w-5 h-5 text-zinc-400" />
                                ) : (
                                  <ChevronDown className="w-5 h-5 text-zinc-400" />
                                )}
                              </button>

                              {/* Topic Content */}
                              <AnimatePresence>
                                {(expandedSections === 'all' || expandedSections.has(topicIndex)) && (
                                  <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-hidden"
                                  >
                                    <div className="p-4 bg-zinc-900/30">
                                      <p className="text-zinc-400 text-sm leading-relaxed">
                                        {topic.content}
                                      </p>
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Key Terms - 핵심 용어 */}
                    {result.structured_summary?.key_terms && result.structured_summary.key_terms.length > 0 && (
                      <div>
                        <h4 className="text-lg font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                          <Lightbulb className="w-5 h-5 text-amber-500" />
                          핵심 용어
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {result.structured_summary.key_terms.map((term, index) => (
                            <div key={index} className="bg-zinc-800/50 rounded-xl p-3 border border-zinc-700/50">
                              <span className="font-medium text-pink-400 text-sm">{term.term}</span>
                              <p className="text-zinc-400 text-xs mt-1 leading-relaxed">{term.definition}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Key Insights - 핵심 인사이트 */}
                    {result.structured_summary?.key_insights && (
                      <div>
                        <h4 className="text-lg font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                          <Sparkles className="w-5 h-5 text-emerald-500" />
                          핵심 인사이트
                        </h4>
                        {typeof result.structured_summary.key_insights === 'string' ? (
                          <p className="text-zinc-300 leading-relaxed">
                            {result.structured_summary.key_insights}
                          </p>
                        ) : (
                          <ul className="space-y-3">
                            {result.structured_summary.key_insights.map((insight, index) => (
                              <li key={index} className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700/50">
                                <p className="text-zinc-200 text-sm">{insight.insight}</p>
                                {insight.importance && (
                                  <p className="text-zinc-500 text-xs mt-2 flex items-center gap-1">
                                    <span className="text-amber-400">중요도:</span> {insight.importance}
                                  </p>
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    {/* 데이터가 하나도 없을 때 */}
                    {!result.structured_summary?.overview &&
                     !result.structured_summary?.sections?.length &&
                     !result.structured_summary?.key_terms?.length &&
                     !result.structured_summary?.key_insights && (
                      <div className="text-center py-8">
                        <AlertCircle className="w-12 h-12 text-zinc-600 mx-auto mb-3" />
                        <p className="text-zinc-500">요약 데이터를 불러올 수 없습니다.</p>
                        <p className="text-zinc-600 text-sm mt-1">영상을 다시 요약해 주세요.</p>
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div
                    key="timeline"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6"
                  >
                    {/* Search */}
                    <div className="relative mb-4">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                      <input
                        type="text"
                        value={timelineSearch}
                        onChange={(e) => setTimelineSearch(e.target.value)}
                        placeholder="타임라인 검색..."
                        className="w-full bg-zinc-800/50 border border-zinc-700 rounded-xl pl-10 pr-4 py-2.5 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-pink-500/50 focus:ring-2 focus:ring-pink-500/20 transition-all text-sm"
                      />
                    </div>

                    {/* Timeline List */}
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                      {filteredTimeline.map((item, index) => (
                        <a
                          key={index}
                          href={`${result.video_info.url}&t=${item.start}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex gap-3 p-3 bg-zinc-800/30 hover:bg-zinc-800/60 rounded-xl transition-colors group"
                        >
                          <span className="text-pink-400 font-mono text-sm whitespace-nowrap group-hover:text-pink-300">
                            {item.time}
                          </span>
                          <span className="text-zinc-300 text-sm line-clamp-2 group-hover:text-zinc-100">
                            {item.text}
                          </span>
                        </a>
                      ))}
                      {filteredTimeline.length === 0 && (
                        <p className="text-zinc-500 text-center py-8">
                          {timelineSearch ? '검색 결과가 없습니다.' : '타임라인이 없습니다.'}
                        </p>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Related Videos */}
              <RelatedVideosSection videoUrl={result.video_info.url} />

              {/* Top Button */}
              <div className="flex justify-end mt-4">
                <button
                  onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                  className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-xl text-zinc-300 text-sm transition-all hover:border-pink-500/50"
                >
                  <ArrowUp className="w-4 h-4" />
                  Top
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-6 text-center text-zinc-600 text-sm">
        <p>YouTube Summary Agent - AI 기반 영상 요약 도구</p>
      </footer>
    </div>
  );
}

export default App;
