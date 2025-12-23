"""
拡張コンテンツ配信ワークフロー

note: 無料版 + 有料版
X: 画像付き投稿 → リプ欄にnote URL
Instagram: 画像付き投稿
"""
import json
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, List
from datetime import datetime

from ai.gemini_client import GeminiClient
from core.config import get_config
from core.utils import logger, ensure_dir, get_timestamp


@dataclass
class NoteArticle:
    """note記事（無料版 + 有料版）"""
    title: str
    
    # 無料版（導入 + 概要）- 2000字目安
    free_content: str
    
    # 有料版（詳細解説 + 実践）- 10000字目安
    paid_content: str
    
    # タグ
    tags: List[str] = field(default_factory=list)
    
    # ヘッダー画像
    header_image_prompt: str = ""
    header_image_path: str = ""
    
    # 参考ソース
    sources: List[str] = field(default_factory=list)


@dataclass
class XPost:
    """X投稿（本文 + リプ欄）"""
    main_text: str          # メイン投稿（画像/ソースURL付き）
    hashtags: List[str]
    image_prompt: str       # 投稿画像のプロンプト
    source_url: str         # ソースURL（本文に含める）
    reply_text: str         # リプ欄（noteへの誘導）
    note_url: str           # noteのURL（リプ欄用）
    campaign_url: str       # キャンペーンURL（リプ欄用）


@dataclass 
class InstagramPost:
    """Instagram投稿"""
    caption: str
    hashtags: List[str]
    image_prompt: str
    source_url: str


@dataclass
class EnhancedTextContent:
    """拡張テキストコンテンツ"""
    topic: str
    created_at: str
    
    # note記事（無料/有料）
    note: NoteArticle
    
    # X投稿（メイン + リプ欄）
    x_post: XPost
    
    # Instagram投稿
    instagram: InstagramPost


