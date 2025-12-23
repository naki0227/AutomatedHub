#!/usr/bin/env python3
"""
トレンド分析スクリプト
YouTube, TikTok, Instagramのトレンドを分析
"""
import argparse
from core.utils import print_info, print_success
from analytics.youtube_analyzer import YouTubeAnalyzer
from analytics.pattern_learner import PatternLearner


def analyze_youtube(category: str = "all", limit: int = 20):
    """YouTubeトレンドを分析"""
    print_info(f"YouTube分析: カテゴリ={category}, 件数={limit}")
    
    analyzer = YouTubeAnalyzer()
    videos = analyzer.get_trending_videos(category=category, max_results=limit)
    
    if not videos:
        print("動画が見つかりませんでした")
        return
    
    # 分析
    analysis = analyzer.analyze_trends(videos)
    
    print(f"\n📊 YouTube トレンド分析結果")
    print(f"動画数: {analysis['video_count']}")
    print(f"平均再生数: {analysis['avg_views']:,}")
    print(f"平均エンゲージメント率: {analysis['avg_engagement_rate']:.4f}")
    
    print(f"\n🏷️ 人気タグ TOP 10:")
    for tag, count in analysis.get("popular_tags", [])[:10]:
        print(f"  - {tag} ({count})")
    
    print(f"\n🎬 TOP 5 動画:")
    for video in analysis.get("top_videos", [])[:5]:
        print(f"  - {video['title'][:50]} ({video['views']:,}再生)")
    
    # パターン学習
    learner = PatternLearner()
    learner.learn_from_youtube(analysis, genre=category)
    print_success("パターンを学習しました")


def main():
    parser = argparse.ArgumentParser(description="トレンド分析")
    parser.add_argument(
        "--platform",
        choices=["youtube", "tiktok", "instagram", "all"],
        default="youtube",
        help="分析プラットフォーム"
    )
    parser.add_argument(
        "--category",
        type=str,
        default="all",
        help="YouTubeカテゴリ (gaming, entertainment, education, etc.)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="取得件数"
    )
    
    args = parser.parse_args()
    
    if args.platform in ["youtube", "all"]:
        analyze_youtube(args.category, args.limit)


if __name__ == "__main__":
    main()
