"""
統合コンテンツ生成システム
X / note / Instagram / TikTok で連携したコンテンツを生成
"""
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from datetime import datetime

from ai.gemini_client import GeminiClient
from core.config import get_config
from core.utils import logger, ensure_dir, get_timestamp


@dataclass
class ConnectedContent:
    """連携コンテンツ"""
    topic: str
    created_at: str
    
    # note記事（メインコンテンツ）
    note_title: str
    note_content: str
    
    # X投稿（記事への誘導）
    x_post: str
    x_hashtags: list
    
    # Instagram投稿
    instagram_caption: str
    instagram_hashtags: list
    instagram_image_prompt: str
    
    # TikTok投稿
    tiktok_caption: str
    tiktok_hashtags: list
    tiktok_video_idea: str


class ConnectedContentGenerator:
    """
    連携コンテンツジェネレーター
    
    1つのトピックから全プラットフォーム用のコンテンツを生成
    - note: 詳細な記事（メイン）
    - X: 記事への誘導・要約
    - Instagram: ビジュアル重視のキャプション
    - TikTok: 動画アイデア + キャプション
    """
    
    def __init__(self):
        config = get_config()
        self.gemini = GeminiClient()
        self.output_dir = config.project_root / "sns" / "connected_content"
        ensure_dir(self.output_dir)
        
        # プロフィール読み込み
        self.profile = self._load_profile(config.project_root / "profile.json")
        
        logger.info("ConnectedContentGenerator initialized")
    
    def _load_profile(self, path: Path) -> dict:
        """プロフィールを読み込み"""
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def generate(self, topic: str) -> ConnectedContent:
        """
        連携コンテンツを生成
        
        Args:
            topic: コンテンツのトピック
        
        Returns:
            ConnectedContent: 全プラットフォーム用コンテンツ
        """
        logger.info(f"Generating connected content: {topic}")
        
        # プロフィールから口調設定を取得
        writing_style = self.profile.get("writing_style", {})
        brand = self.profile.get("profile", {}).get("brand", "")
        
        style_guide = ""
        if writing_style:
            characteristics = "\n".join([f"- {c}" for c in writing_style.get("characteristics", [])])
            avoid = "\n".join([f"- {a}" for a in writing_style.get("avoid", [])])
            style_guide = f"""
【口調の特徴】
{characteristics}

【避けること】
{avoid}
"""
        
        system_instruction = f"""
あなたは個人開発者のコンテンツマーケターです。
1つのトピックから、複数プラットフォーム向けに連携したコンテンツを作成します。

ブランド: {brand}

{style_guide}

【コンテンツ戦略】
- note: メインの詳細記事（500-1000字）
- X: noteへの誘導を意識した短い投稿（280字以内）
- Instagram: ビジュアル映えするキャプション + 画像アイデア
- TikTok: ショート動画のコンセプト + キャプション

全てのコンテンツは同じトピックについて語り、相互に補完し合う内容にしてください。
note記事が最も詳しく、X/Instagram/TikTokは興味を引いてnoteに誘導する役割です。

出力形式（JSON）:
{{
    "note_title": "note記事タイトル",
    "note_content": "note記事本文（Markdown形式、500-1000字）",
    "x_post": "X投稿本文（280字以内）",
    "x_hashtags": ["#タグ1", "#タグ2"],
    "instagram_caption": "Instagramキャプション",
    "instagram_hashtags": ["#タグ1", "#タグ2"],
    "instagram_image_prompt": "画像生成プロンプト（英語）",
    "tiktok_caption": "TikTokキャプション",
    "tiktok_hashtags": ["#タグ1", "#タグ2"],
    "tiktok_video_idea": "動画のコンセプト（30秒程度）"
}}
"""
        
        response = self.gemini.generate_text(
            prompt=f"トピック: {topic}\n\n連携コンテンツを作成してください。",
            system_instruction=system_instruction,
            max_tokens=3000,
            temperature=0.7
        )
        
        # JSON解析
        data = self._parse_response(response)
        
        content = ConnectedContent(
            topic=topic,
            created_at=datetime.now().isoformat(),
            note_title=data.get("note_title", topic),
            note_content=data.get("note_content", ""),
            x_post=data.get("x_post", ""),
            x_hashtags=data.get("x_hashtags", []),
            instagram_caption=data.get("instagram_caption", ""),
            instagram_hashtags=data.get("instagram_hashtags", []),
            instagram_image_prompt=data.get("instagram_image_prompt", ""),
            tiktok_caption=data.get("tiktok_caption", ""),
            tiktok_hashtags=data.get("tiktok_hashtags", []),
            tiktok_video_idea=data.get("tiktok_video_idea", "")
        )
        
        # 保存
        self._save_content(content)
        
        return content
    
    def _parse_response(self, response: str) -> dict:
        """レスポンスをパース"""
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean)
        except:
            return {"note_content": response}
    
    def _save_content(self, content: ConnectedContent):
        """コンテンツを保存"""
        timestamp = get_timestamp()
        
        # JSON形式で保存
        output_path = self.output_dir / f"content_{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(content), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Connected content saved: {output_path}")
    
    def list_contents(self, limit: int = 10) -> list:
        """保存済みコンテンツ一覧を取得"""
        contents = []
        for path in sorted(self.output_dir.glob("content_*.json"), reverse=True)[:limit]:
            with open(path, "r", encoding="utf-8") as f:
                contents.append(json.load(f))
        return contents


def print_content(content: ConnectedContent):
    """コンテンツを表示"""
    print("=" * 60)
    print(f"トピック: {content.topic}")
    print("=" * 60)
    
    print("\n📖 note記事")
    print(f"タイトル: {content.note_title}")
    print(f"本文:\n{content.note_content[:300]}...")
    
    print("\n🐦 X投稿")
    print(content.x_post)
    print(f"ハッシュタグ: {' '.join(content.x_hashtags)}")
    
    print("\n📸 Instagram")
    print(content.instagram_caption)
    print(f"画像アイデア: {content.instagram_image_prompt}")
    
    print("\n🎵 TikTok")
    print(content.tiktok_caption)
    print(f"動画アイデア: {content.tiktok_video_idea}")


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="連携コンテンツ生成")
    parser.add_argument("--topic", type=str, help="コンテンツトピック")
    parser.add_argument("--list", action="store_true", help="保存済み一覧")
    
    args = parser.parse_args()
    
    generator = ConnectedContentGenerator()
    
    if args.list:
        contents = generator.list_contents()
        for c in contents:
            print(f"- {c['created_at']}: {c['topic']}")
    elif args.topic:
        content = generator.generate(args.topic)
        print_content(content)
    else:
        parser.print_help()
