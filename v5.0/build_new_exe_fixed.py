#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新しいTaxDocumentRenamer.exeをビルドするスクリプト
"""

import os
import subprocess
import sys
import shutil

def build_exe():
    print("新しいTaxDocumentRenamer.exeをビルド中...")
    
    # 作業ディレクトリを税務書類リネーマーに変更
    source_dir = r"C:\Users\pukur\tax-doc-renamer"
    if not os.path.exists(source_dir):
        print("エラー: tax-doc-renamer フォルダが見つかりません")
        return False
        
    os.chdir(source_dir)
    print(f"作業ディレクトリ: {os.getcwd()}")
    
    # 出力ディレクトリをクリア
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # PyInstallerコマンド
    cmd = [
        "pyinstaller",
        "--onefile",                    # 単一実行ファイル
        "--windowed",                   # コンソールウィンドウを非表示
        "--name=TaxDocumentRenamer_v2.6_Fixed",  # 新しい名前
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--collect-all=pytesseract",
        "--add-data=requirements.txt;.",  # requirements.txtも含める
        "tax_document_renamer.py"
    ]
    
    try:
        print("PyInstallerを実行中...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # 成功した場合
        exe_path = os.path.join("dist", "TaxDocumentRenamer_v2.6_Fixed.exe")
        if os.path.exists(exe_path):
            # デスクトップのリネームアプリフォルダにコピー
            desktop_app_dir = r"C:\Users\pukur\Desktop\リネームアプリ"
            if not os.path.exists(desktop_app_dir):
                os.makedirs(desktop_app_dir)
            
            dest_path = os.path.join(desktop_app_dir, "TaxDocumentRenamer_v2.6_Fixed.exe")
            shutil.copy2(exe_path, dest_path)
            
            print("ビルド完了!")
            print(f"実行ファイル: {dest_path}")
            print("="*50)
            print("新しいTaxDocumentRenamer_v2.6_Fixed.exe が作成されました!")
            print("場所: C:\\Users\\pukur\\Desktop\\リネームアプリ\\")
            print("Tesseract OCR も既にインストールされているので、すぐに使用できます!")
            print("="*50)
            return True
        else:
            print("エラー: 実行ファイルが作成されませんでした")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"ビルドエラー: {e}")
        if e.stderr:
            print(f"エラー出力: {e.stderr}")
        return False
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return False

if __name__ == "__main__":
    success = build_exe()
    if success:
        print("\n次のステップ:")
        print("1. デスクトップの「リネームアプリ」フォルダを開く")
        print("2. TaxDocumentRenamer_v2.6_Fixed.exe をダブルクリック")
        print("3. PDFファイルを個別選択して処理を実行")
    else:
        print("\nビルドに失敗しました。エラーを確認してください。")
    
    input("\n続行するには何かキーを押してください...")