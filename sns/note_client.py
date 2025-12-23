"""
note.com 自動投稿モジュール
Playwrightでブラウザ操作を自動化
"""
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import json

from playwright.async_api import async_playwright, Page

from core.config import get_config
from core.utils import logger, ensure_dir


@dataclass
class NotePostResult:
    """投稿結果"""
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None


class NoteClient:
    """
    note.com 自動投稿クライアント
    
    Playwrightでブラウザを自動操作して投稿
    初回はログインが必要（手動でログイン → Cookieを保存）
    """
    
    def __init__(self):
        config = get_config()
        self.storage_path = config.project_root / "sns" / "note_storage.json"
        ensure_dir(self.storage_path.parent)
        logger.info("NoteClient initialized")
    
    async def login_and_save_session(self):
        """
        ブラウザを開いてログイン、セッションを保存
        初回のみ手動でログインが必要
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # note.comのログインページへ
            await page.goto("https://note.com/login")
            
            print("=" * 50)
            print("ブラウザでnote.comにログインしてください")
            print("ログイン完了後、このターミナルでEnterを押してください")
            print("=" * 50)
            
            input("ログイン完了後、Enterを押す: ")
            
            # セッションを保存
            await context.storage_state(path=str(self.storage_path))
            print(f"セッション保存完了: {self.storage_path}")
            
            await browser.close()
    
    async def post_article(
        self,
        title: str,
        content: str,
        publish: bool = False
    ) -> NotePostResult:
        """
        記事を投稿
        
        Args:
            title: 記事タイトル
            content: 記事本文（Markdown形式）
            publish: True=公開, False=下書き保存
        """
        logger.info(f"Posting to note.com: {title[:30]}...")
        
        if not self.storage_path.exists():
            return NotePostResult(
                success=False,
                error="セッションがありません。login_and_save_session()を実行してください"
            )
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    storage_state=str(self.storage_path)
                )
                page = await context.new_page()
                
                # 新規記事作成ページへ
                await page.goto("https://note.com/notes/new")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)  # ページ読み込み待機
                
                # ログイン状態確認
                if "login" in page.url:
                    await browser.close()
                    return NotePostResult(
                        success=False,
                        error="セッションが切れています。再ログインしてください"
                    )
                
                # タイトル入力（複数のセレクタを試す）
                title_selectors = [
                    'textarea[placeholder*="タイトル"]',
                    'input[placeholder*="タイトル"]',
                    '[data-testid="note-title"]',
                    '.note-title-input',
                    'textarea[name="title"]',
                    'textarea:first-of-type'
                ]
                
                title_filled = False
                for selector in title_selectors:
                    try:
                        title_input = page.locator(selector).first
                        if await title_input.is_visible(timeout=2000):
                            await title_input.fill(title)
                            title_filled = True
                            break
                    except:
                        continue
                
                if not title_filled:
                    # フォールバック: 最初のテキストエリアに入力
                    await page.keyboard.press("Tab")
                    await page.keyboard.type(title)
                
                # 本文入力エリアに移動
                await page.keyboard.press("Tab")
                await asyncio.sleep(0.5)
                
                # 本文を入力
                for line in content.split("\n"):
                    if line.strip():
                        await page.keyboard.type(line, delay=10)
                    await page.keyboard.press("Enter")
                
                await asyncio.sleep(2)
                
                if publish:
                    # 公開ボタン
                    publish_btn = page.locator('button:has-text("公開")')
                    await publish_btn.click()
                    
                    # 確認ダイアログがあれば
                    confirm_btn = page.locator('button:has-text("公開する")')
                    if await confirm_btn.is_visible():
                        await confirm_btn.click()
                    
                    await page.wait_for_url("**/n/**", timeout=10000)
                    article_url = page.url
                else:
                    # 下書き保存（複数のセレクタを試す）
                    save_selectors = [
                        'button:has-text("下書き保存")',
                        'button:has-text("下書きを保存")',
                        '[data-testid="save-draft"]',
                        'button[type="button"]:has-text("保存")'
                    ]
                    
                    saved = False
                    for selector in save_selectors:
                        try:
                            save_btn = page.locator(selector).first
                            if await save_btn.is_visible(timeout=2000):
                                await save_btn.click()
                                await asyncio.sleep(2)
                                saved = True
                                logger.info(f"下書き保存ボタンをクリック: {selector}")
                                break
                        except:
                            continue
                    
                    if not saved:
                        # Ctrl+S で保存を試みる
                        await page.keyboard.press("Meta+s")
                        await asyncio.sleep(2)
                        logger.info("Ctrl+S で保存を試行")
                    
                    article_url = None
                
                await browser.close()
                
                logger.info(f"Note posted: {article_url or '下書き保存'}")
                return NotePostResult(success=True, url=article_url)
                
        except Exception as e:
            logger.error(f"Note posting failed: {e}")
            return NotePostResult(success=False, error=str(e))
    
    def post_article_sync(
        self,
        title: str,
        content: str,
        publish: bool = False
    ) -> NotePostResult:
        """同期版の投稿メソッド"""
        return asyncio.run(self.post_article(title, content, publish))
    
    def login_sync(self):
        """同期版のログインメソッド"""
        asyncio.run(self.login_and_save_session())


async def generate_note_article(topic: str) -> dict:
    """
    AIでnote記事を生成
    """
    from ai.gemini_client import GeminiClient
    
    gemini = GeminiClient()
    
    system_instruction = """
あなたは個人開発者のブログ記事を書きます。
note.comに投稿する記事を作成してください。

【口調】
- カジュアルだが読みやすい
- 絵文字は使わない
- 技術者目線で具体的に

【構成】
- 導入（100字程度）
- 本文（500-1000字）
- まとめ（100字程度）

出力形式（JSON）:
{
    "title": "記事タイトル",
    "content": "記事本文（Markdown形式）"
}
"""
    
    response = gemini.generate_text(
        prompt=f"トピック: {topic}\n\nnote記事を作成してください。",
        system_instruction=system_instruction,
        max_tokens=2000,
        temperature=0.7
    )
    
    # JSON解析
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean)
    except:
        return {"title": topic, "content": response}


# CLI用
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="note.com 自動投稿")
    parser.add_argument("--login", action="store_true", help="ログインしてセッションを保存")
    parser.add_argument("--topic", type=str, help="記事トピック（AI生成）")
    parser.add_argument("--publish", action="store_true", help="公開する（デフォルトは下書き）")
    
    args = parser.parse_args()
    
    client = NoteClient()
    
    if args.login:
        client.login_sync()
    elif args.topic:
        article = asyncio.run(generate_note_article(args.topic))
        print(f"タイトル: {article['title']}")
        print(f"本文:\n{article['content'][:200]}...")
        
        result = client.post_article_sync(
            title=article["title"],
            content=article["content"],
            publish=args.publish
        )
        
        if result.success:
            print(f"投稿成功: {result.url or '下書き保存'}")
        else:
            print(f"投稿失敗: {result.error}")
