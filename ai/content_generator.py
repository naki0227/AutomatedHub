"""
コンテンツ生成モジュール
テキスト + 画像を統合してSNS投稿用コンテンツを生成
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import json

from core.config import get_config
from core.utils import logger, get_timestamp, ensure_dir
from .gemini_client import GeminiClient
from .image_generator import ImageGenerator


@dataclass
class GeneratedContent:
    """生成されたコンテンツ"""
    text: str
    hashtags: List[str]
    image_path: Optional[Path]
    platform: str
    topic: str
    created_at: str
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "hashtags": self.hashtags,
            "image_path": str(self.image_path) if self.image_path else None,
            "platform": self.platform,
            "topic": self.topic,
            "created_at": self.created_at
        }
    
    def full_text(self) -> str:
        """ハッシュタグ付きの完全なテキスト"""
        tags = " ".join(self.hashtags)
        return f"{self.text}\n\n{tags}" if tags else self.text


class ContentGenerator:
    """統合コンテンツ生成器"""
    
    def __init__(self):
        self.gemini = GeminiClient()
        self.image_gen = ImageGenerator()
        self.config = get_config()
        logger.info("ContentGenerator initialized")
    
    def generate(
        self,
        topic: str,
        platform: str = "x",
        style: str = "casual",
        include_image: bool = True,
        source_url: str = "",
        article_content: str = ""
    ) -> GeneratedContent:
        """
        SNS投稿用コンテンツを生成
        
        Args:
            topic: 投稿トピック
            platform: プラットフォーム (x, instagram, tiktok)
            style: スタイル (casual, professional, fun)
            include_image: 画像を生成するか
            source_url: ソースURL
            article_content: 記事の実際の内容
        
        Returns:
            GeneratedContent
        """
        logger.info(f"Generating content for {platform}: {topic}")
        
        # テキスト生成
        text_result = self.gemini.generate_sns_post(
            topic=topic,
            platform=platform,
            style=style,
            source_url=source_url,
            article_content=article_content
        )
        
        # 画像生成
        image_path = None
        if include_image:
            image_prompt = text_result.get("image_prompt", f"{topic}, modern design")
            if image_prompt:
                image_path = self.image_gen.generate_sns_image(
                    topic=image_prompt,
                    platform=platform
                )
        
        content = GeneratedContent(
            text=text_result.get("text", ""),
            hashtags=text_result.get("hashtags", []),
            image_path=image_path,
            platform=platform,
            topic=topic,
            created_at=get_timestamp()
        )
        
        logger.info(f"Content generated: {len(content.text)} chars, image: {image_path is not None}")
        return content
    
    def generate_batch(
        self,
        topics: List[str],
        platform: str = "x",
        style: str = "casual",
        include_image: bool = True
    ) -> List[GeneratedContent]:
        """複数トピックのコンテンツを一括生成"""
        results = []
        for topic in topics:
            try:
                content = self.generate(
                    topic=topic,
                    platform=platform,
                    style=style,
                    include_image=include_image
                )
                results.append(content)
            except Exception as e:
                logger.error(f"Failed to generate content for '{topic}': {e}")
        return results
    
    def save_as_draft(self, content: GeneratedContent) -> Path:
        """下書きとして保存（Instagram/TikTok用）"""
        drafts_dir = self.config.drafts_dir
        ensure_dir(drafts_dir)
        
        draft_path = drafts_dir / f"{content.platform}_{content.created_at}.json"
        
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(content.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Draft saved: {draft_path}")
        return draft_path
