#!/usr/bin/env python3
"""
金額抽出テストスクリプト
"""
import fitz
import re

def test_amount_extraction(pdf_path):
    """PDFから金額抽出をテスト"""
    print(f"=== テスト対象PDF: {pdf_path} ===\n")

    try:
        doc = fitz.open(pdf_path)
        print(f"総ページ数: {doc.page_count}\n")

        # 最初の3ページをテスト
        for page_num in range(min(3, doc.page_count)):
            print(f"\n{'='*60}")
            print(f"ページ {page_num + 1}")
            print('='*60)

            page = doc[page_num]
            text = page.get_text()

            print(f"\n--- 抽出されたテキスト（全文）---")
            print(text)
            print(f"\n--- テキスト終了 ---\n")

            # 金額抽出パターンをテスト
            patterns = [
                (r'納付すべき税額[^\d]*?([\d,]+)', '納付すべき税額'),
                (r'本税[^\d]*?([\d,]+)', '本税'),
                (r'合計[額金][^\d]*?([\d,]+)', '合計額'),
                (r'納付税額[^\d]*?([\d,]+)', '納付税額'),
                (r'差引[税額納付額]*[^\d]*?([\d,]+)', '差引'),
            ]

            print("金額抽出テスト:")
            found_any = False
            for pattern, label in patterns:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    amount_str = match.group(1).replace(',', '').replace(' ', '')
                    try:
                        amount = int(amount_str)
                        print(f"  ✓ {label}: {amount:,}円")
                        found_any = True
                    except ValueError:
                        print(f"  ✗ {label}: マッチしたが数値変換失敗 ({match.group(1)})")
                else:
                    print(f"  - {label}: マッチなし")

            if not found_any:
                print("\n  ⚠ どのパターンでも金額を抽出できませんでした")

        doc.close()

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pdf_path = r"C:\Users\mayum\Desktop\源泉元データ\受信通知.pdf"
    test_amount_extraction(pdf_path)
