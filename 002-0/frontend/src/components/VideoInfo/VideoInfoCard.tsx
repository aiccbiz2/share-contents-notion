import { useState } from 'react';
import type { VideoInfo } from '../../types';

interface VideoInfoCardProps {
  videoInfo: VideoInfo;
  notionUrl?: string;
}

// Notion 버튼 컴포넌트 (링크 열기 + URL 복사)
function NotionButtons({ notionUrl }: { notionUrl: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(notionUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('URL 복사 실패:', err);
    }
  };

  return (
    <div className="pt-2 flex flex-wrap gap-2">
      {/* Notion 열기 버튼 */}
      <a
        href={notionUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.84-.046.933-.56.933-1.167V6.354c0-.606-.233-.933-.746-.886l-15.177.887c-.56.046-.747.326-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.747 0-.933-.234-1.495-.933l-4.577-7.186v6.952l1.449.327s0 .84-1.168.84l-3.22.186c-.094-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933l3.222-.187zM2.035 1.108l13.823-.933c1.681-.14 2.101.046 2.848.607l3.595 2.567c.56.42.746.933.746 1.54v15.75c0 1.027-.373 1.68-1.68 1.773l-15.458.933c-.98.047-1.448-.093-1.962-.7l-2.846-3.64c-.607-.793-.84-1.4-.84-2.1V2.568c0-.84.373-1.54 1.774-1.46z"/>
        </svg>
        Notion에서 보기
      </a>

      {/* URL 복사 버튼 */}
      <button
        onClick={handleCopy}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${
          copied
            ? 'bg-green-500 text-white'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
        }`}
      >
        {copied ? (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            복사됨!
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            URL 복사
          </>
        )}
      </button>
    </div>
  );
}

// 초를 시:분:초 형식으로 변환
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

export default function VideoInfoCard({ videoInfo, notionUrl }: VideoInfoCardProps) {
  const thumbnailUrl = videoInfo.thumbnail_url ||
    `https://img.youtube.com/vi/${videoInfo.video_id}/maxresdefault.jpg`;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden my-6">
      <div className="flex flex-col sm:flex-row">
        {/* 썸네일 */}
        <div className="sm:w-64 md:w-80 flex-shrink-0">
          <a
            href={videoInfo.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block relative aspect-video sm:aspect-auto sm:h-full"
          >
            <img
              src={thumbnailUrl}
              alt={videoInfo.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                // maxresdefault가 없으면 hqdefault로 대체
                const target = e.target as HTMLImageElement;
                if (target.src.includes('maxresdefault')) {
                  target.src = `https://img.youtube.com/vi/${videoInfo.video_id}/hqdefault.jpg`;
                }
              }}
            />
            {/* 재생 시간 배지 */}
            <div className="absolute bottom-2 right-2 bg-black bg-opacity-80 text-white text-xs px-1.5 py-0.5 rounded">
              {formatDuration(videoInfo.length)}
            </div>
          </a>
        </div>

        {/* 비디오 정보 */}
        <div className="flex-1 p-4 sm:p-5">
          <div className="space-y-3">
            {/* 제목 */}
            <h2 className="text-lg font-semibold text-gray-900 line-clamp-2">
              <a
                href={videoInfo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 transition-colors"
              >
                {videoInfo.title}
              </a>
            </h2>

            {/* 채널명 */}
            <p className="text-sm text-gray-600 flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                  clipRule="evenodd"
                />
              </svg>
              {videoInfo.author}
            </p>

            {/* 메타 정보 */}
            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {formatDuration(videoInfo.length)}
              </span>
            </div>

            {/* Notion 링크 */}
            {notionUrl && (
              <NotionButtons notionUrl={notionUrl} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
