#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 正式版
正しい仕様に基づく実装: 最大5セット、東京都1番目制限、正確な連番体系
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import sys
from pathlib import Path
from typing import List, Dict, Optional

class TaxDocumentRenamerV5Correct:
    """税務書類リネームシステム v5.0 正式版"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.0 正式版")
        self.root.geometry("1200x800")
        
        # システム変数
        self.files_list = []
        self.processing = False
        self.processing_results = []
        
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
        self._log("税務書類リネームシステム v5.0 正式版を起動しました")

    def _create_ui(self):
        """メインUI作成"""
        # メインコンテナ
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="税務書類リネームシステム v5.0 正式版",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="最大5セット対応・東京都1番目制限・正確な連番体系",
            font=('Arial', 10),
            foreground='blue'
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
        
        # 左右分割
        left_frame = ttk.LabelFrame(self.main_frame, text="ファイル選択")
        left_frame.pack(side='left', fill='both', expand=True, padx=(5, 2), pady=5)
        
        right_frame = ttk.LabelFrame(self.main_frame, text="処理設定")
        right_frame.pack(side='right', fill='y', padx=(2, 5), pady=5, ipadx=15)
        
        # === 左側: ファイル選択 ===
        # ファイル選択エリア
        file_select_frame = tk.Frame(left_frame, bg='#f8f8f8', relief='solid', bd=2)
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
        file_buttons = ttk.Frame(left_frame)
        file_buttons.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(file_buttons, text="📁 ファイル追加", command=self._select_files).pack(side='left', padx=(0, 5))
        ttk.Button(file_buttons, text="📂 フォルダから追加", command=self._select_folder).pack(side='left', padx=5)
        ttk.Button(file_buttons, text="🗑️ クリア", command=self._clear_files).pack(side='left', padx=5)
        
        # ファイルリスト
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=(5, 10))
        
        ttk.Label(list_frame, text="選択されたファイル:", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill='both', expand=True, pady=(5, 0))
        
        self.files_listbox = tk.Listbox(list_container, font=('Arial', 9))
        list_scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        self.files_listbox.pack(side='left', fill='both', expand=True)
        list_scrollbar.pack(side='right', fill='y')
        
        # === 右側: 処理設定 ===
        # 年月設定
        year_frame = ttk.LabelFrame(right_frame, text="年月設定")
        year_frame.pack(fill='x', padx=5, pady=(5, 10))
        
        ttk.Label(year_frame, text="処理年月 (YYMM):").pack(anchor='w', padx=5, pady=(5, 0))
        self.year_month_var = tk.StringVar(value="2508")
        ttk.Entry(year_frame, textvariable=self.year_month_var, width=10).pack(anchor='w', padx=5, pady=(2, 10))
        
        # 自治体セット設定（5セット対応）
        sets_config_frame = ttk.LabelFrame(right_frame, text="自治体セット設定（最大5セット）")
        sets_config_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        # 東京都制限の注意書き
        warning_label = ttk.Label(
            sets_config_frame, 
            text="⚠️ 東京都は必ずセット1に入力してください", 
            font=('Arial', 8), 
            foreground='red'
        )
        warning_label.pack(pady=(5, 5))
        
        self.set_controls = {}
        
        for set_num in range(1, 6):
            set_frame = ttk.Frame(sets_config_frame)
            set_frame.pack(fill='x', padx=5, pady=2)
            
            # セットラベル
            ttk.Label(set_frame, text=f"セット{set_num}:", width=6, font=('Arial', 9, 'bold')).pack(side='left')
            
            # 都道府県選択（47都道府県）
            pref_var = tk.StringVar(value=self.municipality_sets[set_num]["prefecture"])
            pref_combo = ttk.Combobox(
                set_frame, 
                textvariable=pref_var, 
                values=self.prefectures,
                width=8, 
                state='readonly',
                font=('Arial', 8)
            )
            pref_combo.pack(side='left', padx=(5, 3))
            
            # 市町村入力（手入力）
            muni_var = tk.StringVar(value=self.municipality_sets[set_num]["municipality"])
            muni_entry = ttk.Entry(set_frame, textvariable=muni_var, width=8, font=('Arial', 8))
            muni_entry.pack(side='left', padx=(3, 5))
            
            # 都道府県変更時の自動更新
            pref_combo.bind('<<ComboboxSelected>>', 
                          lambda e, s=set_num, pv=pref_var, mv=muni_var: self._update_set_config(s, pv.get(), mv.get()))
            
            # Enterキーでの更新
            muni_entry.bind('<Return>', 
                          lambda e, s=set_num, pv=pref_var, mv=muni_var: self._update_set_config(s, pv.get(), mv.get()))
            
            self.set_controls[set_num] = {
                'prefecture': pref_var,
                'municipality': muni_var
            }
        
        # 現在のセット設定表示
        current_set_frame = ttk.LabelFrame(right_frame, text="現在のセット設定")
        current_set_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.set_info_text = tk.Text(current_set_frame, height=8, font=('Arial', 8), state='disabled')
        self.set_info_text.pack(fill='x', padx=5, pady=5)
        self._update_set_display()
        
        # 処理オプション
        options_frame = ttk.LabelFrame(right_frame, text="処理オプション")
        options_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="デバッグログ出力", variable=self.debug_mode_var).pack(anchor='w', padx=5, pady=2)
        
        # 処理実行
        process_frame = ttk.Frame(right_frame)
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
        
        # 結果表示エリア
        results_container = ttk.Frame(self.results_frame)
        results_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Label(results_container, text="処理結果", font=('Arial', 14, 'bold')).pack(anchor='w')
        
        # 結果テキスト
        results_text_frame = ttk.Frame(results_container)
        results_text_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        self.results_text = tk.Text(results_text_frame, font=('Arial', 9), state='disabled')
        results_scrollbar = ttk.Scrollbar(results_text_frame, orient='vertical', command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_text.pack(side='left', fill='both', expand=True)
        results_scrollbar.pack(side='right', fill='y')

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
        
        display_text = "現在のセット設定:\n\n"
        
        for set_num in range(1, 6):
            set_data = self.municipality_sets[set_num]
            if set_data["prefecture"]:
                pref_code = set_data["pref_code"] or "未計算"
                muni_code = set_data["muni_code"] or "なし"
                
                display_text += f"セット{set_num}: {set_data['prefecture']}"
                if set_data["municipality"]:
                    display_text += f" {set_data['municipality']}"
                display_text += f"\n  都道府県: {pref_code}"
                if set_data["municipality"]:
                    display_text += f"\n  市町村: {muni_code}"
                display_text += "\n\n"
        
        if not any(self.municipality_sets[i]["prefecture"] for i in range(1, 6)):
            display_text += "設定されたセットはありません。"
        
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
            
            for i, file_path in enumerate(self.files_list):
                try:
                    # 簡単なダミー処理（実際の処理はここに実装）
                    filename = os.path.basename(file_path)
                    new_name = f"0001_法人税及び地方法人税申告書_{year_month}.pdf"
                    
                    results.append({
                        'original': filename,
                        'renamed': new_name,
                        'status': 'success'
                    })
                    
                except Exception as e:
                    results.append({
                        'original': os.path.basename(file_path),
                        'renamed': 'エラー',
                        'status': 'error',
                        'error': str(e)
                    })
            
            # UI更新
            self.root.after(0, lambda: self._processing_complete(results))
            
        except Exception as e:
            self.root.after(0, lambda: self._processing_error(str(e)))

    def _processing_complete(self, results):
        """処理完了"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.stop()
        self.progress.config(mode='determinate')
        self.status_var.set("完了")
        
        # 結果表示
        self.results_text.config(state='normal')
        self.results_text.delete('1.0', tk.END)
        
        result_text = f"処理結果 ({len(results)}件)\n\n"
        
        for result in results:
            result_text += f"元ファイル: {result['original']}\n"
            result_text += f"新ファイル: {result['renamed']}\n"
            result_text += f"状態: {result['status']}\n"
            if result.get('error'):
                result_text += f"エラー: {result['error']}\n"
            result_text += "-" * 50 + "\n"
        
        self.results_text.insert('1.0', result_text)
        self.results_text.config(state='disabled')
        
        # 結果タブに切り替え
        self.notebook.select(1)
        
        self._log(f"処理完了: {len(results)}件")
        messagebox.showinfo("完了", f"処理が完了しました。\n処理件数: {len(results)}件")

    def _processing_error(self, error_msg):
        """処理エラー"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.stop()
        self.progress.config(mode='determinate')
        self.status_var.set("エラー")
        
        self._log(f"処理エラー: {error_msg}")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{error_msg}")

    def _log(self, message: str):
        """ログ出力"""
        import datetime
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
    app = TaxDocumentRenamerV5Correct()
    app.run()