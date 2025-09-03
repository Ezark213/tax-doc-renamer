#!/usr/bin/env python3
"""
YYMM Policy System v5.3.1
集中化されたYYMM解決ポリシー管理システム
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

# UI-YYMM Force対象コード
FORCE_UI_YYMM_CODES = {
    '6001', '6002', '6003', '0000'
}

class YYMMSource(Enum):
    """YYMM取得元を表す列挙型"""
    GUI_SNAPSHOT = "GUI_SNAPSHOT"  # GUIスナップショットから
    DOC_HEURISTIC = "DOC/HEURISTIC"  # 書類内容から
    UI_YYMM_INJECTION = "UI-YYMM_INJECTION"  # UI-YYMMインジェクション
    FILENAME_EXTRACTION = "FILENAME"  # ファイル名から
    DEFAULT_FALLBACK = "DEFAULT"  # デフォルト値

class YYMMPolicy:
    """YYMM解決ポリシーを管理するクラス"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self._cached_yymm = {}  # キャッシュ
        
    def _log(self, message: str):
        """ログ出力"""
        if self.log_callback:
            self.log_callback(f"[YYMM][POLICY] {message}")
        logging.info(f"[YYMM][POLICY] {message}")
    
    def resolve_yymm_by_policy(self, 
                              doc_code: str,
                              gui_yymm: Optional[str] = None,
                              document_text: str = "",
                              filename: str = "",
                              ui_yymm_inject: Optional[str] = None) -> Tuple[str, YYMMSource]:
        """
        ポリシーベースYYMM解決
        
        Args:
            doc_code: 書類コード (例: "6001", "0000")
            gui_yymm: GUIスナップショットのYYMM
            document_text: 書類内容
            filename: ファイル名
            ui_yymm_inject: UI-YYMMインジェクション値
            
        Returns:
            Tuple[resolved_yymm, source]
        """
        # UI-YYMM Force判定
        if doc_code in FORCE_UI_YYMM_CODES:
            return self._handle_force_ui_yymm(doc_code, gui_yymm, ui_yymm_inject)
        
        # 通常のYYMM解決ロジック
        return self._resolve_standard_yymm(doc_code, gui_yymm, document_text, filename)
    
    def _handle_force_ui_yymm(self, 
                             doc_code: str, 
                             gui_yymm: Optional[str],
                             ui_yymm_inject: Optional[str]) -> Tuple[str, YYMMSource]:
        """UI-YYMM Force対象コードの処理"""
        
        # 1. UI-YYMMインジェクションを最優先
        if ui_yymm_inject and self._is_valid_yymm(ui_yymm_inject):
            self._log(f"code={doc_code}_{self._get_doc_name(doc_code)} value={ui_yymm_inject} source=UI-YYMM_INJECTION")
            return ui_yymm_inject, YYMMSource.UI_YYMM_INJECTION
        
        # 2. GUIスナップショット確認
        if gui_yymm and self._is_valid_yymm(gui_yymm):
            self._log(f"code={doc_code}_{self._get_doc_name(doc_code)} value={gui_yymm} source=GUI_SNAPSHOT")
            return gui_yymm, YYMMSource.GUI_SNAPSHOT
        
        # 3. UI-YYMM Force対象だが値がない場合はFATALエラー
        self._log(f"[FATAL] code={doc_code}_{self._get_doc_name(doc_code)} YYMM must come from GUI snapshot. Got: {gui_yymm}")
        raise ValueError(f"[FATAL] YYMM must come from GUI snapshot for {doc_code}. Got: {gui_yymm}")
    
    def _resolve_standard_yymm(self, 
                              doc_code: str,
                              gui_yymm: Optional[str],
                              document_text: str,
                              filename: str) -> Tuple[str, YYMMSource]:
        """標準YYMM解決ロジック"""
        
        # 1. GUIスナップショット優先
        if gui_yymm and self._is_valid_yymm(gui_yymm):
            self._log(f"code={doc_code}_{self._get_doc_name(doc_code)} value={gui_yymm} source=GUI_SNAPSHOT")
            return gui_yymm, YYMMSource.GUI_SNAPSHOT
        
        # 2. 書類内容からの抽出
        doc_yymm = self._extract_yymm_from_document(document_text)
        if doc_yymm:
            self._log(f"code={doc_code}_{self._get_doc_name(doc_code)} value={doc_yymm} source=DOC/HEURISTIC")
            return doc_yymm, YYMMSource.DOC_HEURISTIC
        
        # 3. ファイル名からの抽出
        filename_yymm = self._extract_yymm_from_filename(filename)
        if filename_yymm:
            self._log(f"code={doc_code}_{self._get_doc_name(doc_code)} value={filename_yymm} source=FILENAME")
            return filename_yymm, YYMMSource.FILENAME_EXTRACTION
        
        # 4. デフォルトフォールバック
        default_yymm = "YYMM"
        self._log(f"code={doc_code}_{self._get_doc_name(doc_code)} value={default_yymm} source=DEFAULT")
        return default_yymm, YYMMSource.DEFAULT_FALLBACK
    
    def _is_valid_yymm(self, yymm: str) -> bool:
        """YYMM形式の妥当性チェック"""
        if not yymm or yymm == "YYMM":
            return False
        
        # YYMM形式チェック (例: 2410)
        if re.match(r'^\d{4}$', yymm):
            year = int(yymm[:2])
            month = int(yymm[2:])
            return 1 <= month <= 12
        
        return False
    
    def _extract_yymm_from_document(self, text: str) -> Optional[str]:
        """書類内容からYYMM抽出"""
        if not text:
            return None
        
        # 年月パターンの検索
        patterns = [
            r'令和(\d{1,2})年(\d{1,2})月',  # 令和X年Y月
            r'(\d{4})/(\d{1,2})',  # YYYY/MM
            r'(\d{2})年(\d{1,2})月',  # YY年MM月
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    if "令和" in pattern:
                        reiwa_year = int(match.group(1))
                        month = int(match.group(2))
                        # 令和元年=令和1年=2019年, 令和6年=2024年
                        yy = (2018 + reiwa_year) % 100
                    elif len(match.group(1)) == 4:  # YYYY形式
                        year = int(match.group(1))
                        month = int(match.group(2))
                        yy = year % 100
                    else:  # YY形式
                        yy = int(match.group(1))
                        month = int(match.group(2))
                    
                    if 1 <= month <= 12:
                        return f"{yy:02d}{month:02d}"
                except ValueError:
                    continue
        
        return None
    
    def _extract_yymm_from_filename(self, filename: str) -> Optional[str]:
        """ファイル名からYYMM抽出"""
        if not filename:
            return None
        
        # ファイル名内のYYMM形式を探す
        patterns = [
            r'(\d{4})',  # 4桁数字
            r'_(\d{2})(\d{2})',  # _YYMM
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, filename)
            for match in matches:
                try:
                    if len(match.groups()) == 1:  # 4桁形式
                        yymm = match.group(1)
                        if len(yymm) == 4:
                            year = int(yymm[:2])
                            month = int(yymm[2:])
                            if 1 <= month <= 12:
                                return yymm
                    else:  # 分割形式
                        yy = int(match.group(1))
                        mm = int(match.group(2))
                        if 1 <= mm <= 12:
                            return f"{yy:02d}{mm:02d}"
                except ValueError:
                    continue
        
        return None
    
    def _get_doc_name(self, doc_code: str) -> str:
        """書類コードから書類名取得"""
        doc_names = {
            "0000": "納付税額一覧表",
            "6001": "固定資産台帳",
            "6002": "一括償却資産明細表", 
            "6003": "少額減価償却資産明細表",
            "5001": "決算書",
            "5002": "総勘定元帳",
            "5003": "補助元帳",
            "5004": "残高試算表",
            "5005": "仕訳帳",
            "7001": "勘定科目別税区分集計表",
            "7002": "税区分集計表"
        }
        return doc_names.get(doc_code, "不明書類")
    
    def inject_ui_yymm_shortcut(self, doc_code: str, yymm: str) -> bool:
        """UI-YYMMショートカットパスのインジェクション"""
        if not self._is_valid_yymm(yymm):
            self._log(f"[ERROR] Invalid YYMM for injection: {yymm}")
            return False
        
        if doc_code in FORCE_UI_YYMM_CODES:
            self._log(f"UI-YYMM injection: code={doc_code} value={yymm}")
            self._cached_yymm[doc_code] = yymm
            return True
        
        self._log(f"[WARN] UI-YYMM injection rejected: code={doc_code} not in FORCE list")
        return False
    
    def get_injected_yymm(self, doc_code: str) -> Optional[str]:
        """インジェクションされたYYMM取得"""
        return self._cached_yymm.get(doc_code)
    
    def clear_injection_cache(self):
        """インジェクションキャッシュクリア"""
        self._cached_yymm.clear()
        self._log("UI-YYMM injection cache cleared")

# グローバルインスタンス
_global_yymm_policy = None

def get_yymm_policy() -> YYMMPolicy:
    """グローバルYYMMポリシーインスタンス取得"""
    global _global_yymm_policy
    if _global_yymm_policy is None:
        _global_yymm_policy = YYMMPolicy()
    return _global_yymm_policy

def resolve_yymm_by_policy(doc_code: str, **kwargs) -> Tuple[str, YYMMSource]:
    """便利関数: ポリシーベースYYMM解決"""
    policy = get_yymm_policy()
    return policy.resolve_yymm_by_policy(doc_code, **kwargs)


def resolve_yymm_unified(class_code: str, ctx, settings, detected_yymm: str = None) -> Tuple[Optional[str], str]:
    """
    v5.3.3 統一YYMMリゾルバー
    命名直前で必ず呼ぶYYMM確定処理
    
    Args:
        class_code: 書類コード (例: "6001", "5003")
        ctx: DocumentContext
        settings: 設定オブジェクト
        detected_yymm: OCR等で検出されたYYMM
        
    Returns:
        (yymm, source) タプル
        - yymm: 確定したYYMM文字列 (None=エラー)
        - source: ソース文字列 ("UI_FORCED", "DETECTED", "UI_FALLBACK", "ERROR")
    """
    # UI強制コードチェック
    if class_code in FORCE_UI_YYMM_CODES:
        # GUIスナップショットから取得
        ui_yymm = getattr(settings, 'gui_yymm', None) or getattr(ctx, 'gui_yymm', None)
        if ui_yymm and ui_yymm != "YYMM":  # 未設定チェック
            return ui_yymm, "UI_FORCED"
        else:
            # UI強制系でYYMMが未設定の場合はエラー
            return None, "ERROR"
    
    # 一般コード: 検出優先→UIフォールバック
    if detected_yymm:
        return detected_yymm, "DETECTED" 
    
    # UIフォールバック
    ui_yymm = getattr(settings, 'gui_yymm', None) or getattr(ctx, 'gui_yymm', None)
    if ui_yymm and ui_yymm != "YYMM":
        return ui_yymm, "UI_FALLBACK"
    
    # すべて失敗
    return None, "ERROR"