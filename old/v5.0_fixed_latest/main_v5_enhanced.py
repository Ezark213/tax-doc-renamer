#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 強化版メインアプリケーション
セットベース連番システム + 完全UI + ドラッグ&ドロップ対応
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pathlib import Path
from typing import List, Dict, Optional
import sys

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 既存のモジュールを使用
from core.pdf_processor import PDFProcessor
from core.ocr_engine import OCREngine
from core.csv_processor import CSVProcessor
from core.classification_v5_fixed import DocumentClassifierV5Fixed, ValidationAlert
from ui.drag_drop import DropZoneFrame

class TaxDocumentRenamerV5Enhanced:
    """税務書類リネームシステム v5.0 強化版メインクラス"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.0 強化版 (完全機能)")
        self.root.geometry("1300x900")
        
        # コアエンジンの初期化
        self.pdf_processor = PDFProcessor()
        self.ocr_engine = OCREngine()
        self.csv_processor = CSVProcessor()
        self.classifier_v5_fixed = DocumentClassifierV5Fixed(debug_mode=True, log_callback=self._log)
        
        # UI変数
        self.files_list = []
        self.processing = False
        self.processing_results = []
        self.validation_alerts = []
        
        # 自治体セット設定
        self.municipality_sets_config = self._initialize_default_sets()
        
        # UI構築
        self._create_ui()

    def _initialize_default_sets(self) -> Dict:
        """デフォルト自治体セット設定"""
        return {
            1: {"prefecture": "東京都", "municipality": ""},
            2: {"prefecture": "愛知県", "municipality": "蒲郡市"},
            3: {"prefecture": "福岡県", "municipality": "福岡市"}
        }

    def _create_ui(self):
        """UIの構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="税務書類リネームシステム v5.0 強化版", 
            font=('Arial', 18, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # 機能説明
        info_label = ttk.Label(
            main_frame,
            text="セットベース連番・OCR突合チェック・完全ドラッグ&ドロップ対応",
            font=('Arial', 11),
            foreground='blue'
        )
        info_label.pack(pady=(0, 15))
        
        # ノートブック（タブ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # タブ1: ファイル選択・設定
        self.file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_frame, text="📁 ファイル・設定")
        self._create_file_tab()
        
        # タブ2: 処理結果・アラート
        self.result_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.result_frame, text="📊 結果・アラート")
        self._create_result_tab()
        
        # タブ3: ログ・デバッグ
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="🔧 ログ")
        self._create_log_tab()

    def _create_file_tab(self):
        """ファイル選択タブの作成"""
        # 全体を左右に分割
        main_paned = ttk.PanedWindow(self.file_frame, orient='horizontal')
        main_paned.pack(fill='both', expand=True)
        
        # 左側: ファイル選択エリア
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)
        
        # 右側: 設定エリア
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        # === 左側: ファイル選択エリア ===
        ttk.Label(left_frame, text="ファイル選択", font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # ドラッグ&ドロップゾーン
        self.drop_zone = DropZoneFrame(left_frame, self._on_files_dropped)
        self.drop_zone.pack(fill='both', expand=True, pady=(0, 10))
        
        # ファイル操作ボタン
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(button_frame, text="📁 ファイル追加", command=self._select_files).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="📂 フォルダ追加", command=self._select_folder).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🗑️ クリア", command=self._clear_files).pack(side='left', padx=5)
        
        # ファイルリスト表示
        ttk.Label(left_frame, text="選択されたファイル", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True)
        
        # ファイルリスト（Treeview使用で詳細表示）
        columns = ('ファイル名', 'サイズ', '種別')
        self.files_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.files_tree.heading(col, text=col)
            if col == 'ファイル名':
                self.files_tree.column(col, width=300)
            else:
                self.files_tree.column(col, width=80)
        
        files_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=files_scrollbar.set)
        
        self.files_tree.pack(side='left', fill='both', expand=True)
        files_scrollbar.pack(side='right', fill='y')
        
        # === 右側: 設定エリア ===
        ttk.Label(right_frame, text="設定", font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # 年月設定
        year_month_frame = ttk.LabelFrame(right_frame, text="年月設定")
        year_month_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(year_month_frame, text="手動入力年月 (YYMM):").pack(anchor='w', pady=(5, 0))
        self.year_month_var = tk.StringVar(value="2508")
        year_entry = ttk.Entry(year_month_frame, textvariable=self.year_month_var, width=10, font=('Arial', 10))
        year_entry.pack(anchor='w', pady=(2, 10))
        
        # 自治体セット設定
        sets_frame = ttk.LabelFrame(right_frame, text="自治体セット設定")
        sets_frame.pack(fill='x', pady=(0, 10))
        
        self._create_municipality_sets_ui(sets_frame)
        
        # 処理オプション
        options_frame = ttk.LabelFrame(right_frame, text="処理オプション")
        options_frame.pack(fill='x', pady=(0, 10))
        
        self.set_based_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="セットベース連番モード", 
            variable=self.set_based_var,
            command=self._on_set_mode_change
        ).pack(anchor='w', pady=2)
        
        self.ocr_check_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="OCR突合チェック", 
            variable=self.ocr_check_var
        ).pack(anchor='w', pady=2)
        
        self.alert_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="アラート機能", 
            variable=self.alert_enabled_var
        ).pack(anchor='w', pady=2)
        
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="デバッグモード", 
            variable=self.debug_mode_var
        ).pack(anchor='w', pady=2)
        
        # 処理ボタン
        process_frame = ttk.Frame(right_frame)
        process_frame.pack(fill='x', pady=(20, 0))
        
        # メイン処理ボタン
        self.process_button = ttk.Button(
            process_frame,
            text="🚀 リネーム処理実行",
            command=self._start_processing,
            style='Accent.TButton'
        )
        self.process_button.pack(fill='x', pady=(0, 10))
        
        # プログレスバー
        self.progress = ttk.Progressbar(process_frame, mode='determinate')
        self.progress.pack(fill='x', pady=(0, 5))
        
        # ステータス表示
        self.status_var = tk.StringVar(value="待機中")
        status_label = ttk.Label(process_frame, textvariable=self.status_var, font=('Arial', 9))
        status_label.pack()

    def _create_municipality_sets_ui(self, parent):
        """自治体セット設定UIの作成"""
        # ヘッダー
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(5, 10))
        
        ttk.Label(header_frame, text="セット", width=6, font=('Arial', 9, 'bold')).pack(side='left')
        ttk.Label(header_frame, text="都道府県", width=10, font=('Arial', 9, 'bold')).pack(side='left', padx=(5, 0))
        ttk.Label(header_frame, text="市町村", width=10, font=('Arial', 9, 'bold')).pack(side='left', padx=(5, 0))
        
        # 自治体選択肢
        prefecture_options = [
            "東京都", "愛知県", "福岡県", "大阪府", "神奈川県", "埼玉県", "千葉県", "北海道", 
            "宮城県", "静岡県", "広島県", "鹿児島県"
        ]
        
        municipality_options = {
            "東京都": [""],
            "愛知県": ["蒲郡市", "名古屋市", "豊田市", "岡崎市"],
            "福岡県": ["福岡市", "北九州市", "久留米市"],
            "大阪府": ["大阪市", "堺市", "東大阪市"],
            "神奈川県": ["横浜市", "川崎市", "相模原市"],
            "埼玉県": ["さいたま市", "川越市", "越谷市"],
            "千葉県": ["千葉市", "船橋市", "柏市"],
            "北海道": ["札幌市", "函館市", "旭川市"],
            "宮城県": ["仙台市", "石巻市", "大崎市"],
            "静岡県": ["静岡市", "浜松市", "沼津市"],
            "広島県": ["広島市", "福山市", "呉市"],
            "鹿児島県": ["鹿児島市", "霧島市", "薩摩川内市"]
        }
        
        self.set_vars = {}
        
        # セット1-3の設定
        for set_num in range(1, 4):
            set_frame = ttk.Frame(parent)
            set_frame.pack(fill='x', pady=2)
            
            ttk.Label(set_frame, text=f"セット{set_num}", width=6).pack(side='left')
            
            # 都道府県選択
            prefecture_var = tk.StringVar(value=self.municipality_sets_config[set_num]["prefecture"])
            prefecture_combo = ttk.Combobox(
                set_frame, 
                textvariable=prefecture_var, 
                values=prefecture_options,
                width=10,
                state='readonly'
            )
            prefecture_combo.pack(side='left', padx=(5, 0))
            
            # 市町村選択
            municipality_var = tk.StringVar(value=self.municipality_sets_config[set_num]["municipality"])
            municipality_combo = ttk.Combobox(
                set_frame, 
                textvariable=municipality_var,
                width=10,
                state='readonly'
            )
            municipality_combo.pack(side='left', padx=(5, 0))
            
            # 都道府県変更時に市町村選択肢を更新
            def update_municipalities(event, p_var=prefecture_var, m_var=municipality_var, m_combo=municipality_combo):
                selected_pref = p_var.get()
                if selected_pref in municipality_options:
                    m_combo['values'] = municipality_options[selected_pref]
                    if municipality_options[selected_pref]:
                        m_var.set(municipality_options[selected_pref][0])
                    else:
                        m_var.set("")
            
            prefecture_combo.bind('<<ComboboxSelected>>', update_municipalities)
            
            # 初期値設定
            if prefecture_var.get() in municipality_options:
                municipality_combo['values'] = municipality_options[prefecture_var.get()]
            
            self.set_vars[set_num] = {
                'prefecture': prefecture_var,
                'municipality': municipality_var
            }
        
        # セット設定の説明
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill='x', pady=(10, 5))
        
        info_text = tk.Text(info_frame, height=4, width=30, font=('Arial', 8), state='disabled')
        info_text.pack(fill='x')
        
        info_content = """連番ルール:
セット1(東京都): 1001, 1003, 1004
セット2(愛知県): 1011, 1013, 1014 + 2001, 2003, 2004  
セット3(福岡県): 1021, 1023, 1024 + 2011, 2013, 2014"""
        
        info_text.config(state='normal')
        info_text.insert('1.0', info_content)
        info_text.config(state='disabled')

    def _create_result_tab(self):
        """処理結果・アラートタブの作成"""
        # 上下分割
        result_paned = ttk.PanedWindow(self.result_frame, orient='vertical')
        result_paned.pack(fill='both', expand=True)
        
        # 上部: 処理結果
        result_upper = ttk.LabelFrame(result_paned, text="処理結果")
        result_paned.add(result_upper, weight=3)
        
        # 処理結果表示用のTreeview
        result_columns = ('元ファイル名', '新ファイル名', 'セット', '信頼度', 'ステータス')
        self.result_tree = ttk.Treeview(result_upper, columns=result_columns, show='headings')
        
        for col in result_columns:
            self.result_tree.heading(col, text=col)
            if col == '元ファイル名' or col == '新ファイル名':
                self.result_tree.column(col, width=200)
            else:
                self.result_tree.column(col, width=100)
        
        result_scrollbar = ttk.Scrollbar(result_upper, orient='vertical', command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_tree.pack(side='left', fill='both', expand=True)
        result_scrollbar.pack(side='right', fill='y')
        
        # 下部: アラート表示
        alert_lower = ttk.LabelFrame(result_paned, text="アラート・警告")
        result_paned.add(alert_lower, weight=2)
        
        self.alert_text = tk.Text(alert_lower, wrap='word', font=('Consolas', 9))
        alert_scrollbar = ttk.Scrollbar(alert_lower, orient='vertical', command=self.alert_text.yview)
        self.alert_text.configure(yscrollcommand=alert_scrollbar.set)
        
        self.alert_text.pack(side='left', fill='both', expand=True)
        alert_scrollbar.pack(side='right', fill='y')
        
        # 結果操作ボタン
        result_button_frame = ttk.Frame(result_upper)
        result_button_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Button(result_button_frame, text="📋 結果コピー", command=self._copy_results).pack(side='left', padx=(0, 5))
        ttk.Button(result_button_frame, text="💾 結果保存", command=self._save_results).pack(side='left', padx=5)
        ttk.Button(result_button_frame, text="🗑️ 結果クリア", command=self._clear_results).pack(side='left', padx=5)

    def _create_log_tab(self):
        """ログ・デバッグタブの作成"""
        log_frame = ttk.Frame(self.log_frame)
        log_frame.pack(fill='both', expand=True)
        
        ttk.Label(log_frame, text="システムログ", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # ログ表示エリア
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_text_frame, wrap='word', font=('Consolas', 9), bg='#f8f8f8')
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # ログ操作ボタン
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(log_button_frame, text="🗑️ ログクリア", command=self._clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(log_button_frame, text="💾 ログ保存", command=self._save_log).pack(side='left', padx=5)
        ttk.Button(log_button_frame, text="🔄 ログ更新", command=self._refresh_log).pack(side='left', padx=5)

    def _log(self, message: str):
        """ログメッセージの表示"""
        if hasattr(self, 'log_text'):
            self.log_text.insert('end', message + '\n')
            self.log_text.see('end')
            self.root.update_idletasks()

    def _on_set_mode_change(self):
        """セットモード変更時の処理"""
        if self.set_based_var.get():
            self._log("セットベース連番モードが有効になりました")
        else:
            self._log("セットベース連番モードが無効になりました")

    def _on_files_dropped(self, files):
        """ファイルドロップ時の処理"""
        added_count = 0
        for file_path in files:
            if file_path.lower().endswith('.pdf') and file_path not in self.files_list:
                self.files_list.append(file_path)
                added_count += 1
        
        if added_count > 0:
            self._update_files_display()
            self._log(f"ドラッグ&ドロップで {added_count} 個のファイルを追加しました")

    def _select_files(self):
        """ファイル選択ダイアログ"""
        files = filedialog.askopenfilenames(
            title="PDFファイルを選択",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if files:
            added_count = 0
            for file_path in files:
                if file_path not in self.files_list:
                    self.files_list.append(file_path)
                    added_count += 1
            
            self._update_files_display()
            self._log(f"{added_count} 個のファイルを追加しました")

    def _select_folder(self):
        """フォルダ選択ダイアログ"""
        folder = filedialog.askdirectory(title="PDFファイルが含まれるフォルダを選択")
        if folder:
            pdf_files = list(Path(folder).glob("*.pdf"))
            added_count = 0
            for file_path in pdf_files:
                file_str = str(file_path)
                if file_str not in self.files_list:
                    self.files_list.append(file_str)
                    added_count += 1
            
            self._update_files_display()
            self._log(f"フォルダから {added_count} 個のPDFファイルを追加しました")

    def _clear_files(self):
        """ファイルリストクリア"""
        self.files_list.clear()
        self._update_files_display()
        self._log("ファイルリストをクリアしました")

    def _update_files_display(self):
        """ファイル表示更新"""
        # Treeviewクリア
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # ファイル情報表示
        for file_path in self.files_list:
            file_name = os.path.basename(file_path)
            try:
                file_size = f"{os.path.getsize(file_path) / 1024:.1f} KB"
            except:
                file_size = "不明"
            
            file_type = "PDF" if file_path.lower().endswith('.pdf') else "その他"
            
            self.files_tree.insert('', 'end', values=(file_name, file_size, file_type))

    def _start_processing(self):
        """処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルがありません。")
            return
        
        if self.processing:
            messagebox.showinfo("情報", "既に処理中です。")
            return
        
        # UI無効化
        self.process_button.config(state='disabled')
        self.processing = True
        
        # 結果クリア
        self._clear_results()
        
        # 別スレッドで処理実行
        thread = threading.Thread(target=self._process_files)
        thread.daemon = True
        thread.start()

    def _process_files(self):
        """ファイル処理メイン"""
        try:
            total_files = len(self.files_list)
            self.progress.config(maximum=total_files)
            
            self.root.after(0, lambda: self.status_var.set("処理開始..."))
            
            for i, file_path in enumerate(self.files_list):
                self.root.after(0, lambda f=file_path: self.status_var.set(f"処理中: {os.path.basename(f)}"))
                
                # OCRテキスト抽出（ダミー実装）
                extracted_text = f"ダミーテキスト for {os.path.basename(file_path)}"
                
                # セットベース分類
                if self.set_based_var.get():
                    document_type, alerts = self.classifier_v5_fixed.classify_document_v5_fixed(
                        extracted_text, os.path.basename(file_path)
                    )
                else:
                    document_type = "0000_未分類"
                    alerts = []
                
                # 年月付与
                year_month = self.year_month_var.get()
                final_filename = f"{document_type}_{year_month}.pdf"
                
                # 結果記録
                result = {
                    'original': os.path.basename(file_path),
                    'new': final_filename,
                    'set': self._extract_set_from_alerts(alerts),
                    'confidence': self._calculate_confidence(alerts),
                    'status': self._determine_status(alerts),
                    'alerts': alerts
                }
                
                self.processing_results.append(result)
                
                # UIに結果表示
                self.root.after(0, self._update_result_display, result)
                
                # アラート処理
                if self.alert_enabled_var.get():
                    for alert in alerts:
                        if alert.alert_type != "SUCCESS":
                            self.root.after(0, self._show_alert, file_path, alert)
                
                # プログレス更新
                self.root.after(0, lambda val=i+1: self.progress.config(value=val))
            
            # 処理完了
            self.root.after(0, self._processing_complete)
            
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"処理エラー: {str(e)}"))
        finally:
            self.root.after(0, self._processing_finished)

    def _extract_set_from_alerts(self, alerts: List[ValidationAlert]) -> str:
        """アラートからセット情報抽出"""
        for alert in alerts:
            if "セット" in alert.message:
                import re
                match = re.search(r'セット(\d+)', alert.message)
                if match:
                    return f"セット{match.group(1)}"
        return "不明"

    def _calculate_confidence(self, alerts: List[ValidationAlert]) -> str:
        """信頼度計算"""
        if not alerts:
            return "0%"
        
        total_confidence = sum(alert.confidence for alert in alerts) / len(alerts)
        return f"{int(total_confidence * 100)}%"

    def _determine_status(self, alerts: List[ValidationAlert]) -> str:
        """ステータス判定"""
        has_mismatch = any(alert.alert_type == "MISMATCH" for alert in alerts)
        has_ambiguous = any(alert.alert_type == "AMBIGUOUS" for alert in alerts)
        
        if has_mismatch:
            return "要確認"
        elif has_ambiguous:
            return "曖昧"
        else:
            return "正常"

    def _update_result_display(self, result: dict):
        """結果表示更新"""
        self.result_tree.insert('', 'end', values=(
            result['original'],
            result['new'],
            result['set'],
            result['confidence'],
            result['status']
        ))

    def _show_alert(self, file_path: str, alert: ValidationAlert):
        """アラート表示"""
        alert_message = f"[{alert.alert_type}] {os.path.basename(file_path)}: {alert.message}\n"
        if alert.suggestions:
            alert_message += f"  提案: {', '.join(alert.suggestions)}\n"
        alert_message += "\n"
        
        self.alert_text.insert('end', alert_message)
        self.alert_text.see('end')

    def _processing_complete(self):
        """処理完了"""
        self.status_var.set("処理完了")
        self._log("全ファイルの処理が完了しました")
        messagebox.showinfo("完了", f"{len(self.processing_results)}件のファイル処理が完了しました。")

    def _processing_finished(self):
        """処理終了時のUI復旧"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.config(value=0)

    def _show_error(self, error_message: str):
        """エラー表示"""
        self._log(f"エラー: {error_message}")
        messagebox.showerror("エラー", error_message)

    def _clear_results(self):
        """結果クリア"""
        self.processing_results.clear()
        
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        self.alert_text.delete('1.0', 'end')

    def _copy_results(self):
        """結果をクリップボードにコピー"""
        if not self.processing_results:
            messagebox.showinfo("情報", "コピーする結果がありません。")
            return
        
        result_text = "元ファイル名\t新ファイル名\tセット\t信頼度\tステータス\n"
        for result in self.processing_results:
            result_text += f"{result['original']}\t{result['new']}\t{result['set']}\t{result['confidence']}\t{result['status']}\n"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(result_text)
        messagebox.showinfo("完了", "結果をクリップボードにコピーしました。")

    def _save_results(self):
        """結果保存"""
        if not self.processing_results:
            messagebox.showinfo("情報", "保存する結果がありません。")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="結果を保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    if file_path.endswith('.csv'):
                        import csv
                        writer = csv.writer(f)
                        writer.writerow(['元ファイル名', '新ファイル名', 'セット', '信頼度', 'ステータス'])
                        for result in self.processing_results:
                            writer.writerow([result['original'], result['new'], result['set'], 
                                           result['confidence'], result['status']])
                    else:
                        for result in self.processing_results:
                            f.write(f"{result['original']} -> {result['new']} ({result['status']})\n")
                
                messagebox.showinfo("完了", f"結果を保存しました: {file_path}")
                self._log(f"結果を保存: {file_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"保存に失敗しました: {str(e)}")

    def _clear_log(self):
        """ログクリア"""
        self.log_text.delete('1.0', 'end')

    def _save_log(self):
        """ログ保存"""
        log_content = self.log_text.get('1.0', 'end')
        file_path = filedialog.asksaveasfilename(
            title="ログ保存",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("完了", f"ログを保存しました: {file_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"ログ保存に失敗: {str(e)}")

    def _refresh_log(self):
        """ログ更新"""
        self._log("ログを更新しました")

    def run(self):
        """アプリケーション実行"""
        self._log("税務書類リネームシステム v5.0 強化版を起動しました")
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = TaxDocumentRenamerV5Enhanced()
        app.run()
    except Exception as e:
        print(f"アプリケーション起動エラー: {e}")
        input("Enterキーを押して終了...")