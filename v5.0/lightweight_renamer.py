#!/usr/bin/env python3
"""
軽量版税務書類リネームシステム - 最小限の機能で高速動作
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import re
from pathlib import Path

class LightweightRenamer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("軽量版税務書類リネーム")
        self.root.geometry("600x400")
        
        self.files = []
        self.setup_gui()
        
    def setup_gui(self):
        """GUI設定"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="軽量版税務書類リネーム", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # ボタンフレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="PDFファイル選択", 
                  command=self.select_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="処理実行", 
                  command=self.process_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="クリア", 
                  command=self.clear_files).pack(side=tk.LEFT)
        
        # ファイル数表示
        self.count_label = ttk.Label(main_frame, text="選択: 0件")
        self.count_label.pack(pady=5)
        
        # ファイルリスト
        self.listbox = tk.Listbox(main_frame, height=12)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 処理結果表示
        self.result_label = ttk.Label(main_frame, text="", foreground="blue")
        self.result_label.pack(pady=5)
        
    def select_files(self):
        """ファイル選択"""
        try:
            files = filedialog.askopenfilenames(
                title="PDFファイルを選択",
                filetypes=[("PDF files", "*.pdf")],
                initialdir=r"C:\Users\pukur\Desktop\iwao"
            )
            
            for file in files:
                if file not in self.files:
                    self.files.append(file)
                    self.listbox.insert(tk.END, os.path.basename(file))
            
            self.count_label.config(text=f"選択: {len(self.files)}件")
            
        except Exception as e:
            messagebox.showerror("エラー", f"ファイル選択エラー: {e}")
    
    def clear_files(self):
        """クリア"""
        self.files.clear()
        self.listbox.delete(0, tk.END)
        self.count_label.config(text="選択: 0件")
        self.result_label.config(text="")
    
    def detect_type(self, filename):
        """ファイル名から書類種別を判定（簡易版）"""
        name = filename.lower()
        
        if "法人税" in filename or "houjinzei" in name:
            return "0001_法人税申告書"
        elif "消費税" in filename or "shouhizei" in name:
            return "3001_消費税申告書"
        elif "都道府県" in filename or "事業税" in filename:
            return "1001_都道府県申告"
        elif "市町村" in filename or "市民税" in filename:
            return "2001_市町村申告"
        elif "決算" in filename:
            return "5001_決算書"
        elif "納付" in filename:
            return "0000_納付情報"
        else:
            return "9999_その他"
    
    def extract_date(self, filename):
        """ファイル名から日付を抽出"""
        # 20250731 形式
        match = re.search(r'(20\d{6})', filename)
        if match:
            date_str = match.group(1)
            return date_str[2:4] + date_str[4:6]  # YYMM形式
        
        # その他の形式も簡単に対応
        match = re.search(r'(\d{4})', filename)
        if match:
            return match.group(1)
        
        return "YYMM"
    
    def process_files(self):
        """処理実行"""
        if not self.files:
            messagebox.showwarning("警告", "ファイルを選択してください")
            return
        
        # 出力先選択
        output_dir = filedialog.askdirectory(
            title="出力先フォルダを選択",
            initialdir=r"C:\Users\pukur\Desktop"
        )
        
        if not output_dir:
            return
        
        try:
            success_count = 0
            
            for file_path in self.files:
                filename = os.path.basename(file_path)
                
                # 書類種別判定
                doc_type = self.detect_type(filename)
                
                # 日付抽出
                date_part = self.extract_date(filename)
                
                # 新しいファイル名作成
                if doc_type.startswith("9999"):
                    new_name = f"その他_{date_part}_{filename}"
                else:
                    new_name = f"{doc_type}_{date_part}.pdf"
                
                # ファイルコピー
                new_path = os.path.join(output_dir, new_name)
                
                # 重複回避
                counter = 1
                original_path = new_path
                while os.path.exists(new_path):
                    name, ext = os.path.splitext(original_path)
                    new_path = f"{name}_{counter:02d}{ext}"
                    counter += 1
                
                shutil.copy2(file_path, new_path)
                success_count += 1
            
            self.result_label.config(
                text=f"✅ {success_count}件のファイルをリネームしました",
                foreground="green"
            )
            
            messagebox.showinfo("完了", 
                              f"{success_count}件のファイルを正常にリネームしました\n"
                              f"出力先: {output_dir}")
            
        except Exception as e:
            self.result_label.config(
                text=f"❌ エラーが発生しました: {str(e)}", 
                foreground="red"
            )
            messagebox.showerror("エラー", f"処理エラー: {e}")
    
    def run(self):
        """実行"""
        self.root.mainloop()

if __name__ == "__main__":
    app = LightweightRenamer()
    app.run()