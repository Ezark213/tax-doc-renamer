#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 メインアプリケーション
AND条件対応・高精度判定システム（完全改訂版）
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pathlib import Path
from typing import List, Dict, Optional
import sys
import pytesseract

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pdf_processor import PDFProcessor
from core.ocr_engine import OCREngine, MunicipalityMatcher, MunicipalitySet
from core.csv_processor import CSVProcessor
from core.classification_v5 import DocumentClassifierV5  # v5.1バグ修正版エンジンを使用
from core.runtime_paths import get_tesseract_executable_path, get_tessdata_dir_path, validate_tesseract_resources
from ui.drag_drop import DropZoneFrame


def _init_tesseract():
    """同梱Tesseractの初期化"""
    try:
        # 同梱tesseract.exe と tessdata を優先使用
        tesseract_bin = get_tesseract_executable_path()
        tessdata_dir = get_tessdata_dir_path()
        
        # リソースが存在するかチェック
        if not validate_tesseract_resources():
            # プレースホルダーファイルが存在する場合はヒント表示
            import glob
            placeholder_files = glob.glob(os.path.join(tessdata_dir, "*.placeholder"))
            if placeholder_files:
                raise RuntimeError(
                    "Tesseractリソースファイルが配置されていません。\n\n"
                    f"以下の手順でファイルを配置してください：\n"
                    f"1. tesseract.exe を {os.path.dirname(tesseract_bin)}/ に配置\n"
                    f"2. jpn.traineddata を {tessdata_dir}/ に配置\n"
                    f"3. eng.traineddata を {tessdata_dir}/ に配置\n\n"
                    f"詳細は resources/tesseract/README.md を参照してください。"
                )
            else:
                raise RuntimeError(f"同梱Tesseractリソースが見つかりません:\n{tesseract_bin}")
        
        # Tesseractの設定
        os.environ["TESSDATA_PREFIX"] = tessdata_dir
        pytesseract.pytesseract.tesseract_cmd = tesseract_bin
        
        # 動作テスト
        try:
            # 簡単なOCRテストを実行
            pytesseract.get_tesseract_version()
            print(f"[OK] 同梱Tesseract初期化成功: {tesseract_bin}")
        except Exception as e:
            raise RuntimeError(f"同梱Tesseractの動作テストに失敗: {e}")
            
    except Exception as e:
        print(f"[WARNING] 同梱Tesseract初期化エラー: {e}")
        print("システムにインストールされたTesseractを探します...")
        
        # システムのTesseractにフォールバック
        import shutil
        system_tesseract = shutil.which("tesseract")
        if system_tesseract:
            print(f"[OK] システムTesseractを使用: {system_tesseract}")
            pytesseract.pytesseract.tesseract_cmd = system_tesseract
        else:
            print("[ERROR] Tesseractが見つかりません。")
            print("")
            print("以下のいずれかを実行してください:")
            print("1. 同梱Tesseractリソースを正しく配置")
            print("2. システムにTesseractをインストール")
            print("")
            print("詳細は resources/tesseract/README.md を参照してください。")
            raise RuntimeError("Tesseractが利用できません。")


# アプリ起動時に1回だけ初期化（エラー時は警告のみ）
try:
    _init_tesseract()
except RuntimeError as e:
    print(f"[WARNING] Tesseract初期化をスキップ: {e}")
    print("[INFO] OCR機能は制限されますが、システムは起動します")


