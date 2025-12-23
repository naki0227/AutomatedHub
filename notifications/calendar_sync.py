"""
カレンダー連携モジュール
投稿スケジュールをカレンダーファイルとして出力
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import json

from core.utils import logger, ensure_dir
from core.config import get_config


@dataclass
class CalendarEvent:
    """カレンダーイベント"""
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None


class CalendarSync:
    """
    カレンダー連携
    
    機能:
    - 投稿スケジュールからICS形式のカレンダーを生成
    - Googleカレンダーインポート用ファイル出力
    """
    
    def __init__(self):
        config = get_config()
        self.output_dir = config.project_root / "notifications" / "calendar"
        ensure_dir(self.output_dir)
        logger.info("CalendarSync initialized")
    
    def create_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        duration_minutes: int = 30
    ) -> CalendarEvent:
        """イベントを作成"""
        return CalendarEvent(
            title=title,
            description=description,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=duration_minutes)
        )
    
    def export_to_ics(
        self,
        events: List[CalendarEvent],
        filename: str = "schedule.ics"
    ) -> Path:
        """
        ICSファイルとしてエクスポート
        Googleカレンダーなどにインポート可能
        """
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Automation Hub//Schedule//JP
CALSCALE:GREGORIAN
METHOD:PUBLISH
"""
        
        for event in events:
            ics_content += f"""BEGIN:VEVENT
DTSTART:{event.start_time.strftime('%Y%m%dT%H%M%S')}
DTEND:{event.end_time.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{event.title}
DESCRIPTION:{event.description}
END:VEVENT
"""
        
        ics_content += "END:VCALENDAR"
        
        output_path = self.output_dir / filename
        output_path.write_text(ics_content, encoding="utf-8")
        
        logger.info(f"ICS file exported: {output_path}")
        return output_path
    
    def create_posting_schedule(
        self,
        platform: str,
        posts_per_day: int = 1,
        days: int = 7,
        preferred_times: List[str] = None
    ) -> List[CalendarEvent]:
        """
        投稿スケジュールを生成
        
        Args:
            platform: プラットフォーム (x, instagram, tiktok)
            posts_per_day: 1日あたりの投稿数
            days: スケジュール日数
            preferred_times: 希望投稿時間 (例: ["12:00", "19:00"])
        """
        if preferred_times is None:
            preferred_times = ["12:00", "19:00"]
        
        events = []
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            
            for i, time_str in enumerate(preferred_times[:posts_per_day]):
                hour, minute = map(int, time_str.split(":"))
                post_time = current_date.replace(hour=hour, minute=minute)
                
                events.append(CalendarEvent(
                    title=f"[{platform.upper()}] 投稿",
                    description=f"{platform}への投稿予定",
                    start_time=post_time,
                    end_time=post_time + timedelta(minutes=15)
                ))
        
        return events
    
    def sync_from_drafts(self) -> List[CalendarEvent]:
        """下書きからスケジュールを同期"""
        config = get_config()
        drafts_dir = config.drafts_dir
        
        events = []
        
        for draft_file in drafts_dir.glob("*.json"):
            if draft_file.name == "schedule.json":
                continue
            
            try:
                with open(draft_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 下書きからイベントを作成
                created_at = datetime.fromisoformat(data.get("created_at", ""))
                platform = data.get("platform", "unknown")
                
                events.append(CalendarEvent(
                    title=f"[{platform.upper()}] 下書き投稿",
                    description=data.get("text", "")[:100],
                    start_time=created_at,
                    end_time=created_at + timedelta(minutes=15)
                ))
                
            except Exception as e:
                logger.warning(f"Failed to parse draft: {draft_file}, {e}")
        
        return events
