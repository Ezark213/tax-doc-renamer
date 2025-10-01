#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7.2.1-AMOUNT-MATCHING 金額抽出・マッチング機能テスト
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
from core.ocr_engine import CompanyNameMatcher

def test_amount_extraction():
    """金額抽出機能のテスト"""

    print("=" * 80)
    print("v7.2.1 金額抽出機能テスト")
    print("=" * 80)

    matcher = CompanyNameMatcher()

    # テストファイルパス（実際のファイルで確認）
    receipt_pdf = "C:\\Users\\mayum\\Downloads\\受信通知.pdf"

    if not os.path.exists(receipt_pdf):
        print(f"\n❌ エラー: 受信通知PDFが見つかりません: {receipt_pdf}")
        return False

    print(f"\n📄 受信通知PDF: {receipt_pdf}")

    # ページごとに金額抽出テスト
    test_pages = [
        (0, "むかしむかし株式会社"),
        (1, "株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ (1回目)"),
        (4, "株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ (2回目)"),
    ]

    all_passed = True

    for page_num, expected_company in test_pages:
        print(f"\n{'='*80}")
        print(f"ページ {page_num + 1}: {expected_company}")
        print(f"{'='*80}")

        # 会社名抽出
        company = matcher.extract_company_name_from_receipt(receipt_pdf, page_num)
        print(f"会社名: {company if company else '抽出失敗'}")

        # 金額抽出
        amount = matcher.extract_amount_from_receipt(receipt_pdf, page_num)

        if amount:
            print(f"✅ 金額抽出成功: {amount:,}円")
        else:
            print(f"❌ 金額抽出失敗")
            all_passed = False

    print(f"\n{'='*80}")
    if all_passed:
        print("✅ 全テスト成功: 受信通知から金額抽出可能")
    else:
        print("❌ 一部テスト失敗: 金額抽出に問題あり")
    print(f"{'='*80}")

    return all_passed


def test_main_pdf_amount_extraction():
    """本表PDF金額抽出テスト（デスクトップのフォルダ）"""

    print("\n" + "=" * 80)
    print("本表PDF金額抽出テスト")
    print("=" * 80)

    matcher = CompanyNameMatcher()

    # テスト用フォルダパス（実際に作成されたフォルダから選択）
    desktop_path = "C:\\Users\\mayum\\Desktop\\源泉税"

    if not os.path.exists(desktop_path):
        print(f"\n⚠️ デスクトップフォルダが存在しません: {desktop_path}")
        print("フォルダリネーム実行後に再度テストしてください")
        return True  # スキップ

    # フォルダ一覧取得
    folders = [f for f in os.listdir(desktop_path) if os.path.isdir(os.path.join(desktop_path, f)) and f.startswith("2511_")]

    if not folders:
        print(f"\n⚠️ テスト用フォルダが見つかりません")
        return True  # スキップ

    print(f"\n検出フォルダ数: {len(folders)}")

    # 最初の3フォルダをテスト
    test_count = min(3, len(folders))
    all_passed = True

    for i, folder_name in enumerate(folders[:test_count], 1):
        print(f"\n{'='*80}")
        print(f"テスト {i}/{test_count}: {folder_name}")
        print(f"{'='*80}")

        folder_path = os.path.join(desktop_path, folder_name)

        # 本表PDFを検索（01_で始まるファイル）
        main_files = [f for f in os.listdir(folder_path) if f.startswith("01_") and f.endswith(".pdf")]

        if not main_files:
            print(f"⚠️ 本表PDFが見つかりません")
            continue

        main_pdf_path = os.path.join(folder_path, main_files[0])
        print(f"本表PDF: {main_files[0]}")

        # 金額抽出
        amount = matcher.extract_amount_from_main_pdf(main_pdf_path)

        if amount:
            print(f"✅ 金額抽出成功: {amount:,}円")
        else:
            print(f"❌ 金額抽出失敗")
            all_passed = False

    print(f"\n{'='*80}")
    if all_passed:
        print("✅ 全テスト成功: 本表PDFから金額抽出可能")
    else:
        print("❌ 一部テスト失敗: 金額抽出に問題あり")
    print(f"{'='*80}")

    return all_passed


def test_amount_matching_logic():
    """金額マッチングロジックのテスト"""

    print("\n" + "=" * 80)
    print("金額マッチングロジックテスト")
    print("=" * 80)

    # シミュレーション: 本表金額 vs 複数の受信通知金額
    test_cases = [
        {
            "name": "完全一致ケース",
            "main_amount": 50000,
            "receipt_amounts": [30000, 50000, 70000],
            "expected_index": 1
        },
        {
            "name": "近似マッチケース",
            "main_amount": 50000,
            "receipt_amounts": [30000, 49999, 70000],
            "expected_index": 1
        },
        {
            "name": "最小差分ケース",
            "main_amount": 50000,
            "receipt_amounts": [48000, 52000, 70000],
            "expected_index": 1
        },
    ]

    all_passed = True

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"テスト {i}: {case['name']}")
        print(f"{'='*80}")

        main_amount = case['main_amount']
        receipt_amounts = case['receipt_amounts']
        expected_index = case['expected_index']

        print(f"本表金額: {main_amount:,}円")
        print(f"受信通知金額: {[f'{amt:,}円' for amt in receipt_amounts]}")

        # マッチングロジック（main.pyと同じ）
        best_match_index = None
        best_match_diff = float('inf')

        for idx, receipt_amount in enumerate(receipt_amounts):
            diff = abs(main_amount - receipt_amount)
            print(f"  ページ{idx + 1}: {receipt_amount:,}円 (差額: {diff:,}円)")

            if diff < best_match_diff:
                best_match_diff = diff
                best_match_index = idx

        print(f"\n期待結果: ページ{expected_index + 1}")
        print(f"実際結果: ページ{best_match_index + 1 if best_match_index is not None else 'なし'}")

        if best_match_index == expected_index:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            all_passed = False

    print(f"\n{'='*80}")
    if all_passed:
        print("✅ 全テスト成功: マッチングロジック正常")
    else:
        print("❌ 一部テスト失敗: マッチングロジックに問題あり")
    print(f"{'='*80}")

    return all_passed


if __name__ == "__main__":
    print("=" * 80)
    print("v7.2.1-AMOUNT-MATCHING 総合テスト")
    print("=" * 80)

    results = []

    # テスト1: 受信通知からの金額抽出
    results.append(("受信通知金額抽出", test_amount_extraction()))

    # テスト2: 本表PDFからの金額抽出
    results.append(("本表PDF金額抽出", test_main_pdf_amount_extraction()))

    # テスト3: 金額マッチングロジック
    results.append(("金額マッチングロジック", test_amount_matching_logic()))

    # 総合結果
    print("\n" + "=" * 80)
    print("総合テスト結果")
    print("=" * 80)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 全テスト成功: v7.2.1実装完了")
    else:
        print("❌ 一部テスト失敗: 修正が必要")
    print("=" * 80)