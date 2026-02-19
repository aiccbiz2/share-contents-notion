import { useState, useEffect } from 'react';

interface LoadingStateProps {
  message?: string;
  startTime?: number;
}

// 밀리초를 hh:mm:ss 형식으로 변환
function formatElapsedTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

export default function LoadingState({ message = '처리 중...', startTime }: LoadingStateProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startTime) return;

    const interval = setInterval(() => {
      setElapsed(Date.now() - startTime);
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 my-6">
      <div className="flex flex-col items-center justify-center space-y-4">
        {/* 로딩 스피너 */}
        <div className="relative">
          <div className="w-16 h-16 border-4 border-gray-200 rounded-full"></div>
          <div className="absolute top-0 left-0 w-16 h-16 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
        </div>

        {/* 로딩 메시지 */}
        <div className="text-center">
          <p className="text-lg font-medium text-gray-700">{message}</p>
          <p className="text-sm text-gray-500 mt-2">
            영상 길이에 따라 수 분이 소요될 수 있습니다.
          </p>
        </div>

        {/* 경과 시간 표시 */}
        {startTime && (
          <div className="flex items-center gap-2 text-blue-600 font-mono text-xl">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{formatElapsedTime(elapsed)}</span>
          </div>
        )}

        {/* 진행 단계 표시 */}
        <div className="w-full max-w-md mt-6">
          <div className="flex justify-between text-xs text-gray-500 mb-2">
            <span>자막 추출</span>
            <span>AI 분석</span>
            <span>Notion 저장</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full animate-pulse w-1/2"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
