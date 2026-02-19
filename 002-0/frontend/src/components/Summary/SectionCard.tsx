import { useState } from 'react';
import type { Section } from '../../types';

interface SectionCardProps {
  section: Section;
  index: number;
}

export default function SectionCard({ section, index }: SectionCardProps) {
  const [isExpanded, setIsExpanded] = useState(true); // 모든 섹션 기본 펼침

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* 섹션 헤더 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-medium">
            {index + 1}
          </span>
          <h4 className="font-medium text-gray-900">{section.section_title}</h4>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {section.subtopics?.length || 0}개 소주제
          </span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* 섹션 콘텐츠 */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {section.subtopics && section.subtopics.length > 0 ? (
            section.subtopics.map((subtopic, subIndex) => {
              // API returns 'title' and 'content', but legacy format uses 'subtopic_title' and 'summary'
              const title = subtopic.title || subtopic.subtopic_title || '';
              const content = subtopic.content || subtopic.summary || '';
              const keyPoints = subtopic.key_points || [];

              return (
                <div key={subIndex} className="border-l-2 border-blue-200 pl-4">
                  <h5 className="font-medium text-gray-800 mb-2">
                    {title}
                  </h5>

                  {/* 내용/요약 */}
                  {content && (
                    <p className="text-gray-600 text-sm mb-3 whitespace-pre-wrap">
                      {content}
                    </p>
                  )}

                  {/* 핵심 포인트 */}
                  {keyPoints.length > 0 && (
                    <ul className="space-y-1">
                      {keyPoints.map((point, pointIndex) => (
                        <li key={pointIndex} className="flex items-start gap-2 text-sm text-gray-600">
                          <span className="text-blue-500 mt-1">•</span>
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* 타임스탬프 범위 */}
                  {subtopic.timestamp_range && (
                    <p className="text-xs text-gray-400 mt-2">
                      {subtopic.timestamp_range}
                    </p>
                  )}
                </div>
              );
            })
          ) : (
            <p className="text-gray-500 text-sm">소주제가 없습니다.</p>
          )}
        </div>
      )}
    </div>
  );
}
