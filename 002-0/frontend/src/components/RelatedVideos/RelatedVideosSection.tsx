import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Video, User, Play } from 'lucide-react';
import { getRelatedVideos, type RelatedVideo } from '../../services/api';

interface RelatedVideosSectionProps {
  videoUrl: string;
}

export default function RelatedVideosSection({ videoUrl }: RelatedVideosSectionProps) {
  const [relatedVideos, setRelatedVideos] = useState<RelatedVideo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedUrl, setLastFetchedUrl] = useState<string>('');

  useEffect(() => {
    const fetchRelatedVideos = async () => {
      try {
        setLoading(true);
        setError(null);
        setRelatedVideos([]);
        const response = await getRelatedVideos(videoUrl);
        if (response.success) {
          setRelatedVideos(response.related_videos);
        } else {
          setError(response.error || '관련 동영상을 가져올 수 없습니다.');
        }
        setLastFetchedUrl(videoUrl);
      } catch (err) {
        setError('관련 동영상 로드 실패');
      } finally {
        setLoading(false);
      }
    };

    // videoUrl이 있고, 아직 fetch하지 않았거나 URL이 변경된 경우에만 fetch
    if (videoUrl && videoUrl !== lastFetchedUrl) {
      fetchRelatedVideos();
    }
  }, [videoUrl, lastFetchedUrl]);

  // URL이 없으면 렌더링하지 않음
  if (!videoUrl) {
    return null;
  }

  // 로딩 중이거나 아직 fetch하지 않은 경우
  if (loading || (videoUrl !== lastFetchedUrl)) {
    return (
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6 mt-6">
        <h3 className="text-lg font-semibold text-zinc-100 mb-4 flex items-center gap-2">
          <Video className="w-5 h-5 text-rose-500" />
          관련 동영상
        </h3>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
          <span className="ml-3 text-zinc-500">관련 동영상 검색 중...</span>
        </div>
      </div>
    );
  }

  // 에러 또는 결과 없음 (fetch 완료 후)
  if (error || relatedVideos.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6 mt-6"
    >
      <h3 className="text-lg font-semibold text-zinc-100 mb-4 flex items-center gap-2">
        <Video className="w-5 h-5 text-rose-500" />
        관련 동영상
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {relatedVideos.map((video) => (
          <a
            key={video.video_id}
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group block rounded-xl overflow-hidden border border-zinc-800 hover:border-pink-500/50 bg-zinc-800/30 hover:bg-zinc-800/60 transition-all"
          >
            {/* 썸네일 */}
            <div className="relative aspect-video bg-zinc-800">
              <img
                src={video.thumbnail_url}
                alt={video.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = `https://img.youtube.com/vi/${video.video_id}/hqdefault.jpg`;
                }}
              />
              {/* 재생 아이콘 오버레이 */}
              <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/40 transition-all">
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-pink-500 to-rose-500 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
                  <Play className="w-5 h-5 text-white ml-0.5" fill="white" />
                </div>
              </div>
            </div>

            {/* 비디오 정보 */}
            <div className="p-3">
              <h4 className="text-sm font-medium text-zinc-100 line-clamp-2 group-hover:text-pink-400 transition-colors">
                {video.title}
              </h4>
              <p className="text-xs text-zinc-500 mt-1 flex items-center gap-1">
                <User className="w-3 h-3" />
                {video.author}
              </p>
            </div>
          </a>
        ))}
      </div>
    </motion.div>
  );
}
