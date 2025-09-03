#!/usr/bin/env python3
"""
YYMM Policy System Test Cases
テスト対象: helpers/yymm_policy.py
"""

import unittest
import sys
import os
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.yymm_policy import (
    FORCE_UI_YYMM_CODES, resolve_yymm_by_policy, require_ui_yymm, 
    validate_policy_result, log_yymm_decision, _valid
)


class TestYYMMPolicy(unittest.TestCase):
    """YYMM Policy System のテストクラス"""
    
    def setUp(self):
        """テストケース共通の設定"""
        # Mock設定オブジェクト
        self.mock_settings = MagicMock()
        self.mock_settings.manual_yymm = "2508"
        
        # Mockコンテキスト
        self.mock_ctx = MagicMock()
        self.mock_ctx.yymm = "2507"
    
    def test_force_ui_yymm_codes_constants(self):
        """FORCE_UI_YYMM_CODES定数のテスト"""
        expected_codes = {"6001", "6002", "6003", "0000"}
        self.assertEqual(FORCE_UI_YYMM_CODES, expected_codes)
        self.assertIn("6001", FORCE_UI_YYMM_CODES)  # 固定資産台帳
        self.assertIn("6002", FORCE_UI_YYMM_CODES)  # 一括償却資産
        self.assertIn("6003", FORCE_UI_YYMM_CODES)  # 少額減価償却資産
        self.assertIn("0000", FORCE_UI_YYMM_CODES)  # 納付税額一覧表
    
    def test_valid_function(self):
        """_valid関数のテスト"""
        # 有効なYYMM値
        self.assertTrue(_valid("2508"))
        self.assertTrue(_valid("2412"))
        self.assertTrue(_valid("2501"))
        
        # 無効なYYMM値
        self.assertFalse(_valid(""))
        self.assertFalse(_valid(None))
        self.assertFalse(_valid("25"))       # 長さ不足
        self.assertFalse(_valid("25088"))    # 長さ超過
        self.assertFalse(_valid("25ab"))     # 文字含む
        self.assertFalse(_valid("YYMM"))     # 全文字
        self.assertFalse(_valid(2508))       # 文字列以外
    
    def test_require_ui_yymm_success(self):
        """require_ui_yymm関数の成功ケース"""
        yymm, source = require_ui_yymm(self.mock_settings)
        self.assertEqual(yymm, "2508")
        self.assertEqual(source, "UI_FORCED")
    
    def test_require_ui_yymm_failure(self):
        """require_ui_yymm関数の失敗ケース"""
        # 無効な設定オブジェクト
        invalid_settings = MagicMock()
        invalid_settings.manual_yymm = "25"  # 無効なYYMM
        
        with self.assertRaises(ValueError) as context:
            require_ui_yymm(invalid_settings)
        self.assertIn("[FATAL] UI YYMM is required", str(context.exception))
    
    def test_resolve_yymm_force_ui_codes(self):
        """resolve_yymm_by_policy: UI強制コードのテスト"""
        for code in FORCE_UI_YYMM_CODES:
            with self.subTest(code=code):
                yymm, source = resolve_yymm_by_policy(
                    class_code=code,
                    ctx=self.mock_ctx,
                    settings=self.mock_settings,
                    detected="2405"  # 検出値があってもUI優先
                )
                self.assertEqual(yymm, "2508")  # GUI値
                self.assertEqual(source, "UI_FORCED")
    
    def test_resolve_yymm_detected_priority(self):
        """resolve_yymm_by_policy: 検出値優先のテスト"""
        yymm, source = resolve_yymm_by_policy(
            class_code="1001",  # UI強制以外のコード
            ctx=self.mock_ctx,
            settings=self.mock_settings,
            detected="2405"  # 有効な検出値
        )
        self.assertEqual(yymm, "2405")  # 検出値が優先
        self.assertEqual(source, "DOC/HEURISTIC")
    
    def test_resolve_yymm_ui_fallback(self):
        """resolve_yymm_by_policy: UIフォールバックのテスト"""
        yymm, source = resolve_yymm_by_policy(
            class_code="1001",  # UI強制以外のコード
            ctx=self.mock_ctx,
            settings=self.mock_settings,
            detected=None  # 検出値なし
        )
        self.assertEqual(yymm, "2508")  # GUI値にフォールバック
        self.assertEqual(source, "UI_FALLBACK")
    
    def test_resolve_yymm_context_fallback(self):
        """resolve_yymm_by_policy: コンテキストフォールバックのテスト"""
        settings_without_yymm = MagicMock()
        settings_without_yymm.manual_yymm = None
        
        yymm, source = resolve_yymm_by_policy(
            class_code="1001",
            ctx=self.mock_ctx,
            settings=settings_without_yymm,
            detected=None
        )
        self.assertEqual(yymm, "2507")  # コンテキスト値にフォールバック
        self.assertEqual(source, "UI_FALLBACK")
    
    def test_resolve_yymm_none_result(self):
        """resolve_yymm_by_policy: 最終的にNoneになるケース"""
        empty_settings = MagicMock()
        empty_settings.manual_yymm = None
        empty_ctx = None
        
        yymm, source = resolve_yymm_by_policy(
            class_code="1001",
            ctx=empty_ctx,
            settings=empty_settings,
            detected=None
        )
        self.assertIsNone(yymm)
        self.assertEqual(source, "NONE")
    
    def test_validate_policy_result_success(self):
        """validate_policy_result関数の成功ケース"""
        # 有効なYYMM
        self.assertTrue(validate_policy_result("2508", "UI_FORCED"))
        self.assertTrue(validate_policy_result("2412", "DOC/HEURISTIC"))
        
        # UI強制コードでUI由来
        for code in FORCE_UI_YYMM_CODES:
            self.assertTrue(validate_policy_result("2508", "UI_FORCED", code))
            self.assertTrue(validate_policy_result("2508", "UI_FALLBACK", code))
    
    def test_validate_policy_result_failure(self):
        """validate_policy_result関数の失敗ケース"""
        # 無効なYYMM
        self.assertFalse(validate_policy_result("25", "UI_FORCED"))
        self.assertFalse(validate_policy_result("", "UI_FORCED"))
        self.assertFalse(validate_policy_result(None, "UI_FORCED"))
        
        # UI強制コードで非UI由来（これは無効）
        self.assertFalse(validate_policy_result("2508", "DOC/HEURISTIC", "6001"))
    
    def test_log_yymm_decision(self):
        """log_yymm_decision関数のテスト"""
        # モックロガー
        mock_logger = MagicMock()
        
        # ログ出力をテスト（例外が発生しないことを確認）
        log_yymm_decision("6001", "2508", "UI_FORCED", mock_logger)
        mock_logger.info.assert_called_once()
        
        # ロガーなしでの呼び出し（例外が発生しないことを確認）
        try:
            log_yymm_decision("6001", "2508", "UI_FORCED", None)
        except Exception as e:
            self.fail(f"log_yymm_decision raised exception without logger: {e}")
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        # class_codeがNone
        yymm, source = resolve_yymm_by_policy(
            class_code=None,
            ctx=self.mock_ctx,
            settings=self.mock_settings,
            detected="2405"
        )
        self.assertEqual(yymm, "2405")  # 検出値優先
        
        # class_codeが空文字
        yymm, source = resolve_yymm_by_policy(
            class_code="",
            ctx=self.mock_ctx,
            settings=self.mock_settings,
            detected="2405"
        )
        self.assertEqual(yymm, "2405")
        
        # class_codeが短い
        yymm, source = resolve_yymm_by_policy(
            class_code="60",  # 4桁未満
            ctx=self.mock_ctx,
            settings=self.mock_settings,
            detected="2405"
        )
        self.assertEqual(yymm, "2405")  # UI強制対象外なので検出値優先

    def test_integration_scenarios(self):
        """統合シナリオのテスト"""
        # シナリオ1: 資産文書（6001）は常にUI強制
        yymm, source = resolve_yymm_by_policy("6001", None, self.mock_settings, "2410")
        self.assertEqual(yymm, "2508")  # GUI値
        self.assertEqual(source, "UI_FORCED")
        
        # シナリオ2: 通常文書（1001）は検出値優先
        yymm, source = resolve_yymm_by_policy("1001", None, self.mock_settings, "2410")
        self.assertEqual(yymm, "2410")  # 検出値
        self.assertEqual(source, "DOC/HEURISTIC")
        
        # シナリオ3: 検出失敗時はUIフォールバック
        yymm, source = resolve_yymm_by_policy("1001", None, self.mock_settings, None)
        self.assertEqual(yymm, "2508")  # GUI値
        self.assertEqual(source, "UI_FALLBACK")


if __name__ == '__main__':
    # テストの実行
    unittest.main(verbosity=2)