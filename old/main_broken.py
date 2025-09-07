#!/usr/bin/env python3
"""Function description"""

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
from helpers.yymm_policy import resolve_yymm_by_policy, log_yymm_decision, validate_policy_result
from helpers.settings_context import UIContext, create_ui_context_from_gui, normalize_settings_input
from helpers.run_config import RunConfig, create_run_config_from_gui
from helpers.job_context import JobContext, create_job_context_from_gui
from core.csv_processor import CSVProcessor
from core.classification_v5 import DocumentClassifierV5  # v5.1バグ修正版エンジンを使用
from core.runtime_paths import get_tesseract_executable_path, get_tessdata_dir_path, validate_tesseract_resources
from ui.drag_drop import DropZoneFrame, AutoSplitControlFrame
# v5.3: Deterministic renaming system
from core.pre_extract import create_pre_extract_engine
from core.rename_engine import create_rename_engine
from core.models import DocItemID, PreExtractSnapshot


def _init_tesseract():
    """Function description"""
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
                    "Tesseractリソースファイルが配置されていません \n\n"
                    f"以下の手順でファイルを配置してください\n"
                    f"1. tesseract.exe を {os.path.dirname(tesseract_bin)}/ に配置\n"
                    f"2. jpn.traineddata を {tessdata_dir}/ に配置\n"
                    f"3. eng.traineddata を {tessdata_dir}/ に配置\n\n"
                    f"詳細は resources/tesseract/README.md を参照してください "
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
            print("[ERROR] Tesseractが見つかりません ")
            print("")
            print("以下のいずれかを実行してください:")
            print("1. 同梱Tesseractリソースを正しく配置")
            print("2. システムにTesseractをインストール")
            print("")
            print("詳細は resources/tesseract/README.md を参照してください ")
            raise RuntimeError("Tesseractが利用できません ")


# アプリ起動時に1回だけ初期化エラー時は警告のみ
try:
    _init_tesseract()
except RuntimeError as e:
    print(f"[WARNING] Tesseract初期化をスキップ: {e}")
    print("[INFO] OCR機能は制限されますが システムは起動します")


