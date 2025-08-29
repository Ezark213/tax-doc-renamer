#!/usr/bin/env python3
"""
東京都制限機能のテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification import DocumentClassifier

def test_tokyo_restriction():
    """東京都制限機能のテスト"""
    print("=== 東京都制限機能テスト ===")
    print()
    
    classifier = DocumentClassifier(debug_mode=True)
    
    # テストケース1: 東京都がセット1にある正常ケース
    print("テスト1: 東京都がセット1にある正常ケース")
    municipality_settings_1 = {
        "set1": {"prefecture": "東京都", "municipality": ""},
        "set2": {"prefecture": "愛知県", "municipality": "蒲郡市"},
        "set3": {"prefecture": "大阪府", "municipality": "大阪市"}
    }
    
    # 都道府県書類のテスト
    result_1_pref = classifier.classify_with_municipality_info(
        "愛知県税事務所 道府県民税 法人事業税申告書",
        "prefecture.pdf",
        municipality_settings_1
    )
    print(f"都道府県書類結果: {result_1_pref.document_type}")
    
    # 市町村書類のテスト
    result_1_muni = classifier.classify_with_municipality_info(
        "蒲郡市役所 法人市民税申告書",
        "municipality.pdf", 
        municipality_settings_1
    )
    print(f"市町村書類結果: {result_1_muni.document_type}")
    print()
    
    # テストケース2: 東京都なしのケース
    print("テスト2: 東京都なしのケース")
    municipality_settings_2 = {
        "set1": {"prefecture": "愛知県", "municipality": "蒲郡市"},
        "set2": {"prefecture": "大阪府", "municipality": "大阪市"},
        "set3": {"prefecture": "福岡県", "municipality": "福岡市"}
    }
    
    # 都道府県書類のテスト
    result_2_pref = classifier.classify_with_municipality_info(
        "愛知県税事務所 道府県民税 法人事業税申告書",
        "prefecture.pdf",
        municipality_settings_2
    )
    print(f"都道府県書類結果: {result_2_pref.document_type}")
    
    # 市町村書類のテスト
    result_2_muni = classifier.classify_with_municipality_info(
        "蒲郡市役所 法人市民税申告書",
        "municipality.pdf",
        municipality_settings_2
    )
    print(f"市町村書類結果: {result_2_muni.document_type}")
    print()
    
    # 期待される結果の検証
    print("=== 結果検証 ===")
    
    # テスト1の検証
    test1_pref_expected = "1011_愛知県"  # 東京都がセット1なので愛知県はセット2→1011
    test1_muni_expected = "2001_愛知県蒲郡市"  # 最初の市町村→2001
    
    test1_pref_ok = test1_pref_expected in result_1_pref.document_type
    test1_muni_ok = test1_muni_expected in result_1_muni.document_type
    
    print(f"テスト1 都道府県: {test1_pref_ok} (期待: {test1_pref_expected} in {result_1_pref.document_type})")
    print(f"テスト1 市町村: {test1_muni_ok} (期待: {test1_muni_expected} in {result_1_muni.document_type})")
    
    # テスト2の検証
    test2_pref_expected = "1001_愛知県"  # 東京都なしなので愛知県がセット1→1001
    test2_muni_expected = "2001_愛知県蒲郡市"  # 最初の市町村→2001
    
    test2_pref_ok = test2_pref_expected in result_2_pref.document_type
    test2_muni_ok = test2_muni_expected in result_2_muni.document_type
    
    print(f"テスト2 都道府県: {test2_pref_ok} (期待: {test2_pref_expected} in {result_2_pref.document_type})")
    print(f"テスト2 市町村: {test2_muni_ok} (期待: {test2_muni_expected} in {result_2_muni.document_type})")
    
    # 全体結果
    all_passed = test1_pref_ok and test1_muni_ok and test2_pref_ok and test2_muni_ok
    print()
    print(f"=== 最終結果: {'PASS' if all_passed else 'FAIL'} ===")
    
    if all_passed:
        print("✅ 全ての東京都制限テストが成功しました！")
    else:
        print("❌ 一部のテストが失敗しました。")
    
    return all_passed

if __name__ == "__main__":
    success = test_tokyo_restriction()
    sys.exit(0 if success else 1)