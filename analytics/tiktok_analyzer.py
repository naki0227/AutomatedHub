"""
TikTok トレンド分析モジュール
非公式APIを使用してトレンドを取得
"""
from dataclasses import dataclass
from typing import List, Optional
import asyncio

from core.utils import logger


@dataclass
class TikTokVideoMetadata:
    """TikTok動画メタデータ"""
    video_id: str
    description: str
    author: str
    hashtags: List[str]
    music_title: str
    play_count: int
    like_count: int
    comment_count: int
    share_count: int
    
    @property
    def engagement_rate(self) -> float:
        if self.play_count == 0:
            return 0.0
        return (self.like_count + self.comment_count + self.share_count) / self.play_count


class TikTokAnalyzer:
    """
    TikTok トレンド分析
    
    注意: 非公式APIを使用するため、動作が不安定な場合があります。
    """
    
    def __init__(self):
        self._api = None
        logger.info("TikTokAnalyzer initialized")
    
    async def _get_api(self):
        """TikTokApiインスタンスを取得（遅延初期化）"""
        if self._api is None:
            try:
                from TikTokApi import TikTokApi
                self._api = TikTokApi()
                await self._api.create_sessions(
                    num_sessions=1,
                    sleep_after=3
                )
            except ImportError:
                logger.error("TikTokApi not installed. Run: pip install TikTokApi")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize TikTokApi: {e}")
                raise
        return self._api
    
    async def get_trending_videos(self, count: int = 20) -> List[TikTokVideoMetadata]:
        """トレンド動画を取得"""
        logger.info(f"Fetching TikTok trending videos: {count}")
        
        try:
            api = await self._get_api()
            videos = []
            
            async for video in api.trending.videos(count=count):
                videos.append(self._parse_video(video))
            
            return videos
        except Exception as e:
            logger.error(f"Failed to fetch TikTok trends: {e}")
            return []
    
    async def get_hashtag_videos(
        self,
        hashtag: str,
        count: int = 20
    ) -> List[TikTokVideoMetadata]:
        """ハッシュタグの動画を取得"""
        logger.info(f"Fetching TikTok hashtag videos: #{hashtag}")
        
        try:
            api = await self._get_api()
            videos = []
            
            tag = api.hashtag(name=hashtag)
            async for video in tag.videos(count=count):
                videos.append(self._parse_video(video))
            
            return videos
        except Exception as e:
            logger.error(f"Failed to fetch hashtag videos: {e}")
            return []
    
    def get_trending_videos_sync(self, count: int = 20) -> List[TikTokVideoMetadata]:
        """同期版: トレンド動画を取得"""
        return asyncio.run(self.get_trending_videos(count))
    
    def get_hashtag_videos_sync(self, hashtag: str, count: int = 20) -> List[TikTokVideoMetadata]:
        """同期版: ハッシュタグ動画を取得"""
        return asyncio.run(self.get_hashtag_videos(hashtag, count))
    
    def analyze_trends(self, videos: List[TikTokVideoMetadata]) -> dict:
        """動画リストからトレンドを分析"""
        if not videos:
            return {}
        
        # ハッシュタグ集計
        all_hashtags = []
        for video in videos:
            all_hashtags.extend(video.hashtags)
        
        hashtag_counts = {}
        for tag in all_hashtags:
            tag_lower = tag.lower()
            hashtag_counts[tag_lower] = hashtag_counts.get(tag_lower, 0) + 1
        
        popular_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # 音楽集計
        music_counts = {}
        for video in videos:
            if video.music_title:
                music_counts[video.music_title] = music_counts.get(video.music_title, 0) + 1
        
        popular_music = sorted(music_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 統計
        total_plays = sum(v.play_count for v in videos)
        avg_plays = total_plays / len(videos)
        avg_engagement = sum(v.engagement_rate for v in videos) / len(videos)
        
        return {
            "video_count": len(videos),
            "total_plays": total_plays,
            "avg_plays": int(avg_plays),
            "avg_engagement_rate": round(avg_engagement, 4),
            "popular_hashtags": popular_hashtags,
            "popular_music": popular_music
        }
    
    def _parse_video(self, video) -> TikTokVideoMetadata:
        """TikTokApi レスポンスをパース"""
        info = video.as_dict
        stats = info.get("stats", {})
        music = info.get("music", {})
        
        # ハッシュタグ抽出
        challenges = info.get("challenges", [])
        hashtags = [c.get("title", "") for c in challenges if c.get("title")]
        
        return TikTokVideoMetadata(
            video_id=info.get("id", ""),
            description=info.get("desc", ""),
            author=info.get("author", {}).get("uniqueId", ""),
            hashtags=hashtags,
            music_title=music.get("title", ""),
            play_count=stats.get("playCount", 0),
            like_count=stats.get("diggCount", 0),
            comment_count=stats.get("commentCount", 0),
            share_count=stats.get("shareCount", 0)
        )
