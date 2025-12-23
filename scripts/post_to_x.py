#!/usr/bin/env python3
"""
X投稿スクリプト
下書きまたは直接入力からXに投稿
"""
import argparse
import json
from pathlib import Path

from core.utils import print_info, print_success, print_error
from sns.x_client import XClient
from sns.post_scheduler import PostScheduler


def post_from_draft(draft_path: Path):
    """下書きから投稿"""
    print_info(f"下書きを読み込み: {draft_path}")
    
    with open(draft_path, "r", encoding="utf-8") as f:
        draft = json.load(f)
    
    text = draft.get("full_text") or draft.get("text", "")
    image_path = draft.get("image_path")
    
    if image_path:
        image_path = Path(image_path)
        if not image_path.exists():
            image_path = None
    
    return post_to_x(text, image_path)


def post_to_x(text: str, image_path: Path = None):
    """Xに投稿"""
    print_info(f"投稿内容:\n{text[:100]}...")
    
    x_client = XClient()
    result = x_client.post(text, image_path)
    
    if result.success:
        print_success(f"投稿完了: {result.url}")
    else:
        print_error(f"投稿失敗: {result.error}")
    
    return result


def list_drafts():
    """下書き一覧"""
    scheduler = PostScheduler()
    drafts = scheduler.list_drafts()
    
    if not drafts:
        print("下書きはありません")
        return
    
    print(f"\n📝 下書き一覧 ({len(drafts)}件):")
    for i, draft in enumerate(drafts[:10], 1):
        platform = draft.get("platform", "unknown")
        text = draft.get("text", "")[:50]
        created = draft.get("created_at", "")[:10]
        print(f"  {i}. [{platform}] {text}... ({created})")
        print(f"     → {draft.get('file_path')}")


def main():
    parser = argparse.ArgumentParser(description="X投稿")
    parser.add_argument("--draft", type=str, help="下書きファイルパス")
    parser.add_argument("--text", type=str, help="直接投稿するテキスト")
    parser.add_argument("--image", type=str, help="添付画像パス")
    parser.add_argument("--list", action="store_true", help="下書き一覧を表示")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（実際には投稿しない）")
    
    args = parser.parse_args()
    
    if args.list:
        list_drafts()
        return
    
    if args.draft:
        draft_path = Path(args.draft)
        if not draft_path.exists():
            print_error(f"下書きが見つかりません: {draft_path}")
            return
        
        if args.dry_run:
            with open(draft_path, "r", encoding="utf-8") as f:
                draft = json.load(f)
            print_info("ドライラン: 投稿内容のプレビュー")
            print(draft.get("full_text") or draft.get("text", ""))
        else:
            post_from_draft(draft_path)
    
    elif args.text:
        image_path = Path(args.image) if args.image else None
        
        if args.dry_run:
            print_info("ドライラン: 投稿内容のプレビュー")
            print(args.text)
        else:
            post_to_x(args.text, image_path)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
