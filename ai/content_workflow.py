"""
コンテンツ配信ワークフロー

テキストコンテンツ:
  トレンド → note記事 → X・Instagram投稿

動画コンテンツ:
  素材動画 → 編集 → YouTube・TikTok
"""
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime

from ai.gemini_client import GeminiClient
from core.config import get_config
from core.utils import logger, ensure_dir, get_timestamp


@dataclass
class TextContent:
    """テキストコンテンツ（note/X/Instagram用）"""
    topic: str
    created_at: str
    
    # note記事（メイン）
    note_title: str
    note_content: str
    
    # X投稿（noteから派生）
    x_post: str
    x_hashtags: list
    
    # Instagram投稿（noteから派生）
    instagram_caption: str
    instagram_hashtags: list
    instagram_image_prompt: str


@dataclass
class VideoContent:
    """動画コンテンツ（YouTube/TikTok用）"""
    source_video: str
    edited_at: str
    
    youtube_path: str  # 16:9
    tiktok_path: str   # 9:16
    
    title: str
    description: str
    hashtags: list


class ContentWorkflow:
    """
    コンテンツ配信ワークフロー
    
    テキスト系:
      1. トレンドからトピック取得
      2. note記事を生成
      3. noteからX・Instagram投稿を派生
    
    動画系:
      1. 素材動画を受け取る
      2. YouTube用(16:9)とTikTok用(9:16)に編集
      3. タイトル・説明文を生成
    """
    
    def __init__(self):
        config = get_config()
        self.gemini = GeminiClient()
        self.output_dir = config.project_root / "sns" / "workflow_output"
        ensure_dir(self.output_dir)
        
        # プロフィール読み込み
        self.profile = self._load_profile(config.project_root / "profile.json")
        
        logger.info("ContentWorkflow initialized")
    
    def _load_profile(self, path: Path) -> dict:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def create_text_content(self, topic: Optional[str] = None) -> TextContent:
        """
        テキストコンテンツを生成
        
        1. トピックがなければトレンドから取得
        2. note記事を生成
        3. X/Instagram投稿を派生
        """
        # トピック取得
        if not topic:
            topic = self._get_trending_topic()
            if not topic:
                raise ValueError("トピックが見つかりません")
        
        logger.info(f"Creating text content for: {topic}")
        
        # Step 1: note記事を生成
        note_content = self._generate_note(topic)
        
        # Step 2: noteからX/Instagram投稿を派生
        derived = self._derive_posts(note_content["title"], note_content["content"])
        
        content = TextContent(
            topic=topic,
            created_at=datetime.now().isoformat(),
            note_title=note_content["title"],
            note_content=note_content["content"],
            x_post=derived["x_post"],
            x_hashtags=derived["x_hashtags"],
            instagram_caption=derived["instagram_caption"],
            instagram_hashtags=derived["instagram_hashtags"],
            instagram_image_prompt=derived["instagram_image_prompt"]
        )
        
        # 保存
        self._save_text_content(content)
        
        return content
    
    def create_video_content(self, video_path: str) -> VideoContent:
        """
        動画コンテンツを生成
        
        1. YouTube用(16:9)に編集
        2. TikTok用(9:16)に編集
        3. タイトル・説明文を生成
        """
        from media.video_editor import VideoEditor
        
        logger.info(f"Creating video content from: {video_path}")
        
        editor = VideoEditor()
        outputs = editor.edit_video(Path(video_path), output_format="both")
        
        youtube_path = ""
        tiktok_path = ""
        
        for out in outputs:
            if "16x9" in str(out):
                youtube_path = str(out)
            elif "9x16" in str(out):
                tiktok_path = str(out)
        
        # タイトル・説明文を生成
        video_name = Path(video_path).stem
        metadata = self._generate_video_metadata(video_name)
        
        content = VideoContent(
            source_video=video_path,
            edited_at=datetime.now().isoformat(),
            youtube_path=youtube_path,
            tiktok_path=tiktok_path,
            title=metadata["title"],
            description=metadata["description"],
            hashtags=metadata["hashtags"]
        )
        
        # 保存
        self._save_video_content(content)
        
        return content
    
    def _get_trending_topic(self) -> Optional[str]:
        """トレンドからトピックを取得"""
        from research.tech_trend_fetcher import TechTrendFetcher
        
        fetcher = TechTrendFetcher()
        articles = fetcher.fetch_all(limit=5)
        
        if not articles:
            return None
        
        # 関連キーワードを優先
        keywords = ["AI", "教育", "学習", "アプリ", "開発"]
        
        for article in articles:
            title = article.get("title", "")
            for keyword in keywords:
                if keyword.lower() in title.lower():
                    return title
        
        return articles[0].get("title", "")
    
    def _generate_note(self, topic: str) -> dict:
        """note記事を生成"""
        writing_style = self.profile.get("writing_style", {})
        
        style_guide = ""
        if writing_style:
            characteristics = "\n".join([f"- {c}" for c in writing_style.get("characteristics", [])])
            avoid = "\n".join([f"- {a}" for a in writing_style.get("avoid", [])])
            style_guide = f"【口調】\n{characteristics}\n\n【避けること】\n{avoid}"
        
        system_instruction = f"""
あなたは個人開発者のブログ記事を書きます。
note.comに投稿する記事を作成してください。

{style_guide}

【構成】
- 導入（読者の興味を引く、100字程度）
- 本文（具体的な内容、500-800字）
- まとめ（100字程度）

出力形式（JSON）:
{{
    "title": "記事タイトル",
    "content": "記事本文（Markdown形式）"
}}
"""
        
        response = self.gemini.generate_text(
            prompt=f"トピック: {topic}\n\nnote記事を作成してください。",
            system_instruction=system_instruction,
            max_tokens=2000,
            temperature=0.7
        )
        
        return self._parse_json(response, {"title": topic, "content": ""})
    
    def _derive_posts(self, note_title: str, note_content: str) -> dict:
        """note記事からX/Instagram投稿を派生"""
        writing_style = self.profile.get("writing_style", {})
        
        style_guide = ""
        if writing_style:
            avoid = "\n".join([f"- {a}" for a in writing_style.get("avoid", [])])
            style_guide = f"【避けること】\n{avoid}"
        
        system_instruction = f"""
以下のnote記事から、X（Twitter）とInstagram用の投稿を作成してください。

{style_guide}

【X投稿のルール】
- 280字以内
- 記事への誘導（note読んでみて的な）
- ハッシュタグは3個以内

【Instagram投稿のルール】
- 記事の要点を伝える
- ビジュアルを想起させる
- ハッシュタグは5個程度

出力形式（JSON）:
{{
    "x_post": "X投稿本文",
    "x_hashtags": ["#タグ1", "#タグ2"],
    "instagram_caption": "Instagramキャプション",
    "instagram_hashtags": ["#タグ1", "#タグ2"],
    "instagram_image_prompt": "投稿画像のプロンプト（英語）"
}}
"""
        
        prompt = f"""
note記事タイトル: {note_title}

note記事本文:
{note_content[:1000]}

この記事からX/Instagram投稿を作成してください。
"""
        
        response = self.gemini.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            max_tokens=1000,
            temperature=0.7
        )
        
        return self._parse_json(response, {
            "x_post": "",
            "x_hashtags": [],
            "instagram_caption": "",
            "instagram_hashtags": [],
            "instagram_image_prompt": ""
        })
    
    def _generate_video_metadata(self, video_name: str) -> dict:
        """動画のタイトル・説明文を生成"""
        system_instruction = """
動画のタイトルと説明文を作成してください。
YouTube/TikTok両方で使えるようにしてください。

出力形式（JSON）:
{
    "title": "動画タイトル",
    "description": "動画の説明文（100字程度）",
    "hashtags": ["#タグ1", "#タグ2"]
}
"""
        
        response = self.gemini.generate_text(
            prompt=f"動画ファイル名: {video_name}\n\nこの動画のメタデータを作成してください。",
            system_instruction=system_instruction,
            max_tokens=500,
            temperature=0.7
        )
        
        return self._parse_json(response, {
            "title": video_name,
            "description": "",
            "hashtags": []
        })
    
    def _parse_json(self, response: str, default: dict) -> dict:
        """JSONをパース"""
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean)
        except:
            return default
    
    def _save_text_content(self, content: TextContent):
        """テキストコンテンツを保存"""
        timestamp = get_timestamp()
        path = self.output_dir / f"text_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(content), f, ensure_ascii=False, indent=2)
        logger.info(f"Text content saved: {path}")
    
    def _save_video_content(self, content: VideoContent):
        """動画コンテンツを保存"""
        timestamp = get_timestamp()
        path = self.output_dir / f"video_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(content), f, ensure_ascii=False, indent=2)
        logger.info(f"Video content saved: {path}")


