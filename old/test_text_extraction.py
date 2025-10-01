#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受信通知PDFのテキスト直接抽出テスト
画像OCRではなく、PDFからテキストを直接取得できるか確認
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz
import re

def test_direct_text_extraction(pdf_path):
    """PDFから直接テキストを抽出してテスト"""

    print("=" * 80)
    print("受信通知PDF - テキスト直接抽出テスト")
    print("=" * 80)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"\n総ページ数: {total_pages}\n")

    for page_num in range(min(3, total_pages)):  # 最初の3ページのみテスト
        print(f"\n{'='*80}")
        print(f"ページ {page_num + 1}")
        print(f"{'='*80}")

        page = doc[page_num]

        # テキストを直接抽出
        text = page.get_text()

        print(f"\n📝 抽出されたテキスト（最初の1000文字）:")
        print("-" * 80)
        print(text[:1000])
        print("-" * 80)

        # 会社名抽出パターン（改善版）
        company_patterns = [
            (r'(?:氏名又は名称|は名称)\s+(.+?)(?:\n|代表者|等氏名)', "フィールド名パターン"),
            (r'識別番号.+?\n(?:氏名又は名称|は名称)\s+(.+?)(?:\n)', "識別番号後パターン"),
        ]

        print(f"\n🔎 会社名抽出試行:")
        extracted_company = None

        for pattern, pattern_name in company_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            if matches:
                extracted_company = matches[0].strip()
                print(f"   ✅ {pattern_name}: {extracted_company}")
                break
            else:
                print(f"   ❌ {pattern_name}: マッチなし")

        if extracted_company:
            print(f"\n🎯 抽出成功: {extracted_company}")
        else:
            print(f"\n❌ 抽出失敗")

    doc.close()

    print(f"\n{'='*80}")
    print("テスト完了")
    print(f"{'='*80}")


if __name__ == "__main__":
    pdf_path = "C:\\Users\\mayum\\Downloads\\受信通知.pdf"
    test_direct_text_extraction(pdf_path)