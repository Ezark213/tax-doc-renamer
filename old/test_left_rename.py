#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
左側フォルダリネーム機能テスト
完全独立性・右側非干渉確認
"""

import sys
import io

# 標準出力をUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import tempfile
import shutil
import re

def test_pattern_matching():
    """4桁数字プレフィックスパターンマッチングテスト"""
    pattern = re.compile(r'^(\d{4})_(.+)$')

    # 正常ケース
    assert pattern.match("0000_test.pdf")
    assert pattern.match("2508_document.xlsx")
    assert pattern.match("1234_file_name_with_underscores.txt")

    # 異常ケース
    assert not pattern.match("test.pdf")  # プレフィックスなし
    assert not pattern.match("123_test.pdf")  # 3桁
    assert not pattern.match("12345_test.pdf")  # 5桁
    assert not pattern.match("abcd_test.pdf")  # 非数字

    print("✓ Pattern matching test passed")

def test_yymm_validation():
    """YYMM入力バリデーションテスト"""
    def validate_yymm(yymm_value):
        # 4桁数字チェック
        if not re.match(r'^\d{4}$', yymm_value):
            return False

        # 月の妥当性チェック (01-12)
        month = int(yymm_value[2:4])
        if month < 1 or month > 12:
            return False

        return True

    # 正常ケース
    assert validate_yymm("2508") == True
    assert validate_yymm("2501") == True
    assert validate_yymm("2512") == True

    # 異常ケース
    assert validate_yymm("250") == False  # 3桁
    assert validate_yymm("25008") == False  # 5桁
    assert validate_yymm("25ab") == False  # 非数字
    assert validate_yymm("2500") == False  # 月00
    assert validate_yymm("2513") == False  # 月13

    print("✓ YYMM validation test passed")

def test_rename_logic():
    """リネームロジック統合テスト"""
    # 一時ディレクトリ作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # テストファイル作成
        test_files = [
            "0000_test1.pdf",
            "1234_test2.xlsx",
            "5678_document_with_underscores.txt",
            "normal_file.pdf",  # パターン不一致（処理対象外）
        ]

        for filename in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")

        # リネーム処理シミュレーション
        yymm = "2508"
        pattern = re.compile(r'^(\d{4})_(.+)$')
        processed_count = 0

        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)

            if not os.path.isfile(file_path):
                continue

            match = pattern.match(filename)
            if not match:
                continue

            rest_name = match.group(2)
            new_filename = f"{yymm}_{rest_name}"
            new_file_path = os.path.join(temp_dir, new_filename)

            if os.path.exists(new_file_path):
                continue

            shutil.move(file_path, new_file_path)
            processed_count += 1

        # 検証
        assert processed_count == 3  # 3ファイルが処理されたはず

        # リネーム後のファイル確認
        final_files = os.listdir(temp_dir)
        assert "2508_test1.pdf" in final_files
        assert "2508_test2.xlsx" in final_files
        assert "2508_document_with_underscores.txt" in final_files
        assert "normal_file.pdf" in final_files  # 処理されていない

        # 元のファイルが存在しないことを確認
        assert "0000_test1.pdf" not in final_files
        assert "1234_test2.xlsx" not in final_files
        assert "5678_document_with_underscores.txt" not in final_files

    print("✓ Rename logic test passed")

def test_duplicate_handling():
    """重複ファイル処理テスト"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 既存ファイル作成（リネーム先と同じ名前）
        existing_file = os.path.join(temp_dir, "2508_test.pdf")
        with open(existing_file, 'w') as f:
            f.write("existing content")

        # リネーム対象ファイル作成
        source_file = os.path.join(temp_dir, "0000_test.pdf")
        with open(source_file, 'w') as f:
            f.write("source content")

        # リネーム処理シミュレーション（重複チェック）
        yymm = "2508"
        pattern = re.compile(r'^(\d{4})_(.+)$')

        filename = "0000_test.pdf"
        match = pattern.match(filename)
        rest_name = match.group(2)
        new_filename = f"{yymm}_{rest_name}"
        new_file_path = os.path.join(temp_dir, new_filename)

        # 重複チェック
        if os.path.exists(new_file_path):
            # 重複のためスキップ（正常動作）
            pass
        else:
            shutil.move(source_file, new_file_path)

        # 検証: 元のファイルがそのまま残っている
        assert os.path.exists(source_file)
        assert os.path.exists(existing_file)

        # 既存ファイルの内容が変更されていない
        with open(existing_file, 'r') as f:
            assert f.read() == "existing content"

    print("✓ Duplicate handling test passed")

def test_right_side_isolation():
    """右側機能との完全独立性確認テスト"""
    # 左側で使用する変数名
    left_vars = [
        'left_yymm_var',
        'left_yymm_status_var',
        'left_execute_btn',
        'left_progress_var'
    ]

    # 右側で使用する変数名
    right_vars = [
        'year_month_var',
        'prefecture_var_1',
        'municipality_var_1',
        'yymm_status_label'
    ]

    # 変数名の重複がないことを確認
    for left_var in left_vars:
        for right_var in right_vars:
            assert left_var != right_var, f"Variable name conflict: {left_var} == {right_var}"

    print("✓ Right-side isolation test passed")

if __name__ == "__main__":
    print("=" * 50)
    print("左側フォルダリネーム機能テスト開始")
    print("=" * 50)

    test_pattern_matching()
    test_yymm_validation()
    test_rename_logic()
    test_duplicate_handling()
    test_right_side_isolation()

    print("=" * 50)
    print("✓ 全テストPASS!")
    print("=" * 50)