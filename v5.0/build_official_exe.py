#!/usr/bin/env python3
"""
正式版税務書類リネームexeを作成（PyMuPDF + OCR対応）
"""

import os
import subprocess
import shutil

def build_official_exe():
    """正式版exeをビルド"""
    print("正式版税務書類リネームexe（OCR対応）を作成中...")
    
    # 元のソースファイルを使用
    source_file = r"C:\Users\pukur\tax-doc-renamer\tax_document_renamer.py"
    
    if not os.path.exists(source_file):
        print(f"エラー: {source_file} が見つかりません")
        return False
    
    # 作業ディレクトリに移動
    work_dir = r"C:\Users\pukur\Desktop\TaxRenamer_Tools"
    os.chdir(work_dir)
    
    # ビルドディレクトリをクリア
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # PyInstallerコマンド（完全版）
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=TaxDocumentRenamer_Official_v2.9",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=fitz",
        "--hidden-import=PyPDF2",
        "--hidden-import=pytesseract",
        "--collect-all=pytesseract",
        "--collect-all=PyMuPDF",
        source_file
    ]
    
    try:
        print("PyInstallerを実行中（OCR + PyMuPDF対応）...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        exe_path = os.path.join("dist", "TaxDocumentRenamer_Official_v2.9.exe")
        if os.path.exists(exe_path):
            # リネームアプリフォルダにコピー
            dest_dir = r"C:\Users\pukur\Desktop\リネームアプリ"
            dest_path = os.path.join(dest_dir, "TaxDocumentRenamer_Official_v2.9.exe")
            shutil.copy2(exe_path, dest_path)
            
            print("="*50)
            print("正式版 TaxDocumentRenamer_Official_v2.9.exe が作成されました!")
            print(f"場所: {dest_path}")
            print("機能:")
            print("- OCR機能（Tesseract）完全対応")
            print("- PyMuPDF によるPDF高度処理")
            print("- タブ形式UI（ファイル選択・結果・ログ）")
            print("- 複数自治体対応")
            print("- 自動書類判定・リネーム")
            print("="*50)
            return True
        else:
            print("実行ファイルの作成に失敗しました")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"ビルドエラー: {e}")
        if e.stderr:
            print(f"エラー出力: {e.stderr}")
        return False

if __name__ == "__main__":
    success = build_official_exe()
    if success:
        print("\n🎉 成功！")
        print("次のステップ:")
        print("1. デスクトップの「リネームアプリ」フォルダを開く")
        print("2. TaxDocumentRenamer_Official_v2.9.exe をダブルクリック")
        print("3. 正式版の高機能リネーマーが起動します")
    else:
        print("\nビルドに失敗しました")
    
    input("\n何かキーを押してください...")