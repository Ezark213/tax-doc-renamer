#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本表PDF金額抽出テストスクリプト
"""
import fitz
import re
import glob
import os

def test_main_pdf_extraction(folder_path):
    """フォルダ内の本表PDFから金額抽出をテスト"""
    print(f"=== テスト対象フォルダ: {folder_path} ===\n")

    # 01_で始まるPDFファイルを探す
    pattern = os.path.join(folder_path, "01_*.pdf")
    pdf_files = glob.glob(pattern)

    if not pdf_files:
        print("01_で始まるPDFが見つかりません")
        return

    for pdf_path in pdf_files[:2]:  # 最初の2ファイルのみ
        print(f"\n{'='*60}")
        print(f"ファイル: {os.path.basename(pdf_path)}")
        print('='*60)

        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            text = page.get_text()
            doc.close()

            print(f"\n--- 抽出されたテキスト（最初の1000文字）---")
            print(text[:1000])
            print(f"\n--- テキスト（続き）---")
            print(text[1000:2000])
            print(f"\n--- テキスト終了 ---\n")

            # 金額抽出パターンをテスト
            patterns = [
                (r'納付税額[^\d]*?([\d,]+)', '納付税額'),
                (r'合計[額金][^\d]*?([\d,]+)', '合計額/合計金'),
                (r'納付すべき[税額]*[^\d]*?([\d,]+)', '納付すべき税額'),
                (r'本税[^\d]*?([\d,]+)', '本税'),
                (r'差引[税額納付額]*[^\d]*?([\d,]+)', '差引'),
                (r'合計金額[^\d]*?([\d,]+)', '合計金額'),
                (r'納付金額[^\d]*?([\d,]+)', '納付金額'),
            ]

            print("金額抽出テスト:")
            for pattern, label in patterns:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    amount_str = match.group(1).replace(',', '').replace(' ', '')
                    try:
                        amount = int(amount_str)
                        print(f"  [OK] {label}: {amount:,}円")
                    except ValueError:
                        print(f"  [NG] {label}: 数値変換失敗 ({match.group(1)})")
                else:
                    print(f"  [ - ] {label}: マッチなし")

        except Exception as e:
            print(f"エラー: {e}")

if __name__ == "__main__":
    # Ｘ－Ｒｅｇｕｌａｔｉｏｎのフォルダを探す
    base_folder = r"C:\Users\mayum\Desktop\源泉税"

    # 報酬・料金等のフォルダ
    folder1 = os.path.join(base_folder, "*報酬・料金等*0413K0063*")
    folders = glob.glob(folder1)

    if folders:
        print(f"報酬・料金等フォルダをテスト:\n")
        test_main_pdf_extraction(folders[0])

    # 給与所得等のフォルダ
    folder2 = os.path.join(base_folder, "*給与所得*0413K0063*")
    folders2 = glob.glob(folder2)

    if folders2:
        print(f"\n\n給与所得等フォルダをテスト:\n")
        test_main_pdf_extraction(folders2[0])
