#!/usr/bin/env python3
"""
書類分類エンジン v5.0
AND条件対応・高精度書類種別判定システム（完全改訂版）
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
import datetime

@dataclass
class AndCondition:
    """AND条件を表すデータクラス"""
    keywords: List[str]
    match_type: str = "all"  # "all" (すべて必要) or "any" (いずれか必要)
    
    def check_match(self, text: str) -> Tuple[bool, List[str]]:
        """AND条件のマッチングチェック"""
        matched = []
        for keyword in self.keywords:
            if keyword in text:
                matched.append(keyword)
        
        if self.match_type == "all":
            return len(matched) == len(self.keywords), matched
        else:  # "any"
            return len(matched) > 0, matched

@dataclass
class ClassificationStep:
    """分類の1ステップを表すデータクラス"""
    document_type: str
    score: float
    matched_keywords: List[str]
    excluded: bool
    exclude_reason: str = ""
    method: str = "normal"  # "highest_priority", "and_condition", "normal"

@dataclass
class ClassificationResult:
    """分類結果を表すデータクラス"""
    document_type: str
    confidence: float
    matched_keywords: List[str]
    classification_method: str
    debug_steps: List[ClassificationStep] = field(default_factory=list)
    processing_log: List[str] = field(default_factory=list)

class DocumentClassifierV5:
    """書類分類エンジン v5.0 - AND条件対応版"""
    
    def __init__(self, debug_mode: bool = False, log_callback: Optional[Callable[[str], None]] = None):
        """初期化
        
        Args:
            debug_mode: デバッグモードの有効化
            log_callback: ログ出力のコールバック関数
        """
        self.debug_mode = debug_mode
        self.log_callback = log_callback
        self.current_filename = ""
        self.processing_log = []
        
        # v5.0 新分類ルール（AND条件対応）
        self.classification_rules_v5 = self._initialize_classification_rules_v5()

    def _initialize_classification_rules_v5(self) -> Dict:
        """v5.0 分類ルール初期化（AND条件対応）"""
        return {
            # ===== 0000番台 - 国税申告書類 =====
            "0000_納付税額一覧表": {
                "priority": 140,
                "highest_priority_conditions": [
                    AndCondition(["納付税額一覧表", "既納付額"], "all"),
                    AndCondition(["納付税額一覧", "確定税額"], "all")
                ],
                "exact_keywords": ["納付税額一覧表"],
                "partial_keywords": ["納付税額", "税額一覧"],
                "exclude_keywords": ["受信通知", "納付区分番号通知", "メール詳細"]
            },
            
            "0001_法人税及び地方法人税申告書": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["事業年度分の法人税申告書", "差引確定法人税額"], "all"),
                    AndCondition(["内国法人の確定申告(青色)", "法人税額"], "all"),
                    AndCondition(["控除しきれなかった金額", "課税留保金額"], "all"),
                    AndCondition(["中間申告分の法人税額", "中間申告分の地方法人税額"], "all")
                ],
                "exact_keywords": [
                    "法人税及び地方法人税申告書", "内国法人の確定申告", "内国法人の確定申告(青色)",
                    "法人税申告書別表一", "申告書第一表"
                ],
                "partial_keywords": ["法人税申告", "内国法人", "確定申告", "青色申告", "事業年度分", "税額控除"],
                "exclude_keywords": ["メール詳細", "受信通知", "納付区分番号通知", "添付資料", "イメージ添付"],
                "filename_keywords": ["内国法人", "確定申告", "青色"]
            },
            
            "0002_添付資料_法人税": {
                "priority": 125,
                "highest_priority_conditions": [
                    AndCondition(["添付資料", "法人税申告", "イメージ添付"], "all"),
                    AndCondition(["添付書類", "法人税", "申告書"], "all")
                ],
                "exact_keywords": [
                    "法人税 添付資料", "添付資料 法人税", "イメージ添付書類(法人税申告)",
                    "イメージ添付書類 法人税", "添付書類 法人税"
                ],
                "partial_keywords": ["添付資料", "法人税 資料", "イメージ添付", "添付書類"],
                "exclude_keywords": ["消費税申告", "法人消費税", "消費税", "受信通知", "納付区分番号通知"],
                "filename_keywords": ["法人税申告", "法人税", "内国法人"]
            },
            
            "0003_受信通知_法人税": {
                "priority": 130,
                "highest_priority_conditions": [
                    AndCondition(["メール詳細", "種目 法人税及び地方法人税申告書"], "all"),
                    AndCondition(["受付番号", "税目 法人税", "受付日時"], "all"),
                    AndCondition(["提出先", "税務署", "法人税及び地方法人税申告書"], "all"),
                    AndCondition(["送信されたデータを受け付けました", "法人税"], "all")
                ],
                "exact_keywords": ["法人税 受信通知", "受信通知 法人税"],
                "partial_keywords": ["受信通知", "国税電子申告", "メール詳細"],
                "exclude_keywords": ["消費税申告書", "納付区分番号通知"],
                "filename_keywords": ["受信通知", "法人税"]
            },
            
            "0004_納付情報_法人税": {
                "priority": 130,
                "highest_priority_conditions": [
                    AndCondition(["メール詳細（納付区分番号通知）", "法人税及地方法人税"], "all"),
                    AndCondition(["納付区分番号通知", "税目 法人税及地方法人税"], "all"),
                    AndCondition(["納付先", "税務署", "法人税及地方法人税"], "all"),
                    AndCondition(["納付内容を確認し", "法人税"], "all")
                ],
                "exact_keywords": ["法人税 納付情報", "納付情報 法人税", "納付区分番号通知"],
                "partial_keywords": ["納付情報", "納付書", "国税 納付"],
                "exclude_keywords": ["消費税及地方消費税", "受信通知"],
                "filename_keywords": ["納付情報", "法人税"]
            },
            
            # ===== 1000番台 - 都道府県税関連 =====
            "1001_都道府県_法人都道府県民税・事業税・特別法人事業税": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["法人都道府県民税・事業税・特別法人事業税申告書", "年400万円以下"], "all"),
                    AndCondition(["県税事務所", "法人事業税", "特別法人事業税"], "all"),
                    AndCondition(["都税事務所", "道府県民税", "事業税"], "all"),
                    AndCondition(["法人事業税申告書", "都道府県民税"], "all")
                ],
                "exact_keywords": [
                    "法人都道府県民税・事業税・特別法人事業税申告書", "法人事業税申告書", "都道府県民税申告書"
                ],
                "partial_keywords": [
                    "都道府県民税", "法人事業税", "特別法人事業税", "道府県民税", "事業税",
                    "県税事務所", "都税事務所", "年400万円以下", "年月日から年月日までの"
                ],
                "exclude_keywords": ["市町村", "市民税", "市役所", "町役場", "村役場", "受信通知", "納付情報"],
                "filename_keywords": ["県税事務所", "都税事務所"]
            },
            
            "1003_受信通知_都道府県": {
                "priority": 130,
                "highest_priority_conditions": [
                    AndCondition(["申告受付完了通知", "都道府県民税", "事業税"], "all"),
                    AndCondition(["県税事務所", "受信通知", "法人事業税"], "all"),
                    AndCondition(["都税事務所", "受付完了通知", "特別法人事業税"], "all")
                ],
                "exact_keywords": ["都道府県 受信通知"],
                "partial_keywords": ["受信通知", "地方税電子申告"],
                "exclude_keywords": ["市町村", "市民税", "国税電子申告"],
                "filename_keywords": ["受信通知", "都道府県"]
            },
            
            "1004_納付情報_都道府県": {
                "priority": 130,
                "highest_priority_conditions": [
                    AndCondition(["納付情報発行結果", "法人二税・特別税"], "all"),
                    AndCondition(["地方税共同機構", "法人都道府県民税・事業税"], "all"),
                    AndCondition(["税目:法人二税・特別税", "納付情報が発行され"], "all"),
                    AndCondition(["ペイジー納付情報", "都道府県民税"], "all")
                ],
                "exact_keywords": ["都道府県 納付情報", "納付情報発行結果", "地方税共同機構"],
                "partial_keywords": ["納付情報", "地方税 納付", "法人二税", "特別税"],
                "exclude_keywords": ["市役所", "町役場", "村役場", "法人市民税", "国税"],
                "filename_keywords": ["納付情報", "都道府県"]
            },
            
            # ===== 2000番台 - 市町村税関連 =====
            "2001_市町村_法人市民税": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["法人市民税申告書", "市役所", "均等割"], "all"),
                    AndCondition(["市町村民税", "法人税割", "申告納付税額"], "all"),
                    AndCondition(["法人市民税", "課税標準総額", "市長"], "all")
                ],
                "exact_keywords": ["法人市民税申告書", "市民税申告書"],
                "partial_keywords": ["法人市民税", "市町村民税", "市役所", "町役場", "村役場"],
                "exclude_keywords": ["都道府県", "事業税", "県税事務所", "都税事務所", "受信通知", "納付情報"],
                "filename_keywords": ["市役所", "市民税"]
            },
            
            "2003_受信通知_市町村": {
                "priority": 140,
                "highest_priority_conditions": [
                    AndCondition(["申告受付完了通知", "法人市町村民税"], "all"),
                    AndCondition(["申告受付完了通知", "法人市民税"], "all"),
                    AndCondition(["法人市民税", "市役所", "申告受付完了通知"], "all"),
                    AndCondition(["市長", "法人市民税", "受付完了通知"], "all"),
                    # 具体的な市町村名での判定
                    AndCondition(["蒲郡市役所", "申告受付完了通知"], "all"),
                    AndCondition(["福岡市", "法人市民税", "受付番号"], "all")
                ],
                "exact_keywords": ["市町村 受信通知", "申告受付完了通知"],
                "partial_keywords": ["受信通知", "地方税電子申告", "市役所"],
                "exclude_keywords": ["県税事務所", "都税事務所", "法人事業税", "国税電子申告"],
                "filename_keywords": ["受信通知", "市町村"]
            },
            
            "2004_納付情報_市町村": {
                "priority": 130,
                "highest_priority_conditions": [
                    AndCondition(["納付情報発行結果", "法人住民税"], "all"),
                    AndCondition(["市役所", "納付情報", "法人市民税"], "all"),
                    AndCondition(["地方税共同機構", "法人市町村民税"], "all")
                ],
                "exact_keywords": ["市町村 納付情報", "法人住民税 納付情報"],
                "partial_keywords": ["納付情報", "地方税 納付", "法人住民税"],
                "exclude_keywords": ["県税事務所", "都税事務所", "法人二税・特別税", "国税"],
                "filename_keywords": ["納付情報", "市町村"]
            },
            
            # ===== 3000番台 - 消費税関連 =====
            "3001_消費税及び地方消費税申告書": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["課税期間分の消費税及び", "基準期間の"], "all"),
                    AndCondition(["消費税及び地方消費税申告(一般・法人)", "課税標準額"], "all"),
                    AndCondition(["現金主義会計の適用", "消費税申告"], "all"),
                    AndCondition(["課税標準額", "消費税及び地方消費税の合計税額"], "all")
                ],
                "exact_keywords": [
                    "消費税申告書", "消費税及び地方消費税申告書",
                    "消費税及び地方消費税申告(一般・法人)", "消費税申告(一般・法人)",
                    "課税期間分の消費税及び", "基準期間の", "現金主義会計の適用"
                ],
                "partial_keywords": ["消費税申告", "地方消費税申告", "消費税申告書", "課税期間分", "基準期間"],
                "exclude_keywords": ["添付資料", "イメージ添付", "資料", "受信通知", "納付区分番号通知"],
                "filename_keywords": ["消費税及び地方消費税申告", "消費税申告", "地方消費税申告"]
            },
            
            "3002_添付資料_消費税": {
                "priority": 125,
                "highest_priority_conditions": [
                    AndCondition(["添付資料", "消費税申告", "イメージ添付"], "all"),
                    AndCondition(["添付書類", "法人消費税申告"], "all"),
                    AndCondition(["イメージ添付書類(法人消費税申告)", "添付資料"], "all")
                ],
                "exact_keywords": [
                    "消費税 添付資料", "添付資料 消費税", "イメージ添付書類(法人消費税申告)",
                    "イメージ添付書類 消費税", "添付書類 消費税"
                ],
                "partial_keywords": ["添付資料", "消費税 資料", "イメージ添付", "添付書類"],
                "exclude_keywords": [
                    "消費税及び地方消費税申告", "消費税申告書", "申告(一般・法人)", 
                    "法人税申告", "内国法人", "確定申告", "受信通知", "納付区分番号通知"
                ],
                "filename_keywords": ["イメージ添付書類", "添付書類", "法人消費税"]
            },
            
            "3003_受信通知_消費税": {
                "priority": 130,
                "highest_priority_conditions": [
                    AndCondition(["メール詳細", "種目 消費税申告書"], "all"),
                    AndCondition(["受付番号", "消費税及び地方消費税", "受付日時"], "all"),
                    AndCondition(["提出先", "税務署", "消費税申告書"], "all"),
                    AndCondition(["送信されたデータを受け付けました", "消費税"], "all")
                ],
                "exact_keywords": ["消費税 受信通知", "受信通知 消費税"],
                "partial_keywords": ["受信通知", "国税電子申告", "メール詳細"],
                "exclude_keywords": ["法人税及び地方法人税申告書", "納付区分番号通知"],
                "filename_keywords": ["受信通知", "消費税"]
            },
            
            "3004_納付情報_消費税": {
                "priority": 130,
                "highest_priority_conditions": [
                    AndCondition(["メール詳細（納付区分番号通知）", "消費税及地方消費税"], "all"),
                    AndCondition(["納付区分番号通知", "税目 消費税及地方消費税"], "all"),
                    AndCondition(["納付先", "税務署", "消費税及地方消費税"], "all"),
                    AndCondition(["納付内容を確認し", "消費税"], "all")
                ],
                "exact_keywords": ["消費税 納付情報", "納付情報 消費税", "消費税 納付区分番号通知"],
                "partial_keywords": ["納付情報", "納付書", "納付区分番号通知"],
                "exclude_keywords": ["法人税及地方法人税", "受信通知"],
                "filename_keywords": ["納付情報", "消費税"]
            }
        }

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # 内部ログリストに追加
        self.processing_log.append(log_entry)
        
        # コールバックがあれば呼び出し
        if self.log_callback:
            self.log_callback(log_entry)
        
        # デバッグモードの場合はコンソール出力
        if self.debug_mode:
            print(log_entry)

    def _log_debug(self, message: str):
        """デバッグレベルのログ"""
        if self.debug_mode:
            self._log(message, "DEBUG")

    def _check_highest_priority_conditions(self, text: str, filename: str) -> Optional[ClassificationResult]:
        """最優先条件（AND条件）をチェック"""
        combined_text = f"{text} {filename}"
        
        self._log("最優先AND条件判定開始")
        
        # 優先度順でチェック
        sorted_rules = sorted(self.classification_rules_v5.items(), 
                            key=lambda x: x[1].get("priority", 0), reverse=True)
        
        for doc_type, rules in sorted_rules:
            highest_priority_conditions = rules.get("highest_priority_conditions", [])
            
            if not highest_priority_conditions:
                continue
            
            for i, condition in enumerate(highest_priority_conditions):
                is_match, matched_keywords = condition.check_match(combined_text)
                
                if is_match:
                    self._log(f"最優先AND条件一致: {doc_type} (条件{i+1})")
                    self._log_debug(f"マッチしたキーワード: {matched_keywords}")
                    self._log_debug(f"マッチタイプ: {condition.match_type}")
                    
                    return ClassificationResult(
                        document_type=doc_type,
                        confidence=1.0,  # 最優先なので信頼度100%
                        matched_keywords=matched_keywords,
                        classification_method="highest_priority_and_condition",
                        debug_steps=[],
                        processing_log=self.processing_log.copy()
                    )
        
        self._log_debug("最優先AND条件マッチなし - 通常分類処理に移行")
        return None

    def classify_document_v5(self, text: str, filename: str = "") -> ClassificationResult:
        """v5.0 書類分類（AND条件対応版）"""
        self.processing_log = []  # ログをリセット
        self.current_filename = filename
        
        self._log(f"書類分類開始 (v5.0): {filename}")
        
        # テキストの前処理
        text_cleaned = self._preprocess_text(text)
        filename_cleaned = self._preprocess_text(filename)
        
        self._log_debug(f"入力テキスト長: {len(text)} → 前処理後: {len(text_cleaned)}")
        self._log_debug(f"ファイル名: {filename} → 前処理後: {filename_cleaned}")
        
        # 抽出テキストの一部を表示（デバッグ用）
        if text_cleaned:
            preview = text_cleaned[:200] + "..." if len(text_cleaned) > 200 else text_cleaned
            self._log_debug(f"テキスト内容: {preview}")
        
        # 最優先AND条件判定
        priority_result = self._check_highest_priority_conditions(text_cleaned, filename_cleaned)
        if priority_result:
            return priority_result
        
        # 通常の分類処理（従来ルールも維持）
        return self._standard_classification(text_cleaned, filename_cleaned)

    def _standard_classification(self, text: str, filename: str) -> ClassificationResult:
        """標準分類処理（従来ルール）"""
        best_match = None
        best_score = 0
        best_keywords = []
        best_method = "standard_keyword_matching"
        debug_steps = []
        
        self._log("標準分類ルール評価開始")
        
        # 各分類ルールに対してスコア計算
        for doc_type, rules in self.classification_rules_v5.items():
            self._log_debug(f"評価中: {doc_type} (優先度: {rules.get('priority', 5)})")
            
            # テキストとファイル名を分けてスコア計算
            text_score, text_keywords = self._calculate_score(text, rules, "テキスト")
            filename_score, filename_keywords = self._calculate_filename_score(filename, rules)
            
            # 総合スコア（ファイル名を重視）
            total_score = text_score + (filename_score * 1.5)
            combined_keywords = text_keywords + filename_keywords
            
            # 除外判定チェック
            excluded = False
            exclude_reason = ""
            
            # 最優先条件が一致している場合は除外キーワードを無視
            has_highest_priority = any(
                condition.check_match(f"{text} {filename}")[0] 
                for condition in rules.get("highest_priority_conditions", [])
            )
            
            if not has_highest_priority:
                # 除外キーワードチェック
                for exclude_keyword in rules.get("exclude_keywords", []):
                    if exclude_keyword in text or exclude_keyword in filename:
                        excluded = True
                        exclude_reason = f"除外キーワード '{exclude_keyword}' を検出"
                        break
            
            # デバッグステップ記録
            step = ClassificationStep(
                document_type=doc_type,
                score=total_score,
                matched_keywords=combined_keywords,
                excluded=excluded,
                exclude_reason=exclude_reason,
                method="standard"
            )
            debug_steps.append(step)
            
            # ログ出力
            if excluded:
                self._log_debug(f"  → {doc_type}: 除外, キーワード:[なし] ({exclude_reason})")
            else:
                self._log_debug(f"  → {doc_type}: スコア:{total_score:.1f}, キーワード:{combined_keywords}")
                if text_score > 0:
                    self._log_debug(f"    - テキストスコア: {text_score:.1f}")
                if filename_score > 0:
                    self._log_debug(f"    - ファイル名スコア: {filename_score:.1f} × 1.5 = {filename_score * 1.5:.1f}")
            
            # 最高スコア更新
            if not excluded and total_score > best_score:
                best_score = total_score
                best_match = doc_type
                best_keywords = combined_keywords
                self._log_debug(f"    新たな最高スコア! → {doc_type}")
        
        # 信頼度を計算（0.0-1.0）
        confidence = min(best_score / 15.0, 1.0)
        
        self._log(f"最終結果: {best_match}, スコア: {best_score:.1f}, 信頼度: {confidence:.2f}")
        
        # 分類できない場合のデフォルト
        if not best_match or confidence < 0.3:
            best_match = "9999_未分類"
            confidence = 0.0
            best_method = "default_fallback"
            self._log(f"信頼度不足により未分類に変更")
        
        return ClassificationResult(
            document_type=best_match,
            confidence=confidence,
            matched_keywords=best_keywords,
            classification_method=best_method,
            debug_steps=debug_steps,
            processing_log=self.processing_log.copy()
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

    def _calculate_score(self, text: str, rules: Dict, source: str = "") -> Tuple[float, List[str]]:
        """分類ルールに基づいてスコアを計算"""
        score = 0
        matched_keywords = []
        priority = rules.get("priority", 5)
        
        # 除外キーワードチェック（優先）
        for exclude_keyword in rules.get("exclude_keywords", []):
            if exclude_keyword in text:
                self._log_debug(f"    除外: {source}除外キーワード検出: '{exclude_keyword}'")
                return 0, []
        
        # 完全一致キーワード（高スコア）
        for exact_keyword in rules.get("exact_keywords", []):
            if exact_keyword in text:
                points = priority * 2
                score += points
                matched_keywords.append(exact_keyword)
                self._log_debug(f"    完全一致: {source}'{exact_keyword}' (+{points})")
        
        # 部分一致キーワード（中スコア）
        for partial_keyword in rules.get("partial_keywords", []):
            if partial_keyword in text:
                points = priority * 1
                score += points
                matched_keywords.append(partial_keyword)
                self._log_debug(f"    部分一致: {source}'{partial_keyword}' (+{points})")
        
        return score, matched_keywords

    def _calculate_filename_score(self, filename: str, rules: Dict) -> Tuple[float, List[str]]:
        """ファイル名に基づいてスコアを計算"""
        score = 0
        matched_keywords = []
        priority = rules.get("priority", 5)
        
        # 除外キーワードチェック（ファイル名でも重要）
        for exclude_keyword in rules.get("exclude_keywords", []):
            if exclude_keyword in filename:
                self._log_debug(f"    除外: ファイル名除外キーワード検出: '{exclude_keyword}'")
                return 0, []
        
        # ファイル名専用キーワードがある場合
        filename_keywords = rules.get("filename_keywords", [])
        for keyword in filename_keywords:
            if keyword in filename:
                points = priority * 3  # ファイル名マッチは最高スコア
                score += points
                matched_keywords.append(f"[ファイル名]{keyword}")
                self._log_debug(f"    ファイル名専用一致: '{keyword}' (+{points})")
        
        # 通常のキーワードもファイル名でチェック
        for exact_keyword in rules.get("exact_keywords", []):
            if exact_keyword in filename:
                points = priority * 2
                score += points
                matched_keywords.append(f"[ファイル名]{exact_keyword}")
                self._log_debug(f"    ファイル名完全一致: '{exact_keyword}' (+{points})")
        
        return score, matched_keywords

    def classify_with_municipality_info_v5(self, text: str, filename: str, 
                                         prefecture_code: Optional[int] = None,
                                         municipality_code: Optional[int] = None) -> ClassificationResult:
        """v5.0 自治体情報を考慮した分類（連番対応）"""
        # v5.0 分類実行
        base_result = self.classify_document_v5(text, filename)
        
        # 連番対応処理
        final_code = self._apply_municipality_numbering(
            base_result.document_type, 
            prefecture_code, 
            municipality_code
        )
        
        if final_code != base_result.document_type:
            self._log(f"自治体名付きコード生成: {base_result.document_type} → {final_code}")
            base_result.document_type = final_code
        
        return base_result

    def _apply_municipality_numbering(self, document_type: str, 
                                    prefecture_code: Optional[int] = None,
                                    municipality_code: Optional[int] = None) -> str:
        """自治体連番の適用"""
        # 都道府県関連書類の連番対応
        if document_type == "1001_都道府県_法人都道府県民税・事業税・特別法人事業税":
            if prefecture_code:
                # 自治体名を取得（実装時に適切な名前を設定）
                prefecture_name = self._get_prefecture_name(prefecture_code)
                return f"{prefecture_code}_{prefecture_name}_法人都道府県民税・事業税・特別法人事業税"
        
        # 市町村関連書類の連番対応
        elif document_type == "2001_市町村_法人市民税":
            if municipality_code:
                # 自治体名を取得（実装時に適切な名前を設定）
                municipality_name = self._get_municipality_name(municipality_code)
                return f"{municipality_code}_{municipality_name}_法人市民税"
        
        elif document_type == "2003_受信通知_市町村":
            if municipality_code:
                # 市町村受信通知の連番対応
                base_code = 2003 + ((municipality_code - 2001) // 10) * 10
                return f"{base_code}_受信通知"
        
        return document_type

    def _get_prefecture_name(self, prefecture_code: int) -> str:
        """都道府県コードから名前を取得（実装時に適切なマッピングを設定）"""
        # 仮実装 - 実際の運用では設定から取得
        mapping = {
            1001: "東京都",
            1011: "愛知県", 
            1021: "福岡県"
        }
        return mapping.get(prefecture_code, "都道府県")

    def _get_municipality_name(self, municipality_code: int) -> str:
        """市町村コードから名前を取得（実装時に適切なマッピングを設定）"""
        # 仮実装 - 実際の運用では設定から取得
        mapping = {
            2001: "愛知県蒲郡市",
            2011: "福岡県福岡市"
        }
        return mapping.get(municipality_code, "市町村")

if __name__ == "__main__":
    # テスト用
    classifier = DocumentClassifierV5(debug_mode=True)
    print("書類分類エンジン v5.0 初期化完了")
    
    # テストケース
    test_cases = [
        {
            "text": "メール詳細 種目 法人税及び地方法人税申告書 受付番号 20250731185710521215",
            "filename": "test_houjinzei.pdf",
            "expected": "0003_受信通知_法人税"
        },
        {
            "text": "納付区分番号通知 税目 消費税及地方消費税 納付先 芝税務署",
            "filename": "test_shouhizei.pdf", 
            "expected": "3004_納付情報_消費税"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n=== テストケース {i} ===")
        result = classifier.classify_document_v5(test_case["text"], test_case["filename"])
        print(f"結果: {result.document_type}")
        print(f"期待値: {test_case['expected']}")
        print(f"マッチ: {'✓' if result.document_type == test_case['expected'] else '✗'}")