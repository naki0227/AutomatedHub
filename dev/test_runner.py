"""
テスト自動実行モジュール
Python (pytest) と Flutter (flutter test) に対応
"""
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import json

from core.utils import logger, print_success, print_error


@dataclass
class TestResult:
    """テスト結果"""
    success: bool
    passed: int
    failed: int
    skipped: int
    duration: float
    output: str
    errors: List[str]


class TestRunner:
    """
    テスト自動実行
    
    対応:
    - Python (pytest)
    - Dart/Flutter (flutter test)
    """
    
    def __init__(self):
        logger.info("TestRunner initialized")
    
    def run_python_tests(
        self,
        project_path: Path,
        test_path: Optional[str] = None,
        verbose: bool = True,
        coverage: bool = False
    ) -> TestResult:
        """
        Pythonテストを実行 (pytest)
        
        Args:
            project_path: プロジェクトルート
            test_path: テストディレクトリ（省略時は tests/）
            verbose: 詳細出力
            coverage: カバレッジを計測
        """
        logger.info(f"Running Python tests: {project_path}")
        
        cmd = ["python", "-m", "pytest"]
        
        if test_path:
            cmd.append(test_path)
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend(["--cov", "--cov-report=term-missing"])
        
        # JSON出力を追加
        cmd.extend(["--tb=short", "-q"])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )
            
            return self._parse_pytest_output(result)
            
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                passed=0,
                failed=0,
                skipped=0,
                duration=300,
                output="Test timed out after 5 minutes",
                errors=["Timeout"]
            )
        except Exception as e:
            return TestResult(
                success=False,
                passed=0,
                failed=0,
                skipped=0,
                duration=0,
                output=str(e),
                errors=[str(e)]
            )
    
    def run_flutter_tests(
        self,
        project_path: Path,
        coverage: bool = False
    ) -> TestResult:
        """
        Flutterテストを実行
        
        Args:
            project_path: Flutterプロジェクトルート
            coverage: カバレッジを計測
        """
        logger.info(f"Running Flutter tests: {project_path}")
        
        cmd = ["flutter", "test"]
        
        if coverage:
            cmd.append("--coverage")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=600  # 10分タイムアウト
            )
            
            return self._parse_flutter_output(result)
            
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                passed=0,
                failed=0,
                skipped=0,
                duration=600,
                output="Test timed out after 10 minutes",
                errors=["Timeout"]
            )
        except FileNotFoundError:
            return TestResult(
                success=False,
                passed=0,
                failed=0,
                skipped=0,
                duration=0,
                output="Flutter not found. Make sure Flutter is installed.",
                errors=["Flutter not installed"]
            )
    
    def run_all_tests(self, project_path: Path) -> dict:
        """
        プロジェクトタイプを判定してテストを実行
        """
        project_path = Path(project_path)
        results = {}
        
        # Python プロジェクト判定
        if (project_path / "requirements.txt").exists() or \
           (project_path / "pyproject.toml").exists() or \
           (project_path / "tests").exists():
            results["python"] = self.run_python_tests(project_path)
        
        # Flutter プロジェクト判定
        if (project_path / "pubspec.yaml").exists():
            results["flutter"] = self.run_flutter_tests(project_path)
        
        return results
    
    def _parse_pytest_output(self, result: subprocess.CompletedProcess) -> TestResult:
        """pytest出力をパース"""
        output = result.stdout + result.stderr
        
        # 結果行を探す (e.g., "5 passed, 1 failed in 0.5s")
        passed = failed = skipped = 0
        duration = 0.0
        
        for line in output.split("\n"):
            if "passed" in line or "failed" in line:
                import re
                if match := re.search(r"(\d+) passed", line):
                    passed = int(match.group(1))
                if match := re.search(r"(\d+) failed", line):
                    failed = int(match.group(1))
                if match := re.search(r"(\d+) skipped", line):
                    skipped = int(match.group(1))
                if match := re.search(r"in ([\d.]+)s", line):
                    duration = float(match.group(1))
        
        errors = []
        if "FAILED" in output:
            # エラー行を抽出
            for line in output.split("\n"):
                if "FAILED" in line or "Error" in line:
                    errors.append(line.strip())
        
        success = result.returncode == 0
        
        if success:
            print_success(f"Tests passed: {passed} passed, {skipped} skipped")
        else:
            print_error(f"Tests failed: {failed} failed, {passed} passed")
        
        return TestResult(
            success=success,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=duration,
            output=output,
            errors=errors
        )
    
    def _parse_flutter_output(self, result: subprocess.CompletedProcess) -> TestResult:
        """Flutter test出力をパース"""
        output = result.stdout + result.stderr
        
        passed = failed = skipped = 0
        
        # Flutter test 出力から結果を抽出
        for line in output.split("\n"):
            if "All tests passed!" in line:
                # 成功時はテスト数を数える
                import re
                if match := re.search(r"(\d+) tests", output):
                    passed = int(match.group(1))
            elif "Some tests failed" in line:
                import re
                if match := re.search(r"(\d+) passed", output):
                    passed = int(match.group(1))
                if match := re.search(r"(\d+) failed", output):
                    failed = int(match.group(1))
        
        errors = []
        if result.returncode != 0:
            for line in output.split("\n"):
                if "FAILED" in line or "Exception" in line:
                    errors.append(line.strip())
        
        success = result.returncode == 0
        
        if success:
            print_success(f"Flutter tests passed: {passed}")
        else:
            print_error(f"Flutter tests failed: {failed} failed")
        
        return TestResult(
            success=success,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=0,
            output=output,
            errors=errors
        )
