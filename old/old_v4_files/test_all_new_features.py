#!/usr/bin/env python3
"""
税務書類分類エンジン v4.0 全機能テストスクリプト
新機能の包括的テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification import DocumentClassifier

def test_new_features():
    """新機能の包括的テスト"""
    print("=== 税務書類分類エンジン v4.0 新機能テスト ===")
    print()
    
    classifier = DocumentClassifier(debug_mode=False)
    
    # テストケース
    test_cases = [
        # 1. 添付書類分類の修正テスト
        {
            "name": "添付書類送付書テスト",
            "text": "添付書類送付書 内国法人の確定申告(青色) 令和6年度",
            "filename": "添付書類送付書.pdf",
            "expected": "0002_添付資料",
            "test_type": "添付書類分類修正"
        },
        {
            "name": "添付書類名称テスト", 
            "text": "添付書類名称 法人税申告書関連資料",
            "filename": "添付書類名称_法人税.pdf",
            "expected": "0002_添付資料",
            "test_type": "添付書類分類修正"
        },
        
        # 2. 都道府県・市町村認識キーワードテスト
        {
            "name": "県税事務所テスト",
            "text": "県税事務所 道府県民税 法人事業税申告書 年400万円以下",
            "filename": "県税事務所_事業税申告.pdf",
            "expected": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税",
            "test_type": "都道府県認識"
        },
        {
            "name": "市役所テスト",
            "text": "市役所 法人市民税申告書 市町村民税",
            "filename": "市役所_市民税申告.pdf", 
            "expected": "2001_市町村_法人市民税",
            "test_type": "市町村認識"
        },
        
        # 3. 既存の最優先キーワードテスト（継続確認）
        {
            "name": "総勘定元帳テスト",
            "text": "総勘定元帳 令和6年度",
            "filename": "総勘定元帳.pdf",
            "expected": "5002_総勘定元帳",
            "test_type": "既存機能継続確認"
        },
        {
            "name": "納付税額一覧表テスト",
            "text": "納付税額一覧表 2024年度",
            "filename": "納付税額一覧表.pdf", 
            "expected": "0000_納付税額一覧表",
            "test_type": "既存機能継続確認"
        }
    ]
    
    # テスト実行
    passed = 0
    failed = 0
    results_by_type = {}
    
    for i, test_case in enumerate(test_cases):
        print(f"--- テスト {i+1}: {test_case['name']} ---")
        print(f"テストタイプ: {test_case['test_type']}")
        print(f"テキスト: {test_case['text']}")
        print(f"ファイル名: {test_case['filename']}")
        print(f"期待値: {test_case['expected']}")
        
        # 分類実行
        result = classifier.classify_document(test_case['text'], test_case['filename'])
        
        # 結果確認
        success = result.document_type == test_case['expected']
        
        if success:
            print(f"PASS: {result.document_type}")
            print(f"   Method: {result.classification_method}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Keywords: {result.matched_keywords}")
            passed += 1
        else:
            print(f"FAIL: Expected {test_case['expected']} != Actual {result.document_type}")
            print(f"   Method: {result.classification_method}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Keywords: {result.matched_keywords}")
            failed += 1
        
        # タイプ別結果集計
        test_type = test_case['test_type']
        if test_type not in results_by_type:
            results_by_type[test_type] = {'passed': 0, 'failed': 0}
        
        if success:
            results_by_type[test_type]['passed'] += 1
        else:
            results_by_type[test_type]['failed'] += 1
        
        print()
    
    # 東京都エラー処理テスト
    print("--- 東京都エラー処理テスト ---")
    tokyo_result = classifier._classify_prefecture_document(
        "都税事務所 道府県民税 法人事業税申告書 年400万円以下", 
        "都税事務所_事業税申告.pdf",
        prefecture_code=1021  # セット3を指定
    )
    
    if tokyo_result and tokyo_result.document_type.startswith("1001_"):
        print("PASS: Tokyo set 2-5 error handling (forced to set 1)")
        passed += 1
        results_by_type['Tokyo Error Handling'] = {'passed': 1, 'failed': 0}
    else:
        print("FAIL: Tokyo set 2-5 error handling")
        failed += 1
        results_by_type['Tokyo Error Handling'] = {'passed': 0, 'failed': 1}
    print()
    
    # セット優先順序テスト
    print("--- セット優先順序テスト ---")
    set_result = classifier._determine_final_code_with_set_priority(
        "1001_都道府県_法人都道府県民税・事業税・特別法人事業税",
        available_sets=[1021, 1011, 1031]  # セット3、セット2、セット4が利用可能
    )
    
    expected_priority_code = "1011_都道府県_法人都道府県民税・事業税・特別法人事業税"  # セット2が最優先
    if set_result == expected_priority_code:
        print(f"PASS: Set priority test ({set_result})")
        passed += 1
        results_by_type['Set Priority'] = {'passed': 1, 'failed': 0}
    else:
        print(f"FAIL: Set priority test (Expected: {expected_priority_code}, Actual: {set_result})")
        failed += 1
        results_by_type['Set Priority'] = {'passed': 0, 'failed': 1}
    print()
    
    # 結果サマリー
    print("=== 総合テスト結果サマリー ===")
    print(f"成功: {passed}件")
    print(f"失敗: {failed}件") 
    print(f"成功率: {(passed/(passed+failed)*100):.1f}%")
    print()
    
    # タイプ別サマリー
    print("=== 機能別テスト結果 ===")
    for test_type, results in results_by_type.items():
        total = results['passed'] + results['failed']
        success_rate = (results['passed'] / total * 100) if total > 0 else 0
        print(f"{test_type}: {results['passed']}/{total} ({success_rate:.1f}%)")
    
    if failed == 0:
        print("\nSUCCESS: All new feature tests passed!")
        return True
    else:
        print(f"\nWARNING: {failed} tests failed.")
        return False

if __name__ == "__main__":
    success = test_new_features()
    sys.exit(0 if success else 1)