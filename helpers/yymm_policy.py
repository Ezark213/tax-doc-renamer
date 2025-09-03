#!/usr/bin/env python3
"""
YYMM Policy System v5.3
高度なYYMM値決定とポリシー適用
"""

from typing import Tuple, Optional

# GUI必須コード（UI強制コード）
FORCE_UI_YYMM_CODES = {
    "6001", "6002", "6003", "0000"  # 固定資産台帳、一括償却資産、少額減価償却資産、納付税額一覧表
}

def _valid(yymm: str) -> bool:
    """YYMM値の妥当性チェック"""
    if not yymm:
        return False
    if not isinstance(yymm, str):
        return False
    if not yymm.isdigit():
        return False
    if len(yymm) != 4:
        return False
    return True

def require_ui_yymm(settings) -> Tuple[str, str]:
    """
    UI由来のYYMM値を必須として取得
    
    Returns:
        Tuple[str, str]: (yymm, source) または例外発生
        
    Raises:
        ValueError: UI値が無い、または無効な場合
    """
    manual_yymm = getattr(settings, "manual_yymm", None)
    
    if not _valid(manual_yymm):
        raise ValueError(f"[FATAL] UI YYMM is required but invalid or missing. Got: {manual_yymm}")
    
    return manual_yymm, "UI_FORCED"

def resolve_yymm_by_policy(class_code: str, ctx, settings, detected: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    class_code に応じて YYMM を決定。
    - FORCE_UI_YYMM_CODES: UIのみ
    - それ以外: detected（既存ロジックの結果）を優先。無ければ UI をフォールバック（安全網）。
    
    Args:
        class_code: 分類コード（4桁プレフィックス）
        ctx: パイプラインコンテキスト
        settings: 設定オブジェクト
        detected: 既存ロジックで検出されたYYMM値
        
    Returns:
        Tuple[Optional[str], str]: (yymm, source)
        
    Raises:
        ValueError: UI強制コードでUI値が無効な場合のみ
    """
    code4 = (class_code or "")[:4]
    
    # UI強制コード：常にUIから取得（必須）
    if code4 in FORCE_UI_YYMM_CODES:
        return require_ui_yymm(settings)
    
    # その他のコード：detected優先、UI fallback
    if detected and _valid(detected):
        return detected, "DOC/HEURISTIC"
    
    # フォールバック：UI値を安全網として使用
    manual_yymm = getattr(settings, "manual_yymm", None)
    ctx_yymm = getattr(ctx, "yymm", None) if ctx else None
    
    fallback_yymm = manual_yymm or ctx_yymm
    
    if _valid(fallback_yymm):
        return fallback_yymm, "UI_FALLBACK"
    
    # 最終防御：既存挙動を維持するため、ここだけは None を返し、上位での既存例外に委ねる
    return None, "NONE"

def log_yymm_decision(class_code: str, yymm: str, source: str, logger=None):
    """YYMM決定をログ出力"""
    if logger:
        logger.info(f"[YYMM][POLICY] code={class_code} value={yymm} source={source}")
    else:
        print(f"[YYMM][POLICY] code={class_code} value={yymm} source={source}")

def validate_policy_result(yymm: str, source: str, class_code: str = None) -> bool:
    """ポリシー適用結果の検証"""
    if not _valid(yymm):
        return False
    
    # UI強制コードの場合はUI由来であることを確認
    if class_code and class_code[:4] in FORCE_UI_YYMM_CODES:
        return source in ("UI_FORCED", "UI_FALLBACK")
    
    return True