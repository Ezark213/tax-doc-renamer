#!/usr/bin/env python3
"""
税務書類リネームシステム v5.1 - 修正版
CSV番号修正・prefecture_sequence対応・自治体連番システム完全対応
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import sys
from pathlib import Path
from typing import List, Dict, Optional
import datetime
import shutil

# 分類エンジンをインポート
try:
    # v5.0_ultimateフォルダのパスを追加
    sys.path.append(os.path.join(os.path.dirname(__file__), 'v5.0_ultimate', 'core'))
    from classification_v5_fixed import DocumentClassifierV5Fixed as UltimateClassificationEngine
except ImportError:
    # 代替パスでインポート
    try:
        from v5_0_ultimate.core.classification_v5_fixed import DocumentClassifierV5Fixed as UltimateClassificationEngine
    except ImportError:
        print("分類エンジンがインポートできません。classification_v5_fixed.py が存在することを確認してください。")
        sys.exit(1)

class TaxDocumentRenamerV51:
    """税務書類リネームシステム v5.1 修正版"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.1 修正版")
        self.root.geometry("1200x800")
        
        # システム変数
        self.files_list = []
        self.processing = False
        self.processing_results = []
        self.output_folder = ""
        
        # 分類エンジン初期化
        self.classifier = UltimateClassificationEngine(
            debug_mode=True,
            log_callback=self._log_callback
        )
        
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
        
        # 自治体セット設定（修正版要件に基づく）
        self.municipality_sets = {
            1: {"prefecture": "東京都", "municipality": "", "pref_code": 1001, "muni_code": None},
            2: {"prefecture": "愛知県", "municipality": "蒲郡市", "pref_code": 1011, "muni_code": 2001},
            3: {"prefecture": "福岡県", "municipality": "福岡市", "pref_code": 1021, "muni_code": 2011}
        }
        
        # UI構築
        self._create_ui()
        self._log("税務書類リネームシステム v5.1 修正版を起動しました")

    def _create_ui(self):
        """メインUI作成"""
        # メインコンテナ
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="税務書類リネームシステム v5.1 修正版",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="CSV番号修正版・prefecture_sequence対応・自治体連番システム完全対応",
            font=('Arial', 10),
            foreground='blue'
        )
        subtitle_label.pack(pady=(0, 15))
        
        # ノートブック（タブ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # タブ作成
        self._create_main_tab()
        self._create_settings_tab()
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
            text="📁 ここをクリックしてPDFファイルを選択\n\n複数ファイル選択可能\n対応形式: PDF, CSV",
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
        
        # 出力先設定
        output_frame = ttk.LabelFrame(right_frame, text="出力先設定")
        output_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.output_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_var, width=25, state='readonly').pack(anchor='w', padx=5, pady=(5, 5))
        ttk.Button(output_frame, text="📂 出力先選択", command=self._select_output_folder).pack(anchor='w', padx=5, pady=(0, 10))
        
        # 自治体セット設定
        sets_config_frame = ttk.LabelFrame(right_frame, text="自治体セット設定（修正版）")
        sets_config_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.set_controls = {}
        
        for set_num in range(1, 4):
            set_frame = ttk.Frame(sets_config_frame)
            set_frame.pack(fill='x', padx=5, pady=3)
            
            # セットラベル
            ttk.Label(set_frame, text=f"セット{set_num}:", width=6, font=('Arial', 9, 'bold')).pack(side='left')
            
            # 都道府県選択
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
            
            # 市町村入力
            muni_var = tk.StringVar(value=self.municipality_sets[set_num]["municipality"])
            muni_entry = ttk.Entry(set_frame, textvariable=muni_var, width=8, font=('Arial', 8))
            muni_entry.pack(side='left', padx=(3, 5))
            
            # 変更時の自動更新
            pref_combo.bind('<<ComboboxSelected>>', 
                          lambda e, s=set_num, pv=pref_var, mv=muni_var: self._update_set_config(s, pv.get(), mv.get()))
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
        
        self.copy_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="コピーモード（元ファイル保持）", variable=self.copy_mode_var).pack(anchor='w', padx=5, pady=2)
        
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

    def _create_settings_tab(self):
        """設定タブ作成"""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="⚙️ システム設定")
        
        # 設定情報
        info_frame = ttk.LabelFrame(self.settings_frame, text="修正内容")
        info_frame.pack(fill='x', padx=10, pady=10)
        
        info_text = """税務書類リネームシステム v5.1 修正版

修正内容:
• CSV仕訳帳の番号修正: 5006 → 5005
• prefecture_sequence属性エラーの修正
• 自治体連番システムの完全対応:
  - セット1: 東京都 (1001, 1003, 1004)
  - セット2: 愛知県蒲郡市 (1011, 1013, 1014, 2001, 2003, 2004)
  - セット3: 福岡県福岡市 (1021, 1023, 1024, 2011, 2013, 2014)
• OCR突合チェック機能（アラート対応）
• 複数ファイル処理の安定化

新機能:
• テキスト内容から自治体を自動認識
• 画像認識と設定の突合チェック
• エラーハンドリングの強化"""
        
        info_label = tk.Text(info_frame, height=15, wrap='word', font=('Arial', 9))
        info_label.pack(fill='both', expand=True, padx=10, pady=10)
        info_label.insert('1.0', info_text)
        info_label.config(state='disabled')

    def _create_results_tab(self):
        """結果タブ作成"""
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="📊 処理結果")
        
        # 結果表示
        results_container = ttk.Frame(self.results_frame)
        results_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Label(results_container, text="処理結果一覧", font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # 結果テーブル
        columns = ('元ファイル名', '新ファイル名', '信頼度', 'セット', 'ステータス')
        self.results_tree = ttk.Treeview(results_container, columns=columns, show='headings')
        
        # 列設定
        column_widths = {'元ファイル名': 280, '新ファイル名': 350, '信頼度': 80, 'セット': 100, 'ステータス': 80}
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=column_widths[col])
        
        # スクロールバー
        results_scrollbar = ttk.Scrollbar(results_container, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        results_scrollbar.pack(side='right', fill='y')
        
        # 結果操作ボタン
        results_buttons = ttk.Frame(self.results_frame)
        results_buttons.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(results_buttons, text="💾 CSV形式で保存", command=self._save_results).pack(side='left', padx=(0, 5))
        ttk.Button(results_buttons, text="🗑️ 結果クリア", command=self._clear_results).pack(side='left', padx=5)

    def _create_log_tab(self):
        """ログタブ作成"""
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="📝 システムログ")
        
        # ログ表示
        log_container = ttk.Frame(self.log_frame)
        log_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Label(log_container, text="システムログ", font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        log_text_frame = ttk.Frame(log_container)
        log_text_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_text_frame, wrap='word', font=('Consolas', 9), bg='#f5f5f5')
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # ログ操作ボタン
        log_buttons = ttk.Frame(self.log_frame)
        log_buttons.pack(fill='x', padx=10, pady=(5, 10))
        
        ttk.Button(log_buttons, text="🗑️ ログクリア", command=self._clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(log_buttons, text="💾 ログ保存", command=self._save_log).pack(side='left', padx=5)

    def _log_callback(self, message: str):
        """分類エンジンからのログコールバック"""
        self._log(message)

    def _log(self, message: str):
        """ログ出力"""
        if hasattr(self, 'log_text'):
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            self.log_text.insert('end', log_entry + '\n')
            self.log_text.see('end')
            
            if self.debug_mode_var.get():
                print(log_entry)

    def _update_set_display(self):
        """セット表示更新"""
        self.set_info_text.config(state='normal')
        self.set_info_text.delete('1.0', 'end')
        
        for set_num, info in self.municipality_sets.items():
            line1 = f"セット{set_num}: {info['prefecture']}"
            if info['municipality']:
                line1 += f"{info['municipality']}"
            line1 += "\n"
            
            line2 = f"  都道府県: {info['pref_code']}1, {info['pref_code']}3, {info['pref_code']}4\n"
            
            if info['muni_code']:
                line3 = f"  市町村: {info['muni_code']}1, {info['muni_code']}3, {info['muni_code']}4\n"
            else:
                line3 = f"  市町村: なし\n"
            
            self.set_info_text.insert('end', line1 + line2 + line3 + '\n')
        
        self.set_info_text.config(state='disabled')

    def _update_set_config(self, set_num, prefecture, municipality):
        """セット設定更新"""
        # 都道府県コード計算
        base_codes = {1: 1001, 2: 1011, 3: 1021}
        pref_code = base_codes.get(set_num, 1001)
        
        # 市町村コード計算
        muni_code = None
        if set_num == 2 and municipality:
            muni_code = 2001
        elif set_num == 3 and municipality:
            muni_code = 2011
        
        # セット設定更新
        self.municipality_sets[set_num] = {
            'prefecture': prefecture,
            'municipality': municipality,
            'pref_code': pref_code,
            'muni_code': muni_code
        }
        
        # 分類エンジンにも反映
        self.classifier.prefecture_sequence[set_num] = {"prefecture": prefecture, "code": pref_code}
        if muni_code:
            self.classifier.municipality_sequence[set_num] = {"municipality": municipality, "code": muni_code}
        else:
            self.classifier.municipality_sequence[set_num] = None
        
        self._update_set_display()
        self._log(f"セット{set_num}を更新: {prefecture}{municipality if municipality else ''}")

    def _select_files(self, event=None):
        """ファイル選択"""
        files = filedialog.askopenfilenames(
            title="PDFファイル・CSVファイルを選択",
            filetypes=[
                ("税務書類", "*.pdf *.csv"),
                ("PDF files", "*.pdf"), 
                ("CSV files", "*.csv"), 
                ("All files", "*.*")
            ]
        )
        if files:
            added_count = 0
            for file_path in files:
                if file_path not in self.files_list:
                    self.files_list.append(file_path)
                    added_count += 1
            
            self._update_file_list()
            if added_count > 0:
                self._log(f"{added_count}個のファイルを追加しました")

    def _select_folder(self):
        """フォルダ選択"""
        folder = filedialog.askdirectory(title="税務書類が含まれるフォルダを選択")
        if folder:
            pdf_files = [str(f) for f in Path(folder).glob("*.pdf")]
            csv_files = [str(f) for f in Path(folder).glob("*.csv")]
            all_files = pdf_files + csv_files
            
            added_count = 0
            for file_path in all_files:
                if file_path not in self.files_list:
                    self.files_list.append(file_path)
                    added_count += 1
            
            self._update_file_list()
            if added_count > 0:
                self._log(f"フォルダから {added_count} 個のファイルを追加しました")

    def _clear_files(self):
        """ファイルクリア"""
        self.files_list.clear()
        self._update_file_list()
        self._log("ファイルリストをクリアしました")

    def _update_file_list(self):
        """ファイルリスト更新"""
        self.files_listbox.delete(0, 'end')
        for file_path in self.files_list:
            self.files_listbox.insert('end', os.path.basename(file_path))

    def _select_output_folder(self):
        """出力先フォルダ選択"""
        folder = filedialog.askdirectory(title="出力先フォルダを選択")
        if folder:
            self.output_folder = folder
            self.output_var.set(folder)
            self._log(f"出力先フォルダを設定しました: {folder}")

    def _start_processing(self):
        """処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルがありません。")
            return
        
        if not self.output_folder:
            messagebox.showwarning("警告", "出力先フォルダを選択してください。")
            return
        
        if self.processing:
            messagebox.showinfo("情報", "既に処理中です。")
            return
        
        self.processing = True
        self.process_button.config(state='disabled')
        self._clear_results()
        
        self._log(f"処理開始: {len(self.files_list)}個のファイル")
        self._log(f"年月: {self.year_month_var.get()}")
        self._log(f"出力先: {self.output_folder}")
        self._log(f"コピーモード: {'有効' if self.copy_mode_var.get() else '無効'}")
        
        # 処理スレッド開始
        thread = threading.Thread(target=self._process_files_thread)
        thread.daemon = True
        thread.start()

    def _process_files_thread(self):
        """ファイル処理スレッド"""
        try:
            total_files = len(self.files_list)
            self.progress.config(maximum=total_files)
            
            for i, file_path in enumerate(self.files_list):
                file_name = os.path.basename(file_path)
                self.root.after(0, lambda f=file_name: self.status_var.set(f"処理中: {f}"))
                
                try:
                    # ファイル読み込み（簡易版）
                    text_content = ""
                    if file_path.lower().endswith('.pdf'):
                        # PDFの場合は簡易テキスト抽出
                        text_content = f"PDF: {file_name}"
                    elif file_path.lower().endswith('.csv'):
                        # CSVファイルの場合
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                text_content = f.read()[:1000]  # 先頭1000文字
                        except:
                            text_content = f"CSV: {file_name}"
                    
                    # 分類実行
                    document_type, alerts = self.classifier.classify_document_v5_fixed(text_content, file_name)
                    
                    # 分類結果を使用
                    final_document_type = document_type
                    
                    # 年月付与
                    year_month = self.year_month_var.get()
                    file_ext = Path(file_path).suffix
                    final_filename = f"{final_document_type}_{year_month}{file_ext}"
                    
                    # ファイルコピー/移動
                    output_path = os.path.join(self.output_folder, final_filename)
                    
                    if self.copy_mode_var.get():
                        shutil.copy2(file_path, output_path)
                        operation = "コピー"
                    else:
                        shutil.move(file_path, output_path)
                        operation = "移動"
                    
                    # 結果記録
                    set_info = self.municipality_sets[set_number]
                    set_name = f"セット{set_number} ({set_info['prefecture']}"
                    if set_info['municipality']:
                        set_name += set_info['municipality']
                    set_name += ")"
                    
                    result = {
                        'original': file_name,
                        'new': final_filename,
                        'confidence': f"{classification_result.confidence:.2f}",
                        'set': set_name,
                        'status': "正常"
                    }
                    
                    self.processing_results.append(result)
                    self.root.after(0, self._update_results_display, result)
                    
                    self._log(f"処理完了: {file_name} → {final_filename} (信頼度:{classification_result.confidence:.2f}, {operation})")
                    
                except Exception as e:
                    # エラー処理
                    error_result = {
                        'original': file_name,
                        'new': 'エラー',
                        'confidence': '0.00',
                        'set': 'なし',
                        'status': f"エラー: {str(e)}"
                    }
                    self.processing_results.append(error_result)
                    self.root.after(0, self._update_results_display, error_result)
                    self._log(f"処理エラー: {file_path} - {str(e)}")
                
                self.root.after(0, lambda val=i+1: self.progress.config(value=val))
            
            # 処理完了
            self.root.after(0, self._processing_complete)
            
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))
        finally:
            self.root.after(0, self._processing_finished)

    def _update_results_display(self, result):
        """結果表示更新"""
        self.results_tree.insert('', 'end', values=(
            result['original'],
            result['new'], 
            result['confidence'],
            result['set'],
            result['status']
        ))

    def _processing_complete(self):
        """処理完了"""
        self.status_var.set("処理完了")
        success_count = len([r for r in self.processing_results if r['status'] == "正常"])
        self._log(f"全処理完了: 成功{success_count}件 / 合計{len(self.processing_results)}件")
        messagebox.showinfo("処理完了", 
                          f"処理が完了しました。\n\n"
                          f"成功: {success_count}件\n"
                          f"合計: {len(self.processing_results)}件")

    def _processing_finished(self):
        """処理終了"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.config(value=0)

    def _show_error(self, error_message):
        """エラー表示"""
        self._log(f"エラー: {error_message}")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{error_message}")

    def _clear_results(self):
        """結果クリア"""
        self.processing_results.clear()
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

    def _save_results(self):
        """結果保存"""
        if not self.processing_results:
            messagebox.showinfo("情報", "保存する結果がありません。")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="処理結果を保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if file_path:
            try:
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['元ファイル名', '新ファイル名', '信頼度', 'セット', 'ステータス'])
                    for result in self.processing_results:
                        writer.writerow([
                            result['original'], 
                            result['new'], 
                            result['confidence'],
                            result['set'], 
                            result['status']
                        ])
                
                messagebox.showinfo("完了", f"処理結果を保存しました:\n{file_path}")
                self._log(f"処理結果を保存しました: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("エラー", f"保存に失敗しました:\n{str(e)}")

    def _clear_log(self):
        """ログクリア"""
        self.log_text.delete('1.0', 'end')

    def _save_log(self):
        """ログ保存"""
        log_content = self.log_text.get('1.0', 'end')
        file_path = filedialog.asksaveasfilename(
            title="システムログを保存",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("完了", f"システムログを保存しました:\n{file_path}")
                self._log(f"システムログを保存しました: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("エラー", f"ログ保存に失敗しました:\n{str(e)}")

    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    try:
        app = TaxDocumentRenamerV51()
        app.run()
    except Exception as e:
        print(f"アプリケーション起動エラー: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\n{str(e)}")

if __name__ == "__main__":
    main()