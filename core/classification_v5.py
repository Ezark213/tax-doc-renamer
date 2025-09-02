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
                "priority": 160,  # 緊急修正: 適切な優先度に変更
                "highest_priority_conditions": [
                    # 非常に限定的な条件のみ使用
                    AndCondition(["納付税額一覧表"], "any"),  # 完全一致のみ
                    AndCondition(["まとめ納付", "納付税額"], "all"),  # 非常に特定の組み合わせのみ
                ],
                "exact_keywords": [
                    "納付税額一覧表",  # 完全一致のみ
                ],
                "partial_keywords": [
                    # 非常に限定的なキーワードのみ
                ],
                "exclude_keywords": [
                    # 強化された除外キーワード
                    "受信通知", "納付区分番号通知", "メール詳細", "添付資料", 
                    "申告書", "イメージ添付", "元帳", "総勘定", "仕訳", "決算",
                    "内国法人", "確定申告", "青色申告", "法人税申告", 
                    "事業年度分", "税額控除", "都道府県民税", "市民税", "消費税",
                    "事業税", "特別法人事業税", "地方法人税", "市長", "市役所", "県税事務所", "都税事務所"
                ],
                "filename_keywords": ["納付税額一覧表", "まとめ納付"]
            },
            
            "0001_法人税及び地方法人税申告書": {
                "priority": 220,  # 緊急修正: 0000より高い優先度
                "highest_priority_conditions": [
                    # 修正指示書に基づく新しい最優先条件を追加
                    AndCondition(["01_内国法人", "確定申告"], "all"),  # ファイル名パターン
                    AndCondition(["内国法人の確定申告(青色)"], "any"),  # 単独でも最優先
                    AndCondition(["事業年度分の法人税申告書", "差引確定法人税額"], "all"),
                    AndCondition(["内国法人の確定申告(青色)", "法人税額"], "all"),
                    AndCondition(["控除しきれなかった金額", "課税留保金額"], "all"),
                    AndCondition(["中間申告分の法人税額", "中間申告分の地方法人税額"], "all")
                ],
                "exact_keywords": [
                    "法人税及び地方法人税申告書", "内国法人の確定申告", "内国法人の確定申告(青色)",
                    "法人税申告書別表一", "申告書第一表"
                ],
                "partial_keywords": ["法人税申告", "内国法人", "確定申告", "青色申告", "事業年度分"],
                "exclude_keywords": ["メール詳細", "受信通知", "納付区分番号通知", "添付資料", "イメージ添付"],
                "filename_keywords": ["内国法人", "確定申告", "青色"]
            },
            
            "0002_添付資料_法人税": {
                "priority": 200,  # バグ修正依頼書: B-2 最高優先度に変更
                "highest_priority_conditions": [
                    # バグ修正依頼書: B-1 完全一致キーワードの追加
                    AndCondition(["法人税 添付資料"], "any"),
                    AndCondition(["添付資料 法人税"], "any"), 
                    AndCondition(["イメージ添付書類(法人税申告)"], "any"),
                    AndCondition(["イメージ添付書類 法人税"], "any"),
                    AndCondition(["添付書類 法人税"], "any"),
                    # 既存条件も維持
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
                "priority": 200,  # 緊急修正: 0000より高い優先度
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
                "exclude_keywords": [
                    "市町村", "市民税", "市役所", "町役場", "村役場", "受信通知", "納付情報",
                    # 緊急修正: 0000番台の誤分類を防ぐための強化された除外キーワード
                    "納付税額一覧表", "納税一覧", "税額一覧表", "納付一覧表",
                    "年間税額", "申告納付額", "差引納付額", "見込納付額",
                    "事業税等小計", "道府県税小計", "地方税小計", "各税目",
                    "法人税等の納付税額", "各税目納付税額", "税額合計",
                    # 緊急追加: 0000番台に関連するキーワードも除外
                    "法人市民税", "消費税", "地方消費税", "まとめ納付", "納付税額", "まとめ", "納付"
                ],
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
                "priority": 185,  # 優先度を上げて確実な判別
                "highest_priority_conditions": [
                    # 税目による完全判別システム
                    AndCondition(["地方税共同機構", "税目:法人二税・特別税"], "all"),
                    AndCondition(["地方税共同機構", "法人都道府県民税・事業税・特別法人事業税"], "all"),
                    AndCondition(["納付情報発行結果", "法人都道府県民税"], "all"),
                    AndCondition(["納付情報発行結果", "法人事業税"], "all"),
                    AndCondition(["納付情報発行結果", "特別法人事業税"], "all"),
                    AndCondition(["地方税共同機構", "都道府県民税・事業税"], "all"),
                    AndCondition(["ペイジー納付情報", "都道府県民税"], "all")
                ],
                "exact_keywords": [
                    "都道府県 納付情報", "納付情報発行結果", "地方税共同機構",
                    "税目:法人二税・特別税", "法人都道府県民税・事業税・特別法人事業税"
                ],
                "partial_keywords": [
                    "納付情報", "地方税 納付", "法人二税", "特別税", "都道府県民税",
                    "法人事業税", "特別法人事業税"
                ],
                "exclude_keywords": ["市役所", "町役場", "村役場", "法人市民税", "法人住民税", "国税"],
                "filename_keywords": ["納付情報", "都道府県", "地方税共同機構"]
            },
            
            # ===== 2000番台 - 市町村税関連 =====
            "2001_市町村_法人市民税": {
                "priority": 210,  # 緊急修正: 0000より高い優先度
                "highest_priority_conditions": [
                    # バグ修正依頼書: C-1 市民税判定条件の強化
                    AndCondition(["法人市民税", "申告書", "市役所"], "all"),
                    AndCondition(["市長", "法人市民税"], "all"),
                    # 既存条件も維持
                    AndCondition(["法人市民税申告書", "市役所", "均等割"], "all"),
                    AndCondition(["市町村民税", "法人税割", "申告納付税額"], "all"),
                    AndCondition(["法人市民税", "課税標準総額", "市長"], "all")
                ],
                "exact_keywords": ["法人市民税申告書", "市民税申告書"],
                "partial_keywords": ["法人市民税", "市町村民税", "市役所", "町役場", "村役場"],
                "exclude_keywords": [
                    "都道府県", "事業税", "県税事務所", "都税事務所", "受信通知", "納付情報",
                    # バグ修正依頼書: C-1 除外条件の追加
                    "内国法人", "確定申告(青色)", "事業年度分", "税額控除",
                    # 緊急修正: 納付情報の誤分類防止
                    "地方税共同機構", "納付情報発行結果", "納付区分番号通知"
                ],
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
                "priority": 195,  # 1004より高い優先度で市町村納付情報を確実判別
                "highest_priority_conditions": [
                    # 税目による完全判別システム（市町村特化版）
                    AndCondition(["地方税共同機構", "税目:法人住民税"], "all"),
                    AndCondition(["地方税共同機構", "法人市町村民税"], "all"),
                    AndCondition(["納付情報発行結果", "法人住民税"], "all"),
                    AndCondition(["納付情報発行結果", "法人市民税"], "all"),
                    AndCondition(["納付情報発行結果", "法人市町村民税"], "all"),
                    # より包括的な単独条件
                    AndCondition(["地方税共同機構"], "any"),  # 地方税共同機構は基本的に市町村
                    AndCondition(["市役所", "納付情報"], "all"),
                    AndCondition(["法人市民税", "納付情報"], "all"),
                    AndCondition(["法人住民税", "納付書"], "all"),
                    AndCondition(["ペイジー", "市町村"], "all")
                ],
                "exact_keywords": [
                    "市町村 納付情報", "法人住民税 納付情報", "地方税共同機構",
                    "納付情報発行結果", "法人市民税 納付情報"
                ],
                "partial_keywords": [
                    "納付情報", "地方税 納付", "法人住民税", "法人市民税", 
                    "納付書", "ペイジー", "市町村税"
                ],
                "exclude_keywords": ["県税事務所", "都税事務所", "法人二税・特別税", "国税", "申告書"],
                "filename_keywords": ["納付情報", "市町村", "地方税共同機構"]
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
                "priority": 200,  # 最高優先度に変更
                "highest_priority_conditions": [
                    # 修正指示書に基づくファイル名最優先条件を追加
                    AndCondition(["イメージ添付書類(法人消費税申告)"], "any"),  # 単独最優先
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
            },
            
            # ===== 5000番台 - 会計書類（修正版） =====
            "5001_決算書": {
                "priority": 170,  # 緊急修正: 0000より高い優先度
                "highest_priority_conditions": [
                    # 修正: 3つのキーワードすべてが揃った場合のみ決算書と判定
                    AndCondition(["販売費及び一般管理費", "貸借対照表", "損益計算書"], "all")
                ],
                "exact_keywords": ["決算報告書"],  # 決算報告書のみ単体で判定可能
                "partial_keywords": ["決算報告"],  # 決算単体キーワードを削除
                "exclude_keywords": [],
                "filename_keywords": ["決算書", "決算報告書"]
            },
            
            "5002_総勘定元帳": {
                "priority": 180,  # 緊急修正: 0000より高い優先度  # 最高優先度
                "highest_priority_conditions": [
                    AndCondition(["総勘定元帳"], "any")
                ],
                "exact_keywords": ["総勘定元帳"],
                "partial_keywords": ["総勘定", "元帳"],
                "exclude_keywords": ["補助元帳", "補助", "内国法人", "確定申告", "01_内国法人"],  # 法人税申告書を除外
                "filename_keywords": ["総勘定元帳", "総勘定"]
            },
            
            "5003_補助元帳": {
                "priority": 170,  # 緊急修正: 0000より高い優先度
                "highest_priority_conditions": [
                    AndCondition(["補助元帳"], "any")
                ],
                "exact_keywords": ["補助元帳"],
                "partial_keywords": ["補助", "元帳"],
                "exclude_keywords": ["総勘定"],
                "filename_keywords": ["補助元帳", "補助"]
            },
            
            "5004_残高試算表": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["残高試算表"], "any"),
                    AndCondition(["試算表"], "any")
                ],
                "exact_keywords": ["残高試算表", "試算表"],
                "partial_keywords": ["残高試算", "試算"],
                "exclude_keywords": [],
                "filename_keywords": ["残高試算表", "試算表"]
            },
            
            "5005_仕訳帳": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["仕訳帳"], "any")
                ],
                "exact_keywords": ["仕訳帳"],
                "partial_keywords": ["仕訳"],
                "exclude_keywords": [],
                "filename_keywords": ["仕訳帳", "仕訳"]
            },
            
            # ===== 6000番台 - 固定資産関連（修正版） =====
            "6001_固定資産台帳": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["固定資産台帳"], "any")
                ],
                "exact_keywords": ["固定資産台帳"],
                "partial_keywords": ["固定資産", "資産台帳"],
                "exclude_keywords": [],
                "filename_keywords": ["固定資産台帳"]
            },
            
            "6002_一括償却資産明細表": {
                "priority": 170,  # 緊急修正: 0000より高い優先度  # 最高優先度
                "highest_priority_conditions": [
                    AndCondition(["一括償却資産明細表"], "any")
                ],
                "exact_keywords": ["一括償却資産明細表"],
                "partial_keywords": ["一括償却", "償却資産明細"],
                "exclude_keywords": ["少額"],
                "filename_keywords": ["一括償却資産明細表", "一括償却"]
            },
            
            "6003_少額減価償却資産明細表": {
                "priority": 170,  # 緊急修正: 0000より高い優先度  # 最高優先度
                "highest_priority_conditions": [
                    AndCondition(["少額減価償却資産明細表"], "any")
                ],
                "exact_keywords": ["少額減価償却資産明細表"],
                "partial_keywords": ["少額減価償却", "少額償却"],
                "exclude_keywords": ["一括"],
                "filename_keywords": ["少額減価償却資産明細表", "少額"]
            },
            
            # ===== 7000番台 - 税区分関連（修正版） =====
            "7001_勘定科目別税区分集計表": {
                "priority": 140,  # 最高優先度
                "highest_priority_conditions": [
                    AndCondition(["勘定科目別税区分集計表"], "any")
                ],
                "exact_keywords": ["勘定科目別税区分集計表"],
                "partial_keywords": ["勘定科目別税区分", "科目別税区分"],
                "exclude_keywords": ["イメージ添付書類", "添付資料", "法人消費税申告"],  # 添付資料系を除外
                "filename_keywords": ["勘定科目別税区分集計表"]
            },
            
            "7002_税区分集計表": {
                "priority": 170,  # 緊急修正: 0000より高い優先度
                "highest_priority_conditions": [
                    AndCondition(["税区分集計表"], "any")
                ],
                "exact_keywords": ["税区分集計表"],
                "partial_keywords": ["税区分集計", "区分集計"],
                "exclude_keywords": ["勘定科目別", "科目別"],
                "filename_keywords": ["税区分集計表"]
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
                    
                    # デバッグ用の詳細情報を追加
                    debug_info = f"最優先AND条件判定: {doc_type} | 条件{i+1}: {condition.keywords} ({condition.match_type}) | マッチキーワード: {matched_keywords}"
                    self._log(debug_info)
                    
                    return ClassificationResult(
                        document_type=doc_type,
                        confidence=1.0,  # 最優先なので信頼度100%
                        matched_keywords=matched_keywords,
                        classification_method=f"highest_priority_and_condition_{i+1}",
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
        
        # バグ修正依頼書: D-2 地方税受信通知専用判定（新規追加）
        municipality_info = self._extract_municipality_info_from_text(text_cleaned, filename_cleaned)
        prefecture_code, municipality_code = municipality_info
        
        local_tax_result = self._classify_local_tax_receipt(text_cleaned, filename_cleaned, prefecture_code, municipality_code)
        if local_tax_result:
            return local_tax_result
        
        # 修正指示書: 修正3 - 納付情報・受信通知の判別強化
        enhanced_result = self._check_enhanced_payment_receipt_detection(text_cleaned, filename_cleaned)
        if enhanced_result:
            return enhanced_result
        
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
        
        # 信頼度を計算（0.0-1.0）会計書類用に調整
        confidence = min(best_score / 10.0, 1.0)  # 会計書類用に閾値を下げる
        
        # 詳細な判定結果のログ出力
        if best_match and best_match != "9999_未分類":
            debug_info = f"標準分類判定: {best_match} | スコア: {best_score:.1f} | 信頼度: {confidence:.2f} | マッチキーワード: {best_keywords}"
            self._log(debug_info)
        else:
            self._log(f"最終結果: {best_match}, スコア: {best_score:.1f}, 信頼度: {confidence:.2f}")
        
        # 分類できない場合のデフォルト（会計書類用に閾値を下げる）
        if not best_match or confidence < 0.2:  # 0.3 → 0.2 に変更
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
                # バグ修正依頼書: C-2 市役所ファイル名パターンの重み付け強化
                multiplier = 3.0  # デフォルトの重み付け
                if keyword == "市役所" and "法人市民税" in str(rules.get("partial_keywords", [])):
                    multiplier = 9.0  # 市役所 → ファイル名スコア × 3.0 の重み付け適用
                    self._log_debug(f"    市役所パターン重み付け強化: 市民税関連で×{multiplier}")
                
                points = priority * multiplier
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
        # まずテキストから自治体情報を抽出（OCRベースの結果を補完）
        if prefecture_code is None or municipality_code is None:
            extracted_prefecture_code, extracted_municipality_code = self._extract_municipality_info_from_text(text, filename)
            if prefecture_code is None:
                prefecture_code = extracted_prefecture_code
            if municipality_code is None:
                municipality_code = extracted_municipality_code
        
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
        """自治体連番の適用（修正版：固定番号を厳格に管理）"""
        self._log_debug(f"自治体連番適用チェック: {document_type}, 都道府県={prefecture_code}, 市町村={municipality_code}")
        
        # 修正1: 固定番号は連番適用除外（重要な修正）
        # 修正指示書: 修正5に基づき、1003_受信通知を固定番号から除外
        FIXED_NUMBERS = {
            "0003_受信通知",     # 法人税受信通知は固定
            "0004_納付情報",     # 法人税納付情報は固定
            "3003_受信通知",     # 消費税受信通知は固定
            "3004_納付情報",     # 消費税納付情報は固定
            "1004_納付情報"      # 都道府県納付情報は固定
            # 緊急修正確認: 2004_納付情報を連番適用対象に変更（2004→2014→2024）
            # 注意: 1003_受信通知と2003_受信通知は連番適用対象のため除外
            # 注意: 2004_納付情報も連番適用対象のため除外
        }
        
        if document_type in FIXED_NUMBERS:
            self._log_debug(f"固定番号のため連番適用除外: {document_type}")
            return document_type
        
        # 修正2: 連番適用は申告書と市町村受信通知のみ
        # 都道府県申告書（1001系統）- 実際の自治体名に修正
        if document_type == "1001_都道府県_法人都道府県民税・事業税・特別法人事業税":
            if prefecture_code:
                prefecture_name = self._get_prefecture_name(prefecture_code)
                return f"{prefecture_code}_{prefecture_name}_法人都道府県民税・事業税・特別法人事業税"
        
        # 市町村申告書（2001系統）- 実際の自治体名に修正
        elif document_type == "2001_市町村_法人市民税":
            if municipality_code:
                municipality_name = self._get_municipality_name(municipality_code)
                return f"{municipality_code}_{municipality_name}_法人市民税"
        
        # 修正指示書: 修正5 - 都道府県受信通知の連番対応
        elif document_type == "1003_受信通知":
            if prefecture_code:
                # セット番号に基づく連番生成: 1003, 1013, 1023
                set_order = self._get_set_order_from_prefecture_code(prefecture_code)
                if set_order == 1:
                    return "1003_受信通知"
                elif set_order == 2:
                    return "1013_受信通知"
                elif set_order == 3:
                    return "1023_受信通知"
        
        # 市町村受信通知（2003系統）の連番対応（緊急修正）
        elif document_type == "2003_受信通知":
            if municipality_code:
                # 緊急修正: セット番号に基づく連番生成
                set_order = self._get_set_order_from_municipality_code(municipality_code)
                self._log_debug(f"連番生成: municipality セット{set_order} → {2003 + (set_order - 1) * 10}")
                
                # 緊急修正: セット1は存在しないため、セット2から3のみ対応
                if set_order == 2:
                    return "2013_受信通知"  # 蒲郡市
                elif set_order == 3:
                    return "2023_受信通知"  # 福岡市
                else:
                    # フォールバック: 不明なセットの場合はセット2を使用
                    self._log_debug(f"不明なセット番号{set_order}、セット2にフォールバック")
                    return "2013_受信通知"
        
        # 市町村納付情報（2004系統）の連番対応（緊急修正）
        elif document_type == "2004_納付情報":
            if municipality_code:
                # セット番号に基づく連番生成: 2014, 2024
                set_order = self._get_set_order_from_municipality_code(municipality_code)
                self._log_debug(f"地方税納付情報（市町村）: セット{set_order} → {2004 + (set_order - 1) * 10}")
                
                if set_order == 2:
                    return "2014_納付情報"  # 蒲郡市
                elif set_order == 3:
                    return "2024_納付情報"  # 福岡市
                else:
                    # フォールバック: 不明なセットの場合はセット2を使用
                    self._log_debug(f"不明なセット番号{set_order}、セット2にフォールバック")
                    return "2014_納付情報"
        
        # 緊急修正: 連番適用しない場合のログ強化
        self._log_debug(f"自治体連番適用なし: {document_type} (prefecture={prefecture_code}, municipality={municipality_code})")
        return document_type

    def _get_set_order_from_prefecture_code(self, prefecture_code: int) -> int:
        """都道府県コードからセット順序を取得（修正指示書: 修正5対応）"""
        # 修正指示書に基づくセット順序マッピング
        code_to_set = {
            1001: 1,  # 東京都 = セット1
            1011: 2,  # 愛知県 = セット2 
            1021: 3,  # 福岡県 = セット3
        }
        return code_to_set.get(prefecture_code, 1)  # デフォルトはセット1
    
    def _get_set_order_from_municipality_code(self, municipality_code: int) -> int:
        """市町村コードからセット順序を取得（緊急修正版）"""
        # 緊急修正: 市町村はセット2とセット3のみ存在（セット1は無し）
        code_to_set = {
            2001: 2,  # 蒲郡市 = セット2
            2011: 3,  # 福岡市 = セット3
        }
        # 緊急修正: デフォルトをセット2に変更（セット1は存在しないため）
        return code_to_set.get(municipality_code, 2)
    
    def _get_city_order_from_code(self, municipality_code: int) -> int:
        """市町村コードから順序を取得（レガシー関数 - 後方互換性のため残す）"""
        code_to_order = {
            2001: 1,  # 1番目の市町村
            2011: 2,  # 2番目の市町村
            2021: 3,  # 3番目の市町村
            2031: 4,  # 4番目の市町村
            2041: 5   # 5番目の市町村
        }
        return code_to_order.get(municipality_code, 1)

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

    def _extract_municipality_info_from_text(self, text: str, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """テキストから自治体コードを抽出（テキストベース解析）"""
        combined_text = f"{text} {filename}".lower()
        
        # 修正指示書に基づく提出先優先の自治体判定（完全修正版 v5.1.2）
        # Step 1: ファイル名から提出先事務所を特定（検出精度最大化）
        submission_office_patterns = {
            1: [  # セット1: 東京都
                "東京都港都税事務所", "港都税事務所", "芝税務署", "都税事務所", 
                "東京都", "港区", "港南", "品川グランドセントラルタワー",
                # 完全修正版: 検出パターン追加
                "tokyo", "港南税務署", "品川税務署", "東京", "都庁"
            ],  
            2: [  # セット2: 愛知県蒲郡市
                "愛知県東三河県税事務所", "東三河県税事務所", "蒲郡市役所", "蒲郡市", 
                "愛知県", "蒲郡", "豊岡町", "東三河",
                # 完全修正版: 検出パターン追加
                "aichi", "gamagori", "豊川税務署", "蒲郡", "愛知"
            ],  
            3: [  # セット3: 福岡県福岡市
                "福岡県西福岡県税事務所", "西福岡県税事務所", "福岡市役所", "福岡市", 
                "福岡県", "福岡", "中央区", "草香江", "西福岡",
                # 完全修正版: 検出パターン追加
                "fukuoka", "博多税務署", "福岡税務署", "福岡中央", "九州"
            ]
        }
        
        # Step 2: 会社住所を除外してからテキスト判定
        # 会社住所パターン（修正指示書に基づく）
        company_address_patterns = [
            r'東京都港区港南.*品川グランドセントラルタワー',
            r'愛知県蒲郡市豊岡町.*44番地',  
            r'福岡県福岡市中央区草香江'
        ]
        
        # 会社住所を除外
        filtered_text = combined_text
        for pattern in company_address_patterns:
            filtered_text = re.sub(pattern, '', filtered_text, flags=re.IGNORECASE)
        
        # ファイル名から提出先セットを判定
        detected_set = None
        for set_num, office_names in submission_office_patterns.items():
            for office_name in office_names:
                if office_name in filename.lower():
                    detected_set = set_num
                    self._log_debug(f"ファイル名提出先検出: {office_name} → セット{set_num}")
                    break
            if detected_set:
                break
        
        # テキストからも提出先を確認（会社住所除外済み）
        if not detected_set:
            for set_num, office_names in submission_office_patterns.items():
                for office_name in office_names:
                    if office_name in filtered_text:
                        detected_set = set_num
                        self._log_debug(f"テキスト提出先検出: {office_name} → セット{set_num}")
                        break
                if detected_set:
                    break
        
        # セット番号をコード番号に変換（東京都特別ルール適用）
        prefecture_code = None
        municipality_code = None
        
        if detected_set == 1:  # セット1: 東京都（市町村なし）
            prefecture_code = 1001  # 東京都は常に1001
        elif detected_set == 2:  # セット2: 愛知県蒲郡市
            prefecture_code = 1011  # セット2の都道府県
            municipality_code = 2001  # 東京都がないので繰り上がり
        elif detected_set == 3:  # セット3: 福岡県福岡市
            prefecture_code = 1021  # セット3の都道府県
            municipality_code = 2011  # 東京都がないので繰り上がり
        
        self._log_debug(f"テキスト自治体認識結果: 都道府県={prefecture_code}, 市町村={municipality_code}")
        return prefecture_code, municipality_code
    
    def _is_payment_info(self, text_content: str, filename: str) -> bool:
        """
        修正指示書: 修正3 - 納付情報の判定強化
        納付情報として必ず分類すべきキーワードをチェック
        """
        payment_indicators = [
            '納付区分番号通知',
            '納付内容を確認し',
            '以下のボタンより納付',
            'メール詳細（納付区分番号通知）'
        ]
        
        # これらのキーワードが含まれる場合は必ず納付情報として分類
        for indicator in payment_indicators:
            if indicator in text_content:
                self._log_debug(f"納付情報強制判定: {indicator}")
                return True
        
        return False
    
    def _is_receipt_notification(self, text_content: str, filename: str) -> bool:
        """
        修正指示書: 修正3 - 受信通知の判定強化
        納付関連キーワードがない場合のみ受信通知とする
        """
        receipt_indicators = [
            '送信されたデータを受け付けました',
            '申告データを受付けました',
            'メール詳細'  # 単独の場合
        ]
        
        # 納付関連キーワードがある場合は受信通知から除外
        exclusion_keywords = ['納付区分番号通知', '納付内容を確認し']
        
        has_receipt = any(indicator in text_content for indicator in receipt_indicators)
        has_payment = any(keyword in text_content for keyword in exclusion_keywords)
        
        result = has_receipt and not has_payment
        if result:
            self._log_debug(f"受信通知強制判定: 受信={has_receipt}, 納付除外={has_payment}")
        
        return result
    
    def _classify_local_tax_receipt(self, text: str, filename: str, prefecture_code: Optional[int], municipality_code: Optional[int]) -> Optional[ClassificationResult]:
        """
        バグ修正依頼書: A-2 地方税受信通知の専用分類処理
        都道府県・市町村の受信通知に適切な連番を付与
        """
        combined_text = f"{text} {filename}"
        
        # 都道府県向け受信通知の判定条件（AND条件）
        prefecture_receipt_conditions = [
            ["申告受付完了通知", "法人事業税"],
            ["申告受付完了通知", "特別法人事業税"], 
            ["県税事務所", "受信通知"],
            ["都税事務所", "受信通知"]
        ]
        
        # 市町村向け受信通知の判定条件（AND条件）
        municipality_receipt_conditions = [
            ["申告受付完了通知", "法人市民税"],
            ["申告受付完了通知", "法人市町村民税"],
            ["市役所", "申告受付完了通知"],
            ["市長", "法人市民税", "受付完了通知"]
        ]
        
        # 都道府県向け判定
        matched_condition = None
        for condition in prefecture_receipt_conditions:
            if all(kw in combined_text for kw in condition):
                matched_condition = condition
                break
        
        if matched_condition:
            set_number = self._get_jurisdiction_set_number(prefecture_code, "prefecture")
            code = self._generate_receipt_number("prefecture", set_number)
            debug_info = f"地方税受信通知判定: {code}_受信通知 | 判定条件: {matched_condition} | セット{set_number}"
            self._log(debug_info)
            
            return ClassificationResult(
                document_type=f"{code}_受信通知",
                confidence=1.0,
                matched_keywords=matched_condition,
                classification_method="local_tax_receipt_detection_prefecture",
                debug_steps=[],
                processing_log=self.processing_log.copy()
            )
        
        # 市町村向け判定  
        matched_municipality_condition = None
        for condition in municipality_receipt_conditions:
            if all(kw in combined_text for kw in condition):
                matched_municipality_condition = condition
                break
        
        if matched_municipality_condition:
            set_number = self._get_jurisdiction_set_number(municipality_code, "municipality")
            code = self._generate_receipt_number("municipality", set_number)
            debug_info = f"地方税受信通知判定: {code}_受信通知 | 判定条件: {matched_municipality_condition} | セット{set_number}"
            self._log(debug_info)
            
            return ClassificationResult(
                document_type=f"{code}_受信通知",
                confidence=1.0,
                matched_keywords=matched_municipality_condition,
                classification_method="local_tax_receipt_detection_municipality",
                debug_steps=[],
                processing_log=self.processing_log.copy()
            )
            
        return None
    
    def _generate_receipt_number(self, classification_type: str, jurisdiction_set_number: int) -> str:
        """
        バグ修正依頼書: A-2 受信通知の連番を生成
        
        Args:
            classification_type: "prefecture" or "municipality"
            jurisdiction_set_number: セット番号 (1-5)
        
        Returns:
            str: 生成された番号 (例: "1003", "2013")
        """
        base_numbers = {
            "prefecture": 1003,
            "municipality": 2003
        }
        
        if classification_type in base_numbers:
            base = base_numbers[classification_type]
            result = str(base + (jurisdiction_set_number - 1) * 10)
            self._log_debug(f"連番生成: {classification_type} セット{jurisdiction_set_number} → {result}")
            return result
        
        return "0003"  # フォールバック
    
    def _get_jurisdiction_set_number(self, code: Optional[int], jurisdiction_type: str) -> int:
        """
        バグ修正依頼書: A-2 自治体コードからセット番号を取得
        
        Args:
            code: 都道府県コードまたは市町村コード
            jurisdiction_type: "prefecture" or "municipality"
        
        Returns:
            int: セット番号 (1-5)
        """
        if jurisdiction_type == "prefecture":
            # 都道府県コードからセット番号への変換
            code_to_set = {
                1001: 1,  # 東京都
                1011: 2,  # 愛知県 
                1021: 3,  # 福岡県
                1031: 4,  # 将来の拡張用
                1041: 5   # 将来の拡張用
            }
            return code_to_set.get(code, 1)  # デフォルトはセット1
        elif jurisdiction_type == "municipality":
            # 市町村コードからセット番号への変換
            code_to_set = {
                2001: 1,  # 1番目の市町村
                2011: 2,  # 2番目の市町村
                2021: 3,  # 3番目の市町村
                2031: 4,  # 4番目の市町村
                2041: 5   # 5番目の市町村
            }
            return code_to_set.get(code, 1)  # デフォルトはセット1
        
        return 1  # フォールバック
    
    def _check_enhanced_payment_receipt_detection(self, text: str, filename: str) -> Optional[ClassificationResult]:
        """
        修正指示書: 修正3 - 納付情報・受信通知の判別強化
        特定のキーワードパターンに基づく強制分類
        """
        combined_text = f"{text} {filename}"
        
        # 納付情報の強制判定
        payment_keywords = []
        if self._is_payment_info(combined_text, filename):
            # 使用されたキーワードを特定
            payment_indicators = ['納付区分番号通知', '納付内容を確認し', '以下のボタンより納付', 'メール詳細（納付区分番号通知）']
            payment_keywords = [kw for kw in payment_indicators if kw in combined_text]
            
            # 税目によって適切な納付情報コードを返す
            if "法人税" in combined_text or "内国法人" in combined_text:
                tax_keywords = ["法人税", "内国法人"]
                found_tax_keywords = [kw for kw in tax_keywords if kw in combined_text]
                debug_info = f"納付情報強制判定: 0004_納付情報 | 判定キーワード: {payment_keywords} | 税目: {found_tax_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="0004_納付情報",
                    confidence=1.0,
                    matched_keywords=payment_keywords + found_tax_keywords,
                    classification_method="enhanced_payment_detection_houjinzei",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "消費税" in combined_text:
                found_tax_keywords = ["消費税"]
                debug_info = f"納付情報強制判定: 3004_納付情報 | 判定キーワード: {payment_keywords} | 税目: {found_tax_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="3004_納付情報",
                    confidence=1.0,
                    matched_keywords=payment_keywords + found_tax_keywords,
                    classification_method="enhanced_payment_detection_shouhizei",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "都道府県" in combined_text or "県税事務所" in combined_text or "都税事務所" in combined_text:
                prefecture_keywords = ["都道府県", "県税事務所", "都税事務所"]
                found_prefecture_keywords = [kw for kw in prefecture_keywords if kw in combined_text]
                debug_info = f"納付情報強制判定: 1004_納付情報 | 判定キーワード: {payment_keywords} | 都道府県: {found_prefecture_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="1004_納付情報",
                    confidence=1.0,
                    matched_keywords=payment_keywords + found_prefecture_keywords,
                    classification_method="enhanced_payment_detection_todofuken",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "市町村" in combined_text or "市役所" in combined_text or "市民税" in combined_text:
                municipality_keywords = ["市町村", "市役所", "市民税"]
                found_municipality_keywords = [kw for kw in municipality_keywords if kw in combined_text]
                debug_info = f"納付情報強制判定: 2004_納付情報 | 判定キーワード: {payment_keywords} | 市町村: {found_municipality_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="2004_納付情報",
                    confidence=1.0,
                    matched_keywords=payment_keywords + found_municipality_keywords,
                    classification_method="enhanced_payment_detection_shichouson",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
        
        # 受信通知の強制判定（納付関連キーワードがない場合のみ）
        if self._is_receipt_notification(combined_text, filename):
            # 使用されたキーワードを特定
            receipt_indicators = ['送信されたデータを受け付けました', '申告データを受付けました', 'メール詳細']
            receipt_keywords = [kw for kw in receipt_indicators if kw in combined_text]
            
            # 税目によって適切な受信通知コードを返す
            if "法人税" in combined_text or "内国法人" in combined_text:
                tax_keywords = ["法人税", "内国法人"]
                found_tax_keywords = [kw for kw in tax_keywords if kw in combined_text]
                debug_info = f"受信通知強制判定: 0003_受信通知 | 判定キーワード: {receipt_keywords} | 税目: {found_tax_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="0003_受信通知",
                    confidence=1.0,
                    matched_keywords=receipt_keywords + found_tax_keywords,
                    classification_method="enhanced_receipt_detection_houjinzei",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "消費税" in combined_text:
                found_tax_keywords = ["消費税"]
                debug_info = f"受信通知強制判定: 3003_受信通知 | 判定キーワード: {receipt_keywords} | 税目: {found_tax_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="3003_受信通知",
                    confidence=1.0,
                    matched_keywords=receipt_keywords + found_tax_keywords,
                    classification_method="enhanced_receipt_detection_shouhizei",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "都道府県" in combined_text or "県税事務所" in combined_text or "都税事務所" in combined_text:
                prefecture_keywords = ["都道府県", "県税事務所", "都税事務所"]
                found_prefecture_keywords = [kw for kw in prefecture_keywords if kw in combined_text]
                debug_info = f"受信通知強制判定: 1003_受信通知 | 判定キーワード: {receipt_keywords} | 都道府県: {found_prefecture_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="1003_受信通知",
                    confidence=1.0,
                    matched_keywords=receipt_keywords + found_prefecture_keywords,
                    classification_method="enhanced_receipt_detection_todofuken",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "市町村" in combined_text or "市役所" in combined_text or "市民税" in combined_text:
                municipality_keywords = ["市町村", "市役所", "市民税"]
                found_municipality_keywords = [kw for kw in municipality_keywords if kw in combined_text]
                debug_info = f"受信通知強制判定: 2003_受信通知 | 判定キーワード: {receipt_keywords} | 市町村: {found_municipality_keywords}"
                self._log(debug_info)
                
                return ClassificationResult(
                    document_type="2003_受信通知",
                    confidence=1.0,
                    matched_keywords=receipt_keywords + found_municipality_keywords,
                    classification_method="enhanced_receipt_detection_shichouson",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
        
        return None

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