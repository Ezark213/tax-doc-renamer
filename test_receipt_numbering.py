#!/usr/bin/env python3
"""
受信通知連番システムのテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def test_receipt_notification_numbering():
    """受信通知の連番処理テスト"""
    classifier = DocumentClassifierV5(debug_mode=True)
    
    print("=== 受信通知連番システムテスト ===")
    
    # セット設定をモックで設定
    test_municipality_sets = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"},
        3: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    classifier.current_municipality_sets = test_municipality_sets
    
    # テストケース1: 東京都の受信通知（セット1 → 1003）
    print("\n=== テスト1: 東京都（セット1）受信通知 ===")
    result_1 = classifier._apply_municipality_numbering("1003_受信通知", prefecture_code=1001, municipality_code=None)
    print(f"結果: {result_1}")
    print(f"期待値: 1003_受信通知")
    
    # テストケース2: 愛知県の受信通知（セット2 → 1013）
    print("\n=== テスト2: 愛知県（セット2）受信通知 ===")
    result_2 = classifier._apply_municipality_numbering("1003_受信通知", prefecture_code=1011, municipality_code=2011)
    print(f"結果: {result_2}")
    print(f"期待値: 1013_受信通知")
    
    # テストケース3: 福岡県の受信通知（セット3 → 1023）
    print("\n=== テスト3: 福岡県（セット3）受信通知 ===")
    result_3 = classifier._apply_municipality_numbering("1003_受信通知", prefecture_code=1021, municipality_code=2021)
    print(f"結果: {result_3}")
    print(f"期待値: 1023_受信通知")
    
    # テストケース4: 愛知県蒲郡市の受信通知（セット2 → 2013）
    print("\n=== テスト4: 愛知県蒲郡市（セット2）受信通知 ===")
    result_4 = classifier._apply_municipality_numbering("2003_受信通知", prefecture_code=1011, municipality_code=2011)
    print(f"結果: {result_4}")
    print(f"期待値: 2013_受信通知")
    
    # テストケース5: 福岡県福岡市の受信通知（セット3 → 2023）
    print("\n=== テスト5: 福岡県福岡市（セット3）受信通知 ===")
    result_5 = classifier._apply_municipality_numbering("2003_受信通知", prefecture_code=1021, municipality_code=2021)
    print(f"結果: {result_5}")
    print(f"期待値: 2023_受信通知")
    
    print("\n=== 結果確認 ===")
    results = [
        ("東京都都道府県受信通知", result_1, "1003_受信通知"),
        ("愛知県都道府県受信通知", result_2, "1013_受信通知"),
        ("福岡県都道府県受信通知", result_3, "1023_受信通知"),
        ("愛知県蒲郡市受信通知", result_4, "2013_受信通知"),
        ("福岡県福岡市受信通知", result_5, "2023_受信通知")
    ]
    
    for name, actual, expected in results:
        status = "✓" if actual == expected else "✗"
        print(f"{status} {name}: {actual} (期待値: {expected})")

if __name__ == "__main__":
    test_receipt_notification_numbering()