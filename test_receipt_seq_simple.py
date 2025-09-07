#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受信通知連番システム v5.3.5-ui-robust の簡易テスト
"""

import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.seq_policy import ReceiptSequencer, is_receipt_notice, is_pref_receipt, is_city_receipt


class MockJobContext:
    """JobContextのモッククラス"""
    def __init__(self, municipality_sets=None):
        self.current_municipality_sets = municipality_sets or {}
    
    def get_set_index_for_pref(self, pref_name):
        for set_id, set_info in self.current_municipality_sets.items():
            if set_info.get("prefecture") == pref_name:
                return set_id
        return None
    
    def get_set_index_for_city(self, pref_name, city_name):
        for set_id, set_info in self.current_municipality_sets.items():
            if (set_info.get("prefecture") == pref_name and 
                set_info.get("city") == city_name):
                return set_id
        return None


def test_receipt_notice_detection():
    """受信通知判定のテスト"""
    print("\n=== 受信通知判定テスト ===")
    
    # 正常ケース
    assert is_receipt_notice("1003_受信通知") == True
    assert is_receipt_notice("2013_受信通知") == True
    print("✓ 受信通知判定: 正常ケース OK")
    
    # 異常ケース
    assert is_receipt_notice("1001_法人都道府県民税") == False
    assert is_receipt_notice("5003_補助元帳") == False
    print("✓ 受信通知判定: 異常ケース OK")
    
    # 都道府県/市町村判定
    assert is_pref_receipt("1003_受信通知") == True
    assert is_city_receipt("2003_受信通知") == True
    assert is_pref_receipt("2003_受信通知") == False
    assert is_city_receipt("1003_受信通知") == False
    print("✓ 都道府県/市町村判定 OK")


def test_standard_numbering():
    """標準的な連番テスト"""
    print("\n=== 標準連番テスト ===")
    
    # 東京都がセット1の標準構成
    standard_sets = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"},
        3: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    ctx = MockJobContext(standard_sets)
    sequencer = ReceiptSequencer(ctx)
    
    # 都道府県連番テスト
    result1 = sequencer.assign_pref_seq("1003_受信通知", "東京都")
    assert result1 == "1003", f"Expected 1003, got {result1}"
    print(f"✓ 東京都 -> {result1}")
    
    result2 = sequencer.assign_pref_seq("1003_受信通知", "愛知県")
    assert result2 == "1013", f"Expected 1013, got {result2}"
    print(f"✓ 愛知県 -> {result2}")
    
    result3 = sequencer.assign_pref_seq("1003_受信通知", "福岡県")
    assert result3 == "1023", f"Expected 1023, got {result3}"
    print(f"✓ 福岡県 -> {result3}")
    
    # 市町村連番テスト（東京都スキップ）
    result4 = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
    assert result4 == "2003", f"Expected 2003, got {result4}"
    print(f"✓ 蒲郡市（東京都スキップ） -> {result4}")
    
    result5 = sequencer.assign_city_seq("2003_受信通知", "福岡県", "福岡市")
    assert result5 == "2013", f"Expected 2013, got {result5}"
    print(f"✓ 福岡市（東京都スキップ） -> {result5}")
    
    print("✓ 標準連番テスト OK")


def test_tokyo_rule_violation():
    """東京都制約違反テスト"""
    print("\n=== 東京都制約違反テスト ===")
    
    # 東京都がセット2にある構成（FATAL error）
    tokyo_wrong_position = {
        1: {"prefecture": "愛知県", "city": "蒲郡市"},
        2: {"prefecture": "東京都", "city": ""},
        3: {"prefecture": "福岡県", "city": "福岡市"}
    }
    
    try:
        ctx = MockJobContext(tokyo_wrong_position)
        sequencer = ReceiptSequencer(ctx)
        # 東京都への連番割当を試行（FATAL errorが発生するはず）
        sequencer.assign_pref_seq("1003_受信通知", "東京都")
        assert False, "Expected FATAL error for Tokyo rule violation"
    except ValueError as e:
        if "FATAL" in str(e) and "Tokyo must be Set #1" in str(e):
            print(f"✓ 東京都制約違反を正しく検出: {e}")
        else:
            assert False, f"Unexpected error message: {e}"
    
    print("✓ 東京都制約違反テスト OK")


def test_no_tokyo_configuration():
    """東京都無し構成テスト"""
    print("\n=== 東京都無し構成テスト ===")
    
    # 東京都無しのセット構成
    no_tokyo_sets = {
        1: {"prefecture": "愛知県", "city": "蒲郡市"},
        2: {"prefecture": "福岡県", "city": "福岡市"},
        3: {"prefecture": "大阪府", "city": "大阪市"}
    }
    
    ctx = MockJobContext(no_tokyo_sets)
    sequencer = ReceiptSequencer(ctx)
    
    # 市町村連番（東京都スキップなし）
    result1 = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
    assert result1 == "2003", f"Expected 2003, got {result1}"
    print(f"✓ 蒲郡市（東京都無し） -> {result1}")
    
    result2 = sequencer.assign_city_seq("2003_受信通知", "福岡県", "福岡市")
    assert result2 == "2013", f"Expected 2013, got {result2}"
    print(f"✓ 福岡市（東京都無し） -> {result2}")
    
    print("✓ 東京都無し構成テスト OK")


def test_error_cases():
    """エラーケーステスト"""
    print("\n=== エラーケーステスト ===")
    
    standard_sets = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"}
    }
    
    ctx = MockJobContext(standard_sets)
    sequencer = ReceiptSequencer(ctx)
    
    # 未知の都道府県
    try:
        sequencer.assign_pref_seq("1003_受信通知", "存在しない県")
        assert False, "Expected error for unknown prefecture"
    except ValueError as e:
        if "Unknown prefecture" in str(e):
            print(f"✓ 未知の都道府県エラー: {e}")
        else:
            assert False, f"Unexpected error: {e}"
    
    # 未知の市町村
    try:
        sequencer.assign_city_seq("2003_受信通知", "愛知県", "存在しない市")
        assert False, "Expected error for unknown city"
    except ValueError as e:
        if "Unknown city" in str(e):
            print(f"✓ 未知の市町村エラー: {e}")
        else:
            assert False, f"Unexpected error: {e}"
    
    print("✓ エラーケーステスト OK")


def test_idempotent_operation():
    """冪等性テスト"""
    print("\n=== 冪等性テスト ===")
    
    standard_sets = {
        1: {"prefecture": "東京都", "city": ""},
        2: {"prefecture": "愛知県", "city": "蒲郡市"}
    }
    
    ctx = MockJobContext(standard_sets)
    sequencer = ReceiptSequencer(ctx)
    
    # 同じ自治体への複数回割当
    result1 = sequencer.assign_pref_seq("1003_受信通知", "愛知県")
    result2 = sequencer.assign_pref_seq("1003_受信通知", "愛知県")
    assert result1 == result2, f"Idempotent failed: {result1} != {result2}"
    print(f"✓ 都道府県冪等性: {result1} == {result2}")
    
    result3 = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
    result4 = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
    assert result3 == result4, f"Idempotent failed: {result3} != {result4}"
    print(f"✓ 市町村冪等性: {result3} == {result4}")
    
    print("✓ 冪等性テスト OK")


def main():
    """テスト実行"""
    print("受信通知連番システム v5.3.5-ui-robust テスト開始")
    print("=" * 60)
    
    try:
        test_receipt_notice_detection()
        test_standard_numbering()
        test_tokyo_rule_violation()
        test_no_tokyo_configuration()
        test_error_cases()
        test_idempotent_operation()
        
        print("\n" + "=" * 60)
        print("✅ 全テスト合格！受信通知連番システムは正常に動作しています。")
        print("v5.3.5-ui-robust 実装完了")
        
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    # テスト実行
    sys.exit(main())