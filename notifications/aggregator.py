"""
通知集約モジュール
GitHub, Slack などの通知を一箇所に集約
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import httpx

from core.utils import logger
from core.config import get_config


@dataclass
class Notification:
    """通知"""
    source: str
    title: str
    message: str
    url: Optional[str]
    priority: str  # low, normal, high
    timestamp: str


class NotificationAggregator:
    """
    通知集約
    
    ソース:
    - GitHub (PRレビュー依頼、Issue言及など)
    - Slack Webhook（送信用）
    """
    
    def __init__(self):
        self.config = get_config()
        self.client = httpx.Client(timeout=30)
        self.notifications: List[Notification] = []
        logger.info("NotificationAggregator initialized")
    
    def fetch_github_notifications(self) -> List[Notification]:
        """GitHub通知を取得"""
        if not self.config.github_token:
            logger.warning("GitHub token not set")
            return []
        
        logger.info("Fetching GitHub notifications...")
        
        try:
            response = self.client.get(
                "https://api.github.com/notifications",
                headers={
                    "Authorization": f"token {self.config.github_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            
            notifications = []
            for item in response.json():
                subject = item.get("subject", {})
                notifications.append(Notification(
                    source="github",
                    title=subject.get("title", ""),
                    message=f"[{item.get('reason', '')}] {subject.get('type', '')}",
                    url=subject.get("url", ""),
                    priority="high" if item.get("reason") == "review_requested" else "normal",
                    timestamp=item.get("updated_at", "")
                ))
            
            logger.info(f"Fetched {len(notifications)} GitHub notifications")
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to fetch GitHub notifications: {e}")
            return []
    
    def send_to_slack(
        self,
        message: str,
        title: Optional[str] = None,
        color: str = "#36a64f"
    ) -> bool:
        """Slackに通知を送信"""
        if not self.config.slack_webhook_url:
            logger.warning("Slack webhook URL not set")
            return False
        
        logger.info(f"Sending to Slack: {message[:50]}...")
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title or "Automation Hub",
                    "text": message,
                    "footer": "Automated Hub",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        try:
            response = self.client.post(
                self.config.slack_webhook_url,
                json=payload
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send to Slack: {e}")
            return False
    
    def aggregate_all(self) -> List[Notification]:
        """全ソースから通知を集約"""
        all_notifications = []
        
        # GitHub
        all_notifications.extend(self.fetch_github_notifications())
        
        # 優先度でソート
        priority_order = {"high": 0, "normal": 1, "low": 2}
        all_notifications.sort(key=lambda x: priority_order.get(x.priority, 1))
        
        self.notifications = all_notifications
        return all_notifications
    
    def get_summary(self) -> str:
        """通知サマリーを生成"""
        if not self.notifications:
            self.aggregate_all()
        
        high_priority = [n for n in self.notifications if n.priority == "high"]
        
        summary = f"📬 通知サマリー ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
        summary += f"合計: {len(self.notifications)}件"
        
        if high_priority:
            summary += f" (🔴 重要: {len(high_priority)}件)\n\n"
            for n in high_priority[:5]:
                summary += f"- [{n.source}] {n.title}\n"
        
        return summary
