#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受信通知連番システム v5.3.5-ui-robust のテスト

Tests:
- ReceiptSequencer class functionality
- Tokyo rule enforcement (FATAL error)
- Prefecture and municipality numbering logic
- OCR-based set matching
- Error handling and edge cases
"""

import sys
import os
import pytest
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.seq_policy import ReceiptSequencer, is_receipt_notice, is_pref_receipt, is_city_receipt
from helpers.job_context import JobContext


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


class TestReceiptNoticeDetection:
    """受信通知判定のテスト"""
    
    def test_is_receipt_notice_valid_codes(self):
        """受信通知コードの正しい判定"""
        assert is_receipt_notice("1003_受信通知") == True
        assert is_receipt_notice("1013_受信通知") == True  
        assert is_receipt_notice("1023_受信通知") == True
        assert is_receipt_notice("2003_受信通知") == True
        assert is_receipt_notice("2013_受信通知") == True
        assert is_receipt_notice("2023_受信通知") == True
    
    def test_is_receipt_notice_invalid_codes(self):
        """受信通知でないコードの判定"""
        assert is_receipt_notice("1001_法人都道府県民税") == False
        assert is_receipt_notice("2001_法人市民税") == False
        assert is_receipt_notice("5003_補助元帳") == False
        assert is_receipt_notice("1004_納付情報") == False
        assert is_receipt_notice("invalid") == False
        assert is_receipt_notice("") == False
    
    def test_is_pref_receipt(self):
        """都道府県受信通知の判定"""
        assert is_pref_receipt("1003_受信通知") == True
        assert is_pref_receipt("1013_受信通知") == True
        assert is_pref_receipt("2003_受信通知") == False
        assert is_pref_receipt("2013_受信通知") == False
    
    def test_is_city_receipt(self):
        """市町村受信通知の判定"""
        assert is_city_receipt("2003_受信通知") == True
        assert is_city_receipt("2013_受信通知") == True
        assert is_city_receipt("1003_受信通知") == False
        assert is_city_receipt("1013_受信通知") == False


class TestReceiptSequencer:
    """ReceiptSequencerクラスのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        # 標準的なセット構成（東京都がセット1）
        self.standard_sets = {
            1: {"prefecture": "東京都", "city": ""},
            2: {"prefecture": "愛知県", "city": "蒲郡市"},
            3: {"prefecture": "福岡県", "city": "福岡市"}
        }
        
        # 東京都無しのセット構成
        self.no_tokyo_sets = {
            1: {"prefecture": "愛知県", "city": "蒲郡市"},
            2: {"prefecture": "福岡県", "city": "福岡市"},
            3: {"prefecture": "大阪府", "city": "大阪市"}
        }
        
        # 東京都がセット2にあるセット構成（FATAL error）
        self.tokyo_wrong_position = {
            1: {"prefecture": "愛知県", "city": "蒲郡市"},
            2: {"prefecture": "東京都", "city": ""},
            3: {"prefecture": "福岡県", "city": "福岡市"}
        }
    
    def test_prefecture_numbering_standard(self):
        """都道府県連番の標準テスト"""
        ctx = MockJobContext(self.standard_sets)
        sequencer = ReceiptSequencer(ctx)
        
        # 東京都: セット1 -> 1003
        result = sequencer.assign_pref_seq("1003_受信通知", "東京都")
        assert result == "1003"
        
        # 愛知県: セット2 -> 1013  
        result = sequencer.assign_pref_seq("1003_受信通知", "愛知県")
        assert result == "1013"
        
        # 福岡県: セット3 -> 1023
        result = sequencer.assign_pref_seq("1003_受信通知", "福岡県")
        assert result == "1023"
    
    def test_municipality_numbering_with_tokyo(self):
        """市町村連番の東京都繰り上がりテスト"""
        ctx = MockJobContext(self.standard_sets)
        sequencer = ReceiptSequencer(ctx)
        
        # 蒲郡市: セット2、東京都スキップで adjusted=1 -> 2003
        result = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
        assert result == "2003"
        
        # 福岡市: セット3、東京都スキップで adjusted=2 -> 2013
        result = sequencer.assign_city_seq("2003_受信通知", "福岡県", "福岡市")
        assert result == "2013"
    
    def test_municipality_numbering_without_tokyo(self):
        """市町村連番の東京都無しテスト"""
        ctx = MockJobContext(self.no_tokyo_sets)
        sequencer = ReceiptSequencer(ctx)
        
        # 蒲郡市: セット1、東京都無しでadjusted=1 -> 2003
        result = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
        assert result == "2003"
        
        # 福岡市: セット2、東京都無しでadjusted=2 -> 2013
        result = sequencer.assign_city_seq("2003_受信通知", "福岡県", "福岡市")  
        assert result == "2013"
    
    def test_tokyo_rule_violation_fatal_error(self):
        """東京都制約違反のFATALエラーテスト"""
        ctx = MockJobContext(self.tokyo_wrong_position)
        
        with pytest.raises(ValueError, match=r"FATAL.*SEQ.*Tokyo must be Set #1"):
            sequencer = ReceiptSequencer(ctx)
            # 東京都が存在するが、セット2にあるのでFATALエラー
            sequencer.assign_pref_seq("1003_受信通知", "東京都")
    
    def test_unknown_prefecture_error(self):
        """未知の都道府県エラーテスト"""
        ctx = MockJobContext(self.standard_sets)
        sequencer = ReceiptSequencer(ctx)
        
        with pytest.raises(ValueError, match="Unknown prefecture"):
            sequencer.assign_pref_seq("1003_受信通知", "存在しない県")
    
    def test_unknown_municipality_error(self):
        """未知の市町村エラーテスト"""
        ctx = MockJobContext(self.standard_sets)
        sequencer = ReceiptSequencer(ctx)
        
        with pytest.raises(ValueError, match="Unknown city"):
            sequencer.assign_city_seq("2003_受信通知", "愛知県", "存在しない市")
    
    def test_idempotent_operation(self):
        """冪等性テスト（同じ自治体への重複割当）"""
        ctx = MockJobContext(self.standard_sets)
        sequencer = ReceiptSequencer(ctx)
        
        # 同じ都道府県に複数回割当
        result1 = sequencer.assign_pref_seq("1003_受信通知", "愛知県")
        result2 = sequencer.assign_pref_seq("1003_受信通知", "愛知県")
        assert result1 == result2 == "1013"
        
        # 同じ市町村に複数回割当
        result1 = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
        result2 = sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市")
        assert result1 == result2 == "2003"
    
    def test_formula_validation(self):
        """連番計算式の検証 BASE + (set_index - 1) * 10"""
        ctx = MockJobContext(self.standard_sets)
        sequencer = ReceiptSequencer(ctx)
        
        # 都道府県: BASE_PREF = 1003
        assert sequencer.assign_pref_seq("1003_受信通知", "東京都") == "1003"  # 1003 + (1-1)*10
        assert sequencer.assign_pref_seq("1003_受信通知", "愛知県") == "1013"  # 1003 + (2-1)*10
        assert sequencer.assign_pref_seq("1003_受信通知", "福岡県") == "1023"  # 1003 + (3-1)*10
        
        # 市町村: BASE_CITY = 2003, 東京都スキップ適用
        assert sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市") == "2003"  # 2003 + (1-1)*10
        assert sequencer.assign_city_seq("2003_受信通知", "福岡県", "福岡市") == "2013"  # 2003 + (2-1)*10


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def test_empty_municipality_sets(self):
        """空のセット構成でのテスト"""
        ctx = MockJobContext({})
        sequencer = ReceiptSequencer(ctx)
        
        with pytest.raises(ValueError, match="Unknown prefecture"):
            sequencer.assign_pref_seq("1003_受信通知", "東京都")
    
    def test_single_set_configuration(self):
        """単一セット構成でのテスト"""
        single_set = {1: {"prefecture": "東京都", "city": ""}}
        ctx = MockJobContext(single_set)
        sequencer = ReceiptSequencer(ctx)
        
        result = sequencer.assign_pref_seq("1003_受信通知", "東京都")
        assert result == "1003"
    
    def test_complex_set_indices(self):
        """非連続なセット番号でのテスト"""
        complex_sets = {
            1: {"prefecture": "東京都", "city": ""},
            3: {"prefecture": "愛知県", "city": "蒲郡市"},  # セット2をスキップ
            5: {"prefecture": "福岡県", "city": "福岡市"}
        }
        ctx = MockJobContext(complex_sets)
        sequencer = ReceiptSequencer(ctx)
        
        # 東京都: セット1 -> 1003
        assert sequencer.assign_pref_seq("1003_受信通知", "東京都") == "1003"
        
        # 愛知県: セット3 -> 1023
        assert sequencer.assign_pref_seq("1003_受信通知", "愛知県") == "1023"
        
        # 蒲郡市: セット3、東京都スキップで adjusted=2 -> 2013  
        assert sequencer.assign_city_seq("2003_受信通知", "愛知県", "蒲郡市") == "2013"


if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
    
    # テスト実行
    pytest.main([__file__, "-v"])