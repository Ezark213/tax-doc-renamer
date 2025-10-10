#!/usr/bin/env python3
"""
Unified classification system v5.3.4
統合分類システム - 全モジュールの統合とワークフロー管理
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

# 新モジュールのインポート
from .domain import resolve_domain
from .overlay import apply_local_overlay, SetContext, OverlayResult
from .logging_bridge import (
    ClassifyResult, log_detailed_classification, log_overlay_decision, 
    log_yymm_resolution, log_filename_generation, log_split_reset,
    create_classification_result, title_of
)
from .yymm_resolver import resolve_yymm, NeedsUserInputError, YYMMSource, audit_yymm_usage
from helpers.settings_context import normalize_settings_input
from .naming_engine import build_filename_from_result, NamingContext, validate_and_build

# 既存システムとの互換性のため
from .classification_v5 import DocumentClassifierV5

logger = logging.getLogger(__name__)


@dataclass
class DocumentContext:
    """文書処理コンテキスト"""
    filename: str
    text: str
    municipality_sets: Optional[Dict[int, Dict[str, str]]] = None
    ui_context: Optional[Dict[str, Any]] = None
    page_info: Optional[Dict[str, Any]] = None


class UnifiedClassifier:
    """統合分類システム v5.3.5-assets-hotfix"""
    
    def __init__(self, debug_mode: bool = False, allow_auto_forced_codes: bool = False, process_mode: str = "確定申告"):
        self.debug_mode = debug_mode
        self.allow_auto_forced_codes = allow_auto_forced_codes
        self.process_mode = process_mode
        self.logger = logging.getLogger(__name__)

        # 既存分類器（後方互換性のため）- process_modeを渡す
        self.legacy_classifier = DocumentClassifierV5(debug_mode=debug_mode, process_mode=process_mode)

        if debug_mode:
            self.logger.setLevel(logging.DEBUG)

        version_msg = f"UnifiedClassifier v5.3.5-assets-hotfix initialized (process_mode={process_mode})"
        if allow_auto_forced_codes:
            version_msg += " (auto_forced_codes=ENABLED)"
        self.logger.info(version_msg)
    
    def classify_and_prepare(self, doc_context: DocumentContext) -> ClassifyResult:
        """
        文書分類と準備処理（v5.3.4統合ワークフロー）
        
        Args:
            doc_context: 文書処理コンテキスト
            
        Returns:
            ClassifyResult: 統合分類結果
            
        Workflow:
            1. 基本分類実行
            2. オーバーレイ処理（地方税のみ、ノイズ抑制）
            3. YYMM解決
            4. 結果統合・ログ出力
        """
        self.logger.debug("Starting unified classification for: %s", doc_context.filename)
        
        # === Step 1: 基本分類実行 ===
        base_result = self._run_base_classification(doc_context)
        self.logger.debug("Base classification: %s (confidence: %.2f)", 
                         base_result.base_code, base_result.confidence)
        
        # === Step 2: オーバーレイ処理（v5.3.4ノイズ抑制対応） ===
        overlay_result = self._apply_overlay_processing(base_result, doc_context)
        base_result.overlay_code = overlay_result.overlay_code
        base_result.meta["overlay_reason"] = overlay_result.reason
        
        # === Step 3: YYMM解決 ===
        yymm_result = self._resolve_yymm(base_result, doc_context)
        base_result.yymm = yymm_result.yymm
        base_result.yymm_source = yymm_result.source.value if yymm_result.source else None
        
        # === Step 4: 結果統合・メタデータ設定 ===
        self._finalize_result(base_result, doc_context)
        
        # === Step 5: ログ出力 ===
        self._log_classification_results(base_result, doc_context, overlay_result)
        
        return base_result
    
    def _run_base_classification(self, doc_context: DocumentContext) -> ClassifyResult:
        """基本分類実行"""
        # 既存分類器を使用（後方互換性）
        legacy_result = self.legacy_classifier.classify_document_v5(
            doc_context.text, doc_context.filename
        )
        
        # 新形式に変換
        result = create_classification_result(
            base_code=legacy_result.document_type,
            title=title_of(legacy_result.document_type),
            confidence=legacy_result.confidence,
            classification_method=legacy_result.classification_method,
            matched_keywords=legacy_result.matched_keywords,
            meta=getattr(legacy_result, 'meta', {})
        )
        
        return result
    
    def _apply_overlay_processing(self, result: ClassifyResult, 
                                 doc_context: DocumentContext) -> OverlayResult:
        """オーバーレイ処理適用"""
        # 自治体セット情報の構築
        set_context = self._build_set_context(doc_context)
        
        # v5.3.4オーバーレイ適用（ノイズ抑制付き）
        overlay_result = apply_local_overlay(result.base_code, set_context)
        
        self.logger.debug("Overlay processing: %s -> %s (%s)",
                         result.base_code, overlay_result.overlay_code, overlay_result.reason)
        
        return overlay_result
    
    def _build_set_context(self, doc_context: DocumentContext) -> SetContext:
        """自治体セットコンテキストの構築"""
        if not doc_context.municipality_sets:
            return SetContext()
        
        # 簡略化: 最初に見つかった自治体情報を使用
        # 実際の実装では、テキスト解析等でより精密に特定
        for set_id, info in doc_context.municipality_sets.items():
            prefecture = info.get('prefecture')
            city = info.get('city', '')
            if prefecture:
                return SetContext(prefecture=prefecture, city=city, set_id=set_id)
        
        return SetContext()
    
    def _resolve_yymm(self, result: ClassifyResult, doc_context: DocumentContext):
        """YYMM解決処理（v5.3.5-assets-hotfix対応）"""
        # 文書オブジェクトの模擬（既存システム互換性）
        from types import SimpleNamespace
        doc_obj = SimpleNamespace(text=doc_context.text, filename=doc_context.filename)
        
        # v5.3.5-ui-robust: 一貫した設定コンテキスト使用
        ui_context_raw = doc_context.ui_context or {}
        normalized_ui_context = normalize_settings_input(ui_context_raw)
        
        try:
            # v5.3.5: 新しいAPIパラメータ
            yymm_result = resolve_yymm(
                code=result.base_code, 
                document=doc_obj, 
                ui_context=normalized_ui_context.to_dict(),
                allow_auto_forced_codes=getattr(self, 'allow_auto_forced_codes', False),
                batch_mode=True,  # 統合分類器は常にバッチモード
                file_id=doc_context.filename or "unknown"
            )
            
            self.logger.debug("YYMM resolved: %s (source: %s)", 
                             yymm_result.yymm, yymm_result.source.value if yymm_result.source else "NONE")
            return yymm_result
            
        except Exception as e:
            self.logger.warning("YYMM resolution failed: %s", str(e))
            from .yymm_resolver import YYMMResult, YYMMSource
            return YYMMResult(None, YYMMSource.NONE, 0.0, "resolution_failed")
    
    def _finalize_result(self, result: ClassifyResult, doc_context: DocumentContext):
        """結果の最終化処理"""
        # ドメイン情報設定
        domain = resolve_domain(result.base_code)
        result.meta["domain"] = domain
        
        # no_splitメタデータ設定（既存ロジック互換）
        no_split_codes = {"6001", "6002", "6003", "5001", "5002", "5003", "5004"}
        code_base = result.base_code.split('_')[0] if '_' in result.base_code else result.base_code
        result.meta["no_split"] = code_base in no_split_codes
        
        # ファイル名妥当性事前チェック
        try:
            naming_context = NamingContext(
                prefecture=self._extract_prefecture(doc_context),
                city=self._extract_city(doc_context)
            )
            
            if result.yymm:  # YYMMが確定している場合のみチェック
                test_filename = build_filename_from_result(result, naming_context)
                result.meta["projected_filename"] = test_filename
            
        except Exception as e:
            self.logger.debug("Filename projection failed: %s", str(e))
            result.meta["filename_error"] = str(e)
    
    def _extract_prefecture(self, doc_context: DocumentContext) -> Optional[str]:
        """都道府県名抽出"""
        if doc_context.municipality_sets:
            for info in doc_context.municipality_sets.values():
                if info.get('prefecture'):
                    return info['prefecture']
        return None
    
    def _extract_city(self, doc_context: DocumentContext) -> Optional[str]:
        """市町村名抽出"""
        if doc_context.municipality_sets:
            for info in doc_context.municipality_sets.values():
                if info.get('city'):
                    return info['city']
        return None
    
    def _log_classification_results(self, result: ClassifyResult, 
                                   doc_context: DocumentContext,
                                   overlay_result: OverlayResult):
        """分類結果のログ出力"""
        # v5.3.4詳細分類ログ（三者一致対応）
        log_detailed_classification(result, doc_context.filename)
        
        # オーバーレイ決定ログ
        set_context = self._build_set_context(doc_context)
        log_overlay_decision(result.base_code, overlay_result, set_context)
        
        # YYMM解決ログ
        from .yymm_resolver import YYMMSource
        yymm_source = YYMMSource(result.yymm_source) if result.yymm_source else YYMMSource.NONE
        log_yymm_resolution(result.base_code, result.yymm, result.yymm_source or "NONE",
                           yymm_source == YYMMSource.UI_REQUIRED)
        
        # YYMM使用監査
        if result.yymm:
            audit_yymm_usage(result.yymm, yymm_source, doc_context.filename)
    
    def build_final_filename(self, result: ClassifyResult, 
                           doc_context: DocumentContext) -> Tuple[str, bool, str]:
        """
        最終ファイル名構築
        
        Returns:
            Tuple[str, bool, str]: (ファイル名, 成功フラグ, メッセージ)
        """
        naming_context = NamingContext(
            prefecture=self._extract_prefecture(doc_context),
            city=self._extract_city(doc_context),
            source_filename=doc_context.filename
        )
        
        filename, is_valid, message = validate_and_build(result, naming_context)
        
        if is_valid:
            log_filename_generation(result, filename)
        else:
            self.logger.warning("Filename building failed: %s", message)
        
        return filename, is_valid, message
    
    def process_document_complete(self, doc_context: DocumentContext) -> Tuple[ClassifyResult, str, bool, str]:
        """
        完全な文書処理ワークフロー（v5.3.5-assets-hotfix対応）
        
        Returns:
            Tuple[ClassifyResult, str, bool, str]: (分類結果, ファイル名, 成功フラグ, メッセージ)
        """
        try:
            # 分類・準備処理
            result = self.classify_and_prepare(doc_context)
            
            # v5.3.5: NEEDS_UI状態のチェック
            from .yymm_resolver import YYMMSource
            if result.yymm_source == YYMMSource.NEEDS_UI.value:
                self.logger.warning("[NEEDS_UI] Processing skipped: code=%s file=%s", 
                                  result.base_code, doc_context.filename)
                return result, "", False, f"NEEDS_UI: {result.base_code} requires user input"
            
            # ファイル名構築
            filename, is_valid, message = self.build_final_filename(result, doc_context)
            
            if is_valid:
                self.logger.info("Document processing completed successfully: %s", filename)
            else:
                self.logger.warning("Document processing completed with issues: %s", message)
            
            return result, filename, is_valid, message
            
        except Exception as e:
            # v5.3.5では NeedsUserInputError は通常発生しない（batch_mode=True）
            self.logger.error("Document processing failed: %s", str(e))
            # フォールバック結果
            fallback_result = create_classification_result("9999", "エラー書類", 0.0, "error")
            return fallback_result, "", False, f"処理エラー: {str(e)}"
    
    @staticmethod
    def log_split_reset(operation: str = "general"):
        """分割リセットログ（v5.3.4新機能）"""
        log_split_reset(operation)


# 便利な関数群
def create_document_context(filename: str, text: str, 
                           municipality_sets: Dict = None,
                           ui_context: Dict = None) -> DocumentContext:
    """DocumentContext作成ヘルパー"""
    return DocumentContext(
        filename=filename,
        text=text, 
        municipality_sets=municipality_sets,
        ui_context=ui_context
    )


def quick_classify(filename: str, text: str, 
                  municipality_sets: Dict = None,
                  ui_context: Dict = None,
                  allow_auto_forced_codes: bool = False) -> Tuple[ClassifyResult, str, bool, str]:
    """クイック分類（ワンライナー用、v5.3.5-assets-hotfix対応）"""
    classifier = UnifiedClassifier(allow_auto_forced_codes=allow_auto_forced_codes)
    context = create_document_context(filename, text, municipality_sets, ui_context)
    return classifier.process_document_complete(context)


if __name__ == "__main__":
    # テスト実行
    import sys
    
    print("統合分類システム v5.3.4 テスト")
    print("=" * 60)
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s:%(name)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # テストケース
    test_cases = [
        {
            "name": "国税書類",
            "filename": "houjinzei_test.pdf",
            "text": "メール詳細 種目 法人税及び地方法人税申告書 受付番号 20250731185710521215",
            "ui_context": {"yymm": "2507"}
        },
        {
            "name": "愛知県地方税",  
            "filename": "aichi_pref_tax.pdf",
            "text": "愛知県東三河県税事務所 法人都道府県民税 事業税 特別法人事業税申告書",
            "municipality_sets": {2: {"prefecture": "愛知県", "city": "蒲郡市"}},
            "ui_context": {"yymm": "2507"}
        },
        {
            "name": "資産書類（UI必須）",
            "filename": "shougaku_shisan.pdf", 
            "text": "少額減価償却資産明細表 固定資産 減価償却",
            "ui_context": {"yymm": "2401"}
        }
    ]
    
    classifier = UnifiedClassifier(debug_mode=True)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} テストケース {i}: {test_case['name']} {'='*20}")
        
        context = create_document_context(
            test_case["filename"],
            test_case["text"],
            test_case.get("municipality_sets"),
            test_case.get("ui_context")
        )
        
        result, filename, success, message = classifier.process_document_complete(context)
        
        print(f"\n🔍 処理結果:")
        print(f"  基本コード: {result.base_code}")
        print(f"  最終コード: {result.final_code}")
        print(f"  期間: {result.yymm}")
        print(f"  ファイル名: {filename}")
        print(f"  成功: {'✅' if success else '❌'}")
        if not success:
            print(f"  メッセージ: {message}")
    
    print(f"\n{'='*60}")
    print("統合テスト完了")