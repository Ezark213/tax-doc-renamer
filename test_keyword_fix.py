#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
キーワード修正のテスト
市長・村長・町長の除外と、当該市町村内・市町村民税の特定寄附金の優先キーワード化をテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def test_keyword_modifications():
    """修正されたキーワードのテスト"""
    classifier = DocumentClassifierV5(debug_mode=False)
    
    # テストケース: 市長関連のテキスト（除外されるべき）
    print("=== テスト1: 市長キーワードの除外テスト ===")
    test_text_1 = "市長 法人市民税 受付完了通知 申告受付完了"
    result_1 = classifier.classify_document_v5(test_text_1, "test_1.pdf")
    print(f"結果: {result_1.document_type}")
    print(f"信頼度: {result_1.confidence:.3f}")
    print(f"マッチキーワード: {result_1.matched_keywords}")
    
    # テストケース: 当該市町村内・市町村民税の特定寄附金（優先されるべき）
    print("\n=== テスト2: 優先キーワードテスト ===")
    test_text_2 = "当該市町村内 市町村民税の特定寄附金 申告受付完了通知"
    result_2 = classifier.classify_document_v5(test_text_2, "test_2.pdf")
    print(f"結果: {result_2.document_type}")
    print(f"信頼度: {result_2.confidence:.3f}")
    print(f"マッチキーワード: {result_2.matched_keywords}")
    
    # テストケース: 旧キーワード vs 新キーワード
    print("\n=== テスト3: 市役所は残存確認 ===")
    test_text_3 = "市役所 法人市民税 申告受付完了通知"
    result_3 = classifier.classify_document_v5(test_text_3, "test_3.pdf")
    print(f"結果: {result_3.document_type}")
    print(f"信頼度: {result_3.confidence:.3f}")
    print(f"マッチキーワード: {result_3.matched_keywords}")
    
    print("\n=== 修正確認完了 ===")

if __name__ == "__main__":
    test_keyword_modifications()