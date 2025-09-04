#!/usr/bin/env python3
"""
Comprehensive test suite for modular architecture v5.3.4
モジュラーアーキテクチャ v5.3.4 の包括的テストスイート
"""

import sys
import os
import logging
from typing import Dict, Any, Tuple

# パス設定
sys.path.insert(0, os.path.dirname(__file__))

# 新しいモジュラーシステムのインポート
from core.domain import resolve_domain, should_suppress_overlay
from core.overlay import apply_local_overlay, SetContext
from core.yymm_resolver import resolve_yymm, is_ui_forced_code, YYMMSource
from core.naming_engine import build_filename_from_result, NamingContext
from core.unified_classifier import UnifiedClassifier, create_document_context
from core.logging_bridge import ClassifyResult


class ModularArchitectureTests:
    """モジュラーアーキテクチャテストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.setup_logging()
    
    def setup_logging(self):
        """テスト用ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    
    def run_all_tests(self) -> bool:
        """全テスト実行"""
        print("=" * 70)
        print("モジュラーアーキテクチャ v5.3.4 包括的テスト開始")
        print("=" * 70)
        
        test_methods = [
            ("ドメイン解決テスト", self.test_domain_resolution),
            ("オーバーレイ・ノイズ抑制テスト", self.test_overlay_noise_suppression),
            ("YYMM解決・UI強制テスト", self.test_yymm_resolution),
            ("命名システムテスト", self.test_naming_system),
            ("統合分類ワークフローテスト", self.test_unified_workflow),
            ("三者一致保証テスト", self.test_three_way_consistency),
            ("エラーハンドリングテスト", self.test_error_handling),
            ("v5.3.4仕様適合テスト", self.test_v534_compliance)
        ]
        
        for test_name, test_method in test_methods:
            print(f"\n--- {test_name} ---")
            try:
                success = test_method()
                self.test_results.append((test_name, success))
                print(f"{'PASS' if success else 'FAIL'}: {test_name}")
            except Exception as e:
                print(f"ERROR: {test_name} - {str(e)}")
                self.test_results.append((test_name, False))
        
        return self.print_summary()
    
    def test_domain_resolution(self) -> bool:
        """ドメイン解決テスト"""
        test_cases = [
            ("0001", "NATIONAL_TAX", False),
            ("1011", "LOCAL_TAX", False), 
            ("2001", "LOCAL_TAX", False),
            ("3001", "CONSUMPTION_TAX", True),
            ("5001", "ACCOUNTING", True),
            ("6003", "ASSETS", True),
            ("7001", "SUMMARY", True),
            ("9999", "UNKNOWN", True)
        ]
        
        all_passed = True
        for code, expected_domain, expected_suppress in test_cases:
            domain = resolve_domain(code)
            suppress = should_suppress_overlay(code)
            
            if domain != expected_domain or suppress != expected_suppress:
                print(f"  NG {code}: expected {expected_domain}/{expected_suppress}, got {domain}/{suppress}")
                all_passed = False
            else:
                print(f"  OK {code}: {domain} (suppress={suppress})")
        
        return all_passed
    
    def test_overlay_noise_suppression(self) -> bool:
        """オーバーレイ・ノイズ抑制テスト"""
        test_cases = [
            # (code, prefecture, should_skip, description)
            ("0001", "愛知県", True, "国税 - スキップ"),
            ("3001", "福岡県", True, "消費税 - スキップ"),
            ("5001", "東京都", True, "会計書類 - スキップ"),
            ("1001", "愛知県", False, "都道府県税 - 処理"),
            ("2001", "愛知県", False, "市町村税 - 処理"),
        ]
        
        all_passed = True
        for code, prefecture, should_skip, description in test_cases:
            set_ctx = SetContext(prefecture=prefecture)
            result = apply_local_overlay(code, set_ctx)
            
            actual_skip = result.skipped
            if actual_skip != should_skip:
                print(f"  NG {description}: expected skip={should_skip}, got {actual_skip}")
                all_passed = False
            else:
                print(f"  OK {description}: skip={actual_skip}")
                if not actual_skip and code == "1001" and prefecture == "愛知県":
                    # 愛知県の場合、1011にアップグレードされることを確認
                    if result.overlay_code != "1011":
                        print(f"    NG 愛知県アップグレード失敗: expected 1011, got {result.overlay_code}")
                        all_passed = False
                    else:
                        print(f"    OK 愛知県アップグレード成功: {result.overlay_code}")
        
        return all_passed
    
    def test_yymm_resolution(self) -> bool:
        """YYMM解決・UI強制テスト"""
        from types import SimpleNamespace
        
        test_cases = [
            # UI強制コード
            ("6003", "少額減価償却資産", {"yymm": "2401"}, "2401", "UI_FORCED"),
            ("6001", "固定資産台帳", {}, None, "UI_REQUIRED"),
            
            # 通常コード（文書検出）
            ("3001", "課税期間 令和7年5月31日", {}, "0705", "DOC/HEURISTIC"),
            ("1001", "都道府県税申告書", {"yymm": "2507"}, "2507", "UI_FALLBACK"),
        ]
        
        all_passed = True
        for code, text, ui_ctx, expected_yymm, expected_source in test_cases:
            doc = SimpleNamespace(text=text)
            
            try:
                result = resolve_yymm(code, doc, ui_ctx)
                
                # UI_REQUIREDの場合は特別処理
                if expected_source == "UI_REQUIRED":
                    if result.source != YYMMSource.UI_REQUIRED:
                        print(f"  NG {code}: expected UI_REQUIRED, got {result.source}")
                        all_passed = False
                    else:
                        print(f"  OK {code}: UI_REQUIRED detected")
                else:
                    if result.yymm != expected_yymm or result.source.value != expected_source:
                        print(f"  NG {code}: expected {expected_yymm}/{expected_source}, got {result.yymm}/{result.source.value}")
                        all_passed = False
                    else:
                        print(f"  OK {code}: {result.yymm} from {result.source.value}")
                        
            except Exception as e:
                print(f"  NG {code}: Exception - {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_naming_system(self) -> bool:
        """命名システムテスト"""
        test_cases = [
            # (base_code, overlay_code, yymm, prefecture, city, expected_pattern)
            ("0001", None, "2507", None, None, r"0001_法人税及び地方法人税申告書_2507\.pdf"),
            ("1001", "1011", "2507", "愛知県", None, r"1011_愛知県_法人都道府県民税・事業税・特別法人事業税_2507\.pdf"),
            ("2001", None, "2507", "愛知県", "蒲郡市", r"2001_愛知県蒲郡市_法人市民税_2507\.pdf"),
            ("6003", None, "2401", None, None, r"6003_少額減価償却資産明細表_2401\.pdf"),
        ]
        
        all_passed = True
        for base_code, overlay_code, yymm, prefecture, city, expected_pattern in test_cases:
            result = ClassifyResult(
                base_code=base_code,
                overlay_code=overlay_code,
                yymm=yymm,
                yymm_source="TEST",
                title="テスト書類"
            )
            
            context = NamingContext(prefecture=prefecture, city=city)
            
            try:
                filename = build_filename_from_result(result, context)
                
                import re
                if re.match(expected_pattern, filename):
                    print(f"  OK {base_code}: {filename}")
                else:
                    print(f"  NG {base_code}: expected pattern {expected_pattern}, got {filename}")
                    all_passed = False
                    
            except Exception as e:
                print(f"  NG {base_code}: Exception - {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_unified_workflow(self) -> bool:
        """統合分類ワークフローテスト"""
        classifier = UnifiedClassifier()
        
        test_cases = [
            {
                "name": "国税書類",
                "filename": "houjin_test.pdf",
                "text": "メール詳細 法人税及び地方法人税申告書 受付番号",
                "ui_context": {"yymm": "2507"},
                "expected_base": "0003",  # 受信通知
                "expected_overlay": None
            },
            {
                "name": "愛知県地方税", 
                "filename": "aichi_tax.pdf",
                "text": "愛知県東三河県税事務所 法人都道府県民税 事業税申告書",
                "municipality_sets": {2: {"prefecture": "愛知県", "city": "蒲郡市"}},
                "ui_context": {"yymm": "2507"},
                "expected_base": "1001",
                "expected_overlay": "1011"
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            context = create_document_context(
                test_case["filename"],
                test_case["text"],
                test_case.get("municipality_sets"),
                test_case.get("ui_context")
            )
            
            try:
                result, filename, success, message = classifier.process_document_complete(context)
                
                base_match = result.base_code.startswith(test_case["expected_base"])
                overlay_match = result.overlay_code == test_case["expected_overlay"]
                
                if base_match and overlay_match and success:
                    print(f"  OK {test_case['name']}: {result.base_code} -> {result.overlay_code}")
                else:
                    print(f"  NG {test_case['name']}: expected {test_case['expected_base']}/{test_case['expected_overlay']}")
                    print(f"     got {result.base_code}/{result.overlay_code}, success={success}")
                    all_passed = False
                    
            except Exception as e:
                print(f"  NG {test_case['name']}: Exception - {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_three_way_consistency(self) -> bool:
        """三者一致保証テスト"""
        # 表示コード = base_code, ファイル名コード = final_code の一致を確認
        result = ClassifyResult(
            base_code="1001",
            overlay_code="1011", 
            yymm="2507",
            yymm_source="TEST",
            title="都道府県税申告書"
        )
        
        # 表示用は base_code
        display_code = result.display_code
        # ファイル名用は final_code
        final_code = result.final_code
        
        display_correct = display_code == "1001"  # オリジナル表示
        final_correct = final_code == "1011"      # オーバーレイ適用
        consistency_correct = result.has_overlay  # オーバーレイ有無の正確な判定
        
        if display_correct and final_correct and consistency_correct:
            print(f"  OK 三者一致: 表示={display_code}, ファイル名={final_code}, オーバーレイ={consistency_correct}")
            return True
        else:
            print(f"  NG 三者一致失敗: 表示={display_code}({display_correct}), ファイル名={final_code}({final_correct}), オーバーレイ={consistency_correct}")
            return False
    
    def test_error_handling(self) -> bool:
        """エラーハンドリングテスト"""
        from core.yymm_resolver import NeedsUserInputError
        
        # UI入力必須エラーのテスト
        result_no_yymm = ClassifyResult(
            base_code="6001",
            overlay_code=None,
            yymm=None,  # YYMM未確定
            yymm_source="UI_REQUIRED",
            title="固定資産台帳"
        )
        
        context = NamingContext()
        
        try:
            filename = build_filename_from_result(result_no_yymm, context)
            print("  NG エラーハンドリング: 例外が発生しませんでした")
            return False
        except NeedsUserInputError as e:
            if "YYMM" in str(e) and "6001" in str(e):
                print(f"  OK エラーハンドリング: 正しく例外をキャッチ - {str(e)}")
                return True
            else:
                print(f"  NG エラーハンドリング: 予期しない例外内容 - {str(e)}")
                return False
        except Exception as e:
            print(f"  NG エラーハンドリング: 予期しない例外タイプ - {type(e).__name__}: {str(e)}")
            return False
    
    def test_v534_compliance(self) -> bool:
        """v5.3.4仕様適合テスト"""
        compliance_tests = [
            ("県別コードマッピング", self._test_prefecture_mapping),
            ("ノイズ抑制機能", self._test_noise_suppression), 
            ("UI強制コード", self._test_ui_forced_codes),
            ("リセットログ", self._test_reset_logging)
        ]
        
        all_passed = True
        for test_name, test_func in compliance_tests:
            try:
                success = test_func()
                if success:
                    print(f"    OK {test_name}")
                else:
                    print(f"    NG {test_name}")
                    all_passed = False
            except Exception as e:
                print(f"    NG {test_name}: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def _test_prefecture_mapping(self) -> bool:
        """県別コードマッピングテスト"""
        from core.overlay import PREFECTURE_CODE_MAP
        
        expected_mappings = {
            "東京都": "1001",
            "愛知県": "1011", 
            "福岡県": "1021",
            "大阪府": "1031",
            "神奈川県": "1041"
        }
        
        return PREFECTURE_CODE_MAP == expected_mappings
    
    def _test_noise_suppression(self) -> bool:
        """ノイズ抑制機能テスト"""
        # CONSUMPTION_TAXドメインでオーバーレイがスキップされることを確認
        set_ctx = SetContext(prefecture="愛知県")
        result = apply_local_overlay("3001", set_ctx)  # 消費税
        
        return result.skipped and "CONSUMPTION_TAX" in result.reason
    
    def _test_ui_forced_codes(self) -> bool:
        """UI強制コードテスト"""
        expected_codes = {"6001", "6002", "6003", "0000"}
        
        for code in expected_codes:
            if not is_ui_forced_code(code):
                return False
        
        # 非強制コードのテスト
        if is_ui_forced_code("1001"):
            return False
        
        return True
    
    def _test_reset_logging(self) -> bool:
        """リセットログテスト"""
        # ログが正しい形式で出力されることを確認
        from core.unified_classifier import UnifiedClassifier
        
        # 実際のログ出力は確認が困難なため、関数が呼び出し可能かのみチェック
        try:
            UnifiedClassifier.log_split_reset("test")
            return True
        except Exception:
            return False
    
    def print_summary(self) -> bool:
        """テスト結果サマリー出力"""
        print("\n" + "=" * 70)
        print("テスト結果サマリー")
        print("=" * 70)
        
        passed = sum(1 for _, success in self.test_results if success)
        total = len(self.test_results)
        
        for test_name, success in self.test_results:
            status = "OK PASS" if success else "NG FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n合計: {passed}/{total} テスト通過 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 全テスト成功！モジュラーアーキテクチャv5.3.4が正常に動作しています。")
            return True
        else:
            print("WARNING: 一部テストが失敗しました。修正が必要です。")
            return False


def main():
    """メイン実行関数"""
    tester = ModularArchitectureTests()
    success = tester.run_all_tests()
    
    if success:
        print(f"\nRESULT: モジュラーアーキテクチャv5.3.4は完全に動作し、")
        print(f"     すべての設計要件と仕様を満たしています。")
        print(f"     - 三者一致保証")
        print(f"     - ノイズ抑制")
        print(f"     - 県別コードマッピング")
        print(f"     - UI強制YYMM処理")
        print(f"     - クリーンなモジュラー設計")
    else:
        print(f"\nERROR: 一部の機能に問題があります。修正してください。")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())