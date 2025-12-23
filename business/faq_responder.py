"""
問い合わせ対応モジュール
よくある質問への自動返信テンプレート生成
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import json

from core.utils import logger, ensure_dir
from core.config import get_config
from ai.gemini_client import GeminiClient


@dataclass
class FAQItem:
    """FAQ項目"""
    category: str
    question: str
    answer: str
    keywords: List[str]


@dataclass
class ResponseSuggestion:
    """返信提案"""
    question: str
    suggested_response: str
    confidence: float
    matched_faq: Optional[str]


class FAQResponder:
    """
    問い合わせ対応
    
    機能:
    - FAQデータベース管理
    - 質問に対する回答提案
    - カスタム返信テンプレート生成
    """
    
    def __init__(self):
        config = get_config()
        self.faq_file = config.project_root / "business" / "faq.json"
        ensure_dir(self.faq_file.parent)
        self.gemini = GeminiClient()
        self._load_faq()
        logger.info("FAQResponder initialized")
    
    def _load_faq(self):
        """FAQを読み込み"""
        self.faq_items: List[FAQItem] = []
        
        if self.faq_file.exists():
            with open(self.faq_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.faq_items = [FAQItem(**item) for item in data]
    
    def _save_faq(self):
        """FAQを保存"""
        with open(self.faq_file, "w", encoding="utf-8") as f:
            data = [
                {
                    "category": item.category,
                    "question": item.question,
                    "answer": item.answer,
                    "keywords": item.keywords
                }
                for item in self.faq_items
            ]
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_faq(
        self,
        category: str,
        question: str,
        answer: str,
        keywords: List[str]
    ) -> FAQItem:
        """FAQを追加"""
        item = FAQItem(
            category=category,
            question=question,
            answer=answer,
            keywords=keywords
        )
        self.faq_items.append(item)
        self._save_faq()
        logger.info(f"FAQ added: {question[:30]}...")
        return item
    
    def suggest_response(self, question: str) -> ResponseSuggestion:
        """
        質問に対する回答を提案
        
        Args:
            question: ユーザーからの質問
        
        Returns:
            ResponseSuggestion
        """
        logger.info(f"Suggesting response for: {question[:50]}...")
        
        # まずFAQから検索
        matched = self._search_faq(question)
        
        if matched and matched[1] > 0.7:
            # 高い確信度でマッチ
            return ResponseSuggestion(
                question=question,
                suggested_response=matched[0].answer,
                confidence=matched[1],
                matched_faq=matched[0].question
            )
        
        # AIで回答を生成
        response = self._generate_response(question, matched[0] if matched else None)
        
        return ResponseSuggestion(
            question=question,
            suggested_response=response,
            confidence=0.5,
            matched_faq=matched[0].question if matched else None
        )
    
    def _search_faq(self, question: str) -> Optional[tuple]:
        """FAQからキーワードマッチで検索"""
        if not self.faq_items:
            return None
        
        question_lower = question.lower()
        best_match = None
        best_score = 0
        
        for item in self.faq_items:
            # キーワードマッチ
            matches = sum(1 for kw in item.keywords if kw.lower() in question_lower)
            score = matches / len(item.keywords) if item.keywords else 0
            
            if score > best_score:
                best_score = score
                best_match = item
        
        if best_match:
            return (best_match, best_score)
        return None
    
    def _generate_response(
        self,
        question: str,
        hint: Optional[FAQItem]
    ) -> str:
        """AIで回答を生成"""
        
        faq_context = ""
        if self.faq_items:
            faq_context = "参考FAQ:\n"
            for item in self.faq_items[:5]:
                faq_context += f"Q: {item.question}\nA: {item.answer}\n\n"
        
        prompt = f"""
以下のユーザーからの問い合わせに対する丁寧な返信を作成してください。

問い合わせ:
{question}

{faq_context}

以下のポイントを守ってください:
- 丁寧かつ簡潔に
- 具体的な解決策があれば提示
- 不明な点は正直に伝える
- 最後に追加の質問がないか確認
"""
        
        return self.gemini.generate_text(
            prompt=prompt,
            system_instruction="カスタマーサポート担当として、親切で的確な回答を行います。",
            max_tokens=500,
            temperature=0.5
        )
    
    def generate_faq_from_questions(
        self,
        questions: List[str],
        app_description: str
    ) -> List[FAQItem]:
        """質問リストからFAQを自動生成"""
        
        prompt = f"""
以下のアプリと質問リストから、FAQを生成してください。

アプリ説明:
{app_description}

よくある質問:
{chr(10).join(questions)}

出力形式（JSON配列）:
[
    {{
        "category": "カテゴリ",
        "question": "質問",
        "answer": "回答",
        "keywords": ["キーワード1", "キーワード2"]
    }}
]
"""
        
        response = self.gemini.generate_text(
            prompt=prompt,
            system_instruction="FAQを作成するエキスパートです。",
            max_tokens=2000,
            temperature=0.5
        )
        
        # パース
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            
            items_data = json.loads(clean)
            items = [FAQItem(**item) for item in items_data]
            
            # 保存
            self.faq_items.extend(items)
            self._save_faq()
            
            return items
        except json.JSONDecodeError:
            logger.error("Failed to parse FAQ JSON")
            return []
    
    def list_faq(self) -> List[FAQItem]:
        """FAQ一覧を取得"""
        return self.faq_items
