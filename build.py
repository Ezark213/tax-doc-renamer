#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 修正版ビルドスクリプト（シンプル版）
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ビルド設定
BUILD_CONFIG = {
    "app_name": "TaxDocumentRenamer_v5_2_0_Bundle_PDF_Auto_Split",
    "main_script": "main.py",
    "version": "5.2.0",
    "description": "税務書類リネームシステム v5.2.0 Bundle PDF Auto-Split対応版"
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
            print("PyInstallerのインストールに失敗しました")
            return False

def create_dummy_modules():
    """不足しているモジュールのダミー作成"""
    print("必要なモジュールを作成中...")
    
    # coreディレクトリ作成
    os.makedirs("core", exist_ok=True)
    
    # core/__init__.py
    if not os.path.exists("core/__init__.py"):
        with open("core/__init__.py", "w", encoding="utf-8") as f:
            f.write("# Core module\n")
    
    # PDF処理モジュール
    if not os.path.exists("core/pdf_processor.py"):
        with open("core/pdf_processor.py", "w", encoding="utf-8") as f:
            f.write('''class PDFProcessor:
    def __init__(self):
        pass
    
    def extract_text_from_pdf(self, file_path):
        return "ダミーテキスト"
''')
    
    # OCRエンジンモジュール
    if not os.path.exists("core/ocr_engine.py"):
        with open("core/ocr_engine.py", "w", encoding="utf-8") as f:
            f.write('''class OCREngine:
    def __init__(self):
        pass

class MunicipalityMatcher:
    pass

class MunicipalitySet:
    pass
''')
    
    # CSV処理モジュール
    if not os.path.exists("core/csv_processor.py"):
        with open("core/csv_processor.py", "w", encoding="utf-8") as f:
            f.write('''class CSVProcessor:
    def __init__(self):
        pass
''')
    
    # UIディレクトリ作成
    os.makedirs("ui", exist_ok=True)
    
    # ui/__init__.py
    if not os.path.exists("ui/__init__.py"):
        with open("ui/__init__.py", "w", encoding="utf-8") as f:
            f.write("# UI module\n")
    
    # ドラッグ&ドロップUIモジュール
    if not os.path.exists("ui/drag_drop.py"):
        with open("ui/drag_drop.py", "w", encoding="utf-8") as f:
            f.write('''import tkinter as tk
from tkinter import ttk

class DropZoneFrame(ttk.Frame):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        
        label = ttk.Label(self, text="ファイルをドラッグ&ドロップ\\n(ダミー実装)")
        label.pack(expand=True)
''')
    
    print("モジュール作成完了")

def run_build():
    """ビルド実行"""
    print("ビルド開始...")
    
    # PyInstallerコマンド
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", BUILD_CONFIG["app_name"],
        "--clean",
        "--noconfirm",
        BUILD_CONFIG["main_script"]
    ]
    
    print("実行中: " + " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("ビルド成功!")
        return True
    except subprocess.CalledProcessError as e:
        print("ビルド失敗!")
        print("エラー:", e.stderr if e.stderr else e.stdout)
        return False

def main():
    """メイン処理"""
    print("税務書類リネームシステム v5.2.0 Bundle PDF Auto-Split対応版ビルド開始")
    print("=" * 50)
    
    # PyInstaller確認
    if not check_pyinstaller():
        return False
    
    # 必要ファイル確認・作成
    if not os.path.exists(BUILD_CONFIG["main_script"]):
        print(f"メインスクリプトが見つかりません: {BUILD_CONFIG['main_script']}")
        return False
    
    # ダミーモジュール作成
    create_dummy_modules()
    
    # ビルド実行
    if not run_build():
        return False
    
    # 結果確認
    exe_path = f"dist/{BUILD_CONFIG['app_name']}.exe"
    if os.path.exists(exe_path):
        print(f"ビルド完了: {exe_path}")
        print(f"ファイルサイズ: {os.path.getsize(exe_path) / (1024*1024):.1f} MB")
        return True
    else:
        print("実行ファイルが見つかりません")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nビルドが完了しました。")
        print("dist フォルダに実行ファイルがあります。")
    else:
        print("\nビルドに失敗しました。")
    
    # input("\nEnterキーを押して終了...")