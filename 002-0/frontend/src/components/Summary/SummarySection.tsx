import { useState } from 'react';
import type { StructuredSummary } from '../../types';
import OverviewCard from './OverviewCard';
import SectionCard from './SectionCard';
import KeyTermsCard from './KeyTermsCard';
import KeyInsightsCard from './KeyInsightsCard';
import ErrorBoundary from '../common/ErrorBoundary';

interface SummarySectionProps {
  summary: StructuredSummary;
}

type TabType = 'overview' | 'sections' | 'terms' | 'insights';

export default function SummarySection({ summary }: SummarySectionProps) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  // key_insights가 문자열인지 배열인지 확인
  const isKeyInsightsString = typeof summary.key_insights === 'string';
  const keyInsightsArray = Array.isArray(summary.key_insights) ? summary.key_insights : [];

  const tabs: { id: TabType; label: string; count?: number }[] = [
    { id: 'overview', label: '개요' },
    { id: 'sections', label: '상세 내용', count: summary.sections?.length || 0 },
    { id: 'terms', label: '핵심 용어', count: Array.isArray(summary.key_terms) ? summary.key_terms.length : 0 },
    { id: 'insights', label: '핵심 인사이트 및 결론', count: isKeyInsightsString ? 1 : keyInsightsArray.length },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* 탭 네비게이션 */}
      <div className="border-b border-gray-200">
        <nav className="flex overflow-x-auto" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex-shrink-0 px-6 py-4 text-sm font-medium border-b-2 transition-colors
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                  activeTab === tab.id
                    ? 'bg-blue-100 text-blue-600'
                    : 'bg-gray-100 text-gray-500'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* 탭 콘텐츠 */}
      <div className="p-6">
        <ErrorBoundary>
          {activeTab === 'overview' && (
            <OverviewCard overview={summary.overview} />
          )}

          {activeTab === 'sections' && (
            <div className="space-y-4">
              {summary.sections && summary.sections.length > 0 ? (
                summary.sections.map((section, index) => (
                  <SectionCard key={index} section={section} index={index} />
                ))
              ) : (
                <p className="text-gray-500 text-center py-8">상세 내용이 없습니다.</p>
              )}
            </div>
          )}

          {activeTab === 'terms' && (
            <KeyTermsCard terms={summary.key_terms || []} />
          )}

          {activeTab === 'insights' && (
            isKeyInsightsString ? (
              // key_insights가 문자열인 경우 - 텍스트로 표시
              <div>
                <div className="flex items-start gap-3 mb-4">
                  <div className="flex-shrink-0 w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">핵심 인사이트 및 결론</h3>
                    <p className="text-sm text-gray-500">영상에서 도출할 수 있는 주요 통찰과 결론입니다.</p>
                  </div>
                </div>
                <div className="bg-gradient-to-br from-amber-50 to-white border border-amber-100 rounded-lg p-4">
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {summary.key_insights as string}
                  </p>
                </div>
              </div>
            ) : (
              <KeyInsightsCard insights={keyInsightsArray} />
            )
          )}
        </ErrorBoundary>
      </div>
    </div>
  );
}
