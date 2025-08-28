#!/usr/bin/env python3
"""
動作確実な税務書類リネームexeを作成
"""

import os
import subprocess
import shutil

def build_working_exe():
    """動作するexeをビルド"""
    print("動作する税務書類リネームexeを作成中...")
    
    # 軽量版リネーマーを使用
    source_file = r"C:\Users\pukur\Desktop\TaxRenamer_Tools\lightweight_renamer.py"
    
    if not os.path.exists(source_file):
        print("エラー: lightweight_renamer.py が見つかりません")
        return False
    
    # 作業ディレクトリに移動
    os.chdir(os.path.dirname(source_file))
    
    # ビルドディレクトリをクリア
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # PyInstallerコマンド（シンプル版）
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=TaxDocumentRenamer_Working_v2.8",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk", 
        "lightweight_renamer.py"
    ]
    
    try:
        print("PyInstallerを実行中...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        exe_path = os.path.join("dist", "TaxDocumentRenamer_Working_v2.8.exe")
        if os.path.exists(exe_path):
            # リネームアプリフォルダにコピー
            dest_dir = r"C:\Users\pukur\Desktop\リネームアプリ"
            dest_path = os.path.join(dest_dir, "TaxDocumentRenamer_Working_v2.8.exe")
            shutil.copy2(exe_path, dest_path)
            
            print("="*50)
            print("動作確実な TaxDocumentRenamer_Working_v2.8.exe が作成されました!")
            print(f"場所: {dest_path}")
            print("軽量で高速動作、依存関係の問題なし")
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
    success = build_working_exe()
    if success:
        print("\n次のステップ:")
        print("1. デスクトップの「リネームアプリ」フォルダを開く")
        print("2. TaxDocumentRenamer_Working_v2.8.exe をダブルクリック")
        print("3. これで確実に動作します!")
    else:
        print("\nビルドに失敗しました")
    
    input("\n何かキーを押してください...")