#!/usr/bin/env python3
"""
税務書類分類エンジン v4.0 修正版テストスクリプト
修正点1-5の包括的テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification import DocumentClassifier

def test_corrections():
    """修正点1-5の包括的テスト"""
    print("=== 税務書類分類エンジン v4.0 修正版テスト ===")
    print()
    
    classifier = DocumentClassifier(debug_mode=False)
    
    # 自治体設定例
    municipality_settings = {
        "set1": {"prefecture": "東京都", "municipality": ""},
        "set2": {"prefecture": "愛知県", "municipality": "蒲郡市"},
        "set3": {"prefecture": "大阪府", "municipality": "大阪市"},
        "set4": {"prefecture": "", "municipality": ""},
        "set5": {"prefecture": "", "municipality": ""}
    }
    
    # テストケース
    test_cases = [
        # 修正点1: 消費税添付資料のテスト
        {
            "name": "消費税添付資料テスト（修正点1）",
            "text": "添付書類送付書 消費税及び地方消費税申告書関連",
            "filename": "添付書類送付書_消費税.pdf",
            "expected": "3002_添付資料",
            "correction": "修正点1"
        },
        
        # 修正点2: 法人税添付資料のテスト
        {
            "name": "法人税添付資料テスト（修正点2）",
            "text": "添付書類送付書 内国法人の確定申告(青色)関連書類",
            "filename": "添付書類送付書_法人税.pdf",
            "expected": "0002_添付資料",
            "correction": "修正点2"
        },
        
        # 修正点3: 納付税額一覧表のテスト
        {
            "name": "納付税額一覧表テスト（修正点3）",
            "text": "納付税額一覧表 既納付額 令和6年度",
            "filename": "納付税額一覧表.pdf",
            "expected": "0000_納付税額一覧表",
            "correction": "修正点3"
        },
        
        # 修正点4: 都道府県書類のテスト
        {
            "name": "都道府県書類テスト（修正点4）",
            "text": "県税事務所 道府県民税 法人事業税申告書 年400万円以下",
            "filename": "県税事務所_事業税申告.pdf",
            "expected_contains": ["愛知県", "法人都道府県民税・事業税・特別法人事業税"],
            "correction": "修正点4"
        },
        
        # 修正点5: 市町村書類のテスト
        {
            "name": "市町村書類テスト（修正点5）",
            "text": "市役所 法人市民税申告書 市町村民税",
            "filename": "市役所_市民税申告.pdf",
            "expected_contains": ["愛知県蒲郡市", "法人市民税"],
            "correction": "修正点5"
        },
        
        # キーワード不足テスト
        {
            "name": "キーワード不足テスト（消費税添付）",
            "text": "添付書類送付書 法人税申告書関連",  # 消費税キーワードなし
            "filename": "添付書類送付書.pdf",
            "expected_not": "3002_添付資料",
            "correction": "要件不足確認"
        },
        
        {
            "name": "キーワード不足テスト（納付税額一覧表）",
            "text": "納付税額一覧表 令和6年度",  # 既納付額キーワードなし
            "filename": "納付税額一覧表.pdf",
            "expected_not": "0000_納付税額一覧表",
            "correction": "要件不足確認"
        }
    ]
    
    # テスト実行
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases):
        print(f"--- テスト {i+1}: {test_case['name']} ---")
        print(f"修正点: {test_case['correction']}")
        print(f"テキスト: {test_case['text']}")
        print(f"ファイル名: {test_case['filename']}")
        
        # 自治体設定を使用した分類
        if "都道府県" in test_case['name'] or "市町村" in test_case['name']:
            result = classifier.classify_with_municipality_info(
                test_case['text'], 
                test_case['filename'], 
                municipality_settings
            )
        else:
            result = classifier.classify_document(test_case['text'], test_case['filename'])
        
        print(f"実際の結果: {result.document_type}")
        
        # 結果確認
        success = False
        
        if "expected" in test_case:
            success = result.document_type == test_case['expected']
            print(f"期待値: {test_case['expected']}")
            
        elif "expected_contains" in test_case:
            success = all(keyword in result.document_type for keyword in test_case['expected_contains'])
            print(f"期待含有キーワード: {test_case['expected_contains']}")
            
        elif "expected_not" in test_case:
            success = result.document_type != test_case['expected_not']
            print(f"期待外キーワード: {test_case['expected_not']}")
        
        if success:
            print("PASS")
            print(f"   Method: {result.classification_method}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Keywords: {result.matched_keywords}")
            passed += 1
        else:
            print("FAIL")
            print(f"   Method: {result.classification_method}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Keywords: {result.matched_keywords}")
            failed += 1
        
        print()
    
    # 東京都エラーテスト
    print("--- 東京都エラーテスト ---")
    tokyo_error_settings = {
        "set1": {"prefecture": "愛知県", "municipality": "名古屋市"},
        "set2": {"prefecture": "東京都", "municipality": ""},  # エラー：東京都がセット2に
    }
    
    error_result = classifier.classify_with_municipality_info(
        "都税事務所 法人事業税申告書",
        "都税事務所.pdf",
        tokyo_error_settings
    )
    
    if "エラー" in error_result.document_type:
        print("PASS: Tokyo error handling")
        print(f"   Error message: {error_result.document_type}")
        passed += 1
    else:
        print("FAIL: Tokyo error handling")
        print(f"   Result: {error_result.document_type}")
        failed += 1
    print()
    
    # 結果サマリー
    print("=== テスト結果サマリー ===")
    print(f"成功: {passed}件")
    print(f"失敗: {failed}件")
    print(f"成功率: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\nSUCCESS: All correction tests passed!")
        return True
    else:
        print(f"\nWARNING: {failed} tests failed.")
        return False

if __name__ == "__main__":
    success = test_corrections()
    sys.exit(0 if success else 1)