"""
App Store提出自動化モジュール
fastlaneと連携してiOSアプリをApp Storeに提出
"""
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from core.utils import logger, print_success, print_error


@dataclass
class DeployResult:
    """デプロイ結果"""
    success: bool
    message: str
    build_number: Optional[str] = None
    version: Optional[str] = None


class AppStoreDeployer:
    """
    App Store提出自動化
    
    前提条件:
    - fastlaneがインストール済み
    - Fastfileが設定済み
    - App Store Connect APIキーが設定済み
    """
    
    def __init__(self):
        self._check_fastlane()
        logger.info("AppStoreDeployer initialized")
    
    def _check_fastlane(self):
        """fastlaneがインストールされているか確認"""
        try:
            result = subprocess.run(
                ["fastlane", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning("fastlane not properly configured")
        except FileNotFoundError:
            logger.warning("fastlane not installed. Install with: brew install fastlane")
    
    def build_and_upload(
        self,
        project_path: Path,
        lane: str = "release"
    ) -> DeployResult:
        """
        ビルドしてApp Store Connectにアップロード
        
        Args:
            project_path: Flutterプロジェクトパス
            lane: fastlane lane名
        """
        logger.info(f"Building and uploading: {project_path}")
        
        ios_path = project_path / "ios"
        if not ios_path.exists():
            return DeployResult(
                success=False,
                message="iOS directory not found"
            )
        
        # Flutter build
        flutter_result = self._run_flutter_build(project_path)
        if not flutter_result.success:
            return flutter_result
        
        # fastlane upload
        return self._run_fastlane(ios_path, lane)
    
    def _run_flutter_build(self, project_path: Path) -> DeployResult:
        """Flutter iOS build"""
        logger.info("Running flutter build ios...")
        
        try:
            result = subprocess.run(
                ["flutter", "build", "ios", "--release", "--no-codesign"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=1800  # 30分タイムアウト
            )
            
            if result.returncode == 0:
                print_success("Flutter build completed")
                return DeployResult(success=True, message="Build successful")
            else:
                print_error("Flutter build failed")
                return DeployResult(
                    success=False,
                    message=f"Build failed: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return DeployResult(
                success=False,
                message="Build timed out after 30 minutes"
            )
    
    def _run_fastlane(self, ios_path: Path, lane: str) -> DeployResult:
        """fastlane実行"""
        logger.info(f"Running fastlane {lane}...")
        
        try:
            result = subprocess.run(
                ["fastlane", lane],
                cwd=ios_path,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode == 0:
                print_success(f"fastlane {lane} completed")
                return DeployResult(
                    success=True,
                    message=f"Upload successful"
                )
            else:
                print_error(f"fastlane {lane} failed")
                return DeployResult(
                    success=False,
                    message=f"fastlane failed: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return DeployResult(
                success=False,
                message="fastlane timed out after 30 minutes"
            )
        except FileNotFoundError:
            return DeployResult(
                success=False,
                message="fastlane not installed"
            )
    
    def update_metadata(
        self,
        ios_path: Path,
        version: str,
        release_notes: str
    ) -> DeployResult:
        """
        メタデータを更新
        
        Args:
            ios_path: iOSプロジェクトパス
            version: バージョン番号
            release_notes: リリースノート
        """
        logger.info(f"Updating metadata: v{version}")
        
        # fastlane metadataディレクトリを更新
        metadata_path = ios_path / "fastlane" / "metadata" / "ja"
        
        if not metadata_path.exists():
            metadata_path.mkdir(parents=True, exist_ok=True)
        
        # release_notes.txt を更新
        release_notes_path = metadata_path / "release_notes.txt"
        release_notes_path.write_text(release_notes, encoding="utf-8")
        
        logger.info(f"Release notes updated: {release_notes_path}")
        
        return DeployResult(
            success=True,
            message="Metadata updated",
            version=version
        )
