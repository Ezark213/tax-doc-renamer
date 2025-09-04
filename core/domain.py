#!/usr/bin/env python3
"""
Domain resolution system for tax document classification v5.3.4
ドメイン解決システム - 書類コードから処理ドメインを判定
"""

from typing import Literal

DomainType = Literal[
    "NATIONAL_TAX",      # 国税 (0xxx)
    "LOCAL_TAX",         # 地方税 (1xxx/2xxx) 
    "CONSUMPTION_TAX",   # 消費税 (3xxx)
    "ACCOUNTING",        # 会計書類 (5xxx)
    "ASSETS",           # 資産 (6xxx)
    "SUMMARY",          # 集計・その他 (7xxx)
    "UNKNOWN"           # 未知
]


def resolve_domain(code: str) -> DomainType:
    """
    書類コードからドメインを解決
    
    Args:
        code: 書類コード (例: "0001", "1011", "3001")
        
    Returns:
        DomainType: 対応するドメイン
        
    Examples:
        >>> resolve_domain("0001")
        'NATIONAL_TAX'
        >>> resolve_domain("1011") 
        'LOCAL_TAX'
        >>> resolve_domain("3001")
        'CONSUMPTION_TAX'
    """
    if not code or not isinstance(code, str):
        return "UNKNOWN"
    
    try:
        head = int(code[0])
    except (ValueError, IndexError):
        return "UNKNOWN"
    
    domain_map = {
        0: "NATIONAL_TAX",      # 国税
        1: "LOCAL_TAX",         # 地方税（都道府県）
        2: "LOCAL_TAX",         # 地方税（市町村）
        3: "CONSUMPTION_TAX",   # 消費税
        5: "ACCOUNTING",        # 会計書類
        6: "ASSETS",           # 資産
        7: "SUMMARY"           # 集計・その他
    }
    
    return domain_map.get(head, "UNKNOWN")


def is_local_tax(code: str) -> bool:
    """地方税ドメインかどうかを判定"""
    return resolve_domain(code) == "LOCAL_TAX"


def is_prefecture_tax(code: str) -> bool:
    """都道府県税かどうかを判定"""
    return code.startswith("10") if code else False


def is_municipal_tax(code: str) -> bool:
    """市町村税かどうかを判定"""
    return code.startswith("20") if code else False


def should_suppress_overlay(code: str) -> bool:
    """オーバーレイ処理を抑制すべきかどうかを判定"""
    return not is_local_tax(code)


# ドメイン別説明
DOMAIN_DESCRIPTIONS = {
    "NATIONAL_TAX": "国税関連書類",
    "LOCAL_TAX": "地方税関連書類",
    "CONSUMPTION_TAX": "消費税関連書類", 
    "ACCOUNTING": "会計書類",
    "ASSETS": "固定資産関連書類",
    "SUMMARY": "集計・税区分関連書類",
    "UNKNOWN": "未分類書類"
}


def get_domain_description(code: str) -> str:
    """ドメインの日本語説明を取得"""
    domain = resolve_domain(code)
    return DOMAIN_DESCRIPTIONS.get(domain, "未知のドメイン")


if __name__ == "__main__":
    # テスト実行
    test_codes = [
        "0001", "0003", "1001", "1011", "2001", "2011", 
        "3001", "3002", "5001", "5002", "6001", "6003", "7001", "9999"
    ]
    
    print("ドメイン解決テスト:")
    print("=" * 50)
    
    for code in test_codes:
        domain = resolve_domain(code)
        desc = get_domain_description(code)
        suppress = should_suppress_overlay(code)
        
        print(f"Code: {code:4s} -> Domain: {domain:15s} ({desc})")
        print(f"               Suppress overlay: {suppress}")
        print()