class EnhancedContentWorkflow:
    """
    拡張コンテンツ配信ワークフロー
    
    1. トレンドからトピック取得
    2. note記事を生成（無料版 + 有料版）
    3. X投稿を生成（画像+ソースURL → リプ欄にnote URL）
    4. Instagram投稿を生成（画像付き）
    """
    
    def __init__(self):
        config = get_config()
        self.gemini = GeminiClient()
        self.output_dir = config.project_root / "sns" / "enhanced_output"
        ensure_dir(self.output_dir)
        
        self.profile = self._load_profile(config.project_root / "profile.json")
        logger.info("EnhancedContentWorkflow initialized")
    
    def _load_profile(self, path: Path) -> dict:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def create_content(self, topic: Optional[str] = None, source_url: str = "") -> EnhancedTextContent:
        """
        拡張コンテンツを生成
        
        Args:
            topic: トピック（省略時はトレンドから）
            source_url: ソースURL（参考リンク）
        """
        if not topic:
            topic, source_url = self._get_trending_topic_with_url()
            if not topic:
                raise ValueError("トピックが見つかりません")
        
        logger.info(f"Creating enhanced content: {topic}")
        
        # Step 1: note記事（無料/有料）を生成
        note = self._generate_note_article(topic, source_url)
        
        # Step 2: X投稿を生成（メイン + リプ欄）
        x_post = self._generate_x_post(note.title, note.free_content, source_url)
        
        # Step 3: Instagram投稿を生成
        instagram = self._generate_instagram_post(note.title, note.free_content, source_url)
        
        content = EnhancedTextContent(
            topic=topic,
            created_at=datetime.now().isoformat(),
            note=note,
            x_post=x_post,
            instagram=instagram
        )
        
        self._save_content(content)
        return content
    
    def _get_trending_topic_with_url(self) -> tuple:
        """トレンドからトピックとURLを取得"""
        from research.tech_trend_fetcher import TechTrendFetcher
        
        fetcher = TechTrendFetcher()
        articles = fetcher.fetch_all(limit=10)
        
        if not articles:
            return None, ""
        
        # Zenn/Qiitaのみにフィルタリング（Hacker Newsを除外）
        tech_articles = [a for a in articles if a.source in ["zenn", "qiita"]]
        
        if not tech_articles:
            # フォールバック: 全記事からキーワードマッチ
            tech_articles = articles
        
        keywords = ["AI", "教育", "学習", "アプリ", "開発", "Flutter", "Python", "個人開発", "自動化", "Gemini", "ChatGPT", "LLM"]
        
        for article in tech_articles:
            title = article.title
            url = article.url
            for keyword in keywords:
                if keyword.lower() in title.lower():
                    return title, url
        
        # マッチしなければ最初のZenn/Qiita記事
        first = tech_articles[0]
        return first.title, first.url
    
    def _generate_note_article(self, topic: str, source_url: str) -> NoteArticle:
        """note記事（無料版2000字 + 有料版10000字）を生成"""
        writing_style = self.profile.get("writing_style", {})
        
        style_guide = ""
        if writing_style:
            characteristics = "\n".join([f"- {c}" for c in writing_style.get("characteristics", [])])
            avoid = "\n".join([f"- {a}" for a in writing_style.get("avoid", [])])
            style_guide = f"【口調】\n{characteristics}\n\n【避けること】\n{avoid}"
        
        # Step 1: タイトルとタグを生成
        logger.info("Generating note title and tags...")
        title, tags = self._generate_note_title_and_tags(topic, source_url)
        
        # Step 2: 無料版生成（2000字）
        logger.info("Generating note free content (2000 chars)...")
        free_content = self._generate_note_free(title, topic, source_url, style_guide)
        
        # Step 3: 有料版生成（10000字を複数パートに分割）
        logger.info("Generating note paid content (10000 chars)...")
        paid_content = self._generate_note_paid_extended(title, topic, source_url, style_guide)
        
        # Step 4: ヘッダー画像プロンプト生成
        logger.info("Generating header image prompt...")
        header_prompt = self._generate_header_image_prompt(title, topic)
        
        return NoteArticle(
            title=title,
            free_content=free_content,
            paid_content=paid_content,
            tags=tags,
            header_image_prompt=header_prompt,
            sources=[source_url] if source_url else []
        )
    
    def _generate_note_title_and_tags(self, topic: str, source_url: str) -> tuple:
        """タイトルとタグを生成"""
        system_instruction = """
あなたはnote.comで人気の記事を書く個人開発者です。
記事のタイトルと5つのタグを生成してください。

【noteで伸びるタイトルの特徴】
- 数字を使う（例: 「3つの理由」「1ヶ月でできる」）
- 読者の課題解決を示唆する
- 具体的でわかりやすい
- 30〜50文字程度

【タグのルール】
- 5つのタグを選定
- 技術系タグ（例: #AI, #プログラミング, #個人開発）
- トレンドタグ（例: #ChatGPT, #副業）
- 一般タグ（例: #仕事術, #生産性向上）

出力形式（JSON）:
{
    "title": "記事タイトル",
    "tags": ["#タグ1", "#タグ2", "#タグ3", "#タグ4", "#タグ5"]
}
"""
        response = self.gemini.generate_text(
            prompt=f"トピック: {topic}\n参考: {source_url}\n\nタイトルとタグをJSON形式で出力してください。",
            system_instruction=system_instruction,
            max_tokens=300,
            temperature=0.7
        )
        data = self._parse_json(response, {"title": topic, "tags": []})
        return data["title"], data.get("tags", [])
    
    def _generate_note_free(self, title: str, topic: str, source_url: str, style_guide: str) -> str:
        """note無料版を生成（2000字）"""
        system_instruction = f"""
あなたはnote.comで人気の記事を書く個人開発者です。
無料で読める導入部分（2000文字程度）を作成してください。

【noteで伸びる記事の書き方】
1. 冒頭で読者の悩みや課題に共感する
2. 自分の経験談を交えて親しみやすく
3. 具体的な数字やエピソードを入れる
4. 有料部分への期待を自然に高める
5. 見出し（##）を使って読みやすく構成

{style_guide}

【無料版の構成（2000字目安）】
## 導入（この記事を読むべき人）
- 読者の悩みに共感
- この記事で得られること

## 私の経験談
- 具体的なエピソード
- 失敗談→気づき

## 結論の予告
- 有料版で解説する内容の概要
- 「続きを読むとこうなれる」という誘導

本文のみをMarkdown形式で出力してください。
"""
        response = self.gemini.generate_text(
            prompt=f"タイトル: {title}\nトピック: {topic}\n参考: {source_url}\n\n2000文字程度の無料版本文を出力してください。",
            system_instruction=system_instruction,
            max_tokens=4000,
            temperature=0.7
        )
        return response.strip()
    
    def _generate_note_paid_extended(self, title: str, topic: str, source_url: str, style_guide: str) -> str:
        """note有料版を生成（6000字を3パートで）"""
        
        # パート構成を先に決める
        outline = self._generate_paid_outline(title, topic)
        
        # 各パートを個別に生成（3パートに削減）
        parts = []
        for i, section in enumerate(outline[:3], 1):  # 3パートに削減
            logger.info(f"Generating paid content part {i}/3: {section[:30]}...")
            part_content = self._generate_paid_section(title, topic, source_url, section, style_guide, i)
            parts.append(part_content)
        
        # まとめを生成
        logger.info("Generating paid content conclusion...")
        conclusion = self._generate_paid_conclusion(title, topic, style_guide)
        parts.append(conclusion)
        
        return "\n\n---\n\n".join(parts)
    
    def _generate_paid_outline(self, title: str, topic: str) -> list:
        """有料版の章構成を生成"""
        system_instruction = """
以下の記事の有料版の章立てを5つ作成してください。
購入者が「買ってよかった」と思える価値ある構成にしてください。

【有料版で期待される内容】
1. 具体的な手順やノウハウ
2. すぐに使えるテンプレートやコード
3. 失敗しないための注意点
4. 上級者向けのテクニック
5. 筆者だけが知る秘訣

出力形式（JSONの配列）:
["章1のタイトル", "章2のタイトル", "章3のタイトル", "章4のタイトル", "章5のタイトル"]
"""
        response = self.gemini.generate_text(
            prompt=f"タイトル: {title}\nトピック: {topic}\n\n章立てをJSON配列で出力してください。",
            system_instruction=system_instruction,
            max_tokens=500,
            temperature=0.7
        )
        return self._parse_json(response, ["基礎知識", "実践手順", "応用テクニック", "よくある失敗", "まとめ"])
    
    def _generate_paid_section(self, title: str, topic: str, source_url: str, section: str, style_guide: str, part_num: int) -> str:
        """有料版の1セクションを生成（2000字程度）"""
        system_instruction = f"""
あなたはnote.comで有料記事を書く個人開発者です。
以下の章の内容を詳しく解説してください（2000文字程度）。

【有料記事の価値を高める書き方】
- 具体的な手順を示す
- コード例やテンプレートを含める
- 自分だけが知るノウハウを惜しみなく共有
- 「これだけで○○できる」と言えるレベルの詳しさ

{style_guide}

本文のみをMarkdown形式で出力してください。
"""
        response = self.gemini.generate_text(
            prompt=f"タイトル: {title}\nトピック: {topic}\n参考: {source_url}\n\n== 有料版 パート{part_num}: {section} ==\n\nこの章を2000文字程度で詳しく解説してください。",
            system_instruction=system_instruction,
            max_tokens=4000,
            temperature=0.7
        )
        return f"## {section}\n\n{response.strip()}"
    
    def _generate_paid_conclusion(self, title: str, topic: str, style_guide: str) -> str:
        """有料版のまとめを生成"""
        system_instruction = f"""
有料記事のまとめを書いてください（1000文字程度）。

{style_guide}

【まとめに含める内容】
- 記事全体の要点
- すぐに実践できる最初のステップ
- 読者への励ましのメッセージ
- 質問・フィードバックへの誘導

本文のみをMarkdown形式で出力してください。
"""
        response = self.gemini.generate_text(
            prompt=f"タイトル: {title}\nトピック: {topic}\n\nまとめを1000文字程度で出力してください。",
            system_instruction=system_instruction,
            max_tokens=2000,
            temperature=0.7
        )
        return f"## まとめ\n\n{response.strip()}"
    
    def _generate_header_image_prompt(self, title: str, topic: str) -> str:
        """ヘッダー画像用のプロンプトを生成"""
        system_instruction = """
note記事のヘッダー画像を生成するためのプロンプトを作成してください。

【ルール】
- 英語で出力
- 写実的でプロフェッショナルなイメージ
- シンプルで読みやすい
- テキストは含めない（画像のみ）
- 16:9のアスペクト比を想定

プロンプトのみを1行で出力してください。
"""
        response = self.gemini.generate_text(
            prompt=f"タイトル: {title}\nトピック: {topic}\n\nヘッダー画像のプロンプトを英語で出力してください。",
            system_instruction=system_instruction,
            max_tokens=200,
            temperature=0.7
        )
        return response.strip()
    
    def _generate_x_post(self, note_title: str, note_content: str, source_url: str) -> XPost:
        """X投稿（メイン + リプ欄）を生成"""
        writing_style = self.profile.get("writing_style", {})
        avoid = "\n".join([f"- {a}" for a in writing_style.get("avoid", [])])
        
        system_instruction = f"""
X（Twitter）用の投稿を作成してください。

【避けること】
{avoid}

【メイン投稿】
- 記事の内容を要約（画像を添える前提）
- ソースURLを含める
- 200字以内
- ハッシュタグ3個以内

【リプ欄（自分への返信）】
- noteへの誘導
- 「詳しくはnoteで書いた」的な自然な誘導
- 100字以内

出力形式（JSON）:
{{
    "main_text": "メイン投稿本文（ソースURL含む）",
    "hashtags": ["#タグ1", "#タグ2"],
    "image_prompt": "投稿画像のプロンプト（英語）",
    "reply_text": "リプ欄の本文（noteへの誘導）"
}}
"""
        
        prompt = f"""
note記事タイトル: {note_title}
note記事内容: {note_content[:500]}
ソースURL: {source_url}

X投稿を作成してください。
"""
        
        response = self.gemini.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            max_tokens=800,
            temperature=0.7
        )
        
        data = self._parse_json(response, {
            "main_text": "",
            "hashtags": [],
            "image_prompt": "",
            "reply_text": ""
        })
        
        # キャンペーンURL取得
        campaign_url = self._get_campaign_url()
        
        return XPost(
            main_text=data["main_text"],
            hashtags=data["hashtags"],
            image_prompt=data["image_prompt"],
            source_url=source_url,
            reply_text=data["reply_text"],
            note_url="",  # 投稿後に設定
            campaign_url=campaign_url
        )
    
    def _generate_instagram_post(self, note_title: str, note_content: str, source_url: str) -> InstagramPost:
        """Instagram投稿を生成"""
        writing_style = self.profile.get("writing_style", {})
        avoid = "\n".join([f"- {a}" for a in writing_style.get("avoid", [])])
        
        system_instruction = f"""
Instagram用の投稿を作成してください。

【避けること】
{avoid}

【キャプション】
- 記事の要点を分かりやすく
- ビジュアルを想起させる
- ハッシュタグは5個程度
- ソースURLを含める

出力形式（JSON）:
{{
    "caption": "キャプション本文",
    "hashtags": ["#タグ1", "#タグ2"],
    "image_prompt": "投稿画像のプロンプト（英語）"
}}
"""
        
        prompt = f"""
note記事タイトル: {note_title}
note記事内容: {note_content[:500]}
ソースURL: {source_url}

Instagram投稿を作成してください。
"""
        
        response = self.gemini.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            max_tokens=800,
            temperature=0.7
        )
        
        data = self._parse_json(response, {
            "caption": "",
            "hashtags": [],
            "image_prompt": ""
        })
        
        return InstagramPost(
            caption=data["caption"],
            hashtags=data["hashtags"],
            image_prompt=data["image_prompt"],
            source_url=source_url
        )
    
    def _parse_json(self, response: str, default: dict) -> dict:
        try:
            clean = response.strip()
            
            # コードブロックの処理
            if "```json" in clean:
                parts = clean.split("```json")
                if len(parts) > 1:
                    clean = parts[1].split("```")[0]
            elif "```" in clean:
                parts = clean.split("```")
                if len(parts) > 1:
                    clean = parts[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                    clean = clean.split("```")[0]
            
            clean = clean.strip()
            
            # JSON解析
            result = json.loads(clean)
            return result
            
        except Exception as e:
            logger.error(f"JSON parse failed: {e}")
            logger.error(f"Response: {response[:500]}...")
            return default
    
    def _get_campaign_url(self) -> str:
        """キャンペーンURLを取得（日付に応じて切り替え）"""
        campaign = self.profile.get("campaign", {})
        
        if not campaign.get("active", False):
            return ""
        
        if not campaign.get("include_in_reply", False):
            return ""
        
        from datetime import date
        
        start_date = campaign.get("start_date", "")
        end_date = campaign.get("end_date", "")
        preview_url = campaign.get("preview_url", "")
        live_url = campaign.get("live_url", "")
        
        today = date.today().isoformat()
        
        # キャンペーン終了後
        if end_date and today > end_date:
            return ""
        
        # キャンペーン開始後
        if start_date and today >= start_date:
            return live_url if live_url else preview_url
        
        # キャンペーン開始前（プレビューURL）
        return preview_url
    
    def _save_content(self, content: EnhancedTextContent):
        """コンテンツを保存"""
        timestamp = get_timestamp()
        path = self.output_dir / f"enhanced_{timestamp}.json"
        
        data = {
            "topic": content.topic,
            "created_at": content.created_at,
            "note": asdict(content.note),
            "x_post": asdict(content.x_post),
            "instagram": asdict(content.instagram)
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Enhanced content saved: {path}")


def print_enhanced_content(content: EnhancedTextContent):
    """拡張コンテンツを表示"""
    print("=" * 70)
    print(f"トピック: {content.topic}")
    print("=" * 70)
    
    print("\n📖 note記事")
    print(f"タイトル: {content.note.title}")
    print(f"\n【無料版】")
    print(content.note.free_content[:300] + "...")
    print(f"\n【有料版】")
    print(content.note.paid_content[:300] + "...")
    
    print("\n" + "-" * 50)
    print("🐦 X投稿")
    print("-" * 50)
    print(f"\n【メイン投稿】")
    print(content.x_post.main_text)
    print(f"ハッシュタグ: {' '.join(content.x_post.hashtags)}")
    print(f"ソースURL: {content.x_post.source_url}")
    print(f"画像アイデア: {content.x_post.image_prompt}")
    print(f"\n【リプ欄（noteへ誘導）】")
    print(content.x_post.reply_text)
    if content.x_post.campaign_url:
        print(f"\n【リプ欄（キャンペーン告知）】")
        print(f"キャンペーンURL: {content.x_post.campaign_url}")
    
    print("\n" + "-" * 50)
    print("📸 Instagram投稿")
    print("-" * 50)
    print(content.instagram.caption)
    print(f"ハッシュタグ: {' '.join(content.instagram.hashtags)}")
    print(f"画像アイデア: {content.instagram.image_prompt}")


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="拡張コンテンツ配信")
    parser.add_argument("--topic", type=str, help="トピック")
    parser.add_argument("--source", type=str, default="", help="ソースURL")
    
    args = parser.parse_args()
    
    workflow = EnhancedContentWorkflow()
    content = workflow.create_content(args.topic, args.source)
    print_enhanced_content(content)
