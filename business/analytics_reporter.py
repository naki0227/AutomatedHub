"""
アプリ分析レポートモジュール
App Store Connect, Firebase のデータからレポート生成
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import json

from core.utils import logger, ensure_dir
from core.config import get_config
from ai.gemini_client import GeminiClient


@dataclass
class AppMetrics:
    """アプリメトリクス"""
    app_name: str
    period: str
    downloads: int
    active_users: int
    revenue: float
    rating: float
    review_count: int
    crash_rate: float


class AnalyticsReporter:
    """
    アプリ分析レポート生成
    
    機能:
    - App Store Connect データの集計（手動入力 or API）
    - 週次/月次レポート生成
    - AIによるインサイト生成
    """
    
    def __init__(self):
        config = get_config()
        self.reports_dir = config.project_root / "business" / "reports"
        ensure_dir(self.reports_dir)
        self.gemini = GeminiClient()
        logger.info("AnalyticsReporter initialized")
    
    def create_report(
        self,
        app_name: str,
        metrics: Dict,
        period: str = "weekly"
    ) -> str:
        """
        分析レポートを生成
        
        Args:
            app_name: アプリ名
            metrics: メトリクスデータ（手動入力）
            period: レポート期間 (weekly, monthly)
        """
        logger.info(f"Creating {period} report for {app_name}")
        
        # レポート生成
        report = self._generate_report_content(app_name, metrics, period)
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d")
        report_path = self.reports_dir / f"{app_name}_{period}_{timestamp}.md"
        report_path.write_text(report, encoding="utf-8")
        
        logger.info(f"Report saved: {report_path}")
        return report
    
    def _generate_report_content(
        self,
        app_name: str,
        metrics: Dict,
        period: str
    ) -> str:
        """レポートコンテンツを生成"""
        
        # 基本レポート
        report = f"""# {app_name} {period.capitalize()} レポート
生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M")}
期間: {metrics.get('start_date', 'N/A')} 〜 {metrics.get('end_date', 'N/A')}

## 主要指標

| 指標 | 今期 | 前期比 |
|------|------|--------|
| ダウンロード数 | {metrics.get('downloads', 'N/A')} | {metrics.get('downloads_change', 'N/A')} |
| アクティブユーザー | {metrics.get('active_users', 'N/A')} | {metrics.get('active_users_change', 'N/A')} |
| 評価 | {metrics.get('rating', 'N/A')} | {metrics.get('rating_change', 'N/A')} |
| レビュー数 | {metrics.get('reviews', 'N/A')} | {metrics.get('reviews_change', 'N/A')} |
| クラッシュ率 | {metrics.get('crash_rate', 'N/A')}% | {metrics.get('crash_rate_change', 'N/A')} |

"""
        
        # AIインサイトを追加
        insights = self._generate_insights(app_name, metrics)
        report += f"""## AIインサイト

{insights}

## 次のアクション

- [ ] 確認した改善点に対応
- [ ] レビュー返信の確認
- [ ] 次週の施策検討
"""
        
        return report
    
    def _generate_insights(self, app_name: str, metrics: Dict) -> str:
        """AIでインサイトを生成"""
        
        prompt = f"""
以下のアプリメトリクスを分析して、インサイトを3点挙げてください：

アプリ名: {app_name}
メトリクス:
{json.dumps(metrics, ensure_ascii=False, indent=2)}

以下の形式で出力:
1. **良かった点**: ...
2. **改善が必要な点**: ...
3. **推奨アクション**: ...
"""
        
        return self.gemini.generate_text(
            prompt=prompt,
            system_instruction="アプリの成長戦略アドバイザーとして分析します。",
            max_tokens=500,
            temperature=0.5
        )
    
    def input_metrics_interactive(self, app_name: str) -> Dict:
        """対話形式でメトリクスを入力（CLIツール用）"""
        print(f"\n=== {app_name} メトリクス入力 ===")
        
        metrics = {
            "start_date": input("開始日 (YYYY-MM-DD): "),
            "end_date": input("終了日 (YYYY-MM-DD): "),
            "downloads": input("ダウンロード数: "),
            "downloads_change": input("前期比 (例: +10%): "),
            "active_users": input("アクティブユーザー数: "),
            "active_users_change": input("前期比: "),
            "rating": input("評価 (例: 4.5): "),
            "rating_change": input("前期比: "),
            "reviews": input("レビュー数: "),
            "reviews_change": input("前期比: "),
            "crash_rate": input("クラッシュ率 (%): "),
            "crash_rate_change": input("前期比: ")
        }
        
        return metrics
    
    def list_reports(self) -> List[str]:
        """保存済みレポート一覧"""
        reports = list(self.reports_dir.glob("*.md"))
        return [r.name for r in sorted(reports, reverse=True)]
