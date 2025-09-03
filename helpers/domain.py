#!/usr/bin/env python3
"""
ドメイン分類ヘルパー v5.3.3
書類コードのドメイン（領域）を判定し、Overlay Gate制御を行う
"""

def code_domain(code: str) -> str:
    """
    書類コードからドメインを判定
    
    Args:
        code: 書類コード (例: "5003", "0001", "1004")
        
    Returns:
        ドメイン名
        - ACCOUNTING_ASSET: 5xxx/6xxx/7xxx (会計・資産・集計)
        - NATIONAL_TAX: 0xxx/3xxx (国税)
        - LOCAL_TAX: 1xxx/2xxx (地方税)
        - UNKNOWN: その他
    """
    if not code:
        return "UNKNOWN"
        
    head = str(code)[:4]
    first_digit = head[:1]
    
    # 会計・資産・集計系（自治体オーバーレイ禁止）
    if first_digit in {"5", "6", "7"}:
        return "ACCOUNTING_ASSET"
    
    # 国税系（自治体オーバーレイ禁止）
    if first_digit == "3":
        return "NATIONAL_TAX"
    if head in {"0001", "0002", "0003", "0004", "0000"}:
        return "NATIONAL_TAX"
    
    # 地方税系（自治体オーバーレイ許可）
    if first_digit in {"1", "2"}:
        return "LOCAL_TAX"
    
    return "UNKNOWN"


def is_overlay_allowed(code: str) -> bool:
    """
    指定された書類コードで自治体オーバーレイが許可されるかチェック
    
    Args:
        code: 書類コード
        
    Returns:
        True: オーバーレイ許可（LOCAL_TAXのみ、ただし納付情報・受信通知コードは除外）
        False: オーバーレイ禁止
    """
    # 納付情報・受信通知コード（1004/2004/1003/2003/1013/2013）は自治体オーバーレイ禁止
    if code in {"1004", "2004", "1003", "2003", "1013", "2013"}:
        return False
    
    return code_domain(code) == "LOCAL_TAX"


def get_domain_description(domain: str) -> str:
    """ドメインの説明を取得"""
    descriptions = {
        "ACCOUNTING_ASSET": "会計・資産・集計系",
        "NATIONAL_TAX": "国税系", 
        "LOCAL_TAX": "地方税系",
        "UNKNOWN": "不明"
    }
    return descriptions.get(domain, "不明")


if __name__ == "__main__":
    # テスト
    test_codes = [
        "5003", "5002", "6001", "6002", "6003", "7001", "7002",  # ACCOUNTING_ASSET
        "0001", "0002", "0003", "0004", "0000", "3001", "3002", "3003", "3004",  # NATIONAL_TAX
        "1001", "1003", "1004", "1011", "1013", "2001", "2003", "2004", "2011", "2013"  # LOCAL_TAX
    ]
    
    print("ドメイン分類テスト:")
    for code in test_codes:
        domain = code_domain(code)
        overlay_ok = is_overlay_allowed(code)
        print(f"  {code}: {domain} (オーバーレイ: {'許可' if overlay_ok else '禁止'})")