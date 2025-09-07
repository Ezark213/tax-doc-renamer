#!/usr/bin/env python3
"""
Bundle PDF Auto-Split v5.2 - Correct UI Version
税務書類リネームシステム - 正しいUI実装
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path

class BundlePDFAutoSplitV52:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.2")
        self.root.geometry("1000x800")
        
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
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Settings/Auto-Split tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="設定・Auto-Split")
        
        self.create_settings_tab(settings_frame)
        
        # Additional tabs can be added here
        
    def create_settings_tab(self, parent):
        # Main container with scrollbar
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
        
        title_label = tk.Label(title_frame, text="Bundle PDF Auto-Split v5.2", 
                              font=("Arial", 16, "bold"), fg="blue")
        title_label.pack()
        
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
                             font=("Arial", 8), fg="gray")
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
        status_label = tk.Label(batch_frame, text="一括処理完了：31件処理（分割：0件）", 
                               fg="green", font=("Arial", 10))
        status_label.pack(pady=(10,0))
        
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
        options_frame.pack(fill=tk.X, padx=20, pady=10)
        
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
        
    def split_only(self):
        messagebox.showinfo("分割のみ", "分割のみ処理を実行します")
        
    def force_split(self):
        messagebox.showinfo("強制分割", "強制分割処理を実行します")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = BundlePDFAutoSplitV52()
    app.run()