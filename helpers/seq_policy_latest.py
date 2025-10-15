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
        東京都の必須セット1制約を検証（強化版）
        
        Raises:
            ValueError: 東京都がセット1以外にある場合のFATALエラー
        """
        if self._tokyo_first_checked:
            return
            
        # JobContextレベルでの東京都制約検証を実行
        try:
            self.ctx.validate_tokyo_constraint()
        except ValueError as e:
            # JobContextからの制約違反を再スロー
            logger.error(f"[SEQ] Tokyo constraint failed at JobContext level: {e}")
            raise
            
        # 追加の個別チェック（冗長だがより確実）
        tokyo_idx = self.ctx.get_set_index_for_pref("東京都")
        if tokyo_idx is not None and tokyo_idx != 1:
            error_msg = f"[FATAL][SEQ] Tokyo must be Set #1 (found at Set #{tokyo_idx}). 修正指示書に基づく制約違反です。"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self._tokyo_first_checked = True
        if tokyo_idx == 1:
            logger.info(f"[SEQ] Tokyo rule validation passed: Tokyo is at Set #1")
        else:
            logger.debug(f"[SEQ] Tokyo rule validation passed: Tokyo not found in sets (set_index={tokyo_idx})")
    
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
        # 修正指示書の連番計算式: 基本番号 + (入力順序 - 1) × 10
        final_code = BASE_PREF + (set_idx - 1) * 10
        final_code_str = f"{final_code:04d}"
        
        # キャッシュに保存
        self._assigned_codes[cache_key] = final_code_str
        
        logger.info(f"[SEQ][PREF] 都道府県連番決定: UI_set={set_idx}, pref={ocr_pref}, formula={BASE_PREF}+({set_idx}-1)*10={final_code_str}")
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
        
        # 東京都がセット1に存在し、かつ市町村なしの場合、市町村の順序を繰り上げ（東京都スキップ）
        # 修正指示書: 東京都は市町村なし（2000番台スキップで市町村順序繰り上げ）
        tokyo_idx = self.ctx.get_set_index_for_pref("東京都")
        adjusted_idx = set_idx

        # 東京都スキップ判定: セット1が東京都で市町村なしの場合のみ繰り上げ
        tokyo_skip_needed = False
        if tokyo_idx == 1:
            # セット1の市町村情報を確認
            tokyo_city = self.ctx.get_city_for_set(1)
            if not tokyo_city or tokyo_city.strip() == "":
                # 東京都（市町村なし）の場合、他の市町村は繰り上げ
                tokyo_skip_needed = (set_idx > 1)

        if tokyo_skip_needed:
            adjusted_idx = set_idx - 1
            logger.info(f"[SEQ][CITY] Tokyo-skip applied: original_set={set_idx} -> adjusted_set={adjusted_idx} (Tokyo at Set1 with no city)")
        
        # 修正指示書の連番計算式: 基本番号 + (調整後入力順序 - 1) × 10
        final_code = BASE_CITY + (adjusted_idx - 1) * 10
        final_code_str = f"{final_code:04d}"
        
        # キャッシュに保存
        self._assigned_codes[cache_key] = final_code_str
        
        logger.info(f"[SEQ][CITY] 市町村連番決定: UI_set={set_idx}, city={ocr_pref} {ocr_city}, tokyo_skip={tokyo_idx==1 and set_idx>1}, formula={BASE_CITY}+({adjusted_idx}-1)*10={final_code_str}")
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

def analyze_prefecture_sets(set_config):
    """
    汎用セット解析機能 - セット設定から都道府県・市町村情報を抽出

    Args:
        set_config: {1: {'prefecture': 'XX県', 'city': 'XX市'}, ...}

    Returns:
        tuple: (prefecture_list, municipality_list, has_tokyo, tokyo_position)
            - prefecture_list: 都道府県リスト（順序保持）
            - municipality_list: 市町村リスト（順序保持、空文字除外、Tokyo skip適用済み）
            - has_tokyo: 東京都の存在フラグ
            - tokyo_position: 東京都の位置（1-based、存在しない場合はNone）
    """
    if not set_config:
        return [], [], False, None

    prefecture_list = []
    raw_municipality_list = []  # Tokyo skip前の生の市町村リスト
    has_tokyo = False
    tokyo_position = None

    # セット番号順で処理
    for set_num in sorted(set_config.keys()):
        set_info = set_config[set_num]
        pref = set_info.get('prefecture', '').strip()
        city = set_info.get('city', '').strip()

        prefecture_list.append(pref)

        # 東京都の検出
        if pref == "東京都":
            has_tokyo = True
            tokyo_position = set_num

        # 市町村が存在する場合のみ追加（空文字・Noneは除外）
        if city:
            raw_municipality_list.append({
                'prefecture': pref,
                'city': city,
                'set_number': set_num,
                'original_position': len(raw_municipality_list)  # 市町村内での元の位置
            })

    # Tokyo skip logic: 東京都が存在し、市町村なしの場合、市町村リストから東京都分を繰り上げ
    municipality_list = []
    if has_tokyo and tokyo_position:
        # 東京都のセットに市町村があるかチェック
        tokyo_set = set_config.get(tokyo_position, {})
        tokyo_has_city = bool(tokyo_set.get('city', '').strip())

        if not tokyo_has_city:
            # 東京都は市町村なし → 市町村リストで東京都以降を繰り上げ
            logger.debug(f"[GENERIC_ANALYSIS] Tokyo skip applied: Tokyo at set {tokyo_position} has no municipality")
            for muni_info in raw_municipality_list:
                if muni_info['set_number'] > tokyo_position:
                    # 東京都より後のセット → 市町村順序で1つ繰り上げ
                    muni_info['adjusted_position'] = muni_info['original_position']  # すでに東京都が除外されているのでそのまま
                else:
                    # 東京都より前のセット → そのまま
                    muni_info['adjusted_position'] = muni_info['original_position']
                municipality_list.append(muni_info)
        else:
            # 東京都に市町村あり → 繰り上げなし
            logger.debug(f"[GENERIC_ANALYSIS] Tokyo has municipality: {tokyo_set.get('city')}, no skip applied")
            municipality_list = raw_municipality_list
            for i, muni_info in enumerate(municipality_list):
                muni_info['adjusted_position'] = i
    else:
        # 東京都なし → 繰り上げなし
        logger.debug(f"[GENERIC_ANALYSIS] No Tokyo found, no skip applied")
        municipality_list = raw_municipality_list
        for i, muni_info in enumerate(municipality_list):
            muni_info['adjusted_position'] = i

    logger.info(f"[GENERIC_ANALYSIS] Analysis complete: {len(prefecture_list)} prefectures, {len(municipality_list)} municipalities, Tokyo={has_tokyo} at position {tokyo_position}")

    return prefecture_list, municipality_list, has_tokyo, tokyo_position

def generate_receipt_number_generic(document_type, target_info, set_config):
    """
    汎用受信通知連番生成機能

    Args:
        document_type: "prefecture_receipt" or "municipality_receipt"
        target_info: OCR解析結果から得られた対象情報 (prefecture, city)
        set_config: セット設定辞書

    Returns:
        str: 生成された連番（例："1013", "2003"）

    Raises:
        ValueError: 対象自治体がセット設定に見つからない場合
    """
    prefecture_list, municipality_list, has_tokyo, tokyo_position = analyze_prefecture_sets(set_config)

    if document_type == "prefecture_receipt":
        # 都道府県受信通知の処理
        base_code = 1003
        target_prefecture = target_info.get('prefecture', '').strip()

        if not target_prefecture:
            raise ValueError("[GENERIC_RECEIPT] Prefecture name is required for prefecture receipt")

        try:
            pref_index = prefecture_list.index(target_prefecture)
            receipt_number = base_code + pref_index * 10
            logger.info(f"[GENERIC_RECEIPT] Prefecture receipt: {target_prefecture} at index {pref_index} → {receipt_number}")
            return f"{receipt_number:04d}"
        except ValueError:
            raise ValueError(f"[GENERIC_RECEIPT] Prefecture '{target_prefecture}' not found in set configuration")

    elif document_type == "municipality_receipt":
        # 市町村受信通知の処理（Tokyo skip適用済み）
        base_code = 2003
        target_prefecture = target_info.get('prefecture', '').strip()
        target_city = target_info.get('city', '').strip()

        if not target_city:
            raise ValueError("[GENERIC_RECEIPT] City name is required for municipality receipt")

        # 市町村リストでの位置を特定（Tokyo skip適用済み）
        municipal_index = None
        for muni_info in municipality_list:
            if (muni_info['prefecture'] == target_prefecture and
                muni_info['city'] == target_city):
                municipal_index = muni_info['adjusted_position']
                logger.info(f"[GENERIC_RECEIPT] Municipality found: {target_prefecture} {target_city} at adjusted position {municipal_index}")
                break

        if municipal_index is None:
            available_cities = [f"{m['prefecture']} {m['city']}" for m in municipality_list]
            raise ValueError(f"[GENERIC_RECEIPT] Municipality '{target_prefecture} {target_city}' not found. Available: {available_cities}")

        receipt_number = base_code + municipal_index * 10
        logger.info(f"[GENERIC_RECEIPT] Municipality receipt: {target_prefecture} {target_city} → position {municipal_index} → {receipt_number}")
        return f"{receipt_number:04d}"

    else:
        raise ValueError(f"[GENERIC_RECEIPT] Unknown document_type: {document_type}")

def extract_prefecture_city_from_ocr(ocr_text):
    """
    OCRテキストから都道府県・市町村を抽出（既存ロジックとの互換性のため）

    Args:
        ocr_text: OCR解析されたテキスト

    Returns:
        dict: {'prefecture': str, 'city': str}
    """
    # 既存のOCR解析ロジックをここに統合
    # 現在は仮実装として返す
    return {'prefecture': '', 'city': ''}