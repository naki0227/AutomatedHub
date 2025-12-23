#!/usr/bin/env python3
"""
コンテンツ生成スクリプト
AIでSNS投稿用コンテンツを生成
"""
import argparse
from core.utils import print_info, print_success
from ai.content_generator import ContentGenerator
from sns.post_scheduler import PostScheduler


def generate_content(
    topic: str,
    platform: str = "x",
    style: str = "casual",
    include_image: bool = True,
    save_draft: bool = True
):
    """コンテンツを生成"""
    print_info(f"コンテンツ生成: {topic}")
    print_info(f"プラットフォーム: {platform}, スタイル: {style}")
    
    generator = ContentGenerator()
    content = generator.generate(
        topic=topic,
        platform=platform,
        style=style,
        include_image=include_image
    )
    
    print(f"\n📝 生成されたコンテンツ:")
    print("-" * 40)
    print(content.text)
    print("-" * 40)
    print(f"ハッシュタグ: {' '.join(content.hashtags)}")
    
    if content.image_path:
        print(f"🖼️ 画像: {content.image_path}")
    
    if save_draft:
        scheduler = PostScheduler()
        draft_path = scheduler.save_draft(
            platform=platform,
            text=content.text,
            hashtags=content.hashtags,
            image_path=content.image_path
        )
        print_success(f"下書き保存: {draft_path}")
    
    return content


def main():
    parser = argparse.ArgumentParser(description="コンテンツ生成")
    parser.add_argument("--topic", type=str, required=True, help="投稿トピック")
    parser.add_argument(
        "--platform",
        choices=["x", "instagram", "tiktok"],
        default="x",
        help="プラットフォーム"
    )
    parser.add_argument(
        "--style",
        choices=["casual", "professional", "fun"],
        default="casual",
        help="スタイル"
    )
    parser.add_argument("--no-image", action="store_true", help="画像を生成しない")
    parser.add_argument("--no-draft", action="store_true", help="下書きを保存しない")
    
    args = parser.parse_args()
    
    generate_content(
        topic=args.topic,
        platform=args.platform,
        style=args.style,
        include_image=not args.no_image,
        save_draft=not args.no_draft
    )


if __name__ == "__main__":
    main()
