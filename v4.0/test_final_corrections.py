#!/usr/bin/env python3
"""
税務書類分類エンジン v4.0 最終修正テストスクリプト
修正点1-5の最終確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification import DocumentClassifier

def test_final_corrections():
    """修正点1-5の最終確認テスト"""
    print("Final Corrections Test for v4.0")
    print("=" * 50)
    
    classifier = DocumentClassifier(debug_mode=False)
    
    # 自治体設定
    municipality_settings = {
        "set1": {"prefecture": "東京都", "municipality": ""},
        "set2": {"prefecture": "愛知県", "municipality": "蒲郡市"},
        "set3": {"prefecture": "大阪府", "municipality": "大阪市"},
    }
    
    tests = []
    
    # 修正点1: 3002_添付資料（消費税添付資料）
    print("Test 1: Correction Point 1 - Consumption tax attachments")
    result1 = classifier.classify_document(
        "添付書類送付書 消費税及び地方消費税申告書関連", 
        "attachment.pdf"
    )
    test1_pass = result1.document_type == "3002_添付資料"
    print(f"  Result: {result1.document_type}")
    print(f"  Expected: 3002_添付資料")
    print(f"  Status: {'PASS' if test1_pass else 'FAIL'}")
    tests.append(test1_pass)
    print()
    
    # 修正点2: 0002_添付資料（法人税添付資料）
    print("Test 2: Correction Point 2 - Corporate tax attachments")
    result2 = classifier.classify_document(
        "添付書類送付書 内国法人の確定申告(青色)関連", 
        "attachment.pdf"
    )
    test2_pass = result2.document_type == "0002_添付資料"
    print(f"  Result: {result2.document_type}")
    print(f"  Expected: 0002_添付資料")
    print(f"  Status: {'PASS' if test2_pass else 'FAIL'}")
    tests.append(test2_pass)
    print()
    
    # 修正点3: 0000_納付税額一覧表（2つのキーワード要件）
    print("Test 3: Correction Point 3 - Tax payment list (requires both keywords)")
    result3 = classifier.classify_document(
        "納付税額一覧表 既納付額 令和6年度", 
        "payment_list.pdf"
    )
    test3_pass = result3.document_type == "0000_納付税額一覧表"
    print(f"  Result: {result3.document_type}")
    print(f"  Expected: 0000_納付税額一覧表")
    print(f"  Status: {'PASS' if test3_pass else 'FAIL'}")
    tests.append(test3_pass)
    print()
    
    # 修正点3-2: 納付税額一覧表（キーワード不足の場合）
    print("Test 3-2: Tax payment list (insufficient keywords - should not match)")
    result3_2 = classifier.classify_document(
        "納付税額一覧表 令和6年度",  # 既納付額キーワードなし
        "payment_list.pdf"
    )
    test3_2_pass = result3_2.document_type != "0000_納付税額一覧表"
    print(f"  Result: {result3_2.document_type}")
    print(f"  Expected: NOT 0000_納付税額一覧表")
    print(f"  Status: {'PASS' if test3_2_pass else 'FAIL'}")
    tests.append(test3_2_pass)
    print()
    
    # 修正点4: 都道府県書類（1011_愛知県_...）
    print("Test 4: Correction Point 4 - Prefecture documents with names and sequence")
    result4 = classifier.classify_with_municipality_info(
        "愛知県税事務所 道府県民税 法人事業税申告書", 
        "prefecture.pdf",
        municipality_settings
    )
    test4_pass = ("1011" in result4.document_type and "愛知県" in result4.document_type)
    print(f"  Result: {result4.document_type}")
    print(f"  Expected: Contains '1011' and '愛知県'")
    print(f"  Status: {'PASS' if test4_pass else 'FAIL'}")
    tests.append(test4_pass)
    print()
    
    # 修正点5: 市町村書類（2011_愛知県蒲郡市_...）
    print("Test 5: Correction Point 5 - Municipality documents with names and sequence")
    result5 = classifier.classify_with_municipality_info(
        "蒲郡市役所 法人市民税申告書", 
        "municipality.pdf",
        municipality_settings
    )
    test5_pass = ("2011" in result5.document_type and "愛知県蒲郡市" in result5.document_type)
    print(f"  Result: {result5.document_type}")
    print(f"  Expected: Contains '2011' and '愛知県蒲郡市'")
    print(f"  Status: {'PASS' if test5_pass else 'FAIL'}")
    tests.append(test5_pass)
    print()
    
    # 東京都エラー処理
    print("Test 6: Tokyo error handling")
    tokyo_error_settings = {
        "set2": {"prefecture": "東京都", "municipality": ""},  # エラー：東京都がセット2
    }
    result6 = classifier.classify_with_municipality_info(
        "都税事務所 法人事業税", 
        "tokyo.pdf",
        tokyo_error_settings
    )
    test6_pass = "エラー" in result6.document_type
    print(f"  Result: {result6.document_type}")
    print(f"  Expected: Contains 'エラー'")
    print(f"  Status: {'PASS' if test6_pass else 'FAIL'}")
    tests.append(test6_pass)
    print()
    
    # 結果サマリー
    print("=" * 50)
    print("FINAL TEST RESULTS")
    passed = sum(tests)
    total = len(tests)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if passed == total:
        print("\nALL CORRECTION TESTS PASSED!")
        print("Ready to build and commit.")
        return True
    else:
        print(f"\n{total-passed} tests failed. Please check implementation.")
        return False

if __name__ == "__main__":
    success = test_final_corrections()
    sys.exit(0 if success else 1)