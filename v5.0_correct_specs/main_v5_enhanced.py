#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 強化版
出力先選択機能 + 処理結果一覧表示機能付き
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import datetime

class TaxDocumentRenamerV5Enhanced:
    """税務書類リネームシステム v5.0 強化版"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.0 強化版")
        self.root.geometry("1300x850")
        
        # システム変数
        self.files_list = []
        self.processing = False
        self.processing_results = []
        self.output_directory = ""
        
        # 47都道府県リスト
        self.prefectures = [
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        # 自治体セット設定（最大5セット）
        self.municipality_sets = {}
        for i in range(1, 6):
            self.municipality_sets[i] = {
                "prefecture": "", 
                "municipality": "", 
                "pref_code": None, 
                "muni_code": None
            }
        
        # UI構築
        self._create_ui()
        self._log("税務書類リネームシステム v5.0 強化版を起動しました")

    def _create_ui(self):
        """メインUI作成"""
        # メインコンテナ
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="税務書類リネームシステム v5.0 強化版",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="出力先選択機能 + 処理結果一覧表示機能付き",
            font=('Arial', 10),
            foreground='green'
        )
        subtitle_label.pack(pady=(0, 15))
        
        # ノートブック（タブ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # タブ作成
        self._create_main_tab()
        self._create_results_tab()
        self._create_log_tab()

    def _create_main_tab(self):
        """メインタブ作成"""
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="📁 メイン処理")
        
        # 3分割レイアウト（左：ファイル、中央：設定、右：出力設定）
        left_frame = ttk.LabelFrame(self.main_frame, text="ファイル選択")
        left_frame.pack(side='left', fill='both', expand=True, padx=(5, 2), pady=5)
        
        center_frame = ttk.LabelFrame(self.main_frame, text="処理設定")
        center_frame.pack(side='left', fill='y', padx=2, pady=5, ipadx=10)
        
        right_frame = ttk.LabelFrame(self.main_frame, text="出力設定")
        right_frame.pack(side='right', fill='y', padx=(2, 5), pady=5, ipadx=15)
        
        # === 左側: ファイル選択 ===
        self._create_file_selection_area(left_frame)
        
        # === 中央: 処理設定 ===
        self._create_processing_settings(center_frame)
        
        # === 右側: 出力設定 ===
        self._create_output_settings(right_frame)

    def _create_file_selection_area(self, parent):
        """ファイル選択エリア作成"""
        # ファイル選択エリア
        file_select_frame = tk.Frame(parent, bg='#f8f8f8', relief='solid', bd=2)
        file_select_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.file_select_label = tk.Label(
            file_select_frame,
            text="📁 ここをクリックしてPDFファイルを選択\n\n複数ファイル選択可能\n対応形式: PDF",
            bg='#f8f8f8',
            font=('Arial', 12),
            fg='#555555',
            cursor='hand2'
        )
        self.file_select_label.pack(expand=True)
        self.file_select_label.bind('<Button-1>', self._select_files)
        file_select_frame.bind('<Button-1>', self._select_files)
        
        # ファイル操作ボタン
        file_buttons = ttk.Frame(parent)
        file_buttons.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(file_buttons, text="📁 ファイル追加", command=self._select_files).pack(side='left', padx=(0, 5))
        ttk.Button(file_buttons, text="📂 フォルダから追加", command=self._select_folder).pack(side='left', padx=5)
        ttk.Button(file_buttons, text="🗑️ クリア", command=self._clear_files).pack(side='left', padx=5)
        
        # ファイルリスト
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill='both', expand=True, padx=10, pady=(5, 10))
        
        ttk.Label(list_frame, text="選択されたファイル:", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill='both', expand=True, pady=(5, 0))
        
        self.files_listbox = tk.Listbox(list_container, font=('Arial', 9))
        list_scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        self.files_listbox.pack(side='left', fill='both', expand=True)
        list_scrollbar.pack(side='right', fill='y')

    def _create_processing_settings(self, parent):
        """処理設定エリア作成"""
        # 年月設定
        year_frame = ttk.LabelFrame(parent, text="年月設定")
        year_frame.pack(fill='x', padx=5, pady=(5, 10))
        
        ttk.Label(year_frame, text="処理年月 (YYMM):").pack(anchor='w', padx=5, pady=(5, 0))
        self.year_month_var = tk.StringVar(value="2508")
        ttk.Entry(year_frame, textvariable=self.year_month_var, width=10).pack(anchor='w', padx=5, pady=(2, 10))
        
        # 自治体セット設定（5セット対応）
        sets_config_frame = ttk.LabelFrame(parent, text="自治体セット設定（最大5セット）")
        sets_config_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        # 東京都制限の注意書き
        warning_label = ttk.Label(
            sets_config_frame, 
            text="⚠️ 東京都は必ずセット1に入力", 
            font=('Arial', 8), 
            foreground='red'
        )
        warning_label.pack(pady=(5, 5))
        
        self.set_controls = {}
        
        for set_num in range(1, 6):
            set_frame = ttk.Frame(sets_config_frame)
            set_frame.pack(fill='x', padx=5, pady=1)
            
            # セットラベル
            ttk.Label(set_frame, text=f"セット{set_num}:", width=6, font=('Arial', 8, 'bold')).pack(side='left')
            
            # 都道府県選択
            pref_var = tk.StringVar(value=self.municipality_sets[set_num]["prefecture"])
            pref_combo = ttk.Combobox(
                set_frame, 
                textvariable=pref_var, 
                values=self.prefectures,
                width=8, 
                state='readonly',
                font=('Arial', 7)
            )
            pref_combo.pack(side='left', padx=(3, 2))
            
            # 市町村入力
            muni_var = tk.StringVar(value=self.municipality_sets[set_num]["municipality"])
            muni_entry = ttk.Entry(set_frame, textvariable=muni_var, width=8, font=('Arial', 7))
            muni_entry.pack(side='left', padx=(2, 3))
            
            # イベントバインド
            pref_combo.bind('<<ComboboxSelected>>', 
                          lambda e, s=set_num, pv=pref_var, mv=muni_var: self._update_set_config(s, pv.get(), mv.get()))
            muni_entry.bind('<Return>', 
                          lambda e, s=set_num, pv=pref_var, mv=muni_var: self._update_set_config(s, pv.get(), mv.get()))
            
            self.set_controls[set_num] = {
                'prefecture': pref_var,
                'municipality': muni_var
            }
        
        # 現在のセット設定表示
        current_set_frame = ttk.LabelFrame(parent, text="現在のセット設定")
        current_set_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.set_info_text = tk.Text(current_set_frame, height=6, font=('Arial', 7), state='disabled')
        self.set_info_text.pack(fill='x', padx=5, pady=5)
        self._update_set_display()

    def _create_output_settings(self, parent):
        """出力設定エリア作成"""
        # 出力先ディレクトリ選択
        output_dir_frame = ttk.LabelFrame(parent, text="出力先ディレクトリ")
        output_dir_frame.pack(fill='x', padx=5, pady=(5, 10))
        
        ttk.Label(output_dir_frame, text="出力先:", font=('Arial', 9)).pack(anchor='w', padx=5, pady=(5, 2))
        
        self.output_dir_var = tk.StringVar(value="元ファイルと同じ場所")
        self.output_dir_label = tk.Label(
            output_dir_frame, 
            textvariable=self.output_dir_var, 
            bg='white', 
            relief='sunken', 
            anchor='w',
            font=('Arial', 8),
            wraplength=150
        )
        self.output_dir_label.pack(fill='x', padx=5, pady=(0, 5))
        
        # 出力先選択ボタン
        output_buttons = ttk.Frame(output_dir_frame)
        output_buttons.pack(fill='x', padx=5, pady=(0, 10))
        
        ttk.Button(output_buttons, text="📂 選択", command=self._select_output_directory, width=8).pack(side='left', padx=(0, 5))
        ttk.Button(output_buttons, text="🔄 リセット", command=self._reset_output_directory, width=8).pack(side='left')
        
        # 処理オプション
        options_frame = ttk.LabelFrame(parent, text="処理オプション")
        options_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.backup_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="元ファイルをバックアップ", variable=self.backup_mode_var).pack(anchor='w', padx=5, pady=2)
        
        self.overwrite_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="既存ファイル上書き", variable=self.overwrite_mode_var).pack(anchor='w', padx=5, pady=2)
        
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="デバッグログ出力", variable=self.debug_mode_var).pack(anchor='w', padx=5, pady=2)
        
        # 処理実行
        process_frame = ttk.Frame(parent)
        process_frame.pack(fill='x', padx=5, pady=15)
        
        self.process_button = ttk.Button(
            process_frame,
            text="🚀 リネーム処理開始",
            command=self._start_processing
        )
        self.process_button.pack(fill='x', pady=(0, 10))
        
        # プログレス
        self.progress = ttk.Progressbar(process_frame)
        self.progress.pack(fill='x', pady=(0, 5))
        
        self.status_var = tk.StringVar(value="待機中")
        ttk.Label(process_frame, textvariable=self.status_var, font=('Arial', 9)).pack()

    def _create_results_tab(self):
        """処理結果タブ作成"""
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="📊 処理結果")
        
        # 結果サマリー
        summary_frame = ttk.LabelFrame(self.results_frame, text="処理サマリー")
        summary_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        self.summary_text = tk.Text(summary_frame, height=4, font=('Arial', 9), state='disabled')
        self.summary_text.pack(fill='x', padx=5, pady=5)
        
        # 詳細結果
        details_frame = ttk.LabelFrame(self.results_frame, text="詳細結果")
        details_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 結果テーブル
        columns = ('元ファイル名', '新ファイル名', '出力先', '状態', '詳細')
        self.results_tree = ttk.Treeview(details_frame, columns=columns, show='headings', height=15)
        
        # カラム設定
        self.results_tree.heading('元ファイル名', text='元ファイル名')
        self.results_tree.heading('新ファイル名', text='新ファイル名') 
        self.results_tree.heading('出力先', text='出力先')
        self.results_tree.heading('状態', text='状態')
        self.results_tree.heading('詳細', text='詳細')
        
        self.results_tree.column('元ファイル名', width=200)
        self.results_tree.column('新ファイル名', width=250)
        self.results_tree.column('出力先', width=200)
        self.results_tree.column('状態', width=80)
        self.results_tree.column('詳細', width=150)
        
        # スクロールバー
        results_scrollbar_v = ttk.Scrollbar(details_frame, orient='vertical', command=self.results_tree.yview)
        results_scrollbar_h = ttk.Scrollbar(details_frame, orient='horizontal', command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=results_scrollbar_v.set, xscrollcommand=results_scrollbar_h.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        results_scrollbar_v.pack(side='right', fill='y')
        results_scrollbar_h.pack(side='bottom', fill='x')
        
        # 結果操作ボタン
        results_buttons = ttk.Frame(self.results_frame)
        results_buttons.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(results_buttons, text="📋 結果をクリップボードにコピー", command=self._copy_results).pack(side='left', padx=(0, 5))
        ttk.Button(results_buttons, text="💾 結果をCSVで保存", command=self._save_results_csv).pack(side='left', padx=5)
        ttk.Button(results_buttons, text="📂 出力フォルダを開く", command=self._open_output_folder).pack(side='left', padx=5)

    def _create_log_tab(self):
        """ログタブ作成"""
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="📋 システムログ")
        
        # ログ表示エリア
        log_container = ttk.Frame(self.log_frame)
        log_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Label(log_container, text="システムログ", font=('Arial', 14, 'bold')).pack(anchor='w')
        
        # ログテキスト
        log_text_frame = ttk.Frame(log_container)
        log_text_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        self.log_text = tk.Text(log_text_frame, font=('Arial', 9), state='disabled')
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')

    def _select_output_directory(self):
        """出力ディレクトリ選択"""
        directory = filedialog.askdirectory(title="出力先ディレクトリを選択")
        if directory:
            self.output_directory = directory
            self.output_dir_var.set(directory)
            self._log(f"出力先を設定: {directory}")

    def _reset_output_directory(self):
        """出力ディレクトリリセット"""
        self.output_directory = ""
        self.output_dir_var.set("元ファイルと同じ場所")
        self._log("出力先をリセット: 元ファイルと同じ場所")

    def _update_set_config(self, set_num: int, prefecture: str, municipality: str):
        """セット設定更新"""
        # 東京都制限チェック
        if prefecture == "東京都" and set_num != 1:
            messagebox.showerror("エラー", "東京都は1番目（セット1）に入力してください")
            self.set_controls[set_num]['prefecture'].set("")
            return
        
        # 他のセットに東京都があるかチェック
        if prefecture == "東京都":
            for other_set in range(1, 6):
                if other_set != set_num and self.municipality_sets[other_set]["prefecture"] == "東京都":
                    messagebox.showerror("エラー", "東京都は既に他のセットに設定されています")
                    self.set_controls[set_num]['prefecture'].set("")
                    return
        
        # 設定更新
        self.municipality_sets[set_num]["prefecture"] = prefecture
        self.municipality_sets[set_num]["municipality"] = municipality
        
        # 連番計算
        active_sets = self._get_active_sets()
        if prefecture in active_sets:
            set_order = active_sets.index(prefecture) + 1
            self.municipality_sets[set_num]["pref_code"] = 1001 + (set_order - 1) * 10
            if municipality:
                self.municipality_sets[set_num]["muni_code"] = 2001 + (set_order - 1) * 10
            else:
                self.municipality_sets[set_num]["muni_code"] = None
        else:
            self.municipality_sets[set_num]["pref_code"] = None
            self.municipality_sets[set_num]["muni_code"] = None
        
        self._update_set_display()
        self._log(f"セット{set_num}を更新: {prefecture} {municipality}")

    def _get_active_sets(self) -> List[str]:
        """アクティブなセットの都道府県リストを入力順で取得"""
        active_sets = []
        for i in range(1, 6):
            if self.municipality_sets[i]["prefecture"]:
                active_sets.append(self.municipality_sets[i]["prefecture"])
        return active_sets

    def _update_set_display(self):
        """セット設定表示更新"""
        self.set_info_text.config(state='normal')
        self.set_info_text.delete('1.0', tk.END)
        
        display_text = "現在の設定:\n"
        
        for set_num in range(1, 6):
            set_data = self.municipality_sets[set_num]
            if set_data["prefecture"]:
                pref_code = set_data["pref_code"] or "未計算"
                muni_code = set_data["muni_code"] or "なし"
                
                display_text += f"セット{set_num}: {set_data['prefecture']}"
                if set_data["municipality"]:
                    display_text += f" {set_data['municipality']}"
                display_text += f" ({pref_code}"
                if set_data["municipality"]:
                    display_text += f"/{muni_code}"
                display_text += ")\n"
        
        if not any(self.municipality_sets[i]["prefecture"] for i in range(1, 6)):
            display_text += "設定なし"
        
        self.set_info_text.insert('1.0', display_text)
        self.set_info_text.config(state='disabled')

    def _select_files(self, event=None):
        """ファイル選択"""
        files = filedialog.askopenfilenames(
            title="PDFファイルを選択",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if files:
            for file_path in files:
                if file_path not in self.files_list:
                    self.files_list.append(file_path)
                    self.files_listbox.insert(tk.END, os.path.basename(file_path))
            self._log(f"{len(files)}個のファイルを追加しました")

    def _select_folder(self):
        """フォルダから選択"""
        folder = filedialog.askdirectory(title="PDFファイルが含まれるフォルダを選択")
        if folder:
            pdf_files = []
            for file_path in Path(folder).glob("*.pdf"):
                if str(file_path) not in self.files_list:
                    pdf_files.append(str(file_path))
                    self.files_list.append(str(file_path))
                    self.files_listbox.insert(tk.END, file_path.name)
            self._log(f"フォルダから{len(pdf_files)}個のPDFファイルを追加しました")

    def _clear_files(self):
        """ファイルリストクリア"""
        self.files_list.clear()
        self.files_listbox.delete(0, tk.END)
        self._log("ファイルリストをクリアしました")

    def _start_processing(self):
        """処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.processing:
            messagebox.showinfo("情報", "処理中です。しばらくお待ちください。")
            return
        
        # 設定検証
        year_month = self.year_month_var.get().strip()
        if not year_month:
            messagebox.showerror("エラー", "年月を入力してください")
            return
        
        if len(year_month) != 4 or not year_month.isdigit():
            messagebox.showerror("エラー", "年月はYYMM形式（4桁）で入力してください")
            return
        
        # 出力ディレクトリ確認
        if self.output_directory and not os.path.exists(self.output_directory):
            messagebox.showerror("エラー", "出力ディレクトリが存在しません")
            return
        
        # 結果テーブルクリア
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # バックグラウンド処理開始
        self.processing = True
        self.process_button.config(state='disabled')
        self.status_var.set("処理中...")
        self.progress.config(mode='indeterminate')
        self.progress.start()
        
        threading.Thread(target=self._process_files, daemon=True).start()

    def _process_files(self):
        """ファイル処理（バックグラウンド）"""
        try:
            results = []
            year_month = self.year_month_var.get().strip()
            success_count = 0
            error_count = 0
            
            for i, file_path in enumerate(self.files_list):
                try:
                    # 出力先決定
                    if self.output_directory:
                        output_dir = self.output_directory
                    else:
                        output_dir = os.path.dirname(file_path)
                    
                    # ファイル名生成（簡単なダミー処理）
                    original_filename = os.path.basename(file_path)
                    new_filename = self._generate_filename(original_filename, year_month)
                    output_path = os.path.join(output_dir, new_filename)
                    
                    # バックアップ処理
                    backup_path = None
                    if self.backup_mode_var.get():
                        backup_dir = os.path.join(output_dir, "backup")
                        os.makedirs(backup_dir, exist_ok=True)
                        backup_path = os.path.join(backup_dir, f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_filename}")
                    
                    # ファイル処理実行
                    if os.path.exists(output_path) and not self.overwrite_mode_var.get():
                        # 重複ファイル名対応
                        base, ext = os.path.splitext(new_filename)
                        counter = 1
                        while os.path.exists(os.path.join(output_dir, f"{base}_{counter:02d}{ext}")):
                            counter += 1
                        new_filename = f"{base}_{counter:02d}{ext}"
                        output_path = os.path.join(output_dir, new_filename)
                    
                    # バックアップ
                    if backup_path:
                        shutil.copy2(file_path, backup_path)
                    
                    # ファイルコピー（実際の処理では分類・リネーム処理を行う）
                    shutil.copy2(file_path, output_path)
                    
                    results.append({
                        'original': original_filename,
                        'renamed': new_filename,
                        'output_dir': output_dir,
                        'status': '成功',
                        'details': '正常処理',
                        'backup_path': backup_path
                    })
                    success_count += 1
                    
                except Exception as e:
                    results.append({
                        'original': os.path.basename(file_path),
                        'renamed': 'エラー',
                        'output_dir': '不明',
                        'status': 'エラー',
                        'details': str(e),
                        'backup_path': None
                    })
                    error_count += 1
            
            # UI更新
            self.root.after(0, lambda: self._processing_complete(results, success_count, error_count))
            
        except Exception as e:
            self.root.after(0, lambda: self._processing_error(str(e)))

    def _generate_filename(self, original_filename: str, year_month: str) -> str:
        """ファイル名生成（簡単な分類ロジック）"""
        # 実際の処理では、PDFの内容を解析して適切な番号を決定
        filename_lower = original_filename.lower()
        
        if "法人税" in original_filename:
            return f"0001_法人税及び地方法人税申告書_{year_month}.pdf"
        elif "消費税" in original_filename:
            return f"3001_消費税及び地方消費税申告書_{year_month}.pdf"
        elif "都道府県" in original_filename or "県税" in original_filename:
            return f"1001_東京都_法人都道府県民税・事業税・特別法人事業税_{year_month}.pdf"
        elif "市民税" in original_filename:
            return f"2001_東京都東京市_法人市民税_{year_month}.pdf"
        elif "納付" in original_filename:
            return f"0000_納付税額一覧表_{year_month}.pdf"
        else:
            return f"0001_法人税及び地方法人税申告書_{year_month}.pdf"

    def _processing_complete(self, results, success_count, error_count):
        """処理完了"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.stop()
        self.progress.config(mode='determinate')
        self.status_var.set("完了")
        
        # サマリー表示
        self.summary_text.config(state='normal')
        self.summary_text.delete('1.0', tk.END)
        
        summary_text = f"""処理完了: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

