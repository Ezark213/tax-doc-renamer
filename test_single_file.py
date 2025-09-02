#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
単一ファイルテスト - ステートレス処理デバッグ用
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.classification_v5 import DocumentClassifierV5

def test_single_file():
    """単一ファイルでステートレス処理をテスト"""
    classifier = DocumentClassifierV5()
    
    # セット設定
    set_settings = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"},
        3: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    # テスト用のテキストとファイル名（実際のログから）
    text = """電子申告完了済
受付日時：2025/07/31 18:46:00
受付番号：R1-2025-19554045
6 0 1 1 0 0 1 1 2 8 6 0 0
福岡市長
東京都港区港南２丁目１６番４号品川グランドセントラルタワー８階
福岡県福岡市中央区草香江２－１１－３０
080-4914-3900
フィットネス用品の提供
メトロノームカブシキカイシャ
メトロノーム株式会社"""
    filename = "メトロノーム　株式会社_福岡市_250731.pdf のコピー.pdf"
    
    print("=== 単一ファイルテスト ===")
    print(f"ファイル名: {filename}")
    print(f"テキスト: {text}")
    print(f"セット設定: {set_settings}")
    print()
    
    # 基本分類をテスト
    base_result = classifier.classify_document_v5(text, filename)
    print(f"基本分類結果: {base_result.document_type}")
    print()
    
    # 完全統合テスト（正規化処理付き）
    try:
        final_result = classifier.classify_with_municipality_info_v5(
            text, filename,
            prefecture_code=None, municipality_code=None,
            municipality_sets=set_settings
        )
        print(f"統合処理結果: {final_result.document_type}")
        
        if final_result.document_type != base_result.document_type:
            print(f"[SUCCESS] 統合処理により変換: {base_result.document_type} → {final_result.document_type}")
        else:
            print(f"[INFO] 統合処理でも変換なし")
            
    except Exception as e:
        print(f"[ERROR] 統合処理エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # 正規化処理を直接テスト
    print("\n--- 正規化処理の直接テスト ---")
    try:
        code, final_label, set_id = classifier.normalize_classification(
            text, filename, base_result.document_type, set_settings
        )
        print(f"正規化処理結果: code={code}, label={final_label}, set_id={set_id}")
        
    except Exception as e:
        print(f"[ERROR] 正規化処理エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # ステートレス処理を直接テスト
    print("\n--- ステートレス処理の直接テスト ---")
    try:
        final_result = classifier._resolve_document_label_stateless(
            base_result.document_type,
            text,
            filename,
            set_settings
        )
        print(f"ステートレス処理結果: {final_result}")
        
        if final_result != base_result.document_type:
            print(f"[SUCCESS] ラベルが変換されました: {base_result.document_type} → {final_result}")
        else:
            print(f"[INFO] ラベル変換なし")
            
    except Exception as e:
        print(f"[ERROR] ステートレス処理エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_file()