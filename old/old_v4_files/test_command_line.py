#!/usr/bin/env python3
"""
v5.0システム コマンドラインテスト
実際のファイル処理をシミュレート
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5
import fitz  # PyMuPDF for PDF processing

def test_file_processing():
    """ファイル処理のテスト"""
    print("=== v5.0システム ファイル処理テスト ===")
    print()
    
    classifier = DocumentClassifierV5(debug_mode=False)
    
    # テスト用ファイル
    test_file = "test_data/sample_corp_tax_notification.txt"
    
    if not os.path.exists(test_file):
        print(f"テストファイルが見つかりません: {test_file}")
        return False
    
    # ファイル読み取り
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = "3_国税.pdf"  # 元のファイル名をシミュレート
    
    print(f"処理ファイル: {filename}")
    print("=" * 50)
    
    # v5.0分類実行
    result = classifier.classify_document_v5(content, filename)
    
    # 結果表示
    print(f"分類結果: {result.document_type}")
    print(f"判定方法: {result.classification_method}")  
    print(f"信頼度: {result.confidence:.2f}")
    print(f"マッチキーワード: {result.matched_keywords}")
    
    # 期待される新ファイル名
    expected_filename = "0003_受信通知_法人税.pdf"
    actual_filename = f"{result.document_type}.pdf"
    
    print(f"\n元ファイル名: {filename}")
    print(f"新ファイル名: {actual_filename}")
    print(f"期待ファイル名: {expected_filename}")
    
    success = actual_filename == expected_filename
    status = "[SUCCESS]" if success else "[FAILED]"
    print(f"リネーム結果: {status}")
    
    if success:
        print("\nv5.0システムが正常に動作しています！")
        print("実際のファイル処理で期待通りの結果が得られました。")
    else:
        print(f"\n期待値と異なる結果です")
    
    return success

def test_multiple_cases():
    """複数パターンのテスト"""
    print("\n" + "=" * 60)
    print("複数パターン処理テスト")
    print("=" * 60)
    
    classifier = DocumentClassifierV5(debug_mode=False)
    
    test_cases = [
        {
            "name": "法人税受信通知",
            "filename": "3_国税.pdf",
            "content": """メール詳細 種目 法人税及び地方法人税申告書 受付番号 20250731185710521215""",
            "expected": "0003_受信通知_法人税.pdf"
        },
        {
            "name": "消費税納付情報", 
            "filename": "2_国税.pdf",
            "content": """メール詳細（納付区分番号通知） 税目 消費税及地方消費税 申告区分 確定申告""",
            "expected": "3004_納付情報_消費税.pdf"
        },
        {
            "name": "従来の申告書",
            "filename": "01_内国法人の確定申告(青色)_メトロノーム株式会社.pdf", 
            "content": """内国法人の確定申告(青色) 法人税及び地方法人税申告書 差引確定法人税額 236,500円""",
            "expected": "0001_法人税及び地方法人税申告書.pdf"
        }
    ]
    
    success_count = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[TEST {i}] {case['name']}")
        print(f"入力: {case['filename']}")
        
        result = classifier.classify_document_v5(case['content'], case['filename'])
        actual = f"{result.document_type}.pdf"
        
        success = actual == case['expected']
        status = "[SUCCESS]" if success else "[FAILED]"
        
        print(f"結果: {actual}")
        print(f"期待: {case['expected']}")
        print(f"ステータス: {status}")
        
        if success:
            success_count += 1
    
    print(f"\n[SUMMARY] 成功: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
    
    return success_count == len(test_cases)

if __name__ == "__main__":
    # 単一ファイルテスト
    single_success = test_file_processing()
    
    # 複数パターンテスト  
    multiple_success = test_multiple_cases()
    
    print("\n" + "=" * 60)
    if single_success and multiple_success:
        print("v5.0システムの準備完了！本格運用が可能です。")
    else:
        print("一部のテストで問題が発生しました。")
    print("=" * 60)