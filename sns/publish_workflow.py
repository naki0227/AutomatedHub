"""
一括投稿ワークフロー

生成 → note投稿 → X投稿 → Instagram下書き保存
"""
import asyncio
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

from core.config import get_config
from core.utils import logger, ensure_dir, get_timestamp


@dataclass
class PublishResult:
    """投稿結果"""
    success: bool
    topic: str
    created_at: str
    
    # note
    note_posted: bool = False
    note_url: Optional[str] = None
    note_error: Optional[str] = None
    
    # X
    x_posted: bool = False
    x_main_url: Optional[str] = None
    x_reply_url: Optional[str] = None
    x_error: Optional[str] = None
    
    # Instagram
    instagram_saved: bool = False
    instagram_draft_path: Optional[str] = None


class PublishWorkflow:
    """
    一括投稿ワークフロー
    
    1. トレンドからコンテンツ生成
    2. noteに投稿
    3. Xに投稿（メイン + リプ欄）
    4. Instagram下書き保存
    """
    
    def __init__(self):
        config = get_config()
        self.project_root = config.project_root
        self.output_dir = config.project_root / "sns" / "publish_results"
        ensure_dir(self.output_dir)
        
        logger.info("PublishWorkflow initialized")
    
    def run(self, topic: Optional[str] = None) -> PublishResult:
        """
        一括投稿を実行
        
        Args:
            topic: トピック（省略時はトレンドから）
        """
        logger.info("Starting publish workflow...")
        
        result = PublishResult(
            success=False,
            topic=topic or "",
            created_at=datetime.now().isoformat()
        )
        
        try:
            # Step 1: コンテンツ生成
            logger.info("Step 1: Generating content...")
            from ai.enhanced_workflow import EnhancedContentWorkflow
            
            workflow = EnhancedContentWorkflow()
            content = workflow.create_content(topic)
            result.topic = content.topic
            
            logger.info(f"Content generated: {content.topic}")
            
            # Step 2: note投稿
            logger.info("Step 2: Posting to note...")
            note_result = self._post_to_note(content)
            result.note_posted = note_result["success"]
            result.note_url = note_result.get("url")
            result.note_error = note_result.get("error")
            
            # Step 3: X投稿
            logger.info("Step 3: Posting to X...")
            x_result = self._post_to_x(content, result.note_url)
            result.x_posted = x_result["success"]
            result.x_main_url = x_result.get("main_url")
            result.x_reply_url = x_result.get("reply_url")
            result.x_error = x_result.get("error")
            
            # Step 4: Instagram下書き保存
            logger.info("Step 4: Saving Instagram draft...")
            insta_result = self._save_instagram_draft(content)
            result.instagram_saved = insta_result["success"]
            result.instagram_draft_path = insta_result.get("path")
            
            # 成功判定
            result.success = result.note_posted or result.x_posted
            
            # 結果保存
            self._save_result(result)
            
            logger.info(f"Publish workflow completed: success={result.success}")
            
        except Exception as e:
            logger.error(f"Publish workflow failed: {e}")
            result.note_error = str(e)
        
        return result
    
    def _post_to_note(self, content) -> dict:
        """noteコンテンツをMarkdownファイルとして保存"""
        try:
            from pathlib import Path
            from datetime import datetime
            
            # 出力ディレクトリ
            output_dir = Path("sns/note_articles")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # タグ文字列
            tags_str = " ".join(content.note.tags) if content.note.tags else ""
            
            # Markdownファイルを作成
            md_content = f"""# {content.note.title}

**タグ**: {tags_str}

**ヘッダー画像プロンプト**: {content.note.header_image_prompt}

---

## 無料版（ここまで無料公開）

{content.note.free_content}

---

## 有料版（ここから有料）

{content.note.paid_content}
"""
            
            # Markdownファイル保存
            md_path = output_dir / f"note_{timestamp}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            # テキストファイル（プレーンテキスト版）も保存
            txt_content = f"""タイトル: {content.note.title}

タグ: {tags_str}

ヘッダー画像プロンプト:
{content.note.header_image_prompt}

========================================
無料版（ここまで無料公開）
========================================

{content.note.free_content}

========================================
有料版（ここから有料）
========================================

{content.note.paid_content}
"""
            txt_path = output_dir / f"note_{timestamp}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(txt_content)
            
            logger.info(f"Note article saved: {md_path}")
            
            return {
                "success": True,
                "url": None,
                "md_path": str(md_path),
                "txt_path": str(txt_path),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Note saving failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _post_to_x(self, content, note_url: Optional[str]) -> dict:
        """Xに投稿"""
        try:
            from sns.x_client import XClient
            
            client = XClient()
            
            # メイン投稿
            main_text = content.x_post.main_text
            hashtags = " ".join(content.x_post.hashtags)
            full_main = f"{main_text}\n{hashtags}"
            
            main_result = client.post(full_main)
            
            # PostResultはdataclassなので属性アクセス
            if not main_result.success:
                return {
                    "success": False,
                    "error": main_result.error or "投稿失敗"
                }
            
            main_tweet_id = main_result.tweet_id
            main_url = f"https://twitter.com/enludus/status/{main_tweet_id}"
            
            # リプ欄投稿（note誘導 + キャンペーン）
            reply_parts = [content.x_post.reply_text]
            
            if note_url:
                reply_parts.append(f"\n詳しくはこちら: {note_url}")
            
            if content.x_post.campaign_url:
                reply_parts.append(f"\n\n実は今、個人開発プロジェクトのクラファンやってます。AI×エンタメで面白いものを作りたいので、応援よろしくお願いします！\n👇詳細はこちら\n{content.x_post.campaign_url}")
            
            reply_text = "".join(reply_parts)
            
            reply_result = client.post(reply_text, reply_to=main_tweet_id)
            
            reply_url = None
            if reply_result.success:
                reply_url = f"https://twitter.com/enludus/status/{reply_result.tweet_id}"
            
            return {
                "success": True,
                "main_url": main_url,
                "reply_url": reply_url
            }
            
        except Exception as e:
            logger.error(f"X posting failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_instagram_draft(self, content) -> dict:
        """Instagram下書きを保存"""
        try:
            draft_dir = self.project_root / "sns" / "drafts"
            ensure_dir(draft_dir)
            
            timestamp = get_timestamp()
            path = draft_dir / f"instagram_{timestamp}.json"
            
            draft = {
                "platform": "instagram",
                "created_at": datetime.now().isoformat(),
                "caption": content.instagram.caption,
                "hashtags": content.instagram.hashtags,
                "image_prompt": content.instagram.image_prompt,
                "source_url": content.instagram.source_url,
                "status": "draft"
            }
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(draft, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "path": str(path)}
            
        except Exception as e:
            logger.error(f"Instagram draft save failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_result(self, result: PublishResult):
        """結果を保存"""
        timestamp = get_timestamp()
        path = self.output_dir / f"publish_{timestamp}.json"
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Publish result saved: {path}")


def print_result(result: PublishResult):
    """結果を表示"""
    print("=" * 60)
    print(f"一括投稿結果: {'✅ 成功' if result.success else '❌ 失敗'}")
    print(f"トピック: {result.topic}")
    print("=" * 60)
    
    print(f"\n📖 note: {'✅' if result.note_posted else '❌'}")
    if result.note_url:
        print(f"   URL: {result.note_url}")
    if result.note_error:
        print(f"   エラー: {result.note_error}")
    
    print(f"\n🐦 X: {'✅' if result.x_posted else '❌'}")
    if result.x_main_url:
        print(f"   メイン: {result.x_main_url}")
    if result.x_reply_url:
        print(f"   リプ欄: {result.x_reply_url}")
    if result.x_error:
        print(f"   エラー: {result.x_error}")
    
    print(f"\n📸 Instagram: {'✅ 下書き保存' if result.instagram_saved else '❌'}")
    if result.instagram_draft_path:
        print(f"   保存先: {result.instagram_draft_path}")


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="一括投稿ワークフロー")
    parser.add_argument("--topic", type=str, help="トピック（省略時はトレンドから）")
    
    args = parser.parse_args()
    
    workflow = PublishWorkflow()
    result = workflow.run(args.topic)
    print_result(result)
