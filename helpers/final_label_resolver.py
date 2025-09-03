#!/usr/bin/env python3
"""
最終ラベルリゾルバー v5.3.3
すべての経路（非分割PDF/分割PDF/CSV）で使用する統一化された最終ラベル確定処理
"""

from typing import Tuple, Optional
from .domain import code_domain, is_overlay_allowed
from .yymm_policy import resolve_yymm_unified
import logging

logger = logging.getLogger(__name__)

class FinalLabelResult:
    """最終ラベル確定結果"""
    def __init__(self, final_label: str, yymm: str, 
                 source_code: str, domain: str, overlay_applied: bool,
                 yymm_source: str):
        self.final_label = final_label
        self.yymm = yymm
        self.source_code = source_code
        self.domain = domain
        self.overlay_applied = overlay_applied
        self.yymm_source = yymm_source


def finalize_label(base_class: str, ctx, settings, detected_yymm: str = None) -> FinalLabelResult:
    """
    統一最終ラベル確定処理
    
    Args:
        base_class: 一次判定で得られた書類クラス (例: "5003_補助元帳")
        ctx: DocumentContext
        settings: 設定オブジェクト 
        detected_yymm: OCR等で検出されたYYMM
        
    Returns:
        FinalLabelResult: 確定された最終ラベル情報
    """
    # ベースコード抽出
    code_part = base_class.split('_')[0] if '_' in base_class else base_class
    domain = code_domain(code_part)
    overlay_allowed = is_overlay_allowed(code_part)
    
    logger.info(f"[FINAL] base={base_class} code={code_part} domain={domain}")
    
    # YYMM解決
    yymm, yymm_source = resolve_yymm_unified(code_part, ctx, settings, detected_yymm)
    if not yymm:
        raise ValueError(f"YYMM resolution failed for {code_part}. GUI YYMM must be set for codes in {{'0000','6001','6002','6003'}}")
    
    # ドメインごとの処理
    if not overlay_allowed:
        # 会計・資産・国税系: オーバーレイなし、ベースクラスを維持
        final_class = base_class
        overlay_applied = False
        logger.info(f"[FINAL] domain={domain} overlay=SKIPPED -> final={final_class} yymm={yymm}")
        
    else:
        # 地方税系: 自治体オーバーレイ適用可能
        # NOTE: ここでは実際のオーバーレイ処理は既存コードに委譲
        # 実装時は normalize_classification の結果を使用
        final_class = base_class  # 仮実装
        overlay_applied = True
        logger.info(f"[FINAL] domain={domain} overlay=APPLIED -> final={final_class} yymm={yymm}")
    
    # ファイル名生成
    if yymm:
        final_label = f"{final_class}_{yymm}.pdf"
    else:
        final_label = f"{final_class}.pdf"
    
    return FinalLabelResult(
        final_label=final_label,
        yymm=yymm, 
        source_code=code_part,
        domain=domain,
        overlay_applied=overlay_applied,
        yymm_source=yymm_source
    )


def log_final_result(result: FinalLabelResult, filename: str = ""):
    """最終結果のログ出力"""
    overlay_status = "APPLIED" if result.overlay_applied else "SKIPPED"
    logger.info(f"[FINAL] base={result.source_code} domain={result.domain} "
                f"overlay={overlay_status} -> final={result.final_label} "
                f"yymm={result.yymm} source={result.yymm_source}")
    
    if filename:
        logger.info(f"[FINAL] {filename} -> {result.final_label}")


if __name__ == "__main__":
    # テスト
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # モックオブジェクト
    class MockContext:
        def __init__(self):
            self.gui_yymm = "2508"
    
    class MockSettings:
        def __init__(self):
            self.gui_yymm = "2508"
    
    ctx = MockContext()
    settings = MockSettings()
    
    # テストケース
    test_cases = [
        "5003_補助元帳",
        "6001_固定資産台帳", 
        "0001_法人税及び地方法人税申告書",
        "1004_納付情報_都道府県",
        "2001_市町村_法人市民税"
    ]
    
    for base_class in test_cases:
        try:
            result = finalize_label(base_class, ctx, settings)
            print(f"{base_class} -> {result.final_label} (domain: {result.domain})")
        except Exception as e:
            print(f"{base_class} -> ERROR: {e}")