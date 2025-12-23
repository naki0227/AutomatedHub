"""
共通ユーティリティ
ロギング、ファイル操作、日時処理など
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Rich console for beautiful output
console = Console()

# Logger instance
logger = logging.getLogger("automated")


def setup_logging(level: int = logging.INFO) -> None:
    """ロギングのセットアップ"""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_path=False
            )
        ]
    )


def get_timestamp() -> str:
    """現在のタイムスタンプを取得 (YYYY-MM-DD_HH-MM-SS)"""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_date_string() -> str:
    """現在の日付を取得 (YYYY-MM-DD)"""
    return datetime.now().strftime("%Y-%m-%d")


def ensure_dir(path: Path) -> Path:
    """ディレクトリが存在することを確認、なければ作成"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_file(path: Path) -> Optional[str]:
    """ファイルを読み込む"""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return None


def write_file(path: Path, content: str) -> bool:
    """ファイルに書き込む"""
    try:
        ensure_dir(path.parent)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Failed to write file: {path}, error: {e}")
        return False


def print_success(message: str) -> None:
    """成功メッセージを表示"""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """エラーメッセージを表示"""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """情報メッセージを表示"""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_warning(message: str) -> None:
    """警告メッセージを表示"""
    console.print(f"[yellow]⚠[/yellow] {message}")


# 初期化時にロギングをセットアップ
setup_logging()
