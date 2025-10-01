#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\mayum\tax-doc-renamer')

from core.ocr_engine import CompanyNameMatcher

matcher = CompanyNameMatcher()

# テスト1: 報酬・料金等PDF
print("=== テスト1: 報酬・料金等PDF ===")
pdf1 = r"C:\Users\mayum\Desktop\源泉税\2511_01_報酬・料金等の所得税徴収高計算書_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ\01_報酬・料金等の所得税徴収高計算書_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ.pdf"
amount1 = matcher.extract_amount_from_main_pdf(pdf1)
print(f"抽出結果: {amount1}")
print()

# テスト2: 給与所得等PDF
print("=== テスト2: 給与所得等PDF ===")
pdf2 = r"C:\Users\mayum\Desktop\源泉税\2511_01_給与所得・退職所得等の所得税徴収高計算書(一般)_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ\01_給与所得・退職所得等の所得税徴収高計算書(一般)_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ.pdf"
amount2 = matcher.extract_amount_from_main_pdf(pdf2)
print(f"抽出結果: {amount2}")
print()

# テスト3: 受信通知（ページ2 - Ｘ－Ｒｅｇｕｌａｔｉｏｎ）
print("=== テスト3: 受信通知（Ｘ－Ｒｅｇｕｌａｔｉｏｎ） ===")
receipt_pdf = r"C:\Users\mayum\Desktop\源泉元データ\受信通知.pdf"
amount3 = matcher.extract_amount_from_receipt(receipt_pdf, 1)  # ページ2 = index 1
print(f"抽出結果: {amount3}")
