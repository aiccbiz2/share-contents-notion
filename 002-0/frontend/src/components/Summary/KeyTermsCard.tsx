import type { KeyTerm } from '../../types';

interface KeyTermsCardProps {
  terms: KeyTerm[];
}

export default function KeyTermsCard({ terms }: KeyTermsCardProps) {
  if (!terms || terms.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        핵심 용어가 없습니다.
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
          <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">핵심 용어</h3>
          <p className="text-sm text-gray-500">영상에서 언급된 주요 용어와 정의입니다.</p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {terms.map((term, index) => (
          <div
            key={index}
            className="bg-gradient-to-br from-purple-50 to-white border border-purple-100 rounded-lg p-4"
          >
            <dt className="font-semibold text-purple-900 mb-1">
              {term.term}
            </dt>
            <dd className="text-sm text-gray-600">
              {term.definition}
            </dd>
          </div>
        ))}
      </div>
    </div>
  );
}
