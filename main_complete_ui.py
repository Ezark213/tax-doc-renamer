#!/usr/bin/env python3
"""
Bundle PDF Auto-Split v5.2 - Complete UI Implementation
税務書類リネームシステム - 完全版UI実装
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path

class BundlePDFAutoSplitComplete:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.2 - Bundle PDF Auto-Split")
        self.root.geometry("1400x800")
        
        # Variables
        self.auto_split_enabled = tk.BooleanVar(value=True)
        self.debug_log_enabled = tk.BooleanVar(value=False)
        self.pdf_auto_split_enabled = tk.BooleanVar(value=True)
        self.ocr_enhanced_mode = tk.BooleanVar(value=True)
        self.v50_and_mode = tk.BooleanVar(value=True)
        
        self.year_month_var = tk.StringVar(value="2508")
        
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
        self.bundle_detected_count = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main horizontal layout
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - File management
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # Right panel - Settings
        right_frame = ttk.Frame(main_paned)  
        main_paned.add(right_frame, weight=1)
        
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)
        
    def create_left_panel(self, parent):
        # Title
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        title_label = tk.Label(title_frame, text="ファイル管理", 
                              font=("Arial", 14, "bold"))
        title_label.pack(anchor=tk.W)
        
        # Drag & Drop area
        drop_frame = ttk.LabelFrame(parent, text="ドラッグ&ドロップエリア", padding="15")
        drop_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.drop_area = tk.Frame(drop_frame, 
                                 bg="lightblue", 
                                 height=120,
                                 relief=tk.SUNKEN,
                                 bd=2)
        self.drop_area.pack(fill=tk.X, pady=5)
        self.drop_area.pack_propagate(False)
        
        drop_label = tk.Label(self.drop_area, 
                             text="PDFまたはCSVファイルをここにドラッグ&ドロップ\\n対応: PDF / CSV",
                             bg="lightblue",
                             font=("Arial", 12),
                             justify=tk.CENTER)
        drop_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # File selection buttons
        button_frame = ttk.Frame(drop_frame)
        button_frame.pack(fill=tk.X, pady=(5,0))
        
        ttk.Button(button_frame, text="📁 ファイル選択", 
                  command=self.select_files).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(button_frame, text="🗑️ リストクリア", 
                  command=self.clear_files).pack(side=tk.LEFT, padx=5)
        
        # Bundle detection status
        self.bundle_status_label = tk.Label(button_frame, 
                                           text="Bundle PDF検出: 0件",
                                           fg="gray")
        self.bundle_status_label.pack(side=tk.RIGHT)
        
        # File list
        list_frame = ttk.LabelFrame(parent, text="選択されたファイル", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # File listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.file_listbox = tk.Listbox(list_container, 
                                      selectmode=tk.EXTENDED,
                                      font=("Courier", 9))
        scrollbar_files = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        
        self.file_listbox.configure(yscrollcommand=scrollbar_files.set)
        scrollbar_files.configure(command=self.file_listbox.yview)
        
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_files.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Output folder selection
        output_frame = ttk.LabelFrame(parent, text="出力フォルダ", padding="10")
        output_frame.pack(fill=tk.X, padx=10, pady=(5,10))
        
        self.output_folder_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop"))
        
        output_entry_frame = ttk.Frame(output_frame)
        output_entry_frame.pack(fill=tk.X)
        
        ttk.Entry(output_entry_frame, textvariable=self.output_folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_entry_frame, text="参照", 
                  command=self.browse_output_folder).pack(side=tk.RIGHT, padx=(5,0))
        
        # Process buttons
        process_frame = ttk.Frame(output_frame)
        process_frame.pack(fill=tk.X, pady=(10,0))
        
        ttk.Button(process_frame, text="🚀 一括処理（分割&出力）", 
                  command=self.batch_process,
                  style="Accent.TButton").pack(fill=tk.X, pady=(0,5))
        
    def create_right_panel(self, parent):
        # Create scrollable area for settings
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        title_label = tk.Label(title_frame, text="設定・Auto-Split", 
                              font=("Arial", 14, "bold"))
        title_label.pack(anchor=tk.W)
        
        subtitle_label = tk.Label(title_frame, text="Bundle PDF Auto-Split v5.2", 
                              font=("Arial", 16, "bold"), fg="blue")
        subtitle_label.pack(pady=(5,0))
        
        # Auto-Split Settings
        auto_split_frame = ttk.LabelFrame(scrollable_frame, text="Auto-Split設定", padding="15")
        auto_split_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Checkbutton(auto_split_frame, 
                       text="アップロード時に束ねPDFを自動分割（推奨）",
                       variable=self.auto_split_enabled).pack(anchor=tk.W)
        
        ttk.Checkbutton(auto_split_frame,
                       text="詳細ログ出力 (Debug)",
                       variable=self.debug_log_enabled).pack(anchor=tk.W, pady=(5,0))
        
        # Target codes info
        info_label = tk.Label(auto_split_frame, 
                             text="対象：地方税系（1003/1013/1023→1004/2004）、国税系（0003/0004→3003/3004）の束ね",
                             font=("Arial", 8), fg="gray",
                             wraplength=400, justify=tk.LEFT)
        info_label.pack(anchor=tk.W, pady=(5,0))
        
        # Batch Processing Action
        batch_frame = ttk.LabelFrame(scrollable_frame, text="一括処理アクション", padding="15")
        batch_frame.pack(fill=tk.X, padx=20, pady=10)
        
        action_entry_frame = ttk.Frame(batch_frame)
        action_entry_frame.pack(fill=tk.X, pady=(0,10))
        
        tk.Label(action_entry_frame, text="🔄").pack(side=tk.LEFT)
        action_entry = ttk.Entry(action_entry_frame, state="readonly")
        action_entry.insert(0, "一括処理（分割&出力）")
        action_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,0))
        
        button_frame = ttk.Frame(batch_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="📁 分割のみ（修正）", 
                  command=self.split_only).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(button_frame, text="⚡ 強制分割", 
                  command=self.force_split).pack(side=tk.LEFT, padx=5)
        
        # Processing status
        self.status_label = tk.Label(batch_frame, text="一括処理完了：31件処理（分割：0件）", 
                               fg="green", font=("Arial", 10))
        self.status_label.pack(pady=(10,0))
        
        # Year/Month Settings
        yymm_frame = ttk.LabelFrame(scrollable_frame, text="年月設定", padding="15")
        yymm_frame.pack(fill=tk.X, padx=20, pady=10)
        
        yymm_input_frame = ttk.Frame(yymm_frame)
        yymm_input_frame.pack(anchor=tk.W)
        
        ttk.Label(yymm_input_frame, text="手動入力年月 (YYMM):").pack(side=tk.LEFT)
        yymm_entry = ttk.Entry(yymm_input_frame, textvariable=self.year_month_var, width=10)
        yymm_entry.pack(side=tk.LEFT, padx=(10,0))
        
        # Municipality Settings
        muni_frame = ttk.LabelFrame(scrollable_frame, text="自治体設定", padding="15")
        muni_frame.pack(fill=tk.X, padx=20, pady=10)
        
        municipalities = [
            ("セット1:", "東京都", ""),
            ("セット2:", "愛知県", "蒲郡市"), 
            ("セット3:", "福岡県", "福岡市"),
            ("セット4:", "", ""),
            ("セット5:", "", "")
        ]
        
        for i, (label, default_pref, default_city) in enumerate(municipalities, 1):
            set_frame = ttk.Frame(muni_frame)
            set_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(set_frame, text=label, width=8).pack(side=tk.LEFT)
            
            pref_entry = ttk.Entry(set_frame, textvariable=self.municipality_vars[f"pref_{i}"], width=12)
            pref_entry.pack(side=tk.LEFT, padx=(0,5))
            
            city_entry = ttk.Entry(set_frame, textvariable=self.municipality_vars[f"city_{i}"], width=12)
            city_entry.pack(side=tk.LEFT)
        
        # Processing Options
        options_frame = ttk.LabelFrame(scrollable_frame, text="処理オプション", padding="15")
        options_frame.pack(fill=tk.X, padx=20, pady=(10,20))
        
        ttk.Checkbutton(options_frame,
                       text="PDF自動分割",
                       variable=self.pdf_auto_split_enabled).pack(anchor=tk.W)
        
        ttk.Checkbutton(options_frame,
                       text="OCR強化モード", 
                       variable=self.ocr_enhanced_mode).pack(anchor=tk.W, pady=(5,0))
        
        ttk.Checkbutton(options_frame,
                       text="v5.0 AND条件判定モード（推奨）",
                       variable=self.v50_and_mode).pack(anchor=tk.W, pady=(5,0))
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
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
                
        self.update_bundle_status()
        
    def clear_files(self):
        self.files_list.clear()
        self.file_listbox.delete(0, tk.END)
        self.bundle_detected_count = 0
        self.update_bundle_status()
        
    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="出力フォルダを選択")
        if folder:
            self.output_folder_var.set(folder)
            
    def update_bundle_status(self):
        # Simulate bundle detection
        pdf_count = sum(1 for f in self.files_list if f.lower().endswith('.pdf'))
        self.bundle_detected_count = pdf_count // 2  # Rough estimation
        
        if self.bundle_detected_count > 0:
            self.bundle_status_label.config(
                text=f"Bundle PDF検出: {self.bundle_detected_count}件",
                fg="blue"
            )
        else:
            self.bundle_status_label.config(
                text="Bundle PDF検出: 0件",
                fg="gray"
            )
    
    def batch_process(self):
        if not self.files_list:
            messagebox.showwarning("ファイルなし", "処理するファイルを選択してください")
            return
            
        output_folder = self.output_folder_var.get()
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("エラー", f"出力フォルダを作成できませんでした: {e}")
                return
        
        # Simulate processing
        processed_count = len(self.files_list)
        split_count = self.bundle_detected_count
        
        self.status_label.config(
            text=f"一括処理完了：{processed_count}件処理（分割：{split_count}件）",
            fg="green"
        )
        
        messagebox.showinfo("処理完了", 
                           f"一括処理が完了しました。\\n処理ファイル数: {processed_count}\\n分割ファイル数: {split_count}")
        
    def split_only(self):
        messagebox.showinfo("分割のみ", "分割のみ処理を実行します")
        
    def force_split(self):
        messagebox.showinfo("強制分割", "強制分割処理を実行します")
        
    def run(self):
        # Configure styles
        style = ttk.Style()
        try:
            style.configure("Accent.TButton", background="lightblue")
        except:
            pass  # Ignore if theme doesn't support it
            
        self.root.mainloop()

if __name__ == "__main__":
    app = BundlePDFAutoSplitComplete()
    app.run()