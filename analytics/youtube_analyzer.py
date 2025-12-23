"""
YouTube Data API分析モジュール
トレンド動画のメタデータを取得・分析
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from googleapiclient.discovery import build

from core.config import get_config
from core.utils import logger


@dataclass
class VideoMetadata:
    """動画メタデータ"""
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    tags: List[str]
    view_count: int
    like_count: int
    comment_count: int
    published_at: str
    duration: str
    thumbnail_url: str
    
    @property
    def engagement_rate(self) -> float:
        """エンゲージメント率 (likes + comments) / views"""
        if self.view_count == 0:
            return 0.0
        return (self.like_count + self.comment_count) / self.view_count


class YouTubeAnalyzer:
    """YouTube トレンド分析"""
    
    # カテゴリID (日本)
    CATEGORIES = {
        "gaming": "20",
        "entertainment": "24",
        "education": "27",
        "science_tech": "28",
        "music": "10",
        "howto_style": "26",
        "news_politics": "25",
        "comedy": "23",
        "film_animation": "1",
        "people_blogs": "22"
    }
    
    def __init__(self):
        config = get_config()
        if not config.validate_youtube():
            raise ValueError("YOUTUBE_API_KEY is not set")
        
        self.youtube = build("youtube", "v3", developerKey=config.youtube_api_key)
        logger.info("YouTubeAnalyzer initialized")
    
    def get_trending_videos(
        self,
        category: str = "all",
        region: str = "JP",
        max_results: int = 20
    ) -> List[VideoMetadata]:
        """
        トレンド動画を取得
        
        Args:
            category: カテゴリ名 (gaming, entertainment, etc.) or "all"
            region: 地域コード
            max_results: 最大取得件数
        """
        logger.info(f"Fetching trending videos: {category}, {region}")
        
        params = {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": min(max_results, 50)
        }
        
        if category != "all" and category in self.CATEGORIES:
            params["videoCategoryId"] = self.CATEGORIES[category]
        
        try:
            response = self.youtube.videos().list(**params).execute()
            return self._parse_videos(response.get("items", []))
        except Exception as e:
            logger.error(f"Failed to fetch trending videos: {e}")
            return []
    
    def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 20,
        order: str = "viewCount"
    ) -> List[VideoMetadata]:
        """
        チャンネルの動画を取得
        
        Args:
            channel_id: チャンネルID
            max_results: 最大取得件数
            order: 並び順 (viewCount, date, rating)
        """
        logger.info(f"Fetching channel videos: {channel_id}")
        
        try:
            # まず検索で動画IDを取得
            search_response = self.youtube.search().list(
                part="id",
                channelId=channel_id,
                type="video",
                order=order,
                maxResults=min(max_results, 50)
            ).execute()
            
            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            
            if not video_ids:
                return []
            
            # 動画の詳細情報を取得
            videos_response = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()
            
            return self._parse_videos(videos_response.get("items", []))
        except Exception as e:
            logger.error(f"Failed to fetch channel videos: {e}")
            return []
    
    def search_videos(
        self,
        query: str,
        max_results: int = 20,
        order: str = "viewCount"
    ) -> List[VideoMetadata]:
        """
        動画を検索
        
        Args:
            query: 検索クエリ
            max_results: 最大取得件数
            order: 並び順 (viewCount, date, relevance)
        """
        logger.info(f"Searching videos: {query}")
        
        try:
            search_response = self.youtube.search().list(
                part="id",
                q=query,
                type="video",
                order=order,
                maxResults=min(max_results, 50),
                regionCode="JP"
            ).execute()
            
            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            
            if not video_ids:
                return []
            
            videos_response = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()
            
            return self._parse_videos(videos_response.get("items", []))
        except Exception as e:
            logger.error(f"Failed to search videos: {e}")
            return []
    
    def analyze_trends(self, videos: List[VideoMetadata]) -> dict:
        """
        動画リストからトレンドを分析
        """
        if not videos:
            return {}
        
        # タグを集計
        all_tags = []
        for video in videos:
            all_tags.extend(video.tags)
        
        tag_counts = {}
        for tag in all_tags:
            tag_lower = tag.lower()
            tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1
        
        # 頻出タグをソート
        popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # 統計
        total_views = sum(v.view_count for v in videos)
        avg_views = total_views / len(videos)
        avg_engagement = sum(v.engagement_rate for v in videos) / len(videos)
        
        # タイトルパターン分析（簡易）
        title_patterns = []
        for video in videos:
            if "【" in video.title and "】" in video.title:
                title_patterns.append("bracket_style")  # 【タイトル】スタイル
            elif "?" in video.title or "！" in video.title:
                title_patterns.append("question_exclaim")
            elif any(emoji in video.title for emoji in ["🔥", "😱", "🎉", "✨"]):
                title_patterns.append("emoji_heavy")
        
        return {
            "video_count": len(videos),
            "total_views": total_views,
            "avg_views": int(avg_views),
            "avg_engagement_rate": round(avg_engagement, 4),
            "popular_tags": popular_tags,
            "title_patterns": title_patterns,
            "top_videos": [
                {"title": v.title, "views": v.view_count, "engagement": round(v.engagement_rate, 4)}
                for v in sorted(videos, key=lambda x: x.view_count, reverse=True)[:5]
            ]
        }
    
    def _parse_videos(self, items: List[dict]) -> List[VideoMetadata]:
        """API レスポンスをパース"""
        videos = []
        for item in items:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            
            videos.append(VideoMetadata(
                video_id=item.get("id", ""),
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                channel_id=snippet.get("channelId", ""),
                channel_title=snippet.get("channelTitle", ""),
                tags=snippet.get("tags", []),
                view_count=int(stats.get("viewCount", 0)),
                like_count=int(stats.get("likeCount", 0)),
                comment_count=int(stats.get("commentCount", 0)),
                published_at=snippet.get("publishedAt", ""),
                duration=content.get("duration", ""),
                thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            ))
        
        return videos
