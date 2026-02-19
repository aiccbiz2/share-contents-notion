interface VideoInputProps {
  url: string;
  onUrlChange: (url: string) => void;
  onPreview: () => void;
  onProcess: () => void;
  onReset: () => void;
  isLoading: boolean;
  hasResult: boolean;
}

export default function VideoInput({
  url,
  onUrlChange,
  onPreview,
  onProcess,
  onReset,
  isLoading,
  hasResult,
}: VideoInputProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onProcess();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onProcess();
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          {/* URL 입력 필드 */}
          <div>
            <label
              htmlFor="youtube-url"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              YouTube URL
            </label>
            <div className="relative">
              <input
                id="youtube-url"
                type="text"
                value={url}
                onChange={(e) => onUrlChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="https://www.youtube.com/watch?v=... 또는 https://youtu.be/..."
                disabled={isLoading}
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
              />
              {url && !isLoading && (
                <button
                  type="button"
                  onClick={() => onUrlChange('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* 버튼 그룹 */}
          <div className="flex flex-wrap gap-3">
            {/* 미리보기 버튼 */}
            <button
              type="button"
              onClick={onPreview}
              disabled={isLoading || !url.trim()}
              className="px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                미리보기
              </span>
            </button>

            {/* 요약 시작 버튼 */}
            <button
              type="submit"
              disabled={isLoading || !url.trim()}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex-1 sm:flex-none"
            >
              <span className="flex items-center justify-center gap-2">
                {isLoading ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    처리 중...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    요약 시작
                  </>
                )}
              </span>
            </button>

            {/* 초기화 버튼 (결과가 있을 때만) */}
            {hasResult && (
              <button
                type="button"
                onClick={onReset}
                disabled={isLoading}
                className="px-4 py-2.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  새로 시작
                </span>
              </button>
            )}
          </div>
        </div>
      </form>

      {/* 도움말 텍스트 */}
      <p className="mt-4 text-xs text-gray-500">
        YouTube 영상 URL을 입력하고 요약을 시작하세요. 영상 길이에 따라 처리 시간이 달라집니다.
      </p>
    </div>
  );
}
