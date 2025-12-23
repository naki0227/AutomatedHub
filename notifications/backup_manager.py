"""
バックアップ管理モジュール
プロジェクトファイルの定期バックアップ
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional

from core.utils import logger, ensure_dir
from core.config import get_config


@dataclass
class BackupInfo:
    """バックアップ情報"""
    name: str
    path: Path
    size_mb: float
    created_at: str


class BackupManager:
    """
    バックアップ管理
    
    機能:
    - ローカルバックアップ（zip圧縮）
    - iCloud Drive連携
    - Git リポジトリのミラー
    """
    
    def __init__(self):
        config = get_config()
        self.backup_dir = Path.home() / "Backups" / "automated"
        ensure_dir(self.backup_dir)
        logger.info("BackupManager initialized")
    
    def backup_project(
        self,
        project_path: Path,
        name: Optional[str] = None
    ) -> BackupInfo:
        """
        プロジェクトをzip圧縮してバックアップ
        
        Args:
            project_path: バックアップ対象のプロジェクトパス
            name: バックアップ名（省略時はディレクトリ名）
        """
        project_path = Path(project_path)
        
        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_path}")
        
        if name is None:
            name = project_path.name
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        logger.info(f"Creating backup: {backup_name}")
        
        # zip圧縮
        shutil.make_archive(
            str(backup_path),
            "zip",
            project_path.parent,
            project_path.name
        )
        
        actual_path = Path(f"{backup_path}.zip")
        size_mb = actual_path.stat().st_size / (1024 * 1024)
        
        logger.info(f"Backup created: {actual_path} ({size_mb:.2f} MB)")
        
        return BackupInfo(
            name=backup_name,
            path=actual_path,
            size_mb=round(size_mb, 2),
            created_at=datetime.now().isoformat()
        )
    
    def backup_to_icloud(
        self,
        project_path: Path,
        name: Optional[str] = None
    ) -> Optional[BackupInfo]:
        """
        iCloud Driveにバックアップ
        
        macOS限定。iCloud Driveが有効な場合のみ動作。
        """
        icloud_path = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Backups"
        
        if not icloud_path.parent.exists():
            logger.warning("iCloud Drive not available")
            return None
        
        ensure_dir(icloud_path)
        
        project_path = Path(project_path)
        
        if name is None:
            name = project_path.name
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}"
        backup_path = icloud_path / backup_name
        
        logger.info(f"Creating iCloud backup: {backup_name}")
        
        shutil.make_archive(
            str(backup_path),
            "zip",
            project_path.parent,
            project_path.name
        )
        
        actual_path = Path(f"{backup_path}.zip")
        size_mb = actual_path.stat().st_size / (1024 * 1024)
        
        logger.info(f"iCloud backup created: {actual_path}")
        
        return BackupInfo(
            name=backup_name,
            path=actual_path,
            size_mb=round(size_mb, 2),
            created_at=datetime.now().isoformat()
        )
    
    def git_mirror(
        self,
        project_path: Path,
        remote_url: Optional[str] = None
    ) -> bool:
        """
        GitリポジトリをリモートにPush
        """
        project_path = Path(project_path)
        
        if not (project_path / ".git").exists():
            logger.warning("Not a git repository")
            return False
        
        try:
            # 未コミットの変更があるか確認
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            
            if status.stdout.strip():
                logger.warning("Uncommitted changes exist")
            
            # Push
            result = subprocess.run(
                ["git", "push", "--all"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Git push successful")
                return True
            else:
                logger.error(f"Git push failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Git mirror failed: {e}")
            return False
    
    def list_backups(self) -> List[BackupInfo]:
        """バックアップ一覧を取得"""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.zip"):
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            backups.append(BackupInfo(
                name=backup_file.stem,
                path=backup_file,
                size_mb=round(size_mb, 2),
                created_at=mtime.isoformat()
            ))
        
        return sorted(backups, key=lambda x: x.created_at, reverse=True)
    
    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """古いバックアップを削除"""
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            return 0
        
        deleted = 0
        for backup in backups[keep_count:]:
            try:
                backup.path.unlink()
                deleted += 1
                logger.info(f"Deleted old backup: {backup.name}")
            except Exception as e:
                logger.warning(f"Failed to delete backup: {backup.name}, {e}")
        
        return deleted
