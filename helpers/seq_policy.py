#!/usr/bin/env python3
"""
受信通知連番ポリシー v5.3.5-ui-robust

都道府県（1003系）・市町村（2003系）の受信通知における決定論的連番付与を実装。
UIセット順とOCR自治体の両方を踏まえた厳格な番号割当。

仕様:
- 都道府県: ベース1003 + (入力順序-1) × 10 → 1003/1013/1023/1033...
- 市町村:   ベース2003 + (入力順序-1) × 10 → 2003/2013/2023/2033...
- 東京都必須セット1制約（FATAL違反時）
- 東京都は市町村なし（2000番台スキップで市町村順序繰り上げ）
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 連番計算のベース番号
BASE_PREF = 1003  # 都道府県受信通知
BASE_CITY = 2003  # 市町村受信通知

class ReceiptSequencer:
    """
    受信通知に限定した決定論的連番計算クラス
    
    依存: JobContext（UIセット順と自治体情報）
    制約: 受信通知以外の分類・命名・YYMM等は一切変更しない
    """
    
    def __init__(self, job_context):
        """
        Args:
            job_context: JobContextインスタンス（UIセット順情報を保持）
        """
        self.ctx = job_context
        self._tokyo_first_checked = False
        self._assigned_codes = {}  # 冪等性のため既割当を記録
        
    def _ensure_tokyo_rule(self):
        """
        東京都の必須セット1制約を検証
        
        Raises:
            ValueError: 東京都がセット1以外にある場合のFATALエラー
        """
        if self._tokyo_first_checked:
            return
            
        tokyo_idx = self.ctx.get_set_index_for_pref("東京都")
        if tokyo_idx is not None and tokyo_idx != 1:
            error_msg = f"[FATAL][SEQ] Tokyo must be Set #1 (found at Set #{tokyo_idx})"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self._tokyo_first_checked = True
        logger.debug(f"[SEQ] Tokyo rule validation passed (set_index={tokyo_idx})")
    
    def assign_pref_seq(self, code: str, ocr_pref: str) -> str:
        """
        都道府県受信通知の連番付与
        
        Args:
            code: 予備コード（例: "1003_受信通知"）
            ocr_pref: OCRで検出された都道府県名
            
        Returns:
            str: 確定した4桁コード（例: "1013"）
            
        Raises:
            ValueError: OCR都道府県がUIセットに未登録の場合
        """
        self._ensure_tokyo_rule()
        
        # 既に同じ都道府県に割当済みの場合は再利用（冪等）
        cache_key = f"pref_{ocr_pref}"
        if cache_key in self._assigned_codes:
            cached_code = self._assigned_codes[cache_key]
            logger.debug(f"[SEQ][PREF] Cached result for {ocr_pref} -> {cached_code}")
            return cached_code
        
        # UIセット順から都道府県の入力順序を取得
        set_idx = self.ctx.get_set_index_for_pref(ocr_pref)
        if set_idx is None:
            error_msg = f"[SEQ][PREF] Unknown prefecture in UI sets: {ocr_pref}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 都道府県は入力順序をそのまま使用
        final_code = BASE_PREF + (set_idx - 1) * 10
        final_code_str = f"{final_code:04d}"
        
        # キャッシュに保存
        self._assigned_codes[cache_key] = final_code_str
        
        logger.debug(f"[SEQ][PREF] UI set={set_idx} pref={ocr_pref} -> {final_code_str}")
        return final_code_str
    
    def assign_city_seq(self, code: str, ocr_pref: str, ocr_city: str) -> str:
        """
        市町村受信通知の連番付与
        
        Args:
            code: 予備コード（例: "2003_受信通知"）
            ocr_pref: OCRで検出された都道府県名
            ocr_city: OCRで検出された市区町村名
            
        Returns:
            str: 確定した4桁コード（例: "2013"）
            
        Raises:
            ValueError: OCR市町村がUIセットに未登録の場合
        """
        self._ensure_tokyo_rule()
        
        # 既に同じ市町村に割当済みの場合は再利用（冪等）
        cache_key = f"city_{ocr_pref}_{ocr_city}"
        if cache_key in self._assigned_codes:
            cached_code = self._assigned_codes[cache_key]
            logger.debug(f"[SEQ][CITY] Cached result for {ocr_pref} {ocr_city} -> {cached_code}")
            return cached_code
        
        # UIセット順から市町村の入力順序を取得
        set_idx = self.ctx.get_set_index_for_city(ocr_pref, ocr_city)
        if set_idx is None:
            error_msg = f"[SEQ][CITY] Unknown city in UI sets: {ocr_pref} {ocr_city}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 東京都がセット1に存在する場合、市町村の順序を繰り上げ（東京都スキップ）
        tokyo_idx = self.ctx.get_set_index_for_pref("東京都")
        adjusted_idx = set_idx
        
        if tokyo_idx == 1 and set_idx > 1:
            adjusted_idx = set_idx - 1
            logger.debug(f"[SEQ][CITY] Tokyo-skip applied: set {set_idx} -> adjusted {adjusted_idx}")
        
        final_code = BASE_CITY + (adjusted_idx - 1) * 10
        final_code_str = f"{final_code:04d}"
        
        # キャッシュに保存
        self._assigned_codes[cache_key] = final_code_str
        
        logger.debug(f"[SEQ][CITY] UI set={set_idx} city={ocr_pref} {ocr_city} (tokyo-skip applied) -> {final_code_str}")
        return final_code_str

def is_receipt_notice(document_type: str) -> bool:
    """
    受信通知かどうかを判定
    
    Args:
        document_type: ドキュメントタイプ（例: "1003_受信通知", "2013_受信通知"）
        
    Returns:
        bool: 受信通知（1003系または2003系）の場合True
    """
    if "_受信通知" not in document_type:
        return False
        
    # 1003系または2003系の受信通知
    code_part = document_type.split("_")[0]
    try:
        code_num = int(code_part)
        return (1000 <= code_num < 2000 and code_num % 10 == 3) or \
               (2000 <= code_num < 3000 and code_num % 10 == 3)
    except ValueError:
        return False

def is_pref_receipt(document_type: str) -> bool:
    """
    都道府県受信通知かどうかを判定
    
    Args:
        document_type: ドキュメントタイプ（例: "1003_受信通知"）
        
    Returns:
        bool: 都道府県受信通知（1003系）の場合True
    """
    if not is_receipt_notice(document_type):
        return False
        
    code_part = document_type.split("_")[0]
    try:
        code_num = int(code_part)
        return 1000 <= code_num < 2000
    except ValueError:
        return False

def is_city_receipt(document_type: str) -> bool:
    """
    市町村受信通知かどうかを判定
    
    Args:
        document_type: ドキュメントタイプ（例: "2003_受信通知"）
        
    Returns:
        bool: 市町村受信通知（2003系）の場合True
    """
    if not is_receipt_notice(document_type):
        return False
        
    code_part = document_type.split("_")[0]
    try:
        code_num = int(code_part)
        return 2000 <= code_num < 3000
    except ValueError:
        return False