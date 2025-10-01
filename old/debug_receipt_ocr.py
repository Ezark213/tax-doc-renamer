#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受信通知OCRデバッグスクリプト
実際のPDFでの動作確認・問題特定
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
from core.ocr_engine import CompanyNameMatcher
import fitz
from PIL import Image
import pytesseract

def debug_receipt_pdf(pdf_path):
    """受信通知PDFをデバッグ"""

    print("=" * 80)
    print(f"受信通知PDFデバッグ: {pdf_path}")
    print("=" * 80)

    if not os.path.exists(pdf_path):
        print(f"ERROR: PDFファイルが見つかりません: {pdf_path}")
        return

    # PDFを開く
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"\n📄 総ページ数: {total_pages}")
    print("=" * 80)

    matcher = CompanyNameMatcher()

    # 各ページを分析
    for page_num in range(total_pages):
        print(f"\n{'='*80}")
        print(f"🔍 ページ {page_num + 1}/{total_pages}")
        print(f"{'='*80}")

        page = doc[page_num]
        page_rect = page.rect

        print(f"\n📐 ページサイズ: {page_rect.width:.1f} x {page_rect.height:.1f}")

        # OCR抽出範囲の表示
        crop_rect = fitz.Rect(
            page_rect.width * 0.30,
            page_rect.height * 0.15,
            page_rect.width * 0.70,
            page_rect.height * 0.65
        )

        print(f"📍 OCR抽出範囲:")
        print(f"   左端: {crop_rect.x0:.1f} ({crop_rect.x0/page_rect.width*100:.1f}%)")
        print(f"   上端: {crop_rect.y0:.1f} ({crop_rect.y0/page_rect.height*100:.1f}%)")
        print(f"   右端: {crop_rect.x1:.1f} ({crop_rect.x1/page_rect.width*100:.1f}%)")
        print(f"   下端: {crop_rect.y1:.1f} ({crop_rect.y1/page_rect.height*100:.1f}%)")

        # 画像化してOCR実行
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat, clip=crop_rect)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # 画像前処理
        from core.ocr_engine import OCREngine
        ocr_engine = OCREngine()
        img_processed = ocr_engine._preprocess_image_for_ocr(img)

        # OCR実行
        ocr_config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
        ocr_text = pytesseract.image_to_string(img_processed, lang='jpn', config=ocr_config)

        print(f"\n📝 OCR抽出テキスト（全文）:")
        print("-" * 80)
        print(ocr_text[:500])  # 最初の500文字
        if len(ocr_text) > 500:
            print(f"... （残り {len(ocr_text) - 500} 文字）")
        print("-" * 80)

        # 正規表現パターンマッチング試行
        import re
        company_patterns = [
            (r'([^\s]{2,30}?)(?:様|殿|御中)', "様・殿・御中パターン"),
            (r'([^\s]{2,30}?)(?:\s*納税者)', "納税者パターン"),
            (r'([^\s]{2,30}?)(?:\s*宛)', "宛パターン"),
        ]

        print(f"\n🔎 正規表現マッチング試行:")
        matched_company = None

        for pattern, pattern_name in company_patterns:
            matches = re.findall(pattern, ocr_text)
            print(f"   {pattern_name}: {len(matches)}件マッチ")
            if matches:
                print(f"      → {matches[:3]}")  # 最初の3件
                if not matched_company:
                    matched_company = matches[0].strip()

        # CompanyNameMatcherを使用して抽出
        print(f"\n🎯 CompanyNameMatcher.extract_company_name_from_receipt() 結果:")
        extracted_company = matcher.extract_company_name_from_receipt(pdf_path, page_num)

        if extracted_company:
            print(f"   ✅ 成功: {extracted_company}")
        else:
            print(f"   ❌ 失敗: 会社名を抽出できませんでした")

        # 正規化テスト
        if extracted_company:
            normalized = matcher.normalize_company_name(extracted_company)
            print(f"\n🔄 正規化結果:")
            print(f"   元の会社名: {extracted_company}")
            print(f"   正規化後:   {normalized}")

        print(f"\n{'='*80}")

    doc.close()

    print(f"\n{'='*80}")
    print(f"✅ デバッグ完了: {total_pages}ページ分析済み")
    print(f"{'='*80}")


def test_folder_matching():
    """フォルダマッチングテスト"""

    print("\n" + "=" * 80)
    print("🔗 フォルダマッチングテスト")
    print("=" * 80)

    # テスト用フォルダ名（実際の形式）
    folder_names = [
        "2511_01_給与所得・退職所得等の所得税徴収高計算書(一般)_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ",
        "2511_01_報酬・料金等の所得税徴収高計算書_0234T0060_株式会社ｄｅｅｃｌ",
        "2511_01_報酬・料金等の所得税徴収高計算書_0345N0033_株式会社ＮｏｒｔｈＷｉｎｇ",
    ]

    # テスト用会社名（受信通知から抽出されると想定）
    test_companies = [
        "株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ様",
        "株式会社ｄｅｅｃｌ 納税者",
        "ＮｏｒｔｈＷｉｎｇ御中",
        "存在しない会社",
    ]

    matcher = CompanyNameMatcher()

    for company in test_companies:
        print(f"\n🔍 テスト会社名: {company}")
        result = matcher.match_folder(company, folder_names, threshold=0.7)

        if result:
            matched_folder, score = result
            print(f"   ✅ マッチ成功")
            print(f"      フォルダ: {matched_folder}")
            print(f"      スコア: {score:.2f}")
        else:
            print(f"   ❌ マッチ失敗（閾値0.7以上のマッチなし）")


if __name__ == "__main__":
    # 受信通知PDFのパス
    receipt_pdf = "C:\\Users\\mayum\\Downloads\\受信通知.pdf"

    # 受信通知PDFのデバッグ
    debug_receipt_pdf(receipt_pdf)

    # フォルダマッチングテスト
    test_folder_matching()

    print("\n" + "=" * 80)
    print("✅ 全デバッグ完了")
    print("=" * 80)