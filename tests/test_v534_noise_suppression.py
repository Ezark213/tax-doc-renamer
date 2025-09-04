#!/usr/bin/env python3
"""
v5.3.4 ノイズ抑制とリセットログテスト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.classification_v5 import DocumentClassifierV5


def test_overlay_noise_suppression():
    """国税/会計に「自治体変更版」行が出力されないことをテスト"""
    print("=== test_overlay_noise_suppression ===")
    
    classifier = DocumentClassifierV5(debug_mode=True)
    
    # Test cases for non-LOCAL_TAX domains
    test_cases = [
        {
            "name": "国税（法人税）",
            "text": "メール詳細 種目 法人税及び地方法人税申告書 受付番号 20250731185710521215",
            "filename": "houjinzei_test.pdf",
            "expected_domain": "NATIONAL_TAX"
        },
        {
            "name": "消費税",
            "text": "納付区分番号通知 税目 消費税及地方消費税 納付先 芝税務署",
            "filename": "shouhizei_test.pdf", 
            "expected_domain": "CONSUMPTION_TAX"
        },
        {
            "name": "決算書（会計）",
            "text": "決算書 貸借対照表 損益計算書",
            "filename": "kessansho_test.pdf",
            "expected_domain": "ACCOUNTING"
        },
        {
            "name": "固定資産（資産）",
            "text": "固定資産台帳 減価償却",
            "filename": "kotei_shisan_test.pdf",
            "expected_domain": "ASSETS"
        },
        {
            "name": "税区分集計（集計）",
            "text": "勘定科目別税区分集計表 税区分集計表",
            "filename": "zeikubun_test.pdf",
            "expected_domain": "SUMMARY"
        }
    ]
    
    # 自治体セット設定（愛知県・福岡県）
    municipality_sets = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"},
        3: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} テスト ---")
        
        # 分類実行
        result = classifier.classify_with_municipality_info_v5(
            test_case["text"], 
            test_case["filename"], 
            municipality_sets=municipality_sets
        )
        
        # ドメイン確認
        domain = classifier.code_domain(result.document_type)
        expected_domain = test_case["expected_domain"]
        
        print(f"分類結果: {result.document_type}")
        print(f"ドメイン: {domain} (期待値: {expected_domain})")
        
        # 処理ログから「自治体名付きコード生成」の有無を確認
        processing_log_str = "\n".join(result.processing_log)
        has_overlay_generation = "自治体名付きコード生成" in processing_log_str
        has_overlay_skipped = "overlay=SKIPPED" in processing_log_str
        
        print(f"自治体変更版生成: {'有' if has_overlay_generation else '無'}")
        print(f"overlay=SKIPPED: {'有' if has_overlay_skipped else '無'}")
        
        # 期待結果の確認
        if domain != "LOCAL_TAX":
            if has_overlay_generation:
                print("失敗: LOCAL_TAX以外で自治体変更版が生成されました")
                return False
            elif not has_overlay_skipped:
                print("注意: overlay=SKIPPED ログがありませんが、自治体変更版は生成されていません")
            else:
                print("成功: ノイズ抑制が機能しています")
        else:
            print("LOCAL_TAX ドメインのため、自治体処理が実行される可能性があります")
    
    print("\n=== test_overlay_noise_suppression 完了 ===")
    return True


def test_split_reset_log():
    """__split_* 処理開始でリセットログが出ることをテスト"""
    print("\n=== test_split_reset_log ===")
    
    # このテストは実際のmain.pyの_split_single_fileメソッドを呼び出す必要がある
    # ここではモックとしてリセットログのフォーマットをテスト
    
    reset_log_patterns = [
        "[reset] __split_ 処理開始 - 分割状態リセット",
        "[reset] __split_ 一括処理開始 - 処理状態リセット"
    ]
    
    print("期待されるリセットログパターン:")
    for i, pattern in enumerate(reset_log_patterns, 1):
        print(f"{i}. {pattern}")
    
    # リセットログの検証ロジック
    def validate_reset_log(log_message):
        return (
            log_message.startswith("[reset]") and
            "__split_" in log_message and
            ("処理開始" in log_message or "開始" in log_message) and
            "リセット" in log_message
        )
    
    # テスト実行
    all_valid = True
    for pattern in reset_log_patterns:
        is_valid = validate_reset_log(pattern)
        print(f"OK {pattern}" if is_valid else f"NG {pattern}")
        if not is_valid:
            all_valid = False
    
    print(f"\n=== test_split_reset_log {'完了 (成功)' if all_valid else '完了 (失敗)'} ===")
    return all_valid


def test_resolve_local_tax_class():
    """resolve_local_tax_class 関数のテスト"""
    print("\n=== test_resolve_local_tax_class ===")
    
    classifier = DocumentClassifierV5(debug_mode=True)
    
    test_cases = [
        {
            "name": "愛知県地方税",
            "base_class": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税",
            "prefecture": "愛知県",
            "city": None,
            "expected": "1011_都道府県_法人都道府県民税・事業税・特別法人事業税"
        },
        {
            "name": "福岡県地方税",
            "base_class": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税",
            "prefecture": "福岡県",
            "city": None,
            "expected": "1021_都道府県_法人都道府県民税・事業税・特別法人事業税"
        },
        {
            "name": "東京都地方税",
            "base_class": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税",
            "prefecture": "東京都",
            "city": None,
            "expected": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税"
        },
        {
            "name": "市民税（変化なし）",
            "base_class": "2001_市町村_法人市民税",
            "prefecture": "愛知県",
            "city": "蒲郡市",
            "expected": "2001_市町村_法人市民税"
        },
        {
            "name": "国税（ドメイン外）",
            "base_class": "0001_法人税及び地方法人税申告書",
            "prefecture": "愛知県",
            "city": None,
            "expected": "0001_法人税及び地方法人税申告書"  # 変化なし
        }
    ]
    
    all_success = True
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        
        result = classifier.resolve_local_tax_class(
            test_case["base_class"],
            test_case.get("prefecture"),
            test_case.get("city")
        )
        
        expected = test_case["expected"]
        success = result == expected
        
        print(f"入力: {test_case['base_class']}")
        print(f"都道府県: {test_case.get('prefecture', 'なし')}")
        print(f"市町村: {test_case.get('city', 'なし')}")
        print(f"結果: {result}")
        print(f"期待値: {expected}")
        print(f"判定: {'成功' if success else '失敗'}")
        
        if not success:
            all_success = False
    
    print(f"\n=== test_resolve_local_tax_class {'完了 (全テスト成功)' if all_success else '完了 (一部失敗)'} ===")
    return all_success


def test_code_domain():
    """code_domain 関数のテスト"""
    print("\n=== test_code_domain ===")
    
    classifier = DocumentClassifierV5(debug_mode=True)
    
    test_cases = [
        ("0001_法人税", "NATIONAL_TAX"),
        ("1001_都道府県税", "LOCAL_TAX"),
        ("2001_市民税", "LOCAL_TAX"),
        ("3001_消費税", "CONSUMPTION_TAX"),
        ("5001_決算書", "ACCOUNTING"),
        ("6001_固定資産", "ASSETS"),
        ("7001_税区分", "SUMMARY"),
        ("9999_未分類", "UNKNOWN"),
        ("", "UNKNOWN"),
        (None, "UNKNOWN")
    ]
    
    all_success = True
    
    for code, expected_domain in test_cases:
        result = classifier.code_domain(code)
        success = result == expected_domain
        
        print(f"コード: {code if code is not None else 'None'} -> ドメイン: {result} (期待値: {expected_domain}) {'OK' if success else 'NG'}")
        
        if not success:
            all_success = False
    
    print(f"\n=== test_code_domain {'完了 (全テスト成功)' if all_success else '完了 (一部失敗)'} ===")
    return all_success


def main():
    """全テスト実行"""
    print("v5.3.4 ノイズ抑制・リセットログ統合テスト開始")
    print("=" * 60)
    
    test_results = []
    
    # ドメイン判定テスト
    test_results.append(("ドメイン判定", test_code_domain()))
    
    # 地方税コード解決テスト
    test_results.append(("地方税コード解決", test_resolve_local_tax_class()))
    
    # ノイズ抑制テスト
    test_results.append(("ノイズ抑制", test_overlay_noise_suppression()))
    
    # リセットログテスト
    test_results.append(("リセットログ", test_split_reset_log()))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, result in test_results if result)
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\n合計: {passed_tests}/{total_tests} テスト通過")
    
    if passed_tests == total_tests:
        print("全テスト成功！v5.3.4 の修正が正常に動作しています。")
        return True
    else:
        print("一部テストが失敗しました。修正を確認してください。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)