"""
Gemini APIクライアント
テキスト生成、コード生成、コンテンツ分析など
"""
from typing import Optional
import google.generativeai as genai

from core.config import get_config
from core.utils import logger


class GeminiClient:
    """Gemini APIクライアント"""
    
    def __init__(self):
        config = get_config()
        if not config.validate_gemini():
            raise ValueError("GEMINI_API_KEY is not set")
        
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro")
        logger.info("GeminiClient initialized")
    
    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """テキストを生成"""
        try:
            # セーフティ設定（緩め）
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # システム指示がある場合はモデルを再作成
            if system_instruction:
                model = genai.GenerativeModel(
                    "gemini-2.0-flash-exp",
                    system_instruction=system_instruction,
                    safety_settings=safety_settings
                )
            else:
                model = genai.GenerativeModel(
                    "gemini-2.0-flash-exp",
                    safety_settings=safety_settings
                )
            
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            # レスポンスチェック
            if not response.candidates:
                logger.warning("No candidates returned from Gemini")
                return f"[生成できませんでした: {prompt[:50]}...]"
            
            candidate = response.candidates[0]
            if candidate.finish_reason and candidate.finish_reason != 1:
                # 1=STOP（正常終了）、2=SAFETY、等
                logger.warning(f"Gemini finish_reason: {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    logger.warning(f"Safety ratings: {candidate.safety_ratings}")
                return f"[セーフティフィルターでブロック: トピックを変更してください]"
            
            return response.text
        except Exception as e:
            logger.error(f"Gemini text generation failed: {e}")
            return f"[エラー: {str(e)[:100]}]"
    
    def generate_sns_post(
        self,
        topic: str,
        platform: str = "x",
        style: str = "casual",
        source_url: str = "",
        article_content: str = ""
    ) -> dict:
        """SNS投稿用コンテンツを生成"""
        
        platform_limits = {
            "x": 280,
            "instagram": 2200,
            "tiktok": 2200
        }
        char_limit = platform_limits.get(platform, 280)
        
        # プロフィールから口調設定を読み込み
        writing_style = self._load_writing_style()
        
        style_instructions = ""
        if writing_style:
            characteristics = "\n".join([f"- {c}" for c in writing_style.get("characteristics", [])])
            avoid_list = "\n".join([f"- {a}" for a in writing_style.get("avoid", [])])
            examples = "\n".join([f"例: 「{e}」" for e in writing_style.get("example_posts", [])])
            
            style_instructions = f"""
【口調の特徴】
{characteristics}

【避けること】
{avoid_list}

【投稿例】
{examples}
"""
        
        source_instruction = ""
        if source_url:
            source_instruction = f"\n【ソースURL】\n投稿の最後にソースURLを含めてください: {source_url}\n"
        
        # 記事内容がある場合は、実際に読んだ内容に基づいて投稿
        article_instruction = ""
        if article_content:
            article_instruction = f"""
【記事の内容】
以下が実際の記事内容です。この内容を読んで、重要なポイントや面白いと思った点を紹介してください。

{article_content[:2000]}
"""
        
        system_instruction = f"""
あなたは個人開発者として、実際に記事を読んでSNSで紹介します。

【投稿スタイル】
- 記事を実際に読んで、自分の言葉で紹介する
- 記事の中で特に面白かった・役立った点を1つ取り上げる
- 「読んでみたら」「この部分が面白い」「なるほどと思った」など読了感を出す
- 自分の感想や考えを必ず一言添える
- AIっぽい機械的な文章は絶対NG
- 「〜です」「〜ます」ではなく「〜だ」「〜だよね」のカジュアル口調

【例】
- 「読んでみたら、〜〜の部分がなるほどと思った」
- 「この記事の〜〜って考え方、確かにそうだなと」
- 「〜〜について調べてたら発見。特に〜〜が参考になった」

- プラットフォーム: {platform}
- 文字数制限: {char_limit}文字以内
- ハッシュタグは3個以内

{style_instructions}
{article_instruction}
{source_instruction}

出力形式（JSON）:
{{
    "text": "投稿本文（記事を読んだ感想を含む）",
    "hashtags": ["#タグ1", "#タグ2"],
    "image_prompt": "投稿に合う画像のプロンプト（英語）"
}}
"""
        
        if article_content:
            prompt = f"トピック: {topic}\n\n上記の記事内容を読んで、面白いと思った点を紹介する投稿を作成してください。"
        else:
            prompt = f"トピック: {topic}\n\n記事を読んで紹介する感じで投稿を作成してください。"
        
        response = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.8
        )
        
        # JSON解析を試みる
        import json
        try:
            # コードブロックを除去
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            return json.loads(clean_response)
        except json.JSONDecodeError:
            # パース失敗時はそのままテキストとして返す
            return {
                "text": response,
                "hashtags": [],
                "image_prompt": ""
            }
    
    def _load_writing_style(self) -> dict:
        """プロフィールから口調設定を読み込み"""
        import json
        from core.config import get_config
        
        config = get_config()
        profile_path = config.project_root / "profile.json"
        
        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("writing_style", {})
            except:
                pass
        return {}
    
    def summarize_article(self, content: str, max_length: int = 200) -> str:
        """記事を要約"""
        system_instruction = "記事を簡潔に要約してください。"
        prompt = f"以下の記事を{max_length}文字以内で要約:\n\n{content}"
        
        return self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            max_tokens=500,
            temperature=0.3
        )
    
    def analyze_code(self, code: str, context: str = "") -> str:
        """コードをレビュー・分析"""
        system_instruction = """
あなたは経験豊富なソフトウェアエンジニアです。
コードをレビューし、以下の観点で分析してください：
- バグや問題点
- 改善提案
- セキュリティ上の懸念
- パフォーマンス改善点
"""
        prompt = f"コンテキスト: {context}\n\nコード:\n```\n{code}\n```\n\nレビューをお願いします。"
        
        return self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3
        )
