#!/usr/bin/env python3
"""
Overlay system for LOCAL_TAX domain with noise suppression v5.3.4
オーバーレイシステム - 地方税の自治体コード変換とノイズ抑制
"""

import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from .domain import resolve_domain, is_prefecture_tax, is_municipal_tax

logger = logging.getLogger(__name__)


@dataclass
class SetContext:
    """自治体セット情報"""
    prefecture: Optional[str] = None
    city: Optional[str] = None
    set_id: Optional[int] = None


class OverlayResult:
    """オーバーレイ処理結果"""
    
    def __init__(self, overlay_code: Optional[str], reason: str):
        self.overlay_code = overlay_code
        self.reason = reason
        self.skipped = overlay_code is None
    
    def __str__(self):
        if self.skipped:
            return f"SKIPPED:{self.reason}"
        return f"APPLIED:{self.overlay_code}({self.reason})"


# v5.3.4 県別コードマッピング
PREFECTURE_CODE_MAP = {
    "東京都": "1001",    # 変化なし（基準値）
    "愛知県": "1011",    # 1001 → 1011にアップグレード
    "福岡県": "1021",    # 1001 → 1021にアップグレード  
    "大阪府": "1031",    # 1001 → 1031にアップグレード
    "神奈川県": "1041"   # 1001 → 1041にアップグレード
}


# 市町村コードマッピング
MUNICIPALITY_CODE_MAP = {
    2001: '愛知県蒲郡市',
    2011: '福岡県福岡市', 
    2021: '大阪市',
    2031: '横浜市',
    2041: '名古屋市'
}


def apply_local_overlay(base_code: str, set_ctx: SetContext) -> OverlayResult:
    """
    地方税オーバーレイ適用（v5.3.4ノイズ抑制対応）
    
    Args:
        base_code: 元の分類コード
        set_ctx: 自治体セット情報
        
    Returns:
        OverlayResult: オーバーレイ処理結果
        
    v5.3.4 仕様:
        - LOCAL_TAX以外はオーバーレイスキップ（ノイズ抑制）
        - 地方税のみ自治体別コードアップグレード実行
    """
    domain = resolve_domain(base_code)
    
    # v5.3.4: LOCAL_TAX以外はオーバーレイスキップ
    if domain != "LOCAL_TAX":
        logger.info("overlay=SKIPPED(domain=%s)", domain)
        return OverlayResult(None, domain)
    
    # ここから地方税のみの処理
    logger.debug("LOCAL_TAX domain detected: applying overlay logic")
    
    # 都道府県税の処理
    if is_prefecture_tax(base_code):
        return _apply_prefecture_overlay(base_code, set_ctx)
    
    # 市町村税の処理
    if is_municipal_tax(base_code):
        return _apply_municipal_overlay(base_code, set_ctx)
    
    # その他の地方税コード
    logger.debug("Other LOCAL_TAX code, no overlay applied: %s", base_code)
    return OverlayResult(base_code, "OTHER_LOCAL_TAX")


def _apply_prefecture_overlay(base_code: str, set_ctx: SetContext) -> OverlayResult:
    """都道府県税オーバーレイ適用"""
    if not set_ctx.prefecture:
        logger.debug("No prefecture context, keeping base code: %s", base_code)
        return OverlayResult(base_code, "NO_PREFECTURE")
    
    # 県別コードアップグレード
    upgraded_code = PREFECTURE_CODE_MAP.get(set_ctx.prefecture)
    if upgraded_code:
        logger.info("Prefecture code upgrade: %s -> %s (%s)", 
                   base_code, upgraded_code, set_ctx.prefecture)
        return OverlayResult(upgraded_code, f"PREF={set_ctx.prefecture}")
    
    # マッピングにない場合は基準値（1001）を維持
    logger.debug("Prefecture not in mapping, keeping base: %s (%s)", 
                base_code, set_ctx.prefecture)
    return OverlayResult(base_code, f"UNMAPPED_PREF={set_ctx.prefecture}")


def _apply_municipal_overlay(base_code: str, set_ctx: SetContext) -> OverlayResult:
    """市町村税オーバーレイ適用"""
    # 市町村税は分類時点で既に適切なコード（2001/2011/2021等）が決定済み
    # オーバーレイでは特に変更しない
    logger.debug("Municipal tax code, keeping as classified: %s", base_code)
    
    if set_ctx.city:
        return OverlayResult(base_code, f"MUNICIPAL={set_ctx.city}")
    else:
        return OverlayResult(base_code, "MUNICIPAL_NO_CITY")


def get_prefecture_final_code(base_code: str, prefecture: str) -> str:
    """都道府県の最終コードを取得（保険処理用）"""
    if not is_prefecture_tax(base_code):
        return base_code
    
    upgraded = PREFECTURE_CODE_MAP.get(prefecture)
    if upgraded:
        logger.debug("Final prefecture code: %s -> %s", base_code, upgraded)
        return upgraded
    
    return base_code


def resolve_municipality_label(code: str) -> str:
    """市町村コードから自治体名ラベルを解決"""
    try:
        code_int = int(code)
        return MUNICIPALITY_CODE_MAP.get(code_int, "市町村不詳")
    except (ValueError, TypeError):
        return "市町村不詳"


def is_overlay_applicable(code: str) -> bool:
    """オーバーレイ適用対象かどうかを判定"""
    return resolve_domain(code) == "LOCAL_TAX"


def should_log_overlay_skip(code: str) -> bool:
    """オーバーレイスキップログを出力すべきかどうか"""
    return not is_overlay_applicable(code)


def format_overlay_skip_log(code: str) -> str:
    """オーバーレイスキップログの形式を生成"""
    domain = resolve_domain(code)
    return f"overlay=SKIPPED(domain={domain})"


if __name__ == "__main__":
    # テスト実行
    import sys
    
    print("オーバーレイシステム テスト")
    print("=" * 50)
    
    # テストケース
    test_cases = [
        ("0001", SetContext("愛知県", None), "国税 - スキップ"),
        ("3001", SetContext("福岡県", None), "消費税 - スキップ"),
        ("5001", SetContext("東京都", None), "会計書類 - スキップ"),
        ("1001", SetContext("愛知県", None), "都道府県税 - アップグレード"),
        ("1001", SetContext("福岡県", None), "都道府県税 - アップグレード"),
        ("1001", SetContext("東京都", None), "都道府県税 - 基準値維持"),
        ("2001", SetContext("愛知県", "蒲郡市"), "市町村税 - 維持"),
        ("6003", SetContext("愛知県", None), "資産 - スキップ"),
    ]
    
    for base_code, ctx, description in test_cases:
        print(f"\n--- {description} ---")
        print(f"Input: {base_code}, Prefecture: {ctx.prefecture}, City: {ctx.city}")
        
        result = apply_local_overlay(base_code, ctx)
        print(f"Result: {result}")
        
        if result.overlay_code:
            print(f"Final code: {result.overlay_code}")
        else:
            print("No overlay applied (suppressed)")
    
    print("\n" + "=" * 50)
    print("テスト完了")