"""
AIコードレビューモジュール
PRのdiffをGeminiで分析
"""
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import subprocess

from core.utils import logger
from ai.gemini_client import GeminiClient


@dataclass
class ReviewComment:
    """レビューコメント"""
    severity: str  # info, warning, error
    file: str
    line: Optional[int]
    message: str
    suggestion: Optional[str]


@dataclass
class ReviewResult:
    """レビュー結果"""
    summary: str
    comments: List[ReviewComment]
    approval_status: str  # approved, changes_requested, needs_discussion
    score: int  # 1-10


class CodeReviewer:
    """
    AIコードレビュー
    
    機能:
    - Gitのdiffを取得してGeminiで分析
    - 問題点・改善提案を生成
    - PRコメント形式で出力
    """
    
    def __init__(self):
        self.gemini = GeminiClient()
        logger.info("CodeReviewer initialized")
    
    def review_diff(
        self,
        project_path: Path,
        base_branch: str = "main",
        target_branch: str = "HEAD"
    ) -> ReviewResult:
        """
        Git diffをレビュー
        
        Args:
            project_path: リポジトリパス
            base_branch: 比較元ブランチ
            target_branch: 比較先ブランチ
        """
        logger.info(f"Reviewing diff: {base_branch}..{target_branch}")
        
        # diffを取得
        diff = self._get_git_diff(project_path, base_branch, target_branch)
        
        if not diff:
            return ReviewResult(
                summary="No changes to review",
                comments=[],
                approval_status="approved",
                score=10
            )
        
        return self._analyze_diff(diff)
    
    def review_file(self, file_path: Path) -> ReviewResult:
        """単一ファイルをレビュー"""
        logger.info(f"Reviewing file: {file_path}")
        
        if not file_path.exists():
            return ReviewResult(
                summary="File not found",
                comments=[],
                approval_status="changes_requested",
                score=0
            )
        
        content = file_path.read_text(encoding="utf-8")
        return self._analyze_code(content, str(file_path))
    
    def review_staged_changes(self, project_path: Path) -> ReviewResult:
        """ステージ済み変更をレビュー"""
        logger.info("Reviewing staged changes")
        
        diff = self._get_git_diff(project_path, "--cached")
        
        if not diff:
            return ReviewResult(
                summary="No staged changes",
                comments=[],
                approval_status="approved",
                score=10
            )
        
        return self._analyze_diff(diff)
    
    def _get_git_diff(
        self,
        project_path: Path,
        base: str,
        target: str = ""
    ) -> str:
        """Git diffを取得"""
        try:
            cmd = ["git", "diff", base]
            if target:
                cmd.append(target)
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to get git diff: {e}")
            return ""
    
    def _analyze_diff(self, diff: str) -> ReviewResult:
        """Geminiでdiffを分析"""
        
        # diffが長すぎる場合は分割
        if len(diff) > 10000:
            diff = diff[:10000] + "\n... (truncated)"
        
        prompt = f"""
以下のGit diffをコードレビューしてください。

```diff
{diff}
```

以下の観点で分析してください:
1. バグや潜在的な問題
2. セキュリティ上の懸念
3. パフォーマンスの問題
4. コードスタイル・可読性
5. 改善提案

出力形式（JSON）:
{{
    "summary": "変更の概要と総評",
    "comments": [
        {{
            "severity": "error/warning/info",
            "file": "ファイル名",
            "line": 行番号またはnull,
            "message": "問題点",
            "suggestion": "改善案"
        }}
    ],
    "approval_status": "approved/changes_requested/needs_discussion",
    "score": 1-10
}}
"""
        
        response = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="あなたは経験豊富なソフトウェアエンジニアです。厳密かつ建設的なコードレビューを行います。",
            temperature=0.3
        )
        
        return self._parse_review_response(response)
    
    def _analyze_code(self, code: str, filename: str) -> ReviewResult:
        """コードを分析"""
        
        prompt = f"""
以下のコード ({filename}) をレビューしてください。

```
{code}
```

以下の観点で分析してください:
1. バグや潜在的な問題
2. セキュリティ上の懸念
3. パフォーマンスの問題
4. コードスタイル・可読性
5. 改善提案

出力形式（JSON）:
{{
    "summary": "コードの概要と総評",
    "comments": [
        {{
            "severity": "error/warning/info",
            "file": "{filename}",
            "line": 行番号またはnull,
            "message": "問題点",
            "suggestion": "改善案"
        }}
    ],
    "approval_status": "approved/changes_requested/needs_discussion",
    "score": 1-10
}}
"""
        
        response = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="あなたは経験豊富なソフトウェアエンジニアです。厳密かつ建設的なコードレビューを行います。",
            temperature=0.3
        )
        
        return self._parse_review_response(response)
    
    def _parse_review_response(self, response: str) -> ReviewResult:
        """レビュー結果をパース"""
        import json
        
        try:
            # コードブロックを除去
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            
            data = json.loads(clean)
            
            comments = [
                ReviewComment(
                    severity=c.get("severity", "info"),
                    file=c.get("file", ""),
                    line=c.get("line"),
                    message=c.get("message", ""),
                    suggestion=c.get("suggestion")
                )
                for c in data.get("comments", [])
            ]
            
            return ReviewResult(
                summary=data.get("summary", ""),
                comments=comments,
                approval_status=data.get("approval_status", "needs_discussion"),
                score=data.get("score", 5)
            )
            
        except json.JSONDecodeError:
            return ReviewResult(
                summary=response,
                comments=[],
                approval_status="needs_discussion",
                score=5
            )
