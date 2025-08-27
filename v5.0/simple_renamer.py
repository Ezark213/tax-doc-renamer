#!/usr/bin/env python3
"""
簡易版税務書類リネームシステム (OCR不要)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
from pathlib import Path
import re

class SimpleDocumentRenamer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("簡易版税務書類リネームシステム")
        self.root.geometry("800x600")
        
        self.files = []
        self.setup_gui()
        
    def setup_gui(self):
        """GUI設定"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="簡易版税務書類リネームシステム", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # ファイル選択セクション
        file_frame = ttk.LabelFrame(main_frame, text="ファイル選択", padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        # ボタン
        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="PDFファイルを選択", 
                  command=self.select_files).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="フォルダを選択", 
                  command=self.select_folder).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="クリア", 
                  command=self.clear_files).grid(row=0, column=2)
        
        # ファイル数表示
        self.file_count_label = ttk.Label(button_frame, text="選択ファイル: 0件")
        self.file_count_label.grid(row=0, column=3, padx=(20, 0))
        
        # ファイルリスト
        list_frame = ttk.Frame(file_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        list_frame.columnconfigure(0, weight=1)
        
        self.file_listbox = tk.Listbox(list_frame, height=8)
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 処理ボタン
        process_frame = ttk.Frame(main_frame)
        process_frame.grid(row=2, column=0, pady=20)
        
        ttk.Button(process_frame, text="ファイル名から自動判定・リネーム", 
                  command=self.process_files, 
                  style='Accent.TButton').grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(process_frame, text="ヘルプ", 
                  command=self.show_help).grid(row=0, column=1)
        
        # 結果表示
        result_frame = ttk.LabelFrame(main_frame, text="処理結果", padding="10")
        result_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        self.result_text = tk.Text(result_frame, height=8, wrap=tk.WORD)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.configure(yscrollcommand=scrollbar.set)
    
    def select_files(self):
        """ファイル選択"""
        filetypes = [("PDF files", "*.pdf"), ("All files", "*.*")]
        filenames = filedialog.askopenfilenames(title="PDFファイルを選択", filetypes=filetypes)
        
        for filename in filenames:
            if filename not in self.files:
                self.files.append(filename)
                self.file_listbox.insert(tk.END, os.path.basename(filename))
        
        self.update_file_count()
    
    def select_folder(self):
        """フォルダ選択"""
        folder_path = filedialog.askdirectory(title="PDFファイルが含まれるフォルダを選択")
        if folder_path:
            pdf_files = list(Path(folder_path).glob("*.pdf"))
            for pdf_file in pdf_files:
                if str(pdf_file) not in self.files:
                    self.files.append(str(pdf_file))
                    self.file_listbox.insert(tk.END, pdf_file.name)
            self.update_file_count()
    
    def clear_files(self):
        """ファイルリストクリア"""
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.update_file_count()
    
    def update_file_count(self):
        """ファイル数表示更新"""
        count = len(self.files)
        self.file_count_label.config(text=f"選択ファイル: {count}件")
    
    def detect_document_type(self, filename):
        """ファイル名から書類種別を推定"""
        filename_lower = filename.lower()
        
        # 法人税関連
        if any(keyword in filename_lower for keyword in ['法人税', 'houjinzei']):
            return '0001_法人税申告書'
        
        # 消費税関連  
        if any(keyword in filename_lower for keyword in ['消費税', 'shouhizei']):
            return '3001_消費税申告書'
            
        # 地方税関連
        if any(keyword in filename_lower for keyword in ['都道府県民税', 'todofukenminzei', '事業税', 'jigyouzei']):
            return '1001_都道府県申告'
            
        if any(keyword in filename_lower for keyword in ['市町村民税', 'shichosominzei', '市民税', 'shiminzei']):
            return '2001_市町村申告'
        
        # 会計書類
        if any(keyword in filename_lower for keyword in ['決算', 'kessan']):
            return '5001_決算書'
            
        if any(keyword in filename_lower for keyword in ['元帳', 'motochou']):
            return '5002_総勘定元帳'
        
        # その他
        if any(keyword in filename_lower for keyword in ['納付', 'noufu']):
            return '0000_納付税額一覧表'
            
        if any(keyword in filename_lower for keyword in ['受信', 'jushin']):
            return '0003_受信通知'
        
        return '9999_その他'
    
    def extract_year_month(self, filename):
        """ファイル名から年月を抽出"""
        # YYMM形式を探す
        match = re.search(r'[^\d](\d{4})[^\d]', filename)
        if match:
            yymm = match.group(1)
            if len(yymm) == 4:
                return yymm
        
        # 20YYMM形式を探す
        match = re.search(r'(20\d{2})(\d{2})', filename)
        if match:
            year = int(match.group(1)) % 100
            month = match.group(2)
            return f"{year:02d}{month}"
        
        return "YYMM"
    
    def process_files(self):
        """ファイル処理"""
        if not self.files:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        # 出力フォルダを選択
        output_dir = filedialog.askdirectory(title="リネームしたファイルの保存先を選択")
        if not output_dir:
            return
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"処理開始: {len(self.files)}件のファイルを処理します\n")
        self.result_text.insert(tk.END, f"出力先: {output_dir}\n\n")
        
        success_count = 0
        for i, file_path in enumerate(self.files):
            try:
                filename = os.path.basename(file_path)
                
                # 書類種別判定
                doc_type = self.detect_document_type(filename)
                
                # 年月抽出
                year_month = self.extract_year_month(filename)
                
                # 新しいファイル名生成
                if doc_type.startswith('9999_'):
                    new_filename = f"{doc_type.replace('9999_', '')}{year_month}_{filename}"
                else:
                    new_filename = f"{doc_type}_{year_month}.pdf"
                
                # ファイルコピー
                new_path = os.path.join(output_dir, new_filename)
                
                # 重複ファイル名の処理
                counter = 1
                base_path = new_path
                while os.path.exists(new_path):
                    name, ext = os.path.splitext(base_path)
                    new_path = f"{name}_{counter:02d}{ext}"
                    counter += 1
                
                shutil.copy2(file_path, new_path)
                success_count += 1
                
                result_msg = f"[{i+1}] {filename} → {os.path.basename(new_path)}\n"
                self.result_text.insert(tk.END, result_msg)
                self.result_text.see(tk.END)
                self.root.update()
                
            except Exception as e:
                error_msg = f"[{i+1}] エラー: {filename} - {str(e)}\n"
                self.result_text.insert(tk.END, error_msg)
        
        self.result_text.insert(tk.END, f"\n処理完了: {success_count}件のファイルをリネームしました\n")
        messagebox.showinfo("完了", f"{success_count}件のファイルをリネームしました")
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
簡易版税務書類リネームシステム

【機能】
・ファイル名から書類種別を自動判定
・年月情報を自動抽出
・標準的な命名規則でリネーム

【対応書類】
・法人税申告書 → 0001_法人税申告書_YYMM.pdf
・消費税申告書 → 3001_消費税申告書_YYMM.pdf  
・都道府県民税・事業税 → 1001_都道府県申告_YYMM.pdf
・市町村民税 → 2001_市町村申告_YYMM.pdf
・決算書 → 5001_決算書_YYMM.pdf
・総勘定元帳 → 5002_総勘定元帳_YYMM.pdf

【使用方法】
1. PDFファイルまたはフォルダを選択
2. 「ファイル名から自動判定・リネーム」をクリック
3. 出力先フォルダを選択
4. 処理完了を確認

注意: この簡易版はOCR機能がないため、ファイル名からの判定のみ行います。
        """
        messagebox.showinfo("ヘルプ", help_text)
    
    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

if __name__ == "__main__":
    app = SimpleDocumentRenamer()
    app.run()