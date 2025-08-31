#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 スモークテストスクリプト
基本的な動作確認を実施
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from core.runtime_paths import (
        validate_tesseract_resources, 
        get_debug_info,
        get_tesseract_executable_path,
        get_tessdata_dir_path
    )
    from core.classification_v5 import DocumentClassifierV5
    import pytesseract
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("必要なモジュールが見つかりません。v4.0ディレクトリから実行してください。")
    sys.exit(1)


class SmokeTestRunner:
    """スモークテスト実行クラス"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """テスト結果をログに記録"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
        
        print(result)
        self.test_results.append((test_name, success, message))
        
        if not success:
            self.failed_tests.append(test_name)
    
    def test_tesseract_resources(self) -> bool:
        """Tesseractリソース存在確認テスト"""
        try:
            is_valid = validate_tesseract_resources()
            if is_valid:
                self.log_result("Tesseractリソース確認", True, "全てのリソースが存在")
                return True
            else:
                self.log_result("Tesseractリソース確認", False, "リソースが不足")
                return False
        except Exception as e:
            self.log_result("Tesseractリソース確認", False, f"例外: {e}")
            return False
    
    def test_tesseract_execution(self) -> bool:
        """Tesseract実行テスト"""
        try:
            version = pytesseract.get_tesseract_version()
            self.log_result("Tesseract実行確認", True, f"バージョン: {version}")
            return True
        except Exception as e:
            self.log_result("Tesseract実行確認", False, f"実行失敗: {e}")
            return False
    
    def test_classification_engine(self) -> bool:
        """分類エンジン初期化テスト"""
        try:
            classifier = DocumentClassifierV5(debug_mode=True)
            self.log_result("分類エンジン初期化", True, "正常に初期化")
            return True
        except Exception as e:
            self.log_result("分類エンジン初期化", False, f"初期化失敗: {e}")
            return False
    
    def test_classification_basic(self) -> bool:
        """基本分類テスト"""
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            
            # テストケース
            test_cases = [
                {
                    "text": "メール詳細 種目 法人税及び地方法人税申告書 受信通知",
                    "filename": "houjin_receipt.pdf",
                    "expected_code": "0003"
                },
                {
                    "text": "消費税及び地方消費税申告書 平成",
                    "filename": "shouhizei.pdf", 
                    "expected_code": "3001"
                },
                {
                    "text": "納付情報 消費税",
                    "filename": "shouhizei_payment.pdf",
                    "expected_code": "3004"
                }
            ]
            
            passed = 0
            for case in test_cases:
                result = classifier.classify_document_v5(case["text"], case["filename"])
                if result.document_code.startswith(case["expected_code"][:4]):
                    passed += 1
                    print(f"  ✅ {case['filename']}: {result.document_code} ({result.document_name})")
                else:
                    print(f"  ❌ {case['filename']}: 期待{case['expected_code']} 実際{result.document_code}")
            
            success = passed == len(test_cases)
            self.log_result("基本分類テスト", success, f"{passed}/{len(test_cases)}件成功")
            return success
            
        except Exception as e:
            self.log_result("基本分類テスト", False, f"例外: {e}")
            return False
    
    def test_file_operations(self) -> bool:
        """ファイル操作テスト"""
        try:
            # 一時ディレクトリでファイル操作テスト
            with tempfile.TemporaryDirectory() as temp_dir:
                # テスト用ファイル作成
                test_file = os.path.join(temp_dir, "test.txt")
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write("テストファイル")
                
                # ファイル存在確認
                if not os.path.exists(test_file):
                    self.log_result("ファイル操作テスト", False, "ファイル作成に失敗")
                    return False
                
                # ファイル読み込みテスト
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content != "テストファイル":
                    self.log_result("ファイル操作テスト", False, "ファイル読み込み内容が異なる")
                    return False
                
                self.log_result("ファイル操作テスト", True, "正常に動作")
                return True
                
        except Exception as e:
            self.log_result("ファイル操作テスト", False, f"例外: {e}")
            return False
    
    def test_encoding(self) -> bool:
        """日本語エンコーディングテスト"""
        try:
            test_strings = [
                "法人税及び地方法人税申告書",
                "消費税及び地方消費税申告書", 
                "東京都港区",
                "愛知県蒲郡市",
                "受信通知",
                "納付情報"
            ]
            
            for test_str in test_strings:
                # エンコード・デコードテスト
                encoded = test_str.encode('utf-8')
                decoded = encoded.decode('utf-8')
                
                if decoded != test_str:
                    self.log_result("日本語エンコーディングテスト", False, f"文字化け: {test_str}")
                    return False
            
            self.log_result("日本語エンコーディングテスト", True, "正常に処理")
            return True
            
        except Exception as e:
            self.log_result("日本語エンコーディングテスト", False, f"例外: {e}")
            return False
    
    def print_system_info(self):
        """システム情報の表示"""
        print("\n=== システム情報 ===")
        debug_info = get_debug_info()
        for key, value in debug_info.items():
            print(f"{key}: {value}")
    
    def print_summary(self):
        """テスト結果サマリーの表示"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success, _ in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        print(f"\n=== テスト結果サマリー ===")
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n失敗したテスト:")
            for test_name in self.failed_tests:
                print(f"  - {test_name}")
        
        return failed_tests == 0
    
    def run_all_tests(self) -> bool:
        """全テストを実行"""
        print("=== 税務書類リネームシステム v5.0 スモークテスト ===")
        print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # システム情報表示
        self.print_system_info()
        
        print("\n=== テスト実行 ===")
        
        # 各テスト実行
        tests = [
            self.test_tesseract_resources,
            self.test_tesseract_execution,
            self.test_file_operations,
            self.test_encoding,
            self.test_classification_engine,
            self.test_classification_basic,
        ]
        
        for test in tests:
            test()
        
        # 結果サマリー
        success = self.print_summary()
        
        if success:
            print("\n🎉 全テストが正常に完了しました！")
            print("システムは受け入れ準備ができています。")
        else:
            print("\n⚠️  一部テストが失敗しました。")
            print("失敗したテストを確認して問題を修正してください。")
        
        return success


def main():
    """メイン関数"""
    runner = SmokeTestRunner()
    success = runner.run_all_tests()
    
    # 終了コード設定
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()