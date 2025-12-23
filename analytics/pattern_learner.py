"""
パターン学習モジュール
複数プラットフォームのトレンドから共通パターンを抽出・保存
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from core.config import get_config
from core.utils import logger, ensure_dir


@dataclass
class TrendPattern:
    """学習したトレンドパターン"""
    platform: str
    genre: str
    updated_at: str
    sample_count: int
    
    # コンテンツパターン
    popular_hashtags: List[tuple]  # (tag, count)
    popular_tags: List[tuple]      # YouTube用
    title_patterns: List[str]
    
    # エンゲージメント統計
    avg_engagement_rate: float
    
    # コンテンツ特性
    avg_content_length: Optional[int] = None  # キャプション/説明文の長さ
    video_ratio: Optional[float] = None       # 動画の割合


class PatternLearner:
    """
    トレンドパターン学習エンジン
    
    各プラットフォームの分析結果から共通パターンを抽出し、
    JSONとして保存。コンテンツ生成時に参照。
    """
    
    def __init__(self):
        config = get_config()
        self.patterns_dir = config.project_root / "analytics" / "patterns"
        ensure_dir(self.patterns_dir)
        logger.info("PatternLearner initialized")
    
    def learn_from_youtube(self, analysis: dict, genre: str = "general") -> TrendPattern:
        """YouTubeの分析結果からパターンを学習"""
        pattern = TrendPattern(
            platform="youtube",
            genre=genre,
            updated_at=datetime.now().isoformat(),
            sample_count=analysis.get("video_count", 0),
            popular_hashtags=[],
            popular_tags=analysis.get("popular_tags", []),
            title_patterns=analysis.get("title_patterns", []),
            avg_engagement_rate=analysis.get("avg_engagement_rate", 0)
        )
        
        self._save_pattern(pattern)
        return pattern
    
    def learn_from_tiktok(self, analysis: dict, genre: str = "general") -> TrendPattern:
        """TikTokの分析結果からパターンを学習"""
        pattern = TrendPattern(
            platform="tiktok",
            genre=genre,
            updated_at=datetime.now().isoformat(),
            sample_count=analysis.get("video_count", 0),
            popular_hashtags=analysis.get("popular_hashtags", []),
            popular_tags=[],
            title_patterns=[],
            avg_engagement_rate=analysis.get("avg_engagement_rate", 0)
        )
        
        self._save_pattern(pattern)
        return pattern
    
    def learn_from_instagram(self, analysis: dict, genre: str = "general") -> TrendPattern:
        """Instagramの分析結果からパターンを学習"""
        pattern = TrendPattern(
            platform="instagram",
            genre=genre,
            updated_at=datetime.now().isoformat(),
            sample_count=analysis.get("post_count", 0),
            popular_hashtags=analysis.get("popular_hashtags", []),
            popular_tags=[],
            title_patterns=[],
            avg_engagement_rate=0,  # Instagramはエンゲージメント率を別途計算
            avg_content_length=analysis.get("avg_caption_length"),
            video_ratio=analysis.get("video_ratio")
        )
        
        self._save_pattern(pattern)
        return pattern
    
    def get_pattern(self, platform: str, genre: str = "general") -> Optional[TrendPattern]:
        """保存済みパターンを取得"""
        pattern_path = self.patterns_dir / f"{platform}_{genre}.json"
        
        if not pattern_path.exists():
            logger.warning(f"Pattern not found: {pattern_path}")
            return None
        
        try:
            with open(pattern_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return TrendPattern(**data)
        except Exception as e:
            logger.error(f"Failed to load pattern: {e}")
            return None
    
    def get_recommended_hashtags(
        self,
        platform: str,
        genre: str = "general",
        count: int = 5
    ) -> List[str]:
        """おすすめハッシュタグを取得"""
        pattern = self.get_pattern(platform, genre)
        
        if not pattern:
            return []
        
        # 頻出順に取得
        hashtags = pattern.popular_hashtags[:count]
        return [f"#{tag}" for tag, _ in hashtags]
    
    def merge_patterns(
        self,
        patterns: List[TrendPattern]
    ) -> Dict[str, List[str]]:
        """複数プラットフォームのパターンを統合"""
        merged_hashtags = {}
        
        for pattern in patterns:
            for tag, count in pattern.popular_hashtags:
                tag_lower = tag.lower()
                if tag_lower not in merged_hashtags:
                    merged_hashtags[tag_lower] = 0
                merged_hashtags[tag_lower] += count
        
        # 共通ハッシュタグ（複数プラットフォームで使われているもの）
        sorted_tags = sorted(merged_hashtags.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "common_hashtags": [f"#{tag}" for tag, _ in sorted_tags[:10]],
            "platforms_analyzed": [p.platform for p in patterns],
            "total_samples": sum(p.sample_count for p in patterns)
        }
    
    def _save_pattern(self, pattern: TrendPattern) -> Path:
        """パターンをJSONとして保存"""
        pattern_path = self.patterns_dir / f"{pattern.platform}_{pattern.genre}.json"
        
        with open(pattern_path, "w", encoding="utf-8") as f:
            json.dump(asdict(pattern), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Pattern saved: {pattern_path}")
        return pattern_path
    
    def list_patterns(self) -> List[str]:
        """保存済みパターン一覧を取得"""
        patterns = list(self.patterns_dir.glob("*.json"))
        return [p.stem for p in patterns]
