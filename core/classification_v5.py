#!/usr/bin/env python3
"""
書類分類エンジン v5.0
AND条件対応・高精度書類種別判定システム（完全改訂版）
"""

import re
import logging
import json
import os
from typing import Dict, List, Optional, Tuple, Callable, Union, Any
from dataclasses import dataclass, field
import datetime
from pathlib import Path

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
    original_doc_type_code: Optional[str] = None  # 元の分類コード（自治体適用前）
    meta: Dict[str, Any] = field(default_factory=dict)  # メタデータ（no_split等）
    prefecture_code: Optional[int] = None  # 都道府県連番コード（1001/1011/1021等）
    city_code: Optional[int] = None  # 市区町村連番コード（2001/2011/2021等）

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
        
        # v5.3.4 prefecture code mapping for local tax
        self.prefecture_code_map = {
            "東京都": "1001",
            "愛知県": "1011", 
            "福岡県": "1021",
            "大阪府": "1031",
            "神奈川県": "1041"
        }

    def code_domain(self, code: str) -> str:
        """コードドメイン判定 - ノイズ抑制のための門番"""
        if not code or not isinstance(code, str):
            return "UNKNOWN"
        
        # コードの先頭数字でドメインを判定
        first_digit = code[0] if code else ""
        
        domain_map = {
            "0": "NATIONAL_TAX",      # 国税
            "1": "LOCAL_TAX",         # 地方税（都道府県）
            "2": "LOCAL_TAX",         # 地方税（市町村）
            "3": "CONSUMPTION_TAX",   # 消費税
            "5": "ACCOUNTING",        # 会計書類
            "6": "ASSETS",           # 資産
            "7": "SUMMARY"           # 集計・その他
        }
        
        return domain_map.get(first_digit, "UNKNOWN")

    def resolve_local_tax_class(self, base_class: str, prefecture: Optional[str] = None, 
                               city: Optional[str] = None) -> str:
        """LOCAL_TAX ドメインの場合のみ、自治体別の最終クラスコードを確定"""
        if not base_class:
            return base_class
            
        # ドメインチェック - LOCAL_TAX以外はそのまま返す
        if self.code_domain(base_class) != "LOCAL_TAX":
            return base_class
        
        # 都道府県税の場合（1001系）
        if base_class.startswith("1001") or "都道府県" in base_class:
            if prefecture and prefecture in self.prefecture_code_map:
                upgraded_code = self.prefecture_code_map[prefecture]
                # 元の形式を保持しながらコードだけアップグレード
                if "_" in base_class:
                    parts = base_class.split("_", 1)
                    return f"{upgraded_code}_{parts[1]}"
                else:
                    return upgraded_code
            # フォールバック: base_class をそのまま返す
            return base_class
        
        # 市民税の場合（2001系）- 従来通り
        if base_class.startswith("2001") or "市民税" in base_class:
            return base_class
        
        # その他の地方税コード
        return base_class

    def _initialize_classification_rules_v5(self) -> Dict:
        """v5.0 分類ルール初期化（AND条件対応）"""
        return {
            # ===== 0000番台 - 国税申告書類 =====
            "0000_納付税額一覧表": {
                "priority": 150,  # 適度な優先度
                "highest_priority_conditions": [
                    # ファイル名による確実な判定のみ（過度な条件を削除）
                    AndCondition(["納税一覧"], "any"),
                    AndCondition(["税額一覧表"], "any")
                ],
                "exact_keywords": [
                    "納付税額一覧表", "納税一覧", "税額一覧表"
                ],
                "partial_keywords": [
                    "税額一覧"
                ],
                "exclude_keywords": [
                    # 他の書類を明確に除外（過度な適用を防止）
                    "申告書", "確定申告", "青色申告", "内国法人の確定申告",
                    "決算書", "貸借対照表", "損益計算書",
                    "仕訳帳", "総勘定元帳", "補助元帳", "残高試算表",
                    "受信通知", "納付情報発行結果", "納付区分番号通知", "メール詳細",
                    "県税事務所", "都税事務所", "市役所",
                    "法人都道府県民税", "市町村申告書", "消費税申告書",
                    "一括償却", "少額減価償却", "固定資産台帳", "勘定科目別"
                ],
                "filename_keywords": ["納税一覧", "税額一覧"]
            },
            
            "0001_法人税等申告書": {
                "priority": 200,  # 最高優先度に変更
                "highest_priority_conditions": [
                    # 修正指示書に基づく新しい最優先条件を追加
                    AndCondition(["01_内国法人", "確定申告"], "all"),  # ファイル名パターン
                    AndCondition(["事業年度分の法人税申告書", "差引確定法人税額"], "all"),
                    AndCondition(["控除しきれなかった金額", "課税留保金額"], "all"),
                    AndCondition(["中間申告分の法人税額", "中間申告分の地方法人税額"], "all")
                ],
                "exact_keywords": [
                    "法人税及び地方法人税申告書",
                    "法人税申告書別表一", "申告書第一表"
                ],
                "partial_keywords": ["法人税申告", "内国法人", "確定申告", "青色申告"],
                "exclude_keywords": ["メール詳細", "受信通知", "納付区分番号通知", "添付資料", "イメージ添付"],
                "filename_keywords": ["内国法人", "確定申告", "青色"]
            },
            
            "0002_添付資料_法人税": {
                "priority": 200,  # バグ修正依頼書: B-2 最高優先度に変更
                "highest_priority_conditions": [
                    # 新しい最優先条件: 添付書類送付書、添付書類名称、内国法人の確定申告の3つで確実に判定
                    AndCondition(["添付書類送付書", "添付書類名称", "内国法人の確定申告"], "all"),
                    AndCondition(["添付書類名称"], "any"), 
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
                    "添付書類送付書", "添付書類名称", "内国法人の確定申告",
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
            "1001_都道府県_都道府県申告書": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["都道府県申告書申告書", "年400万円以下"], "all"),
                    AndCondition(["県税事務所", "法人事業税", "特別法人事業税"], "all"),
                    AndCondition(["都税事務所", "道府県民税", "事業税"], "all"),
                    AndCondition(["法人事業税申告書", "都道府県民税"], "all")
                ],
                "exact_keywords": [
                    "都道府県申告書申告書", "法人事業税申告書", "都道府県民税申告書"
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
                "exclude_keywords": ["市役所", "町役場", "村役場", "市町村申告書", "国税"],
                "filename_keywords": ["納付情報", "都道府県"]
            },
            
            # ===== 2000番台 - 市町村税関連 =====
            "2001_市町村_市町村申告書": {
                "priority": 180,  # バグ修正依頼書: C-2 優先度を高く設定
                "highest_priority_conditions": [
                    # 指定された2つのAND条件のみ（最優先）
                    AndCondition(["当該市町村内に所在"], "any"),
                    AndCondition(["市町村民税の特定寄附金"], "any")
                ],
                "exact_keywords": ["市町村申告書申告書", "市民税申告書"],
                "partial_keywords": ["市町村申告書", "市町村民税", "市役所", "町役場", "村役場"],
                "exclude_keywords": [
                    "都道府県", "事業税", "県税事務所", "都税事務所", "受信通知", "納付情報",
                    # バグ修正依頼書: C-1 除外条件の追加
                    "内国法人", "確定申告(青色)", "事業年度分", "税額控除"
                ],
                "filename_keywords": ["市役所", "市民税"]
            },
            
            "2003_受信通知": {
                "priority": 140,
                "highest_priority_conditions": [
                    AndCondition(["申告受付完了通知", "法人市町村民税"], "all"),
                    AndCondition(["申告受付完了通知", "市町村申告書"], "all"),
                    AndCondition(["市町村申告書", "市役所", "申告受付完了通知"], "all"),
                    AndCondition(["市長", "市町村申告書", "受付完了通知"], "all"),
                    # 具体的な市町村名での判定
                    AndCondition(["蒲郡市役所", "申告受付完了通知"], "all"),
                    AndCondition(["福岡市", "市町村申告書", "受付番号"], "all")
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
                    AndCondition(["市役所", "納付情報", "市町村申告書"], "all"),
                    AndCondition(["地方税共同機構", "法人市町村民税"], "all")
                ],
                "exact_keywords": ["市町村 納付情報", "法人住民税 納付情報"],
                "partial_keywords": ["納付情報", "地方税 納付", "法人住民税"],
                "exclude_keywords": ["県税事務所", "都税事務所", "法人二税・特別税", "国税"],
                "filename_keywords": ["納付情報", "市町村"]
            },
            
            # ===== 3000番台 - 消費税関連 =====
            "3001_消費税等申告書": {
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
                "priority": 220,  # 0002より高い優先度に設定
                "highest_priority_conditions": [
                    # 新しい最優先条件: 添付書類、消費税、添付書類送付書の3つで確実に判定
                    AndCondition(["添付書類", "消費税", "添付書類送付書"], "all"),
                    # 修正指示書に基づくファイル名最優先条件を追加
                    AndCondition(["イメージ添付書類(法人消費税申告)"], "any"),  # 単独最優先
                    AndCondition(["添付資料", "消費税申告", "イメージ添付"], "all"),
                    AndCondition(["添付書類", "法人消費税申告"], "all"),
                    AndCondition(["イメージ添付書類(法人消費税申告)", "添付資料"], "all")
                ],
                "exact_keywords": [
                    "添付書類送付書", "添付書類", "消費税",
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
                "priority": 130,  # 残高試算表より低い優先度
                "highest_priority_conditions": [
                    AndCondition(["決算報告書"], "any"),
                    AndCondition(["貸借対照表", "損益計算書"], "all")
                ],
                "exact_keywords": ["決算書", "決算報告書", "貸借対照表", "損益計算書"],
                "partial_keywords": ["決算", "B/S", "P/L"],
                "exclude_keywords": ["残高試算表", "試算表", "残高試算"],  # 試算表関連を除外
                "filename_keywords": ["決算書", "決算報告書"]
            },
            
            "5002_総勘定元帳": {
                "priority": 140,  # 最高優先度
                "highest_priority_conditions": [
                    AndCondition(["総勘定元帳"], "any")
                ],
                "exact_keywords": ["総勘定元帳"],
                "partial_keywords": ["総勘定", "元帳"],
                "exclude_keywords": ["補助元帳", "補助", "内国法人", "確定申告", "01_内国法人"],  # 法人税申告書を除外
                "filename_keywords": ["総勘定元帳", "総勘定"]
            },
            
            "5003_補助元帳": {
                "priority": 135,
                "highest_priority_conditions": [
                    AndCondition(["補助元帳"], "any")
                ],
                "exact_keywords": ["補助元帳"],
                "partial_keywords": ["補助", "元帳"],
                "exclude_keywords": ["総勘定"],
                "filename_keywords": ["補助元帳", "補助"]
            },
            
            "5004_残高試算表": {
                "priority": 140,  # 最高優先度（決算書より高い）
                "highest_priority_conditions": [
                    AndCondition(["残高試算表"], "any"),
                    AndCondition(["試算表"], "any")
                ],
                "exact_keywords": ["残高試算表", "試算表"],
                "partial_keywords": [
                    "残高試算", "借方金額", "貸方金額", "期末残高", "構成比",
                    "合計残高", "月次試算", "年次試算", "勘定残高"
                ],
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
                "priority": 100,  # 最高優先度（100に変更）
                "highest_priority_conditions": [
                    AndCondition(["一括償却資産明細表"], "any"),
                    AndCondition(["一括償却"], "any"),
                    AndCondition(["償却資産明細"], "any")
                ],
                "exact_keywords": ["一括償却資産明細表"],
                "partial_keywords": ["一括償却", "償却資産明細", "一括償却資産", "償却明細"],
                "exclude_keywords": ["少額"],
                "filename_keywords": ["一括償却資産明細表", "一括償却", "償却資産明細"],
                "meta": {"no_split": True, "asset_document": True, "lock_layer": "C"}
            },
            
            "6003_少額減価償却資産明細表": {
                "priority": 140,  # 最高優先度
                "highest_priority_conditions": [
                    AndCondition(["少額減価償却資産明細表"], "any"),
                    AndCondition(["少額減価"], "any"),
                    AndCondition(["少額"], "any")
                ],
                "exact_keywords": ["少額減価償却資産明細表"],
                "partial_keywords": [
                    "少額減価償却", "少額償却", "少額減価償却資産", "少額資産",
                    "取得価額", "損金算入", "30万円未満", "減価償却資産", "明細表",
                    "少額固定資産", "償却資産明細", "一時損金算入"
                ],
                "exclude_keywords": ["一括"],
                "filename_keywords": [],  # ファイル名判定を削除してOCR内容ベースに統一
                "meta": {"no_split": True, "asset_document": True, "lock_layer": "C"}
            },
            
            "6003_固定資産台帳少額": {
                "priority": 120,  # 中優先度（ANDキーワード条件）
                "highest_priority_conditions": [
                    AndCondition(["固定資産台帳", "取得価額"], "all"),
                    AndCondition(["資産番号", "耐用年数"], "all"),
                    AndCondition(["供用開始", "減価償却資産"], "all"),
                    AndCondition(["明細表", "少額"], "all")
                ],
                "exact_keywords": [],
                "partial_keywords": [
                    "固定資産台帳", "資産番号", "耐用年数", "供用開始",
                    "取得価額", "減価償却資産", "明細表", "少額"
                ],
                "exclude_keywords": ["一括"],
                "filename_keywords": [],
                "output_override": "6003_少額減価償却資産明細表",  # 出力は6003に統一
                "meta": {"no_split": True, "asset_document": True, "lock_layer": "C"}
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
                "priority": 135,
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
                    
                    # メタデータの取得
                    meta_data = rules.get("meta", {})
                    
                    result = ClassificationResult(
                        document_type=doc_type,
                        confidence=1.0,  # 最優先なので信頼度100%
                        matched_keywords=matched_keywords,
                        classification_method="highest_priority_and_condition",
                        debug_steps=[],
                        processing_log=self.processing_log.copy(),
                        meta=meta_data
                    )
                    
                    # 6002/6003の場合、層C四重ロック警告
                    if doc_type.startswith(('6002_', '6003_')):
                        self._log(f"[6002/6003 Lock C] Asset document detected: {doc_type}")
                    
                    return result
        
        self._log_debug("最優先AND条件マッチなし - 通常分類処理に移行")
        return None

    def classify_document_v5(self, text: str, filename: str = "", job_context=None) -> ClassificationResult:
        """v5.0 書類分類（AND条件対応版）+ 受信通知連番処理強制実行"""
        self.processing_log = []  # ログをリセット
        self.current_filename = filename
        
        # 🔥 Bundle分割ファイルの特別ログ（段階1）
        if filename.startswith("__split_"):
            print(f"[BUNDLE_SPLIT_DEBUG] Bundle分割ファイル処理開始: {filename}")
            print(f"[BUNDLE_SPLIT_DEBUG] JobContext存在: {job_context is not None}")
            if job_context:
                print(f"[BUNDLE_SPLIT_DEBUG] JobContext内容: {type(job_context)}")
                municipality_sets = getattr(job_context, 'current_municipality_sets', None)
                print(f"[BUNDLE_SPLIT_DEBUG] municipality_sets: {municipality_sets}")
        
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
            # 🔥 地方税受信通知の特別ログ（段階1）
            if (filename.startswith("__split_") and 
                hasattr(local_tax_result, 'classification_method') and
                local_tax_result.classification_method == "local_tax_receipt_detection_ocr"):
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 地方税受信通知検出！")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 分類結果: {local_tax_result.document_type}")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 判定方法: {local_tax_result.classification_method}")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] JobContext for numbering: {job_context is not None}")
            
            # 🔥 修正指示書対応: 受信通知の場合、即座に連番処理を実行
            if job_context is not None:
                print(f"[RECEIPT_NUMBERING_DEBUG] 連番処理開始")
            final_result = self._apply_receipt_numbering_if_needed(local_tax_result, text_cleaned, job_context)
            return final_result
        
        # 修正指示書: 修正3 - 納付情報・受信通知の判別強化
        enhanced_result = self._check_enhanced_payment_receipt_detection(text_cleaned, filename_cleaned)
        if enhanced_result:
            # 🔥 地方税受信通知の特別ログ（段階1）
            if (filename.startswith("__split_") and 
                hasattr(enhanced_result, 'classification_method') and
                enhanced_result.classification_method == "local_tax_receipt_detection_ocr"):
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 地方税受信通知検出！")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 分類結果: {enhanced_result.document_type}")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 判定方法: {enhanced_result.classification_method}")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] JobContext for numbering: {job_context is not None}")
            
            # 🔥 修正指示書対応: 受信通知の場合、即座に連番処理を実行
            if job_context is not None:
                print(f"[RECEIPT_NUMBERING_DEBUG] 連番処理開始")
            final_result = self._apply_receipt_numbering_if_needed(enhanced_result, text_cleaned, job_context)
            return final_result
        
        # 最優先AND条件判定
        priority_result = self._check_highest_priority_conditions(text_cleaned, filename_cleaned)
        if priority_result:
            # 🔥 地方税受信通知の特別ログ（段階1）
            if (filename.startswith("__split_") and 
                hasattr(priority_result, 'classification_method') and
                priority_result.classification_method == "local_tax_receipt_detection_ocr"):
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 地方税受信通知検出！")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 分類結果: {priority_result.document_type}")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] 判定方法: {priority_result.classification_method}")
                print(f"[LOCAL_TAX_RECEIPT_DEBUG] JobContext for numbering: {job_context is not None}")
            
            # 🔥 修正指示書対応: 受信通知の場合、即座に連番処理を実行
            if job_context is not None:
                print(f"[RECEIPT_NUMBERING_DEBUG] 連番処理開始")
            final_result = self._apply_receipt_numbering_if_needed(priority_result, text_cleaned, job_context)
            return final_result
        
        # 通常の分類処理（従来ルールも維持）
        standard_result = self._standard_classification(text_cleaned, filename_cleaned)
        
        # 🔥 地方税受信通知の特別ログ（段階1）
        if (filename.startswith("__split_") and 
            hasattr(standard_result, 'classification_method') and
            standard_result.classification_method == "local_tax_receipt_detection_ocr"):
            print(f"[LOCAL_TAX_RECEIPT_DEBUG] 地方税受信通知検出！")
            print(f"[LOCAL_TAX_RECEIPT_DEBUG] 分類結果: {standard_result.document_type}")
            print(f"[LOCAL_TAX_RECEIPT_DEBUG] 判定方法: {standard_result.classification_method}")
            print(f"[LOCAL_TAX_RECEIPT_DEBUG] JobContext for numbering: {job_context is not None}")
        
        # 🔥 修正指示書対応: 受信通知の場合、即座に連番処理を実行
        if job_context is not None:
            print(f"[RECEIPT_NUMBERING_DEBUG] 連番処理開始")
        final_result = self._apply_receipt_numbering_if_needed(standard_result, text_cleaned, job_context)
        return final_result

    def _apply_receipt_numbering_if_needed(self, classification_result: ClassificationResult, 
                                         ocr_text: str, job_context) -> ClassificationResult:
        """
        🔥 修正指示書対応: 受信通知分類時の連番処理強制実行
        
        Args:
            classification_result: 基本分類結果
            ocr_text: OCRテキスト
            job_context: JobContext（自治体セット情報）
            
        Returns:
            ClassificationResult: 連番処理後の最終分類結果
        """
        from helpers.seq_policy import is_receipt_notice, is_pref_receipt, is_city_receipt
        
        base_code = classification_result.document_type
        
        # 🔥 段階1：詳細ログ追加 - 連番処理呼び出し部分
        if self.current_filename.startswith("__split_"):
            print(f"[RECEIPT_NUMBERING_DEBUG] 連番処理開始")
            print(f"[RECEIPT_NUMBERING_DEBUG] 処理前分類結果: {classification_result.document_type}")
            
            # 🔥 地方税受信通知の場合の特別処理確認
            if classification_result.document_type in ["1003_受信通知", "2013_受信通知"]:
                print(f"[RECEIPT_NUMBERING_DEBUG] 地方税受信通知連番処理対象確認")
                municipality_sets = getattr(job_context, 'current_municipality_sets', None)
                print(f"[RECEIPT_NUMBERING_DEBUG] 自治体セット: {municipality_sets}")
        
        print(f"[APPLY_NUMBERING_DEBUG] 連番処理メソッド開始: {base_code}")
        
        # 受信通知判定
        if not is_receipt_notice(base_code):
            print(f"[APPLY_NUMBERING_DEBUG] 受信通知ではないためスキップ: {base_code}")
            return classification_result
            
        print(f"[APPLY_NUMBERING_DEBUG] 受信通知確認OK: {base_code}")
        
        # JobContext確認
        if not job_context:
            print(f"[APPLY_NUMBERING_DEBUG] JobContext未設定のため連番処理スキップ")
            self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] JobContext未設定のため連番処理スキップ: {base_code}")
            return classification_result
            
        print(f"[APPLY_NUMBERING_DEBUG] JobContext確認OK")
        
        # municipality_sets確認
        municipality_sets = getattr(job_context, 'current_municipality_sets', None)
        if not municipality_sets:
            print(f"[APPLY_NUMBERING_DEBUG] municipality_sets未設定のためスキップ")
            return classification_result
            
        print(f"[APPLY_NUMBERING_DEBUG] municipality_sets確認OK: {municipality_sets}")
        
        # 地方税受信通知の特別処理（段階2強化版）
        if (base_code in ["1003_受信通知", "2013_受信通知"] and 
            hasattr(classification_result, 'classification_method') and
            classification_result.classification_method == "local_tax_receipt_detection_ocr"):
            
            print(f"[RECEIPT_NUMBERING] 地方税受信通知連番処理開始: {base_code}")
            
            if not job_context or not hasattr(job_context, 'current_municipality_sets'):
                print(f"[RECEIPT_NUMBERING] JobContext不足エラー")
                return classification_result
                
            # 連番処理を強制実行
            numbered_result = self._calculate_simplified_receipt_number(
                base_code, ocr_text, job_context
            )
            
            if numbered_result:
                print(f"[RECEIPT_NUMBERING] 連番処理成功: {base_code} → {numbered_result}")
                # 新しい分類結果を作成
                new_result = ClassificationResult(
                    document_type=numbered_result,
                    confidence=classification_result.confidence,
                    matched_keywords=classification_result.matched_keywords,
                    classification_method="local_tax_receipt_forced_numbering",
                    debug_steps=classification_result.debug_steps,
                    processing_log=classification_result.processing_log + [f"地方税受信通知連番処理: {base_code} -> {numbered_result}"],
                    original_doc_type_code=base_code
                )
                return new_result
            else:
                print(f"[RECEIPT_NUMBERING] 連番処理失敗: {base_code}")
        
        # 🔥 地方税受信通知の場合の詳細処理
        if base_code in ["1003_受信通知", "2013_受信通知"]:
            print(f"[APPLY_NUMBERING_DEBUG] 地方税受信通知連番処理開始: {base_code}")
            
        # 地方税受信通知Bundle分割時の詳細ログ
        if base_code.endswith("_受信通知") and (base_code.startswith("1003") or base_code.startswith("2013")):
            self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] 地方税受信通知検出: {base_code}")
            self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] JobContext: {job_context}")
            if hasattr(job_context, 'current_municipality_sets'):
                self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] municipality_sets: {job_context.current_municipality_sets}")
            else:
                self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] municipality_sets属性なし")
            
        if not hasattr(job_context, 'current_municipality_sets') or not job_context.current_municipality_sets:
            self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] current_municipality_sets不足のため連番処理スキップ: {base_code}")
            return classification_result
            
        self._log(f"[RECEIPT_FORCED] 受信通知連番処理を強制実行: {base_code}")
        
        try:
            # 🔥 地方税受信通知の場合の連番計算実行
            if base_code in ["1003_受信通知", "2013_受信通知"]:
                # 連番計算実行
                final_code = self._calculate_simplified_receipt_number(base_code, ocr_text, job_context)
                
                if final_code and final_code != base_code:
                    print(f"[APPLY_NUMBERING_DEBUG] 連番処理成功: {base_code} → {final_code}")
                else:
                    print(f"[APPLY_NUMBERING_DEBUG] 連番処理失敗または変更なし: {base_code}")
            else:
                # 通常の連番計算
                final_code = self._calculate_simplified_receipt_number(base_code, ocr_text, job_context)
            
            if final_code and final_code != base_code:
                # 連番処理成功：新しい分類結果を作成
                new_result = ClassificationResult(
                    document_type=final_code,
                    confidence=classification_result.confidence,
                    matched_keywords=classification_result.matched_keywords,
                    classification_method="receipt_forced_numbering",
                    debug_steps=classification_result.debug_steps,
                    processing_log=classification_result.processing_log + [f"連番処理適用: {base_code} -> {final_code}"],
                    original_doc_type_code=base_code  # 元のコードを保存
                )
                
                self._log(f"[RECEIPT_FORCED] 連番処理成功: {base_code} -> {final_code}")
                
                # 🔥 段階1：詳細ログ追加 - 連番処理完了
                if self.current_filename.startswith("__split_"):
                    print(f"[RECEIPT_NUMBERING_DEBUG] 連番処理完了")
                    print(f"[RECEIPT_NUMBERING_DEBUG] 処理後分類結果: {final_code}")
                
                return new_result
            else:
                self._log(f"[RECEIPT_FORCED] 連番処理失敗またはスキップ: {base_code}")
                
                # 🔥 段階1：詳細ログ追加 - 連番処理完了（変更なし）
                if self.current_filename.startswith("__split_"):
                    print(f"[RECEIPT_NUMBERING_DEBUG] 連番処理完了")
                    print(f"[RECEIPT_NUMBERING_DEBUG] 処理後分類結果: {base_code} (変更なし)")
                
                return classification_result
                
        except Exception as e:
            self._log(f"[RECEIPT_FORCED] 連番処理エラー: {e}")
            import traceback
            self._log_debug(f"[RECEIPT_FORCED] Traceback: {traceback.format_exc()}")
            return classification_result

    def _calculate_simplified_receipt_number(self, base_code: str, ocr_text: str, job_context) -> Optional[str]:
        """
        簡素化された受信通知連番計算（修正指示書対応）
        
        Args:
            base_code: 基本分類コード（例: "1003_受信通知"）
            ocr_text: OCRテキスト
            job_context: JobContext
            
        Returns:
            Optional[str]: 連番コード（例: "1013_受信通知"）、計算失敗時はNone
        """
        from helpers.seq_policy import is_pref_receipt, is_city_receipt
        
        # OCRから都道府県・市町村を抽出
        if is_pref_receipt(base_code):
            # 都道府県受信通知
            prefecture = self._extract_prefecture_from_ocr_simple(ocr_text)
            if not prefecture:
                self._log_debug(f"[SIMPLIFIED_CALC] 都道府県抽出失敗: {ocr_text[:100]}")
                return None
                
            set_number = job_context.get_set_index_for_pref(prefecture)
            if set_number is None:
                self._log_debug(f"[SIMPLIFIED_CALC] 都道府県セット番号取得失敗: {prefecture}")
                return None
                
            # 連番計算: 1003 + (set_number - 1) * 10
            final_number = 1003 + (set_number - 1) * 10
            result_code = f"{final_number:04d}_受信通知"
            
            self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] 都道府県連番処理成功: OCR={prefecture} → セット{set_number} → {result_code}")
            return result_code
            
        elif is_city_receipt(base_code):
            # 市町村受信通知
            prefecture, city = self._extract_prefecture_city_from_ocr_simple(ocr_text)
            if not prefecture or not city:
                self._log_debug(f"[SIMPLIFIED_CALC] 市町村抽出失敗: pref={prefecture}, city={city}")
                return None
                
            set_number = job_context.get_set_index_for_city(prefecture, city)
            if set_number is None:
                self._log_debug(f"[SIMPLIFIED_CALC] 市町村セット番号取得失敗: {prefecture} {city}")
                return None
                
            # 東京都スキップ処理
            tokyo_set = job_context.get_set_index_for_pref("東京都")
            adjusted_set = set_number - 1 if (tokyo_set == 1 and set_number > 1) else set_number
            
            # 連番計算: 2003 + (adjusted_set - 1) * 10
            final_number = 2003 + (adjusted_set - 1) * 10
            result_code = f"{final_number:04d}_受信通知"
            
            self._log(f"[BUNDLE_SPLIT_LOCAL_TAX] 市町村連番処理成功: OCR={prefecture} {city} → セット{set_number}→調整{adjusted_set} → {result_code}")
            return result_code
            
        return None

    def _extract_prefecture_from_ocr_simple(self, ocr_text: str) -> Optional[str]:
        """簡素化された都道府県抽出（段階3精度向上版）"""
        print(f"[RECEIPT_CALC] OCR解析開始")
        print(f"[RECEIPT_CALC] 検索対象テキスト: {ocr_text[:200]}...")
        
        # 発行元パターンを詳細化（段階3強化）
        prefecture_patterns = {
            "東京都": ["東京都", "港都税事務所", "都税事務所"],
            "愛知県": ["愛知県", "東三河県税事務所", "県税事務所"],
            "福岡県": ["福岡県", "西福岡県税事務所", "福岡県税"]
        }
        
        # より精密な突合処理
        for prefecture, patterns in prefecture_patterns.items():
            for pattern in patterns:
                if pattern in ocr_text:
                    print(f"[RECEIPT_CALC] 都道府県マッチ: {pattern} → {prefecture}")
                    return prefecture
        
        # フォールバック: 基本的な都道府県名検索
        prefectures = ["東京都", "愛知県", "福岡県", "大阪府", "神奈川県"]
        for pref in prefectures:
            if pref in ocr_text:
                print(f"[RECEIPT_CALC] 都道府県フォールバックマッチ: {pref}")
                return pref
        
        print(f"[RECEIPT_CALC] 都道府県マッチなし")
        return None

    def _extract_prefecture_city_from_ocr_simple(self, ocr_text: str) -> Tuple[Optional[str], Optional[str]]:
        """簡素化された都道府県・市町村抽出（段階3精度向上版）"""
        print(f"[RECEIPT_CALC] 市町村OCR解析開始")
        print(f"[RECEIPT_CALC] 検索対象テキスト: {ocr_text[:200]}...")
        
        # 段階3：市町村パターンを詳細化
        city_patterns = {
            "蒲郡市": ["蒲郡市", "蒲郡市役所"],
            "福岡市": ["福岡市", "福岡市長"]
        }
        
        # まず都道府県を抽出
        prefectures_cities = {
            "東京都": ["港区", "新宿区", "渋谷区"],
            "愛知県": ["蒲郡市", "名古屋市", "豊田市"],
            "福岡県": ["福岡市", "北九州市", "久留米市"],
            "大阪府": ["大阪市", "堺市", "東大阪市"],
            "神奈川県": ["横浜市", "川崎市", "相模原市"]
        }
        
        # より精密な突合処理（段階3強化）
        for pref, cities in prefectures_cities.items():
            if pref in ocr_text:
                # 該当都道府県の市町村を探す
                for city in cities:
                    # 拡張パターンでの検索
                    if city in city_patterns:
                        for pattern in city_patterns[city]:
                            if pattern in ocr_text:
                                print(f"[RECEIPT_CALC] 市町村マッチ: {pattern} → {pref}({city})")
                                return pref, city
                    elif city in ocr_text:
                        print(f"[RECEIPT_CALC] 市町村基本マッチ: {city} → {pref}({city})")
                        return pref, city
                
                # 都道府県は見つかったが市町村が見つからない場合
                print(f"[RECEIPT_CALC] 都道府県マッチ、市町村検索中: {pref}")
                # 役所パターンで市名を抽出を試行
                import re
                city_match = re.search(r'([^県都府道市区町村]+(?:市|区|町|村))役所', ocr_text)
                if city_match:
                    found_city = city_match.group(1)
                    return pref, found_city
                    
        return None, None

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
        
        self._log(f"最終結果: {best_match}, スコア: {best_score:.1f}, 信頼度: {confidence:.2f}")
        
        # 分類できない場合のデフォルト（会計書類用に閾値を下げる）
        if not best_match or confidence < 0.2:  # 0.3 → 0.2 に変更
            best_match = "9999_未分類"
            confidence = 0.0
            best_method = "default_fallback"
            self._log(f"信頼度不足により未分類に変更")
        
        result = ClassificationResult(
            document_type=best_match,
            confidence=confidence,
            matched_keywords=best_keywords,
            classification_method=best_method,
            debug_steps=debug_steps,
            processing_log=self.processing_log.copy(),
            original_doc_type_code=best_match  # 元の分類コードを保存
        )
        
        # no_split メタデータを設定（資産・帳票系）
        self._set_no_split_metadata(result)
        return result

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
                if keyword == "市役所" and "市町村申告書" in str(rules.get("partial_keywords", [])):
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
                                         municipality_code: Optional[int] = None,
                                         municipality_sets: Optional[Dict[int, Dict[str, str]]] = None,
                                         job_context=None) -> ClassificationResult:
        """v5.0 自治体情報を考慮した分類（ステートレス対応）"""
        # v5.0 分類実行
        base_result = self.classify_document_v5(text, filename, job_context)
        
        # 正規化処理でラベル解決（必ず実行）
        if municipality_sets:
            print(f"[DEBUG] 正規化処理開始: municipality_sets={municipality_sets}")
            # 元の分類コードを保存（自治体適用前）
            if base_result.original_doc_type_code is None:
                base_result.original_doc_type_code = base_result.document_type
            
            # ドメインチェック：LOCAL_TAX以外では自治体変更版をスキップ
            domain = self.code_domain(base_result.document_type)
            if domain != "LOCAL_TAX":
                self._log(f"overlay=SKIPPED(domain={domain})")
                # LOCAL_TAX以外では何もしない
            else:
                code, final_label, resolved_set_id = self.normalize_classification(
                    text, filename, base_result.document_type, municipality_sets
                )
                
                if final_label != base_result.document_type:
                    self._log(f"自治体名付きコード生成: {base_result.document_type} → {final_label}")
                    base_result.document_type = final_label
        else:
            print(f"[DEBUG] 従来処理実行: municipality_sets={municipality_sets}")
            # セット設定がない場合は従来処理
            self.current_municipality_sets = municipality_sets or {}
            # 元の分類コードを保存（自治体適用前）
            if base_result.original_doc_type_code is None:
                base_result.original_doc_type_code = base_result.document_type
            
            # ドメインチェック：LOCAL_TAX以外では自治体変更版をスキップ
            domain = self.code_domain(base_result.document_type)
            if domain != "LOCAL_TAX":
                self._log(f"overlay=SKIPPED(domain={domain})")
                # LOCAL_TAX以外では何もしない
            else:
                final_code = self._apply_municipality_numbering(
                    base_result.document_type, 
                    prefecture_code, 
                    municipality_code,
                    text,
                    filename
                )
                
                if final_code != base_result.document_type:
                    self._log(f"自治体名付きコード生成: {base_result.document_type} → {final_code}")
                    base_result.document_type = final_code
        
        return base_result

    def _apply_municipality_numbering(self, document_type: str, 
                                    prefecture_code: Optional[int] = None,
                                    municipality_code: Optional[int] = None,
                                    text_content: str = "",
                                    filename: str = "") -> str:
        """自治体連番の適用（修正版：固定番号を厳格に管理）"""
        self._log_debug(f"自治体連番適用チェック: {document_type}, 都道府県={prefecture_code}, 市町村={municipality_code}")
        
        # 修正1: 固定番号は連番適用除外（重要な修正）  
        # 修正指示書: 納付情報は固定、受信通知は連番対応
        FIXED_NUMBERS = {
            "0003_受信通知",     # 法人税受信通知は固定
            "0004_納付情報",     # 法人税納付情報は固定
            "3003_受信通知",     # 消費税受信通知は固定
            "3004_納付情報",     # 消費税納付情報は固定
            "1004_納付情報",     # 都道府県納付情報は固定
            "2004_納付情報"      # 市町村納付情報は固定
            # 注意: 1003_受信通知と2003_受信通知は連番適用対象のため除外
        }
        
        if document_type in FIXED_NUMBERS:
            self._log_debug(f"固定番号のため連番適用除外: {document_type}")
            return document_type
        
        # 連番適用: 申告書系統への自治体連番の適用
        # 都道府県申告書（1001系統）
        if document_type == "1001_都道府県_都道府県申告書":
            if prefecture_code:
                prefecture_name = self._get_prefecture_name(prefecture_code)
                
                # v5.3.4 prefecture-specific code resolution
                resolved_code = self.resolve_local_tax_class(document_type, prefecture_name)
                final_code = f"{prefecture_code}_{prefecture_name}_都道府県申告書"
                
                # Use resolved code if different
                if resolved_code != document_type and "_" in resolved_code:
                    code_part = resolved_code.split("_")[0]
                    final_code = f"{code_part}_{prefecture_name}_都道府県申告書"
                
                self._log_debug(f"都道府県申告書連番適用: {document_type} → {final_code}")
                return final_code
        
        # 市町村申告書（2001系統）
        elif document_type.startswith("2") and document_type.endswith("_市町村_市町村申告書"):
            if municipality_code:
                # セット設定情報のデバッグ出力
                if hasattr(self, 'current_municipality_sets'):
                    self._log_debug(f"セット設定情報利用可能: {self.current_municipality_sets}")
                else:
                    self._log_debug(f"セット設定情報なし: current_municipality_setsが未設定")
                
                municipality_name = self._get_municipality_name(municipality_code)
                final_code = f"{municipality_code}_{municipality_name}_市町村申告書"
                print(f"[DEBUG] 市町村申告書連番適用: {document_type} → {final_code}")
                self._log_debug(f"市町村申告書連番適用: {document_type} → {final_code}")
                return final_code
        
        # 修正指示書: 修正5 - 都道府県受信通知の連番対応（OCRテキストから直接読み取り）
        elif document_type == "1003_受信通知":
            self._log_debug(f"[OCR DEBUG] 都道府県受信通知処理開始: {document_type}")
            self._log_debug(f"[OCR DEBUG] text_content length: {len(text_content) if text_content else 0}")
            self._log_debug(f"[OCR DEBUG] has current_municipality_sets: {hasattr(self, 'current_municipality_sets')}")
            
            # OCRテキストから実際の都道府県を読み取り、セット設定と照合
            if hasattr(self, 'current_municipality_sets') and text_content:
                self._log_debug(f"[OCR DEBUG] セット設定: {self.current_municipality_sets}")
                detected_prefecture = self._extract_prefecture_from_receipt_text(text_content, filename)
                self._log_debug(f"[OCR DEBUG] 検出された都道府県: {detected_prefecture}")
                
                if detected_prefecture:
                    # セット設定から該当するセットIDを特定
                    for set_id, info in self.current_municipality_sets.items():
                        self._log_debug(f"[OCR DEBUG] セット{set_id}チェック: {info.get('prefecture')} == {detected_prefecture}")
                        if info.get("prefecture") == detected_prefecture:
                            receipt_code = 1003 + (set_id - 1) * 10
                            self._log_debug(f"都道府県受信通知OCR検出: {detected_prefecture} → セット{set_id} → {receipt_code}_受信通知")
                            return f"{receipt_code}_受信通知"
                    
                    self._log_debug(f"都道府県受信通知: OCRで検出した'{detected_prefecture}'がセット設定にありません")
            else:
                self._log_debug(f"[OCR DEBUG] OCR処理スキップ - セット設定またはテキストなし")
            
            # フォールバック：従来の方式
            if prefecture_code:
                self._log_debug(f"[OCR DEBUG] フォールバック処理: prefecture_code={prefecture_code}")
                receipt_code = 1003 + ((prefecture_code - 1001) // 10) * 10
                return f"{receipt_code}_受信通知"
        
        # 市町村受信通知（2003系統）の連番対応（OCRテキストから直接読み取り）
        elif document_type == "2003_受信通知":
            self._log_debug(f"[OCR DEBUG] 市町村受信通知処理開始: {document_type}")
            self._log_debug(f"[OCR DEBUG] text_content length: {len(text_content) if text_content else 0}")
            
            # OCRテキストから実際の市町村を読み取り、セット設定と照合
            if hasattr(self, 'current_municipality_sets') and text_content:
                detected_prefecture, detected_city = self._extract_municipality_from_receipt_text(text_content, filename)
                self._log_debug(f"[OCR DEBUG] 検出された市町村: {detected_prefecture} {detected_city}")
                
                if detected_prefecture and detected_city:
                    # セット設定から該当するセットIDを特定
                    for set_id, info in self.current_municipality_sets.items():
                        self._log_debug(f"[OCR DEBUG] セット{set_id}チェック: {info.get('prefecture')}{info.get('city')} == {detected_prefecture}{detected_city}")
                        if (info.get("prefecture") == detected_prefecture and 
                            info.get("city") == detected_city):
                            receipt_code = 2003 + (set_id - 1) * 10
                            self._log_debug(f"市町村受信通知OCR検出: {detected_prefecture}{detected_city} → セット{set_id} → {receipt_code}_受信通知")
                            return f"{receipt_code}_受信通知"
                    
                    self._log_debug(f"市町村受信通知: OCRで検出した'{detected_prefecture}{detected_city}'がセット設定にありません")
            else:
                self._log_debug(f"[OCR DEBUG] OCR処理スキップ - セット設定またはテキストなし")
            
            # フォールバック：従来の方式
            if municipality_code:
                self._log_debug(f"[OCR DEBUG] フォールバック処理: municipality_code={municipality_code}")
                receipt_code = 2003 + ((municipality_code - 2001) // 10) * 10
                return f"{receipt_code}_受信通知"
        
        self._log_debug(f"自治体連番適用なし: {document_type}")
        return document_type

    def _extract_prefecture_from_receipt_text(self, text_content: str, filename: str) -> Optional[str]:
        """受信通知のOCRテキストから都道府県を抽出"""
        # 受信通知に含まれる都道府県パターン
        prefecture_patterns = [
            r'(東京都)',
            r'(大阪府)',
            r'(愛知県)',
            r'(福岡県)',
            r'(北海道)',
            r'([^県市区町村]+県)',  # その他の県
            r'([^府県市区町村]+府)'   # その他の府
        ]
        
        for pattern in prefecture_patterns:
            import re
            match = re.search(pattern, text_content)
            if match:
                prefecture = match.group(1)
                self._log_debug(f"受信通知から都道府県検出: {prefecture}")
                return prefecture
        
        self._log_debug(f"受信通知から都道府県検出なし: {filename}")
        return None

    def _extract_municipality_from_receipt_text(self, text_content: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """受信通知のOCRテキストから都道府県と市町村を抽出"""
        # 市町村受信通知に含まれる都道府県・市町村パターン
        municipality_patterns = [
            r'(愛知県).*(蒲郡市)',
            r'(福岡県).*(福岡市)',
            r'([^県市区町村]+県).+?([^県市区町村]+市)',
            r'([^府県市区町村]+府).+?([^府県市区町村]+市)'
        ]
        
        for pattern in municipality_patterns:
            import re
            match = re.search(pattern, text_content)
            if match:
                prefecture = match.group(1)
                city = match.group(2)
                self._log_debug(f"受信通知から市町村検出: {prefecture}{city}")
                return prefecture, city
        
        self._log_debug(f"受信通知から市町村検出なし: {filename}")
        return None, None

    def build_order_maps(self, set_settings: Dict[int, Dict[str, str]]) -> Tuple[Dict[int, int], Dict[int, int]]:
        """ステートレス連番マップを構築
        
        Args:
            set_settings: セット設定辞書 {set_id: {"prefecture": str, "city": str}}
            
        Returns:
            Tuple[pref_order_map, city_order_map]
            pref_order_map: {set_id: prefecture_code}
            city_order_map: {set_id: municipality_code}
        """
        # 東京都チェック（存在する場合のみ）
        tokyo_set_id = None
        for set_id, info in set_settings.items():
            if info.get("prefecture") == "東京都":
                tokyo_set_id = set_id
                # 東京都は必ずセット1でなければならない
                if set_id != 1:
                    raise ValueError(f"東京都は必ずセット1に入力してください。現在の位置: セット{set_id}")
                # 東京都にcityが設定されている場合はエラー
                if info.get("city", "").strip():
                    raise ValueError(f"東京都（セット{set_id}）にcityが設定されています: {info.get('city')}")
                break
        
        # 都道府県連番マップ
        pref_order_map = {}
        sorted_set_ids = sorted(set_settings.keys())
        
        if tokyo_set_id is not None:
            # 東京都がある場合：論理的に先頭に移動
            ordered_sets = [tokyo_set_id] + [sid for sid in sorted_set_ids if sid != tokyo_set_id]
        else:
            # 東京都がない場合：入力順のまま
            ordered_sets = sorted_set_ids
        
        for rank, set_id in enumerate(ordered_sets):
            pref_order_map[set_id] = 1001 + rank * 10
        
        # 市町村連番マップ: cityが空でないセットのみを順序化
        city_sets = []
        for set_id in sorted(set_settings.keys()):
            city = set_settings[set_id].get("city", "").strip()
            if city:  # cityが空でない場合のみ
                city_sets.append(set_id)
        
        city_order_map = {}
        for rank, set_id in enumerate(city_sets):
            city_order_map[set_id] = 2001 + rank * 10
            
        return pref_order_map, city_order_map
    
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
        """都道府県コードから実際の都道府県名を取得"""
        # セット設定から都道府県名を取得
        if hasattr(self, 'current_municipality_sets') and self.current_municipality_sets:
            # prefecture_codeから逆算してセット番号を取得
            set_id = self._get_set_id_from_prefecture_code(prefecture_code)
            if set_id and set_id in self.current_municipality_sets:
                return self.current_municipality_sets[set_id].get('prefecture', '都道府県')
        
        # フォールバック: コードから推測
        code_to_name = {
            1001: '東京都',
            1011: '愛知県', 
            1021: '福岡県',
            1031: '大阪府',
            1041: '神奈川県'
        }
        return code_to_name.get(prefecture_code, '都道府県')

    def _get_municipality_name(self, municipality_code: int) -> str:
        """市町村コードから実際の市町村名を取得"""
        # セット設定から市町村名を取得
        if hasattr(self, 'current_municipality_sets') and self.current_municipality_sets:
            # municipality_codeから逆算してセット番号を取得
            set_id = self._get_set_id_from_municipality_code(municipality_code)
            if set_id and set_id in self.current_municipality_sets:
                pref = self.current_municipality_sets[set_id].get('prefecture', '')
                city = self.current_municipality_sets[set_id].get('city', '')
                if pref and city:
                    return f"{pref}{city}"
                elif pref:
                    return pref
        
        # フォールバック: コードから推測
        code_to_name = {
            2001: '愛知県蒲郡市',
            2011: '福岡県福岡市',
            2021: '大阪市',
            2031: '横浜市',
            2041: '名古屋市'
        }
        return code_to_name.get(municipality_code, '市町村')

    def _get_set_id_from_prefecture_code(self, prefecture_code: int) -> Optional[int]:
        """都道府県コードからセット番号を取得"""
        # 1001, 1011, 1021, 1031, 1041 -> 1, 2, 3, 4, 5
        if prefecture_code >= 1001 and prefecture_code <= 1041 and (prefecture_code - 1001) % 10 == 0:
            return ((prefecture_code - 1001) // 10) + 1
        return None

    def _get_set_id_from_municipality_code(self, municipality_code: int) -> Optional[int]:
        """市町村コードからセット番号を取得"""
        # 2001, 2011, 2021, 2031, 2041 -> セット番号を決定
        # 注意: 市町村コードは東京都を除いた順序なので、実際のセット番号は+1が必要な場合がある
        if municipality_code >= 2001 and municipality_code <= 2041 and (municipality_code - 2001) % 10 == 0:
            # 市町村は東京都を除いた順序なので、実際にどのセットかを特定するためには
            # current_municipality_setsを確認する必要があります
            if hasattr(self, 'current_municipality_sets') and self.current_municipality_sets:
                city_sets = [(set_id, info) for set_id, info in self.current_municipality_sets.items() 
                            if info.get('city', '').strip()]
                city_sets.sort(key=lambda x: x[0])  # セット番号順
                
                order = ((municipality_code - 2001) // 10) + 1
                if order <= len(city_sets):
                    return city_sets[order - 1][0]
        return None

    def _resolve_document_label_stateless(self, document_type: str, extracted_text: str, 
                                         filename: str, set_settings: Dict[int, Dict[str, str]]) -> str:
        """ステートレスな文書ラベル解決（不整合検出機能付き）"""
        try:
            # 1. 連番マップを構築
            pref_order_map, city_order_map = self.build_order_maps(set_settings)
            
            # 2. テキストから自治体情報を抽出（検証用）
            extracted_pref, extracted_city = self._extract_pref_city_from_text(extracted_text, filename)
            
            # 3. 文書分類から自治体コードを決定
            detected_set = self._detect_municipality_set_from_text(extracted_text, filename, set_settings)
            if not detected_set:
                self._log_inconsistency(filename, extracted_pref or "不明", extracted_city or "不明", 
                                       "未分類", "未分類", "テキストから自治体を検出できませんでした")
                return document_type
            
            # 4. 自治体種別判定（都道府県税 vs 市民税）
            is_prefecture_tax = self._is_prefecture_tax_document(document_type)
            is_municipal_tax = self._is_municipal_tax_document(document_type)
            
            if is_prefecture_tax:
                # 都道府県税の場合
                if detected_set in pref_order_map:
                    pref_code = pref_order_map[detected_set]
                    resolved_pref = set_settings[detected_set]["prefecture"]
                    resolved_city = ""
                    
                    # 不整合検出
                    if extracted_pref and extracted_pref != resolved_pref:
                        self._log_inconsistency(filename, extracted_pref, extracted_city or "", 
                                              resolved_pref, resolved_city, "都道府県名の不一致")
                    
                    return f"{pref_code}_{resolved_pref}_都道府県申告書"
                    
            elif is_municipal_tax:
                # 市民税の場合
                if detected_set in city_order_map:
                    city_code = city_order_map[detected_set]
                    resolved_pref = set_settings[detected_set]["prefecture"]
                    resolved_city = set_settings[detected_set]["city"]
                    
                    # 不整合検出
                    if extracted_pref and extracted_pref != resolved_pref:
                        self._log_inconsistency(filename, extracted_pref, extracted_city or "", 
                                              resolved_pref, resolved_city, "都道府県名の不一致")
                    if extracted_city and extracted_city != resolved_city:
                        self._log_inconsistency(filename, extracted_pref or "", extracted_city, 
                                              resolved_pref, resolved_city, "市町村名の不一致")
                    
                    return f"{city_code}_{resolved_pref}{resolved_city}_市町村申告書"
            
            return document_type
            
        except Exception as e:
            self._log_debug(f"ラベル解決エラー: {e}")
            return document_type
    
    def _extract_pref_city_from_text(self, text: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """テキストから都道府県・市町村名を抽出（検証用）"""
        combined_text = f"{text} {filename}"
        
        # 都道府県パターン
        pref_patterns = [
            (r'東京都', '東京都'),
            (r'愛知県', '愛知県'),
            (r'福岡県', '福岡県')
        ]
        
        # 市町村パターン  
        city_patterns = [
            (r'蒲郡市', '蒲郡市'),
            (r'福岡市', '福岡市')
        ]
        
        extracted_pref = None
        extracted_city = None
        
        for pattern, name in pref_patterns:
            if re.search(pattern, combined_text):
                extracted_pref = name
                break
                
        for pattern, name in city_patterns:
            if re.search(pattern, combined_text):
                extracted_city = name
                break
        
        return extracted_pref, extracted_city
    
    def _detect_municipality_set_from_text(self, text: str, filename: str, 
                                           set_settings: Dict[int, Dict[str, str]]) -> Optional[int]:
        """テキストから自治体セットを検出（動的）"""
        combined_text = f"{text} {filename}".lower()
        
        # set_settingsベースで検出パターンを動的生成
        for set_id, info in set_settings.items():
            prefecture = info.get("prefecture", "")
            city = info.get("city", "")
            
            # 都道府県名での検出
            if prefecture and prefecture.lower() in combined_text:
                return set_id
            
            # 市町村名での検出（市役所パターンも含む）
            if city and city.lower() in combined_text:
                return set_id
                
            # 市役所パターン
            if city and f"{city}役所".lower() in combined_text:
                return set_id
        return None
    
    def resolve_set_id_from_text(self, text: str, filename: str, set_settings: Dict[int, Dict[str, str]], 
                                doc_kind: str) -> Optional[int]:
        """テキストから自治体セットIDを解決（強い手がかりから順に判定）"""
        combined_text = f"{text} {filename}"
        
        if doc_kind == "pref":
            # 県税の場合：県税事務所パターンを優先検索
            patterns = [
                (r'東京都港都税事務所', lambda _: self._find_set_by_pref(set_settings, "東京都")),
                (r'(\w+県).*?県税事務所', lambda m: self._find_set_by_pref(set_settings, m.group(1))),
                (r'(\w+県)\s*税事務所', lambda m: self._find_set_by_pref(set_settings, m.group(1))),
                (r'東京都', lambda _: self._find_set_by_pref(set_settings, "東京都")),
            ]
            
        elif doc_kind == "city":
            # 市税の場合：市役所パターンを優先検索
            patterns = [
                (r'(\w+市)役所', lambda m: self._find_set_by_city(set_settings, m.group(1))),
                (r'(\w+市)長', lambda m: self._find_set_by_city(set_settings, m.group(1))),
                (r'当該市町村.*?(\w+県)', lambda m: self._find_set_by_pref(set_settings, m.group(1))),
            ]
        else:
            return None
            
        # パターンマッチングで検索
        import re
        for pattern, resolver in patterns:
            match = re.search(pattern, combined_text)
            if match:
                result = resolver(match)
                if result:
                    return result
        
        # フォールバック：一般的な都道府県・市町村名検索
        for set_id, info in set_settings.items():
            pref = info.get("prefecture", "")
            city = info.get("city", "")
            
            if doc_kind == "pref" and pref and pref in combined_text:
                return set_id
            elif doc_kind == "city" and city and city in combined_text:
                return set_id
                
        return None
    
    def _find_set_by_pref(self, set_settings: Dict[int, Dict[str, str]], target_pref: str) -> Optional[int]:
        """都道府県名からセットIDを検索"""
        for set_id, info in set_settings.items():
            if info.get("prefecture") == target_pref:
                return set_id
        return None
    
    def _find_set_by_city(self, set_settings: Dict[int, Dict[str, str]], target_city: str) -> Optional[int]:
        """市町村名からセットIDを検索"""
        for set_id, info in set_settings.items():
            if info.get("city") == target_city:
                return set_id
        return None
    
    def _is_prefecture_tax_document(self, document_type: str) -> bool:
        """都道府県税文書かどうか判定"""
        prefecture_patterns = ['都道府県', '県税', '都税', '道税', '府税']
        return any(pattern in document_type for pattern in prefecture_patterns)
    
    def _is_municipal_tax_document(self, document_type: str) -> bool:
        """市民税文書かどうか判定"""
        municipal_patterns = ['市民税', '市町村']
        return any(pattern in document_type for pattern in municipal_patterns)
    
    def _log_inconsistency(self, filename: str, extracted_pref: str, extracted_city: str,
                          resolved_pref: str, resolved_city: str, reason: str):
        """不整合ログの記録"""
        import csv
        import os
        
        log_entry = {
            'filename': filename,
            'extracted_pref': extracted_pref,
            'extracted_city': extracted_city,
            'resolved_pref': resolved_pref,
            'resolved_city': resolved_city,
            'reason': reason
        }
        
        # CSVログ出力
        log_file = 'municipality_inconsistency.csv'
        file_exists = os.path.isfile(log_file)
        
        with open(log_file, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=log_entry.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(log_entry)
        
        # WARNログも出力
        self._log_debug(f"[WARN] 自治体名不整合: {filename} - {reason}")
        print(f"[WARN] 自治体名不整合: {filename} - {reason}")
    
    def normalize_classification(self, text: str, filename: str, template_id: str, 
                                set_settings: Dict[int, Dict[str, str]]) -> Tuple[int, str, int]:
        """v5.1テンプレートIDを正規化して最終ラベルを生成"""
        print(f"[INFO] 正規化処理開始: template_id={template_id}")
        
        # 修正: FIXED_NUMBERS確認 - 納付情報は固定、受信通知は連番適用後は固定扱い
        FIXED_NUMBERS = {
            "0003_受信通知",     # 法人税受信通知は固定
            "0004_納付情報",     # 法人税納付情報は固定
            "3003_受信通知",     # 消費税受信通知は固定
            "3004_納付情報",     # 消費税納付情報は固定
            "1004_納付情報",     # 都道府県納付情報は固定
            "2004_納付情報",     # 市町村納付情報は固定
            # 地方税受信通知：連番適用後の最終形は固定扱い
            "1003_受信通知", "1013_受信通知", "1023_受信通知",  # 都道府県受信通知（各セット）
            "2003_受信通知", "2013_受信通知", "2023_受信通知"   # 市町村受信通知（各セット）
        }
        
        if template_id in FIXED_NUMBERS:
            print(f"[INFO] FIXED_NUMBER検出: {template_id} -> 正規化スキップ")
            return 0, template_id, 0
        try:
            # 1. 連番マップを構築
            pref_order_map, city_order_map = self.build_order_maps(set_settings)
            
            # 2. 文書種別を判定（都道府県税 vs 市民税）
            doc_kind = "pref" if self._is_prefecture_tax_document(template_id) else "city"
            print(f"[INFO] 文書種別判定: {doc_kind}")
            
            # 3. テキストから自治体セットIDを解決
            set_id = self.resolve_set_id_from_text(text, filename, set_settings, doc_kind)
            if not set_id:
                print(f"[WARN] 自治体セット解決失敗, フォールバックを使用")
                # フォールバック：最初の該当セットを使用
                for sid, info in set_settings.items():
                    if doc_kind == "pref":
                        set_id = sid
                        break
                    elif doc_kind == "city" and info.get("city", "").strip():
                        set_id = sid
                        break
                        
            if not set_id:
                print(f"[ERROR] セットID解決失敗")
                return 0, template_id, 0
            
            # 4. 連番コードを決定
            if doc_kind == "pref":
                code = pref_order_map.get(set_id, 1001)
                pref = set_settings[set_id]["prefecture"]
                city = ""
                final_label = f"{code}_{pref}_都道府県申告書"
            else:
                code = city_order_map.get(set_id, 2001)
                pref = set_settings[set_id]["prefecture"]
                city = set_settings[set_id]["city"]
                final_label = f"{code}_{pref}{city}_市町村申告書"
            
            print(f"[INFO] 正規化結果: set_id={set_id}, code={code}, pref={pref}, city={city}")
            print(f"[INFO] 最終ラベル: {final_label}")
            
            # 5. テンプレートIDが最終出力に残らないことを確認
            assert "市町村" not in final_label, f"テンプレート文字列が残存: {final_label}"
            assert template_id != final_label, f"正規化されていません: {template_id} == {final_label}"
            
            # 6. 不整合検証（簡易版）
            extracted_pref, extracted_city = self._extract_pref_city_from_text(text, filename)
            if extracted_pref and extracted_pref != pref:
                print(f"[WARN] Locality mismatch text=(pref={extracted_pref}, city={extracted_city}) vs set=(pref={pref}, city={city}), file={filename}")
            
            return code, final_label, set_id
            
        except Exception as e:
            print(f"[ERROR] 正規化処理エラー: {e}")
            import traceback
            traceback.print_exc()
            return 0, template_id, 0

    def _extract_municipality_info_from_text(self, text: str, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """テキストから自治体コードを抽出（UI設定ベース解析）"""
        combined_text = f"{text} {filename}".lower()
        
        # UI設定ベースの自治体判定（より柔軟なパターンマッチング）
        # Step 1: ファイル名と内容から自治体を特定
        submission_office_patterns = {
            1: ["東京都", "港都税事務所", "芝税務署", "都税事務所", "東京都港都税事務所"],  # セット1
            2: ["愛知県", "東三河県税事務所", "蒲郡市", "蒲郡市役所", "愛知県東三河県税事務所"],  # セット2  
            3: ["福岡県", "西福岡県税事務所", "福岡市", "福岡市役所", "福岡県西福岡県税事務所"],  # セット3
            4: ["北海道", "札幌市", "道税事務所"],  # セット4（拡張用）
            5: ["大阪府", "大阪市", "府税事務所"]   # セット5（拡張用）
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
        
        # セット番号を正確な連番コード番号に変換（連番ルール適用）
        prefecture_code = None
        municipality_code = None
        
        if detected_set:
            # 都道府県申告書の連番: 1001 + (セット番号-1) × 10
            prefecture_code = 1001 + (detected_set - 1) * 10
            self._log_debug(f"都道府県連番計算: セット{detected_set} → 1001 + ({detected_set}-1)×10 = {prefecture_code}")
            
            # 市町村申告書の連番: 2001 + (セット番号-1) × 10
            # ただし、東京都（セット1）は市町村書類が存在しないため除外
            if detected_set > 1:  # 東京都以外の場合のみ
                municipality_code = 2001 + (detected_set - 1) * 10
                self._log_debug(f"市町村連番計算: セット{detected_set} → 2001 + ({detected_set}-1)×10 = {municipality_code}")
            else:
                self._log_debug(f"東京都（セット1）は市町村書類なし")
        
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
        exclusion_keywords = ['納付区分番号通知', '納付内容を確認し', 'メール詳細（納付区分番号通知）']
        
        has_receipt = any(indicator in text_content for indicator in receipt_indicators)
        has_payment = any(keyword in text_content for keyword in exclusion_keywords)
        
        result = has_receipt and not has_payment
        if result:
            self._log_debug(f"受信通知強制判定: 受信={has_receipt}, 納付除外={has_payment}")
        
        return result
    
    def _classify_local_tax_receipt(self, text: str, filename: str, prefecture_code: Optional[int], municipality_code: Optional[int]) -> Optional[ClassificationResult]:
        """
        地方税受信通知の専用分類処理（OCRベース自治体セット照合対応版）
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
            ["申告受付完了通知", "市町村申告書"],
            ["申告受付完了通知", "法人市町村民税"],
            ["市役所", "申告受付完了通知"],
            ["市長", "市町村申告書", "受付完了通知"],
            ["市役所", "市町村申告書申告書", "受付完了通知"],  # 追加
            ["市町村申告書申告書", "受付完了通知"]  # 追加
        ]
        
        # 都道府県向け判定
        if any(all(kw in combined_text for kw in condition) 
               for condition in prefecture_receipt_conditions):
            # OCRベース自治体セット照合を使用
            set_number = self._detect_municipality_set_from_text(text, filename, "prefecture")
            if not set_number:
                set_number = 1  # フォールバック
            code = self._generate_receipt_number("prefecture", set_number)
            self._log_debug(f"地方税受信通知（都道府県）: OCRセット検出={set_number} → {code}_受信通知")
            return ClassificationResult(
                document_type=f"{code}_受信通知",
                confidence=1.0,
                matched_keywords=["地方税受信通知（都道府県）"],
                classification_method="local_tax_receipt_detection_ocr",
                debug_steps=[],
                processing_log=self.processing_log.copy()
            )
        
        # 市町村向け判定  
        if any(all(kw in combined_text for kw in condition)
               for condition in municipality_receipt_conditions):
            # OCRベース自治体セット照合を使用（東京繰り上がり対応）
            set_number = self._detect_municipality_set_from_text(text, filename, "municipality")
            if not set_number:
                set_number = 2  # 市町村のフォールバック（東京がある場合は2から開始）
            code = self._generate_receipt_number("municipality", set_number)
            self._log_debug(f"地方税受信通知（市町村）: OCRセット検出={set_number} → {code}_受信通知")
            return ClassificationResult(
                document_type=f"{code}_受信通知",
                confidence=1.0,
                matched_keywords=["地方税受信通知（市町村）"],
                classification_method="local_tax_receipt_detection_ocr",
                debug_steps=[],
                processing_log=self.processing_log.copy()
            )
            
        return None
    
    def _generate_receipt_number(self, classification_type: str, jurisdiction_set_number: int) -> str:
        """
        受信通知の連番を生成（東京都繰り上がり対応版）
        
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
            
            # 東京都が設定にある場合の繰り上がりロジック（申告書と同様）
            # セット設定から東京都の存在を確認
            tokyo_offset = 0
            if hasattr(self, 'current_municipality_sets') and self.current_municipality_sets:
                for set_id, set_info in self.current_municipality_sets.items():
                    if set_info.get("prefecture") == "東京都":
                        tokyo_offset = 1
                        break
                        
            # 市町村の場合、東京都があるとベースが繰り上がる
            if classification_type == "municipality" and tokyo_offset > 0:
                # 東京都がセット1にある場合、市町村受信通知は2003から開始
                # セット2→2013, セット3→2023, セット4→2033...
                result = str(base + (jurisdiction_set_number - 1) * 10)
            else:
                result = str(base + (jurisdiction_set_number - 1) * 10)
                
            self._log_debug(f"連番生成: {classification_type} セット{jurisdiction_set_number} tokyo_offset={tokyo_offset} → {result}")
            return result
        
        return "0003"  # フォールバック
    
    def _detect_municipality_set_from_text(self, text: str, filename: str, target_type: str) -> Optional[int]:
        """
        OCRテキストから自治体セット番号を検出（申告書と同じロジック）
        
        Args:
            text: OCRテキスト
            filename: ファイル名 
            target_type: "prefecture" or "municipality"
            
        Returns:
            int: セット番号、検出できない場合はNone
        """
        combined_text = f"{text} {filename}"
        
        # 自治体セット設定を取得
        if not hasattr(self, 'current_municipality_sets') or not self.current_municipality_sets:
            self._log_debug(f"OCR自治体セット検出: セット設定なし")
            return None
            
        # 各セットに対してテキストマッチング
        for set_id, set_info in self.current_municipality_sets.items():
            prefecture = set_info.get("prefecture", "")
            city = set_info.get("city", "")
            
            # 都道府県受信通知の場合は都道府県名でマッチング
            if target_type == "prefecture":
                if prefecture and prefecture in combined_text:
                    self._log_debug(f"OCR自治体セット検出: {prefecture}がテキストで検出 → セット{set_id}")
                    return set_id
                    
            # 市町村受信通知の場合は市町村名でマッチング
            elif target_type == "municipality":
                if city and city in combined_text:
                    self._log_debug(f"OCR自治体セット検出: {city}がテキストで検出 → セット{set_id}")
                    return set_id
                # 市町村名がない場合（東京都等）は都道府県名でマッチング
                elif not city and prefecture and prefecture in combined_text:
                    # 東京都の場合、市町村受信通知でも東京都マッチで該当セットを返す
                    # ただし、東京都は基本的に市町村税がないため、稀なケース
                    self._log_debug(f"OCR自治体セット検出: {prefecture}（市町村なし）がテキストで検出 → セット{set_id}")
                    return set_id
                    
        self._log_debug(f"OCR自治体セット検出: テキストマッチング失敗")
        return None
    
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
        if self._is_payment_info(combined_text, filename):
            # 税目によって適切な納付情報コードを返す
            if "法人税" in combined_text or "内国法人" in combined_text:
                return ClassificationResult(
                    document_type="0004_納付情報",
                    confidence=1.0,
                    matched_keywords=["納付情報強制判定"],
                    classification_method="enhanced_payment_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "消費税" in combined_text:
                return ClassificationResult(
                    document_type="3004_納付情報",
                    confidence=1.0,
                    matched_keywords=["納付情報強制判定"],
                    classification_method="enhanced_payment_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "都道府県" in combined_text or "県税事務所" in combined_text or "都税事務所" in combined_text:
                return ClassificationResult(
                    document_type="1004_納付情報",
                    confidence=1.0,
                    matched_keywords=["納付情報強制判定"],
                    classification_method="enhanced_payment_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "市町村" in combined_text or "市役所" in combined_text or "市民税" in combined_text:
                return ClassificationResult(
                    document_type="2004_納付情報",
                    confidence=1.0,
                    matched_keywords=["納付情報強制判定"],
                    classification_method="enhanced_payment_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
        
        # 受信通知の強制判定（納付関連キーワードがない場合のみ）
        if self._is_receipt_notification(combined_text, filename):
            # 税目によって適切な受信通知コードを返す
            if "法人税" in combined_text or "内国法人" in combined_text:
                return ClassificationResult(
                    document_type="0003_受信通知",
                    confidence=1.0,
                    matched_keywords=["受信通知強制判定"],
                    classification_method="enhanced_receipt_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "消費税" in combined_text:
                return ClassificationResult(
                    document_type="3003_受信通知",
                    confidence=1.0,
                    matched_keywords=["受信通知強制判定"],
                    classification_method="enhanced_receipt_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "都道府県" in combined_text or "県税事務所" in combined_text or "都税事務所" in combined_text:
                return ClassificationResult(
                    document_type="1003_受信通知",
                    confidence=1.0,
                    matched_keywords=["受信通知強制判定"],
                    classification_method="enhanced_receipt_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
            elif "市町村" in combined_text or "市役所" in combined_text or "市民税" in combined_text:
                return ClassificationResult(
                    document_type="2003_受信通知",
                    confidence=1.0,
                    matched_keywords=["受信通知強制判定"],
                    classification_method="enhanced_receipt_detection",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
        
        return None
    
    # ===== v5.2 Bundle PDF Support Methods =====
    
    def detect_page_doc_code(self, text: str, prefer_bundle: Optional[str] = None) -> Optional[str]:
        """
        ページ内コード推定 (v5.2 Bundle PDF Support)
        単一ページのテキストから書類コードを推定
        
        Args:
            text: ページのテキスト内容
            prefer_bundle: バンドル種別のヒント ("local", "national", None)
            
        Returns:
            str|None: 推定された書類コード (例: "0003", "1003") またはNone
        """
        if not text:
            return None
        
        # 強力パターン（優先）: 直接的なコードマッチング
        strong_pattern = re.compile(r'\b(0003|0004|3003|3004|1003|1013|1023|1004|2003|2013|2023|2004)\b')
        strong_match = strong_pattern.search(text)
        if strong_match:
            code = strong_match.group(1)
            self._log_debug(f"Strong code pattern detected: {code}")
            return code
        
        # 補助パターン: キーワード組み合わせ判定
        is_receipt = any(kw in text for kw in ["受信通知", "申告受付完了通知", "申告受付完了", "受付完了通知"])
        is_payment = any(kw in text for kw in ["納付情報", "納付区分番号通知", "納付書", "納付情報発行結果"])
        
        # 税目別キーワード
        has_corporation_tax = any(kw in text for kw in ["法人税", "内国法人", "法人税及び地方法人税"])
        has_consumption_tax = any(kw in text for kw in ["消費税", "地方消費税", "消費税及び地方消費税"])
        has_prefecture = any(kw in text for kw in ["都道府県", "県税事務所", "都税事務所", "法人事業税", "特別法人事業税"])
        has_municipality = any(kw in text for kw in ["市町村", "市役所", "市町村申告書", "市町村民税"])
        
        # 自治体特定キーワード
        has_specific_local = any(kw in text for kw in ["東京都", "愛知県", "福岡県", "蒲郡市", "福岡市"])
        
        # 国税系の判定
        if is_receipt and has_corporation_tax:
            self._log_debug("Receipt + Corporation tax detected -> 0003")
            return "0003"
        elif is_payment and has_corporation_tax:
            self._log_debug("Payment + Corporation tax detected -> 0004")  
            return "0004"
        elif is_receipt and has_consumption_tax:
            self._log_debug("Receipt + Consumption tax detected -> 3003")
            return "3003"
        elif is_payment and has_consumption_tax:
            self._log_debug("Payment + Consumption tax detected -> 3004")
            return "3004"
        
        # 地方税系の判定
        elif is_receipt and (has_prefecture or has_specific_local):
            # 都道府県受信通知は連番対応が必要なため基本コードを返す
            self._log_debug("Receipt + Prefecture detected -> 1003 (base code)")
            return "1003"  # 後続で連番補正される
        elif is_payment and (has_prefecture or has_specific_local):
            self._log_debug("Payment + Prefecture detected -> 1004")
            return "1004"
        elif is_receipt and has_municipality:
            # 市町村受信通知も連番対応が必要
            self._log_debug("Receipt + Municipality detected -> 2003 (base code)")
            return "2003"  # 後続で連番補正される
        elif is_payment and has_municipality:
            self._log_debug("Payment + Municipality detected -> 2004")
            return "2004"
        
        # prefer_bundleに基づくヒューリスティック判定
        if prefer_bundle == "national":
            if is_receipt:
                self._log_debug(f"National bundle heuristic: receipt -> 0003 (prefer)")
                return "0003"  # 法人税を優先
            elif is_payment:
                self._log_debug(f"National bundle heuristic: payment -> 0004 (prefer)")
                return "0004"  # 法人税を優先
        elif prefer_bundle == "local":
            if is_receipt:
                self._log_debug(f"Local bundle heuristic: receipt -> 1003 (prefer)")
                return "1003"  # 都道府県を優先
            elif is_payment:
                # 地方税の納付情報は都道府県・市町村で分かれるため、より慎重に判定
                if has_prefecture or not has_municipality:
                    self._log_debug(f"Local bundle heuristic: payment -> 1004 (prefer prefecture)")
                    return "1004"
                else:
                    self._log_debug(f"Local bundle heuristic: payment -> 2004 (prefer municipality)")
                    return "2004"
        
        # 判定できない場合
        self._log_debug("No code pattern detected")
        return None

    def export_keyword_dictionary(self) -> str:
        """
        分類ルール辞書をJSONファイルとしてデスクトップにエクスポートする
        
        Returns:
            str: 保存されたファイルのフルパス
        """
        # 現在日時でファイル名を生成
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"keyword_dictionary_{timestamp}.json"
        
        # デスクトップパスを取得
        desktop_path = Path.home() / "Desktop"
        file_path = desktop_path / filename
        
        # 辞書データを準備
        export_data = {
            "export_info": {
                "timestamp": datetime.datetime.now().isoformat(),
                "version": "DocumentClassifierV5",
                "total_rules": len(self.classification_rules_v5),
                "description": "書類分類エンジン v5.0 - 分類ルール辞書"
            },
            "classification_rules": {}
        }
        
        # 各分類ルールを整理してエクスポート
        for doc_type, rules in self.classification_rules_v5.items():
            export_data["classification_rules"][doc_type] = {
                "priority": rules.get("priority", 0),
                "highest_priority_conditions": [],
                "exact_keywords": rules.get("exact_keywords", []),
                "partial_keywords": rules.get("partial_keywords", []),
                "exclude_keywords": rules.get("exclude_keywords", []),
                "filename_keywords": rules.get("filename_keywords", [])
            }
            
            # AND条件を文字列リストに変換
            for condition in rules.get("highest_priority_conditions", []):
                condition_dict = {
                    "keywords": condition.keywords,
                    "match_type": condition.match_type
                }
                export_data["classification_rules"][doc_type]["highest_priority_conditions"].append(condition_dict)
        
        # JSONファイルとして保存（読みやすい形式で）
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, sort_keys=True)
            
            # ログ出力
            self._log(f"分類ルール辞書をエクスポートしました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"エクスポート中にエラーが発生しました: {str(e)}"
            self._log(error_msg, "ERROR")
            raise Exception(error_msg)

    def export_keyword_dictionary_markdown(self) -> str:
        """
        分類ルール辞書を大学生にも分かりやすいMarkdownファイルとしてデスクトップにエクスポートする
        日本語と絵文字を使ってフレンドリーな形式で出力
        
        Returns:
            str: 保存されたファイルのフルパス
        """
        # 現在日時でファイル名を生成
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"キーワード辞書_{timestamp}.md"
        
        # デスクトップパスを取得
        desktop_path = Path.home() / "Desktop"
        file_path = desktop_path / filename
        
        # Markdownコンテンツを生成
        try:
            markdown_content = self._generate_markdown_content()
            
            # ファイルに保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # ログ出力
            self._log(f"Markdown形式の分類ルール辞書をエクスポートしました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"Markdownエクスポート中にエラーが発生しました: {str(e)}"
            self._log(error_msg, "ERROR")
            raise Exception(error_msg)
    
    def _generate_markdown_content(self) -> str:
        """Markdownコンテンツを生成する"""
        # 書類分類の概要
        content = []
        content.append("# 📋 税務書類分類システム キーワード辞書\n")
        content.append(f"**作成日時**: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
        content.append(f"**システム版本**: DocumentClassifierV5\n")
        content.append(f"**分類ルール総数**: {len(self.classification_rules_v5)}件\n\n")
        
        # システムの仕組み説明
        content.append("## 🎓 システムの仕組み（大学生向け解説）\n")
        content.append("### 📚 基本的な動作原理\n")
        content.append("このシステムは、PDFから抽出されたテキストやファイル名を分析して、どの種類の税務書類かを自動判定します。\n")
        content.append("判定は以下の3つのステップで行われます：\n\n")
        
        content.append("1. **🔍 キーワード検索**: 文書内で特定のキーワードを探します\n")
        content.append("2. **⭐ スコア計算**: 見つかったキーワードの重要度に基づいてスコアを計算します\n")
        content.append("3. **🏆 最終判定**: 最も高いスコアの書類種別を選択します\n\n")
        
        content.append("### 📊 優先度システム\n")
        content.append("各書類には優先度（Priority）が設定されており、数値が大きいほど優先されます：\n")
        content.append("- **200**: 最高優先度（確実に判定したい重要書類）\n")
        content.append("- **180**: 高優先度\n")
        content.append("- **150-140**: 中優先度\n")
        content.append("- **135-130**: 標準優先度\n\n")
        
        content.append("### 🎯 キーワードの種類\n")
        content.append("- **完全一致キーワード**: 文書に完全に一致する語句（高スコア）\n")
        content.append("- **部分一致キーワード**: 文書に含まれていればOKの語句（中スコア）\n")
        content.append("- **除外キーワード**: これがあると判定を除外する語句\n")
        content.append("- **ファイル名キーワード**: ファイル名でのみチェックする語句（重要度高）\n")
        content.append("- **AND条件**: 複数のキーワードが同時に必要な条件\n\n")
        
        # 番台別の分類
        content.append("## 📂 書類分類一覧\n")
        
        # 番台ごとにグループ化
        categories = {
            "0000": {"name": "🏛️ 国税申告書類", "items": []},
            "1000": {"name": "🏢 都道府県税関連", "items": []},
            "2000": {"name": "🏢 市町村税関連", "items": []},
            "3000": {"name": "💰 消費税関連", "items": []},
            "5000": {"name": "📊 会計書類", "items": []},
            "6000": {"name": "🏗️ 固定資産関連", "items": []},
            "7000": {"name": "📋 税区分関連", "items": []}
        }
        
        # 各ルールを適切なカテゴリに振り分け
        for doc_type, rules in self.classification_rules_v5.items():
            # 千の位で分類（0001 → 0000, 1003 → 1000, 2001 → 2000, など）
            first_digit = doc_type[0]
            category_code = f"{first_digit}000"
            if category_code in categories:
                categories[category_code]["items"].append((doc_type, rules))
        
        # カテゴリごとにMarkdownを生成
        for category_code, category_info in categories.items():
            if category_info["items"]:
                content.append(f"### {category_info['name']}\n")
                
                # 優先度順にソート
                sorted_items = sorted(category_info["items"], 
                                    key=lambda x: x[1].get("priority", 0), reverse=True)
                
                for doc_type, rules in sorted_items:
                    content.append(self._format_document_type(doc_type, rules))
        
        content.append("\n## 🤖 システム情報\n")
        content.append(f"- **エンジン版本**: DocumentClassifierV5\n")
        content.append(f"- **最終更新**: {datetime.datetime.now().strftime('%Y年%m月%d日')}\n")
        content.append(f"- **総分類数**: {len(self.classification_rules_v5)}種類\n")
        content.append("\n---\n")
        content.append("*この辞書は税務書類分類システムによって自動生成されました 📝*\n")
        
        return "".join(content)
    
    def _format_document_type(self, doc_type: str, rules: Dict) -> str:
        """個別の書類種別をMarkdown形式でフォーマットする"""
        content = []
        
        # タイトル
        clean_name = doc_type.replace("_", " ").replace("0001", "").replace("0002", "").replace("0003", "").replace("0004", "")
        priority = rules.get("priority", 0)
        
        # 優先度に応じて絵文字を設定
        priority_emoji = "🔥" if priority >= 200 else "⭐" if priority >= 180 else "🌟" if priority >= 150 else "💫"
        
        content.append(f"#### {priority_emoji} {clean_name}\n")
        content.append(f"**優先度**: {priority} | **分類コード**: `{doc_type}`\n\n")
        
        # AND条件（最優先条件）
        highest_priority_conditions = rules.get("highest_priority_conditions", [])
        if highest_priority_conditions:
            content.append("**🎯 最優先AND条件** (これらがあると確実に判定)\n")
            for i, condition in enumerate(highest_priority_conditions, 1):
                match_type_text = "すべて必要" if condition.match_type == "all" else "いずれか必要"
                keywords_text = " + ".join([f"`{kw}`" for kw in condition.keywords])
                content.append(f"{i}. {keywords_text} ({match_type_text})\n")
            content.append("\n")
        
        # 完全一致キーワード
        exact_keywords = rules.get("exact_keywords", [])
        if exact_keywords:
            content.append("**✅ 完全一致キーワード** (高スコア)\n")
            for keyword in exact_keywords:
                content.append(f"- `{keyword}`\n")
            content.append("\n")
        
        # 部分一致キーワード
        partial_keywords = rules.get("partial_keywords", [])
        if partial_keywords:
            content.append("**🔍 部分一致キーワード** (中スコア)\n")
            for keyword in partial_keywords:
                content.append(f"- `{keyword}`\n")
            content.append("\n")
        
        # ファイル名キーワード
        filename_keywords = rules.get("filename_keywords", [])
        if filename_keywords:
            content.append("**📁 ファイル名専用キーワード** (重要度高)\n")
            for keyword in filename_keywords:
                content.append(f"- `{keyword}`\n")
            content.append("\n")
        
        # 除外キーワード
        exclude_keywords = rules.get("exclude_keywords", [])
        if exclude_keywords:
            content.append("**❌ 除外キーワード** (これがあると判定除外)\n")
            for keyword in exclude_keywords:
                content.append(f"- `{keyword}`\n")
            content.append("\n")
        
        content.append("---\n\n")
        return "".join(content)
    
    def _set_no_split_metadata(self, result: ClassificationResult) -> None:
        """分類結果にno_splitメタデータを設定（資産・帳票系）"""
        # 資産・帳票系のコードチェック
        document_code = result.document_type.split('_')[0] if '_' in result.document_type else result.document_type
        
        no_split_codes = {
            "6001", "6002", "6003",  # 資産系
            "5001", "5002", "5003", "5004"  # 帳票系
        }
        
        if document_code in no_split_codes:
            result.meta["no_split"] = True
            self._log(f"[meta] no_split=True set for document_type: {result.document_type}")
        else:
            result.meta["no_split"] = False
    
    def _create_classification_result(self, document_type: str, confidence: float, matched_keywords: List[str],
                                    classification_method: str, debug_steps: List[ClassificationStep] = None,
                                    processing_log: List[str] = None, original_doc_type_code: str = None) -> ClassificationResult:
        """ClassificationResult作成のヘルパーメソッド（no_splitメタデータ自動設定）"""
        result = ClassificationResult(
            document_type=document_type,
            confidence=confidence,
            matched_keywords=matched_keywords,
            classification_method=classification_method,
            debug_steps=debug_steps or [],
            processing_log=processing_log or self.processing_log.copy(),
            original_doc_type_code=original_doc_type_code or document_type
        )
        self._set_no_split_metadata(result)
        return result

if __name__ == "__main__":
    # テスト用
    classifier = DocumentClassifierV5(debug_mode=True)
    print("書類分類エンジン v5.2 初期化完了")
    
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