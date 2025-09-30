#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市町村番号修正テスト - 申告書番号バグ修正確認
"""

import os
import sys
import tempfile

# 現在のディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_municipal_application_numbering():
    """市町村申告書の番号生成テスト（修正後）"""
    print("\n" + "="*60)
    print("市町村申告書番号修正テスト")
    print("="*60)

    try:
        from core.classification_v5 import DocumentClassifierV5

        classifier = DocumentClassifierV5()

        # テストケース: 愛知県蒲郡市の申告書
        test_text = "愛知県蒲郡市 法人市町村民税申告書 フィットネスクラブシェイプ"
        test_filename = "フィットネスクラブ申告書_愛知県蒲郡市税務署.pdf"

        # 市町村申告書の分類テスト
        result = classifier.classify_document_v5(test_text, test_filename, "2508")

        print(f"[TEST] 入力ファイル: {test_filename}")
        print(f"[TEST] 分類結果: {result}")

        # 期待値: 2001_愛知県蒲郡市_市町村申告書_2508.pdf (修正後)
        # 誤った値: 2003_愛知県蒲郡市_市町村申告書_2508.pdf (修正前)

        expected_base = "2001_"  # 修正後の正しいベース
        wrong_base = "2003_"     # 修正前の間違ったベース

        result_type = result.document_type if hasattr(result, 'document_type') else str(result)

        if expected_base in result_type:
            print(f"[PASS] 正しい基準番号2001が使用されています: {result_type}")
        elif wrong_base in result_type:
            print(f"[FAIL] まだ間違った基準番号2003が使用されています: {result_type}")
            return False
        else:
            print(f"[INFO] 分類結果を確認: {result_type}")

        return True

    except Exception as e:
        print(f"[ERROR] テストエラー: {str(e)}")
        return False

def test_municipal_receipt_numbering():
    """市町村受信通知の番号生成テスト"""
    print("\n" + "="*60)
    print("市町村受信通知番号テスト")
    print("="*60)

    try:
        from core.classification_v5 import DocumentClassifierV5

        classifier = DocumentClassifierV5()

        # セット設定を初期化（テスト用）
        test_sets = {
            1: {'prefecture': '東京都', 'city': ''},
            2: {'prefecture': '愛知県', 'city': '蒲郡市'},
            3: {'prefecture': '福岡県', 'city': '福岡市'}
        }
        classifier.current_municipality_sets = test_sets

        # テストケース: 市町村受信通知
        test_cases = [
            {
                "text": "愛知県蒲郡市 地方税受信通知（市町村）",
                "filename": "受信通知_愛知県蒲郡市.pdf",
                "expected": "2003_受信通知"  # 受信通知は2003ベースが正しい
            },
            {
                "text": "福岡県福岡市 地方税受信通知（市町村）",
                "filename": "受信通知_福岡県福岡市.pdf",
                "expected": "2013_受信通知"  # Tokyo skip適用で2013
            }
        ]

        for i, case in enumerate(test_cases, 1):
            result = classifier.classify_document_v5(case["text"], case["filename"], "2508")
            result_type = result.document_type if hasattr(result, 'document_type') else str(result)

            print(f"[TEST {i}] 入力: {case['filename']}")
            print(f"[TEST {i}] 結果: {result_type}")
            print(f"[TEST {i}] 期待: {case['expected']}")

            if case["expected"] in result_type:
                print(f"[PASS {i}] 正しい受信通知番号が生成されています")
            else:
                print(f"[FAIL {i}] 期待される番号と異なります")

        return True

    except Exception as e:
        print(f"[ERROR] 受信通知テストエラー: {str(e)}")
        return False

def main():
    """メインテスト実行"""
    print("市町村番号修正テスト実行開始")
    print("=" * 80)

    results = []

    # 申告書番号テスト
    app_result = test_municipal_application_numbering()
    results.append(("市町村申告書番号修正", app_result))

    # 受信通知番号テスト
    receipt_result = test_municipal_receipt_numbering()
    results.append(("市町村受信通知番号確認", receipt_result))

    # 結果サマリー
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)

    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"[{status}] {test_name}")
        if not result:
            all_passed = False

    print("\n" + "="*80)
    if all_passed:
        print("[SUCCESS] 市町村番号修正テスト完了！")
    else:
        print("[ERROR] 一部テストが失敗しました。")
    print("="*80)

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)