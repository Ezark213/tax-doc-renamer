#!/usr/bin/env python3
"""
書類分類エンジン v5.0 修正版
セットベース連番システム + 画像認識突合チェック対応
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
import datetime

@dataclass
class MunicipalitySet:
    """自治体セットの定義"""
    set_number: int
    prefecture_name: str
    prefecture_code: int
    municipality_name: Optional[str] = None
    municipality_code: Optional[int] = None
    keywords: List[str] = field(default_factory=list)

@dataclass
class ValidationAlert:
    """検証アラート情報"""
    alert_type: str  # "MISMATCH", "AMBIGUOUS", "NOT_FOUND"
    message: str
    confidence: float
    suggestions: List[str] = field(default_factory=list)

class DocumentClassifierV5Fixed:
    """書類分類エンジン v5.0 修正版 - セットベース連番システム"""
    
    def __init__(self, debug_mode: bool = False, log_callback: Optional[Callable[[str], None]] = None):
        """初期化"""
        self.debug_mode = debug_mode
        self.log_callback = log_callback
        self.current_filename = ""
        self.processing_log = []
        
        # セット定義の初期化
        self.municipality_sets = self._initialize_municipality_sets()
        
        # v5.0 分類ルール（修正版）
        self.classification_rules_v5 = self._initialize_classification_rules_v5()

    def _initialize_municipality_sets(self) -> Dict[int, MunicipalitySet]:
        """自治体セットの初期化"""
        return {
            1: MunicipalitySet(
                set_number=1,
                prefecture_name="東京都", 
                prefecture_code=1001,
                municipality_name=None,  # 東京都は市町村設定なし
                municipality_code=None,
                keywords=[
                    "芝税務署", "東京都港都税事務所", "都税事務所",
                    "東京都", "港区", "品川区"
                ]
            ),
            2: MunicipalitySet(
                set_number=2,
                prefecture_name="愛知県",
                prefecture_code=1011,
                municipality_name="愛知県蒲郡市",
                municipality_code=2001,
                keywords=[
                    "愛知県東三河県税事務所", "東三河県税事務所", "愛知県",
                    "蒲郡市役所", "蒲郡市", "蒲郡市長"
                ]
            ),
            3: MunicipalitySet(
                set_number=3,
                prefecture_name="福岡県",
                prefecture_code=1021,
                municipality_name="福岡県福岡市",
                municipality_code=2011,
                keywords=[
                    "福岡県西福岡県税事務所", "西福岡県税事務所", "福岡県",
                    "福岡市役所", "福岡市", "福岡市長"
                ]
            )
        }

    def _detect_municipality_set_from_content(self, text: str, filename: str) -> Tuple[Optional[int], ValidationAlert]:
        """コンテンツベースでセット検出（主要処理）"""
        combined_text = f"{text} {filename}".lower()
        detection_scores = {}
        matched_keywords = {}
        
        self._log_debug("セット検出開始（コンテンツベース）")
        
        # 各セットのキーワードマッチング
        for set_num, municipality_set in self.municipality_sets.items():
            score = 0
            matched = []
            
            for keyword in municipality_set.keywords:
                if keyword.lower() in combined_text:
                    score += 1
                    matched.append(keyword)
                    self._log_debug(f"セット{set_num}キーワードマッチ: {keyword}")
            
            if score > 0:
                detection_scores[set_num] = score
                matched_keywords[set_num] = matched
        
        # 結果判定
        if not detection_scores:
            alert = ValidationAlert(
                alert_type="NOT_FOUND",
                message="自治体セットが検出されませんでした",
                confidence=0.0,
                suggestions=["手動でセット選択を確認してください"]
            )
            return None, alert
        
        # 最高スコアのセットを選択
        best_set = max(detection_scores.items(), key=lambda x: x[1])
        best_set_num, best_score = best_set
        
        # 複数セットが同じスコアの場合はアラート
        tied_sets = [set_num for set_num, score in detection_scores.items() if score == best_score]
        
        if len(tied_sets) > 1:
            alert = ValidationAlert(
                alert_type="AMBIGUOUS",
                message=f"複数セットが同スコア: {tied_sets} (スコア: {best_score})",
                confidence=0.5,
                suggestions=[f"セット{s}: {matched_keywords.get(s, [])}" for s in tied_sets]
            )
            self._log(f"⚠️ 複数セット検出アラート: {tied_sets}")
        else:
            confidence = min(1.0, best_score / 3.0)  # 3個以上マッチで信頼度100%
            alert = ValidationAlert(
                alert_type="SUCCESS",
                message=f"セット{best_set_num}を検出 (スコア: {best_score})",
                confidence=confidence,
                suggestions=matched_keywords[best_set_num]
            )
        
        self._log(f"✅ 検出結果: セット{best_set_num} (信頼度: {alert.confidence:.2f})")
        return best_set_num, alert

    def _apply_set_based_numbering(self, document_type: str, detected_set: int) -> str:
        """セットベース連番適用"""
        if detected_set not in self.municipality_sets:
            self._log(f"⚠️ 不明なセット番号: {detected_set}")
            return document_type
        
        municipality_set = self.municipality_sets[detected_set]
        self._log_debug(f"セット{detected_set}連番適用: {municipality_set.prefecture_name}")
        
        # 書類種別ごとの連番ルール
        if "受信通知" in document_type:
            # 受信通知は末尾03
            if document_type.startswith("0003_"):  # 国税受信通知
                new_code = f"{municipality_set.prefecture_code}3"  # 1003, 1013, 1023
                return f"{new_code}_受信通知"
            elif document_type.startswith("1003_") or "都道府県" in document_type:  # 都道府県受信通知
                new_code = f"{municipality_set.prefecture_code}3"  # 1003, 1013, 1023
                return f"{new_code}_受信通知"
            elif document_type.startswith("2003_") and municipality_set.municipality_code:  # 市町村受信通知
                if detected_set == 1:  # 東京都は市町村なし
                    return document_type
                new_code = f"{municipality_set.municipality_code}3"  # 2003, 2013
                return f"{new_code}_受信通知"
        
        elif "納付情報" in document_type:
            # 納付情報は末尾04
            if document_type.startswith("0004_"):  # 国税納付情報
                new_code = f"{municipality_set.prefecture_code}4"  # 1004, 1014, 1024
                return f"{new_code}_納付情報"
            elif document_type.startswith("1004_"):  # 都道府県納付情報
                new_code = f"{municipality_set.prefecture_code}4"  # 1004, 1014, 1024
                return f"{new_code}_納付情報"
            elif document_type.startswith("2004_") and municipality_set.municipality_code:  # 市町村納付情報
                if detected_set == 1:  # 東京都は市町村なし
                    return document_type
                new_code = f"{municipality_set.municipality_code}4"  # 2004, 2014
                return f"{new_code}_納付情報"
            elif document_type.startswith("3004_"):  # 消費税納付情報
                new_code = f"{municipality_set.prefecture_code}4"  # 1004, 1014, 1024
                return f"{new_code}_消費税納付情報"
        
        elif "申告書" in document_type or "申告" in document_type:
            # 申告書は末尾01
            if document_type.startswith("0001_") or "法人税" in document_type:
                new_code = f"{municipality_set.prefecture_code}1"  # 1001, 1011, 1021
                return f"{new_code}_法人税及び地方法人税申告書"
            elif document_type.startswith("1001_") or "都道府県民税" in document_type:
                new_code = f"{municipality_set.prefecture_code}1"  # 1001, 1011, 1021
                return f"{new_code}_{municipality_set.prefecture_name}_法人都道府県民税・事業税・特別法人事業税"
            elif document_type.startswith("2001_") and municipality_set.municipality_code:
                if detected_set == 1:  # 東京都は市町村なし
                    return document_type
                new_code = f"{municipality_set.municipality_code}1"  # 2001, 2011
                return f"{new_code}_{municipality_set.municipality_name}_法人市民税"
            elif document_type.startswith("3001_") or "消費税" in document_type:
                new_code = f"{municipality_set.prefecture_code}1"  # 1001, 1011, 1021
                return f"{new_code}_消費税及び地方消費税申告書"
        
        self._log_debug(f"セット連番適用なし: {document_type}")
        return document_type

    def _cross_validate_with_ocr(self, document_type: str, detected_set: int, text: str) -> ValidationAlert:
        """OCR結果との突合チェック"""
        municipality_set = self.municipality_sets[detected_set]
        text_lower = text.lower()
        
        # 検証キーワードの設定
        expected_keywords = municipality_set.keywords
        found_keywords = [kw for kw in expected_keywords if kw.lower() in text_lower]
        
        # 矛盾キーワードチェック（他のセットのキーワードが含まれていないか）
        conflicting_sets = []
        for other_set_num, other_set in self.municipality_sets.items():
            if other_set_num != detected_set:
                conflicts = [kw for kw in other_set.keywords if kw.lower() in text_lower]
                if conflicts:
                    conflicting_sets.append((other_set_num, conflicts))
        
        # 判定
        if conflicting_sets:
            return ValidationAlert(
                alert_type="MISMATCH",
                message=f"セット{detected_set}と判定したが、他セットのキーワードも検出",
                confidence=0.3,
                suggestions=[f"セット{s}: {kws}" for s, kws in conflicting_sets]
            )
        elif not found_keywords:
            return ValidationAlert(
                alert_type="MISMATCH", 
                message=f"セット{detected_set}の確認キーワードがOCRテキストに見つかりません",
                confidence=0.2,
                suggestions=[f"期待キーワード: {expected_keywords}"]
            )
        else:
            confidence = len(found_keywords) / len(expected_keywords)
            return ValidationAlert(
                alert_type="SUCCESS",
                message=f"OCR突合チェック成功 ({len(found_keywords)}/{len(expected_keywords)}キーワードマッチ)",
                confidence=confidence,
                suggestions=found_keywords
            )

    def classify_document_v5_fixed(self, text: str, filename: str = "") -> Tuple[str, List[ValidationAlert]]:
        """v5.0 修正版書類分類（セットベース + 突合チェック）"""
        self.processing_log = []
        self.current_filename = filename
        alerts = []
        
        self._log(f"書類分類開始 (v5.0修正版): {filename}")
        
        # Step 1: セット検出
        detected_set, detection_alert = self._detect_municipality_set_from_content(text, filename)
        alerts.append(detection_alert)
        
        if detected_set is None:
            self._log("❌ セット検出失敗 - デフォルト分類を実行")
            return self._fallback_classification(text, filename), alerts
        
        # Step 2: 書類種別判定（既存のAND条件ロジック使用）
        classification_result = self._check_highest_priority_conditions(text, filename)
        if not classification_result:
            classification_result = self._standard_classification(text, filename)
        
        base_document_type = classification_result.document_type
        self._log(f"基本書類種別: {base_document_type}")
        
        # Step 3: セットベース連番適用
        final_document_type = self._apply_set_based_numbering(base_document_type, detected_set)
        self._log(f"最終書類種別: {final_document_type}")
        
        # Step 4: OCR突合チェック
        validation_alert = self._cross_validate_with_ocr(final_document_type, detected_set, text)
        alerts.append(validation_alert)
        
        # Step 5: アラート判定
        if validation_alert.alert_type == "MISMATCH":
            self._log(f"⚠️ 検証アラート: {validation_alert.message}")
        
        return final_document_type, alerts

    def _fallback_classification(self, text: str, filename: str) -> str:
        """フォールバック分類（セット検出失敗時）"""
        self._log("フォールバック分類実行")
        classification_result = self._check_highest_priority_conditions(text, filename)
        if classification_result:
            return classification_result.document_type
        return "0000_未分類"

    # 既存のメソッドも含める（省略部分は元のコードから継承）
    def _initialize_classification_rules_v5(self) -> Dict:
        """v5.0 分類ルール初期化（AND条件対応）"""
        return {
            # ===== 0000番台 - 国税申告書類 =====
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
            
            "0003_受信通知": {
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
            
            "0004_納付情報": {
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
            
            "1003_受信通知": {
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
            
            "1004_納付情報": {
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
            
            "2003_受信通知": {
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
            
            "2004_納付情報": {
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
            
            "3003_受信通知": {
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
            
            "3004_納付情報": {
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

    def _check_highest_priority_conditions(self, text: str, filename: str):
        """最優先条件（AND条件）をチェック - 既存実装を使用"""
        # 既存のメソッドをそのまま使用
        pass
    
    def _standard_classification(self, text: str, filename: str):
        """標準分類処理 - 既存実装を使用"""
        # 既存のメソッドをそのまま使用
        pass

    def _preprocess_text(self, text: str) -> str:
        """テキスト前処理"""
        if not text:
            return ""
        
        # 改行・タブの正規化
        text = re.sub(r'[\r\n\t]+', ' ', text)
        # 複数スペースを単一スペースに
        text = re.sub(r'\s+', ' ', text)
        # 前後の空白を削除
        text = text.strip()
        
        return text

# AndCondition クラスの定義
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