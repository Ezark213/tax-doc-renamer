#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詳細ログ機能テストスクリプト
"""

import sys
import os
import io

# Windows環境でのUTF-8出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# パスにコアモジュールを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification import DocumentClassifier

def test_classification_logging():
    """分類ログのテスト"""
    print("詳細ログ機能テスト開始\n")
    
    # デバッグモード有効で分類器を初期化
    classifier = DocumentClassifier(debug_mode=True)
    
    # テストケース1: 法人税申告書
    print("=" * 60)
    print("テストケース1: 法人税申告書")
    print("=" * 60)
    
    test_text1 = """
    法人税及び地方法人税申告書
    内国法人の確定申告（青色）
    事業年度分の法人税申告書
    """
    
    test_filename1 = "内国法人の確定申告_2508.pdf"
    
    result1 = classifier.classify_document(test_text1, test_filename1)
    
    print(f"\n最終判定結果:")
    print(f"書類種別: {result1.document_type}")
    print(f"信頼度: {result1.confidence:.2f}")
    print(f"マッチキーワード: {result1.matched_keywords}")
    
    # テストケース2: 消費税申告書
    print("\n" + "=" * 60)
    print("テストケース2: 消費税申告書")
    print("=" * 60)
    
    test_text2 = """
    消費税及び地方消費税申告書
    消費税申告（一般・法人）
    """
    
    test_filename2 = "消費税及び地方消費税申告_2508.pdf"
    
    result2 = classifier.classify_document(test_text2, test_filename2)
    
    print(f"\n最終判定結果:")
    print(f"書類種別: {result2.document_type}")
    print(f"信頼度: {result2.confidence:.2f}")
    print(f"マッチキーワード: {result2.matched_keywords}")
    
    # テストケース3: 添付資料（混同テスト）
    print("\n" + "=" * 60)
    print("テストケース3: 添付資料（混同しやすいケース）")
    print("=" * 60)
    
    test_text3 = """
    イメージ添付書類（法人税申告）
    添付資料
    内国法人
    """
    
    test_filename3 = "イメージ添付書類_法人税_2508.pdf"
    
    result3 = classifier.classify_document(test_text3, test_filename3)
    
    print(f"\n最終判定結果:")
    print(f"書類種別: {result3.document_type}")
    print(f"信頼度: {result3.confidence:.2f}")
    print(f"マッチキーワード: {result3.matched_keywords}")
    
    # テストケース4: 勘定科目別税区分集計表 vs 税区分集計表
    print("\n" + "=" * 60)
    print("テストケース4: 税区分集計表（判定精度テスト）")
    print("=" * 60)
    
    test_text4 = """
    勘定科目別税区分集計表
    科目別税区分
    """
    
    test_filename4 = "勘定科目別税区分集計表_2508.pdf"
    
    result4 = classifier.classify_document(test_text4, test_filename4)
    
    print(f"\n最終判定結果:")
    print(f"書類種別: {result4.document_type}")
    print(f"信頼度: {result4.confidence:.2f}")
    print(f"マッチキーワード: {result4.matched_keywords}")

    # テストケース5: 都道府県申告書（新機能テスト）
    print("\n" + "=" * 60)
    print("テストケース5: 都道府県申告書（特別判定テスト）")
    print("=" * 60)
    
    test_text5 = """
    事業税
    特別法人事業税
    年400万円以下
    申告書
    """
    
    test_filename5 = "メトロノーム　株式会社_福岡県西福岡県税事務所_250731.pdf"
    
    result5 = classifier.classify_with_municipality_info(test_text5, test_filename5, 1011, None)
    
    print(f"\n最終判定結果:")
    print(f"書類種別: {result5.document_type}")
    print(f"信頼度: {result5.confidence:.2f}")
    print(f"マッチキーワード: {result5.matched_keywords}")
    print(f"判定方法: {result5.classification_method}")
    
    print("\n" + "=" * 60)
    print("詳細ログ機能テスト完了")
    print("=" * 60)

if __name__ == "__main__":
    test_classification_logging()