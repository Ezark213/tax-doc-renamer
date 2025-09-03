#!/usr/bin/env python3
"""
分類結果修正のテスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent))

from core.classification_v5 import DocumentClassifierV5

def test_classification_fix():
    """分類結果のテスト"""
    print("=== 分類結果修正テスト ===")
    
    # 分類器初期化
    classifier = DocumentClassifierV5(debug_mode=True)
    
    # テストケース1: 消費税申告書
    test_text1 = "電子申告等利用届出書 受付日時：2025/07/31 18:57:12 受付番号：20250731185712915418 東京都港区港南二丁目16番4号 品川グランドセントラルタワー8階 消費税及び地方消費税申告書"
    test_filename1 = "01_消費税及び地方消費税申告書(一般・法人)_テストファイル.pdf"
    
    # 自治体セット設定（既存の設定を模倣）
    municipality_sets = {
        1: {'prefecture': '東京都', 'city': ''},
        2: {'prefecture': '愛知県', 'city': '蒲郡市'},
        3: {'prefecture': '福岡県', 'city': '福岡市'}
    }
    
    print(f"\n--- テストケース1: 消費税申告書 ---")
    print(f"テキスト（一部）: {test_text1[:100]}...")
    print(f"ファイル名: {test_filename1}")
    
    # 分類実行
    result1 = classifier.classify_with_municipality_info_v5(
        test_text1, test_filename1, municipality_sets=municipality_sets
    )
    
    print(f"\n【結果】")
    print(f"document_type: {result1.document_type}")
    print(f"original_doc_type_code: {getattr(result1, 'original_doc_type_code', 'None')}")
    print(f"confidence: {result1.confidence}")
    print(f"classification_method: {result1.classification_method}")
    print(f"matched_keywords: {result1.matched_keywords}")
    
    # テストケース2: 法人税申告書
    test_text2 = "電子申告等利用届出書 受付日時：2025/07/31 18:57:10 受付番号：20250731185710521215 東京都港区港南二丁目16番4号 法人税及び地方法人税申告書"
    test_filename2 = "01_法人税及び地方法人税申告書(青)_テストファイル.pdf"
    
    print(f"\n--- テストケース2: 法人税申告書 ---")
    print(f"テキスト（一部）: {test_text2[:100]}...")
    print(f"ファイル名: {test_filename2}")
    
    result2 = classifier.classify_with_municipality_info_v5(
        test_text2, test_filename2, municipality_sets=municipality_sets
    )
    
    print(f"\n【結果】")
    print(f"document_type: {result2.document_type}")
    print(f"original_doc_type_code: {getattr(result2, 'original_doc_type_code', 'None')}")
    print(f"confidence: {result2.confidence}")
    print(f"classification_method: {result2.classification_method}")
    print(f"matched_keywords: {result2.matched_keywords}")
    
    # 修正の成功判定
    success = True
    
    # テスト1: 消費税申告書が正しく認識されているか
    if hasattr(result1, 'original_doc_type_code') and result1.original_doc_type_code:
        if result1.original_doc_type_code.startswith('3001'):
            print(f"\n✅ テスト1成功: 消費税申告書の元コード保存 ({result1.original_doc_type_code})")
        else:
            print(f"\n❌ テスト1失敗: 消費税申告書の元コード不正 ({result1.original_doc_type_code})")
            success = False
    else:
        print(f"\n❌ テスト1失敗: original_doc_type_code が設定されていない")
        success = False
    
    # テスト2: 法人税申告書が正しく認識されているか  
    if hasattr(result2, 'original_doc_type_code') and result2.original_doc_type_code:
        if result2.original_doc_type_code.startswith('0001'):
            print(f"✅ テスト2成功: 法人税申告書の元コード保存 ({result2.original_doc_type_code})")
        else:
            print(f"❌ テスト2失敗: 法人税申告書の元コード不正 ({result2.original_doc_type_code})")
            success = False
    else:
        print(f"❌ テスト2失敗: original_doc_type_code が設定されていない")
        success = False
    
    if success:
        print(f"\n🎉 修正テスト成功！元の分類コードが正しく保存されています")
    else:
        print(f"\n💥 修正テスト失敗：元の分類コードの保存に問題があります")
    
    return success

if __name__ == "__main__":
    test_classification_fix()