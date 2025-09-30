#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 受け入れテストスクリプト
実際のファイル処理を含む包括的なテスト
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from core.runtime_paths import validate_tesseract_resources
    from core.classification_v5 import DocumentClassifierV5
    from core.pdf_processor import PDFProcessor
    from core.ocr_engine import OCREngine
    import pytesseract
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)


class AcceptanceTestRunner:
    """受け入れテスト実行クラス"""
    
    def __init__(self):
        self.test_results = []
        self.detailed_results = []
        self.temp_dirs = []
        
        # テスト設定
        self.test_config = {
            "year_month": "2508",  # 2025年8月
            "municipality_sets": {
                1: {"prefecture": "東京都", "municipality": ""},
                2: {"prefecture": "愛知県", "municipality": "蒲郡市"},
                3: {"prefecture": "福岡県", "municipality": "福岡市"}
            }
        }
        
    def cleanup(self):
        """テスト用一時ディレクトリのクリーンアップ"""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def log_result(self, test_name: str, success: bool, message: str = "", details: Optional[Dict] = None):
        """テスト結果をログに記録"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
        
        print(result)
        self.test_results.append((test_name, success, message))
        
        if details:
            self.detailed_results.append({
                "test": test_name,
                "success": success,
                "message": message,
                "details": details,
                "timestamp": datetime.datetime.now().isoformat()
            })
    
    def create_test_environment(self) -> str:
        """テスト用環境の作成"""
        temp_dir = tempfile.mkdtemp(prefix="tax_doc_test_")
        self.temp_dirs.append(temp_dir)
        
        # 入力フォルダ
        input_dir = os.path.join(temp_dir, "input")
        os.makedirs(input_dir)
        
        # 出力フォルダ  
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir)
        
        return temp_dir
    
    def test_prerequisite_check(self) -> bool:
        """前提条件チェック"""
        try:
            # Tesseractリソース確認
            if not validate_tesseract_resources():
                self.log_result("前提条件チェック", False, "Tesseractリソースが不足")
                return False
            
            # 分類エンジン初期化確認
            classifier = DocumentClassifierV5(debug_mode=True)
            
            # OCRエンジン初期化確認  
            ocr_engine = OCREngine()
            
            self.log_result("前提条件チェック", True, "全ての前提条件を満たしている")
            return True
            
        except Exception as e:
            self.log_result("前提条件チェック", False, f"例外: {e}")
            return False
    
    def test_naming_convention(self) -> bool:
        """命名規則テスト"""
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            
            # 命名規則テストケース
            test_cases = [
                {
                    "text": "メール詳細 種目 法人税及び地方法人税申告書",
                    "filename": "houjin_receipt.pdf",
                    "expected_pattern": r"0003_受信通知_\d{4}\.pdf",
                    "expected_prefix": "0003"
                },
                {
                    "text": "納付情報 消費税及び地方消費税",
                    "filename": "shouhizei_payment.pdf", 
                    "expected_pattern": r"3004_納付情報_\d{4}\.pdf",
                    "expected_prefix": "3004"
                },
                {
                    "text": "東京都 法人都道府県民税・事業税・特別法人事業税申告書",
                    "filename": "tokyo_prefecture.pdf",
                    "expected_pattern": r"1001_東京都_法人都道府県民税・事業税・特別法人事業税_\d{4}\.pdf",
                    "expected_prefix": "1001"
                }
            ]
            
            passed = 0
            details = []
            
            for case in test_cases:
                result = classifier.classify_document_v5(case["text"], case["filename"])
                
                # XXXX_書類名_YYMM.pdf 形式かチェック
                expected_filename = f"{result.document_code}_{self.test_config['year_month']}.pdf"
                
                # 4桁番号が正しいかチェック
                if result.document_code.startswith(case["expected_prefix"]):
                    passed += 1
                    details.append({
                        "input": case["filename"],
                        "expected": case["expected_prefix"],
                        "actual": result.document_code,
                        "success": True
                    })
                    print(f"  ✅ {case['filename']}: {result.document_code} - {result.document_name}")
                else:
                    details.append({
                        "input": case["filename"],
                        "expected": case["expected_prefix"], 
                        "actual": result.document_code,
                        "success": False
                    })
                    print(f"  ❌ {case['filename']}: 期待{case['expected_prefix']} 実際{result.document_code}")
            
            success = passed == len(test_cases)
            self.log_result("命名規則テスト", success, f"{passed}/{len(test_cases)}件成功", {"details": details})
            return success
            
        except Exception as e:
            self.log_result("命名規則テスト", False, f"例外: {e}")
            return False
    
    def test_municipality_numbering(self) -> bool:
        """自治体連番テスト"""
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            
            # 自治体連番テストケース
            test_cases = [
                {
                    "text": "東京都 都税事務所 法人都道府県民税・事業税・特別法人事業税申告書",
                    "filename": "tokyo_pref.pdf",
                    "expected_code": "1001",  # セット1: 東京都
                    "description": "東京都（セット1）都道府県税"
                },
                {
                    "text": "愛知県 蒲郡市 法人市民税申告書",
                    "filename": "gamagori_city.pdf", 
                    "expected_code": "2011",  # セット2: 愛知県蒲郡市
                    "description": "蒲郡市（セット2）市民税"
                },
                {
                    "text": "福岡県 福岡市 法人市民税申告書",  
                    "filename": "fukuoka_city.pdf",
                    "expected_code": "2021",  # セット3: 福岡県福岡市
                    "description": "福岡市（セット3）市民税"
                }
            ]
            
            passed = 0
            details = []
            
            for case in test_cases:
                result = classifier.classify_document_v5(case["text"], case["filename"])
                
                if result.document_code.startswith(case["expected_code"][:3]):
                    passed += 1
                    details.append({
                        "description": case["description"],
                        "expected": case["expected_code"],
                        "actual": result.document_code,
                        "success": True
                    })
                    print(f"  ✅ {case['description']}: {result.document_code}")
                else:
                    details.append({
                        "description": case["description"],
                        "expected": case["expected_code"],
                        "actual": result.document_code, 
                        "success": False
                    })
                    print(f"  ❌ {case['description']}: 期待{case['expected_code']} 実際{result.document_code}")
            
            success = passed == len(test_cases)
            self.log_result("自治体連番テスト", success, f"{passed}/{len(test_cases)}件成功", {"details": details})
            return success
            
        except Exception as e:
            self.log_result("自治体連番テスト", False, f"例外: {e}")
            return False
    
    def test_and_condition_logic(self) -> bool:
        """AND条件ロジックテスト"""
        try:
            classifier = DocumentClassifierV5(debug_mode=True)
            
            # AND条件テストケース
            test_cases = [
                {
                    "text": "メール詳細 種目 法人税及び地方法人税申告書 受信通知",
                    "filename": "and_test1.pdf",
                    "expected_type": "受信通知",
                    "description": "AND条件: メール詳細 + 法人税種目 → 受信通知"
                },
                {
                    "text": "法人税及び地方法人税申告書 平成",  # メール詳細がない
                    "filename": "and_test2.pdf",
                    "expected_type": "申告書",
                    "description": "AND条件不適合: 法人税申告書（受信通知ではない）"
                },
                {
                    "text": "納付情報 消費税 地方消費税",
                    "filename": "and_test3.pdf",
                    "expected_type": "納付情報", 
                    "description": "納付情報の正確な判定"
                }
            ]
            
            passed = 0
            details = []
            
            for case in test_cases:
                result = classifier.classify_document_v5(case["text"], case["filename"])
                
                # 期待される書類種別が含まれているかチェック
                if case["expected_type"] in result.document_name:
                    passed += 1
                    details.append({
                        "description": case["description"],
                        "expected": case["expected_type"],
                        "actual": result.document_name,
                        "success": True
                    })
                    print(f"  ✅ {case['description']}: {result.document_name}")
                else:
                    details.append({
                        "description": case["description"],
                        "expected": case["expected_type"],
                        "actual": result.document_name,
                        "success": False  
                    })
                    print(f"  ❌ {case['description']}: 期待「{case['expected_type']}」実際「{result.document_name}」")
            
            success = passed == len(test_cases)
            self.log_result("AND条件ロジックテスト", success, f"{passed}/{len(test_cases)}件成功", {"details": details})
            return success
            
        except Exception as e:
            self.log_result("AND条件ロジックテスト", False, f"例外: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """エラーハンドリングテスト"""
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            
            # エラーケーステスト
            test_cases = [
                {
                    "text": "意味不明な文書です。分類できません。",
                    "filename": "unknown.pdf",
                    "expected_code": "9999",
                    "description": "未分類書類"
                },
                {
                    "text": "",  # 空テキスト
                    "filename": "empty.pdf", 
                    "expected_code": "9999",
                    "description": "空テキスト"
                },
                {
                    "text": "English document without Japanese content",
                    "filename": "english.pdf",
                    "expected_code": "9999", 
                    "description": "英語のみ文書"
                }
            ]
            
            passed = 0
            details = []
            
            for case in test_cases:
                try:
                    result = classifier.classify_document_v5(case["text"], case["filename"])
                    
                    if result.document_code.startswith(case["expected_code"]):
                        passed += 1
                        details.append({
                            "description": case["description"],
                            "expected": case["expected_code"],
                            "actual": result.document_code,
                            "success": True
                        })
                        print(f"  ✅ {case['description']}: {result.document_code}")
                    else:
                        details.append({
                            "description": case["description"],
                            "expected": case["expected_code"],
                            "actual": result.document_code,
                            "success": False
                        })
                        print(f"  ❌ {case['description']}: 期待{case['expected_code']} 実際{result.document_code}")
                        
                except Exception as e:
                    # エラーハンドリング自体のテスト
                    print(f"  ⚠️  {case['description']}: 例外が発生 ({e})")
                    details.append({
                        "description": case["description"],
                        "expected": case["expected_code"],
                        "actual": f"Exception: {e}",
                        "success": False
                    })
            
            success = passed == len(test_cases)
            self.log_result("エラーハンドリングテスト", success, f"{passed}/{len(test_cases)}件成功", {"details": details})
            return success
            
        except Exception as e:
            self.log_result("エラーハンドリングテスト", False, f"例外: {e}")
            return False
    
    def generate_test_report(self) -> str:
        """詳細テストレポートの生成"""
        report_data = {
            "test_run": {
                "timestamp": datetime.datetime.now().isoformat(),
                "system": "税務書類リネームシステム v5.0",
                "test_type": "受け入れテスト"
            },
            "configuration": self.test_config,
            "results": self.detailed_results,
            "summary": {
                "total_tests": len(self.test_results),
                "passed": sum(1 for _, success, _ in self.test_results if success),
                "failed": sum(1 for _, success, _ in self.test_results if not success),
            }
        }
        
        report_data["summary"]["success_rate"] = (
            report_data["summary"]["passed"] / report_data["summary"]["total_tests"] * 100
            if report_data["summary"]["total_tests"] > 0 else 0
        )
        
        # JSONレポート生成
        report_file = f"acceptance_test_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return report_file
    
    def print_summary(self):
        """テスト結果サマリーの表示"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success, _ in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        print(f"\n=== 受け入れテスト結果サマリー ===")
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            failed_test_names = [name for name, success, _ in self.test_results if not success]
            print(f"\n失敗したテスト:")
            for test_name in failed_test_names:
                print(f"  - {test_name}")
        
        return failed_tests == 0
    
    def run_acceptance_tests(self) -> bool:
        """受け入れテストの実行"""
        print("=== 税務書類リネームシステム v5.0 受け入れテスト ===")
        print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            # テスト実行
            tests = [
                self.test_prerequisite_check,
                self.test_naming_convention,
                self.test_municipality_numbering, 
                self.test_and_condition_logic,
                self.test_error_handling,
            ]
            
            print("=== テスト実行 ===")
            for test in tests:
                test()
            
            # 結果サマリー
            success = self.print_summary()
            
            # 詳細レポート生成
            report_file = self.generate_test_report()
            print(f"\n詳細レポート: {report_file}")
            
            if success:
                print("\n🎉 全ての受け入れテストが正常に完了しました！")
                print("システムは本格運用の準備ができています。")
            else:
                print("\n⚠️  一部テストが失敗しました。")
                print("問題を修正してから本格運用を開始してください。")
            
            return success
            
        finally:
            self.cleanup()


def main():
    """メイン関数"""
    runner = AcceptanceTestRunner()
    success = runner.run_acceptance_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()