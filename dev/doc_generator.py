"""
ドキュメント自動生成モジュール
コードからREADME、API仕様書を生成
"""
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from core.utils import logger, write_file
from ai.gemini_client import GeminiClient


@dataclass
class GeneratedDoc:
    """生成されたドキュメント"""
    title: str
    content: str
    path: Path


class DocGenerator:
    """
    ドキュメント自動生成
    
    機能:
    - コードからREADME生成
    - API仕様書生成
    - 関数・クラスのdocstring生成
    """
    
    def __init__(self):
        self.gemini = GeminiClient()
        logger.info("DocGenerator initialized")
    
    def generate_readme(
        self,
        project_path: Path,
        output_path: Optional[Path] = None
    ) -> GeneratedDoc:
        """
        プロジェクトからREADMEを生成
        
        Args:
            project_path: プロジェクトルート
            output_path: 出力先（省略時はproject_path/README.md）
        """
        logger.info(f"Generating README for: {project_path}")
        
        # プロジェクト情報を収集
        project_info = self._collect_project_info(project_path)
        
        prompt = f"""
以下のプロジェクト情報からREADME.mdを生成してください。

プロジェクト情報:
{project_info}

以下のセクションを含めてください:
- プロジェクト名と概要
- 主な機能
- インストール方法
- 使い方（コード例付き）
- ディレクトリ構造（簡潔に）
- ライセンス（MITと仮定）

マークダウン形式で出力してください。
"""
        
        content = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="あなたは技術ドキュメントライターです。簡潔で分かりやすいREADMEを作成します。",
            max_tokens=3000,
            temperature=0.5
        )
        
        if output_path is None:
            output_path = project_path / "README.md"
        
        write_file(output_path, content)
        logger.info(f"README generated: {output_path}")
        
        return GeneratedDoc(
            title="README.md",
            content=content,
            path=output_path
        )
    
    def generate_api_docs(
        self,
        source_path: Path,
        output_path: Optional[Path] = None
    ) -> GeneratedDoc:
        """
        ソースコードからAPI仕様書を生成
        
        Args:
            source_path: ソースファイルまたはディレクトリ
            output_path: 出力先
        """
        logger.info(f"Generating API docs for: {source_path}")
        
        # ソースコードを収集
        source_code = self._collect_source_code(source_path)
        
        prompt = f"""
以下のソースコードからAPI仕様書を生成してください。

```python
{source_code}
```

以下の形式でドキュメントを作成:
- 各クラス・関数の説明
- パラメータと戻り値
- 使用例
- 注意事項

マークダウン形式で出力してください。
"""
        
        content = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="あなたは技術ドキュメントライターです。APIドキュメントを作成します。",
            max_tokens=4000,
            temperature=0.3
        )
        
        if output_path is None:
            output_path = source_path.parent / "API.md"
        
        write_file(output_path, content)
        logger.info(f"API docs generated: {output_path}")
        
        return GeneratedDoc(
            title="API Documentation",
            content=content,
            path=output_path
        )
    
    def generate_docstrings(self, file_path: Path) -> str:
        """
        Pythonファイルにdocstringを追加
        
        Args:
            file_path: 対象ファイル
        
        Returns:
            docstring付きのコード
        """
        logger.info(f"Generating docstrings for: {file_path}")
        
        content = file_path.read_text(encoding="utf-8")
        
        prompt = f"""
以下のPythonコードにdocstringを追加してください。
既存のdocstringは改善し、ない場合は追加してください。
Google styleのdocstringを使用してください。

```python
{content}
```

docstring付きの完全なコードを出力してください。
"""
        
        result = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="Pythonのdocstringを追加するエキスパートです。Google styleを使用します。",
            max_tokens=5000,
            temperature=0.2
        )
        
        # コードブロックを除去
        if "```python" in result:
            result = result.split("```python")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        
        return result.strip()
    
    def _collect_project_info(self, project_path: Path) -> str:
        """プロジェクト情報を収集"""
        info_parts = []
        
        # ディレクトリ構造
        info_parts.append("ディレクトリ構造:")
        for item in sorted(project_path.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                info_parts.append(f"  {item.name}/")
            else:
                info_parts.append(f"  {item.name}")
        
        # requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            info_parts.append("\n依存パッケージ:")
            info_parts.append(req_file.read_text()[:500])
        
        # pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            info_parts.append("\npyproject.toml (抜粋):")
            info_parts.append(pyproject.read_text()[:500])
        
        # pubspec.yaml (Flutter)
        pubspec = project_path / "pubspec.yaml"
        if pubspec.exists():
            info_parts.append("\npubspec.yaml (抜粋):")
            info_parts.append(pubspec.read_text()[:500])
        
        return "\n".join(info_parts)
    
    def _collect_source_code(self, source_path: Path, max_chars: int = 8000) -> str:
        """ソースコードを収集"""
        if source_path.is_file():
            content = source_path.read_text(encoding="utf-8")
            return content[:max_chars]
        
        # ディレクトリの場合は全てのPythonファイルを収集
        codes = []
        remaining = max_chars
        
        for py_file in sorted(source_path.rglob("*.py")):
            if remaining <= 0:
                break
            
            content = py_file.read_text(encoding="utf-8")
            codes.append(f"# {py_file.name}\n{content[:remaining]}")
            remaining -= len(content)
        
        return "\n\n".join(codes)
