import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, ChevronDown, ChevronUp, ChevronRight, CheckCircle, AlertCircle, Archive } from 'lucide-react';
import { getSummaries, getSummaryDetail, type SummaryItem, type SummaryDetail } from '../../services/api';

interface HistorySectionProps {
  onSelectSummary?: (summary: SummaryDetail) => void;
}

// 시간 포맷팅 헬퍼
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return '오늘';
  } else if (diffDays === 1) {
    return '어제';
  } else if (diffDays < 7) {
    return `${diffDays}일 전`;
  } else {
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  }
}

function formatProcessingTime(ms: number | null): string {
  if (!ms) return '';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) {
    return `${seconds}초`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}분 ${remainingSeconds}초`;
}

export default function HistorySection({ onSelectSummary }: HistorySectionProps) {
  const [summaries, setSummaries] = useState<SummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState<number | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchSummaries();
    }
  }, [isOpen]);

  const fetchSummaries = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getSummaries(30, 50);
      if (response.success) {
        setSummaries(response.summaries);
      } else {
        setError(response.error || '요약 내역을 불러올 수 없습니다.');
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { status?: number } };
      if (axiosError?.response?.status === 404) {
        setError('서버를 재시작해주세요. (백엔드 서버가 최신 버전이 아닙니다)');
      } else {
        setError('요약 내역 로드 실패');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectItem = async (item: SummaryItem) => {
    if (!onSelectSummary) return;

    try {
      setLoadingDetail(item.id);
      const response = await getSummaryDetail(item.id);
      if (response.success && response.summary) {
        onSelectSummary(response.summary);
        setIsOpen(false);
      }
    } catch (err) {
      console.error('상세 조회 실패:', err);
    } finally {
      setLoadingDetail(null);
    }
  };

  return (
    <div className="mb-6">
      {/* 토글 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl p-4 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Clock className="w-5 h-5 text-pink-500" />
          <span className="font-medium text-zinc-100">요약 내역</span>
          {summaries.length > 0 && (
            <span className="text-xs bg-pink-500/20 text-pink-400 px-2 py-0.5 rounded-full">
              {summaries.length}개
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-zinc-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-zinc-400" />
        )}
      </button>

      {/* 내역 목록 */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl overflow-hidden"
          >
            {loading ? (
              <div className="p-8 flex items-center justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-pink-500"></div>
                <span className="ml-3 text-zinc-500">불러오는 중...</span>
              </div>
            ) : error ? (
              <div className="p-6 text-center text-zinc-500">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 text-zinc-600" />
                <p>{error}</p>
              </div>
            ) : summaries.length === 0 ? (
              <div className="p-8 text-center text-zinc-500">
                <Archive className="w-12 h-12 mx-auto mb-3 text-zinc-700" />
                <p className="text-sm">아직 요약한 영상이 없습니다.</p>
                <p className="text-xs text-zinc-600 mt-1">영상을 요약하면 여기에 기록됩니다.</p>
              </div>
            ) : (
              <div className="max-h-[400px] overflow-y-auto divide-y divide-zinc-800">
                {summaries.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleSelectItem(item)}
                    disabled={loadingDetail === item.id}
                    className="w-full p-4 flex gap-4 hover:bg-zinc-800/50 transition-colors text-left disabled:opacity-50"
                  >
                    {/* 썸네일 */}
                    <div className="flex-shrink-0 w-24 aspect-video rounded-lg overflow-hidden bg-zinc-800">
                      <img
                        src={item.thumbnail_url}
                        alt={item.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.src = `https://img.youtube.com/vi/${item.video_id}/default.jpg`;
                        }}
                      />
                    </div>

                    {/* 정보 */}
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-zinc-100 line-clamp-2">{item.title}</h4>
                      <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                        <span>{item.author}</span>
                        <span className="text-zinc-700">|</span>
                        <span>{formatDuration(item.duration)}</span>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-zinc-600">
                        <span>{formatDate(item.created_at)}</span>
                        {item.processing_time_ms && (
                          <>
                            <span className="text-zinc-700">|</span>
                            <span>처리: {formatProcessingTime(item.processing_time_ms)}</span>
                          </>
                        )}
                        {item.notion_url && (
                          <span className="text-pink-400 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Notion
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 로딩 또는 화살표 */}
                    <div className="flex-shrink-0 self-center">
                      {loadingDetail === item.id ? (
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-pink-500"></div>
                      ) : (
                        <ChevronRight className="w-5 h-5 text-zinc-600" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* 하단 정보 */}
            {summaries.length > 0 && (
              <div className="px-4 py-3 bg-zinc-800/30 border-t border-zinc-800 text-xs text-zinc-600 text-center">
                최근 30일간의 요약 내역 (최대 50개)
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
