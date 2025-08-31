#!/usr/bin/env python3
"""
税務書類リネームシステム v4.0 メインアプリケーション
完全ゼロベース再構築版
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

from core.pdf_processor import PDFProcessor
from core.ocr_engine import OCREngine, MunicipalityMatcher, MunicipalitySet
from core.csv_processor import CSVProcessor
from core.classification import DocumentClassifier
from ui.drag_drop import DropZoneFrame

class TaxDocumentRenamerV4:
    """税務書類リネームシステム v4.0 メインクラス"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v4.0")
        self.root.geometry("1000x700")
        
        # コアエンジンの初期化
        self.pdf_processor = PDFProcessor()
        self.ocr_engine = OCREngine()
        self.csv_processor = CSVProcessor()
        self.classifier = DocumentClassifier(debug_mode=True, log_callback=self._log)
        
        # UI変数
        self.files_list = []
        self.split_processing = False
        self.rename_processing = False
        self.municipality_sets = []
        
        # UI構築
        self._create_ui()
        
        # 自治体セットのデフォルト設定
        self._setup_default_municipalities()

    def _create_ui(self):
        """UIの構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="税務書類リネームシステム v4.0", 
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # ノートブック（タブ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # タブ1: ファイル選択・設定
        self.file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_frame, text="📁 ファイル選択・設定")
        self._create_file_tab()
        
        # タブ2: 処理結果
        self.result_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.result_frame, text="📊 処理結果")
        self._create_result_tab()
        
        # タブ3: ログ・デバッグ
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="🔧 ログ・デバッグ")
        self._create_log_tab()

    def _create_file_tab(self):
        """ファイル選択タブの作成"""
        # 左右分割
        paned = ttk.PanedWindow(self.file_frame, orient='horizontal')
        paned.pack(fill='both', expand=True)
        
        # 左側: ファイル選択
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        # ドラッグ&ドロップゾーン
        ttk.Label(left_frame, text="ファイル選択", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        self.drop_zone = DropZoneFrame(left_frame, self._on_files_dropped)
        self.drop_zone.pack(fill='both', expand=True, pady=(0, 10))
        
        # ファイル操作ボタン
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(button_frame, text="📁 ファイル選択", command=self._select_files).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="📂 フォルダ選択", command=self._select_folder).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🗑️ クリア", command=self._clear_files).pack(side='left', padx=5)
        
        # ファイルリスト
        ttk.Label(left_frame, text="選択されたファイル").pack(anchor='w')
        
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True)
        
        self.files_listbox = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.files_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # 右側: 設定
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="設定", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # 年月設定
        year_month_frame = ttk.LabelFrame(right_frame, text="年月設定")
        year_month_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(year_month_frame, text="手動入力年月 (YYMM):").pack(anchor='w')
        self.year_month_var = tk.StringVar()
        ttk.Entry(year_month_frame, textvariable=self.year_month_var, width=10).pack(anchor='w', pady=5)
        
        # 自治体設定
        municipality_frame = ttk.LabelFrame(right_frame, text="自治体設定")
        municipality_frame.pack(fill='x', pady=(0, 10))
        
        # 東京都設定の注意メッセージ
        tokyo_notice_frame = ttk.Frame(municipality_frame)
        tokyo_notice_frame.pack(fill='x', pady=(5, 10))
        
        notice_label = ttk.Label(
            tokyo_notice_frame, 
            text="⚠️ 注意：東京都あての地方税申告書がある場合には、\n東京都はセット1に入力してください",
            foreground='red',
            font=('Arial', 9, 'bold'),
            justify='center'
        )
        notice_label.pack()
        
        self._create_municipality_settings(municipality_frame)
        
        # 処理オプション
        options_frame = ttk.LabelFrame(right_frame, text="処理オプション")
        options_frame.pack(fill='x', pady=(0, 10))
        
        self.auto_split_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="PDF自動分割", variable=self.auto_split_var).pack(anchor='w')
        
        self.ocr_enhanced_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="OCR強化モード", variable=self.ocr_enhanced_var).pack(anchor='w')
        
        # 処理ボタン（分割・リネーム独立化）
        process_frame = ttk.Frame(right_frame)
        process_frame.pack(fill='x', pady=20)
        
        # 分割実行ボタン
        self.split_button = ttk.Button(
            process_frame, 
            text="📄 分割実行", 
            command=self._start_split_processing,
            style='Accent.TButton'
        )
        self.split_button.pack(fill='x', pady=(0, 5))
        
        # リネーム実行ボタン
        self.rename_button = ttk.Button(
            process_frame, 
            text="✏️ リネーム実行", 
            command=self._start_rename_processing,
            style='Accent.TButton'
        )
        self.rename_button.pack(fill='x')
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            process_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.pack(fill='x', pady=(10, 0))
        
        # ステータス
        self.status_var = tk.StringVar(value="待機中")
        ttk.Label(process_frame, textvariable=self.status_var).pack(pady=(5, 0))

    def _create_municipality_settings(self, parent):
        """自治体設定UIの作成"""
        self.municipality_vars = []
        self.municipality_entries = []
        
        # ヘッダー
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(header_frame, text="セット", width=8).pack(side='left')
        ttk.Label(header_frame, text="都道府県", width=10).pack(side='left')
        ttk.Label(header_frame, text="市町村", width=12).pack(side='left')
        
        for i in range(5):
            set_frame = ttk.Frame(parent)
            set_frame.pack(fill='x', pady=2)
            
            ttk.Label(set_frame, text=f"セット{i+1}:", width=8).pack(side='left')
            
            prefecture_var = tk.StringVar()
            municipality_var = tk.StringVar()
            
            prefecture_entry = ttk.Entry(set_frame, textvariable=prefecture_var, width=10)
            prefecture_entry.pack(side='left', padx=(0, 2))
            
            municipality_entry = ttk.Entry(set_frame, textvariable=municipality_var, width=12)
            municipality_entry.pack(side='left')
            
            # 東京都入力時の市町村欄制御
            prefecture_var.trace('w', lambda *args, idx=i: self._on_prefecture_changed(idx))
            
            self.municipality_vars.append((prefecture_var, municipality_var))
            self.municipality_entries.append((prefecture_entry, municipality_entry))
    
    def _on_prefecture_changed(self, set_index: int):
        """都道府県入力変更時の処理"""
        prefecture_var, municipality_var = self.municipality_vars[set_index]
        prefecture_entry, municipality_entry = self.municipality_entries[set_index]
        
        prefecture = prefecture_var.get().strip()
        
        # 東京都が入力された場合の処理
        if "東京" in prefecture:
            # 市町村欄をクリアして無効化
            municipality_var.set("")
            municipality_entry.configure(state='disabled')
        else:
            # 東京都以外の場合は市町村欄を有効化
            municipality_entry.configure(state='normal')
    
    def _validate_municipality_settings(self) -> bool:
        """自治体設定の妥当性チェック"""
        tokyo_sets = []
        
        # 東京都が入力されているセットを検索
        for i, (prefecture_var, municipality_var) in enumerate(self.municipality_vars):
            prefecture = prefecture_var.get().strip()
            if "東京" in prefecture and prefecture != "":
                tokyo_sets.append(i + 1)  # セット番号（1から開始）
        
        # 東京都がセット1以外にある場合はエラー
        if tokyo_sets and 1 not in tokyo_sets:
            error_msg = f"エラー: 東京都はセット1に入力してください。\n現在の東京都の位置: セット{tokyo_sets[0]}"
            messagebox.showerror("設定エラー", error_msg)
            return False
        
        # 東京都が複数のセットにある場合はエラー
        if len(tokyo_sets) > 1:
            error_msg = f"エラー: 東京都は1つのセットにのみ入力してください。\n現在の東京都の位置: セット{', セット'.join(map(str, tokyo_sets))}"
            messagebox.showerror("設定エラー", error_msg)
            return False
        
        return True

    def _create_result_tab(self):
        """処理結果タブの作成"""
        # 結果表示用のTreeview
        ttk.Label(self.result_frame, text="処理結果", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Treeviewとスクロールバー
        tree_frame = ttk.Frame(self.result_frame)
        tree_frame.pack(fill='both', expand=True)
        
        columns = ('元ファイル名', '新ファイル名', '分類', '状態', '詳細')
        self.result_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col in columns:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=150)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.result_tree.pack(side='left', fill='both', expand=True)
        tree_scrollbar.pack(side='right', fill='y')
        
        # 結果操作ボタン
        result_button_frame = ttk.Frame(self.result_frame)
        result_button_frame.pack(fill='x', pady=10)
        
        ttk.Button(result_button_frame, text="📁 出力フォルダを開く", command=self._open_output_folder).pack(side='left', padx=(0, 5))
        ttk.Button(result_button_frame, text="📄 結果をエクスポート", command=self._export_results).pack(side='left', padx=5)
        ttk.Button(result_button_frame, text="🔄 結果をクリア", command=self._clear_results).pack(side='left', padx=5)

    def _create_log_tab(self):
        """ログタブの作成"""
        ttk.Label(self.log_frame, text="処理ログ・デバッグ情報", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # ログ表示エリア
        log_text_frame = ttk.Frame(self.log_frame)
        log_text_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_text_frame, wrap='word', font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # ログ操作ボタン
        log_button_frame = ttk.Frame(self.log_frame)
        log_button_frame.pack(fill='x', pady=10)
        
        ttk.Button(log_button_frame, text="🗑️ ログクリア", command=self._clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(log_button_frame, text="💾 ログ保存", command=self._save_log).pack(side='left', padx=5)

    def _setup_default_municipalities(self):
        """デフォルト自治体設定"""
        defaults = [
            ("東京都", ""),
            ("愛知県", "蒲郡市"),
            ("大阪府", "大阪市"),
            ("", ""),
            ("", "")
        ]
        
        for i, (prefecture, municipality) in enumerate(defaults):
            if i < len(self.municipality_vars):
                self.municipality_vars[i][0].set(prefecture)
                self.municipality_vars[i][1].set(municipality)
                
                # 東京都の場合は市町村欄を無効化
                if "東京" in prefecture:
                    self.municipality_entries[i][1].configure(state='disabled')

    def _on_files_dropped(self, files: List[str]):
        """ファイルドロップ時の処理"""
        for file_path in files:
            if file_path not in self.files_list:
                self.files_list.append(file_path)
                self.files_listbox.insert(tk.END, os.path.basename(file_path))
        
        self._log(f"ファイル追加: {len(files)}件")

    def _select_files(self):
        """ファイル選択ダイアログ"""
        filetypes = [
            ('対応ファイル', '*.pdf;*.csv'),
            ('PDFファイル', '*.pdf'),
            ('CSVファイル', '*.csv'),
            ('すべてのファイル', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="処理するファイルを選択",
            filetypes=filetypes
        )
        
        if files:
            self._on_files_dropped(list(files))

    def _select_folder(self):
        """フォルダ選択"""
        folder = filedialog.askdirectory(title="フォルダを選択")
        if folder:
            files = []
            for ext in ['.pdf', '.csv']:
                files.extend(Path(folder).glob(f"*{ext}"))
            
            if files:
                self._on_files_dropped([str(f) for f in files])
            else:
                messagebox.showinfo("情報", "対応ファイル（PDF・CSV）が見つかりませんでした")

    def _clear_files(self):
        """ファイルリストクリア"""
        self.files_list.clear()
        self.files_listbox.delete(0, tk.END)
        self._log("ファイルリストをクリアしました")

    def _start_split_processing(self):
        """分割処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.split_processing or self.rename_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 自治体設定の妥当性チェック
        if not self._validate_municipality_settings():
            return
        
        # 出力フォルダ選択
        output_folder = filedialog.askdirectory(title="分割ファイルの出力フォルダを選択")
        if not output_folder:
            return
        
        # バックグラウンド処理開始
        self.split_processing = True
        self._update_button_states()
        
        thread = threading.Thread(
            target=self._split_files_background,
            args=(output_folder,),
            daemon=True
        )
        thread.start()
    
    def _start_rename_processing(self):
        """リネーム処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.split_processing or self.rename_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 自治体設定の妥当性チェック
        if not self._validate_municipality_settings():
            return
        
        # 自治体セットを取得
        self.municipality_sets = self._get_municipality_sets()
        
        # 出力フォルダ選択
        output_folder = filedialog.askdirectory(title="リネーム済みファイルの出力フォルダを選択")
        if not output_folder:
            return
        
        # バックグラウンド処理開始
        self.rename_processing = True
        self._update_button_states()
        
        thread = threading.Thread(
            target=self._rename_files_background,
            args=(output_folder,),
            daemon=True
        )
        thread.start()

    def _get_municipality_sets(self) -> List[MunicipalitySet]:
        """自治体設定を取得"""
        sets = []
        for i, (pref_var, muni_var) in enumerate(self.municipality_vars):
            pref = pref_var.get().strip()
            muni = muni_var.get().strip()
            
            if pref:  # 都道府県が入力されている場合のみ
                sets.append(MunicipalitySet(i + 1, pref, muni))
        
        return sets

    def _split_files_background(self, output_folder: str):
        """分割処理のバックグラウンド処理"""
        try:
            total_files = len(self.files_list)
            split_count = 0
            
            for i, file_path in enumerate(self.files_list):
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda f=os.path.basename(file_path): self.status_var.set(f"分割処理中: {f}"))
                
                try:
                    if self._is_split_target(file_path):
                        split_results = self._split_single_file(file_path, output_folder)
                        split_count += len(split_results)
                        
                        for result in split_results:
                            self.root.after(0, lambda r=result: self._add_result_success(
                                file_path, os.path.basename(r), "分割完了"
                            ))
                    else:
                        self._log(f"分割対象外: {os.path.basename(file_path)}")
                        
                except Exception as e:
                    self._log(f"分割エラー: {file_path} - {str(e)}")
                    self.root.after(0, lambda f=file_path, e=str(e): self._add_result_error(f, f"分割エラー: {e}"))
            
            # 処理完了
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda c=split_count: self.status_var.set(f"分割完了: {c}ページ処理"))
            
        except Exception as e:
            self._log(f"分割処理エラー: {str(e)}")
        finally:
            self.root.after(0, self._split_processing_finished)
    
    def _rename_files_background(self, output_folder: str):
        """リネーム処理のバックグラウンド処理"""
        try:
            total_files = len(self.files_list)
            
            for i, file_path in enumerate(self.files_list):
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda f=os.path.basename(file_path): self.status_var.set(f"リネーム処理中: {f}"))
                
                try:
                    self._process_single_file(file_path, output_folder)
                except Exception as e:
                    self._log(f"リネームエラー: {file_path} - {str(e)}")
                    self.root.after(0, lambda f=file_path, e=str(e): self._add_result_error(f, f"リネームエラー: {e}"))
            
            # 処理完了
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set(f"リネーム完了: {total_files}件処理"))
            
        except Exception as e:
            self._log(f"リネーム処理エラー: {str(e)}")
        finally:
            self.root.after(0, self._rename_processing_finished)

    def _process_single_file(self, file_path: str, output_folder: str):
        """単一ファイルの処理"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        self._log(f"処理開始: {filename}")
        
        if ext == '.pdf':
            self._process_pdf_file(file_path, output_folder)
        elif ext == '.csv':
            self._process_csv_file(file_path, output_folder)
        else:
            raise ValueError(f"未対応ファイル形式: {ext}")

    def _process_pdf_file(self, file_path: str, output_folder: str):
        """PDFファイルの処理"""
        filename = os.path.basename(file_path)
        
        # PDF分割チェック
        if self.auto_split_var.get():
            # 国税受信通知チェック
            if self.pdf_processor.is_national_tax_notification_bundle(file_path):
                self._log(f"国税受信通知一式として分割: {filename}")
                year_month = self.year_month_var.get() or "YYMM"
                split_results = self.pdf_processor.split_national_tax_notifications(
                    file_path, output_folder, year_month
                )
                
                for result in split_results:
                    if result.success:
                        self.root.after(0, lambda r=result: self._add_result_success(file_path, r.filename, "国税分割"))
                    else:
                        self.root.after(0, lambda r=result: self._add_result_error(file_path, r.error_message))
                return
            
            # 地方税受信通知チェック
            if self.pdf_processor.is_local_tax_notification_bundle(file_path):
                self._log(f"地方税受信通知一式として分割: {filename}")
                year_month = self.year_month_var.get() or "YYMM"
                split_results = self.pdf_processor.split_local_tax_notifications(
                    file_path, output_folder, year_month
                )
                
                for result in split_results:
                    if result.success:
                        self.root.after(0, lambda r=result: self._add_result_success(file_path, r.filename, "地方税分割"))
                    else:
                        self.root.after(0, lambda r=result: self._add_result_error(file_path, r.error_message))
                return
        
        # 通常のPDF処理
        self._process_regular_pdf(file_path, output_folder)

    def _process_regular_pdf(self, file_path: str, output_folder: str):
        """通常PDFの処理"""
        filename = os.path.basename(file_path)
        
        # OCR・テキスト抽出
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            self._log(f"PDF読み取りエラー: {e}")
            text = ""
        
        # 自治体認識
        prefecture_code = None
        municipality_code = None
        
        if self.ocr_enhanced_var.get() and self.municipality_sets:
            matcher = MunicipalityMatcher(self.municipality_sets)
            match_result = matcher.get_best_match(file_path)
            prefecture_code = match_result['prefecture_code']
            municipality_code = match_result['municipality_code']
            
            self._log(f"自治体認識: 都道府県={prefecture_code}, 市町村={municipality_code}")
        else:
            # 自治体設定がない場合でも都道府県申告書を判定するため、
            # デフォルトでセット2のコード（1011）を使用して特別判定を有効化
            if self.municipality_sets and len(self.municipality_sets) >= 2:
                prefecture_code = 1011  # セット2
            elif self.municipality_sets and len(self.municipality_sets) >= 1:
                prefecture_code = 1011  # セット2デフォルト
        
        # 自治体設定を辞書形式に変換
        municipality_settings = {}
        if self.municipality_sets:
            for i, municipality_set in enumerate(self.municipality_sets, 1):
                municipality_settings[f"set{i}"] = {
                    "prefecture": municipality_set.prefecture,
                    "municipality": municipality_set.municipality
                }
        
        # 書類分類（詳細ログ付き）
        classification_result = self.classifier.classify_with_municipality_info(
            text, filename, municipality_settings, file_path
        )
        
        # 分類詳細ログを出力
        self._log(f"分類結果詳細:")
        self._log(f"  - 書類種別: {classification_result.document_type}")
        self._log(f"  - 信頼度: {classification_result.confidence:.2f}")
        self._log(f"  - マッチキーワード: {classification_result.matched_keywords}")
        
        # デバッグステップ情報
        if hasattr(classification_result, 'debug_steps') and classification_result.debug_steps:
            self._log("全分類候補のスコア:")
            sorted_steps = sorted(classification_result.debug_steps, key=lambda x: x.score, reverse=True)
            for i, step in enumerate(sorted_steps[:5]):  # 上位5位まで表示
                status = "除外" if step.excluded else f"{step.score:.1f}点"
                self._log(f"  {i+1}位: {step.document_type} - {status}")
                if step.matched_keywords:
                    self._log(f"       キーワード: {step.matched_keywords}")
                if step.exclude_reason:
                    self._log(f"       除外理由: {step.exclude_reason}")
        
        # 年月決定
        year_month = self.year_month_var.get() or self._extract_year_month_from_pdf(text, filename)
        
        # 新ファイル名生成
        new_filename = self._generate_filename(classification_result.document_type, year_month, "pdf")
        
        # ファイルコピー
        import shutil
        output_path = os.path.join(output_folder, new_filename)
        shutil.copy2(file_path, output_path)
        
        self._log(f"完了: {filename} -> {new_filename}")
        self.root.after(0, lambda: self._add_result_success(file_path, new_filename, classification_result.document_type))

    def _process_csv_file(self, file_path: str, output_folder: str):
        """CSVファイルの処理"""
        filename = os.path.basename(file_path)
        
        # CSV処理
        result = self.csv_processor.process_csv(file_path)
        
        if not result.success:
            raise ValueError(result.error_message)
        
        # 年月決定（手動入力優先）
        year_month = self.year_month_var.get() or result.year_month
        
        # 新ファイル名生成
        new_filename = self.csv_processor.generate_csv_filename(result)
        if year_month != "YYMM":
            # 年月を手動入力で上書き
            base_name = os.path.splitext(new_filename)[0]
            ext = os.path.splitext(new_filename)[1]
            parts = base_name.split('_')
            if len(parts) >= 3:
                parts[-1] = year_month
                new_filename = '_'.join(parts) + ext
        
        # ファイルコピー
        import shutil
        output_path = os.path.join(output_folder, new_filename)
        shutil.copy2(file_path, output_path)
        
        self._log(f"CSV完了: {filename} -> {new_filename}")
        self.root.after(0, lambda: self._add_result_success(file_path, new_filename, result.document_type))

    def _extract_year_month_from_pdf(self, text: str, filename: str) -> str:
        """PDFから年月を抽出"""
        import re
        
        # 簡単な年月抽出ロジック
        patterns = [
            r'(\d{2})(\d{2})',  # YYMM
            r'(\d{4})(\d{2})',  # YYYYMM
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename + text)
            if match:
                year = match.group(1)
                month = match.group(2)
                if len(year) == 4:
                    year = year[2:]
                return f"{year}{month}"
        
        return "YYMM"

    def _generate_filename(self, doc_type: str, year_month: str, ext: str) -> str:
        """ファイル名生成"""
        return f"{doc_type}_{year_month}.{ext}"
    
    def _is_split_target(self, file_path: str) -> bool:
        """分割対象ファイルか判定"""
        try:
            # PDFファイルのみ対象
            if not file_path.lower().endswith('.pdf'):
                return False
            
            # ファイルのテキストを抽出
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            # 分割対象キーワードの定義
            split_keywords = [
                # 分割対象1: 申告受付関連書類
                "申告受付完了通知",
                "納付情報発行結果",
                # 分割対象2: メール詳細関連書類
                "メール詳細",
                "納付区分番号通知"
            ]
            
            # キーワードマッチング
            for keyword in split_keywords:
                if keyword in text:
                    self._log(f"分割対象検出: {os.path.basename(file_path)} - キーワード: {keyword}")
                    return True
            
            return False
            
        except Exception as e:
            self._log(f"分割対象判定エラー: {file_path} - {str(e)}")
            return False
    
    def _is_empty_page(self, doc, page_num: int) -> bool:
        """ページが空かどうかを判定"""
        try:
            page = doc[page_num]
            
            # テキスト抽出による判定
            text_content = page.get_text().strip()
            if len(text_content) > 10:  # 10文字以上のテキストがある場合は有効ページ
                return False
            
            # 画像・図形の有無による判定
            image_list = page.get_images()
            if len(image_list) > 0:  # 画像がある場合は有効ページ
                return False
            
            # 描画オブジェクトの有無による判定
            drawings = page.get_drawings()
            if len(drawings) > 0:  # 描画がある場合は有効ページ
                return False
            
            # フォントリストによる判定（テキストが少なくてもフォント情報があれば有効）
            fonts = page.get_fonts()
            if len(fonts) > 1:  # 基本フォント以外がある場合は有効ページ
                return False
            
            # 複数の条件で空ページと判断
            if len(text_content) <= 2 and len(image_list) == 0 and len(drawings) == 0:
                return True
            
            return False
            
        except Exception as e:
            self._log(f"空ページ判定エラー - ページ{page_num + 1}: {str(e)}")
            # エラーの場合は安全のため有効ページとして扱う
            return False
    
    def _split_single_file(self, file_path: str, output_folder: str) -> List[str]:
        """単一ファイルのページ分割（空ページ除外機能付き）"""
        split_files = []
        
        try:
            import fitz
            doc = fitz.open(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            self._log(f"分割開始: {os.path.basename(file_path)} ({doc.page_count}ページ)")
            
            empty_pages = []
            valid_pages = []
            
            for page_num in range(doc.page_count):
                # 空ページチェック
                if self._is_empty_page(doc, page_num):
                    empty_pages.append(page_num + 1)
                    self._log(f"空ページ検出 - ページ{page_num + 1}: スキップします")
                    continue
                
                valid_pages.append(page_num)
                
                # 各ページを個別PDFとして保存
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                # 出力ファイル名生成
                output_filename = f"{base_name}_ページ{page_num + 1:03d}.pdf"
                output_path = os.path.join(output_folder, output_filename)
                
                # 重複ファイル名の対応
                output_path = self._generate_unique_filename(output_path)
                
                # PDF保存
                new_doc.save(output_path)
                new_doc.close()
                
                split_files.append(output_path)
                self._log(f"ページ{page_num + 1}分割完了: {os.path.basename(output_path)}")
            
            doc.close()
            
            # 結果ログ
            if empty_pages:
                self._log(f"空ページ除外: {len(empty_pages)}ページ ({empty_pages})")
            self._log(f"分割完了: {len(split_files)}ページ生成（有効ページ: {len(valid_pages)}）")
            
        except Exception as e:
            self._log(f"分割エラー: {file_path} - {str(e)}")
            raise
        
        return split_files
    
    def _generate_unique_filename(self, filepath: str) -> str:
        """重複しないファイル名を生成"""
        if not os.path.exists(filepath):
            return filepath
        
        dir_name = os.path.dirname(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        ext = os.path.splitext(filepath)[1]
        
        counter = 1
        while True:
            new_filename = f"{base_name}_{counter:03d}{ext}"
            new_filepath = os.path.join(dir_name, new_filename)
            if not os.path.exists(new_filepath):
                return new_filepath
            counter += 1

    def _split_processing_finished(self):
        """分割処理完了時の処理"""
        self.split_processing = False
        self._update_button_states()
        self.notebook.select(1)  # 結果タブに切り替え
        messagebox.showinfo("完了", "分割処理が完了しました")
    
    def _rename_processing_finished(self):
        """リネーム処理完了時の処理"""
        self.rename_processing = False
        self._update_button_states()
        self.notebook.select(1)  # 結果タブに切り替え
        messagebox.showinfo("完了", "リネーム処理が完了しました")
    
    def _update_button_states(self):
        """ボタンの状態を更新"""
        if self.split_processing:
            self.split_button.config(state='disabled', text="分割処理中...")
            self.rename_button.config(state='disabled')
        elif self.rename_processing:
            self.split_button.config(state='disabled')
            self.rename_button.config(state='disabled', text="リネーム処理中...")
        else:
            # 両方とも処理中でない場合
            self.split_button.config(state='normal', text="📄 分割実行")
            self.rename_button.config(state='normal', text="✏️ リネーム実行")

    def _add_result_success(self, original_file: str, new_filename: str, doc_type: str):
        """成功結果を追加"""
        self.result_tree.insert('', 'end', values=(
            os.path.basename(original_file),
            new_filename,
            doc_type,
            "✅ 成功",
            "正常に処理されました"
        ))

    def _add_result_error(self, original_file: str, error: str):
        """エラー結果を追加"""
        self.result_tree.insert('', 'end', values=(
            os.path.basename(original_file),
            "-",
            "-",
            "❌ エラー",
            error
        ))

    def _open_output_folder(self):
        """出力フォルダを開く"""
        # 実装省略
        pass

    def _export_results(self):
        """結果をエクスポート"""
        # 実装省略
        pass

    def _clear_results(self):
        """結果をクリア"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

    def _log(self, message: str):
        """ログメッセージ追加"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.root.after(0, lambda: self.log_text.insert(tk.END, log_entry))
        self.root.after(0, lambda: self.log_text.see(tk.END))

    def _clear_log(self):
        """ログクリア"""
        self.log_text.delete(1.0, tk.END)

    def _save_log(self):
        """ログ保存"""
        # 実装省略
        pass

    def run(self):
        """アプリケーション実行"""
        self._log("税務書類リネームシステム v4.0 起動")
        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV4()
    app.run()