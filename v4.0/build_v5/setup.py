#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 セットアップスクリプト
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Python バージョン確認"""
    if sys.version_info < (3, 8):
        print("NG Python 3.8以上が必要です")
        print(f"現在のバージョン: {sys.version}")
        return False
    
    print(f"OK Python {sys.version.split()[0]} 確認完了")
    return True

def install_requirements():
    """必要なライブラリをインストール"""
    print("\n必要なライブラリのインストール中...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✅ ライブラリインストール完了")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ライブラリインストール失敗: {e}")
        return False

def setup_directories():
    """必要なディレクトリを作成"""
    print("\nディレクトリ設定中...")
    
    dirs_to_create = [
        "logs",
        "test_data", 
        "output"
    ]
    
    for dir_name in dirs_to_create:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"  ✓ {dir_name}/")
    
    return True

def run_initial_test():
    """初期テストを実行"""
    print("\n初期テスト実行中...")
    
    try:
        # インポートテスト
        sys.path.append(os.getcwd())
        from core.classification_v5 import DocumentClassifierV5
        
        # 基本機能テスト
        classifier = DocumentClassifierV5(debug_mode=False)
        result = classifier.classify_document_v5("テスト", "test.pdf")
        
        if hasattr(result, 'document_type'):
            print("✅ 基本機能テスト合格")
            return True
        else:
            print("❌ 基本機能テスト失敗")
            return False
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return False

def main():
    """メインセットアップ処理"""
    print("=" * 60)
    print("税務書類リネームシステム v5.0 セットアップ")
    print("=" * 60)
    
    # チェック項目
    checks = [
        ("Python バージョン確認", check_python_version),
        ("必要ライブラリインストール", install_requirements),
        ("ディレクトリ設定", setup_directories),
        ("初期テスト", run_initial_test)
    ]
    
    success_count = 0
    
    for name, check_func in checks:
        print(f"\n[{name}]")
        if check_func():
            success_count += 1
        else:
            print(f"❌ {name} に失敗しました")
            break
    
    print("\n" + "=" * 60)
    if success_count == len(checks):
        print("🎉 セットアップ完了！")
        print("\n使用方法:")
        print("1. python main_v5.py でアプリケーション起動")
        print("2. v5.0モードにチェックを入れる")
        print("3. PDFフォルダを選択してリネーム実行")
        print("\n確認方法:")
        print("- python test_v5.py でテスト実行")
        print("- docs/ フォルダで詳細マニュアル確認")
    else:
        print("❌ セットアップに失敗しました")
        print("エラーを修正して再度実行してください")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
