#!/usr/bin/env python3
"""
税務書類リネームシステム v3.0 完全版exe作成
"""

import os
import subprocess
import shutil

def build_v3_exe():
    """v3.0完全版exeをビルド"""
    print("税務書類リネームシステム v3.0 完全版exeを作成中...")
    
    # v3.0ソースファイルを使用
    source_file = r"C:\Users\pukur\tax-doc-renamer\tax_document_renamer_v3.py"
    
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
    
    # PyInstallerコマンド（v3.0完全版）
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=TaxDocumentRenamer_v3.0_Complete",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=fitz",
        "--hidden-import=PyPDF2",
        "--hidden-import=pytesseract",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--collect-all=pytesseract",
        "--collect-all=PyMuPDF",
        "--collect-all=pandas",
        source_file
    ]
    
    try:
        print("PyInstallerを実行中（v3.0 全機能対応）...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        exe_path = os.path.join("dist", "TaxDocumentRenamer_v3.0_Complete.exe")
        if os.path.exists(exe_path):
            # リネームアプリフォルダにコピー
            dest_dir = r"C:\Users\pukur\Desktop\リネームアプリ"
            dest_path = os.path.join(dest_dir, "TaxDocumentRenamer_v3.0_Complete.exe")
            shutil.copy2(exe_path, dest_path)
            
            print("="*60)
            print("* TaxDocumentRenamer_v3.0_Complete.exe が作成されました!")
            print(f"場所: {dest_path}")
            print()
            print("v3.0 新機能:")
            print("* 修正点1: 手動入力年月の最優先処理")
            print("* 修正点2: 国税受信通知一式の自動分割")
            print("* 修正点3: 税区分集計表の正確な分類（7001/7002）")
            print("* 修正点4: 法人税申告書の正しい分類")
            print("* 修正点5: 自治体別連番処理の強化")
            print("* 修正点6: 地方税受信通知一式の自動分割")
            print("* 修正点7: CSVファイル完全対応")
            print()
            print("技術仕様:")
            print("- OCR機能（Tesseract + 日本語対応）")
            print("- PDF分割機能（PyMuPDF）")
            print("- CSV処理機能（pandas）")
            print("- タブ形式UI（ファイル選択・結果・ログ）")
            print("- 最大5自治体対応")
            print("- 詳細ログ出力")
            print("="*60)
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
    success = build_v3_exe()
    if success:
        print("\n次のステップ:")
        print("1. デスクトップの「リネームアプリ」フォルダを開く")
        print("2. TaxDocumentRenamer_v3.0_Complete.exe をダブルクリック")
        print("3. v3.0完全版の高機能リネーマーが起動します")
        print("4. 全ての修正点が実装済みです！")
    else:
        print("\nビルドに失敗しました")
    
    input("\n何かキーを押してください...")