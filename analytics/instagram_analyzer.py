"""
Instagram トレンド分析モジュール
Instaloaderを使用してトレンドを取得
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from core.utils import logger


@dataclass
class InstagramPostMetadata:
    """Instagram投稿メタデータ"""
    shortcode: str
    caption: str
    hashtags: List[str]
    owner: str
    like_count: int
    comment_count: int
    is_video: bool
    posted_at: datetime
    
    @property
    def engagement(self) -> int:
        return self.like_count + self.comment_count


class InstagramAnalyzer:
    """
    Instagram トレンド分析
    
    注意: Instaloaderを使用。ログイン不要ですが、
    大量リクエストはレート制限を受ける可能性があります。
    """
    
    def __init__(self):
        self._loader = None
        logger.info("InstagramAnalyzer initialized")
    
    def _get_loader(self):
        """Instaloaderインスタンスを取得（遅延初期化）"""
        if self._loader is None:
            try:
                import instaloader
                self._loader = instaloader.Instaloader(
                    download_pictures=False,
                    download_videos=False,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=False,
                    compress_json=False
                )
            except ImportError:
                logger.error("Instaloader not installed. Run: pip install instaloader")
                raise
        return self._loader
    
    def get_hashtag_posts(
        self,
        hashtag: str,
        count: int = 20
    ) -> List[InstagramPostMetadata]:
        """ハッシュタグの投稿を取得"""
        logger.info(f"Fetching Instagram hashtag posts: #{hashtag}")
        
        try:
            loader = self._get_loader()
            import instaloader
            
            posts = []
            hashtag_obj = instaloader.Hashtag.from_name(loader.context, hashtag)
            
            for i, post in enumerate(hashtag_obj.get_posts()):
                if i >= count:
                    break
                posts.append(self._parse_post(post))
            
            return posts
        except Exception as e:
            logger.error(f"Failed to fetch hashtag posts: {e}")
            return []
    
    def get_profile_posts(
        self,
        username: str,
        count: int = 20
    ) -> List[InstagramPostMetadata]:
        """プロフィールの投稿を取得"""
        logger.info(f"Fetching Instagram profile posts: @{username}")
        
        try:
            loader = self._get_loader()
            import instaloader
            
            profile = instaloader.Profile.from_username(loader.context, username)
            posts = []
            
            for i, post in enumerate(profile.get_posts()):
                if i >= count:
                    break
                posts.append(self._parse_post(post))
            
            return posts
        except Exception as e:
            logger.error(f"Failed to fetch profile posts: {e}")
            return []
    
    def analyze_trends(self, posts: List[InstagramPostMetadata]) -> dict:
        """投稿リストからトレンドを分析"""
        if not posts:
            return {}
        
        # ハッシュタグ集計
        all_hashtags = []
        for post in posts:
            all_hashtags.extend(post.hashtags)
        
        hashtag_counts = {}
        for tag in all_hashtags:
            tag_lower = tag.lower()
            hashtag_counts[tag_lower] = hashtag_counts.get(tag_lower, 0) + 1
        
        popular_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # 統計
        total_likes = sum(p.like_count for p in posts)
        avg_likes = total_likes / len(posts)
        avg_comments = sum(p.comment_count for p in posts) / len(posts)
        video_ratio = sum(1 for p in posts if p.is_video) / len(posts)
        
        # キャプション長分析
        avg_caption_length = sum(len(p.caption) for p in posts) / len(posts)
        avg_hashtag_count = sum(len(p.hashtags) for p in posts) / len(posts)
        
        return {
            "post_count": len(posts),
            "total_likes": total_likes,
            "avg_likes": int(avg_likes),
            "avg_comments": round(avg_comments, 1),
            "video_ratio": round(video_ratio, 2),
            "avg_caption_length": int(avg_caption_length),
            "avg_hashtag_count": round(avg_hashtag_count, 1),
            "popular_hashtags": popular_hashtags,
            "top_posts": [
                {"caption": p.caption[:50], "likes": p.like_count, "comments": p.comment_count}
                for p in sorted(posts, key=lambda x: x.engagement, reverse=True)[:5]
            ]
        }
    
    def _parse_post(self, post) -> InstagramPostMetadata:
        """Instaloader投稿をパース"""
        # キャプションからハッシュタグを抽出
        caption = post.caption or ""
        hashtags = [word[1:] for word in caption.split() if word.startswith("#")]
        
        return InstagramPostMetadata(
            shortcode=post.shortcode,
            caption=caption,
            hashtags=hashtags,
            owner=post.owner_username,
            like_count=post.likes,
            comment_count=post.comments,
            is_video=post.is_video,
            posted_at=post.date_utc
        )
