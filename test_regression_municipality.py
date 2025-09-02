#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市町村ラベル回帰テスト

期待結果:
1. 福岡市(市民税): 2021_福岡県福岡市_法人市民税
2. 福岡県税(都道府県税): 1021_福岡県_法人都道府県民税・事業税・特別法人事業税
3. 東京都税(都道府県税): 1001_東京都_法人都道府県民税・事業税・特別法人事業税
4. 蒲郡市(市民税): 2011_愛知県蒲郡市_法人市民税
5. 愛知県税(都道府県民税): 1011_愛知県_法人都道府県民税・事業税・特別法人事業税
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.classification_v5 import DocumentClassifierV5

def test_municipality_regression():
    """回帰テスト実行"""
    classifier = DocumentClassifierV5()
    
    print("=== 市町村ラベル回帰テスト開始 ===")
    
    # テストセット1: 東京都ありの場合
    set_settings_with_tokyo = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"},
        3: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    test_cases_with_tokyo = [
        {
            "name": "福岡市市民税",
            "text": "福岡市役所 法人市民税申告書 福岡県福岡市",
            "filename": "test_fukuoka_city.pdf",
            "expected": "2011_福岡県福岡市_法人市民税",  # 市町村2番目（東京都除外のため）
            "document_type": "2001_市町村_法人市民税"
        },
        {
            "name": "福岡県税", 
            "text": "福岡県西福岡県税事務所 法人都道府県民税 福岡県",
            "filename": "test_fukuoka_pref.pdf",
            "expected": "1021_福岡県_法人都道府県民税・事業税・特別法人事業税",  # 都道府県3番目
            "document_type": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税"
        },
        {
            "name": "東京都税",
            "text": "東京都港都税事務所 法人都道府県民税 東京都",
            "filename": "test_tokyo.pdf", 
            "expected": "1001_東京都_法人都道府県民税・事業税・特別法人事業税",  # 東京都は先頭固定
            "document_type": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税"
        },
        {
            "name": "蒲郡市市民税",
            "text": "蒲郡市役所 法人市民税申告書 愛知県蒲郡市",
            "filename": "test_gamagori.pdf",
            "expected": "2001_愛知県蒲郡市_法人市民税",  # 市町村1番目（東京都除外のため）
            "document_type": "2001_市町村_法人市民税"
        },
        {
            "name": "愛知県税",
            "text": "愛知県東三河県税事務所 法人都道府県民税 愛知県",
            "filename": "test_aichi_pref.pdf",
            "expected": "1011_愛知県_法人都道府県民税・事業税・特別法人事業税",  # 都道府県2番目
            "document_type": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税"
        }
    ]
    
    # テストセット2: 東京都なしの場合
    set_settings_without_tokyo = {
        1: {"prefecture": "愛知県", "city": "蒲郡市"},
        2: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    test_cases_without_tokyo = [
        {
            "name": "愛知県税（東京都なし）",
            "text": "愛知県東三河県税事務所 法人都道府県民税 愛知県",
            "filename": "test_aichi_pref_no_tokyo.pdf",
            "expected": "1001_愛知県_法人都道府県民税・事業税・特別法人事業税",  # 都道府県1番目
            "document_type": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税"
        },
        {
            "name": "福岡県税（東京都なし）",
            "text": "福岡県西福岡県税事務所 法人都道府県民税 福岡県", 
            "filename": "test_fukuoka_pref_no_tokyo.pdf",
            "expected": "1011_福岡県_法人都道府県民税・事業税・特別法人事業税",  # 都道府県2番目
            "document_type": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税"
        },
        {
            "name": "蒲郡市市民税（東京都なし）",
            "text": "蒲郡市役所 法人市民税申告書 愛知県蒲郡市",
            "filename": "test_gamagori_no_tokyo.pdf",
            "expected": "2001_愛知県蒲郡市_法人市民税",  # 市町村1番目
            "document_type": "2001_市町村_法人市民税"
        },
        {
            "name": "福岡市市民税（東京都なし）",
            "text": "福岡市役所 法人市民税申告書 福岡県福岡市",
            "filename": "test_fukuoka_city_no_tokyo.pdf",
            "expected": "2011_福岡県福岡市_法人市民税",  # 市町村2番目
            "document_type": "2001_市町村_法人市民税"
        }
    ]
    
    all_tests_passed = True
    
    def run_test_suite(test_name: str, set_settings: dict, test_cases: list) -> bool:
        """テストスイートを実行"""
        print(f"\n### {test_name} ###")
        print(f"セット設定: {set_settings}")
        print()
        
        # 連番マップ構築テスト
        try:
            pref_map, city_map = classifier.build_order_maps(set_settings)
            print(f"[OK] 連番マップ構築成功")
            print(f"  都道府県マップ: {pref_map}")
            print(f"  市町村マップ: {city_map}")
            print()
        except Exception as e:
            print(f"[NG] 連番マップ構築失敗: {e}")
            return False
        
        # 各テストケース実行
        results = []
        for i, case in enumerate(test_cases, 1):
            print(f"テスト {i}: {case['name']}")
            print(f"  入力テキスト: {case['text']}")
            print(f"  ファイル名: {case['filename']}")
            
            try:
                # ステートレス処理でラベル解決
                result = classifier._resolve_document_label_stateless(
                    case['document_type'],
                    case['text'],
                    case['filename'], 
                    set_settings
                )
                
                success = result == case['expected']
                results.append(success)
                
                status = "[PASS]" if success else "[FAIL]"
                print(f"  期待結果: {case['expected']}")
                print(f"  実際結果: {result}")
                print(f"  判定: {status}")
                
                if not success:
                    print(f"    [ERROR] 期待値と実際値が一致しません")
                
            except Exception as e:
                print(f"  判定: [ERROR] - {e}")
                results.append(False)
            
            print()
        
        # 結果サマリー
        passed = sum(results)
        total = len(results)
        print(f"=== {test_name} 結果 ===")
        print(f"成功: {passed}/{total} ({passed/total*100:.1f}%)")
        
        return passed == total
    
    # テストスイート実行
    suite1_passed = run_test_suite("東京都ありテスト", set_settings_with_tokyo, test_cases_with_tokyo)
    suite2_passed = run_test_suite("東京都なしテスト", set_settings_without_tokyo, test_cases_without_tokyo)
    
    # 全体結果サマリー
    print(f"\n=== 全体テスト結果 ===")
    if suite1_passed and suite2_passed:
        print("[SUCCESS] 全テストスイートが成功しました！")
        return True
    else:
        print("[FAILED] 一部テストスイートが失敗しました")
        if not suite1_passed:
            print("  - 東京都ありテスト: 失敗")
        if not suite2_passed:
            print("  - 東京都なしテスト: 失敗")
        return False

if __name__ == "__main__":
    test_municipality_regression()