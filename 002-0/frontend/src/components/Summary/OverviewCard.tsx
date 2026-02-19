interface OverviewCardProps {
  overview: string;
}

export default function OverviewCard({ overview }: OverviewCardProps) {
  if (!overview) {
    return (
      <div className="text-gray-500 text-center py-8">
        개요가 없습니다.
      </div>
    );
  }

  return (
    <div className="prose prose-blue max-w-none">
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">영상 개요</h3>
          <p className="text-sm text-gray-500">AI가 분석한 영상의 전체적인 요약입니다.</p>
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
          {overview}
        </p>
      </div>
    </div>
  );
}
