#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 統合テストランナー
全てのテストを順次実行
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path

def run_test_script(script_path: str, description: str) -> bool:
    """テストスクリプトを実行"""
    print(f"\n{'='*60}")
    print(f"実行中: {description}")
    print(f"スクリプト: {script_path}")
    print('='*60)
    
    if not os.path.exists(script_path):
        print(f"❌ スクリプトが見つかりません: {script_path}")
        return False
    
    try:
        # Pythonスクリプト実行
        result = subprocess.run([
            sys.executable, script_path
        ], cwd=os.path.dirname(script_path), capture_output=False, text=True)
        
        success = result.returncode == 0
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"\n{description}: {status}")
        
        return success
        
    except Exception as e:
        print(f"❌ スクリプト実行中にエラー: {e}")
        return False

def main():
    """メイン関数"""
    print("=" * 80)
    print("税務書類リネームシステム v5.0 統合テスト")
    print(f"実行開始: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # テスト実行順序
    tests = [
        {
            "script": "smoke_test.py",
            "description": "スモークテスト（基本動作確認）",
            "required": True
        },
        {
            "script": "acceptance_test.py", 
            "description": "受け入れテスト（包括機能確認）",
            "required": True
        },
        {
            "script": "../test_v5.py",
            "description": "v5.0エンジンテスト",
            "required": False
        }
    ]
    
    # 現在のディレクトリ（testsディレクトリ）を基準とする
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    results = []
    
    # 各テスト実行
    for test in tests:
        script_path = os.path.join(current_dir, test["script"])
        script_path = os.path.normpath(script_path)
        
        success = run_test_script(script_path, test["description"])
        results.append({
            "name": test["description"],
            "success": success,
            "required": test["required"]
        })
        
        # 必須テストが失敗した場合は停止
        if test["required"] and not success:
            print(f"\n⚠️ 必須テスト「{test['description']}」が失敗したため、テストを中断します。")
            break
    
    # 結果サマリー
    print(f"\n{'='*80}")
    print("統合テスト結果サマリー")
    print(f"完了時刻: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"実行テスト数: {total_tests}")
    print(f"成功: {passed_tests}")
    print(f"失敗: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 全てのテストが正常に完了しました！")
        print("✅ システムは本格運用の準備ができています。")
        
        print("\n次のステップ:")
        print("1. Tesseractリソースファイルの配置（resources/tesseract/README.md参照）")
        print("2. ビルドスクリプトの実行（build_win_portable.bat等）")
        print("3. 実際のPDFファイルでの動作確認")
        print("4. 本格運用開始")
        
        return True
    else:
        print("\n⚠️ 一部テストが失敗しました。")
        print("\n失敗したテスト:")
        for result in results:
            if not result["success"]:
                required_str = "（必須）" if result["required"] else "（任意）"
                print(f"  - {result['name']} {required_str}")
        
        print("\n対処方法:")
        print("1. 失敗したテストのエラーメッセージを確認")
        print("2. Tesseractリソースの配置状況を確認")
        print("3. 必要に応じてシステム要件を確認")
        print("4. 問題修正後に再度テストを実行")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)