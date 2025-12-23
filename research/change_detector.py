"""
Webサイト・アプリ変更検知システム
自動でトピックを検出してコンテンツを生成
"""
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from core.config import get_config
from core.utils import logger, ensure_dir, get_timestamp


@dataclass
class ChangeDetection:
    """変更検知結果"""
    source: str  # 変更元 (URL or "app_store")
    source_name: str  # 表示名
    change_type: str  # "new", "updated", "version"
    old_value: Optional[str]
    new_value: str
    detected_at: str
    description: str


class ChangeDetector:
    """
    変更検知システム
    
    - Webサイトのコンテンツ変更
    - App Storeのバージョン更新
    - GitHubのリリース
    などを自動検知
    """
    
    def __init__(self):
        config = get_config()
        self.data_dir = config.project_root / "data" / "change_detection"
        ensure_dir(self.data_dir)
        
        # 前回のスナップショット
        self.snapshot_file = self.data_dir / "snapshots.json"
        self.snapshots = self._load_snapshots()
        
        # 監視対象を読み込み
        self.targets = self._load_targets(config.project_root / "profile.json")
        
        logger.info(f"ChangeDetector initialized with {len(self.targets)} targets")
    
    def _load_snapshots(self) -> dict:
        """前回のスナップショットを読み込み"""
        if self.snapshot_file.exists():
            with open(self.snapshot_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _save_snapshots(self):
        """スナップショットを保存"""
        with open(self.snapshot_file, "w", encoding="utf-8") as f:
            json.dump(self.snapshots, f, ensure_ascii=False, indent=2)
    
    def _load_targets(self, profile_path: Path) -> List[Dict]:
        """プロフィールから監視対象を読み込み"""
        targets = []
        
        if profile_path.exists():
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
            
            # リリース済みプロジェクトを監視対象に
            for project in profile.get("projects", {}).get("released", []):
                name = project.get("name", "")
                
                # Webサイト
                if "url" in project:
                    targets.append({
                        "type": "website",
                        "name": name,
                        "url": project["url"]
                    })
                
                # App Store
                if "app_store_url" in project:
                    # App Store URLからIDを抽出
                    url = project["app_store_url"]
                    if "/id" in url:
                        app_id = url.split("/id")[-1].split("?")[0]
                        targets.append({
                            "type": "app_store",
                            "name": name,
                            "app_id": app_id,
                            "url": url
                        })
            
            # メインWebサイト
            main_website = profile.get("profile", {}).get("website")
            if main_website:
                targets.append({
                    "type": "website",
                    "name": "Enludus公式",
                    "url": main_website
                })
            
            # GitHub
            github = profile.get("profile", {}).get("github")
            if github:
                targets.append({
                    "type": "github",
                    "name": "GitHub",
                    "url": github
                })
        
        return targets
    
    def check_all(self) -> List[ChangeDetection]:
        """全ての監視対象をチェック"""
        changes = []
        
        for target in self.targets:
            try:
                if target["type"] == "website":
                    change = self._check_website(target)
                elif target["type"] == "app_store":
                    change = self._check_app_store(target)
                elif target["type"] == "github":
                    change = self._check_github(target)
                else:
                    continue
                
                if change:
                    changes.append(change)
            except Exception as e:
                logger.warning(f"Failed to check {target['name']}: {e}")
        
        # スナップショット保存
        self._save_snapshots()
        
        return changes
    
    def _check_website(self, target: Dict) -> Optional[ChangeDetection]:
        """Webサイトの変更をチェック"""
        url = target["url"]
        name = target["name"]
        
        logger.info(f"Checking website: {name} ({url})")
        
        response = httpx.get(url, timeout=30, follow_redirects=True)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # タイトルと主要コンテンツのハッシュを計算
        title = soup.title.string if soup.title else ""
        
        # 主要なテキストコンテンツを抽出
        main_content = ""
        for tag in soup.find_all(["h1", "h2", "h3", "p"]):
            main_content += tag.get_text(strip=True) + " "
        
        content_hash = hashlib.md5(main_content.encode()).hexdigest()
        
        # 前回と比較
        key = f"website:{url}"
        old_snapshot = self.snapshots.get(key, {})
        old_hash = old_snapshot.get("content_hash", "")
        
        # 新しいスナップショットを保存
        self.snapshots[key] = {
            "content_hash": content_hash,
            "title": title,
            "checked_at": datetime.now().isoformat()
        }
        
        # 変更があれば
        if old_hash and old_hash != content_hash:
            return ChangeDetection(
                source=url,
                source_name=name,
                change_type="updated",
                old_value=old_hash[:8],
                new_value=content_hash[:8],
                detected_at=datetime.now().isoformat(),
                description=f"{name}のWebサイトが更新されました"
            )
        
        # 初回チェック
        if not old_hash:
            logger.info(f"First snapshot saved for {name}")
        
        return None
    
    def _check_app_store(self, target: Dict) -> Optional[ChangeDetection]:
        """App Storeのバージョンをチェック"""
        app_id = target["app_id"]
        name = target["name"]
        
        logger.info(f"Checking App Store: {name} (ID: {app_id})")
        
        # iTunes API
        url = f"https://itunes.apple.com/lookup?id={app_id}&country=jp"
        response = httpx.get(url, timeout=30)
        data = response.json()
        
        if not data.get("results"):
            return None
        
        app_info = data["results"][0]
        current_version = app_info.get("version", "")
        release_notes = app_info.get("releaseNotes", "")
        
        # 前回と比較
        key = f"app_store:{app_id}"
        old_snapshot = self.snapshots.get(key, {})
        old_version = old_snapshot.get("version", "")
        
        # 新しいスナップショットを保存
        self.snapshots[key] = {
            "version": current_version,
            "release_notes": release_notes[:200],
            "checked_at": datetime.now().isoformat()
        }
        
        # バージョンが変わったら
        if old_version and old_version != current_version:
            return ChangeDetection(
                source=target["url"],
                source_name=name,
                change_type="version",
                old_value=old_version,
                new_value=current_version,
                detected_at=datetime.now().isoformat(),
                description=f"{name}がv{current_version}にアップデート。{release_notes[:100]}"
            )
        
        return None
    
    def _check_github(self, target: Dict) -> Optional[ChangeDetection]:
        """GitHubの新しいリリースをチェック"""
        # TODO: GitHub APIでリリースをチェック
        return None


def auto_generate_content():
    """
    変更を検知して自動でコンテンツを生成
    
    Returns:
        生成されたコンテンツ or None
    """
    from ai.connected_content import ConnectedContentGenerator
    
    detector = ChangeDetector()
    changes = detector.check_all()
    
    if not changes:
        logger.info("No changes detected")
        return None
    
    # 変更があればコンテンツを生成
    logger.info(f"Detected {len(changes)} changes")
    
    generator = ConnectedContentGenerator()
    contents = []
    
    for change in changes:
        # 変更内容からトピックを生成
        topic = f"{change.source_name}: {change.description}"
        
        logger.info(f"Generating content for: {topic}")
        content = generator.generate(topic)
        contents.append(content)
    
    return contents


def get_trending_topic():
    """
    リサーチから自動でトピックを取得
    """
    from research.tech_trend_fetcher import TechTrendFetcher
    
    fetcher = TechTrendFetcher()
    articles = fetcher.fetch_all(limit=5)
    
    if not articles:
        return None
    
    # 最も関連性の高い記事をトピックに
    # (学習/教育/AIに関連するものを優先)
    keywords = ["AI", "教育", "学習", "アプリ", "開発", "Flutter", "Python"]
    
    for article in articles:
        title = article.get("title", "")
        for keyword in keywords:
            if keyword.lower() in title.lower():
                return title
    
    # なければ最初の記事
    return articles[0].get("title", "")


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="変更検知 & 自動コンテンツ生成")
    parser.add_argument("--check", action="store_true", help="変更をチェック")
    parser.add_argument("--auto", action="store_true", help="変更検知してコンテンツ生成")
    parser.add_argument("--trend", action="store_true", help="トレンドからトピック取得")
    
    args = parser.parse_args()
    
    if args.check:
        detector = ChangeDetector()
        changes = detector.check_all()
        
        if changes:
            print(f"\n{len(changes)} 件の変更を検知:")
            for c in changes:
                print(f"  - [{c.change_type}] {c.source_name}: {c.description}")
        else:
            print("変更なし")
    
    elif args.auto:
        contents = auto_generate_content()
        if contents:
            print(f"\n{len(contents)} 件のコンテンツを生成")
        else:
            print("変更なし、コンテンツ未生成")
    
    elif args.trend:
        topic = get_trending_topic()
        if topic:
            print(f"トレンドトピック: {topic}")
        else:
            print("トピックが見つかりません")
    
    else:
        parser.print_help()
