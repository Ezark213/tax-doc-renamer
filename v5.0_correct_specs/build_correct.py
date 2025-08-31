#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 正式版ビルドスクリプト
正しい仕様に基づく実装
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

def build_correct_version():
    """正式版のビルド"""
    print("正式版をビルド中...")
    
    # ビルドコマンド
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "TaxDocumentRenamer_v5_Correct",
        "--clean",
        "--noconfirm",
        "main_v5_correct.py"
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

def create_correct_package():
    """正式版パッケージ作成"""
    print("正式版パッケージを作成中...")
    
    package_dir = "dist/TaxDocumentRenamer_v5_Correct_Package"
    
    # パッケージディレクトリ作成
    os.makedirs(package_dir, exist_ok=True)
    
    # 実行ファイルコピー
    exe_source = "dist/TaxDocumentRenamer_v5_Correct.exe"
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, f"{package_dir}/TaxDocumentRenamer_v5_Correct.exe")
        print(f"実行ファイルをコピー: {exe_source}")
    
    # README作成
    readme_content = """# 税務書類リネームシステム v5.0 正式版

## 概要
正しい仕様に基づく税務書類自動リネームシステム正式版です。

## 主な特徴
- **最大5セット対応**: 自治体設定を最大5セットまで設定可能
- **東京都1番目制限**: 東京都は必ずセット1に配置（他の位置でエラー）
- **正確な連番体系**: 入力順通りに連番付与
- **完全仕様準拠**: 要件定義書・番号体系ガイドに完全準拠

## 連番体系
### 都道府県税（1000番台）
- 1番目: 1001, 2番目: 1011, 3番目: 1021, 4番目: 1031, 5番目: 1041

### 市町村税（2000番台）  
- 1番目: 2001, 2番目: 2011, 3番目: 2021, 4番目: 2031, 5番目: 2041

### 受信通知（市町村のみ）
- 1番目: 2003, 2番目: 2013, 3番目: 2023, 4番目: 2033, 5番目: 2043

## 重要なルール
1. **東京都制限**: 東京都は必ずセット1に入力（他の位置ではエラー）
2. **入力順連番**: 入力された順番通りに連番を付与
3. **東京都特例**: 東京都には市町村分（2000番台）の書類は存在しない
4. **最大5セット**: セット1～セット5まで設定可能

## 使用方法
1. TaxDocumentRenamer_v5_Correct.exe を実行
2. PDFファイルを選択（クリック選択）
3. 年月設定 (例: 2508)
4. 自治体セット設定（東京都は必ずセット1）
5. 「リネーム処理開始」をクリック
6. 処理結果確認

## セット設定例

### 例1: 複数自治体
- セット1: 東京都
- セット2: 愛知県 蒲郡市  
- セット3: 福岡県 福岡市
→ 結果: 東京都→1001, 愛知県→1011, 蒲郡市→2001, 福岡県→1021, 福岡市→2011

### 例2: 単一自治体（東京都）
- セット1: 東京都
→ 結果: 東京都→1001

### 例3: 単一自治体（その他）
- セット1: 大阪府 大阪市
→ 結果: 大阪府→1001, 大阪市→2001

## 新機能
- 最大5セット対応
- 東京都位置制限エラーチェック
- 正確な入力順連番システム
- 仕様準拠の完全実装

Version: 5.0 Correct Specs
Build Date: 2025-08-28
Base: TaxDocumentRenamer_v4.0_BugFixed_EnhancedBlankRemoval.exe
"""
    
    with open(f"{package_dir}/README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"正式版パッケージ作成完了: {package_dir}")
    return package_dir

def main():
    """メイン処理"""
    print("税務書類リネームシステム v5.0 正式版ビルド開始")
    print("=" * 50)
    
    # PyInstaller確認
    if not check_pyinstaller():
        return False
    
    # メインスクリプト確認
    if not os.path.exists("main_v5_correct.py"):
        print("main_v5_correct.py が見つかりません")
        return False
    
    # ビルド実行
    if not build_correct_version():
        return False
    
    # パッケージ作成
    package_dir = create_correct_package()
    
    # 結果確認
    exe_path = f"{package_dir}/TaxDocumentRenamer_v5_Correct.exe"
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024*1024)
        print(f"正式版ビルド完了: {exe_path}")
        print(f"ファイルサイズ: {size:.1f} MB")
        return True
    else:
        print("実行ファイルが見つかりません")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n正式版ビルドが成功しました!")
        print("dist フォルダに実行ファイルがあります。")
    else:
        print("\nビルドに失敗しました。")
    
    # 自動実行用にコメントアウト
    # input("\nEnterキーを押して終了...")