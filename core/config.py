"""
設定管理モジュール
環境変数からAPIキーなどの設定を読み込む
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """アプリケーション設定"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Gemini API (メイン)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    
    # OpenAI API (オプション、DALL-Eフォールバック用)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    
    # YouTube Data API
    youtube_api_key: str = Field(default="", alias="YOUTUBE_API_KEY")
    
    # X (Twitter) API
    x_api_key: str = Field(default="", alias="X_API_KEY")
    x_api_secret: str = Field(default="", alias="X_API_SECRET")
    x_access_token: str = Field(default="", alias="X_ACCESS_TOKEN")
    x_access_token_secret: str = Field(default="", alias="X_ACCESS_TOKEN_SECRET")
    x_bearer_token: str = Field(default="", alias="X_BEARER_TOKEN")
    
    # GitHub
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    
    # Slack (オプション)
    slack_webhook_url: Optional[str] = Field(default=None, alias="SLACK_WEBHOOK_URL")
    
    # プロジェクトパス
    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent
    
    @property
    def drafts_dir(self) -> Path:
        path = self.project_root / "sns" / "drafts"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def reports_dir(self) -> Path:
        path = self.project_root / "analytics" / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def validate_gemini(self) -> bool:
        """Gemini APIキーが設定されているか確認"""
        return bool(self.gemini_api_key)
    
    def validate_youtube(self) -> bool:
        """YouTube APIキーが設定されているか確認"""
        return bool(self.youtube_api_key)
    
    def validate_x(self) -> bool:
        """X APIキーが設定されているか確認"""
        return all([
            self.x_api_key,
            self.x_api_secret,
            self.x_access_token,
            self.x_access_token_secret
        ])


@lru_cache()
def get_config() -> Config:
    """設定のシングルトンインスタンスを取得"""
    return Config()
