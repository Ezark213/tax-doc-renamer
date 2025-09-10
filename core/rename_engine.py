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
from helpers.seq_policy import ReceiptSequencer, is_receipt_notice, is_pref_receipt, is_city_receipt

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
            "0001": "法人税等申告書",
            "0002": "添付資料_法人税",
            "0003": "受信通知",
            "0004": "納付情報",
            
            # 地方税系（都道府県）
            "1001": "都道府県申告書",
            "1003": "受信通知",
            "1013": "受信通知",  # 連番2番目
            "1023": "受信通知",  # 連番3番目
            "1004": "納付情報",
            
            # 地方税系（市町村）
            "2001": "市町村申告書",
            "2003": "受信通知",
            "2013": "受信通知",  # 連番2番目
            "2023": "受信通知",  # 連番3番目
            "2004": "納付情報",
            
            # 消費税系
            "3001": "消費税等申告書",
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
                
                # UI強制コード検証ログ強化（6001/6002/6003/0000）
                self._log_ui_forced_code_verification(final_code, final_yymm, yymm_source)
                
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
        
        # 最終ラベル決定（overlay優先採用システム）
        final_label = self._select_final_label_with_overlay(final_code, fields, snapshot, doc_item_id)
        code, title, muni, period = final_label.code, final_label.title, final_label.municipality, final_label.period
        
        # v5.3.5-ui-robust: 受信通知OCRベース連番処理（最終命名前）
        receipt_processed_code = self._apply_receipt_numbering_hook(code, fields, job_context)
        effective_code = receipt_processed_code or code
        
        # 連番処理（地方税系の場合）
        serial_code = self._compute_serial_if_needed(effective_code, doc_item_id, snapshot, fields)
        
        # ファイル名構築
        filename = self._format_filename(serial_code or effective_code, title, muni, period)
        
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
        # 禁止パターン（受信通知・納付情報からの_市町村・_都道府県 + 強化版）
        FORBIDDEN_SUFFIX_PATTERNS = [
            r'_市町村_(\d{4})$',  # _市町村_2508 → _2508
            r'_都道府県_(\d{4})$',  # _都道府県_2508 → _2508
            r'_市町村$',         # _市町村 → 削除
            r'_都道府県$',       # _都道府県 → 削除
            # 強化版：汎用語パターンの完全削除
            r'_受信通知_市町村_(\d{4})$',     # _受信通知_市町村_2508 → _受信通知_2508
            r'_受信通知_都道府県_(\d{4})$',   # _受信通知_都道府県_2508 → _受信通知_2508
            r'_納付情報_市町村_(\d{4})$',     # _納付情報_市町村_2508 → _納付情報_2508
            r'_納付情報_都道府県_(\d{4})$',   # _納付情報_都道府県_2508 → _納付情報_2508
            # 汎用語単体削除（汎用的すぎるラベル）
            r'_法人市民税_(\d{4})$',         # 具体自治体名がある場合のみ有効なので削除対象
            r'_法人都道府県民税_(\d{4})$'    # 同上
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
    
    def _select_final_label_with_overlay(self, final_code: str, fields: RenameFields, 
                                       snapshot: PreExtractSnapshot, doc_item_id: DocItemID) -> 'FinalLabel':
        """
        最終ラベル（code/name/pref/city）を単一点で決定。
        overlay(自治体変更版)があれば全面採用、なければ元コード。
        """
        from dataclasses import dataclass
        from typing import Optional
        
        @dataclass
        class FinalLabel:
            code: str
            title: str
            municipality: str
            period: str
            source: str = "base"  # base/overlay
        
        # 基本ラベル（フォールバック）
        base_code = final_code or fields.code_hint or "9999"
        base_title = self._get_title_for_code(base_code, fields)
        base_muni = self._format_municipality(fields.muni_name)
        base_period = self._format_period(fields.period_yyyymm)
        
        # classification_resultからoverlay情報を取得（スナップショットベース）
        if doc_item_id.page_index < len(snapshot.pages):
            page_result = snapshot.pages[doc_item_id.page_index]
            
            # overlay情報がある場合（自治体変更版）
            if hasattr(page_result, 'original_doc_type_code') and page_result.original_doc_type_code:
                # 現在のdocument_typeが変更後、original_doc_type_codeが元コード
                if hasattr(page_result, 'document_type') and page_result.document_type != page_result.original_doc_type_code:
                    overlay_code = page_result.document_type
                    overlay_title = self._get_title_for_code(overlay_code, fields)
                    
                    # 自治体名の詳細情報を抽出
                    overlay_muni = self._extract_municipality_from_overlay(overlay_code, fields)
                    
                    self.logger.info(f"[OVERLAY] Final label selection: {page_result.original_doc_type_code} → {overlay_code}")
                    self.logger.info(f"[OVERLAY] Municipality extracted: {overlay_muni}")
                    
                    return FinalLabel(
                        code=overlay_code,
                        title=overlay_title,
                        municipality=overlay_muni,
                        period=base_period,
                        source="overlay"
                    )
        
        # フォールバック：基本ラベル
        self.logger.debug(f"[LABEL] Using base label: code={base_code}, title={base_title}")
        
        return FinalLabel(
            code=base_code,
            title=base_title,
            municipality=base_muni,
            period=base_period,
            source="base"
        )
    
    def _extract_municipality_from_overlay(self, overlay_code: str, fields: RenameFields) -> str:
        """overlayコードから自治体名を抽出"""
        # overlayコード形式: 1011_愛知県_..., 2013_愛知県蒲郡市_... など
        if '_' in overlay_code:
            parts = overlay_code.split('_')
            if len(parts) >= 2:
                # 2番目の部分が自治体名
                muni_part = parts[1]
                # 禁止サフィックス除去適用
                muni_part = self._remove_forbidden_suffixes(f"dummy_{muni_part}_dummy").replace("dummy_", "").replace("_dummy", "")
                return muni_part
        
        # フォールバック：元の自治体名
        return self._format_municipality(fields.muni_name)
    
    def _log_ui_forced_code_verification(self, classification_code: str, yymm: str, yymm_source: str):
        """UI強制コード（6001/6002/6003/0000）の監査ログ強化"""
        from helpers.yymm_policy import log_yymm_audit, log_yymm_fatal
        
        code4 = classification_code[:4] if classification_code else ""
        ui_forced_codes = {"6001", "6002", "6003", "0000"}
        
        if code4 in ui_forced_codes:
            # UI強制コードの場合は特別監査ログ
            if yymm_source in ("UI", "UI_FORCED", "UI_FALLBACK"):
                # 成功ケース：UI値が正しく適用
                log_yymm_audit("UI_FORCED_SUCCESS", {
                    "code": code4,
                    "yymm": yymm,
                    "source": yymm_source,
                    "validation": "PASSED",
                    "mandatory": "TRUE"
                }, self.logger)
                
                # 回帰防止のための詳細ログ
                self.logger.info(f"[UI_FORCED][{code4}] ✅ UI YYMM mandatory application SUCCESS")
                self.logger.info(f"[UI_FORCED][{code4}] value={yymm} source={yymm_source} status=APPLIED")
                
            else:
                # 失敗ケース：UI値が適用されていない
                log_yymm_fatal(code4, f"UI YYMM mandatory but not applied: yymm={yymm}, source={yymm_source}", self.logger)
                
                self.logger.error(f"[UI_FORCED][{code4}] ❌ UI YYMM mandatory application FAILED")
                self.logger.error(f"[UI_FORCED][{code4}] expected=UI_FORCED actual={yymm_source}")
                
                raise ValueError(f"[FATAL] UI强制码 {code4} 需要UI输入的YYMM值，但未获得: source={yymm_source}")
        else:
            # 通常コードの場合は簡潔ログ
            if yymm and yymm_source:
                self.logger.debug(f"[YYMM_VERIFY] code={code4} yymm={yymm} source={yymm_source}")
    
    def _ensure_unique_filename(self, filename: str, doc_item_id: DocItemID) -> str:
        """ファイル名の一意性確保（決定論的サフィックス）"""
        # 基本的にはそのまま使用
        # 将来的に重複が発生した場合の対応を準備
        
        # 決定論的サフィックスの例（必要時のみ）
        # suffix = f"_{doc_item_id.page_index:03d}"
        # return f"{filename}{suffix}"
        
        return filename
    
    def _apply_receipt_numbering_hook(self, code: str, fields: RenameFields, 
                                     job_context: Optional['JobContext']) -> Optional[str]:
        """
        v5.3.5-ui-robust: 受信通知OCRベース連番処理フック（修正版）
        
        Args:
            code: 分類器による分類コード（例: "1003_受信通知"）
            fields: OCRから抽出されたフィールド
            job_context: UIセット順情報を保持するJobContext
            
        Returns:
            Optional[str]: 受信通知の場合は決定論的コード（例: "1013"）、そうでなければNone
        """
        # 受信通知でない場合はスキップ
        if not is_receipt_notice(code):
            return None
            
        # JobContextが無い場合はスキップ（フォールバック）
        if not job_context or not job_context.current_municipality_sets:
            self.logger.debug(f"[RECEIPT_HOOK] Skipped (no JobContext): {code}")
            return None
            
        try:
            # ReceiptSequencerインスタンス作成
            sequencer = ReceiptSequencer(job_context)
            
            # OCRテキストを複数のソースから取得を試行
            ocr_text = ""
            if hasattr(fields, 'document_text') and fields.document_text:
                ocr_text = fields.document_text
            elif hasattr(fields, 'ocr_text') and fields.ocr_text:
                ocr_text = fields.ocr_text
            elif hasattr(fields, 'full_text') and fields.full_text:
                ocr_text = fields.full_text
            
            # デバッグ用のフィールド内容出力
            self.logger.debug(f"[RECEIPT_HOOK] fields attributes: {[attr for attr in dir(fields) if not attr.startswith('_')]}")
            self.logger.debug(f"[RECEIPT_HOOK] OCR text length: {len(ocr_text) if ocr_text else 0}")
            
            if not ocr_text:
                self.logger.warning(f"[RECEIPT_HOOK] No OCR text available in fields for code: {code}")
                return None
            
            if is_pref_receipt(code):
                # 都道府県受信通知
                ocr_pref = self._extract_prefecture_from_ocr(ocr_text)
                if not ocr_pref:
                    self.logger.warning(f"[RECEIPT_HOOK][PREF] No prefecture detected in OCR text: '{ocr_text[:200]}'")
                    return None
                    
                final_code = sequencer.assign_pref_seq(code, ocr_pref)
                self.logger.info(f"[RECEIPT_HOOK][PREF] {code} + OCR={ocr_pref} -> {final_code}")
                return final_code
                
            elif is_city_receipt(code):
                # 市町村受信通知  
                ocr_pref, ocr_city = self._extract_prefecture_city_from_ocr(ocr_text)
                if not ocr_pref or not ocr_city:
                    self.logger.warning(f"[RECEIPT_HOOK][CITY] Incomplete OCR: pref={ocr_pref}, city={ocr_city}, text: '{ocr_text[:200]}'")
                    return None
                    
                final_code = sequencer.assign_city_seq(code, ocr_pref, ocr_city)
                self.logger.info(f"[RECEIPT_HOOK][CITY] {code} + OCR={ocr_pref}_{ocr_city} -> {final_code}")
                return final_code
                
        except ValueError as e:
            # 東京都制約違反など致命的エラー
            self.logger.error(f"[RECEIPT_HOOK] FATAL: {e}")
            raise
        except Exception as e:
            self.logger.error(f"[RECEIPT_HOOK] Unexpected error: {e}")
            import traceback
            self.logger.error(f"[RECEIPT_HOOK] Traceback: {traceback.format_exc()}")
            return None
            
        return None
    
    def _extract_prefecture_from_ocr(self, ocr_text: str) -> Optional[str]:
        """OCRテキストから都道府県名を抽出（強化版）"""
        if not ocr_text:
            return None
            
        # 修正指示書に基づく詳細なOCR検出パターン
        ocr_patterns = [
            # 都道府県税務署パターン
            r"([^県都府道]*(?:県|都|府|道))[^県都府道]*(?:県税事務所|都税事務所)",
            r"発行元\s*([^県都府道]*(?:県|都|府|道))[^県都府道]*(?:県税事務所|都税事務所)",
            # 市役所から県名を推定するパターンを追加
            r"([^県都府道]*(?:県|都|府|道))[^県都府道]*(?:市|区|町|村)",
            # 直接的な都道府県名パターン
            r"([^県都府道]*(?:県|都|府|道))",
        ]
        
        # 都道府県リスト（優先度順）
        prefectures = [
            "東京都", "愛知県", "福岡県", "大阪府", "神奈川県",  # 優先都道府県
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "新潟県", "富山県", 
            "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "三重県", 
            "滋賀県", "京都府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", 
            "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", 
            "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        # パターンマッチングで詳細検索
        import re
        for pattern in ocr_patterns:
            matches = re.findall(pattern, ocr_text)
            for match in matches:
                # マッチした文字列を正規化
                normalized = match.strip()
                if normalized in prefectures:
                    self.logger.debug(f"[OCR_PREF] Pattern matched: '{normalized}' from text: '{ocr_text[:100]}'")
                    return normalized
        
        # 直接検索（フォールバック）
        for pref in prefectures:
            if pref in ocr_text:
                self.logger.debug(f"[OCR_PREF] Direct match: '{pref}' from text: '{ocr_text[:100]}'")
                return pref
                
        self.logger.debug(f"[OCR_PREF] No prefecture found in text: '{ocr_text[:100]}'")
        return None
    
    def _extract_prefecture_city_from_ocr(self, ocr_text: str) -> Tuple[Optional[str], Optional[str]]:
        """OCRテキストから都道府県名と市区町村名を抽出（強化版）"""
        if not ocr_text:
            return None, None
            
        pref = self._extract_prefecture_from_ocr(ocr_text)
        if not pref:
            return None, None
            
        # 修正指示書に基づく市町村税務署パターン
        import re
        city_patterns = [
            # 市町村税務署パターン  
            r"([^市区町村]*(?:市|区|町|村))役所",
            r"発行元\s*([^市区町村]*(?:市|区|町|村))",
            r"提出先名\s*([^市区町村]*(?:市|区|町|村))長?",
            # 直接的な市区町村名パターン
            r"([^県都府道市区町村]*(?:市|区|町|村))",
        ]
        
        # 除外すべき都道府県関連の語句
        prefecture_suffixes = ["県", "都", "府", "道"]
        
        for pattern in city_patterns:
            matches = re.findall(pattern, ocr_text)
            for match in matches:
                normalized = match.strip()
                
                # 都道府県名を除外し、有効な市区町村名のみ抽出
                if (normalized and 
                    normalized != pref and 
                    len(normalized) >= 2 and
                    not any(normalized.endswith(suffix) for suffix in prefecture_suffixes)):
                    
                    self.logger.debug(f"[OCR_CITY] Pattern matched: pref='{pref}', city='{normalized}' from text: '{ocr_text[:100]}'")
                    return pref, normalized
                    
        # フォールバック：直接検索
        city_pattern = r'([^県都府道]*(?:市|区|町|村))'
        matches = re.findall(city_pattern, ocr_text)
        
        for match in matches:
            normalized = match.strip()
            if (normalized and 
                normalized != pref and 
                len(normalized) >= 2 and
                not any(normalized.endswith(suffix) for suffix in prefecture_suffixes)):
                
                self.logger.debug(f"[OCR_CITY] Direct match: pref='{pref}', city='{normalized}' from text: '{ocr_text[:100]}'")
                return pref, normalized
                
        self.logger.debug(f"[OCR_CITY] No city found for pref='{pref}' from text: '{ocr_text[:100]}'")
        return pref, None
    
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