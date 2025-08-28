#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 完全版ビルドスクリプト
"""

import os
import sys
import subprocess
import shutil

def check_pyinstaller():
    """PyInstallerの確認・インストール"""
    print("PyInstallerをチェック...")
    try:
        import PyInstaller
        print("PyInstaller: 利用可能")
        return True
    except ImportError:
        print("PyInstallerをインストール中...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller: インストール完了")
            return True
        except subprocess.CalledProcessError:
            print("PyInstallerのインストールに失敗")
            return False

def build_complete_version():
    """完全版のビルド"""
    print("完全版をビルド中...")
    
    # ビルドコマンド
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "TaxDocumentRenamer_v5_Complete",
        "--clean",
        "--noconfirm",
        "main_v5_complete.py"
    ]
    
    print("実行中:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("ビルド成功!")
        return True
    except subprocess.CalledProcessError as e:
        print("ビルド失敗!")
        print("エラー:", e.stderr if e.stderr else e.stdout)
        return False

def create_complete_package():
    """完全版パッケージ作成"""
    print("完全版パッケージを作成中...")
    
    package_dir = "dist/TaxDocumentRenamer_v5_Complete_Package"
    
    # パッケージディレクトリ作成
    os.makedirs(package_dir, exist_ok=True)
    
    # 実行ファイルコピー
    exe_source = "dist/TaxDocumentRenamer_v5_Complete.exe"
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, f"{package_dir}/TaxDocumentRenamer_v5_Complete.exe")
        print(f"実行ファイルをコピー: {exe_source}")
    
    # README作成
    readme_content = """# 税務書類リネームシステム v5.0 完全版

## 特徴
- セットベース連番システム
- 都道府県・市町村選択UI
- 確実なファイル選択機能（ドラッグ&ドロップ対応）
- OCR突合チェック
- 詳細な処理結果表示

## セット設定
- セット1: 東京都 (1001, 1003, 1004)
- セット2: 愛知県蒲郡市 (1011, 1013, 1014) + (2001, 2003, 2004)
- セット3: 福岡県福岡市 (1021, 1023, 1024) + (2011, 2013, 2014)

## 使用方法
1. TaxDocumentRenamer_v5_Complete.exe を実行
2. PDFファイルを選択（ドラッグ&ドロップまたはボタンクリック）
3. 年月設定 (例: 2508)
4. 自治体セット確認・変更
5. 「リネーム処理開始」をクリック
6. 処理結果確認

## 新機能
- 都道府県選択UI
- 市町村自動連動
- 処理結果の詳細表示
- CSV結果出力
- システムログ表示

## 修正内容
- ドラッグ&ドロップ機能の改善
- 都道府県選択UIの追加
- セット設定の可視化
- エラーハンドリングの強化

Version: 5.0 Complete
Build Date: 2024-08-28
"""
    
    with open(f"{package_dir}/README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"完全版パッケージ作成完了: {package_dir}")
    return package_dir

def main():
    """メイン処理"""
    print("税務書類リネームシステム v5.0 完全版ビルド開始")
    print("=" * 50)
    
    # PyInstaller確認
    if not check_pyinstaller():
        return False
    
    # メインスクリプト確認
    if not os.path.exists("main_v5_complete.py"):
        print("main_v5_complete.py が見つかりません")
        return False
    
    # ビルド実行
    if not build_complete_version():
        return False
    
    # パッケージ作成
    package_dir = create_complete_package()
    
    # 結果確認
    exe_path = f"{package_dir}/TaxDocumentRenamer_v5_Complete.exe"
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024*1024)
        print(f"完全版ビルド完了: {exe_path}")
        print(f"ファイルサイズ: {size:.1f} MB")
        return True
    else:
        print("実行ファイルが見つかりません")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n完全版ビルドが成功しました!")
        print("dist フォルダに実行ファイルがあります。")
    else:
        print("\nビルドに失敗しました。")
    
    input("\nEnterキーを押して終了...")