総処理件数: {len(results)}件
成功: {success_count}件
エラー: {error_count}件
出力先: {self.output_directory or '元ファイルと同じ場所'}
バックアップ: {'有効' if self.backup_mode_var.get() else '無効'}"""
        
        self.summary_text.insert('1.0', summary_text)
        self.summary_text.config(state='disabled')
        
        # 詳細結果表示
        for result in results:
            self.results_tree.insert('', 'end', values=(
                result['original'],
                result['renamed'],
                result['output_dir'],
                result['status'],
                result['details']
            ))
        
        # 結果保存
        self.processing_results = results
        
        # 結果タブに切り替え
        self.notebook.select(1)
        
        self._log(f"処理完了: 成功{success_count}件、エラー{error_count}件")
        messagebox.showinfo("完了", f"処理が完了しました。\n成功: {success_count}件\nエラー: {error_count}件")

    def _processing_error(self, error_msg):
        """処理エラー"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.stop()
        self.progress.config(mode='determinate')
        self.status_var.set("エラー")
        
        self._log(f"処理エラー: {error_msg}")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{error_msg}")

    def _copy_results(self):
        """結果をクリップボードにコピー"""
        if not self.processing_results:
            messagebox.showinfo("情報", "処理結果がありません")
            return
        
        result_text = "処理結果\n" + "="*50 + "\n"
        for result in self.processing_results:
            result_text += f"元ファイル: {result['original']}\n"
            result_text += f"新ファイル: {result['renamed']}\n"
            result_text += f"出力先: {result['output_dir']}\n"
            result_text += f"状態: {result['status']}\n"
            result_text += f"詳細: {result['details']}\n"
            result_text += "-" * 30 + "\n"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(result_text)
        messagebox.showinfo("完了", "処理結果をクリップボードにコピーしました")

    def _save_results_csv(self):
        """結果をCSVで保存"""
        if not self.processing_results:
            messagebox.showinfo("情報", "処理結果がありません")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="処理結果を保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ['元ファイル名', '新ファイル名', '出力先', '状態', '詳細']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for result in self.processing_results:
                        writer.writerow({
                            '元ファイル名': result['original'],
                            '新ファイル名': result['renamed'],
                            '出力先': result['output_dir'],
                            '状態': result['status'],
                            '詳細': result['details']
                        })
                
                messagebox.showinfo("完了", f"処理結果を保存しました:\n{file_path}")
                self._log(f"処理結果をCSV保存: {file_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"CSV保存中にエラーが発生しました:\n{e}")

    def _open_output_folder(self):
        """出力フォルダを開く"""
        if self.output_directory:
            os.startfile(self.output_directory)
        else:
            messagebox.showinfo("情報", "出力フォルダが設定されていません")

    def _log(self, message: str):
        """ログ出力"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV5Enhanced()
    app.run()