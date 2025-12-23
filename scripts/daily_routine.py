#!/usr/bin/env python3
"""
日次ルーティン実行スクリプト
朝: トレンド収集 → 昼: コンテンツ生成・投稿 → 夜: 開発サポート
"""
import argparse
from datetime import datetime

from core.utils import logger, print_success, print_info
from research.tech_trend_fetcher import TechTrendFetcher
from research.competitor_watcher import CompetitorWatcher
from analytics.youtube_analyzer import YouTubeAnalyzer
from ai.content_generator import ContentGenerator
from sns.x_client import XClient
from sns.post_scheduler import PostScheduler
from notifications.aggregator import NotificationAggregator


def fetch_article_content(url: str) -> str:
    """記事URLから内容を取得"""
    import httpx
    from bs4 import BeautifulSoup
    
    try:
        response = httpx.get(url, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 不要な要素を削除
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        # 記事本文を取得（一般的なセレクタを試す）
        content = ""
        
        # Zenn
        if "zenn.dev" in url:
            article = soup.select_one("article")
            if article:
                content = article.get_text(separator="\n", strip=True)
        # Qiita
        elif "qiita.com" in url:
            article = soup.select_one(".it-MdContent")
            if article:
                content = article.get_text(separator="\n", strip=True)
        # 一般的なセレクタ
        else:
            for selector in ["article", "main", ".content", "#content", ".post"]:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text(separator="\n", strip=True)
                    break
        
        # 取得できなければbody全体
        if not content:
            body = soup.find("body")
            if body:
                content = body.get_text(separator="\n", strip=True)
        
        # 長すぎる場合は切り詰め
        if len(content) > 3000:
            content = content[:3000] + "..."
        
        return content
        
    except Exception as e:
        logger.warning(f"Failed to fetch article: {e}")
        return ""


def morning_routine():
    """朝のルーティン: トレンドリサーチ + 5トピック保存"""
    import json
    from pathlib import Path
    
    print_info("🌅 朝のルーティン開始")
    
    # 技術トレンド収集
    print_info("技術トレンドを収集中...")
    fetcher = TechTrendFetcher()
    articles = fetcher.fetch_all(limit=15)
    
    # Zenn/Qiitaを優先
    priority_sources = ["zenn", "qiita"]
    sorted_articles = sorted(
        articles,
        key=lambda a: 0 if a.source in priority_sources else 1
    )
    
    # 5つの注目トピックを選定（内容が取得できるもの）
    selected_topics = []
    print_info("注目トピックを選定中...")
    
    for article in sorted_articles:
        if len(selected_topics) >= 5:
            break
        
        content = fetch_article_content(article.url)
        if content and len(content) > 200 and "javascript" not in content.lower():
            selected_topics.append({
                "title": article.title,
                "url": article.url,
                "source": article.source,
                "content": content[:2000]  # 保存用に短縮
            })
            print_info(f"  ✓ [{article.source}] {article.title[:40]}...")
        else:
            print_info(f"  ✗ スキップ: {article.source}")
    
    # 保存
    topics_file = Path("sns/daily_topics.json")
    with open(topics_file, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "topics": selected_topics
        }, f, ensure_ascii=False, indent=2)
    
    print_info(f"📋 {len(selected_topics)}件のトピックを保存: {topics_file}")
    
    # サマリー表示
    print("\n" + "=" * 50)
    print("📰 今日の注目トピック")
    print("=" * 50)
    for i, t in enumerate(selected_topics, 1):
        print(f"{i}. [{t['source']}] {t['title']}")
    print("=" * 50)
    
    print_success("朝のルーティン完了")


def afternoon_routine(topic: str = None, dry_run: bool = True):
    """昼のルーティン: 朝に保存したトピックから投稿を生成"""
    import json
    from pathlib import Path
    
    print_info("☀️ 昼のルーティン開始")
    
    topics_file = Path("sns/daily_topics.json")
    
    # 朝に保存したトピックを読み込み
    if not topics_file.exists():
        print_info("⚠️ 朝のトピックが保存されていません。トレンドから取得します。")
        morning_routine()  # 朝ルーティンを実行
    
    try:
        with open(topics_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print_info(f"トピック読み込み失敗: {e}")
        return
    
    topics = data.get("topics", [])
    if not topics:
        print_info("⚠️ トピックがありません")
        return
    
    print_info(f"📋 {len(topics)}件のトピックから投稿を生成します")
    print("=" * 50)
    
    generator = ContentGenerator()
    scheduler = PostScheduler()
    generated_posts = []
    
    for i, t in enumerate(topics, 1):
        print_info(f"\n[{i}/{len(topics)}] {t['title'][:40]}...")
        
        try:
            # X用コンテンツ生成
            content = generator.generate(
                topic=t["title"],
                platform="x",
                include_image=False,
                source_url=t["url"],
                article_content=t.get("content", "")
            )
            
            print(f"📝 生成された投稿:\n{content.full_text()}\n")
            
            if not dry_run:
                # 実際に投稿
                x_client = XClient()
                result = x_client.post(content.full_text())
                if result.success:
                    print_success(f"投稿完了: {result.url}")
                else:
                    logger.error(f"投稿失敗: {result.error}")
            else:
                # 下書きとして保存
                draft_path = scheduler.save_draft(
                    platform="x",
                    text=content.text,
                    hashtags=content.hashtags,
                    source_url=t["url"]
                )
                generated_posts.append({
                    "topic": t["title"],
                    "draft_path": str(draft_path)
                })
                print_info(f"下書き保存: {draft_path}")
                
        except Exception as e:
            logger.error(f"エラー: {e}")
            continue
        
        print("-" * 50)
    
    print("\n" + "=" * 50)
    print(f"✅ {len(generated_posts)}/{len(topics)}件の投稿を生成しました")
    if dry_run:
        print("（ドライラン: 下書き保存のみ）")
    print("=" * 50)
    
    print_success("昼のルーティン完了")


def evening_routine():
    """夜のルーティン: 開発サポート"""
    print_info("🌙 夜のルーティン開始")
    
    # 通知集約
    print_info("通知を集約中...")
    aggregator = NotificationAggregator()
    notifications = aggregator.aggregate_all()
    
    high_priority = [n for n in notifications if n.priority == "high"]
    if high_priority:
        print_info(f"🔴 重要な通知が {len(high_priority)} 件あります:")
        for n in high_priority[:5]:
            print(f"  - [{n.source}] {n.title}")
    
    print_success("夜のルーティン完了")


def full_routine(topic: str = None, dry_run: bool = True):
    """全ルーティン実行"""
    print_info(f"🚀 全ルーティン開始 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    
    morning_routine()
    afternoon_routine(topic, dry_run)
    evening_routine()
    
    print_success("✅ 全ルーティン完了")


def main():
    parser = argparse.ArgumentParser(description="日次ルーティン実行")
    parser.add_argument(
        "routine",
        choices=["morning", "afternoon", "evening", "all"],
        default="all",
        nargs="?",
        help="実行するルーティン"
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="投稿トピック（昼のルーティン用）"
    )
    parser.add_argument(
        "--post",
        action="store_true",
        help="実際に投稿する（デフォルトはドライラン）"
    )
    
    args = parser.parse_args()
    
    if args.routine == "morning":
        morning_routine()
    elif args.routine == "afternoon":
        afternoon_routine(args.topic, not args.post)
    elif args.routine == "evening":
        evening_routine()
    else:
        full_routine(args.topic, not args.post)


if __name__ == "__main__":
    main()