def print_text_content(content: TextContent):
    """テキストコンテンツを表示"""
    print("=" * 60)
    print(f"トピック: {content.topic}")
    print("=" * 60)
    
    print("\n📖 note記事")
    print(f"タイトル: {content.note_title}")
    print(f"本文:\n{content.note_content[:400]}...")
    
    print("\n" + "-" * 40)
    print("↓ noteから派生 ↓")
    print("-" * 40)
    
    print("\n🐦 X投稿")
    print(content.x_post)
    print(f"ハッシュタグ: {' '.join(content.x_hashtags)}")
    
    print("\n📸 Instagram")
    print(content.instagram_caption)
    print(f"画像アイデア: {content.instagram_image_prompt}")


def print_video_content(content: VideoContent):
    """動画コンテンツを表示"""
    print("=" * 60)
    print(f"元動画: {content.source_video}")
    print("=" * 60)
    
    print(f"\n📺 YouTube用: {content.youtube_path}")
    print(f"🎵 TikTok用: {content.tiktok_path}")
    
    print(f"\nタイトル: {content.title}")
    print(f"説明: {content.description}")
    print(f"ハッシュタグ: {' '.join(content.hashtags)}")


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="コンテンツ配信ワークフロー")
    parser.add_argument("--text", action="store_true", help="テキストコンテンツ生成（トレンドから）")
    parser.add_argument("--topic", type=str, help="トピック指定")
    parser.add_argument("--video", type=str, help="動画コンテンツ生成（動画パス指定）")
    
    args = parser.parse_args()
    
    workflow = ContentWorkflow()
    
    if args.text or args.topic:
        content = workflow.create_text_content(args.topic)
        print_text_content(content)
    
    elif args.video:
        content = workflow.create_video_content(args.video)
        print_video_content(content)
    
    else:
        parser.print_help()
