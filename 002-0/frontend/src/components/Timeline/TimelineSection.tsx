import { useState, useMemo } from 'react';
import type { TimelineItem } from '../../types';

interface TimelineSectionProps {
  timeline: TimelineItem[];
  videoUrl: string;
}

// 시간 문자열을 초로 변환
function timeToSeconds(time: string): number {
  const parts = time.split(':').map(Number);
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return parts[0] * 60 + parts[1];
}

// YouTube URL에 타임스탬프 추가
function getTimestampUrl(videoUrl: string, time: string): string {
  const seconds = timeToSeconds(time);
  const url = new URL(videoUrl);
  url.searchParams.set('t', seconds.toString());
  return url.toString();
}

export default function TimelineSection({ timeline, videoUrl }: TimelineSectionProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  // 검색 필터링
  const filteredTimeline = useMemo(() => {
    if (!searchQuery.trim()) return timeline;
    const query = searchQuery.toLowerCase();
    return timeline.filter((item) =>
      item.text.toLowerCase().includes(query) ||
      item.time.includes(query)
    );
  }, [timeline, searchQuery]);

  // 표시할 아이템 (펼치기 전에는 20개만)
  const displayedItems = isExpanded ? filteredTimeline : filteredTimeline.slice(0, 20);
  const hasMore = filteredTimeline.length > 20;

  if (!timeline || timeline.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* 헤더 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">자막 타임라인</h3>
              <p className="text-sm text-gray-500">{timeline.length}개의 자막</p>
            </div>
          </div>
        </div>

        {/* 검색 입력 */}
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="자막 내용 검색..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
          />
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}
        </div>

        {/* 검색 결과 수 */}
        {searchQuery && (
          <p className="mt-2 text-xs text-gray-500">
            {filteredTimeline.length}개의 검색 결과
          </p>
        )}
      </div>

      {/* 타임라인 리스트 */}
      <div className="max-h-96 overflow-y-auto">
        {displayedItems.length > 0 ? (
          <ul className="divide-y divide-gray-100">
            {displayedItems.map((item, index) => (
              <li key={index} className="hover:bg-gray-50 transition-colors">
                <a
                  href={getTimestampUrl(videoUrl, item.time)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 p-3"
                >
                  <span className="flex-shrink-0 px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-mono font-medium">
                    {item.time}
                  </span>
                  <span className="text-sm text-gray-700 leading-relaxed">
                    {searchQuery ? (
                      highlightText(item.text, searchQuery)
                    ) : (
                      item.text
                    )}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-8 text-center text-gray-500">
            검색 결과가 없습니다.
          </div>
        )}
      </div>

      {/* 더 보기 버튼 */}
      {hasMore && !searchQuery && (
        <div className="p-3 border-t border-gray-100">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full py-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            {isExpanded ? '접기' : `${filteredTimeline.length - 20}개 더 보기`}
          </button>
        </div>
      )}
    </div>
  );
}

// 검색어 하이라이트
function highlightText(text: string, query: string) {
  const parts = text.split(new RegExp(`(${query})`, 'gi'));
  return parts.map((part, index) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={index} className="bg-yellow-200 text-yellow-900 rounded px-0.5">
        {part}
      </mark>
    ) : (
      part
    )
  );
}
