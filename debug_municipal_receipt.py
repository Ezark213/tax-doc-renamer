#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市町村受信通知番号生成デバッグテスト
"""

import os
import sys

# 現在のディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fukuoka_receipt_debug():
    """福岡市受信通知のデバッグテスト"""
    print("\n" + "="*60)
    print("福岡市受信通知番号デバッグテスト")
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
        print(f"[DEBUG] セット設定: {test_sets}")

        # 福岡市のテストケース
        test_text = "福岡県福岡市 地方税受信通知（市町村）"
        test_filename = "受信通知_福岡県福岡市.pdf"

        print(f"[DEBUG] テストテキスト: {test_text}")
        print(f"[DEBUG] テストファイル名: {test_filename}")

        # OCRテキスト抽出テスト
        detected_prefecture, detected_city = classifier._extract_municipality_from_receipt_text(test_text, test_filename)
        print(f"[DEBUG] 抽出結果: 都道府県={detected_prefecture}, 市町村={detected_city}")

        if detected_prefecture and detected_city:
            # 汎用Tokyo skip関数を直接テスト
            try:
                from helpers.seq_policy import generate_receipt_number_generic
                target_info = {'prefecture': detected_prefecture, 'city': detected_city}
                receipt_code = generate_receipt_number_generic("municipality_receipt", target_info, test_sets)
                print(f"[DEBUG] 汎用関数結果: {receipt_code}")

                expected_code = f"{receipt_code}_受信通知"
                print(f"[DEBUG] 期待結果: {expected_code}")
            except Exception as e:
                print(f"[ERROR] 汎用関数エラー: {e}")
        else:
            print("[ERROR] OCRテキストからの抽出に失敗")

        # 実際の分類テスト
        result = classifier.classify_document_v5(test_text, test_filename, "2508")
        print(f"[DEBUG] 実際の分類結果: {result.document_type}")

        return True

    except Exception as e:
        print(f"[ERROR] テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_fukuoka_receipt_debug()