#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市町村連番システムのテスト
「当該市町村内」「市町村民税の特定寄附金」が法人市民税として正しく連番化されるかテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def test_municipality_numbering():
    """市町村連番システムのテスト"""
    classifier = DocumentClassifierV5(debug_mode=True)
    
    print("=== 市町村連番システムテスト ===")
    
    # テストケース1: 蒲郡市（セット2）
    test_text_1 = "当該市町村内 市町村民税の特定寄附金 蒲郡市役所"
    result_1 = classifier.classify_with_municipality_info_v5(test_text_1, "gamagori_test.pdf", None, 2001)
    print(f"\n=== テスト1: 蒲郡市（セット2）===")
    print(f"結果: {result_1.document_type}")
    print(f"信頼度: {result_1.confidence:.3f}")
    print(f"マッチキーワード: {result_1.matched_keywords}")
    
    # テストケース2: 福岡市（セット3）
    test_text_2 = "当該市町村内 市町村民税の特定寄附金 福岡市役所"
    result_2 = classifier.classify_with_municipality_info_v5(test_text_2, "fukuoka_test.pdf", None, 2011)
    print(f"\n=== テスト2: 福岡市（セット3）===")
    print(f"結果: {result_2.document_type}")
    print(f"信頼度: {result_2.confidence:.3f}")
    print(f"マッチキーワード: {result_2.matched_keywords}")
    
    # テストケース3: 東京都は市町村なしなのでテストしない
    
    print(f"\n=== 連番確認 ===")
    print("期待値:")
    print("- 蒲郡市（セット2、municipality_code=2001）→ 2001_愛知県蒲郡市_法人市民税")
    print("- 福岡市（セット3、municipality_code=2011）→ 2011_福岡県福岡市_法人市民税")

if __name__ == "__main__":
    test_municipality_numbering()