"""
X (Twitter) 投稿クライアント
Free tierで動作（月1,500ツイート投稿可能）
"""
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import tweepy

from core.config import get_config
from core.utils import logger


@dataclass
class PostResult:
    """投稿結果"""
    success: bool
    tweet_id: Optional[str] = None
    error: Optional[str] = None
    url: Optional[str] = None


class XClient:
    """
    X (Twitter) API v2 クライアント
    
    Free tier制限:
    - 投稿: 月1,500件（1日約50件）
    - 読み取り: 不可
    """
    
    def __init__(self):
        config = get_config()
        if not config.validate_x():
            raise ValueError("X API credentials are not set")
        
        # API v2 (OAuth 1.0a User Context)
        self.client = tweepy.Client(
            consumer_key=config.x_api_key,
            consumer_secret=config.x_api_secret,
            access_token=config.x_access_token,
            access_token_secret=config.x_access_token_secret
        )
        
        # API v1.1 (メディアアップロード用)
        auth = tweepy.OAuth1UserHandler(
            config.x_api_key,
            config.x_api_secret,
            config.x_access_token,
            config.x_access_token_secret
        )
        self.api_v1 = tweepy.API(auth)
        
        logger.info("XClient initialized")
    
    def post(
        self,
        text: str,
        image_path: Optional[Path] = None,
        reply_to: Optional[str] = None
    ) -> PostResult:
        """
        ツイートを投稿
        
        Args:
            text: ツイート本文（280文字以内）
            image_path: 添付画像パス（オプション）
            reply_to: リプライ先のツイートID（オプション）
        """
        logger.info(f"Posting to X: {text[:50]}...")
        
        try:
            media_ids = None
            
            # 画像がある場合はアップロード
            if image_path and image_path.exists():
                media = self.api_v1.media_upload(str(image_path))
                media_ids = [media.media_id]
                logger.info(f"Media uploaded: {media.media_id}")
            
            # ツイート投稿
            response = self.client.create_tweet(
                text=text,
                media_ids=media_ids,
                in_reply_to_tweet_id=reply_to
            )
            
            tweet_id = response.data["id"]
            url = f"https://twitter.com/user/status/{tweet_id}"
            
            logger.info(f"Tweet posted: {tweet_id}")
            return PostResult(success=True, tweet_id=tweet_id, url=url)
            
        except tweepy.TweepyException as e:
            error_msg = str(e)
            logger.error(f"Failed to post tweet: {error_msg}")
            return PostResult(success=False, error=error_msg)
    
    def post_thread(self, texts: list[str]) -> list[PostResult]:
        """
        スレッド（連続ツイート）を投稿
        
        Args:
            texts: ツイート本文のリスト
        """
        results = []
        reply_to_id = None
        
        for i, text in enumerate(texts):
            logger.info(f"Posting thread {i+1}/{len(texts)}")
            
            try:
                response = self.client.create_tweet(
                    text=text,
                    in_reply_to_tweet_id=reply_to_id
                )
                
                tweet_id = response.data["id"]
                reply_to_id = tweet_id
                
                results.append(PostResult(
                    success=True,
                    tweet_id=tweet_id,
                    url=f"https://twitter.com/user/status/{tweet_id}"
                ))
                
            except tweepy.TweepyException as e:
                results.append(PostResult(success=False, error=str(e)))
                break  # スレッドが途切れるので中断
        
        return results
    
    def delete_tweet(self, tweet_id: str) -> bool:
        """ツイートを削除"""
        try:
            self.client.delete_tweet(tweet_id)
            logger.info(f"Tweet deleted: {tweet_id}")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Failed to delete tweet: {e}")
            return False