class TaxDocumentRenamerV5:
    """税務書類リネームシステム v5.0 メインクラス"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.1 (バグ修正版)")
        self.root.geometry("1000x700")
        
        # v5.0 コアエンジンの初期化
        self.pdf_processor = PDFProcessor()
        self.ocr_engine = OCREngine()
        self.csv_processor = CSVProcessor()
        self.classifier_v5 = DocumentClassifierV5(debug_mode=True)
        
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
            text="税務書類リネームシステム v5.1 (バグ修正版)", 
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # v5.0 新機能の説明
        info_label = ttk.Label(
            main_frame,
            text="✨ v5.1バグ修正: 地方税受信通知連番・添付資料分類・市民税識別強化",
            font=('Arial', 10),
            foreground='blue'
        )
        info_label.pack(pady=(0, 10))
        
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
        self.year_month_var = tk.StringVar(value="2508")  # デフォルト値設定
        ttk.Entry(year_month_frame, textvariable=self.year_month_var, width=10).pack(anchor='w', pady=5)
        
        # 自治体設定
        municipality_frame = ttk.LabelFrame(right_frame, text="自治体設定")
        municipality_frame.pack(fill='x', pady=(0, 10))
        
        self._create_municipality_settings(municipality_frame)
        
        # 処理オプション
        options_frame = ttk.LabelFrame(right_frame, text="処理オプション")
        options_frame.pack(fill='x', pady=(0, 10))
        
        self.auto_split_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="PDF自動分割", variable=self.auto_split_var).pack(anchor='w')
        
        self.ocr_enhanced_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="OCR強化モード", variable=self.ocr_enhanced_var).pack(anchor='w')
        
        # v5.0 専用オプション
        self.v5_mode_var = tk.BooleanVar(value=True)
        v5_checkbox = ttk.Checkbutton(
            options_frame, 
            text="v5.0 AND条件判定モード（推奨）", 
            variable=self.v5_mode_var
        )
        v5_checkbox.pack(anchor='w')
        
        # v5.0 モードの説明
        v5_info = ttk.Label(
            options_frame,
            text="※AND条件で受信通知・納付情報を高精度判定",
            font=('Arial', 8),
            foreground='gray'
        )
        v5_info.pack(anchor='w', padx=20)
        
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
        
        # リネーム実行ボタン（v5.0対応）
        self.rename_button = ttk.Button(
            process_frame, 
            text="✏️ リネーム実行 (v5.0)", 
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
        self.status_var = tk.StringVar(value="待機中 (v5.0モード)")
        ttk.Label(process_frame, textvariable=self.status_var).pack(pady=(5, 0))

    def _create_municipality_settings(self, parent):
        """自治体設定UIの作成"""
        self.municipality_vars = []
        
        for i in range(5):
            set_frame = ttk.Frame(parent)
            set_frame.pack(fill='x', pady=2)
            
            ttk.Label(set_frame, text=f"セット{i+1}:", width=8).pack(side='left')
            
            prefecture_var = tk.StringVar()
            municipality_var = tk.StringVar()
            
            ttk.Entry(set_frame, textvariable=prefecture_var, width=8).pack(side='left', padx=(0, 2))
            ttk.Entry(set_frame, textvariable=municipality_var, width=12).pack(side='left')
            
            self.municipality_vars.append((prefecture_var, municipality_var))

    def _create_result_tab(self):
        """処理結果タブの作成"""
        # 結果表示用のTreeview
        ttk.Label(self.result_frame, text="処理結果", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Treeviewとスクロールバー
        tree_frame = ttk.Frame(self.result_frame)
        tree_frame.pack(fill='both', expand=True)
        
        columns = ('元ファイル名', '新ファイル名', '分類', '判定方法', '信頼度', '状態')
        self.result_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col in columns:
            self.result_tree.heading(col, text=col)
            if col == '判定方法':
                self.result_tree.column(col, width=200)
            elif col == '信頼度':
                self.result_tree.column(col, width=80)
            else:
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
        ttk.Label(self.log_frame, text="処理ログ・デバッグ情報 (v5.0)", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
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
            ("福岡県", "福岡市"),
            ("", ""),
            ("", "")
        ]
        
        for i, (prefecture, municipality) in enumerate(defaults):
            if i < len(self.municipality_vars):
                self.municipality_vars[i][0].set(prefecture)
                self.municipality_vars[i][1].set(municipality)

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
        """v5.0 リネーム処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.split_processing or self.rename_processing:
            messagebox.showwarning("警告", "処理中です")
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
        
        # v5.0モードの確認
        use_v5_mode = self.v5_mode_var.get()
        self._log(f"リネーム処理開始: v5.0モード={'有効' if use_v5_mode else '無効'}")
        
        thread = threading.Thread(
            target=self._rename_files_background_v5,
            args=(output_folder, use_v5_mode),
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
                                file_path, os.path.basename(r), "分割完了", "ページ分割", "1.00"
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

    def _rename_files_background_v5(self, output_folder: str, use_v5_mode: bool):
        """v5.0 リネーム処理のバックグラウンド処理"""
        try:
            total_files = len(self.files_list)
            
            for i, file_path in enumerate(self.files_list):
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda f=os.path.basename(file_path): self.status_var.set(f"v5.0処理中: {f}"))
                
                try:
                    if use_v5_mode:
                        self._process_single_file_v5(file_path, output_folder)
                    else:
                        self._process_single_file_legacy(file_path, output_folder)
                except Exception as e:
                    self._log(f"リネームエラー: {file_path} - {str(e)}")
                    self.root.after(0, lambda f=file_path, e=str(e): self._add_result_error(f, f"リネームエラー: {e}"))
            
            # 処理完了
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set(f"v5.0リネーム完了: {total_files}件処理"))
            
        except Exception as e:
            self._log(f"v5.0リネーム処理エラー: {str(e)}")
        finally:
            self.root.after(0, self._rename_processing_finished)

    def _process_single_file_v5(self, file_path: str, output_folder: str):
        """v5.0 単一ファイルの処理"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        self._log(f"v5.0処理開始: {filename}")
        
        if ext == '.pdf':
            self._process_pdf_file_v5(file_path, output_folder)
        elif ext == '.csv':
            self._process_csv_file(file_path, output_folder)  # CSVは従来通り
        else:
            raise ValueError(f"未対応ファイル形式: {ext}")

    def _process_pdf_file_v5(self, file_path: str, output_folder: str):
        """v5.0 PDFファイルの処理"""
        filename = os.path.basename(file_path)
        
        # PDF自動分割チェック（従来と同じ）
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
                        self.root.after(0, lambda r=result: self._add_result_success(
                            file_path, r.filename, "国税分割", "自動分割", "1.00"
                        ))
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
                        self.root.after(0, lambda r=result: self._add_result_success(
                            file_path, r.filename, "地方税分割", "自動分割", "1.00"
                        ))
                    else:
                        self.root.after(0, lambda r=result: self._add_result_error(file_path, r.error_message))
                return
        
        # v5.0 通常PDF処理
        self._process_regular_pdf_v5(file_path, output_folder)

    def _process_regular_pdf_v5(self, file_path: str, output_folder: str):
        """v5.0 通常PDFの処理"""
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
        
        # v5.0 書類分類（AND条件対応 + セット連番適用）
        # 修正: 自治体情報を考慮した分類を使用して、実際の自治体名をファイル名に反映
        classification_result = self.classifier_v5.classify_with_municipality_info_v5(text, filename)
        document_type = classification_result.document_type if classification_result else "9999_未分類"
        alerts = []  # v5.1では単純化
        
        # classification_resultは既に取得済み
        
        # 分類詳細ログを出力（v5.1版）- デバッグ情報強化
        if classification_result:
            self._log(f"v5.1分類結果:")
            self._log(f"  - 書類種別: {classification_result.document_type}")
            self._log(f"  - 信頼度: {classification_result.confidence:.2f}")
            self._log(f"  - 判定方法: {classification_result.classification_method}")
            
            # 判定キーワードの詳細表示
            if classification_result.matched_keywords:
                keywords_str = ", ".join(classification_result.matched_keywords)
                self._log(f"  - 判定キーワード: [{keywords_str}]")
            
            # 処理ログからデバッグ情報を抽出して表示
            for log_entry in classification_result.processing_log:
                if any(keyword in log_entry for keyword in ["判定", "条件", "マッチ", "強制"]):
                    self._log(f"  🔍 {log_entry}")
        else:
            self._log("分類に失敗しました")
        
        # 年月決定
        year_month = self.year_month_var.get() or self._extract_year_month_from_pdf(text, filename)
        
        # 新ファイル名生成
        new_filename = self._generate_filename(classification_result.document_type, year_month, "pdf")
        
        # ファイルコピー
        import shutil
        output_path = os.path.join(output_folder, new_filename)
        shutil.copy2(file_path, output_path)
        
        self._log(f"v5.0完了: {filename} -> {new_filename}")
        
        # 結果追加（判定方法と信頼度を含む）- デバッグ情報追加
        method_display = self._get_method_display(classification_result.classification_method)
        confidence_display = f"{classification_result.confidence:.2f}"
        
        # 判定キーワードも表示に含める
        if classification_result.matched_keywords:
            keywords_summary = ", ".join(classification_result.matched_keywords[:3])  # 最初の3個まで
            if len(classification_result.matched_keywords) > 3:
                keywords_summary += "..."
            method_display += f" | キーワード: [{keywords_summary}]"
        
        self.root.after(0, lambda: self._add_result_success(
            file_path, new_filename, classification_result.document_type, 
            method_display, confidence_display
        ))

    def _process_single_file_legacy(self, file_path: str, output_folder: str):
        """従来版 単一ファイルの処理（互換性のため）"""
        # 従来のclassification.pyを使用した処理
        # 実装は従来のmain.pyのロジックを使用
        self._log(f"従来モード処理: {os.path.basename(file_path)}")
        # ここに従来の処理ロジックを実装...

    def _process_csv_file(self, file_path: str, output_folder: str):
        """CSVファイルの処理（従来と同じ）"""
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
        self.root.after(0, lambda: self._add_result_success(
            file_path, new_filename, result.document_type, "CSV判定", "1.00"
        ))

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

    def _get_method_display(self, method: str) -> str:
        """判定方法の表示用文字列を取得"""
        method_map = {
            "highest_priority_and_condition": "最優先AND条件",
            "standard_keyword_matching": "標準キーワード判定",
            "default_fallback": "デフォルト分類"
        }
        return method_map.get(method, method)

    def _is_split_target(self, file_path: str) -> bool:
        """分割対象ファイルか判定（従来と同じ）"""
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

    def _split_single_file(self, file_path: str, output_folder: str) -> List[str]:
        """単一ファイルのページ分割（従来と同じ）"""
        split_files = []
        
        try:
            import fitz
            doc = fitz.open(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            self._log(f"分割開始: {os.path.basename(file_path)} ({doc.page_count}ページ)")
            
            for page_num in range(doc.page_count):
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
            self._log(f"分割完了: {len(split_files)}ページ生成")
            
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
        messagebox.showinfo("完了", "v5.0リネーム処理が完了しました")

    def _update_button_states(self):
        """ボタンの状態を更新"""
        if self.split_processing:
            self.split_button.config(state='disabled', text="分割処理中...")
            self.rename_button.config(state='disabled')
        elif self.rename_processing:
            self.split_button.config(state='disabled')
            self.rename_button.config(state='disabled', text="v5.0処理中...")
        else:
            # 両方とも処理中でない場合
            self.split_button.config(state='normal', text="📄 分割実行")
            self.rename_button.config(state='normal', text="✏️ リネーム実行 (v5.0)")

    def _add_result_success(self, original_file: str, new_filename: str, doc_type: str, method: str, confidence: str):
        """成功結果を追加（v5.0拡張版）"""
        self.result_tree.insert('', 'end', values=(
            os.path.basename(original_file),
            new_filename,
            doc_type,
            method,
            confidence,
            "✅ 成功"
        ))

    def _add_result_error(self, original_file: str, error: str):
        """エラー結果を追加"""
        self.result_tree.insert('', 'end', values=(
            os.path.basename(original_file),
            "-",
            "-",
            "-",
            "0.00",
            f"❌ エラー: {error}"
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
        self._log("税務書類リネームシステム v5.0 起動 (AND条件対応版)")
        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV5()
    app.run()