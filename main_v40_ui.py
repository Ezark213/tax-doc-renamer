#!/usr/bin/env python3
"""
税務書類リネームシステム v4.0 - Exact UI Implementation
正確な3タブレイアウト実装
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path

class TaxDocumentRenamerV40:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v4.0")
        self.root.geometry("800x600")
        self.root.configure(bg='white')
        
        # Variables
        self.year_month_var = tk.StringVar(value="2508")
        self.pdf_auto_split = tk.BooleanVar(value=True)
        self.ocr_enhanced = tk.BooleanVar(value=True)
        
        # Municipality settings
        self.municipality_vars = {}
        municipalities = [
            ("セット1:", "東京都", ""),
            ("セット2:", "愛知県", "蒲郡市"),
            ("セット3:", "福岡県", "福岡市"),
            ("セット4:", "", ""),
            ("セット5:", "", "")
        ]
        
        for i, (label, pref, city) in enumerate(municipalities, 1):
            self.municipality_vars[f"pref_{i}"] = tk.StringVar(value=pref)
            self.municipality_vars[f"city_{i}"] = tk.StringVar(value=city)
        
        # File management
        self.files_list = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg='white', height=60)
        header_frame.pack(fill=tk.X, padx=10, pady=(10,0))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(header_frame, 
                              text="税務書類リネームシステム v4.0",
                              font=("Arial", 20, "bold"),
                              bg='white')
        title_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Menu bar simulation
        menu_frame = tk.Frame(self.root, bg='#f0f0f0', height=30)
        menu_frame.pack(fill=tk.X, padx=10)
        menu_frame.pack_propagate(False)
        
        menu_items = ["ファイル選択・設定", "設定管理", "ログ・デバッグ"]
        for item in menu_items:
            menu_label = tk.Label(menu_frame, text=item, bg='#f0f0f0', 
                                 padx=10, pady=5, font=("Arial", 9))
            menu_label.pack(side=tk.LEFT)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        
        # Tab 1: File Selection
        file_tab = tk.Frame(notebook, bg='white')
        notebook.add(file_tab, text="ファイル選択")
        
        # Tab 2: Settings  
        settings_tab = tk.Frame(notebook, bg='white')
        notebook.add(settings_tab, text="設定")
        
        # Tab 3: Results/Log
        results_tab = tk.Frame(notebook, bg='white')
        notebook.add(results_tab, text="処理結果")
        
        self.create_file_selection_tab(file_tab)
        self.create_settings_tab(settings_tab)
        self.create_results_tab(results_tab)
        
    def create_file_selection_tab(self, parent):
        # Main container
        main_container = tk.Frame(parent, bg='white')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left side - File operations
        left_frame = tk.Frame(main_container, bg='white')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,20))
        
        # File selection section
        file_section = tk.LabelFrame(left_frame, text="ファイル選択", 
                                   font=("Arial", 12, "bold"), bg='white')
        file_section.pack(fill=tk.X, pady=(0,20))
        
        # Drag & Drop area
        self.drop_area = tk.Frame(file_section, 
                                 bg='#e8f4f8', 
                                 height=120,
                                 relief=tk.RAISED,
                                 bd=2)
        self.drop_area.pack(fill=tk.X, padx=20, pady=20)
        self.drop_area.pack_propagate(False)
        
        drop_icon = tk.Label(self.drop_area, text="📁", 
                            bg='#e8f4f8', font=("Arial", 24))
        drop_icon.place(relx=0.5, rely=0.3, anchor=tk.CENTER)
        
        drop_text1 = tk.Label(self.drop_area, 
                             text="ファイルをここにドラッグ&ドロップ",
                             bg='#e8f4f8', font=("Arial", 12, "bold"))
        drop_text1.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        drop_text2 = tk.Label(self.drop_area,
                             text="対応形式: PDF, CSV",
                             bg='#e8f4f8', font=("Arial", 10), fg='gray')
        drop_text2.place(relx=0.5, rely=0.7, anchor=tk.CENTER)
        
        # Click to select text
        click_text = tk.Label(file_section,
                             text="クリックでファイル選択",
                             bg='white', font=("Arial", 10),
                             cursor="hand2", fg='blue')
        click_text.pack(pady=(0,20))
        click_text.bind("<Button-1>", lambda e: self.select_files())
        
        # File list section
        list_section = tk.LabelFrame(left_frame, text="選択されたファイル",
                                   font=("Arial", 10), bg='white')
        list_section.pack(fill=tk.BOTH, expand=True)
        
        # File list with buttons
        list_button_frame = tk.Frame(list_section, bg='white')
        list_button_frame.pack(fill=tk.X, padx=10, pady=(10,5))
        
        tk.Button(list_button_frame, text="ファイル選択", 
                 command=self.select_files, bg='lightgray').pack(side=tk.LEFT, padx=(0,5))
        tk.Button(list_button_frame, text="ファイル削除", 
                 command=self.remove_files, bg='lightgray').pack(side=tk.LEFT, padx=5)
        tk.Button(list_button_frame, text="クリア", 
                 command=self.clear_files, bg='lightgray').pack(side=tk.LEFT, padx=5)
        
        # File listbox
        list_container = tk.Frame(list_section, bg='white')
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        
        self.file_listbox = tk.Listbox(list_container, 
                                      selectmode=tk.EXTENDED,
                                      font=("Courier", 8),
                                      bg='white')
        scrollbar_files = tk.Scrollbar(list_container, orient=tk.VERTICAL)
        
        self.file_listbox.configure(yscrollcommand=scrollbar_files.set)
        scrollbar_files.configure(command=self.file_listbox.yview)
        
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_files.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right side - Settings panel
        right_frame = tk.Frame(main_container, bg='white', width=250)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        # Settings title
        settings_title = tk.Label(right_frame, text="設定", 
                                 font=("Arial", 14, "bold"), bg='white')
        settings_title.pack(anchor=tk.W, pady=(0,20))
        
        # Year/Month settings
        yymm_frame = tk.LabelFrame(right_frame, text="年月設定",
                                 font=("Arial", 10), bg='white')
        yymm_frame.pack(fill=tk.X, pady=(0,20))
        
        tk.Label(yymm_frame, text="手動入力年月 (YYMM):", 
                bg='white', font=("Arial", 9)).pack(anchor=tk.W, padx=10, pady=(10,5))
        
        yymm_entry = tk.Entry(yymm_frame, textvariable=self.year_month_var, 
                             font=("Arial", 10), width=10)
        yymm_entry.pack(anchor=tk.W, padx=10, pady=(0,10))
        
        # Municipality settings
        muni_frame = tk.LabelFrame(right_frame, text="自治体設定",
                                 font=("Arial", 10), bg='white')
        muni_frame.pack(fill=tk.X, pady=(0,20))
        
        municipalities = [
            ("セット1:", "東京都", ""),
            ("セット2:", "愛知県", "蒲郡市"), 
            ("セット3:", "福岡県", "福岡市"),
            ("セット4:", "", ""),
            ("セット5:", "", "")
        ]
        
        for i, (label, default_pref, default_city) in enumerate(municipalities, 1):
            set_container = tk.Frame(muni_frame, bg='white')
            set_container.pack(fill=tk.X, padx=10, pady=2)
            
            tk.Label(set_container, text=label, width=6, anchor=tk.W,
                    bg='white', font=("Arial", 9)).pack(side=tk.LEFT)
            
            pref_entry = tk.Entry(set_container, 
                                textvariable=self.municipality_vars[f"pref_{i}"], 
                                width=8, font=("Arial", 8))
            pref_entry.pack(side=tk.LEFT, padx=(0,2))
            
            city_entry = tk.Entry(set_container,
                                textvariable=self.municipality_vars[f"city_{i}"], 
                                width=8, font=("Arial", 8))
            city_entry.pack(side=tk.LEFT)
        
        # Processing options
        options_frame = tk.LabelFrame(right_frame, text="処理オプション",
                                    font=("Arial", 10), bg='white')
        options_frame.pack(fill=tk.X, pady=(0,20))
        
        tk.Checkbutton(options_frame, text="PDF自動分割",
                      variable=self.pdf_auto_split, bg='white',
                      font=("Arial", 9)).pack(anchor=tk.W, padx=10, pady=5)
        
        tk.Checkbutton(options_frame, text="OCR強化モード", 
                      variable=self.ocr_enhanced, bg='white',
                      font=("Arial", 9)).pack(anchor=tk.W, padx=10, pady=(0,10))
        
        # Process buttons
        button_container = tk.Frame(right_frame, bg='white')
        button_container.pack(fill=tk.X, pady=(0,10))
        
        tk.Button(button_container, text="分割実行", 
                 bg='lightblue', font=("Arial", 10),
                 command=self.split_execute).pack(fill=tk.X, pady=(0,5))
        
        tk.Button(button_container, text="リネーム実行", 
                 bg='lightgreen', font=("Arial", 10, "bold"),
                 command=self.rename_execute).pack(fill=tk.X)
        
        # Status
        self.status_label = tk.Label(button_container,
                                   text="リネーム完了: 20件完了",
                                   bg='white', fg='green', font=("Arial", 9))
        self.status_label.pack(pady=(10,0))
        
    def create_settings_tab(self, parent):
        settings_container = tk.Frame(parent, bg='white')
        settings_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(settings_container, text="詳細設定", 
                font=("Arial", 16, "bold"), bg='white').pack(pady=(0,20))
        
        # Additional settings would go here
        tk.Label(settings_container, 
                text="高度な設定オプションがここに表示されます。",
                bg='white', font=("Arial", 12)).pack()
        
    def create_results_tab(self, parent):
        results_container = tk.Frame(parent, bg='white')
        results_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(results_container, text="処理結果・ログ", 
                font=("Arial", 16, "bold"), bg='white').pack(pady=(0,20))
        
        # Results log area
        log_frame = tk.Frame(results_container, bg='white')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, font=("Courier", 9), bg='white')
        log_scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL)
        
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.configure(command=self.log_text.yview)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add some sample log entries
        sample_logs = [
            "賞与明細_20250818_1017.pdf のコピー.pdf",
            "納税一覧.pdf のコピー.pdf", 
            "法人県民税_20250818_1012.pdf のコピー.pdf",
            "消費税集計表_20250818_1020.pdf のコピー.pdf",
            "固定資産.pdf のコピー.pdf",
            "預り金_20250818_1018.pdf のコピー.pdf",
            "固定資産償却調書.pdf のコピー.pdf",
            "住民票_20250818_1012.pdf のコピー.pdf",
            "所得控除別内訳・住民税集計表_20250818_1020 .pdf のコピー.pdf",
            "一般償却資産明細.pdf のコピー.pdf"
        ]
        
        for log_entry in sample_logs:
            self.log_text.insert(tk.END, log_entry + "\n")
        
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="PDFまたはCSVファイルを選択",
            filetypes=[
                ("対応ファイル", "*.pdf *.csv"),
                ("PDFファイル", "*.pdf"),
                ("CSVファイル", "*.csv"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        for file in files:
            if file not in self.files_list:
                self.files_list.append(file)
                self.file_listbox.insert(tk.END, os.path.basename(file))
                
    def remove_files(self):
        selected_indices = self.file_listbox.curselection()
        for index in reversed(selected_indices):
            del self.files_list[index]
            self.file_listbox.delete(index)
        
    def clear_files(self):
        self.files_list.clear()
        self.file_listbox.delete(0, tk.END)
        
    def split_execute(self):
        if not self.files_list:
            messagebox.showwarning("ファイルなし", "処理するファイルを選択してください")
            return
        messagebox.showinfo("分割実行", "PDF分割処理を実行しました")
        
    def rename_execute(self):
        if not self.files_list:
            messagebox.showwarning("ファイルなし", "処理するファイルを選択してください")
            return
        
        processed = len(self.files_list)
        self.status_label.config(text=f"リネーム完了: {processed}件完了")
        messagebox.showinfo("リネーム完了", f"{processed}件のファイルを処理しました")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV40()
    app.run()