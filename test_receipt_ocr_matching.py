#!/usr/bin/env python3
"""
受信通知OCR照合システムのテスト（東京都繰り上がり対応）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def test_receipt_notification_ocr_matching():
    """受信通知のOCRベース自治体セット照合テスト"""
    classifier = DocumentClassifierV5(debug_mode=True)
    
    print("=== 受信通知OCR照合システムテスト ===")
    
    # セット設定をモックで設定（東京都あり）
    test_municipality_sets = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"},
        3: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    classifier.current_municipality_sets = test_municipality_sets
    
    # テスト1: 東京都の市町村受信通知（存在しないが、テスト用）
    print("\n=== テスト1: 東京都市町村受信通知（理論的） ===")
    test_text_1 = "申告受付完了通知 法人市民税 東京都"
    result_1 = classifier._classify_local_tax_receipt(test_text_1, "tokyo_municipal.pdf", None, None)
    if result_1:
        print(f"結果: {result_1.document_type}")
        print(f"マッチ手法: {result_1.classification_method}")
    else:
        print("マッチなし")
    
    # テスト2: 愛知県蒲郡市の市町村受信通知
    print("\n=== テスト2: 愛知県蒲郡市市町村受信通知 ===")
    test_text_2 = "申告受付完了通知 法人市民税 蒲郡市役所"
    result_2 = classifier._classify_local_tax_receipt(test_text_2, "gamagori_municipal.pdf", None, None)
    if result_2:
        print(f"結果: {result_2.document_type}")
        print(f"マッチ手法: {result_2.classification_method}")
    else:
        print("マッチなし")
        
    # テスト3: 福岡県福岡市の市町村受信通知
    print("\n=== テスト3: 福岡県福岡市市町村受信通知 ===")
    test_text_3 = "申告受付完了通知 法人市民税 福岡市長"
    result_3 = classifier._classify_local_tax_receipt(test_text_3, "fukuoka_municipal.pdf", None, None)
    if result_3:
        print(f"結果: {result_3.document_type}")
        print(f"マッチ手法: {result_3.classification_method}")
    else:
        print("マッチなし")
    
    # テスト4: 愛知県の都道府県受信通知
    print("\n=== テスト4: 愛知県都道府県受信通知 ===")
    test_text_4 = "申告受付完了通知 法人事業税 愛知県"
    result_4 = classifier._classify_local_tax_receipt(test_text_4, "aichi_pref.pdf", None, None)
    if result_4:
        print(f"結果: {result_4.document_type}")
        print(f"マッチ手法: {result_4.classification_method}")
    else:
        print("マッチなし")
    
    print("\n=== 期待値確認 ===")
    expected_results = [
        ("東京都市町村受信通知", result_1.document_type if result_1 else None, "2003_受信通知"),
        ("蒲郡市市町村受信通知", result_2.document_type if result_2 else None, "2013_受信通知"),
        ("福岡市市町村受信通知", result_3.document_type if result_3 else None, "2023_受信通知"),
        ("愛知県都道府県受信通知", result_4.document_type if result_4 else None, "1013_受信通知"),
    ]
    
    for name, actual, expected in expected_results:
        status = "✓" if actual == expected else "✗"
        print(f"{status} {name}: {actual} (期待値: {expected})")

    # 東京都繰り上がりの詳細解説
    print("\n=== 東京都繰り上がりロジック ===")
    print("セット1: 東京都 → 市町村受信通知は2003から開始")
    print("セット2: 愛知県蒲郡市 → 市町村受信通知は2013")
    print("セット3: 福岡県福岡市 → 市町村受信通知は2023")

if __name__ == "__main__":
    test_receipt_notification_ocr_matching()