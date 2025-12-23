"""
記事要約モジュール
URLから記事を取得してAIで要約
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from core.utils import logger
from ai.gemini_client import GeminiClient


@dataclass
class ArticleSummary:
    """記事要約結果"""
    url: str
    title: str
    summary: str
    key_points: list[str]
    created_at: str


class ArticleSummarizer:
    """
    記事要約
    
    URLから記事を取得し、AIで要約を生成
    """
    
    def __init__(self):
        self.client = httpx.Client(timeout=30, follow_redirects=True)
        self.gemini = GeminiClient()
        logger.info("ArticleSummarizer initialized")
    
    def summarize_url(self, url: str) -> Optional[ArticleSummary]:
        """
        URLから記事を要約
        
        Args:
            url: 記事URL
        
        Returns:
            ArticleSummary or None
        """
        logger.info(f"Summarizing: {url}")
        
        # 記事を取得
        content = self._fetch_article(url)
        if not content:
            return None
        
        title = content.get("title", "")
        text = content.get("text", "")
        
        if not text:
            logger.warning("No content found")
            return None
        
        # AIで要約
        summary_data = self._generate_summary(title, text)
        
        return ArticleSummary(
            url=url,
            title=title,
            summary=summary_data.get("summary", ""),
            key_points=summary_data.get("key_points", []),
            created_at=datetime.now().isoformat()
        )
    
    def summarize_text(self, text: str, title: str = "") -> ArticleSummary:
        """テキストを直接要約"""
        summary_data = self._generate_summary(title, text)
        
        return ArticleSummary(
            url="",
            title=title,
            summary=summary_data.get("summary", ""),
            key_points=summary_data.get("key_points", []),
            created_at=datetime.now().isoformat()
        )
    
    def _fetch_article(self, url: str) -> Optional[dict]:
        """URLから記事を取得"""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # タイトルを取得
            title = ""
            if soup.title:
                title = soup.title.string or ""
            elif soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)
            
            # 本文を取得 (記事タグを優先)
            article = soup.find("article") or soup.find("main") or soup.body
            
            if not article:
                return None
            
            # スクリプト・スタイルを除去
            for tag in article.find_all(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            
            # テキストを抽出
            paragraphs = article.find_all(["p", "h1", "h2", "h3", "li"])
            text = "\n".join([p.get_text(strip=True) for p in paragraphs])
            
            # 長すぎる場合は切り詰め
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            return {"title": title, "text": text}
            
        except Exception as e:
            logger.error(f"Failed to fetch article: {e}")
            return None
    
    def _generate_summary(self, title: str, text: str) -> dict:
        """AIで要約を生成"""
        prompt = f"""
以下の記事を要約してください:

タイトル: {title}

本文:
{text[:5000]}

出力形式（JSON）:
{{
    "summary": "200文字以内の要約",
    "key_points": ["ポイント1", "ポイント2", "ポイント3"]
}}
"""
        
        response = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="記事を簡潔に要約するエキスパートです。",
            max_tokens=500,
            temperature=0.3
        )
        
        # JSONをパース
        import json
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean)
        except json.JSONDecodeError:
            return {"summary": response, "key_points": []}
    
    def batch_summarize(self, urls: list[str]) -> list[ArticleSummary]:
        """複数URLを一括要約"""
        summaries = []
        for url in urls:
            summary = self.summarize_url(url)
            if summary:
                summaries.append(summary)
        return summaries
