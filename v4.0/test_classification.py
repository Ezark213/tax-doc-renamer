#!/usr/bin/env python3
"""
分類エンジンテスト - ユーザーが指摘した具体的なファイルをテスト
"""

import sys
sys.path.append('.')

from main_v5_ultimate_fixed import UltimateClassificationEngine

def test_classification():
    """分類エンジンのテスト"""
    engine = UltimateClassificationEngine()
    
    test_cases = [
        ("仕訳帳_20250720_1541.pdf", "5005", "仕訳帳"),
        ("税区分集計表_20250720_1540.pdf", "7002", "税区分集計表"),
        ("総勘定元帳_20250720_1537.pdf", "5002", "総勘定元帳"),
        ("残高試算表_20250301_1234.pdf", "5004", "残高試算表"),
        ("補助元帳_20250301_1235.pdf", "5003", "補助元帳"),
        ("勘定科目別税区分集計表_20250301.pdf", "7001", "勘定科目別税区分集計表"),
    ]
    
    print("=== 分類エンジン テスト ===")
    print()
    
    all_passed = True
    
    for filename, expected_code, expected_name in test_cases:
        print(f"テスト: {filename}")
        
        # テキスト抽出をシミュレート（ファイル名から）
        text = filename.replace(".pdf", "").replace("_", " ")
        
        # 分類実行
        code, confidence, name = engine.classify_document(text, filename)
        result = {'code': code, 'confidence': int(confidence * 100), 'name': name}
        
        if result['code'] == expected_code:
            print(f"  OK 正解: {result['code']} - {result['name']} (信頼度: {result['confidence']}%)")
        else:
            print(f"  NG 不正解: 期待値 {expected_code} - {expected_name}")
            print(f"             実際値 {result['code']} - {result['name']} (信頼度: {result['confidence']}%)")
            all_passed = False
        
        print()
    
    if all_passed:
        print("OK 全てのテストケースが正常に分類されました！")
    else:
        print("NG 一部のテストケースで分類に問題があります。")
    
    return all_passed

if __name__ == "__main__":
    success = test_classification()
    sys.exit(0 if success else 1)