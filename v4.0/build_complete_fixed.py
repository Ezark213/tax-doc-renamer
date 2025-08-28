#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 完全修正版ビルドスクリプト
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ビルド設定
BUILD_CONFIG = {
    "app_name": "TaxDocumentRenamer_v6_Requirements",
    "main_script": "main_v6_requirements_fixed.py",
    "version": "6.0.0",
    "description": "税務書類リネームシステム v6.0 要件定義対応版"
}

def check_pyinstaller():
    """PyInstallerの確認・インストール"""
    print("PyInstallerをチェック中...")
    try:
        import PyInstaller
        print("PyInstaller: OK")
        return True
    except ImportError:
        print("PyInstallerが見つかりません。インストール中...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller: インストール完了")
            return True
        except subprocess.CalledProcessError:
            print("PyInstallerのインストールに失敗しました。")
            return False

def clean_build():
    """ビルド前クリーンアップ"""
    print("クリーンアップ中...")
    folders_to_clean = ['build', 'dist', '__pycache__']
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"削除: {folder}")

def create_spec_file():
    """specファイル作成"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{BUILD_CONFIG["main_script"]}'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'threading',
        'shutil',
        'pathlib',
        'typing',
        'csv',
        'datetime',
        're'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{BUILD_CONFIG["app_name"]}',
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
    
    spec_filename = f"{BUILD_CONFIG['app_name']}.spec"
    with open(spec_filename, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"specファイル作成: {spec_filename}")
    return spec_filename

def build_executable(spec_file):
    """実行ファイルビルド"""
    print("ビルド開始...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("ビルド成功!")
            return True
        else:
            print("ビルドエラー:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"ビルド中にエラーが発生しました: {e}")
        return False

def check_build_result():
    """ビルド結果確認"""
    exe_path = os.path.join("dist", f"{BUILD_CONFIG['app_name']}.exe")
    
    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
        print(f"ビルド完了: {exe_path}")
        print(f"ファイルサイズ: {file_size:.1f} MB")
        return True
    else:
        print("実行ファイルが見つかりません。")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print(f"{BUILD_CONFIG['description']} ビルド開始")
    print("=" * 60)
    
    # 前提条件チェック
    if not os.path.exists(BUILD_CONFIG['main_script']):
        print(f"エラー: {BUILD_CONFIG['main_script']} が見つかりません。")
        return False
    
    # PyInstallerチェック
    if not check_pyinstaller():
        return False
    
    # クリーンアップ（スキップ - 実行中のプロセスがある場合）
    try:
        clean_build()
    except Exception as e:
        print(f"クリーンアップをスキップしました: {e}")
    
    # specファイル作成
    spec_file = create_spec_file()
    
    # ビルド実行
    if not build_executable(spec_file):
        return False
    
    # 結果確認
    if not check_build_result():
        return False
    
    print("\\nビルドが完了しました。")
    print("dist フォルダに実行ファイルが生成されています。")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\\nビルドがキャンセルされました。")
    except Exception as e:
        print(f"\\n予期しないエラー: {e}")
        import traceback
        traceback.print_exc()