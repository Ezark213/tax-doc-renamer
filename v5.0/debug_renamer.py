#!/usr/bin/env python3
"""
デバッグ版税務書類リネームシステム
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path

class DebugRenamer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("デバッグ版リネームシステム")
        self.root.geometry("700x500")
        
        self.files = []
        self.setup_gui()
        
    def setup_gui(self):
        """GUI設定"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        ttk.Label(main_frame, text="デバッグ版リネームシステム", 
                 font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # 現在のディレクトリ表示
        ttk.Label(main_frame, text=f"現在のディレクトリ: {os.getcwd()}", 
                 wraplength=600).pack(pady=(0, 5))
        
        # Pythonバージョン表示
        ttk.Label(main_frame, text=f"Python: {sys.version}").pack(pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="個別ファイル選択", 
                  command=self.select_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="フォルダ選択", 
                  command=self.select_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="テストフォルダを開く", 
                  command=self.test_folder_access).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="クリア", 
                  command=self.clear_files).pack(side=tk.LEFT)
        
        # ファイル数表示
        self.file_count_label = ttk.Label(main_frame, text="選択ファイル: 0件")
        self.file_count_label.pack(pady=5)
        
        # ファイルリスト
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.file_listbox = tk.Listbox(list_frame)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        # ログエリア
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 初期ログ
        self.log(f"アプリケーション開始")
        self.log(f"作業ディレクトリ: {os.getcwd()}")
        
    def log(self, message):
        """ログメッセージを追加"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def test_folder_access(self):
        """テストフォルダへのアクセステスト"""
        test_paths = [
            r"C:\Users\pukur\Desktop\iwao",
            r"C:\Users\pukur\Desktop",
            os.path.expanduser("~/Desktop/iwao"),
            os.path.expanduser("~/Desktop")
        ]
        
        self.log("=== フォルダアクセステスト ===")
        for path in test_paths:
            try:
                if os.path.exists(path):
                    files = list(Path(path).glob("*.pdf"))
                    self.log(f"✅ {path} - {len(files)}個のPDFファイル")
                    for f in files[:3]:  # 最初の3つだけ表示
                        self.log(f"   - {f.name}")
                else:
                    self.log(f"❌ {path} - フォルダが存在しません")
            except Exception as e:
                self.log(f"❌ {path} - エラー: {str(e)}")
        self.log("=== テスト完了 ===")
        
    def select_files(self):
        """ファイル選択"""
        try:
            self.log("個別ファイル選択を開始...")
            filetypes = [("PDF files", "*.pdf"), ("All files", "*.*")]
            filenames = filedialog.askopenfilenames(
                title="PDFファイルを選択", 
                filetypes=filetypes,
                initialdir=r"C:\Users\pukur\Desktop"
            )
            
            self.log(f"選択されたファイル数: {len(filenames)}")
            
            for filename in filenames:
                if filename not in self.files:
                    self.files.append(filename)
                    self.file_listbox.insert(tk.END, os.path.basename(filename))
                    self.log(f"追加: {os.path.basename(filename)}")
            
            self.update_file_count()
            
        except Exception as e:
            self.log(f"ファイル選択エラー: {str(e)}")
            messagebox.showerror("エラー", f"ファイル選択エラー: {str(e)}")
    
    def select_folder(self):
        """フォルダ選択"""
        try:
            self.log("フォルダ選択を開始...")
            folder_path = filedialog.askdirectory(
                title="PDFファイルが含まれるフォルダを選択",
                initialdir=r"C:\Users\pukur\Desktop"
            )
            
            if folder_path:
                self.log(f"選択されたフォルダ: {folder_path}")
                pdf_files = list(Path(folder_path).glob("*.pdf"))
                self.log(f"フォルダ内のPDFファイル数: {len(pdf_files)}")
                
                added_count = 0
                for pdf_file in pdf_files:
                    if str(pdf_file) not in self.files:
                        self.files.append(str(pdf_file))
                        self.file_listbox.insert(tk.END, pdf_file.name)
                        self.log(f"追加: {pdf_file.name}")
                        added_count += 1
                
                self.log(f"合計 {added_count} 個のファイルを追加しました")
                self.update_file_count()
            else:
                self.log("フォルダ選択がキャンセルされました")
                
        except Exception as e:
            self.log(f"フォルダ選択エラー: {str(e)}")
            messagebox.showerror("エラー", f"フォルダ選択エラー: {str(e)}")
    
    def clear_files(self):
        """ファイルリストクリア"""
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.update_file_count()
        self.log("ファイルリストをクリアしました")
    
    def update_file_count(self):
        """ファイル数表示更新"""
        count = len(self.files)
        self.file_count_label.config(text=f"選択ファイル: {count}件")
    
    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

if __name__ == "__main__":
    app = DebugRenamer()
    app.run()