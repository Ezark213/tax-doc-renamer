#!/usr/bin/env python3
"""
税務書類分類エンジン v4.0 修正版テストスクリプト
最優先キーワード判定のテスト
"""

import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification import DocumentClassifier

def test_highest_priority_keywords():
    """最優先キーワード判定テスト"""
    print("=== 税務書類分類エンジン v4.0 修正版テスト ===")
    print()
    
    # 分類エンジンの初期化
    classifier = DocumentClassifier(debug_mode=True)
    
    # テストケース
    test_cases = [
        {
            "name": "納付税額一覧表テスト",
            "text": "納付税額一覧表 2024年度",
            "filename": "納付税額一覧表.pdf",
            "expected": "0000_納付税額一覧表"
        },
        {
            "name": "総勘定元帳テスト",
            "text": "総勘定元帳 令和6年度",
            "filename": "総勘定元帳.pdf",
            "expected": "5002_総勘定元帳"
        },
        {
            "name": "少額減価償却資産明細表テスト",
            "text": "少額減価償却資産明細表",
            "filename": "少額減価償却資産明細表.pdf",
            "expected": "6003_少額減価償却資産明細表"
        },
        {
            "name": "一括償却資産明細表テスト",
            "text": "一括償却資産明細表",
            "filename": "一括償却資産明細表 のコピー.pdf",
            "expected": "6002_一括償却資産明細表"
        },
        {
            "name": "消費税申告書テスト",
            "text": "課税期間分の消費税及び地方消費税申告書",
            "filename": "01_消費税及び地方消費税申告(一般・法人)_メトロノーム株式会社.pdf",
            "expected": "3001_消費税及び地方消費税申告書"
        },
        {
            "name": "法人税申告書テスト",
            "text": "事業年度分の法人税申告書 内国法人の確定申告(青色)",
            "filename": "01_内国法人の確定申告(青色)_メトロノーム株式会社.pdf",
            "expected": "0001_法人税及び地方法人税申告書"
        },
    ]
    
    # テスト実行
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases):
        print(f"--- テスト {i+1}: {test_case['name']} ---")
        print(f"テキスト: {test_case['text']}")
        print(f"ファイル名: {test_case['filename']}")
        print(f"期待値: {test_case['expected']}")
        print()
        
        # 分類実行
        result = classifier.classify_document(test_case['text'], test_case['filename'])
        
        # 結果確認
        if result.document_type == test_case['expected']:
            print(f"✅ PASS: {result.document_type}")
            print(f"   信頼度: {result.confidence:.2f}")
            print(f"   分類方法: {result.classification_method}")
            print(f"   マッチキーワード: {result.matched_keywords}")
            passed += 1
        else:
            print(f"❌ FAIL: 期待値 {test_case['expected']} != 実際値 {result.document_type}")
            print(f"   信頼度: {result.confidence:.2f}")
            print(f"   分類方法: {result.classification_method}")
            print(f"   マッチキーワード: {result.matched_keywords}")
            failed += 1
        
        print()
    
    # 結果サマリー
    print("=== テスト結果サマリー ===")
    print(f"成功: {passed}件")
    print(f"失敗: {failed}件")
    print(f"成功率: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("🎉 全てのテストに成功しました！")
        return True
    else:
        print("⚠️  一部のテストに失敗しました。")
        return False

if __name__ == "__main__":
    success = test_highest_priority_keywords()
    sys.exit(0 if success else 1)