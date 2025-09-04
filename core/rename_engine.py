#!/usr/bin/env python3
"""
決定論的リネームエンジン v5.3
スナップショット方式による安定したファイル名生成システム
"""

import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, TYPE_CHECKING
from collections import defaultdict

from .models import (
    DocItemID, PreExtractSnapshot, RenameFields, SerialAllocation,
    make_bucket_key, compute_text_sha1
)
from helpers.yymm_policy import resolve_yymm_by_policy, log_yymm_decision, validate_policy_result, log_yymm_fatal, log_yymm_audit
from helpers.settings_context import normalize_settings_input

if TYPE_CHECKING:
    from helpers.job_context import JobContext


class RenameEngine:
    """決定論的ファイル名生成エンジン"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # 書類コードと名称のマッピング（既存システムから移植）
        self.code_titles = {
            # 国税系
            "0000": "納付税額一覧表",
            "0001": "法人税及び地方法人税申告書",
            "0002": "添付資料_法人税",
            "0003": "受信通知",
            "0004": "納付情報",
            
            # 地方税系（都道府県）
            "1001": "法人都道府県民税・事業税・特別法人事業税申告書",
            "1003": "受信通知",
            "1013": "受信通知",  # 連番2番目
            "1023": "受信通知",  # 連番3番目
            "1004": "納付情報",
            
            # 地方税系（市町村）
            "2001": "法人市民税申告書",
            "2003": "受信通知",
            "2013": "受信通知",  # 連番2番目
            "2023": "受信通知",  # 連番3番目
            "2004": "納付情報",
            
            # 消費税系
            "3001": "消費税及び地方消費税申告書",
            "3002": "添付資料_消費税",
            "3003": "受信通知",
            "3004": "納付情報",
            
            # 帳票系
            "5001": "総勘定元帳",
            "5002": "仕訳帳等",
            "5003": "補助簿等",
            "5004": "試算表",
            "5005": "稟議書",
            
            # 資産系
            "6001": "固定資産台帳",
            "6002": "一括償却資産明細表",
            "6003": "少額減価償却資産明細表",
            
            # その他
            "7001": "勘定科目内訳明細書",
            "7002": "法人事業概況説明書",
            
            # 未分類
            "9999": "その他書類"
        }
        
        # 連番キャッシュ（セッション内で安定化）
        self.serial_cache: Dict[str, SerialAllocation] = {}
    
    def compute_filename(self, doc_item_id: DocItemID, snapshot: PreExtractSnapshot, 
                        final_code: str, fallback_ocr_text: Optional[str] = None, 
                        job_context: Optional['JobContext'] = None) -> str:
        """
        決定論的ファイル名生成のメイン関数
        
        Args:
            doc_item_id: 分割後書類の源泉情報
            snapshot: Pre-Extractスナップショット
            final_code: 最終分類コード（分類器の結果）
            fallback_ocr_text: スナップショット不足時のフォールバックテキスト
            job_context: JobContext（YYMM一元管理）
            
        Returns:
            str: 生成されたファイル名（拡張子なし）
        """
        self.logger.debug(f"[rename] Computing filename for page {doc_item_id.page_index}, code={final_code}")
        
        # スナップショットからフィールド取得
        fields = self._get_rename_fields(doc_item_id, snapshot, fallback_ocr_text)
        
        # --- YYMM JobContext Integration v5.3.5 ---
        # JobContextがある場合は一元管理されたYYMMを使用
        if job_context and job_context.confirmed_yymm:
            try:
                final_yymm = job_context.get_yymm_for_classification(final_code)
                yymm_source = job_context.yymm_source
                
                # Enhanced logging with AUDIT support
                log_yymm_audit("JOB_CONTEXT_USE", {
                    "job_id": job_context.job_id,
                    "code": final_code,
                    "yymm": final_yymm,
                    "source": yymm_source
                }, self.logger)
                
                fields.period_yyyymm = final_yymm
                
            except ValueError as e:
                log_yymm_fatal(final_code, str(e), self.logger)
                raise
                
        else:
            # フォールバック: 従来のポリシーベースYYMM決定
            detected = fields.period_yyyymm if (fields.period_yyyymm and fields.period_yyyymm.isdigit() and len(fields.period_yyyymm) == 4) else None
            
            try:
                # v5.3.5-ui-robust: 一貫した設定コンテキスト使用
                normalized_settings = normalize_settings_input(snapshot)
                pipeline_context = getattr(doc_item_id, '_pipeline_context', None)
                
                # ポリシーによるYYMM決定
                final_yymm, yymm_source = resolve_yymm_by_policy(
                    class_code=final_code,
                    ctx=pipeline_context,
                    settings=normalized_settings,
                    detected=detected
                )
                
                # ポリシー結果の検証
                if not validate_policy_result(final_yymm, yymm_source, final_code):
                    raise ValueError(f"[FATAL] Policy validation failed: yymm={final_yymm}, source={yymm_source}, code={final_code}")
                
                # ログ出力
                log_yymm_decision(final_code, final_yymm, yymm_source, self.logger)
                
                # fieldsに反映
                fields.period_yyyymm = final_yymm
            
            except Exception as e:
                log_yymm_fatal(final_code, f"Failed to resolve YYMM: {e}", self.logger)
                raise
        
        # v5.3 hotfix: source_pathの互換アクセス
        from helpers.paths import get_source_path
        try:
            source_path = get_source_path(doc_item_id)
            self.logger.info(f"[AUDIT][YYMM] use={fields.period_yyyymm} source=GUI file={Path(source_path).name}")
        except AttributeError:
            self.logger.info(f"[AUDIT][YYMM] use={fields.period_yyyymm} source=GUI file=unknown")
        
        # コード選定：最終分類を優先、フォールバックでヒント
        code = final_code or fields.code_hint or "9999"
        
        # 基本情報抽出
        title = self._get_title_for_code(code, fields)
        muni = self._format_municipality(fields.muni_name)
        period = self._format_period(fields.period_yyyymm)
        
        # 連番処理（地方税系の場合）
        serial_code = self._compute_serial_if_needed(code, doc_item_id, snapshot, fields)
        
        # ファイル名構築
        filename = self._format_filename(serial_code or code, title, muni, period)
        
        # 競合回避（決定論的サフィックス）
        final_filename = self._ensure_unique_filename(filename, doc_item_id)
        
        self.logger.info(f"[rename] Generated: {final_filename}")
        return final_filename
    
    def _get_rename_fields(self, doc_item_id: DocItemID, snapshot: PreExtractSnapshot,
                          fallback_text: Optional[str]) -> RenameFields:
        """スナップショットからRenameFieldsを取得"""
        if doc_item_id.page_index < len(snapshot.pages):
            fields = snapshot.pages[doc_item_id.page_index]
            self.logger.debug(f"[rename] Using snapshot data for page {doc_item_id.page_index}")
            return fields
        else:
            # フォールバック：再OCR
            self.logger.warning(f"[rename] Snapshot missing for page {doc_item_id.page_index}, using fallback")
            if fallback_text:
                return self._extract_fields_from_text(fallback_text)
            else:
                return RenameFields()  # 空のフィールド
    
    def _extract_fields_from_text(self, text: str) -> RenameFields:
        """フォールバック用のフィールド抽出（簡易版）"""
        fields = RenameFields()
        
        # 基本的なコード検出のみ
        code_match = re.search(r'\b(0003|0004|1003|1013|1023|1004|2003|2013|2023|2004|3003|3004)\b', text)
        if code_match:
            fields.code_hint = code_match.group(1)
        
        # 簡易自治体名検出
        muni_match = re.search(r'([都道府県市区町村]{2,6}[都道府県市区町村])', text)
        if muni_match:
            fields.muni_name = muni_match.group(1)
        
        return fields
    
    def _get_title_for_code(self, code: str, fields: RenameFields) -> str:
        """書類コードから適切なタイトルを生成"""
        # 基本タイトル
        base_title = self.code_titles.get(code, "")
        
        # 書類ヒントによる調整
        if fields.doc_hints and base_title in ["受信通知", "納付情報"]:
            # ヒントがある場合はより具体的に
            if "申告受付完了" in fields.doc_hints:
                base_title = "申告受付完了通知"
            elif "納付区分番号" in fields.doc_hints:
                base_title = "納付区分番号通知"
        
        return base_title
    
    def _format_municipality(self, muni_name: Optional[str]) -> str:
        """自治体名のフォーマット"""
        if not muni_name:
            return ""
        
        # 既存システムの形式に合わせる
        # 例：愛知県蒲郡市 -> 愛知県蒲郡市、東京都 -> 東京都
        return muni_name.strip()
    
    def _format_period(self, period_yyyymm: Optional[str]) -> str:
        """期間のフォーマット"""
        if not period_yyyymm:
            return ""
        
        # YYMM形式（例：2508）での出力
        # すでに正規化済みの前提
        return period_yyyymm
    
    def _compute_serial_if_needed(self, code: str, doc_item_id: DocItemID, 
                                 snapshot: PreExtractSnapshot, fields: RenameFields) -> Optional[str]:
        """必要に応じて連番コードを計算"""
        if not self._needs_serial_number(code):
            return None
        
        # 連番バケット生成
        bucket_key = make_bucket_key(
            doc_item_id.source_doc_md5,
            fields.muni_name or "NO_MUNI",
            fields.period_yyyymm or "NO_PERIOD"
        )
        
        # キャッシュから取得または生成
        if bucket_key not in self.serial_cache:
            self.serial_cache[bucket_key] = self._build_serial_allocation(
                snapshot, doc_item_id.source_doc_md5, fields.muni_name, fields.period_yyyymm, code
            )
        
        allocation = self.serial_cache[bucket_key]
        
        # 該当ページの連番を取得
        serial = allocation.get_serial_for_page(doc_item_id.page_index, doc_item_id.fp.text_sha1)
        
        if serial is not None:
            # 基本コード + 10の倍数
            base_code = int(code) if code.isdigit() else 9999
            serial_code = str(base_code + (serial - 1) * 10)
            self.logger.debug(f"[rename] Serial allocation: {code} -> {serial_code} (serial={serial})")
            return serial_code
        
        return None
    
    def _needs_serial_number(self, code: str) -> bool:
        """連番が必要な書類コードかどうか判定"""
        # 地方税の受信通知系（1003, 2003）が基点
        serial_base_codes = ["1003", "2003"]
        return code in serial_base_codes
    
    def _build_serial_allocation(self, snapshot: PreExtractSnapshot, source_md5: str,
                               muni_name: Optional[str], period: Optional[str], 
                               target_code: str) -> SerialAllocation:
        """連番割り当てテーブルの構築（決定論的安定化）"""
        bucket_key = make_bucket_key(source_md5, muni_name or "NO_MUNI", period or "NO_PERIOD")
        
        # 対象ページの収集（同じ自治体・期間・コード系）
        candidates = []
        for i, fields in enumerate(snapshot.pages):
            if (fields.muni_name == muni_name and 
                fields.period_yyyymm == period and
                fields.code_hint and fields.code_hint.startswith(target_code[:3])):
                
                # 決定論的ソート用のキー生成
                sort_key = self._generate_deterministic_sort_key(i, fields, source_md5)
                candidates.append((i, sort_key, fields.code_hint))
        
        # 決定論的ソート（ページ順 -> ソートキー順）
        candidates.sort(key=lambda x: (x[0], x[1]))
        
        # 連番割り当て（東京都特例・10刻み対応）
        items = []
        serial_counter = self._get_serial_start_number(muni_name, target_code)
        
        for page_index, sort_key, code_hint in candidates:
            items.append((page_index, sort_key, serial_counter))
            next_serial = self._calculate_next_serial(serial_counter, muni_name)
            self.logger.debug(f"[rename] 決定論的連番割当: page={page_index}, code={code_hint}, serial={serial_counter}")
            serial_counter = next_serial
        
        return SerialAllocation(bucket_key=bucket_key, items=items)
    
    def _generate_deterministic_sort_key(self, page_index: int, fields: RenameFields, source_md5: str) -> str:
        """決定論的ソートキー生成"""
        key_components = [
            str(page_index).zfill(4),
            fields.code_hint or "0000",
            fields.muni_name or "NO_MUNI",
            source_md5[:8]  # MD5の先頭8文字で安定性確保
        ]
        return "_".join(key_components)
    
    def _get_serial_start_number(self, muni_name: Optional[str], target_code: str) -> int:
        """連番開始番号を取得（自治体セット順序に基づく）"""
        # 基本連番（1番目の自治体）
        base_serials = {"1003": 1, "2003": 1}  # 1番目から開始
        
        if not muni_name or target_code not in base_serials:
            return 1
        
        # 自治体セット順序による連番調整（将来実装）
        # TODO: municipality_sets からセット順序を取得
        return base_serials[target_code]
    
    def _calculate_next_serial(self, current_serial: int, muni_name: Optional[str]) -> int:
        """次の連番を計算（10刻み）"""
        # 基本的には +1 だが、将来的に自治体間で10刻みにする場合の準備
        return current_serial + 1
    
    def _format_filename(self, code: str, title: str, muni: str, period: str) -> str:
        """ファイル名の最終フォーマット（決定論的独立化・単一点管理）"""
        # 基本構造: XXXX_[自治体名_]書類名_YYMM.pdf
        parts = [code]
        
        # 自治体名の付与（地方税のみ）
        if muni and self._should_include_municipality(code):
            parts.append(muni)
        
        # 書類名（必須）
        if title:
            parts.append(title)
        
        # 年月（YYMM形式、ポリシー決定値）
        if period and period != "YYMM":
            parts.append(period)
            self.logger.info(f"[v5.3] Using YYMM from policy system: {period}")
        
        filename = "_".join(parts)
        
        # 禁止サフィックス除去（受信通知・納付情報）
        filename = self._remove_forbidden_suffixes(filename)
        
        # 危険文字の除去
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', '_', filename)  # 空白をアンダースコアに
        
        return filename
    
    def _should_include_municipality(self, code: str) -> bool:
        """自治体名を含めるべき書類コードか判定"""
        # 地方税系（1000番台・2000番台）のみ自治体名を付与
        if code.isdigit() and len(code) == 4:
            code_int = int(code)
            return 1000 <= code_int < 3000
        return False
    
    def _remove_forbidden_suffixes(self, filename: str) -> str:
        """禁止されたサフィックスを除去（最終段で実行）"""
        # 禁止パターン（受信通知・納付情報からの_市町村・_都道府県）
        FORBIDDEN_SUFFIX_PATTERNS = [
            r'_市町村_(\d{4})$',  # _市町村_2508 → _2508
            r'_都道府県_(\d{4})$',  # _都道府県_2508 → _2508
            r'_市町村$',         # _市町村 → 削除
            r'_都道府県$'        # _都道府県 → 削除
        ]
        
        original_filename = filename
        for pattern in FORBIDDEN_SUFFIX_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                if match.groups():  # 年月がある場合
                    filename = re.sub(pattern, f'_{match.group(1)}', filename)
                else:  # 年月がない場合
                    filename = re.sub(pattern, '', filename)
                self.logger.debug(f"[rename] Forbidden suffix removed: '{original_filename}' → '{filename}'")
        
        return filename
    
    def _ensure_unique_filename(self, filename: str, doc_item_id: DocItemID) -> str:
        """ファイル名の一意性確保（決定論的サフィックス）"""
        # 基本的にはそのまま使用
        # 将来的に重複が発生した場合の対応を準備
        
        # 決定論的サフィックスの例（必要時のみ）
        # suffix = f"_{doc_item_id.page_index:03d}"
        # return f"{filename}{suffix}"
        
        return filename
    
    def precompute_all_serials(self, snapshot: PreExtractSnapshot) -> Dict[str, SerialAllocation]:
        """全連番を事前計算（dry-runモード用）"""
        self.logger.info("[rename] Precomputing all serial allocations")
        
        # 全バケットを特定
        buckets = defaultdict(list)
        
        for i, fields in enumerate(snapshot.pages):
            if fields.code_hint and self._needs_serial_number(fields.code_hint):
                bucket_key = make_bucket_key(
                    snapshot.source_doc_md5,
                    fields.muni_name or "NO_MUNI", 
                    fields.period_yyyymm or "NO_PERIOD"
                )
                buckets[bucket_key].append((i, fields))
        
        # 各バケットの連番計算
        all_allocations = {}
        for bucket_key, items in buckets.items():
            # 代表フィールドを使用してallocation構築
            if items:
                representative_fields = items[0][1]  # 最初のアイテムのフィールド
                allocation = self._build_serial_allocation(
                    snapshot, snapshot.source_doc_md5,
                    representative_fields.muni_name, representative_fields.period_yyyymm,
                    representative_fields.code_hint[:4] if representative_fields.code_hint else "1003"
                )
                all_allocations[bucket_key] = allocation
        
        self.logger.info(f"[rename] Precomputed {len(all_allocations)} serial buckets")
        return all_allocations
    
    def clear_serial_cache(self):
        """連番キャッシュのクリア（新しいPDF処理時）"""
        self.serial_cache.clear()
        self.logger.debug("[rename] Serial cache cleared")


def to_yymm(gui_value: str) -> str:
    """
    GUI値専用の薄いバリデータ関数
    他入力を受け取らないシグネチャに変更
    
    Args:
        gui_value: GUIからの4桁YYMM値のみ
        
    Returns:
        str: 検証済みYYMM値
        
    Raises:
        ValueError: GUI値以外または不正な値
    """
    if not gui_value or not gui_value.isdigit() or len(gui_value) != 4:
        raise ValueError(f"[FATAL] to_yymm: GUI only, must be 4 digits. Got: {gui_value}")
    return gui_value


def detect_period_from_ocr(text: str) -> str:
    """
    旧OCR期間検出関数の無効化スタブ
    万一呼ばれたら即座エラーで原因が視視可能
    """
    raise NotImplementedError("[FATAL] detect_period_from_ocr is disabled in v5.3. Use GUI YYMM only.")


def extract_period_from_filename(filename: str) -> Optional[str]:
    """
    旧ファイル名期間抽出関数の無効化スタブ
    万一呼ばれたら即座エラーで原因が視視可能
    """
    raise NotImplementedError("[FATAL] extract_period_from_filename is disabled in v5.3. Use GUI YYMM only.")


def validate_output_yymm(output_filenames: List[str], expected_yymm: str, logger: Optional[logging.Logger] = None) -> None:
    """
    出力ファイル名の YYMM 最終検証（全成果物共通フック）
    
    Args:
        output_filenames: 生成されたファイル名リスト（拡張子あり）
        expected_yymm: GUIで指定された期待値（例: "2508"）
        logger: ロガー
    
    Raises:
        AssertionError: YYMMが一致しないファイルがある場合
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    yymm_pattern = re.compile(rf"_{expected_yymm}\.(pdf|csv)$")
    
    failed_files = []
    for filename in output_filenames:
        if not yymm_pattern.search(filename):
            failed_files.append(filename)
    
    if failed_files:
        logger.error(f"[AUDIT][YYMM-CHECK] FAILED: {len(failed_files)} files with incorrect YYMM")
        for file in failed_files:
            logger.error(f"[AUDIT][YYMM-CHECK] DRIFT: {file} (expected _{expected_yymm})")
        raise AssertionError(f"[FATAL] YYMM drift detected in {len(failed_files)} files")
    
    logger.info(f"[AUDIT][YYMM-CHECK] OK: All {len(output_filenames)} files use correct YYMM={expected_yymm}")


def create_rename_engine(logger: Optional[logging.Logger] = None) -> RenameEngine:
    """RenameEngineのファクトリ関数"""
    return RenameEngine(logger=logger)