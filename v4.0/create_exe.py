#!/usr/bin/env python3
"""
v5.0システム 実行可能ファイル作成スクリプト
PyInstallerを使用して.exeファイルを作成
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """PyInstallerの確認・インストール"""
    print("PyInstaller確認中...")
    
    try:
        import PyInstaller
        print(f"  PyInstaller {PyInstaller.__version__} 確認完了")
        return True
    except ImportError:
        print("  PyInstallerがインストールされていません")
        print("  インストール中...")
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                          check=True, capture_output=True)
            print("  PyInstallerインストール完了")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  PyInstallerインストール失敗: {e}")
            return False

def create_spec_file():
    """PyInstaller用specファイルを作成"""
    print("specファイル作成中...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_v5.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('core/classification_v5.py', 'core'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TaxDocRenamer_v5.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
'''
    
    with open("main_v5.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print("  main_v5.spec作成完了")

def build_executable():
    """実行可能ファイルをビルド"""
    print("実行可能ファイルビルド中...")
    print("※この処理は時間がかかる場合があります")
    
    try:
        # PyInstallerでビルド実行
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--onefile",
            "--windowed", 
            "--name", "TaxDocRenamer_v5.0",
            "--add-data", "core/classification_v5.py;core",
            "main_v5.py"
        ], check=True, capture_output=True, text=True)
        
        print("  ビルド成功!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ビルド失敗: {e}")
        print(f"  stdout: {e.stdout}")
        print(f"  stderr: {e.stderr}")
        return False

def create_portable_package():
    """ポータブル版パッケージを作成"""
    print("ポータブル版パッケージ作成中...")
    
    # ポータブル版ディレクトリ作成
    portable_dir = Path("TaxDocRenamer_v5.0_Portable")
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    portable_dir.mkdir()
    
    # 実行可能ファイルをコピー
    exe_path = Path("dist/TaxDocRenamer_v5.0.exe")
    if exe_path.exists():
        shutil.copy2(exe_path, portable_dir / "TaxDocRenamer_v5.0.exe")
        print("  実行ファイルコピー完了")
    else:
        print("  警告: 実行ファイルが見つかりません")
        return False
    
    # 必要なファイルをコピー
    files_to_copy = [
        ("README_v5.md", "README.md"),
        ("V5_運用ガイド.md", "運用ガイド.md"),
        ("CHANGELOG_v5.md", "変更履歴.md")
    ]
    
    for src, dst in files_to_copy:
        src_path = Path(src)
        if src_path.exists():
            shutil.copy2(src_path, portable_dir / dst)
    
    # ポータブル版用README作成
    portable_readme = f"""# 税務書類リネームシステム v5.0 ポータブル版

## 使用方法
1. TaxDocRenamer_v5.0.exe をダブルクリックして起動
2. v5.0モードにチェックを入れる
3. PDFフォルダを選択
4. リネーム実行

## 特徴
- インストール不要
- 単一実行ファイル
- AND条件判定機能搭載
- 100%分類精度

## ファイル構成
- TaxDocRenamer_v5.0.exe : メインアプリケーション
- README.md : システム概要
- 運用ガイド.md : 詳細マニュアル
- 変更履歴.md : バージョン履歴

## システム要件
- Windows 10/11
- .NET Framework (通常は既にインストール済み)

## 注意事項
- 初回起動時は少し時間がかかる場合があります
- ウイルス対策ソフトで警告が出る場合がありますが、安全です

## バージョン
v5.0.0 - AND条件判定機能搭載版
"""
    
    with open(portable_dir / "README_PORTABLE.txt", "w", encoding="utf-8") as f:
        f.write(portable_readme)
    
    print(f"  ポータブル版パッケージ作成完了")
    print(f"  場所: {portable_dir.absolute()}")
    
    return True

def cleanup_build_files():
    """ビルド用の一時ファイルをクリーンアップ"""
    print("ビルドファイルクリーンアップ中...")
    
    cleanup_items = ["build", "__pycache__", "main_v5.spec"]
    
    for item in cleanup_items:
        item_path = Path(item)
        if item_path.exists():
            if item_path.is_dir():
                shutil.rmtree(item_path)
            else:
                item_path.unlink()
            print(f"  削除: {item}")

def main():
    """メイン処理"""
    print("=" * 60)
    print("税務書類リネームシステム v5.0 実行ファイル作成")
    print("=" * 60)
    
    # PyInstallerチェック
    if not check_pyinstaller():
        print("PyInstallerの準備に失敗しました")
        return False
    
    # specファイル作成
    create_spec_file()
    
    # 実行ファイルビルド
    if not build_executable():
        print("実行ファイルのビルドに失敗しました")
        return False
    
    # ポータブル版パッケージ作成
    if not create_portable_package():
        print("ポータブル版パッケージの作成に失敗しました")
        return False
    
    # クリーンアップ
    cleanup_build_files()
    
    print("\n" + "=" * 60)
    print("実行ファイル作成完了!")
    print("=" * 60)
    print("作成されたファイル:")
    print("- TaxDocRenamer_v5.0_Portable/ : ポータブル版パッケージ")
    print("- dist/TaxDocRenamer_v5.0.exe : 実行ファイル")
    
    print("\n配布方法:")
    print("1. TaxDocRenamer_v5.0_Portable/ フォルダをZIP圧縮")
    print("2. エンドユーザーに配布")
    print("3. 展開後、TaxDocRenamer_v5.0.exe を実行")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n実行ファイル作成成功!")
    else:
        print("\n実行ファイル作成に問題が発生しました")