class TaxDocumentRenamerV5:
    """Function description"""
    
    def __init__(self):
        """Function description"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.2 (Bundle PDF Auto-Split)")
        self.root.geometry("1200x800")
        
        # v5.2 コアエンジンの初期化ロガー付き
        import logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.pdf_processor = PDFProcessor(logger=self.logger)
        self.ocr_engine = OCREngine()
        self.csv_processor = CSVProcessor()
        self.classifier_v5 = DocumentClassifierV5(debug_mode=True)
        
        # v5.3: Deterministic renaming system
        snapshots_dir = Path("./snapshots")
        snapshots_dir.mkdir(exist_ok=True)
        self.pre_extract_engine = create_pre_extract_engine(logger=self.logger, snapshot_dir=snapshots_dir)
        self.rename_engine = create_rename_engine(logger=self.logger)
        
        # UI変数
        self.files_list = []
        self.split_processing = False
        self.rename_processing = False
        self.auto_split_processing = False  # v5.2 new
        self.municipality_sets = {}
        
        # v5.2 Auto-Split settings
        self.auto_split_settings = {'auto_split_bundles': True, 'debug_mode': False}
        
        # RunConfig for UI YYMM centralization
        self.run_config = None  # 一括処理時に作成
        
        # UI構築
        self._create_ui()
        
        # 自治体セットのデフォルト設定
        self._setup_default_municipalities()
    
    def _validate_yymm_input(self, *args):
        """Function description"""
        try:
            from helpers.yymm_policy import _normalize_yymm, _validate_yymm
            
            current_value = self.year_month_var.get()
            if not current_value:
                self.yymm_status_var.set("  YYMM入力待ち")
                self.yymm_status_label.config(foreground='gray')
                return
            
            # 正規化を試行
            normalized = _normalize_yymm(current_value)
            if normalized and _validate_yymm(normalized):
                self.yymm_status_var.set(f"  正常: {current_value}   {normalized} (UI強制対応)")
                self.yymm_status_label.config(foreground='green')
                
                # UI強制コードへの対応状況も表示
                forced_codes = ["6001", "6002", "6003", "0000"]
                self.yymm_status_var.set(f"  正常: {current_value}   {normalized} | UI強制対応({', '.join(forced_codes)})")
            else:
                self.yymm_status_var.set(f"   無効: {current_value} (例: 2508, 25/08,     )")
                self.yymm_status_label.config(foreground='red')
                
        except Exception as e:
            self.yymm_status_var.set(f"  エラー: {str(e)}")
            self.yymm_status_label.config(foreground='red')

    def _create_ui(self):
        """Function description"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="税務書類リネームシステム v5.2", 
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 5))
        
        # v5.2 新機能の説明
        info_label = ttk.Label(
            main_frame,
            text="  v5.2 New: Bundle PDF Auto-Split |   v5.1バグ修正完了版",
            font=('Arial', 10),
            foreground='blue'
        )
        info_label.pack(pady=(0, 10))
        
        # ノートブックタブ
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # タブ1: ファイル選択 設定
        self.file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_frame, text="  ファイル選択 設定")
        self._create_file_tab()
        
        # タブ2: 処理結果
        self.result_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.result_frame, text="  処理結果")
        self._create_result_tab()
        
        # タブ3: ログ デバッグ
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="  ログ デバッグ")
        self._create_log_tab()

    def _create_file_tab(self):
        """Function description"""
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
        
        ttk.Button(button_frame, text="  ファイル選択", command=self._select_files).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="  フォルダ選択", command=self._select_folder).pack(side='left', padx=5)
        ttk.Button(button_frame, text="   クリア", command=self._clear_files).pack(side='left', padx=5)
        
        # ファイルリスト
        ttk.Label(left_frame, text="選択されたファイル").pack(anchor='w')
        
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True)
        
        self.files_listbox = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.files_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # 右側: 設定 + Auto-Split控制
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="設定 Auto-Split", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # v5.2 Auto-Split控制フレーム
        self.auto_split_control = AutoSplitControlFrame(right_frame)
        self.auto_split_control.pack(fill='x', pady=(0, 10))
        
        # コールバック設定
        self.auto_split_control.set_callbacks(
            batch_callback=self._start_batch_processing,
            split_callback=self._start_split_only_processing,
            force_callback=self._start_force_split_processing
        )
        
        # 年月設定
        year_month_frame = ttk.LabelFrame(right_frame, text="年月設定")
        year_month_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(year_month_frame, text="手動入力年月 (YYMM):").pack(anchor='w')
        self.year_month_var = tk.StringVar(value="2508")  # デフォルト値設定
        yymm_entry = ttk.Entry(year_month_frame, textvariable=self.year_month_var, width=10)
        yymm_entry.pack(anchor='w', pady=5)
        
        # YYMM設定状態表示
        self.yymm_status_var = tk.StringVar()
        self.yymm_status_label = ttk.Label(year_month_frame, textvariable=self.yymm_status_var, 
                                          font=('Arial', 8), foreground='blue')
        self.yymm_status_label.pack(anchor='w', pady=(0, 5))
        
        # YYMMバリデーション設定リアルタイム更新
        self.year_month_var.trace_add('write', self._validate_yymm_input)
        self._validate_yymm_input()  # 初期バリデーション
        
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
        
        # v5.3 専用オプション
        self.v5_mode_var = tk.BooleanVar(value=True)
        v5_checkbox = ttk.Checkbutton(
            options_frame, 
            text="v5.3 YYMM Policy System AND条件判定モード推奨", 
            variable=self.v5_mode_var
        )
        v5_checkbox.pack(anchor='w')
        
        # v5.3 モードの説明
        v5_info = ttk.Label(
            options_frame,
            text=" AND条件で受信通知 納付情報を高精度判定",
            font=('Arial', 8),
            foreground='gray'
        )
        v5_info.pack(anchor='w', padx=20)
        
        # エクスポート設定
        export_frame = ttk.LabelFrame(right_frame, text="エクスポート設定")
        export_frame.pack(fill='x', pady=(0, 10))
        
        # キーワード辞書エクスポートボタン
        ttk.Button(
            export_frame,
            text="  キーワード辞書をエクスポート",
            command=self._export_keyword_dictionary
        ).pack(anchor='w', pady=5)
        
        export_info = ttk.Label(
            export_frame,
            text=" 分類ルール辞書をJSONファイルでデスクトップに保存",
            font=('Arial', 8),
            foreground='gray'
        )
        export_info.pack(anchor='w', padx=20)
        
        # 処理ボタン分割 リネーム独立化
        process_frame = ttk.Frame(right_frame)
        process_frame.pack(fill='x', pady=20)
        
        # 分割実行ボタン
        self.split_button = ttk.Button(
            process_frame, 
            text="  分割実行", 
            command=self._start_split_processing,
            style='Accent.TButton'
        )
        self.split_button.pack(fill='x', pady=(0, 5))
        
        # リネーム実行ボタンv5.3対応
        self.rename_button = ttk.Button(
            process_frame, 
            text="   リネーム実行 (v5.3)", 
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
        self.status_var = tk.StringVar(value="待機中 (v5.3モード)")
        ttk.Label(process_frame, textvariable=self.status_var).pack(pady=(5, 0))

    def _create_municipality_settings(self, parent):
        """Function description"""
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
        """Function description"""
        # 結果表示用のTreeview
        ttk.Label(self.result_frame, text="処理結果", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Treeviewとスクロールバー
        tree_frame = ttk.Frame(self.result_frame)
        tree_frame.pack(fill='both', expand=True)
        
        columns = ('元ファイル名', '新ファイル名', '分類', '判定方法', '信頼度', 'マッチしたキーワード', '状態')
        self.result_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        for col in columns:
            self.result_tree.heading(col, text=col)
            if col == '判定方法':
                self.result_tree.column(col, width=150)
            elif col == '信頼度':
                self.result_tree.column(col, width=80)
            elif col == 'マッチしたキーワード':
                self.result_tree.column(col, width=200)
            else:
                self.result_tree.column(col, width=130)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.result_tree.pack(side='left', fill='both', expand=True)
        tree_scrollbar.pack(side='right', fill='y')
        
        # 結果操作ボタン
        result_button_frame = ttk.Frame(self.result_frame)
        result_button_frame.pack(fill='x', pady=10)
        
        ttk.Button(result_button_frame, text="  出力フォルダを開く", command=self._open_output_folder).pack(side='left', padx=(0, 5))
        ttk.Button(result_button_frame, text="  結果をエクスポート", command=self._export_results).pack(side='left', padx=5)
        ttk.Button(result_button_frame, text="  結果をクリア", command=self._clear_results).pack(side='left', padx=5)

    def _create_log_tab(self):
        """Function description"""
        ttk.Label(self.log_frame, text="処理ログ デバッグ情報 (v5.3)", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
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
        
        ttk.Button(log_button_frame, text="   ログクリア", command=self._clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(log_button_frame, text="  ログ保存", command=self._save_log).pack(side='left', padx=5)

    def _create_municipality_settings(self, parent_frame):
        """Function description"""
        # セット1-5のStringVar変数を初期化
        for i in range(1, 6):
            setattr(self, f'prefecture_var_{i}', tk.StringVar())
            setattr(self, f'city_var_{i}', tk.StringVar())
        
        # UI作成
        for i in range(1, 6):
            set_frame = ttk.Frame(parent_frame)
            set_frame.pack(fill='x', pady=2)
            
            ttk.Label(set_frame, text=f"セット{i}:", width=8).pack(side='left')
            
            prefecture_var = getattr(self, f'prefecture_var_{i}')
            city_var = getattr(self, f'city_var_{i}')
            
            ttk.Entry(set_frame, textvariable=prefecture_var, width=12).pack(side='left', padx=2)
            ttk.Entry(set_frame, textvariable=city_var, width=12).pack(side='left', padx=2)

    def _setup_default_municipalities(self):
        """Function description"""
        defaults = [
            ("東京都", ""),
            ("愛知県", "蒲郡市"),
            ("福岡県", "福岡市"),
            ("", ""),
            ("", "")
        ]
        
        for i, (prefecture, city) in enumerate(defaults, 1):
            if i <= 5:
                prefecture_var = getattr(self, f'prefecture_var_{i}', None)
                city_var = getattr(self, f'city_var_{i}', None)
                if prefecture_var and city_var:
                    prefecture_var.set(prefecture)
                    city_var.set(city)

    # Commented out old method since we have the new v5.2 version above
    # def _on_files_dropped(self, files: List[str]):

    def _select_files(self):
        """Function description"""
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
        """Function description"""
        folder = filedialog.askdirectory(title="フォルダを選択")
        if folder:
            files = []
            for ext in ['.pdf', '.csv']:
                files.extend(Path(folder).glob(f"*{ext}"))
            
            if files:
                self._on_files_dropped([str(f) for f in files])
            else:
                messagebox.showinfo("情報", "対応ファイルPDF CSVが見つかりませんでした")

    def _clear_files(self):
        """Function description"""
        self.files_list.clear()
        self.files_listbox.delete(0, tk.END)
        self._log("ファイルリストをクリアしました")

    def _start_split_processing(self):
        """Function description"""
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
        """Function description"""
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
        
        # v5.3モードの確認
        use_v5_mode = self.v5_mode_var.get()
        self._log(f"リネーム処理開始: v5.3モード={'有効' if use_v5_mode else '無効'}")
        
        thread = threading.Thread(
            target=self._rename_files_background_v5,
            args=(output_folder, use_v5_mode),
            daemon=True
        )
        thread.start()

    # ===== v5.2 Auto-Split Processing Methods =====
    
    def _start_batch_processing(self):
        """Function description"""
        # v5.3.4 Split reset logging
        self._log(f"[reset] __split_ 一括処理開始 - 処理状態リセット")
        
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.auto_split_processing or self.rename_processing or self.split_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 出力フォルダ選択
        output_folder = filedialog.askdirectory(title="処理済みファイルの出力フォルダを選択")
        if not output_folder:
            return
        
        # RunConfig作成一括処理用
        try:
            gui_yymm = self.year_month_var.get()
            self.run_config = create_run_config_from_gui(
                yymm_var_value=gui_yymm,
                batch_mode=True,
                debug_mode=self.auto_split_control.get_settings().get('debug_mode', False)
            )
            self.run_config.log_config()
            
            # UI必須コードの事前チェックUI強制コード検証
            self._pre_validate_ui_forced_codes()
            self._log(f"[RUN_CONFIG] Batch processing started with manual_yymm={self.run_config.manual_yymm}")
            
        except Exception as e:
            self.logger.error(f"[RUN_CONFIG] Failed to create RunConfig: {e}")
            messagebox.showerror("設定エラー", f"YYMM設定エラー: {e}")
            return
        
        # 設定取得
        self.auto_split_settings = self.auto_split_control.get_settings()
        
        # バックグラウンド処理開始
        self.auto_split_processing = True
        self._update_auto_split_button_states()
        
        thread = threading.Thread(
            target=self._batch_processing_background,
            args=(output_folder,),
            daemon=True
        )
        thread.start()
    
    def _start_split_only_processing(self):
        """Function description"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.auto_split_processing or self.rename_processing or self.split_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 出力フォルダ選択
        output_folder = filedialog.askdirectory(title="分割ファイルの出力フォルダを選択")
        if not output_folder:
            return
        
        # 設定取得
        self.auto_split_settings = self.auto_split_control.get_settings()
        
        # バックグラウンド処理開始
        self.auto_split_processing = True
        self._update_auto_split_button_states()
        
        thread = threading.Thread(
            target=self._split_only_processing_background,
            args=(output_folder,),
            daemon=True
        )
        thread.start()
    
    def _start_force_split_processing(self):
        """Function description"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.auto_split_processing or self.rename_processing or self.split_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 確認ダイアログ
        result = messagebox.askyesno(
            "強制分割の確認",
            "選択したすべてのPDFファイルを強制的に1ページごとに分割しますか \n\n"
            "  束ね判定に関係なく分割されます "
        )
        if not result:
            return
        
        # 出力フォルダ選択
        output_folder = filedialog.askdirectory(title="強制分割ファイルの出力フォルダを選択")
        if not output_folder:
            return
        
        # 設定取得
        self.auto_split_settings = self.auto_split_control.get_settings()
        
        # バックグラウンド処理開始
        self.auto_split_processing = True
        self._update_auto_split_button_states()
        
        thread = threading.Thread(
            target=self._force_split_processing_background,
            args=(output_folder,),
            daemon=True
        )
        thread.start()
    
    def _batch_processing_background(self, output_folder: str):
        """Function description"""
        try:
            total_files = len(self.files_list)
            processed_count = 0
            split_count = 0
            
            self.root.after(0, lambda: self.auto_split_control.update_progress("一括処理開始...", "blue"))
            
            for i, file_path in enumerate(self.files_list):
                progress = (i / total_files) * 100
                filename = os.path.basename(file_path)
                
                self.root.after(0, lambda f=filename: self.auto_split_control.update_progress(
                    f"処理中: {f} ({i+1}/{total_files})", "blue"
                ))
                
                try:
                    if file_path.lower().endswith('.pdf'):
                        # v5.3: 決定論的独立化パイプライン
                        # Step 1: Pre-Extract スナップショット生成分割前
                        self._log(f"[v5.3] Pre-Extract スナップショット生成中: {filename}")
                        
                        # UI設定を構築して伝搬
                        gui_yymm = self.year_month_var.get()
                        ui_context = create_ui_context_from_gui(
                            yymm_var_value=gui_yymm,
                            municipality_sets=getattr(self, 'municipality_sets', {}),
                            batch_mode=True,
                            allow_auto_forced_codes=getattr(self, 'allow_auto_forced_codes', False),
                            file_path=file_path
                        )
                        
                        user_yymm = self._resolve_yymm_with_policy(file_path, None)  # ポリシーシステム使用
                        snapshot = self.pre_extract_engine.build_snapshot(file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
                        
                        # Step 2: Bundle検出グローバル除外対応
                        # Step 3: 分割実行 or 単一処理
                        def processing_callback(temp_path, page_num, bundle_type, doc_item_id: Optional[DocItemID] = None):
                            # v5.3.5: JobContext統合での決定論的リネーム
                            gui_yymm = self.year_month_var.get()
                            job_context = create_job_context_from_gui(
                                yymm_var_value=gui_yymm,
                                output_directory=output_folder,
                                batch_mode=True,
                                debug_mode=getattr(self, 'debug_mode', False)
                            )
                            self._process_single_file_v5_with_snapshot(temp_path, output_folder, snapshot, doc_item_id, job_context)
                        
                        was_split = self.pdf_processor.maybe_split_pdf(
                            file_path, output_folder, force=False, processing_callback=processing_callback
                        )
                        
                        if was_split:
                            split_count += 1
                            self._log(f"[v5.3] Bundle分割完了: {filename}")
                        else:
                            # Step 4: 単一ファイル処理JobContext統合
                            gui_yymm = self.year_month_var.get()
                            job_context = create_job_context_from_gui(
                                yymm_var_value=gui_yymm,
                                output_directory=output_folder,
                                batch_mode=True,
                                debug_mode=getattr(self, 'debug_mode', False)
                            )
                            self._process_single_file_v5_with_snapshot(file_path, output_folder, snapshot, None, job_context)
                            self._log(f"[v5.3] 単一ファイル処理完了: {filename}")
                    
                    else:
                        # Process non-PDF files normally
                        self._process_single_file_v5(file_path, output_folder)
                    
                    processed_count += 1
                    
                except Exception as e:
                    self._log(f"Processing error: {filename} - {str(e)}")
                    self.root.after(0, lambda f=filename, e=str(e): self._add_result_error(
                        f, f"処理エラー: {e}"
                    ))
            
            # 処理完了
            self.root.after(0, lambda: self.auto_split_control.update_progress(
                f"一括処理完了: {processed_count}件処理 (分割: {split_count}件)", "green"
            ))
            
        except Exception as e:
            self._log(f"Batch processing error: {str(e)}")
            self.root.after(0, lambda: self.auto_split_control.update_progress(
                f"処理エラー: {str(e)}", "red"
            ))
        finally:
            # 層D誤分割された6002/6003をレスキューロールバック
            self._rescue_if_assets_split(output_folder)
            self.root.after(0, self._auto_split_processing_finished)
    
    def _rescue_if_assets_split(self, output_folder: str):
        """Function description"""
        import os
        
        # v5.3 hotfix: デフォルトで救済機能を無効化
        RESCUE_ENABLED = bool(int(os.getenv("RESCUE_ENABLED", "0")))
        
        if not RESCUE_ENABLED:
            self._log("[6002/6003 Lock D] rescue disabled by default")
            return
        
        try:
            from PyPDF2 import PdfWriter
            
            self._log("[6002/6003 Lock D] Rescue operation started")
            asset_files = []
            
            # 出力フォルダー内の全PDFファイルをチェック
            for pdf_file in Path(output_folder).glob("*.pdf"):
                if pdf_file.name.startswith("__split_"):  # 分割ファイルをスキップ
                    continue
                
                try:
                    # 各ファイルを分類して6002/6003かチェック
                    classifier = DocumentClassifierV5(debug_mode=False)
                    
                    # OCRでテキスト抽出
                    from core.ocr_engine import OCREngine
                    ocr = OCREngine()
                    text = ocr.extract_text_from_pdf(str(pdf_file))
                    
                    # 分類実行
                    result = classifier.classify_document_v5(text, pdf_file.name)
                    
                    # 6002/6003の場合 資産文書リストに追加
                    if result.document_type.startswith(('6002_', '6003_')):
                        asset_files.append((pdf_file, result.document_type))
                        self._log(f"[6002/6003 Lock D] Asset document found: {pdf_file.name} -> {result.document_type}")
                    
                except Exception as e:
                    self._log(f"[6002/6003 Lock D] File check error: {pdf_file.name} - {e}")
                    continue
            
            # 同一元ファイルからの資産文書をグループ化してマージ
            if asset_files:
                self._log(f"[6002/6003 Lock D] Found {len(asset_files)} asset files to rescue")
                
                # ファイル名から元ファイルを推定してグループ化
                asset_groups = {}
                for pdf_file, doc_type in asset_files:
                    # ファイル名から基本部分を抽出YYMM部分を除去
                    base_name = pdf_file.stem
                    if '_' in base_name:
                        parts = base_name.split('_')
                        if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) == 4:  # YYMM部分を除去
                            estimated_source = '_'.join(parts[:-1])
                        else:
                            estimated_source = base_name
                    else:
                        estimated_source = base_name
                    
                    if estimated_source not in asset_groups:
                        asset_groups[estimated_source] = []
                    asset_groups[estimated_source].append((pdf_file, doc_type))
                
                # 各グループをマージして警告
                for source_name, files_group in asset_groups.items():
                    if len(files_group) > 1:
                        self._log(f"[6002/6003 Lock D] WARNING: Multiple asset files from same source detected: {source_name}")
                        for pdf_file, doc_type in files_group:
                            self._log(f"[6002/6003 Lock D]   - {pdf_file.name} ({doc_type})")
                        self._log(f"[6002/6003 Lock D] These files should NOT have been split!")
                    else:
                        pdf_file, doc_type = files_group[0]
                        self._log(f"[6002/6003 Lock D] Single asset file: {pdf_file.name} ({doc_type}) - OK")
            else:
                self._log("[6002/6003 Lock D] No asset documents found in output")
            
        except Exception as e:
            self._log(f"[6002/6003 Lock D] Rescue operation error: {e}")
    
    def _split_only_processing_background(self, output_folder: str):
        """Function description"""
        try:
            total_files = len(self.files_list)
            split_count = 0
            
            self.root.after(0, lambda: self.auto_split_control.update_progress("分割のみ処理開始...", "blue"))
            
            for i, file_path in enumerate(self.files_list):
                progress = (i / total_files) * 100
                filename = os.path.basename(file_path)
                
                self.root.after(0, lambda f=filename: self.auto_split_control.update_progress(
                    f"分割判定中: {f} ({i+1}/{total_files})", "blue"
                ))
                
                try:
                    if file_path.lower().endswith('.pdf'):
                        # RunConfig/YYMM伝搬用コールバック定義Bundle分割経路でも確実に伝搬
                        def processing_callback(temp_path, page_num, bundle_type, doc_item_id: Optional[DocItemID] = None):
                            # JobContext生成Bundle分割経路でも確実にYYMM伝搬
                            gui_yymm = self.year_month_var.get()
                            job_context = create_job_context_from_gui(
                                yymm_var_value=gui_yymm,
                                output_directory=output_folder,
                                batch_mode=True,
                                debug_mode=getattr(self, 'debug_mode', False)
                            )
                            
                            # スナップショット生成RunConfig/YYMM情報含む
                            ui_context = create_ui_context_from_gui(
                                yymm_var_value=gui_yymm,
                                municipality_sets=getattr(self, 'municipality_sets', {}),
                                batch_mode=True,
                                allow_auto_forced_codes=getattr(self, 'allow_auto_forced_codes', False),
                                file_path=file_path
                            )
                            user_yymm = self._resolve_yymm_with_policy(file_path, None)
                            snapshot = self.pre_extract_engine.build_snapshot(file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
                            # Bundle分割ファイルでもJobContext参照処理
                            self._process_single_file_v5_with_snapshot(temp_path, output_folder, snapshot, doc_item_id, job_context)
                        
                        was_split = self.pdf_processor.maybe_split_pdf(
                            file_path, output_folder, force=False, processing_callback=processing_callback
                        )
                        
                        if was_split:
                            split_count += 1
                            self._log(f"Bundle split completed (split-only): {filename}")
                            self.root.after(0, lambda f=file_path: self._add_result_success(
                                f, "分割済み", "Bundle分割", "Auto-Split", "1.00", ["Bundle自動検出"]
                            ))
                        else:
                            self._log(f"Not a bundle, skipped: {filename}")
                            self.root.after(0, lambda f=file_path: self._add_result_success(
                                f, "対象外", "通常PDF", "Bundle判定", "0.00", ["Bundle対象外"]
                            ))
                    else:
                        self._log(f"Non-PDF file, skipped: {filename}")
                        
                except Exception as e:
                    self._log(f"Split-only error: {filename} - {str(e)}")
                    self.root.after(0, lambda f=filename, e=str(e): self._add_result_error(
                        f, f"分割エラー: {e}"
                    ))
            
            # 処理完了
            self.root.after(0, lambda: self.auto_split_control.update_progress(
                f"分割のみ処理完了: {split_count}件分割", "green"
            ))
            
        except Exception as e:
            self._log(f"Split-only processing error: {str(e)}")
            self.root.after(0, lambda: self.auto_split_control.update_progress(
                f"分割エラー: {str(e)}", "red"
            ))
        finally:
            self.root.after(0, self._auto_split_processing_finished)
    
    def _force_split_processing_background(self, output_folder: str):
        """Function description"""
        try:
            total_files = len(self.files_list)
            force_split_count = 0
            
            self.root.after(0, lambda: self.auto_split_control.update_progress("強制分割処理開始...", "orange"))
            
            for i, file_path in enumerate(self.files_list):
                filename = os.path.basename(file_path)
                
                self.root.after(0, lambda f=filename: self.auto_split_control.update_progress(
                    f"強制分割中: {f} ({i+1}/{total_files})", "orange"
                ))
                
                try:
                    if file_path.lower().endswith('.pdf'):
                        # RunConfig/YYMM伝搬用コールバック定義強制分割でも確実に伝搬
                        def processing_callback(temp_path, page_num, bundle_type, doc_item_id: Optional[DocItemID] = None):
                            # JobContext生成強制分割経路でも確実にYYMM伝搬
                            gui_yymm = self.year_month_var.get()
                            job_context = create_job_context_from_gui(
                                yymm_var_value=gui_yymm,
                                output_directory=output_folder,
                                batch_mode=True,
                                debug_mode=getattr(self, 'debug_mode', False)
                            )
                            
                            # スナップショット生成RunConfig/YYMM情報含む
                            ui_context = create_ui_context_from_gui(
                                yymm_var_value=gui_yymm,
                                municipality_sets=getattr(self, 'municipality_sets', {}),
                                batch_mode=True,
                                allow_auto_forced_codes=getattr(self, 'allow_auto_forced_codes', False),
                                file_path=file_path
                            )
                            user_yymm = self._resolve_yymm_with_policy(file_path, None)
                            snapshot = self.pre_extract_engine.build_snapshot(file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
                            # 強制分割ファイルでもJobContext参照処理
                            self._process_single_file_v5_with_snapshot(temp_path, output_folder, snapshot, doc_item_id, job_context)
                        
                        was_split = self.pdf_processor.maybe_split_pdf(
                            file_path, output_folder, force=True, processing_callback=processing_callback
                        )
                        
                        if was_split:
                            force_split_count += 1
                            self._log(f"Force split completed: {filename}")
                            self.root.after(0, lambda f=file_path: self._add_result_success(
                                f, "強制分割済み", "PDF分割", "Force Split", "1.00", ["強制分割実行"]
                            ))
                        else:
                            self._log(f"Force split failed: {filename}")
                            self.root.after(0, lambda f=file_path: self._add_result_error(
                                f, "強制分割失敗"
                            ))
                    else:
                        self._log(f"Non-PDF file for force split: {filename}")
                        
                except Exception as e:
                    self._log(f"Force split error: {filename} - {str(e)}")
                    self.root.after(0, lambda f=filename, e=str(e): self._add_result_error(
                        f, f"強制分割エラー: {e}"
                    ))
            
            # 処理完了
            self.root.after(0, lambda: self.auto_split_control.update_progress(
                f"強制分割処理完了: {force_split_count}件分割", "green"
            ))
            
        except Exception as e:
            self._log(f"Force split processing error: {str(e)}")
            self.root.after(0, lambda: self.auto_split_control.update_progress(
                f"強制分割エラー: {str(e)}", "red"
            ))
        finally:
            self.root.after(0, self._auto_split_processing_finished)
    
    def _auto_split_processing_finished(self):
        """Function description"""
        self.auto_split_processing = False
        self._update_auto_split_button_states()
        self.notebook.select(1)  # 結果タブに切り替え
        messagebox.showinfo("完了", "Auto-Split処理が完了しました")
    
    def _update_auto_split_button_states(self):
        """Function description"""
        if self.auto_split_processing:
            self.auto_split_control.set_button_states(False)
        else:
            self.auto_split_control.set_button_states(True)
    
    def _on_files_dropped(self, files: List[str]):
        """Function description"""
        for file_path in files:
            if file_path not in self.files_list:
                self.files_list.append(file_path)
                self.files_listbox.insert(tk.END, os.path.basename(file_path))
        
        self._log(f"ファイル追加: {len(files)}件")
        
        # v5.2 Auto-split on upload (if enabled)
        if self.auto_split_settings.get('auto_split_bundles', True):
            self._auto_split_on_upload(files)
    
    def _auto_split_on_upload(self, files: List[str]):
        """Function description"""
        bundle_candidates = []
        
        for file_path in files:
            if file_path.lower().endswith('.pdf'):
                # Quick bundle detection
                detection_result = self.pdf_processor._detect_bundle_type(file_path)
                if detection_result.is_bundle:
                    bundle_candidates.append((file_path, detection_result))
        
        if bundle_candidates:
            # Show notification for detected bundles
            bundle_names = [os.path.basename(path) for path, _ in bundle_candidates]
            message = f"束ねPDF検出: {len(bundle_candidates)}件\n\n{', '.join(bundle_names[:3])}"
            if len(bundle_names) > 3:
                message += f"\n...他{len(bundle_names)-3}件"
            
            message += "\n\n 一括処理 で自動分割 出力できます "
            
            self.auto_split_control.update_progress(
                f"束ねPDF検出: {len(bundle_candidates)}件", "orange"
            )
            
            # Optional: Show info dialog
            messagebox.showinfo("Bundle PDF検出", message)


    def _split_files_background(self, output_folder: str):
        """Function description"""
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
                                file_path, os.path.basename(r), "分割完了", "ページ分割", "1.00", ["分割対象検出"]
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
        """Function description"""
        try:
            total_files = len(self.files_list)
            
            for i, file_path in enumerate(self.files_list):
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda f=os.path.basename(file_path): self.status_var.set(f"v5.3処理中: {f}"))
                
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
            self.root.after(0, lambda: self.status_var.set(f"v5.3リネーム完了: {total_files}件処理"))
            
        except Exception as e:
            self._log(f"v5.3リネーム処理エラー: {str(e)}")
        finally:
            self.root.after(0, self._rename_processing_finished)

    def _process_single_file_v5(self, file_path: str, output_folder: str):
        """Function description"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        self._log(f"v5.3処理開始: {filename}")
        
        if ext == '.pdf':
            # v5.3 統一処理常に pre-extract   決定論的リネーム経路
            # UI設定を構築して伝搬
            gui_yymm = self.year_month_var.get()
            ui_context = create_ui_context_from_gui(
                yymm_var_value=gui_yymm,
                municipality_sets=getattr(self, 'municipality_sets', {}),
                batch_mode=True,
                allow_auto_forced_codes=getattr(self, 'allow_auto_forced_codes', False),
                file_path=file_path
            )
            
            user_yymm = self._resolve_yymm_with_policy(file_path, None)  # ポリシーシステム使用
            snapshot = self.pre_extract_engine.build_snapshot(file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
            
            # JobContext生成非分割処理でも確実にYYMM伝搬
            job_context = create_job_context_from_gui(
                yymm_var_value=gui_yymm,
                output_directory=output_folder,
                batch_mode=False,  # 単一ファイル処理
                debug_mode=getattr(self, 'debug_mode', False)
            )
            self._process_single_file_v5_with_snapshot(file_path, output_folder, snapshot, None, job_context)
        elif ext == '.csv':
            self._process_csv_file(file_path, output_folder)  # CSVは従来通り
        else:
            raise ValueError(f"未対応ファイル形式: {ext}")
    
    def _pre_validate_ui_forced_codes(self):
        """Function description"""
        if not self.run_config or not self.run_config.has_manual_yymm():
            # UI YYMMが設定されていない場合は警告のみ処理は継続
            self._log(f"[PRE_VALIDATE] No UI YYMM provided - UI forced codes will fail if encountered")
            return
        
        # UI強制コードリスト
        ui_forced_codes = {"6001", "6002", "6003", "0000"}
        
        # ファイルリスト中でUI強制コードが使われそうな書類をチェック
        potential_ui_forced_files = []
        
        for file_path in self.files_list:
            filename = os.path.basename(file_path).lower()
            
            # ファイル名パターンでUI強制書類を推測
            if any(keyword in filename for keyword in [
                "固定資産", "一括償却", "少額減価償却", "納付税額一覧", "資産台帳"
            ]):
                potential_ui_forced_files.append(file_path)
        
        if potential_ui_forced_files:
            self._log(f"[PRE_VALIDATE] Found {len(potential_ui_forced_files)} potential UI-forced files")
            self._log(f"[PRE_VALIDATE] UI YYMM confirmed: {self.run_config.manual_yymm}")
        
        # 正規化テスト早期エラー検出
        try:
            normalized_yymm = RunConfig._normalize_yymm(self.run_config.manual_yymm)
            self._log(f"[PRE_VALIDATE] YYMM normalized: {self.run_config.manual_yymm} -> {normalized_yymm}")
        except ValueError as e:
            raise ValueError(f"[FATAL][PRE_VALIDATE] Invalid UI YYMM format: {e}")
    
    def _process_single_file_v5_with_snapshot(self, file_path: str, output_folder: str, 
                                             snapshot: PreExtractSnapshot, doc_item_id: Optional[DocItemID] = None,
                                             job_context: Optional[JobContext] = None):
        """Function description"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        self._log(f"[v5.3] 決定論的処理開始: {filename}")
        
        if ext == '.pdf':
            self._process_pdf_file_v5_with_snapshot(file_path, output_folder, snapshot, doc_item_id, job_context)
        elif ext == '.csv':
            self._process_csv_file(file_path, output_folder)  # CSVは従来通り
        else:
            raise ValueError(f"未対応ファイル形式: {ext}")

    def _resolve_yymm_with_policy(self, file_path: str, classification_code: Optional[str]) -> str:
        """
        RunConfig中心のポリシーシステムでYYMM値を決定する
        
<<<<<<< HEAD
        # v5.2 Bundle PDF Auto-Split チェック新統合版
        if self.auto_split_var.get():
            try:
                # v5.2 Bundle PDF Auto-Split を使用
                def processing_callback(temp_path, page_num, bundle_type, reset_context=False):
                    # v5.3.3 分割文脈隔離
                    if reset_context:
                        self._log(f"[SPLIT] Context reset for {os.path.basename(temp_path)} (page {page_num})")
                    
                    # 分割されたページを v5.2 分類エンジンで処理
                    self._process_regular_pdf_v5(temp_path, output_folder)
                    self._log(f"Bundle split page processed: {os.path.basename(temp_path)} (page {page_num}, type: {bundle_type})")
                
                was_split = self.pdf_processor.maybe_split_pdf(
                    file_path, output_folder, force=False, processing_callback=processing_callback
                )
            
            # 新しいRunConfig中心のポリシーシステムを使用
            ctx = {
                'log': self.logger,
                'run_config': self.run_config
            }
            
            final_yymm, yymm_source = resolve_yymm_by_policy(
                class_code=classification_code,
                ctx=ctx,
                settings=self.run_config,
                detected=None
            )
            
            # 結果検証
            if final_yymm:
                if not validate_policy_result(final_yymm, yymm_source, classification_code):
                    raise ValueError(f"Policy validation failed: yymm={final_yymm}, source={yymm_source}, code={classification_code}")
                
                # 監査ログ
                self.logger.info(f"[AUDIT][YYMM] source={yymm_source} value={final_yymm} validation=PASSED")
                self.logger.info(f"[v5.3] YYMM source validation passed: {final_yymm} ({yymm_source} mandatory)")
                
                return final_yymm
            else:
                # YYMMが取得できない場合のエラーハンドリング
                raise ValueError(f"[FATAL][YYMM] Failed to resolve YYMM for {classification_code or 'UNKNOWN'}. source={yymm_source}")
            
        except Exception as e:
            self.logger.error(f"[YYMM][POLICY] Failed to resolve YYMM: {e}")
            raise  # エラーを再提出して呼び出し元に処理を任せる

    def _process_pdf_file_v5(self, file_path: str, output_folder: str):
        """Function description"""
        # v5.3 統一処理すべてスナップショット経由
        # UI設定を構築して伝搬
        gui_yymm = self.year_month_var.get()
        ui_context = create_ui_context_from_gui(
            yymm_var_value=gui_yymm,
            municipality_sets=getattr(self, 'municipality_sets', {}),
            batch_mode=True,
            allow_auto_forced_codes=getattr(self, 'allow_auto_forced_codes', False),
            file_path=file_path
        )
        
        user_yymm = self._resolve_yymm_with_policy(file_path, None)  # ポリシーシステム使用
        snapshot = self.pre_extract_engine.build_snapshot(file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
        
        # JobContext生成v5.3統一パイプラインでも確実にYYMM伝搬
        job_context = create_job_context_from_gui(
            yymm_var_value=gui_yymm,
            output_directory=output_folder,
            batch_mode=True,
            debug_mode=getattr(self, 'debug_mode', False)
        )
        self._process_single_file_v5_with_snapshot(file_path, output_folder, snapshot, None, job_context)

    def _process_regular_pdf_v5(self, file_path: str, output_folder: str):
        """Function description"""
        filename = os.path.basename(file_path)
        
        # OCR テキスト抽出
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
        
        # v5.2 書類分類セット連番対応 + 詳細ログ
        # セット設定情報を取得
        municipality_sets = self._get_municipality_sets()
        
        # 自治体情報を考慮した分類を実行
        classification_result = self.classifier_v5.classify_with_municipality_info_v5(
            text, filename, 
            prefecture_code=None, municipality_code=None,  # テキストから自動推定
            municipality_sets=municipality_sets
        )
        
        document_type = classification_result.document_type if classification_result else "9999_未分類"
        alerts = []  # v5.2では単純化
        
        # 詳細分類ログを出力
        self._log_detailed_classification_info(classification_result, text, filename)
        
        # classification_resultは既に取得済み
        
        # 分類詳細ログを出力v5.1版
        if classification_result:
            self._log(f"v5.1分類結果:")
            self._log(f"  - 書類種別: {classification_result.document_type}")
            self._log(f"  - 信頼度: {classification_result.confidence:.2f}")
            self._log(f"  - 判定方法: {classification_result.classification_method}")
        else:
            self._log("分類に失敗しました")
        
        # v5.3.3 統一パイプライン使用
        try:
            from helpers.final_label_resolver import finalize_label, log_final_result
            
            # DocumentContext模拟对象
            class MockContext:
                def __init__(self, gui_yymm):
                    self.gui_yymm = gui_yymm
                    self.last_class = None
                    self.jurisdiction_hint = None
                    self.selected_set_id = None
                    self.yymm_source = None
            
            # Settings模拟对象  
            class MockSettings:
                def __init__(self, gui_yymm):
                    self.gui_yymm = gui_yymm
            
            # 年月取得
            gui_yymm = self.year_month_var.get()
            detected_yymm = self._extract_year_month_from_pdf(text, filename) if not gui_yymm else None
            
            ctx = MockContext(gui_yymm)
            settings = MockSettings(gui_yymm)
            
            # 統一最終ラベル確定
            result = finalize_label(classification_result.document_type, ctx, settings, detected_yymm)
            log_final_result(result, filename)
            
            new_filename = result.final_label
            
        except Exception as e:
            self._log(f"[WARN] 統一パイプライン失敗 フォールバック使用: {e}")
            import traceback
            traceback.print_exc()  # デバッグ用
            # フォールバック: 従来方式
            year_month = self.year_month_var.get() or self._extract_year_month_from_pdf(text, filename)
            new_filename = self._generate_filename(classification_result.document_type, year_month, "pdf")
        
        # ファイルコピー
        import shutil
        output_path = os.path.join(output_folder, new_filename)
        shutil.copy2(file_path, output_path)
        
        self._log(f"v5.3完了: {filename} -> {new_filename}")
        
        # 結果追加判定方法と信頼度を含む
        method_display = self._get_method_display(classification_result.classification_method)
        confidence_display = f"{classification_result.confidence:.2f}"
        matched_keywords = classification_result.matched_keywords if classification_result.matched_keywords else []
        
        self.root.after(0, lambda: self._add_result_success(
            file_path, new_filename, classification_result.document_type, 
            method_display, confidence_display, matched_keywords
        ))
    
    def _process_pdf_file_v5_with_snapshot(self, file_path: str, output_folder: str, 
                                          snapshot: PreExtractSnapshot, doc_item_id: Optional[DocItemID] = None,
                                          job_context: Optional[JobContext] = None):
        """Function description"""
        filename = os.path.basename(file_path)
        
        # 分類実行従来通り
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
        
        # 空白ページ除外チェック
        if self._should_exclude_blank_page(text, filename):
            self._log(f"[exclude] 空白ページとして除外: {filename}")
            self._log(f"[exclude] テキスト長: {len(text)}, 内容: {text[:100]}...")
            return  # 空白ページは処理をスキップ

        # 決定論的独立化分割 非分割に関係なく統一処理
        municipality_sets = self._get_municipality_sets()
        classification_result = self.classifier_v5.classify_with_municipality_info_v5(
            text, filename, municipality_sets=municipality_sets
        )
        self._log(f"[v5.3] 決定論的独立化処理分割 非分割統一")
        
        # 信頼度チェック0.00かつ9999_未分類の場合は空白ページ可能性を再チェック
        if (classification_result and 
            classification_result.confidence == 0.0 and 
            classification_result.document_type == "9999_未分類" and
            len(text.strip()) < 100):  # より厳格な条件
            self._log(f"[exclude] 信頼度0.00かつ未分類の短いテキスト - 空白ページとして除外: {filename}")
            return
            
        # 決定論的独立化統一された処理フロー
        self._log(f"[v5.3] 決定論的独立化命名開始")
        
        # 元の分類コードを優先使用
        if classification_result and hasattr(classification_result, 'original_doc_type_code') and classification_result.original_doc_type_code:
            document_type = classification_result.original_doc_type_code
            self._log(f"[v5.3]   元の分類コード使用: {document_type} (自治体変更版: {classification_result.document_type})")
        else:
            document_type = classification_result.document_type if classification_result else "9999_未分類"
            self._log(f"[v5.3] 分類結果そのまま: {document_type}")
        
        # 分割 非分割に関係ない統一命名処理
        if doc_item_id:
            # 分割ファイルv5.3決定論的リネーム
            fallback_ocr_text = text if not snapshot.pages else None
            deterministic_filename = self.rename_engine.compute_filename(
                doc_item_id, snapshot, document_type, fallback_ocr_text, job_context
            )
            new_filename = f"{deterministic_filename}.pdf"
        else:
            # 非分割ファイルv5.3決定論的リネーム同じ処理
            # 疑似DocItemIDを作成して統一処理
            from core.models import DocItemID, PageFingerprint, compute_text_sha1, compute_file_md5
            
            # ファイルパスから基本情報を取得
            file_md5 = compute_file_md5(file_path)
            page_fp = PageFingerprint(
                page_md5=file_md5[:16], 
                text_sha1=compute_text_sha1(text[:1000])  # テキストの先頭部分
            )
            pseudo_doc_item_id = DocItemID(
                source_doc_md5=file_md5,
                page_index=0,
                fp=page_fp
            )
            
            fallback_ocr_text = text if not snapshot.pages else None
            deterministic_filename = self.rename_engine.compute_filename(
                pseudo_doc_item_id, snapshot, document_type, fallback_ocr_text, job_context
            )
            new_filename = f"{deterministic_filename}.pdf"
        
        self._log(f"[v5.3] 決定論的独立化命名完了: {new_filename}")
        
        # ファイルコピー
        output_path = os.path.join(output_folder, new_filename)
        output_path = self._generate_unique_filename(output_path)
        
        import shutil
        shutil.copy2(file_path, output_path)
        
        # 結果追加
        if classification_result:
            confidence = f"{classification_result.confidence:.2f}"
            method = self._get_method_display(classification_result.classification_method)
            matched_keywords = classification_result.matched_keywords or []
        else:
            confidence = "0.00"
            method = "未分類"
            matched_keywords = []
        
        self.root.after(0, lambda: self._add_result_success(
            file_path, os.path.basename(output_path), document_type, 
            method, confidence, matched_keywords
        ))
        
        self._log_detailed_classification_info(classification_result, text, filename)

    def _get_municipality_sets(self) -> Dict[int, Dict[str, str]]:
        """Function description"""
        municipality_sets = {}
        
        # セット1-5の設定を取得
        for i in range(1, 6):
            prefecture_var = getattr(self, f'prefecture_var_{i}', None)
            city_var = getattr(self, f'city_var_{i}', None)
            
            if prefecture_var and prefecture_var.get().strip():
                municipality_sets[i] = {
                    "prefecture": prefecture_var.get().strip(),
                    "city": city_var.get().strip() if city_var else ""
                }
                
        self._log(f"セット設定情報: {municipality_sets}")
        return municipality_sets
    
    def _log_detailed_classification_info(self, classification_result, text: str, filename: str):
        """Function description"""
        if not classification_result:
            self._log("  分類に失敗しました")
            return
            
        self._log("=" * 60)
        self._log("  **詳細分類結果**")
        self._log(f"  ファイル名: {filename}")
        
        # 表示は最終使用コードファイル名と一致を使用
        display_document_type = classification_result.original_doc_type_code if (
            hasattr(classification_result, 'original_doc_type_code') and 
            classification_result.original_doc_type_code
        ) else classification_result.document_type
        
        self._log(f"  分類結果: {display_document_type}")
        self._log(f"  信頼度: {classification_result.confidence:.2f}")
        self._log(f"   判定方法: {classification_result.classification_method}")
        
        # 自治体変更版がある場合のみ表示
        if (hasattr(classification_result, 'original_doc_type_code') and 
            classification_result.original_doc_type_code and
            classification_result.original_doc_type_code != classification_result.document_type):
            self._log(f"  自治体変更版: {classification_result.document_type}")
        
        # マッチしたキーワードの詳細
        if classification_result.matched_keywords:
            self._log(f"  マッチしたキーワード: {classification_result.matched_keywords}")
        
        # デバッグステップの詳細利用可能な場合
        if hasattr(classification_result, 'debug_steps') and classification_result.debug_steps:
            self._log("  分類ステップ詳細:")
            for i, step in enumerate(classification_result.debug_steps[:3], 1):  # 上位3件のみ表示
                self._log(f"  {i}. {step.document_type}: スコア {step.score:.1f}, キーワード {step.matched_keywords}")
                if step.excluded:
                    self._log(f"       除外理由: {step.exclude_reason}")
        
        # テキスト内容の一部を表示デバッグ用
        if text:
            preview = text[:200] + "..." if len(text) > 200 else text
            self._log(f"  抽出テキスト先頭200字: {preview}")
        
        # 処理ログがある場合は重要な部分のみ表示
        if hasattr(classification_result, 'processing_log') and classification_result.processing_log:
            important_logs = [log for log in classification_result.processing_log if 
                            "最優先AND条件一致" in log or "自治体連番適用" in log or "強制判定" in log]
            if important_logs:
                self._log("  重要な処理ログ:")
                for log in important_logs[-3:]:  # 最新の3件のみ
                    self._log(f"  {log}")
                    
        self._log("=" * 60)

    def _process_single_file_legacy(self, file_path: str, output_folder: str):
        """Function description"""
        # 従来のclassification.pyを使用した処理
        # 実装は従来のmain.pyのロジックを使用
        self._log(f"従来モード処理: {os.path.basename(file_path)}")
        # ここに従来の処理ロジックを実装...

    def _process_csv_file(self, file_path: str, output_folder: str):
        """Function description"""
        filename = os.path.basename(file_path)
        
        # CSV処理
        result = self.csv_processor.process_csv(file_path)
        
        if not result.success:
            raise ValueError(result.error_message)
        
        # 年月決定手動入力優先
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
            file_path, new_filename, result.document_type, "CSV判定", "1.00", ["CSV自動判定"]
        ))

    def _extract_year_month_from_pdf(self, text: str, filename: str) -> str:
        """Function description"""
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
        """Function description"""
        return f"{doc_type}_{year_month}.{ext}"

    def _get_method_display(self, method: str) -> str:
        """Function description"""
        method_map = {
            "highest_priority_and_condition": "最優先AND条件",
            "standard_keyword_matching": "標準キーワード判定",
            "default_fallback": "デフォルト分類"
        }
        return method_map.get(method, method)

    def _is_split_target(self, file_path: str) -> bool:
        """Function description"""
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
        """Function description"""
        split_files = []
        
        # v5.3.4 Split reset logging
        self._log(f"[reset] __split_ 処理開始 - 分割状態リセット")
        
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
        """Function description"""
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
        """Function description"""
        self.split_processing = False
        self._update_button_states()
        self.notebook.select(1)  # 結果タブに切り替え
        messagebox.showinfo("完了", "分割処理が完了しました")

    def _rename_processing_finished(self):
        """Function description"""
        self.rename_processing = False
        self._update_button_states()
        self.notebook.select(1)  # 結果タブに切り替え
        messagebox.showinfo("完了", "v5.3リネーム処理が完了しました")

    def _update_button_states(self):
        """Function description"""
        if self.split_processing:
            self.split_button.config(state='disabled', text="分割処理中...")
            self.rename_button.config(state='disabled')
        elif self.rename_processing:
            self.split_button.config(state='disabled')
            self.rename_button.config(state='disabled', text="v5.3処理中...")
        else:
            # 両方とも処理中でない場合
            self.split_button.config(state='normal', text="  分割実行")
            self.rename_button.config(state='normal', text="   リネーム実行 (v5.3)")

    def _add_result_success(self, original_file: str, new_filename: str, doc_type: str, method: str, confidence: str, matched_keywords: List[str] = None):
        """Function description"""
        # マッチしたキーワードの表示文字列を生成
        keywords_display = ""
        if matched_keywords:
            # キーワードリストを文字列に変換最大3個まで表示
            display_keywords = matched_keywords[:3]
            keywords_display = ", ".join(display_keywords)
            if len(matched_keywords) > 3:
                keywords_display += f" (+{len(matched_keywords)-3}件)"
        else:
            keywords_display = "なし"
        
        self.result_tree.insert('', 'end', values=(
            os.path.basename(original_file),
            new_filename,
            doc_type,
            method,
            confidence,
            keywords_display,
            "  成功"
        ))

    def _add_result_error(self, original_file: str, error: str):
        """Function description"""
        self.result_tree.insert('', 'end', values=(
            os.path.basename(original_file),
            "-",
            "-",
            "-",
            "0.00",
            "-",
            f"  エラー: {error}"
        ))

    def _open_output_folder(self):
        """Function description"""
        # 実装省略
        pass

    def _export_results(self):
        """Function description"""
        # 実装省略
        pass

    def _clear_results(self):
        """Function description"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

    def _log(self, message: str):
        """Function description"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.root.after(0, lambda: self.log_text.insert(tk.END, log_entry))
        self.root.after(0, lambda: self.log_text.see(tk.END))

    def _clear_log(self):
        """Function description"""
        self.log_text.delete(1.0, tk.END)

    def _save_log(self):
        """Function description"""
        # 実装省略
        pass

    def _export_keyword_dictionary(self):
        """Function description"""
        try:
            # 分類器のエクスポート機能を呼び出し
            export_path = self.classifier_v5.export_keyword_dictionary()
            
            # 成功メッセージ
            messagebox.showinfo(
                "エクスポート完了",
                f"キーワード辞書をエクスポートしました\n{export_path}"
            )
            
            # ログに記録
            self._log(f"キーワード辞書エクスポート完了: {export_path}")
            
        except Exception as e:
            # エラーメッセージ
            messagebox.showerror(
                "エクスポートエラー",
                f"キーワード辞書のエクスポートに失敗しました\n{str(e)}"
            )
            
            # ログに記録
            self._log(f"キーワード辞書エクスポートエラー: {str(e)}")

    def _should_exclude_blank_page(self, ocr_text: str, filename: str) -> bool:
        """Function description"""
        text = ocr_text.strip()
        
        # まず 有意味な税務コンテンツをチェック優先
        meaningful_keywords = [
            "申告書", "受信通知", "納付", "税務", "法人", "消費税", "地方税",
            "都道府県", "市町村", "税務署", "都税事務所", "一括償却", "固定資産"
        ]
        
        has_meaningful_content = any(keyword in text for keyword in meaningful_keywords)
        
        # 有意味なコンテンツがある場合は除外しない
        if has_meaningful_content:
            return False
        
        # 除外キーワード
        exclude_keywords = [
            "Page", "of", "メッセージ", "file:///", 
            "Temp", "TzTemp", "AppData"
        ]
        
        # 除外キーワードチェック
        if any(keyword in text for keyword in exclude_keywords):
            return True
        
        # 非常に短いテキストのチェック有意味コンテンツがない場合のみ
        if len(text) < 30:
            return True
        
        # ファイル名から信頼度の低いページをチェック
        low_confidence_patterns = [
            "__split_", "temp", "blank"
        ]
        
        if any(pattern in filename.lower() for pattern in low_confidence_patterns):
            # 有意味コンテンツがない場合のみ除外
            if not has_meaningful_content and len(text) < 80:
                return True
                
        return False

    def run(self):
        """Function description"""
        self._log("税務書類リネームシステム v5.2 起動 (Bundle PDF Auto-Split対応版)")
        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV5()
    app.run()
"""