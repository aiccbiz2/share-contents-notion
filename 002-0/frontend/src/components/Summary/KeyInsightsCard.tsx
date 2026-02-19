import type { KeyInsight } from '../../types';

interface KeyInsightsCardProps {
  insights: KeyInsight[];
}

export default function KeyInsightsCard({ insights }: KeyInsightsCardProps) {
  // 안전한 데이터 처리 - 배열이 아니거나 undefined인 경우 빈 배열로 처리
  const safeInsights = Array.isArray(insights) ? insights : [];

  if (safeInsights.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        핵심 인사이트가 없습니다.
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-shrink-0 w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
          <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">핵심 인사이트</h3>
          <p className="text-sm text-gray-500">영상에서 도출할 수 있는 주요 통찰입니다.</p>
        </div>
      </div>

      <div className="space-y-3">
        {safeInsights.map((item, index) => {
          // 각 아이템도 안전하게 처리
          const insight = item?.insight || '';
          const importance = item?.importance || '';

          return (
            <div
              key={index}
              className="bg-gradient-to-br from-amber-50 to-white border border-amber-100 rounded-lg p-4"
            >
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-amber-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
                  {index + 1}
                </span>
                <div className="flex-1">
                  <p className="font-medium text-gray-900 mb-1">
                    {insight}
                  </p>
                  {importance && (
                    <p className="text-sm text-gray-600">
                      <span className="text-amber-600 font-medium">중요성:</span> {importance}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
