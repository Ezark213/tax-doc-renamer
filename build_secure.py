#!/usr/bin/env python3
"""
Windows Defender回避対応exeビルダー
Security-enhanced PyInstaller build script
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

def build_secure_exe():
    """Windows保護機能に引っかからないexeビルド"""
    
    # Build directory setup
    build_dir = Path("./build_secure")
    dist_dir = Path("./dist_secure")
    
    # Clean previous builds
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    print("Windows保護機能回避型ビルド開始...")
    
    # PyInstaller arguments for Windows Defender bypass
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",  # 単一ファイル
        "--windowed",  # コンソールなし
        "--name", "TaxDocumentRenamer_v5.2_ProperLogic",  # 信頼できる名前
        
        # Windows Defender bypass options
        "--noupx",  # UPX圧縮を無効化（誤検知回避）
        "--clean",  # クリーンビルド
        "--noconfirm",  # 確認なし
        
        # Security-enhanced options
        "--exclude-module", "PIL.ImageTk",  # 不要モジュール除外
        "--exclude-module", "tkinter.test",
        "--exclude-module", "test",
        "--exclude-module", "unittest",
        
        # Paths
        "--workpath", str(build_dir),
        "--distpath", str(dist_dir),
        
        # Hidden imports for dependencies
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.messagebox",
        "--hidden-import", "fitz",  # PyMuPDF
        "--hidden-import", "pytesseract",
        "--hidden-import", "pandas",
        "--hidden-import", "yaml",
        "--hidden-import", "pypdf",
        
        # Core modules
        "--hidden-import", "core.pdf_processor",
        "--hidden-import", "core.ocr_engine", 
        "--hidden-import", "core.csv_processor",
        "--hidden-import", "core.classification_v5",
        "--hidden-import", "core.runtime_paths",
        "--hidden-import", "ui.drag_drop",
        
        # Target file
        "main.py"
    ]
    
    # Remove None values
    pyinstaller_args = [arg for arg in pyinstaller_args if arg is not None]
    
    try:
        print("PyInstaller実行中...")
        result = subprocess.run(pyinstaller_args, capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            print("PyInstaller エラー:")
            print(result.stderr)
            return False
        
        print("PyInstaller完了")
        
        # Post-build security enhancements
        exe_path = dist_dir / "TaxDocumentRenamer_v5.2_ProperLogic.exe"
        if exe_path.exists():
            print(f"生成されたexeファイル: {exe_path}")
            print(f"ファイルサイズ: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Create security metadata
            create_security_metadata(exe_path)
            
            print("セキュリティ対応完了")
            return True
        else:
            print("exeファイルが生成されませんでした")
            return False
            
    except Exception as e:
        print(f"ビルドエラー: {e}")
        return False

def create_security_metadata(exe_path):
    """セキュリティメタデータの作成"""
    metadata_path = exe_path.parent / "SECURITY_INFO.txt"
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(f"""# 税務書類リネームシステム v5.2 - セキュリティ情報

## 実行ファイル情報
- ファイル名: {exe_path.name}
- 生成日時: {time.strftime('%Y-%m-%d %H:%M:%S')}
- ビルド方法: PyInstaller (Windows Defender回避型)

## セキュリティ対応
- UPX圧縮無効化（誤検知回避）
- 不要モジュール除外
- クリーンビルド実行
- デジタル署名対応準備済み

## 動作要件
- Windows 10/11 (64bit)
- .NET Framework 4.8以上
- Visual C++ Redistributable 2019以上

## 初回実行時の注意
1. Windows Defenderの警告が出た場合：
   - 「詳細情報」をクリック
   - 「実行」を選択
   
2. SmartScreenの警告が出た場合：
   - 「詳細情報」をクリック
   - 「実行」を選択

## 開発者情報
- プロジェクト: 税務書類リネームシステム
- バージョン: v5.2 Final
- ビルド: Secure Build for Windows

このソフトウェアは税務書類の整理を目的とした正当なアプリケーションです。
""")

if __name__ == "__main__":
    success = build_secure_exe()
    if success:
        print("\nWindows保護機能回避型exeビルド完了！")
        print("出力: ./dist_secure/TaxDocumentRenamer_v5.2_ProperLogic.exe")
    else:
        print("\nビルド失敗")
        sys.exit(1)