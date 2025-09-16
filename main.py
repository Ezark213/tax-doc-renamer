#!/usr/bin/env python3
"""
税務書類リネームシステム v5.4.2 メインアプリケーション
YYMM Policy System・固定資産書類対応・高精度判定システム
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pathlib import Path
from typing import List, Dict, Optional
import sys
import pytesseract
import shutil

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pdf_processor import PDFProcessor
from core.ocr_engine import OCREngine, MunicipalityMatcher, MunicipalitySet
from helpers.yymm_policy import resolve_yymm_by_policy, log_yymm_decision, validate_policy_result
from helpers.settings_context import UIContext, create_ui_context_from_gui, normalize_settings_input
from helpers.run_config import RunConfig, create_run_config_from_gui
from core.csv_processor import CSVProcessor
from core.classification_v5 import DocumentClassifierV5  # v5.1バグ修正版エンジンを使用
from core.runtime_paths import get_tesseract_executable_path, get_tessdata_dir_path, validate_tesseract_resources
from ui.drag_drop import DropZoneFrame, AutoSplitControlFrame
# v5.4.2: Deterministic renaming system
from core.pre_extract import create_pre_extract_engine
from core.rename_engine import create_rename_engine
from core.models import DocItemID, PreExtractSnapshot
from helpers.job_context import JobContext


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
    """税務書類リネームシステム v5.4.2 メインクラス"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.4.2 (Bundle PDF Auto-Split)")
        self.root.geometry("1200x800")
        
        # v5.2 コアエンジンの初期化（ロガー付き）
        import logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.pdf_processor = PDFProcessor(logger=self.logger)
        self.ocr_engine = OCREngine()
        self.csv_processor = CSVProcessor()
        self.classifier_v5 = DocumentClassifierV5(debug_mode=True)
        
        # v5.4.2: Deterministic renaming system
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
        
        # Bundle二重処理防止: 起動時の古い__split_ファイル一括クリーンアップ
        self._cleanup_old_split_files()
    
    def _validate_yymm_input(self, *args):
        """YYMMの入力値をリアルタイムバリデーション"""
        try:
            from helpers.yymm_policy import _normalize_yymm, _validate_yymm
            
            current_value = self.year_month_var.get()
            if not current_value:
                self.yymm_status_var.set("📋 YYMM入力待ち")
                self.yymm_status_label.config(foreground='gray')
                return
            
            # 正規化を試行
            normalized = _normalize_yymm(current_value)
            if normalized and _validate_yymm(normalized):
                self.yymm_status_var.set(f"✓ 正常: {current_value} → {normalized} (UI強制対応)")
                self.yymm_status_label.config(foreground='green')
                
                # UI強制コードへの対応状況も表示
                forced_codes = ["6001", "6002", "6003", "0000"]
                self.yymm_status_var.set(f"✓ 正常: {current_value} → {normalized} | UI強制対応({', '.join(forced_codes)})")
            else:
                self.yymm_status_var.set(f"⚠️ 無効: {current_value} (例: 2508, 25/08, ２５０８)")
                self.yymm_status_label.config(foreground='red')
                
        except Exception as e:
            self.yymm_status_var.set(f"❌ エラー: {str(e)}")
            self.yymm_status_label.config(foreground='red')

    def _create_ui(self):
        """UIの構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="税務書類リネームシステム v5.4.2", 
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 5))
        
        # v5.2 新機能の説明
        info_label = ttk.Label(
            main_frame,
            text="🆕 v5.2 New: Bundle PDF Auto-Split | ✨ v5.1バグ修正完了版",
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
        
        # 右側: 設定 + Auto-Split控制
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="設定・Auto-Split", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # v5.2 Auto-Split控制フレーム
        self.auto_split_control = AutoSplitControlFrame(right_frame)
        self.auto_split_control.pack(fill='x', pady=(0, 10))
        
        # コールバック設定 - v5.4.2 簡素化版（フォルダ処理）
        self.auto_split_control.set_callbacks(
            batch_callback=self._start_folder_batch_processing
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
        
        # YYMMバリデーション設定（リアルタイム更新）
        self.year_month_var.trace_add('write', self._validate_yymm_input)
        self._validate_yymm_input()  # 初期バリデーション
        
        # 自治体設定
        municipality_frame = ttk.LabelFrame(right_frame, text="自治体設定")
        municipality_frame.pack(fill='x', pady=(0, 10))
        
        self._create_municipality_settings(municipality_frame)
        
        # 処理オプション（機能常時有効のため設定UI削除）
        # self.auto_split_var, self.ocr_enhanced_var, self.v5_mode_var は常にTrueとして動作
        
        # エクスポート設定
        export_frame = ttk.LabelFrame(right_frame, text="エクスポート設定")
        export_frame.pack(fill='x', pady=(0, 10))
        
        # キーワード辞書エクスポートボタン
        ttk.Button(
            export_frame,
            text="📤 キーワード辞書をエクスポート",
            command=self._export_keyword_dictionary
        ).pack(anchor='w', pady=5)
        
        export_info = ttk.Label(
            export_frame,
            text="※分類ルール辞書をJSONファイルでデスクトップに保存",
            font=('Arial', 8),
            foreground='gray'
        )
        export_info.pack(anchor='w', padx=20)
        
        # 処理ボタン（簡素化版 - フォルダ指定による自動処理）
        # ※従来の分割実行・リネーム実行ボタンは削除し、フォルダ指定による一括自動処理に統一

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
        
        ttk.Button(result_button_frame, text="📁 出力フォルダを開く", command=self._open_output_folder).pack(side='left', padx=(0, 5))
        ttk.Button(result_button_frame, text="📄 結果をエクスポート", command=self._export_results).pack(side='left', padx=5)
        ttk.Button(result_button_frame, text="🔄 結果をクリア", command=self._clear_results).pack(side='left', padx=5)

    def _create_log_tab(self):
        """ログタブの作成"""
        ttk.Label(self.log_frame, text="処理ログ・デバッグ情報 (v5.4.2)", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
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

    def _create_municipality_settings(self, parent_frame):
        """自治体設定UIの作成"""
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
        """デフォルト自治体設定"""
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
    
    def _cleanup_old_split_files(self):
        """Bundle二重処理防止: 古い__split_ファイルを一括クリーンアップ"""
        try:
            import glob
            import os
            
            # 現在のディレクトリとその配下のフォルダから__split_ファイルを検索
            search_patterns = [
                "__split_*.pdf",  # 現在のディレクトリ
                "*/__split_*.pdf",  # 1階層下のフォルダ
                "*/*/__split_*.pdf"  # 2階層下のフォルダ（出力フォルダ等）
            ]
            
            total_cleaned = 0
            for pattern in search_patterns:
                split_files = glob.glob(pattern)
                for split_file in split_files:
                    try:
                        os.remove(split_file)
                        total_cleaned += 1
                        self._log(f"[CLEANUP] 古い__split_ファイルを削除: {split_file}")
                    except Exception as e:
                        self._log(f"[CLEANUP] ファイル削除エラー {split_file}: {e}")
            
            if total_cleaned > 0:
                self._log(f"[CLEANUP] Bundle二重処理防止: {total_cleaned}件の古い__split_ファイルをクリーンアップしました")
            else:
                self._log("[CLEANUP] クリーンアップ対象の__split_ファイルはありませんでした")
                
        except Exception as e:
            self._log(f"[CLEANUP] クリーンアップ処理エラー: {e}")

    def _on_files_dropped(self, files):
        """ファイルドロップ時の処理"""
        # __split_ファイルを除外
        valid_files = [f for f in files if not os.path.basename(f).startswith("__split_")]
        
        # ファイルリストを更新
        self.files_list = valid_files
        
        # リストボックスの更新
        self.files_listbox.delete(0, tk.END)
        for file_path in valid_files:
            self.files_listbox.insert(tk.END, os.path.basename(file_path))
        
        self._log(f"ファイルが選択されました: {len(valid_files)}件")

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
        """v5.4.2 リネーム処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.split_processing or self.rename_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 自治体セットを取得し、キャッシュをクリア（新しい処理開始）
        self._cached_municipality_sets = None  # 前回のキャッシュをクリア
        self.municipality_sets = self._get_municipality_sets()
        
        # 出力フォルダ選択
        output_folder = filedialog.askdirectory(title="リネーム済みファイルの出力フォルダを選択")
        if not output_folder:
            return
        
        # バックグラウンド処理開始
        self.rename_processing = True
        self._update_button_states()
        
        # v5.4.2モードの確認
        use_v5_mode = True  # 機能常時有効
        self._log(f"リネーム処理開始: v5.4.2モード={'有効' if use_v5_mode else '無効'}")
        
        thread = threading.Thread(
            target=self._rename_files_background_v5,
            args=(output_folder, use_v5_mode),
            daemon=True
        )
        thread.start()

    def _start_folder_batch_processing(self, source_folder=None):
        """v5.4.2 フォルダ一括処理開始（オリジナルの処理フロー復元）"""
        # フォルダが指定されていない場合はダイアログで選択
        if not source_folder:
            source_folder = filedialog.askdirectory(title="処理対象フォルダを選択（PDFファイルが含まれるフォルダ）")
            if not source_folder:
                return
        
        # PDFファイルを検索
        pdf_files = []
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                if file.lower().endswith('.pdf') and not file.startswith('__split_'):
                    pdf_files.append(os.path.join(root, file))
        
        if not pdf_files:
            messagebox.showwarning("警告", f"選択されたフォルダにPDFファイルが見つかりませんでした:\n{source_folder}")
            return
        
        # 処理中の場合はスキップ
        if self.rename_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 自治体セットを取得し、キャッシュをクリア（新しい処理開始）
        self._cached_municipality_sets = None  # 前回のキャッシュをクリア
        self.municipality_sets = self._get_municipality_sets()
        
        # YYMMフォルダを作成（重複時は_2, _3と連番で作成）
        yymm = self.year_month_var.get()
        base_output_folder = os.path.join(source_folder, yymm)
        
        # 既存フォルダがある場合は連番を追加
        counter = 1
        output_folder = base_output_folder
        
        while os.path.exists(output_folder):
            counter += 1
            output_folder = f"{base_output_folder}_{counter}"
        
        try:
            os.makedirs(output_folder, exist_ok=True)
            if counter > 1:
                self._log(f"YYMMフォルダ作成（連番）: {output_folder}")
            else:
                self._log(f"YYMMフォルダ作成: {output_folder}")
        except Exception as e:
            messagebox.showerror("エラー", f"YYMMフォルダの作成に失敗しました:\n{e}")
            return
        
        # 重複ファイル名キャッシュをクリア
        if hasattr(self, '_used_filenames'):
            self._used_filenames.clear()
            self._log("[DEBUG] ファイル名キャッシュクリア")
        
        # バックグラウンド処理開始
        self.rename_processing = True
        self._update_button_states()
        
        # ファイル名重複追跡の初期化
        if not hasattr(self, '_filename_lock'):
            self._filename_lock = threading.Lock()
            self._used_filenames = set()
        else:
            # 既存のセッション情報をクリアして新しい処理を開始
            with self._filename_lock:
                self._used_filenames.clear()
        
        self._log(f"フォルダ一括処理開始: {len(pdf_files)}件のPDFファイルを処理")
        self._log(f"処理対象フォルダ: {source_folder}")
        self._log(f"出力先: {output_folder}")
        
        thread = threading.Thread(
            target=self._folder_batch_processing_background,
            args=(pdf_files, output_folder),
            daemon=True
        )
        thread.start()

    def _folder_batch_processing_background(self, pdf_files, output_folder):
        """フォルダ一括処理のバックグラウンド処理"""
        try:
            total_files = len(pdf_files)
            processed_files = 0
            
            for i, file_path in enumerate(pdf_files, 1):
                filename = os.path.basename(file_path)
                
                # リネーム済みファイルをスキップ（無限リネーム防止）
                if self._is_already_renamed(filename):
                    self.root.after(0, lambda f=filename: self._log(f"スキップ（既リネーム済み）: {f}"))
                    continue
                
                self.root.after(0, lambda f=filename: self._log(f"処理中 ({i}/{total_files}): {f}"))
                
                try:
                    # v5.4.2統一処理: 常に pre-extract → 決定論的リネーム経路
                    gui_yymm = self.year_month_var.get()
                    ui_context = create_ui_context_from_gui(
                        yymm_var_value=gui_yymm,
                        municipality_sets=getattr(self, 'municipality_sets', {}),
                        batch_mode=True,
                        debug_mode=False
                    )
                    
                    # ファイル処理（Bundle分割含む）
                    # まず分割を試行（Bundleファイルの場合）
                    split_result = self.pdf_processor.maybe_split_pdf(
                        input_pdf_path=file_path,
                        out_dir=output_folder,
                        force=False,
                        processing_callback=None
                    )
                    
                    if split_result['success']:
                        # Bundle分割が成功した場合
                        processed_files += 1
                        self.root.after(0, lambda f=filename: self._log(f"Bundle分割完了: {f}"))
                        
                        # Bundle分割後の各ファイルをリネーム処理
                        if split_result.get('split_files'):
                            split_files = split_result.get('split_files', [])
                            for split_file_path in split_files:
                                try:
                                    # 分割後ファイルにもリネーム処理を適用
                                    user_yymm = self._resolve_yymm_with_policy(split_file_path, None)
                                    snapshot = self.pre_extract_engine.build_snapshot(split_file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
                                    success = self._process_single_file_v5_with_snapshot(split_file_path, output_folder, snapshot)
                                    if success:
                                        self.root.after(0, lambda sf=os.path.basename(split_file_path): self._log(f"分割後ファイル処理完了: {sf}"))
                                    
                                    # 一時ファイル削除処理
                                    if os.path.exists(split_file_path) and os.path.basename(split_file_path).startswith("__split_"):
                                        try:
                                            # 一時ファイルを削除（未分類移動せず）
                                            os.remove(split_file_path)
                                            self.root.after(0, lambda sf=os.path.basename(split_file_path): self._log(f"[cleanup] 一時ファイル削除: {sf}"))
                                        except Exception as cleanup_error:
                                            self.root.after(0, lambda sf=os.path.basename(split_file_path), err=str(cleanup_error):
                                                           self._log(f"[cleanup] 一時ファイル削除失敗 {sf}: {err}"))
                                    
                                except Exception as e:
                                    self.root.after(0, lambda err=str(e), sf=os.path.basename(split_file_path): self._log(f"分割後ファイル処理エラー {sf}: {err}"))
                                    # エラー時は一時ファイルを削除
                                    try:
                                        if os.path.exists(split_file_path):
                                            os.remove(split_file_path)
                                            self.root.after(0, lambda sf=os.path.basename(split_file_path): self._log(f"[error-recovery] エラーファイルを削除: {sf}"))
                                    except Exception as recovery_error:
                                        self.root.after(0, lambda err=str(recovery_error): self._log(f"[error-recovery] ファイル削除失敗: {err}"))
                    else:
                        # 通常の単一ファイル処理 - スナップショットを作成してから処理
                        user_yymm = self._resolve_yymm_with_policy(file_path, None)
                        snapshot = self.pre_extract_engine.build_snapshot(file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
                        success = self._process_single_file_v5_with_snapshot(file_path, output_folder, snapshot)
                        if success:
                            processed_files += 1
                        
                except Exception as e:
                    self.root.after(0, lambda err=str(e), f=filename: self._log(f"ファイル処理エラー {f}: {err}"))
                    continue
            
            self.root.after(0, lambda: self._log(f"フォルダ一括処理完了"))
            
        except Exception as e:
            self._log(f"v5.4.2リネーム処理エラー: {str(e)}")
        finally:
            self.root.after(0, self._rename_processing_finished)

    def _process_single_file_v5(self, file_path: str, output_folder: str):
        """v5.4.2 単一ファイルの処理"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        self._log(f"v5.4.2処理開始: {filename}")
        
        if ext == '.pdf':
            # v5.4.2 統一処理：常に pre-extract → 決定論的リネーム経路
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
            self._process_single_file_v5_with_snapshot(file_path, output_folder, snapshot)
        elif ext == '.csv':
            self._process_csv_file(file_path, output_folder)  # CSVは従来通り
        else:
            raise ValueError(f"未対応ファイル形式: {ext}")
    
    def _process_single_file_v5_with_snapshot(self, file_path: str, output_folder: str, 
                                             snapshot: PreExtractSnapshot, doc_item_id: Optional[DocItemID] = None, job_context: Optional['JobContext'] = None):
        """v5.4.2 スナップショット方式を使用したファイル処理（決定論的命名）"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        self._log(f"[v5.4.2] 決定論的処理開始: {filename}")
        
        if ext == '.pdf':
            self._process_pdf_file_v5_with_snapshot(file_path, output_folder, snapshot, doc_item_id, job_context)
        elif ext == '.csv':
            self._process_csv_file(file_path, output_folder)  # CSVは従来通り
        else:
            raise ValueError(f"未対応ファイル形式: {ext}")

    def _resolve_yymm_with_policy(self, file_path: str, classification_code: Optional[str]) -> str:
        """
        RunConfig中心のポリシーシステムでYYMM値を決定する
        
        Args:
            file_path: 処理対象PDFファイルパス
            classification_code: 分類コード（分かっている場合）
            
        Returns:
            str: ポリシーで決定されたYYMM値
            
        Raises:
            ValueError: ポリシーによる決定に失敗した場合
        """
        try:
            # RunConfigを作成または取得
            if self.run_config is None:
                gui_yymm = self.year_month_var.get()
                self.run_config = create_run_config_from_gui(
                    yymm_var_value=gui_yymm,
                    batch_mode=False,  # 単発処理
                    debug_mode=getattr(self, 'debug_mode', False)
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
                self.logger.info(f"[v5.4.2] YYMM source validation passed: {final_yymm} ({yymm_source} mandatory)")
                
                return final_yymm
            else:
                # YYMMが取得できない場合のエラーハンドリング
                raise ValueError(f"[FATAL][YYMM] Failed to resolve YYMM for {classification_code or 'UNKNOWN'}. source={yymm_source}")
            
        except Exception as e:
            self.logger.error(f"[YYMM][POLICY] Failed to resolve YYMM: {e}")
            raise  # エラーを再提出して呼び出し元に処理を任せる

    def _process_pdf_file_v5(self, file_path: str, output_folder: str):
        """v5.4.2 統一パイプライン PDFファイル処理"""
        # v5.4.2 統一処理：すべてスナップショット経由
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
        self._process_single_file_v5_with_snapshot(file_path, output_folder, snapshot)

    def _process_regular_pdf_v5(self, file_path: str, output_folder: str):
        """v5.2 通常PDFの処理 (高精度分類エンジン)"""
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
        
        # v5.2 書類分類（セット連番対応 + 詳細ログ）
        # セット設定情報を取得（キャッシュ済みの場合は再利用）
        municipality_sets = getattr(self, '_cached_municipality_sets', None)
        if municipality_sets is None:
            municipality_sets = self._get_municipality_sets()
            self._cached_municipality_sets = municipality_sets
        
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
        
        # 分類詳細ログを出力（v5.1版）
        if classification_result:
            self._log(f"v5.1分類結果:")
            self._log(f"  - 書類種別: {classification_result.document_type}")
            self._log(f"  - 信頼度: {classification_result.confidence:.2f}")
            self._log(f"  - 判定方法: {classification_result.classification_method}")
        else:
            self._log("分類に失敗しました")
        
        # 年月決定
        year_month = self.year_month_var.get() or self._extract_year_month_from_pdf(text, filename)
        
        # 新ファイル名生成（最新市町村連番システム対応）
        new_filename = self._generate_filename(classification_result.document_type, year_month, "pdf", classification_result)
        
        # ファイルコピー
        import shutil
        output_path = os.path.join(output_folder, new_filename)
        
        # デバッグ: フォルダ存在確認
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            self._log(f"[DEBUG] 出力フォルダが存在しません: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
            self._log(f"[DEBUG] 出力フォルダを作成しました: {output_dir}")
        
        self._log(f"[DEBUG] ファイルコピー開始: {file_path} -> {output_path}")
        try:
            shutil.copy2(file_path, output_path)
            # コピー結果を確認
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self._log(f"[DEBUG] ファイルコピー成功: {output_path} ({file_size} bytes)")
            else:
                self._log(f"[ERROR] ファイルコピー失敗: {output_path} が作成されませんでした")
        except Exception as e:
            self._log(f"[ERROR] ファイルコピーエラー: {str(e)}")
            raise
        
        self._log(f"v5.4.2完了: {filename} -> {new_filename}")
        
        # 結果追加（判定方法と信頼度を含む）
        method_display = self._get_method_display(classification_result.classification_method)
        confidence_display = f"{classification_result.confidence:.2f}"
        matched_keywords = classification_result.matched_keywords if classification_result.matched_keywords else []
        
        self.root.after(0, lambda: self._add_result_success(
            file_path, new_filename, classification_result.document_type, 
            method_display, confidence_display, matched_keywords
        ))
    
    def _process_pdf_file_v5_with_snapshot(self, file_path: str, output_folder: str, 
                                          snapshot: PreExtractSnapshot, doc_item_id: Optional[DocItemID] = None, job_context: Optional['JobContext'] = None):
        """v5.4.2 スナップショット方式PDFファイル処理（決定論的命名）"""
        filename = os.path.basename(file_path)
        
        # Debug log for Bundle splitting files
        if filename.startswith("__split_"):
            print(f"[DEBUG_TEST] Bundle分割ファイル処理: {filename}")
            print(f"[DEBUG_TEST] job_context存在: {job_context is not None}")
            if job_context:
                print(f"[DEBUG_TEST] job_context.current_municipality_sets: {getattr(job_context, 'current_municipality_sets', None)}")
        
        # 分類実行（従来通り）
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
            return None  # 空白ページは処理をスキップ

        # 決定論的独立化：分割・非分割に関係なく統一処理
        # セット設定情報を取得（キャッシュ済みの場合は再利用）
        municipality_sets = getattr(self, '_cached_municipality_sets', None)
        if municipality_sets is None:
            municipality_sets = self._get_municipality_sets()
            self._cached_municipality_sets = municipality_sets
        
        # job_contextがある場合（Bundle分割）は連番処理対応のメソッドを使用
        if job_context is not None:
            self._log(f"[BUNDLE_SPLIT] JobContext付き分類開始: page={job_context.page_number}")
            classification_result = self.classifier_v5.classify_document_v5(
                text, filename, job_context=job_context
            )
        else:
            classification_result = self.classifier_v5.classify_with_municipality_info_v5(
                text, filename, municipality_sets=municipality_sets, job_context=job_context
            )
        self._log(f"[v5.4.2] 決定論的独立化処理：分割・非分割統一")
        
        # 信頼度チェック：0.00かつ9999_未分類の場合は空白ページ可能性を再チェック
        if (classification_result and 
            classification_result.confidence == 0.0 and 
            classification_result.document_type == "9999_未分類" and
            len(text.strip()) < 100):  # より厳格な条件
            self._log(f"[exclude] 信頼度0.00かつ未分類の短いテキスト - 空白ページとして除外: {filename}")
            return None
            
        # 決定論的独立化：統一された処理フロー
        self._log(f"[v5.4.2] 決定論的独立化命名開始")
        
        # ファイル名用には最終結果（オーバーレイ適用後）を使用
        final_document_type = classification_result.document_type if classification_result else "9999_未分類"
        
        # 表示用に元コードと最終結果を比較
        if classification_result and hasattr(classification_result, 'original_doc_type_code') and classification_result.original_doc_type_code:
            if classification_result.original_doc_type_code != classification_result.document_type:
                self._log(f"[v5.4.2] 🎯 市町村連番適用: {classification_result.original_doc_type_code} → {final_document_type}")
            else:
                self._log(f"[v5.4.2] 🎯 分類結果: {final_document_type}")
        else:
            self._log(f"[v5.4.2] 🎯 分類結果: {final_document_type}")
        
        # YYMMポリシーシステムでYYMM値を取得
        user_yymm = self._resolve_yymm_with_policy(file_path, final_document_type)
        
        # ファイル名生成（市町村連番システム対応）
        new_filename = self._generate_filename(final_document_type, user_yymm, "pdf", classification_result)
        
        # 🔥 段階3：最終ファイル名生成の確認ログ
        if filename.startswith("__split_"):
            print(f"[FILENAME_DEBUG] 分類結果: {final_document_type}")
            print(f"[FILENAME_DEBUG] 最終ファイル名: {new_filename}")
        
        self._log(f"[v5.4.2] 統一ファイル名生成完了: {new_filename}")
        
        # ファイルコピー
        output_path = os.path.join(output_folder, new_filename)
        output_path = self._generate_unique_filename(output_path)
        
        # デバッグ: フォルダ存在確認
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            self._log(f"[DEBUG] 出力フォルダが存在しません: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
            self._log(f"[DEBUG] 出力フォルダを作成しました: {output_dir}")
        
        import shutil
        self._log(f"[DEBUG] ファイルコピー開始: {file_path} -> {output_path}")
        try:
            shutil.copy2(file_path, output_path)
            # コピー結果を確認
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self._log(f"[DEBUG] ファイルコピー成功: {output_path} ({file_size} bytes)")
            else:
                self._log(f"[ERROR] ファイルコピー失敗: {output_path} が作成されませんでした")
        except Exception as e:
            self._log(f"[ERROR] ファイルコピーエラー: {str(e)}")
            raise
        
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
            file_path, os.path.basename(output_path), final_document_type, 
            method, confidence, matched_keywords
        ))
        
        self._log_detailed_classification_info(classification_result, text, filename)
        
        # リネーム後のファイルパスを返す
        return output_path

    def _get_municipality_sets(self) -> Dict[int, Dict[str, str]]:
        """自治体セット情報を取得 - Bundle分割対応版"""
        municipality_sets = {}
        
        print(f"[MUNICIPALITY_SETS] 自治体セット情報取得開始")
        
        # UI変数からの取得を試行
        for i in range(1, 4):  # Bundle分割では1-3のみを使用
            pref_var = getattr(self, f'prefecture_var_{i}', None)
            city_var = getattr(self, f'city_var_{i}', None)
            
            print(f"[MUNICIPALITY_SETS] セット{i}: 変数存在確認 pref={pref_var is not None}, city={city_var is not None}")
            
            # UI変数が正常に設定されている場合
            if pref_var and city_var:
                try:
                    pref = pref_var.get().strip()
                    city = city_var.get().strip()
                    print(f"[MUNICIPALITY_SETS] セット{i}: UI値取得 '{pref}', '{city}'")
                    
                    if pref:  # 都道府県名が設定されている場合のみセット作成
                        municipality_sets[i] = {
                            'prefecture': pref,
                            'city': city
                        }
                        print(f"[MUNICIPALITY_SETS] UI設定取得: セット{i} = {pref} {city}")
                except Exception as e:
                    print(f"[MUNICIPALITY_SETS] UI変数アクセスエラー: セット{i}, {e}")
            else:
                print(f"[MUNICIPALITY_SETS] セット{i}: 変数が存在しないためスキップ")
        
        print(f"[MUNICIPALITY_SETS] UI取得結果: {municipality_sets}")
        
        # フォールバック: UI変数から取得できない場合はデフォルト設定を使用
        if not municipality_sets:
            print(f"[MUNICIPALITY_SETS] フォールバック: デフォルト設定を適用")
            municipality_sets = {
                1: {'prefecture': '東京都', 'city': ''},
                2: {'prefecture': '愛知県', 'city': '蒲郡市'},
                3: {'prefecture': '福岡県', 'city': '福岡市'}
            }
            print(f"[MUNICIPALITY_SETS] デフォルト設定適用完了")
        
        print(f"[MUNICIPALITY_SETS] 最終セット情報: {municipality_sets}")
        
        # UI変数が取得できない場合の警告
        if len(municipality_sets) < 3:
            print(f"[MUNICIPALITY_SETS] 警告: 自治体セット情報が不完全です（{len(municipality_sets)}/3セット）")
            print(f"[MUNICIPALITY_SETS] Bundle分割連番処理に影響する可能性があります")
        
        self._log(f"セット設定情報: {municipality_sets}")
        return municipality_sets
    
    def _log_detailed_classification_info(self, classification_result, text: str, filename: str):
        """詳細な分類情報をログ出力"""
        if not classification_result:
            self._log("❌ 分類に失敗しました")
            return
            
        self._log("=" * 60)
        self._log("🔍 **詳細分類結果**")
        self._log(f"📄 ファイル名: {filename}")
        
        # 表示は最終使用コード（ファイル名と一致）を使用
        display_document_type = classification_result.original_doc_type_code if (
            hasattr(classification_result, 'original_doc_type_code') and 
            classification_result.original_doc_type_code
        ) else classification_result.document_type
        
        self._log(f"📋 分類結果: {display_document_type}")
        self._log(f"🎯 信頼度: {classification_result.confidence:.2f}")
        self._log(f"⚙️ 判定方法: {classification_result.classification_method}")
        
        # 自治体変更版がある場合のみ表示
        if (hasattr(classification_result, 'original_doc_type_code') and 
            classification_result.original_doc_type_code and
            classification_result.original_doc_type_code != classification_result.document_type):
            self._log(f"📍 自治体変更版: {classification_result.document_type}")
        
        # マッチしたキーワードの詳細
        if classification_result.matched_keywords:
            self._log(f"🔑 マッチしたキーワード: {classification_result.matched_keywords}")
        
        # デバッグステップの詳細（利用可能な場合）
        if hasattr(classification_result, 'debug_steps') and classification_result.debug_steps:
            self._log("📊 分類ステップ詳細:")
            for i, step in enumerate(classification_result.debug_steps[:3], 1):  # 上位3件のみ表示
                self._log(f"  {i}. {step.document_type}: スコア {step.score:.1f}, キーワード {step.matched_keywords}")
                if step.excluded:
                    self._log(f"     ❌ 除外理由: {step.exclude_reason}")
        
        # テキスト内容の一部を表示（デバッグ用）
        if text:
            preview = text[:200] + "..." if len(text) > 200 else text
            self._log(f"📝 抽出テキスト（先頭200字）: {preview}")
        
        # 処理ログがある場合は重要な部分のみ表示
        if hasattr(classification_result, 'processing_log') and classification_result.processing_log:
            important_logs = [log for log in classification_result.processing_log if 
                            "最優先AND条件一致" in log or "自治体連番適用" in log or "強制判定" in log]
            if important_logs:
                self._log("🔧 重要な処理ログ:")
                for log in important_logs[-3:]:  # 最新の3件のみ
                    self._log(f"  {log}")
                    
        self._log("=" * 60)

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
            file_path, new_filename, result.document_type, "CSV判定", "1.00", ["CSV自動判定"]
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

    def _generate_filename(self, doc_type: str, year_month: str, ext: str, classification_result=None) -> str:
        """
        ファイル名生成（市町村連番システム対応版 - 修正版）
        
        Args:
            doc_type: 分類結果 (基本は使わない、classification_resultから取得)
            year_month: YYMM形式の年月  
            ext: 拡張子
            classification_result: 分類結果オブジェクト（オーバーレイ情報含む）
        """
        # classification_resultから最終的なdocument_typeを取得
        final_doc_type = doc_type
        if classification_result:
            # オーバーレイが適用されている場合は classification_result.document_type を使用
            if hasattr(classification_result, 'document_type') and classification_result.document_type:
                final_doc_type = classification_result.document_type
                self._log(f"[市町村連番システム] 分類結果からdocument_type使用: {final_doc_type}")
            
            # さらに、元コードと違う場合は自治体変更版が適用されていることを確認
            if (hasattr(classification_result, 'original_doc_type_code') and 
                classification_result.original_doc_type_code and 
                final_doc_type != classification_result.original_doc_type_code):
                self._log(f"[市町村連番システム] 自治体変更版適用: {classification_result.original_doc_type_code} → {final_doc_type}")
        
        # 最終ファイル名生成
        filename = f"{final_doc_type}_{year_month}.{ext}"
        self._log(f"[最終ファイル名] {filename}")
        return filename
    
    def _apply_municipality_serial_numbering(self, filename: str, classification_result) -> str:
        """
        市町村連番システム適用（GitHub ff12ea5準拠）
        
        基本仕様：
        - 東京都: 1001番台（固定）
        - 愛知県: 1011番台（1001 + 10）
        - 福岡県: 1021番台（1001 + 20）
        - 市レベル: 2001→2011→2021（+10刻み）
        """
        if not hasattr(classification_result, 'prefecture_code') or not hasattr(classification_result, 'city_code'):
            # 市町村情報がない場合はそのまま返す
            return filename
        
        pref_code = classification_result.prefecture_code
        city_code = classification_result.city_code
        
        # ファイル名から現在のコードを抽出
        parts = filename.split('_')
        if len(parts) < 2:
            return filename
            
        current_code = parts[0]
        
        # 地方税系コードの場合のみ処理
        if not current_code.isdigit() or len(current_code) != 4:
            return filename
            
        code_int = int(current_code)
        
        # 都道府県レベル（1000番台）の連番処理
        if 1000 <= code_int < 2000:
            if pref_code and pref_code != 1001:  # 東京都以外
                # 新しいコードに置換
                new_parts = parts.copy()
                new_parts[0] = str(pref_code)
                
                # 都道府県名も更新（可能なら）
                if len(parts) > 1 and pref_code == 1011:
                    new_parts[1] = "愛知県"
                elif len(parts) > 1 and pref_code == 1021:
                    new_parts[1] = "福岡県"
                
                return '_'.join(new_parts)
        
        # 市区町村レベル（2000番台）の連番処理
        elif 2000 <= code_int < 3000:
            if city_code and city_code != 2001:  # 基本市以外
                # 新しいコードに置換
                new_parts = parts.copy()
                new_parts[0] = str(city_code)
                
                # 市区町村名も更新（可能なら）
                if len(parts) > 1:
                    if city_code == 2011:
                        new_parts[1] = "愛知県蒲郡市"
                    elif city_code == 2021:
                        new_parts[1] = "福岡県福岡市"
                
                return '_'.join(new_parts)
        
        return filename

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
        
        # v5.4.2.4 Split reset logging
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
        """重複しないファイル名を生成（スレッドセーフ）"""
        # スレッドセーフなロック機構を使用
        if not hasattr(self, '_filename_lock'):
            self._filename_lock = threading.Lock()
            self._used_filenames = set()
        
        with self._filename_lock:
            # 既に使用されているファイル名をチェック
            if filepath not in self._used_filenames and not os.path.exists(filepath):
                self._used_filenames.add(filepath)
                return filepath
            
            dir_name = os.path.dirname(filepath)
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            ext = os.path.splitext(filepath)[1]
            
            counter = 1
            while True:
                new_filename = f"{base_name}_{counter:03d}{ext}"
                new_filepath = os.path.join(dir_name, new_filename)
                if new_filepath not in self._used_filenames and not os.path.exists(new_filepath):
                    self._used_filenames.add(new_filepath)
                    # 重複処理のログ出力
                    print(f"[DUPLICATE] {os.path.basename(filepath)} -> {os.path.basename(new_filepath)}")
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
        
        # 使用済みファイル名セットをクリア
        if hasattr(self, '_used_filenames'):
            self._used_filenames.clear()
        
        self.notebook.select(1)  # 結果タブに切り替え
        messagebox.showinfo("完了", "v5.4.2リネーム処理が完了しました")

    def _is_already_renamed(self, filename):
        """ファイルが既にリネーム済みかチェック（無限リネーム防止）"""
        import re
        # 4桁の数字で始まるファイル名（例：0001_、1001_、2001_など）はリネーム済み
        # _001, _002等の番号付きバリアントも対象に含める
        renamed_pattern = r'^[0-9]{4}_.*(?:_[0-9]{3})?\.pdf$'
        # __split_ファイルは処理が必要な一時ファイルなので除外しない
        if filename.startswith('__split_'):
            return False

        return bool(re.match(renamed_pattern, filename, re.IGNORECASE))

    def _update_button_states(self):
        """ボタンの状態を更新（簡素化版）"""
        # フォルダ指定による自動処理に統一したため、ボタン状態更新は不要
        pass

    def _add_result_success(self, original_file: str, new_filename: str, doc_type: str, method: str, confidence: str, matched_keywords: List[str] = None):
        """成功結果を追加（v5.4.2拡張版・YYMM Policy対応）"""
        # マッチしたキーワードの表示文字列を生成
        keywords_display = ""
        if matched_keywords:
            # キーワードリストを文字列に変換（最大3個まで表示）
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
            "-",
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

    def _export_keyword_dictionary(self):
        """キーワード辞書をエクスポート"""
        try:
            # 分類器のエクスポート機能を呼び出し
            export_path = self.classifier_v5.export_keyword_dictionary()
            
            # 成功メッセージ
            messagebox.showinfo(
                "エクスポート完了",
                f"キーワード辞書をエクスポートしました：\n{export_path}"
            )
            
            # ログに記録
            self._log(f"キーワード辞書エクスポート完了: {export_path}")
            
        except Exception as e:
            # エラーメッセージ
            messagebox.showerror(
                "エクスポートエラー",
                f"キーワード辞書のエクスポートに失敗しました：\n{str(e)}"
            )
            
            # ログに記録
            self._log(f"キーワード辞書エクスポートエラー: {str(e)}")

    def _should_exclude_blank_page(self, ocr_text: str, filename: str) -> bool:
        """空白ページかどうかを判定"""
        text = ocr_text.strip()
        
        # まず、有意味な税務コンテンツをチェック（優先）
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
        
        # 非常に短いテキストのチェック（有意味コンテンツがない場合のみ）
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
        """アプリケーション実行"""
        self._log("税務書類リネームシステム v5.4.2 起動 (Bundle PDF Auto-Split対応版)")
        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV5()
    app.run()