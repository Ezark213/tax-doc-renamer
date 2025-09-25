#!/usr/bin/env python3
"""
重複処理修正の動作検証テスト
修正後のduplicate prevention機能をテスト
"""

import re

def _is_already_renamed(filename):
    """ファイルが既にリネーム済みかチェック（無限リネーム防止）"""
    # 4桁の数字で始まるファイル名（例：0001_、1001_、2001_など）はリネーム済み
    # _001, _002等の番号付きバリアントも対象に含める
    renamed_pattern = r'^[0-9]{4}_.*(?:_[0-9]{3})?\.pdf$'
    # __split_ファイルは処理が必要な一時ファイルなので除外しない
    if filename.startswith('__split_'):
        return False

    return bool(re.match(renamed_pattern, filename, re.IGNORECASE))

def test_duplicate_detection():
    """重複検出ロジックのテスト"""
    print("=== 重複検出ロジックテスト ===")

    test_cases = [
        # (filename, expected_result, description)
        ("0000_納付書金額一覧表_2508.pdf", True, "基本リネーム済み"),
        ("0000_納付書金額一覧表_2508_001.pdf", True, "番号付きバリアント"),
        ("0000_納付書金額一覧表_2508_002.pdf", True, "番号付きバリアント2"),
        ("1003_東京都_受信通知_2508.pdf", True, "受信通知リネーム済み"),
        ("1003_東京都_受信通知_2508_001.pdf", True, "受信通知番号付き"),
        ("__split_001_1758007850158559.pdf", False, "分割ファイル（処理必要）"),
        ("元のファイル.pdf", False, "未リネームファイル"),
        ("01_法人税確定申告書(青)_フィットネス........pdf", False, "未リネームファイル2")
    ]

    all_passed = True
    for filename, expected, description in test_cases:
        result = _is_already_renamed(filename)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status}: {filename} -> {result} ({description})")
        if result != expected:
            all_passed = False

    if all_passed:
        print("\n全テストケース PASSED - 重複検出ロジック正常動作")
        return True
    else:
        print("\nテスト失敗 - 重複検出ロジックに問題あり")
        return False

if __name__ == "__main__":
    test_duplicate_detection()