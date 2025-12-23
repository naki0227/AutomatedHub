"""
コンテンツアイデア生成
YouTube/TikTok/note用のネタを自動で提案
"""
import json
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

from ai.gemini_client import GeminiClient
from core.config import get_config
from core.utils import logger, ensure_dir, get_timestamp


@dataclass
class ContentIdea:
    """コンテンツアイデア"""
    category: str  # 技術 / 語学 / アプリPR
    title: str
    description: str
    platform: str  # youtube / tiktok / note
    
    # 詳細
    key_points: List[str]
    target_audience: str
    estimated_duration: str
    
    # 関連
    related_project: Optional[str] = None
    hashtags: List[str] = None
    
    created_at: str = None


class ContentIdeaGenerator:
    """
    コンテンツアイデアジェネレーター
    
    テーマ:
    - 技術: Flutter, Python, AI, 個人開発
    - 語学: 効率的な学習法, アプリ活用
    - アプリPR: Encura, Vidnitive, Mirutabi
    """
    
    def __init__(self):
        config = get_config()
        self.gemini = GeminiClient()
        self.output_dir = config.project_root / "sns" / "content_ideas"
        ensure_dir(self.output_dir)
        
        # プロフィールから設定読み込み
        self.profile = self._load_profile(config.project_root / "profile.json")
        self.themes = self.profile.get("video_content", {}).get("themes", [])
        self.projects = self.profile.get("projects", {})
        
        logger.info("ContentIdeaGenerator initialized")
    
    def _load_profile(self, path: Path) -> dict:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def generate_ideas(self, count: int = 5, platform: str = "all") -> List[ContentIdea]:
        """
        コンテンツアイデアを生成
        
        Args:
            count: 生成するアイデア数
            platform: "youtube", "tiktok", "note", "all"
        """
        logger.info(f"Generating {count} content ideas for {platform}")
        
        # テーマからランダムにピック
        all_topics = []
        for theme in self.themes:
            category = theme["category"]
            for topic in theme["topics"]:
                all_topics.append((category, topic))
        
        # プロジェクト情報
        released_projects = self.projects.get("released", [])
        in_dev_projects = self.projects.get("in_development", [])
        
        projects_info = []
        for p in released_projects:
            projects_info.append(f"{p['name']}: {p['description']} ({p['platform']})")
        
        # Geminiでアイデア生成
        system_instruction = f"""
あなたはEnludusというブランドのコンテンツプランナーです。
技術・語学・自作アプリPRに関するSNSコンテンツのアイデアを提案します。

【発信者プロフィール】
- ブランド: Enludus
- テーマ: 学びを冒険に。壁を、扉に。
- 専門: AI, Flutter, Python, 教育テック

【リリース済みプロジェクト】
{chr(10).join(projects_info)}

【開発中プロジェクト】
{', '.join(in_dev_projects)}

【コンテンツカテゴリ】
1. 技術: Flutter/Python/AI開発Tips、個人開発の裏側
2. 語学: 効率的な学習法、アプリで学ぶ外国語
3. アプリPR: 自作アプリの機能紹介、活用法、開発秘話

【プラットフォーム別特徴】
- YouTube: 5-10分の解説・チュートリアル
- TikTok: 30-60秒のTips・ハック
- note: 詳しい解説記事

{count}個のコンテンツアイデアをJSON配列で出力してください。

出力形式:
[
  {{
    "category": "技術|語学|アプリPR",
    "title": "タイトル",
    "description": "概要",
    "platform": "youtube|tiktok|note",
    "key_points": ["ポイント1", "ポイント2"],
    "target_audience": "想定視聴者",
    "estimated_duration": "想定時間",
    "related_project": "関連プロジェクト名（あれば）",
    "hashtags": ["#タグ1", "#タグ2"]
  }}
]
"""
        
        platform_filter = "" if platform == "all" else f"プラットフォームは{platform}に限定してください。"
        
        response = self.gemini.generate_text(
            prompt=f"コンテンツアイデアを{count}個提案してください。{platform_filter}",
            system_instruction=system_instruction,
            max_tokens=3000,
            temperature=0.9
        )
        
        # パース
        ideas = self._parse_response(response, count, platform)
        
        # 保存
        self._save_ideas(ideas)
        
        return ideas
    
    def _parse_response(self, response: str, count: int, platform: str) -> List[ContentIdea]:
        """レスポンスをパース"""
        ideas = []
        
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            
            data = json.loads(clean)
            
            for item in data:
                idea = ContentIdea(
                    category=item.get("category", "技術"),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    platform=item.get("platform", platform if platform != "all" else "youtube"),
                    key_points=item.get("key_points", []),
                    target_audience=item.get("target_audience", ""),
                    estimated_duration=item.get("estimated_duration", ""),
                    related_project=item.get("related_project"),
                    hashtags=item.get("hashtags", []),
                    created_at=datetime.now().isoformat()
                )
                ideas.append(idea)
        except Exception as e:
            logger.error(f"Failed to parse ideas: {e}")
        
        return ideas
    
    def _save_ideas(self, ideas: List[ContentIdea]):
        """アイデアを保存"""
        timestamp = get_timestamp()
        path = self.output_dir / f"ideas_{timestamp}.json"
        
        data = [asdict(idea) for idea in ideas]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Ideas saved: {path}")
    
    def get_weekly_plan(self) -> dict:
        """1週間分のコンテンツプランを生成"""
        ideas = self.generate_ideas(count=7, platform="all")
        
        days = ["月", "火", "水", "木", "金", "土", "日"]
        plan = {}
        
        for i, day in enumerate(days):
            if i < len(ideas):
                plan[day] = asdict(ideas[i])
            else:
                plan[day] = None
        
        return plan


def print_ideas(ideas: List[ContentIdea]):
    """アイデアを表示"""
    print("=" * 60)
    print(f"コンテンツアイデア {len(ideas)}件")
    print("=" * 60)
    
    for i, idea in enumerate(ideas, 1):
        print(f"\n【{i}】{idea.title}")
        print(f"   カテゴリ: {idea.category}")
        print(f"   プラットフォーム: {idea.platform}")
        print(f"   概要: {idea.description}")
        print(f"   想定視聴者: {idea.target_audience}")
        print(f"   想定時間: {idea.estimated_duration}")
        if idea.related_project:
            print(f"   関連プロジェクト: {idea.related_project}")
        print(f"   ポイント: {', '.join(idea.key_points[:3])}")
        print(f"   ハッシュタグ: {' '.join(idea.hashtags[:3])}")


def print_weekly_plan(plan: dict):
    """週間プランを表示"""
    print("=" * 60)
    print("1週間コンテンツプラン")
    print("=" * 60)
    
    for day, idea in plan.items():
        if idea:
            print(f"\n{day}曜: [{idea['platform']}] {idea['title']}")
            print(f"     {idea['description'][:50]}...")
        else:
            print(f"\n{day}曜: なし")


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="コンテンツアイデア生成")
    parser.add_argument("--count", type=int, default=5, help="アイデア数")
    parser.add_argument("--platform", choices=["youtube", "tiktok", "note", "all"], default="all")
    parser.add_argument("--weekly", action="store_true", help="週間プラン生成")
    
    args = parser.parse_args()
    
    generator = ContentIdeaGenerator()
    
    if args.weekly:
        plan = generator.get_weekly_plan()
        print_weekly_plan(plan)
    else:
        ideas = generator.generate_ideas(args.count, args.platform)
        print_ideas(ideas)
