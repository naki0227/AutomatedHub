"""
競合アプリ監視モジュール
App Storeの競合アプリ評価・更新を追跡
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import json

from core.utils import logger, ensure_dir
from core.config import get_config


@dataclass
class AppInfo:
    """アプリ情報"""
    app_id: str
    name: str
    developer: str
    rating: float
    review_count: int
    version: str
    last_updated: str
    price: str
    url: str
    description: Optional[str] = None


@dataclass
class AppUpdate:
    """アプリ更新情報"""
    app_id: str
    app_name: str
    change_type: str  # version, rating, review_count
    old_value: str
    new_value: str
    detected_at: str


class CompetitorWatcher:
    """
    競合アプリ監視
    
    機能:
    - App Storeのアプリ情報取得
    - 評価・レビュー数の変動監視
    - バージョン更新の検出
    """
    
    def __init__(self):
        self.client = httpx.Client(timeout=30)
        config = get_config()
        self.data_dir = config.project_root / "research" / "competitor_data"
        ensure_dir(self.data_dir)
        logger.info("CompetitorWatcher initialized")
    
    def get_app_info(self, app_id: str, country: str = "jp") -> Optional[AppInfo]:
        """
        App Store APIでアプリ情報を取得
        
        Args:
            app_id: App Store ID (例: "123456789")
            country: 国コード
        """
        logger.info(f"Fetching app info: {app_id}")
        
        try:
            response = self.client.get(
                f"https://itunes.apple.com/lookup",
                params={"id": app_id, "country": country}
            )
            data = response.json()
            
            if data.get("resultCount", 0) == 0:
                logger.warning(f"App not found: {app_id}")
                return None
            
            result = data["results"][0]
            
            return AppInfo(
                app_id=app_id,
                name=result.get("trackName", ""),
                developer=result.get("sellerName", ""),
                rating=result.get("averageUserRating", 0),
                review_count=result.get("userRatingCount", 0),
                version=result.get("version", ""),
                last_updated=result.get("currentVersionReleaseDate", ""),
                price=result.get("formattedPrice", "Free"),
                url=result.get("trackViewUrl", ""),
                description=result.get("description", "")[:500]
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch app info: {e}")
            return None
    
    def search_apps(
        self,
        term: str,
        country: str = "jp",
        limit: int = 10
    ) -> List[AppInfo]:
        """
        App Storeでアプリを検索
        """
        logger.info(f"Searching apps: {term}")
        
        try:
            response = self.client.get(
                "https://itunes.apple.com/search",
                params={
                    "term": term,
                    "country": country,
                    "entity": "software",
                    "limit": limit
                }
            )
            data = response.json()
            
            apps = []
            for result in data.get("results", []):
                apps.append(AppInfo(
                    app_id=str(result.get("trackId", "")),
                    name=result.get("trackName", ""),
                    developer=result.get("sellerName", ""),
                    rating=result.get("averageUserRating", 0),
                    review_count=result.get("userRatingCount", 0),
                    version=result.get("version", ""),
                    last_updated=result.get("currentVersionReleaseDate", ""),
                    price=result.get("formattedPrice", "Free"),
                    url=result.get("trackViewUrl", "")
                ))
            
            return apps
            
        except Exception as e:
            logger.error(f"Failed to search apps: {e}")
            return []
    
    def watch_app(self, app_id: str) -> List[AppUpdate]:
        """
        アプリの変更を監視
        前回のデータと比較して変更を検出
        """
        current = self.get_app_info(app_id)
        if not current:
            return []
        
        # 前回のデータを読み込み
        history_file = self.data_dir / f"{app_id}.json"
        previous = None
        
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                previous_data = json.load(f)
                previous = AppInfo(**previous_data)
        
        # 現在のデータを保存
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump({
                "app_id": current.app_id,
                "name": current.name,
                "developer": current.developer,
                "rating": current.rating,
                "review_count": current.review_count,
                "version": current.version,
                "last_updated": current.last_updated,
                "price": current.price,
                "url": current.url
            }, f, ensure_ascii=False, indent=2)
        
        # 変更を検出
        updates = []
        now = datetime.now().isoformat()
        
        if previous:
            if current.version != previous.version:
                updates.append(AppUpdate(
                    app_id=app_id,
                    app_name=current.name,
                    change_type="version",
                    old_value=previous.version,
                    new_value=current.version,
                    detected_at=now
                ))
            
            if abs(current.rating - previous.rating) > 0.1:
                updates.append(AppUpdate(
                    app_id=app_id,
                    app_name=current.name,
                    change_type="rating",
                    old_value=str(previous.rating),
                    new_value=str(current.rating),
                    detected_at=now
                ))
            
            review_change = current.review_count - previous.review_count
            if abs(review_change) > 10:
                updates.append(AppUpdate(
                    app_id=app_id,
                    app_name=current.name,
                    change_type="review_count",
                    old_value=str(previous.review_count),
                    new_value=f"{current.review_count} ({review_change:+d})",
                    detected_at=now
                ))
        
        return updates
    
    def watch_multiple(self, app_ids: List[str]) -> List[AppUpdate]:
        """複数アプリを監視"""
        all_updates = []
        for app_id in app_ids:
            updates = self.watch_app(app_id)
            all_updates.extend(updates)
        return all_updates
    
    def generate_report(self, app_ids: List[str]) -> str:
        """競合分析レポートを生成"""
        report = f"# 競合アプリレポート\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for app_id in app_ids:
            app = self.get_app_info(app_id)
            if app:
                report += f"""## {app.name}
- 開発者: {app.developer}
- 評価: {app.rating:.1f} ({app.review_count}件)
- バージョン: {app.version}
- 価格: {app.price}
- [App Store]({app.url})

"""
        
        return report
