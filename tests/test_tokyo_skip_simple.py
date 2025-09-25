#!/usr/bin/env python3
"""
Tokyo skip logic簡易テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.seq_policy import (
    analyze_prefecture_sets,
    generate_receipt_number_generic
)

def test_tokyo_skip_basic():
    """基本的なTokyo skipテスト"""
    print("=== Tokyo skip基本テスト ===")

    # テストケース1: 東京都 + 他県市
    set_config = {
        1: {'prefecture': '東京都', 'city': ''},
        2: {'prefecture': '愛知県', 'city': '蒲郡市'},
        3: {'prefecture': '福岡県', 'city': '福岡市'}
    }

    # 市町村受信通知テスト（期待値：東京都スキップで2003, 2013）
    gamagori_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '愛知県', 'city': '蒲郡市'},
        set_config
    )
    fukuoka_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '福岡県', 'city': '福岡市'},
        set_config
    )

    print(f"蒲郡市: {gamagori_receipt} (期待値: 2003)")
    print(f"福岡市: {fukuoka_receipt} (期待値: 2013)")

    # 検証
    assert gamagori_receipt == "2003", f"蒲郡市: 期待値2003、実際{gamagori_receipt}"
    assert fukuoka_receipt == "2013", f"福岡市: 期待値2013、実際{fukuoka_receipt}"

    print("基本テスト PASSED")

def test_no_tokyo():
    """東京都なしテスト"""
    print("\n=== 東京都なしテスト ===")

    set_config = {
        1: {'prefecture': '愛知県', 'city': '名古屋市'},
        2: {'prefecture': '福岡県', 'city': '福岡市'}
    }

    nagoya_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '愛知県', 'city': '名古屋市'},
        set_config
    )
    fukuoka_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '福岡県', 'city': '福岡市'},
        set_config
    )

    print(f"名古屋市: {nagoya_receipt} (期待値: 2003)")
    print(f"福岡市: {fukuoka_receipt} (期待値: 2013)")

    assert nagoya_receipt == "2003", f"名古屋市: 期待値2003、実際{nagoya_receipt}"
    assert fukuoka_receipt == "2013", f"福岡市: 期待値2013、実際{fukuoka_receipt}"

    print("東京都なしテスト PASSED")

if __name__ == "__main__":
    print("Tokyo skip logic簡易テスト開始")

    try:
        test_tokyo_skip_basic()
        test_no_tokyo()
        print("\n全テストケース PASSED!")

    except Exception as e:
        print(f"\nテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)