"""
投稿スケジューラー
定期投稿とベストタイミング提案
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass, asdict
import schedule
import time
import threading

from core.config import get_config
from core.utils import logger, ensure_dir


@dataclass
class ScheduledPost:
    """スケジュール済み投稿"""
    id: str
    platform: str
    text: str
    image_path: Optional[str]
    scheduled_time: str
    status: str  # pending, posted, failed
    created_at: str


class PostScheduler:
    """
    投稿スケジューラー
    
    機能:
    - 投稿のスケジューリング
    - 下書き保存（Instagram/TikTok用）
    - ベストタイミング提案
    """
    
    # 最適投稿時間（日本時間）
    BEST_TIMES = {
        "x": ["7:00", "12:00", "18:00", "21:00"],
        "instagram": ["12:00", "19:00", "21:00"],
        "tiktok": ["19:00", "21:00", "22:00"]
    }
    
    def __init__(self):
        config = get_config()
        self.drafts_dir = config.drafts_dir
        self.schedule_file = self.drafts_dir / "schedule.json"
        self._scheduled_posts: List[ScheduledPost] = []
        self._load_schedule()
        logger.info("PostScheduler initialized")
    
    def schedule_post(
        self,
        platform: str,
        text: str,
        scheduled_time: datetime,
        image_path: Optional[Path] = None
    ) -> ScheduledPost:
        """投稿をスケジュール"""
        post = ScheduledPost(
            id=f"{platform}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            platform=platform,
            text=text,
            image_path=str(image_path) if image_path else None,
            scheduled_time=scheduled_time.isoformat(),
            status="pending",
            created_at=datetime.now().isoformat()
        )
        
        self._scheduled_posts.append(post)
        self._save_schedule()
        
        logger.info(f"Post scheduled: {post.id} at {scheduled_time}")
        return post
    
    def save_draft(
        self,
        platform: str,
        text: str,
        hashtags: List[str],
        image_path: Optional[Path] = None,
        source_url: str = ""
    ) -> Path:
        """
        下書きを保存（Instagram/TikTok用）
        手動投稿時に使用
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_path = self.drafts_dir / f"{platform}_{timestamp}.json"
        
        draft_data = {
            "platform": platform,
            "text": text,
            "hashtags": hashtags,
            "full_text": f"{text}\n\n{' '.join(hashtags)}",
            "image_path": str(image_path) if image_path else None,
            "source_url": source_url,
            "created_at": datetime.now().isoformat()
        }
        
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Draft saved: {draft_path}")
        return draft_path
    
    def get_pending_posts(self) -> List[ScheduledPost]:
        """未投稿のスケジュールを取得"""
        return [p for p in self._scheduled_posts if p.status == "pending"]
    
    def get_best_time(self, platform: str) -> str:
        """次のベストな投稿時間を取得"""
        now = datetime.now()
        times = self.BEST_TIMES.get(platform, ["12:00"])
        
        for time_str in times:
            hour, minute = map(int, time_str.split(":"))
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target > now:
                return target.strftime("%Y-%m-%d %H:%M")
        
        # 今日の時間が全て過ぎていたら明日の最初の時間
        hour, minute = map(int, times[0].split(":"))
        tomorrow = now + timedelta(days=1)
        target = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return target.strftime("%Y-%m-%d %H:%M")
    
    def list_drafts(self) -> List[dict]:
        """保存済み下書き一覧を取得"""
        drafts = []
        for draft_file in self.drafts_dir.glob("*.json"):
            if draft_file.name == "schedule.json":
                continue
            try:
                with open(draft_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["file_path"] = str(draft_file)
                    drafts.append(data)
            except Exception as e:
                logger.warning(f"Failed to read draft: {draft_file}, {e}")
        
        return sorted(drafts, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def mark_as_posted(self, post_id: str) -> bool:
        """投稿完了としてマーク"""
        for post in self._scheduled_posts:
            if post.id == post_id:
                post.status = "posted"
                self._save_schedule()
                return True
        return False
    
    def _load_schedule(self):
        """スケジュールを読み込み"""
        if self.schedule_file.exists():
            try:
                with open(self.schedule_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._scheduled_posts = [ScheduledPost(**p) for p in data]
            except Exception as e:
                logger.warning(f"Failed to load schedule: {e}")
    
    def _save_schedule(self):
        """スケジュールを保存"""
        ensure_dir(self.drafts_dir)
        with open(self.schedule_file, "w", encoding="utf-8") as f:
            data = [asdict(p) for p in self._scheduled_posts]
            json.dump(data, f, ensure_ascii=False, indent=2)
