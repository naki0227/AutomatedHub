"""
技術トレンド収集モジュール
Hacker News, Zenn, Qiita の注目記事を収集
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from core.utils import logger
from ai.gemini_client import GeminiClient


@dataclass
class TechArticle:
    """技術記事"""
    title: str
    url: str
    source: str
    score: Optional[int] = None
    summary: Optional[str] = None
    fetched_at: str = ""


class TechTrendFetcher:
    """
    技術トレンド収集
    
    対応ソース:
    - Hacker News (トップ記事)
    - Zenn (トレンド)
    - Qiita (トレンド)
    """
    
    def __init__(self):
        self.client = httpx.Client(timeout=30)
        self.gemini = GeminiClient()
        logger.info("TechTrendFetcher initialized")
    
    def fetch_all(self, limit: int = 10) -> List[TechArticle]:
        """全ソースから記事を収集"""
        articles = []
        
        articles.extend(self.fetch_hackernews(limit))
        articles.extend(self.fetch_zenn(limit))
        articles.extend(self.fetch_qiita(limit))
        
        # スコア順にソート
        articles.sort(key=lambda x: x.score or 0, reverse=True)
        return articles
    
    def fetch_hackernews(self, limit: int = 10) -> List[TechArticle]:
        """Hacker Newsトップ記事を取得"""
        logger.info("Fetching Hacker News...")
        
        try:
            # トップストーリーIDを取得
            response = self.client.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json"
            )
            story_ids = response.json()[:limit]
            
            articles = []
            for story_id in story_ids:
                story_response = self.client.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                )
                story = story_response.json()
                
                if story and story.get("url"):
                    articles.append(TechArticle(
                        title=story.get("title", ""),
                        url=story.get("url", ""),
                        source="hackernews",
                        score=story.get("score", 0),
                        fetched_at=datetime.now().isoformat()
                    ))
            
            logger.info(f"Fetched {len(articles)} articles from Hacker News")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch Hacker News: {e}")
            return []
    
    def fetch_zenn(self, limit: int = 10) -> List[TechArticle]:
        """Zennトレンド記事を取得"""
        logger.info("Fetching Zenn...")
        
        try:
            response = self.client.get(
                f"https://zenn.dev/api/articles?order=daily&count={limit}"
            )
            data = response.json()
            
            articles = []
            for article in data.get("articles", [])[:limit]:
                articles.append(TechArticle(
                    title=article.get("title", ""),
                    url=f"https://zenn.dev{article.get('path', '')}",
                    source="zenn",
                    score=article.get("liked_count", 0),
                    fetched_at=datetime.now().isoformat()
                ))
            
            logger.info(f"Fetched {len(articles)} articles from Zenn")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch Zenn: {e}")
            return []
    
    def fetch_qiita(self, limit: int = 10) -> List[TechArticle]:
        """Qiitaトレンド記事を取得"""
        logger.info("Fetching Qiita...")
        
        try:
            response = self.client.get(
                f"https://qiita.com/api/v2/items?page=1&per_page={limit}&query=stocks:>10"
            )
            data = response.json()
            
            articles = []
            for article in data[:limit]:
                articles.append(TechArticle(
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    source="qiita",
                    score=article.get("likes_count", 0),
                    fetched_at=datetime.now().isoformat()
                ))
            
            logger.info(f"Fetched {len(articles)} articles from Qiita")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch Qiita: {e}")
            return []
    
    def summarize_articles(
        self,
        articles: List[TechArticle],
        max_articles: int = 5
    ) -> str:
        """記事リストを要約"""
        logger.info(f"Summarizing {len(articles)} articles...")
        
        # 記事タイトル一覧
        article_list = "\n".join([
            f"- [{a.source}] {a.title} (スコア: {a.score})"
            for a in articles[:max_articles]
        ])
        
        prompt = f"""
以下の技術記事のトレンドを日本語で簡潔に要約してください：

{article_list}

以下の形式で出力:
1. 今日のトレンド概要（2-3行）
2. 注目トピック（箇条書き）
3. SNS投稿向けの一言コメント
"""
        
        summary = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="技術トレンドを分かりやすく解説するエキスパートです。",
            max_tokens=500,
            temperature=0.5
        )
        
        return summary
    
    def generate_daily_report(self) -> str:
        """日次トレンドレポートを生成"""
        articles = self.fetch_all(limit=10)
        summary = self.summarize_articles(articles)
        
        report = f"""# 技術トレンドレポート
生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## サマリー
{summary}

## 記事一覧
"""
        for article in articles[:10]:
            report += f"- [{article.source}] [{article.title}]({article.url}) (スコア: {article.score})\n"
        
        return report
