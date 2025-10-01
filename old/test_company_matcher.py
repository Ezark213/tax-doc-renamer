#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CompanyNameMatcher統合テスト
会社名マッチングロジックの検証
"""

import sys
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import tempfile
from core.ocr_engine import CompanyNameMatcher


def test_extract_company_name_from_folder():
    """フォルダ名から会社名抽出テスト"""
    matcher = CompanyNameMatcher()

    # 正常ケース
    test_cases = [
        ("2511_01_給与所得・退職所得等の所得税徴収高計算書(一般)_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ", "株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ"),
        ("2511_01_報酬・料金等の所得税徴収高計算書_0234T0060_株式会社ｄｅｅｃｌ", "株式会社ｄｅｅｃｌ"),
        ("2511_0001_報酬・料金等の所得税徴収高計算書_0345N0033_株式会社ＮｏｒｔｈＷｉｎｇ", "株式会社ＮｏｒｔｈＷｉｎｇ"),
        ("2511_01_給与所得_0413K0063_有限会社ABC", "有限会社ABC"),
        ("2511_9999_報酬_0234T0060_(株)テスト商事", "(株)テスト商事"),
    ]

    for folder_name, expected in test_cases:
        result = matcher.extract_company_name_from_folder(folder_name)
        assert result == expected, f"Failed: {folder_name} -> {result} (expected: {expected})"

    # 異常ケース
    assert matcher.extract_company_name_from_folder("") is None
    assert matcher.extract_company_name_from_folder("invalid_folder_name") is None

    print("✓ フォルダ名から会社名抽出テスト PASS")


def test_normalize_company_name():
    """会社名正規化テスト"""
    matcher = CompanyNameMatcher()

    # 正常化テストケース
    test_cases = [
        # 法人格除去
        ("株式会社ABC", "abc"),
        ("(株)ABC", "abc"),
        ("（株）ABC", "abc"),
        ("有限会社ABC", "abc"),
        ("ABC株式会社", "abc"),

        # 全角・半角統一
        ("ＡＢＣ", "abc"),
        ("ａｂｃ", "abc"),
        ("１２３", "123"),

        # 記号除去
        ("A-B-C", "abc"),
        ("A－B－C", "abc"),
        ("A B C", "abc"),

        # 旧字体統一
        ("髙橋商事", "高橋商事"),
        ("渡邊建設", "渡辺建設"),
        ("川﨑工業", "川崎工業"),

        # 複合ケース
        ("株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ", "xregulation"),
        ("(株)ｄｅｅｃｌ", "deecl"),
        ("株式会社ＮｏｒｔｈＷｉｎｇ", "northwing"),
    ]

    for input_name, expected in test_cases:
        result = matcher.normalize_company_name(input_name)
        assert result == expected, f"Failed: {input_name} -> {result} (expected: {expected})"

    # 空文字列ケース
    assert matcher.normalize_company_name("") == ""
    assert matcher.normalize_company_name(None) == ""

    print("✓ 会社名正規化テスト PASS")


def test_match_folder():
    """フォルダマッチングテスト"""
    matcher = CompanyNameMatcher()

    # フォルダ名リスト
    folder_names = [
        "2511_01_給与所得・退職所得等の所得税徴収高計算書(一般)_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ",
        "2511_01_報酬・料金等の所得税徴収高計算書_0234T0060_株式会社ｄｅｅｃｌ",
        "2511_01_報酬・料金等の所得税徴収高計算書_0345N0033_株式会社ＮｏｒｔｈＷｉｎｇ",
        "2511_01_給与所得_0413K0064_有限会社ABC商事",
        "2511_01_報酬_0234T0061_(株)テスト工業",
    ]

    # 完全一致テストケース
    test_cases_exact = [
        ("株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ", folder_names[0], 1.0),
        ("株式会社ｄｅｅｃｌ", folder_names[1], 1.0),
        ("株式会社ＮｏｒｔｈＷｉｎｇ", folder_names[2], 1.0),
    ]

    for receipt_company, expected_folder, expected_score in test_cases_exact:
        result = matcher.match_folder(receipt_company, folder_names, threshold=0.7)
        assert result is not None, f"Failed: {receipt_company} -> No match"
        matched_folder, score = result
        assert matched_folder == expected_folder, f"Failed: {receipt_company} -> {matched_folder} (expected: {expected_folder})"
        assert score == expected_score, f"Failed: {receipt_company} -> score {score} (expected: {expected_score})"

    # 部分一致テストケース（法人格なし）
    test_cases_partial = [
        ("Ｘ－Ｒｅｇｕｌａｔｉｏｎ", folder_names[0]),
        ("ｄｅｅｃｌ", folder_names[1]),
        ("ＮｏｒｔｈＷｉｎｇ", folder_names[2]),
        ("ABC商事", folder_names[3]),
        ("テスト工業", folder_names[4]),
    ]

    for receipt_company, expected_folder in test_cases_partial:
        result = matcher.match_folder(receipt_company, folder_names, threshold=0.7)
        assert result is not None, f"Failed: {receipt_company} -> No match"
        matched_folder, score = result
        assert matched_folder == expected_folder, f"Failed: {receipt_company} -> {matched_folder} (expected: {expected_folder})"
        assert score >= 0.7, f"Failed: {receipt_company} -> score {score} < 0.7"

    # マッチング失敗ケース
    no_match_cases = [
        "存在しない会社",
        "XYZABC株式会社",
        "",
    ]

    for receipt_company in no_match_cases:
        result = matcher.match_folder(receipt_company, folder_names, threshold=0.7)
        assert result is None, f"Failed: {receipt_company} should not match"

    print("✓ フォルダマッチングテスト PASS")


def test_integration():
    """統合テスト（エンドツーエンド）"""
    matcher = CompanyNameMatcher()

    # シナリオ: 受信通知から会社名抽出 → フォルダマッチング
    folder_names = [
        "2511_01_給与所得_0001_株式会社テストA",
        "2511_01_報酬_0002_有限会社テストB",
        "2511_01_給与所得_0003_(株)テストC商事",
    ]

    # 受信通知から抽出される会社名（シミュレーション）
    receipt_companies = [
        "株式会社テストA様",  # "様"付き
        "有限会社テストB 納税者",  # "納税者"付き
        "(株)テストC商事御中",  # "御中"付き
    ]

    # 各受信通知がそれぞれのフォルダにマッチすることを確認
    for i, receipt_company in enumerate(receipt_companies):
        # 会社名抽出シミュレーション（パターンマッチング）
        import re
        company_patterns = [
            r'([^\s]{2,30}?)(?:様|殿|御中)',
            r'([^\s]{2,30}?)(?:\s*納税者)',
            r'([^\s]{2,30}?)(?:\s*宛)',
        ]
        extracted_company = None
        for pattern in company_patterns:
            match = re.search(pattern, receipt_company)
            if match:
                extracted_company = match.group(1).strip()
                break

        assert extracted_company is not None, f"Failed to extract company from: {receipt_company}"

        # フォルダマッチング
        result = matcher.match_folder(extracted_company, folder_names, threshold=0.7)
        assert result is not None, f"Failed to match: {extracted_company}"

        matched_folder, score = result
        assert matched_folder == folder_names[i], f"Failed: {extracted_company} -> {matched_folder} (expected: {folder_names[i]})"

    print("✓ 統合テスト PASS")


if __name__ == "__main__":
    print("=" * 50)
    print("CompanyNameMatcher統合テスト開始")
    print("=" * 50)

    test_extract_company_name_from_folder()
    test_normalize_company_name()
    test_match_folder()
    test_integration()

    print("=" * 50)
    print("✓ 全テストPASS!")
    print("=" * 50)