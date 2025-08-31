#!/usr/bin/env python3
"""
エッジケース失敗の詳細デバッグ
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def debug_edge_case():
    """エッジケース失敗の詳細分析"""
    print("=== エッジケース失敗デバッグ ===")
    print()
    
    classifier = DocumentClassifierV5(debug_mode=True)
    
    # 問題のケース
    problem_case = {
        "name": "複数税目",
        "content": "法人税及び地方法人税申告書 消費税及び地方消費税申告書 内国法人",
        "expected": "0001_法人税及び地方法人税申告書"
    }
    
    print(f"テスト内容: {problem_case['content']}")
    print(f"期待値: {problem_case['expected']}")
    print("=" * 60)
    
    result = classifier.classify_document_v5(problem_case['content'], "debug_test.pdf")
    
    print(f"実際の結果: {result.document_type}")
    print(f"期待値: {problem_case['expected']}")
    print(f"マッチ: {'YES' if result.document_type == problem_case['expected'] else 'NO'}")
    print(f"信頼度: {result.confidence:.2f}")
    print(f"判定方法: {result.classification_method}")
    print(f"マッチキーワード: {result.matched_keywords}")
    
    # 個別にキーワードをテスト
    print("\n個別キーワードテスト:")
    print("-" * 30)
    
    individual_tests = [
        "法人税及び地方法人税申告書",
        "消費税及び地方消費税申告書", 
        "内国法人の確定申告",
        "法人税及び地方法人税申告書 内国法人"
    ]
    
    for i, test_content in enumerate(individual_tests, 1):
        result = classifier.classify_document_v5(test_content, f"individual_{i}.pdf")
        print(f"{i}. '{test_content}' -> {result.document_type}")

if __name__ == "__main__":
    debug_edge_case()