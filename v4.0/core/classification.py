#!/usr/bin/env python3
"""
書類分類エンジン v4.0
高精度書類種別判定システム
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    """分類結果を表すデータクラス"""
    document_type: str
    confidence: float
    matched_keywords: List[str]
    classification_method: str

class DocumentClassifier:
    """書類分類のメインクラス"""
    
    def __init__(self):
        """初期化"""
        # 書類分類の優先度付きキーワード辞書
        self.classification_rules = {
            # 申告書類（0000番台）
            "0000_納付税額一覧表": {
                "priority": 10,
                "exact_keywords": ["納付税額一覧表", "税額一覧", "納付一覧"],
                "partial_keywords": ["納付税額", "税額一覧"],
                "exclude_keywords": []
            },
            "0001_法人税及び地方法人税申告書": {
                "priority": 10,
                "exact_keywords": [
                    "法人税及び地方法人税申告書",
                    "内国法人の確定申告",
                    "法人税申告書別表一",
                    "申告書第一表"
                ],
                "partial_keywords": ["法人税申告", "内国法人", "確定申告"],
                "exclude_keywords": ["添付資料", "資料", "別添", "参考"]
            },
            "0002_添付資料_法人税": {
                "priority": 8,
                "exact_keywords": ["法人税 添付資料", "添付資料 法人税"],
                "partial_keywords": ["添付資料", "法人税 資料", "申告資料"],
                "exclude_keywords": ["消費税", "地方税"]
            },
            "0003_受信通知_法人税": {
                "priority": 9,
                "exact_keywords": ["法人税 受信通知", "受信通知 法人税"],
                "partial_keywords": ["受信通知", "国税電子申告"],
                "exclude_keywords": ["消費税", "地方税"]
            },
            "0004_納付情報_法人税": {
                "priority": 9,
                "exact_keywords": ["法人税 納付情報", "納付情報 法人税"],
                "partial_keywords": ["納付情報", "納付書", "国税 納付"],
                "exclude_keywords": ["消費税", "地方税"]
            },
            
            # 都道府県関連（1000番台）
            "1001_都道府県_法人都道府県民税・事業税・特別法人事業税": {
                "priority": 9,
                "exact_keywords": [
                    "法人都道府県民税・事業税・特別法人事業税申告書",
                    "法人事業税申告書",
                    "都道府県民税申告書"
                ],
                "partial_keywords": ["都道府県民税", "法人事業税", "特別法人事業税"],
                "exclude_keywords": ["市町村", "市民税"]
            },
            "1003_受信通知_都道府県": {
                "priority": 8,
                "exact_keywords": ["都道府県 受信通知"],
                "partial_keywords": ["受信通知", "地方税電子申告"],
                "exclude_keywords": ["市町村", "国税"]
            },
            "1004_納付情報_都道府県": {
                "priority": 8,
                "exact_keywords": ["都道府県 納付情報"],
                "partial_keywords": ["納付情報", "地方税 納付"],
                "exclude_keywords": ["市町村", "国税"]
            },
            
            # 市町村関連（2000番台）
            "2001_市町村_法人市民税": {
                "priority": 9,
                "exact_keywords": ["法人市民税申告書", "市民税申告書"],
                "partial_keywords": ["法人市民税", "市町村民税"],
                "exclude_keywords": ["都道府県", "事業税"]
            },
            "2003_受信通知_市町村": {
                "priority": 8,
                "exact_keywords": ["市町村 受信通知"],
                "partial_keywords": ["受信通知", "地方税電子申告"],
                "exclude_keywords": ["都道府県", "国税"]
            },
            "2004_納付情報_市町村": {
                "priority": 8,
                "exact_keywords": ["市町村 納付情報"],
                "partial_keywords": ["納付情報", "地方税 納付"],
                "exclude_keywords": ["都道府県", "国税"]
            },
            
            # 消費税関連（3000番台）
            "3001_消費税申告書": {
                "priority": 10,
                "exact_keywords": ["消費税申告書", "消費税及び地方消費税申告書"],
                "partial_keywords": ["消費税申告", "地方消費税"],
                "exclude_keywords": ["法人税", "添付資料"]
            },
            "3002_添付資料_消費税": {
                "priority": 8,
                "exact_keywords": ["消費税 添付資料", "添付資料 消費税"],
                "partial_keywords": ["添付資料", "消費税 資料"],
                "exclude_keywords": ["法人税", "地方税", "勘定科目別", "税区分集計表"]
            },
            "3003_受信通知_消費税": {
                "priority": 9,
                "exact_keywords": ["消費税 受信通知", "受信通知 消費税"],
                "partial_keywords": ["受信通知", "国税電子申告"],
                "exclude_keywords": ["法人税", "地方税"]
            },
            "3004_納付情報_消費税": {
                "priority": 9,
                "exact_keywords": ["消費税 納付情報", "納付情報 消費税"],
                "partial_keywords": ["納付情報", "納付書"],
                "exclude_keywords": ["法人税", "地方税"]
            },
            
            # 会計書類（5000番台）
            "5001_決算書": {
                "priority": 9,
                "exact_keywords": ["決算書", "貸借対照表", "損益計算書"],
                "partial_keywords": ["決算", "B/S", "P/L"],
                "exclude_keywords": []
            },
            "5002_総勘定元帳": {
                "priority": 9,
                "exact_keywords": ["総勘定元帳"],
                "partial_keywords": ["総勘定", "元帳"],
                "exclude_keywords": ["補助元帳", "補助"]
            },
            "5003_補助元帳": {
                "priority": 9,
                "exact_keywords": ["補助元帳"],
                "partial_keywords": ["補助元帳", "補助"],
                "exclude_keywords": ["総勘定"]
            },
            "5004_残高試算表": {
                "priority": 9,
                "exact_keywords": ["残高試算表", "試算表"],
                "partial_keywords": ["残高試算", "試算表"],
                "exclude_keywords": []
            },
            "5005_仕訳帳": {
                "priority": 9,
                "exact_keywords": ["仕訳帳"],
                "partial_keywords": ["仕訳"],
                "exclude_keywords": []
            },
            
            # 固定資産関連（6000番台）
            "6001_固定資産台帳": {
                "priority": 9,
                "exact_keywords": ["固定資産台帳"],
                "partial_keywords": ["固定資産台帳", "資産台帳"],
                "exclude_keywords": []
            },
            "6002_一括償却資産明細表": {
                "priority": 9,
                "exact_keywords": ["一括償却資産明細表"],
                "partial_keywords": ["一括償却", "償却資産明細"],
                "exclude_keywords": ["少額"]
            },
            "6003_少額減価償却資産明細表": {
                "priority": 9,
                "exact_keywords": ["少額減価償却資産明細表"],
                "partial_keywords": ["少額減価償却", "少額償却"],
                "exclude_keywords": ["一括"]
            },
            
            # 税区分関連（7000番台）- 重要な修正
            "7001_勘定科目別税区分集計表": {
                "priority": 10,
                "exact_keywords": ["勘定科目別税区分集計表"],
                "partial_keywords": ["勘定科目別税区分", "勘定科目別", "科目別税区分"],
                "exclude_keywords": []
            },
            "7002_税区分集計表": {
                "priority": 9,
                "exact_keywords": ["税区分集計表"],
                "partial_keywords": ["税区分集計", "区分集計"],
                "exclude_keywords": ["勘定科目別", "科目別"]  # 重要：勘定科目別を含む場合は除外
            }
        }

    def classify_document(self, text: str, filename: str = "") -> ClassificationResult:
        """書類を分類"""
        # テキストの前処理
        text_cleaned = self._preprocess_text(text)
        filename_cleaned = self._preprocess_text(filename)
        combined_text = f"{text_cleaned} {filename_cleaned}"
        
        best_match = None
        best_score = 0
        best_keywords = []
        best_method = "keyword_matching"
        
        # 各分類ルールに対してスコア計算
        for doc_type, rules in self.classification_rules.items():
            score, matched_keywords = self._calculate_score(combined_text, rules)
            
            if score > best_score:
                best_score = score
                best_match = doc_type
                best_keywords = matched_keywords
        
        # 信頼度を計算（0.0-1.0）
        confidence = min(best_score / 10.0, 1.0)
        
        # 分類できない場合のデフォルト
        if not best_match or confidence < 0.3:
            best_match = "0000_未分類"
            confidence = 0.0
            best_method = "default"
        
        return ClassificationResult(
            document_type=best_match,
            confidence=confidence,
            matched_keywords=best_keywords,
            classification_method=best_method
        )

    def _preprocess_text(self, text: str) -> str:
        """テキストの前処理"""
        if not text:
            return ""
        
        # 不要な空白・改行を除去
        cleaned = re.sub(r'\s+', ' ', text)
        
        # 全角英数字を半角に変換
        cleaned = cleaned.translate(str.maketrans(
            '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        ))
        
        return cleaned.strip()

    def _calculate_score(self, text: str, rules: Dict) -> Tuple[float, List[str]]:
        """分類ルールに基づいてスコアを計算"""
        score = 0
        matched_keywords = []
        
        # 除外キーワードチェック（優先）
        for exclude_keyword in rules.get("exclude_keywords", []):
            if exclude_keyword in text:
                return 0, []  # 除外キーワードが含まれている場合はスコア0
        
        # 完全一致キーワード（高スコア）
        for exact_keyword in rules.get("exact_keywords", []):
            if exact_keyword in text:
                score += rules.get("priority", 5) * 2
                matched_keywords.append(exact_keyword)
        
        # 部分一致キーワード（中スコア）
        for partial_keyword in rules.get("partial_keywords", []):
            if partial_keyword in text:
                score += rules.get("priority", 5) * 1
                matched_keywords.append(partial_keyword)
        
        return score, matched_keywords

    def classify_with_municipality_info(self, text: str, filename: str, 
                                      prefecture_code: Optional[int] = None,
                                      municipality_code: Optional[int] = None) -> ClassificationResult:
        """自治体情報を考慮した分類"""
        # 基本分類を実行
        base_result = self.classify_document(text, filename)
        
        # 自治体関連書類の場合、連番を調整
        if prefecture_code and base_result.document_type.startswith("1001_"):
            # 都道府県番台の連番調整
            base_code = base_result.document_type.split("_", 1)
            if len(base_code) == 2:
                new_code = f"{prefecture_code}_{base_code[1]}"
                base_result.document_type = new_code
        
        if municipality_code and base_result.document_type.startswith("2001_"):
            # 市町村番台の連番調整
            base_code = base_result.document_type.split("_", 1)
            if len(base_code) == 2:
                new_code = f"{municipality_code}_{base_code[1]}"
                base_result.document_type = new_code
        
        return base_result

    def get_document_category(self, document_type: str) -> str:
        """書類分類からカテゴリを取得"""
        if document_type.startswith("0"):
            return "申告書類"
        elif document_type.startswith("1"):
            return "都道府県関連"
        elif document_type.startswith("2"):
            return "市町村関連"
        elif document_type.startswith("3"):
            return "消費税関連"
        elif document_type.startswith("5"):
            return "会計書類"
        elif document_type.startswith("6"):
            return "固定資産関連"
        elif document_type.startswith("7"):
            return "税区分関連"
        else:
            return "その他"

if __name__ == "__main__":
    # テスト用
    classifier = DocumentClassifier()
    print("書類分類エンジン v4.0 初期化完了")