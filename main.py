#!/usr/bin/env python3
"""
税務書類リネームシステム v8.6.1 メインアプリケーション
Phase D-1〜D-5リファクタリング完了版
- 受信通知検出分離 (Phase D-1)
- 左側・右側処理分離 (Phase D-2, D-3)
- アーキテクチャ改善 (Phase D-5)
- 東京都設定UI改善 (v8.2.0)
- 処理モード統一・中間申告対応 (v8.5.14)
- 接頭辞UI独立化・完了表示改善 (v8.6.0)
- 受信通知検出ロジック改善 (v8.6.1)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import threading
from pathlib import Path
from typing import List, Dict, Optional
import sys
import shutil
import datetime
import tempfile
import atexit

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pdf_processor import PDFProcessor
from helpers.company_matcher import CompanyNameMatcher
from helpers.yymm_policy import resolve_yymm_by_policy, log_yymm_decision, validate_policy_result
from helpers.settings_context import UIContext, create_ui_context_from_gui, normalize_settings_input
from helpers.run_config import RunConfig, create_run_config_from_gui
from helpers.user_settings import get_user_settings_manager
from core.csv_processor import CSVProcessor
from core.classification_v5 import DocumentClassifierV5  # v5.1バグ修正版エンジンを使用
# v5.4.2: Deterministic renaming system
from core.pre_extract import create_pre_extract_engine
from core.rename_engine import create_rename_engine
from core.models import DocItemID, PreExtractSnapshot
from helpers.job_context import JobContext
# Phase 1: Modern UI theme
from ui.theme_config import apply_modern_theme
# Phase 2: Tooltip support
from ui.tooltip import create_tooltip
# Phase D-1: Receipt Detector separation
from processors.receipt_detector import ReceiptDetector
# Phase D-2, D-3: Left/Right Processor separation
from processors.left_processor import LeftProcessor
from processors.right_processor import RightProcessor
# Phase D-5: Application Orchestrator
from core.app_orchestrator import AppOrchestrator
from core.thread_manager import ThreadManager


# Tesseract/OCR機能は使用していないため削除済み
# CompanyNameMatcherはPyMuPDFのget_text()のみを使用


class TaxDocumentRenamerV5:
    """税務書類リネームシステム v8.6.1 メインクラス (Phase D-1〜D-5完了, UI改善, 受信通知検出改善)"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム")
        self.root.geometry("1200x800")

        # アプリケーションアイコン設定
        try:
            # PyInstallerでビルドされた場合のパス取得
            if getattr(sys, 'frozen', False):
                # PyInstallerでビルドされた場合
                base_path = sys._MEIPASS
            else:
                # 開発環境の場合
                base_path = os.path.dirname(__file__)

            icon_path = os.path.join(base_path, 'app_icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            pass  # アイコン読み込みエラーは無視

        # パフォーマンス最適化: ダブルバッファリングとスムーズな再描画
        try:
            # Windowsでのちらつき防止
            self.root.wm_attributes('-alpha', 0.0)  # 初期化中は非表示
        except:
            pass

        # カラースキーム定義
        self.colors = {
            'primary': '#4F46E5',      # メインの青紫
            'secondary': '#10B981',    # 成功の緑
            'danger': '#EF4444',       # エラーの赤
            'bg_card': '#FFFFFF',      # カード背景
            'bg_light': '#F9FAFB',     # 薄い背景
            'bg_window': '#E3F2FD',    # ウィンドウ背景（アイコンに合わせた薄いライトブルー）
            'text_dark': '#1F2937',    # メインテキスト
            'text_medium': '#6B7280',  # サブテキスト
            'border': '#E5E7EB'        # ボーダー
        }

        # ウィンドウ背景色設定
        self.root.configure(bg=self.colors['bg_window'])

        # v5.2 コアエンジンの初期化（ロガー付き）
        import logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # ユーザー設定管理の初期化
        self.user_settings = get_user_settings_manager()

        self.pdf_processor = PDFProcessor(logger=self.logger)
        self.csv_processor = CSVProcessor()
        self.classifier_v5 = DocumentClassifierV5(debug_mode=True)
        
        # v5.4.2: Deterministic renaming system with temporary snapshots directory
        try:
            # 一時ディレクトリを作成（ワークディレクトリ汚染回避）
            self.temp_snapshots_dir = tempfile.mkdtemp(prefix="tax_snapshots_")
            snapshots_dir = Path(self.temp_snapshots_dir)
            self.logger.info(f"一時snapshotsディレクトリ作成: {snapshots_dir}")

            # プロセス終了時の自動クリーンアップ設定
            atexit.register(self._cleanup_temp_snapshots)

        except Exception as e:
            # 一時ディレクトリ作成失敗時のフォールバック
            self.logger.warning(f"一時ディレクトリ作成失敗、フォールバック使用: {e}")
            snapshots_dir = Path("./snapshots")
            snapshots_dir.mkdir(exist_ok=True)
            self.temp_snapshots_dir = None

        self.pre_extract_engine = create_pre_extract_engine(logger=self.logger, snapshot_dir=snapshots_dir)
        # リネームエンジンは処理時に動的に作成する（処理モードに応じて）
        self.rename_engine = None
        
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

        # Phase 3: プロセスカテゴリー選択
        self.process_type_var = None  # _create_left_rename_panel()で初期化

        # Phase 1: モダンUIテーマ適用
        apply_modern_theme(self.root)

        # ボタン視認性向上スタイル設定
        self._configure_button_styles()

        # UI構築
        self._create_ui()

        # Phase D-5: オーケストレーターとスレッドマネージャーの初期化
        self.orchestrator = AppOrchestrator(self)
        self.thread_manager = ThreadManager(self.root)

        # メニューバー作成
        self._create_menubar()

        # 自治体セットのデフォルト設定
        self._setup_default_municipalities()

        # パフォーマンス最適化: フォーカスイベントの処理を最適化
        self._setup_focus_optimization()
        
        # Bundle二重処理防止: 起動時の古い__split_ファイル一括クリーンアップ
        self._cleanup_old_split_files()
    
    def _configure_button_styles(self):
        """ボタン視認性向上のためのスタイル設定"""
        style = ttk.Style()

        # フレームスタイル設定
        style.configure('TFrame',
                       background=self.colors['bg_card'])

        style.configure('TLabelFrame',
                       background=self.colors['bg_card'],
                       borderwidth=1,
                       relief='solid')
        style.configure('TLabelFrame.Label',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_dark'],
                       font=('Yu Gothic UI', 12, 'bold'))

        # Comboboxスタイル設定
        style.configure('TCombobox',
                       fieldbackground='white',
                       background='white',
                       foreground='black',
                       selectbackground='white',
                       selectforeground='black')
        style.map('TCombobox',
                 fieldbackground=[('readonly', 'white'), ('active', 'white')],
                 selectbackground=[('readonly', 'white')],
                 foreground=[('readonly', 'black'), ('active', 'black')])

        # Comboboxドロップダウンリストの背景色
        self.root.option_add('*TCombobox*Listbox*Background', 'white')
        self.root.option_add('*TCombobox*Listbox*Foreground', 'black')
        self.root.option_add('*TCombobox*Listbox*selectBackground', '#0078D7')
        self.root.option_add('*TCombobox*Listbox*selectForeground', 'white')

        # ラベルスタイル設定
        style.configure('TLabel',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_dark'],
                       font=('Yu Gothic UI', 10))

        style.configure('Heading.TLabel',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_dark'],
                       font=('Yu Gothic UI', 12, 'bold'))

        style.configure('Muted.TLabel',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_medium'],
                       font=('Yu Gothic UI', 10))

        # 大きなボタンスタイル（通常操作用）
        style.configure('Large.TButton',
                       font=('Yu Gothic UI', 11),
                       padding=10,
                       background=self.colors['primary'],
                       foreground='black')
        style.map('Large.TButton',
                 background=[('active', '#3730A3')],  # ホバー時に濃い色
                 foreground=[('!disabled', 'black'), ('disabled', '#999999')])

        # アクセントボタンスタイル（主要アクション用）
        style.configure('Accent.TButton',
                       font=('Yu Gothic UI', 12, 'bold'),
                       padding=12,
                       background=self.colors['primary'],
                       foreground='black')
        style.map('Accent.TButton',
                 background=[('active', '#3730A3')],
                 foreground=[('!disabled', 'black'), ('disabled', '#999999')])

        # セカンダリーボタンスタイル
        style.configure('Secondary.TButton',
                       font=('Yu Gothic UI', 10),
                       padding=8,
                       background=self.colors['bg_light'],
                       foreground='black')
        style.map('Secondary.TButton',
                 background=[('active', '#E5E7EB')],
                 foreground=[('!disabled', 'black'), ('disabled', '#999999')])

        # 成功ボタンスタイル（エクスポート、保存用）
        style.configure('Success.TButton',
                       font=('Yu Gothic UI', 10, 'bold'),
                       padding=8,
                       background=self.colors['secondary'],
                       foreground='black')
        style.map('Success.TButton',
                 background=[('active', '#059669')],
                 foreground=[('!disabled', 'black'), ('disabled', '#999999')])

        # 危険ボタンスタイル（クリア、削除用）
        style.configure('Danger.TButton',
                       font=('Yu Gothic UI', 10),
                       padding=8,
                       background=self.colors['danger'],
                       foreground='black')
        style.map('Danger.TButton',
                 background=[('active', '#DC2626')],
                 foreground=[('!disabled', 'black'), ('disabled', '#999999')])

        # デフォルトのTButtonスタイルも設定
        style.configure('TButton',
                       font=('Yu Gothic UI', 10),
                       padding=8,
                       background=self.colors['primary'],
                       foreground='black')
        style.map('TButton',
                 background=[('active', '#3730A3')],
                 foreground=[('!disabled', 'black'), ('disabled', '#999999')])

        # Entryスタイル
        style.configure('TEntry',
                       fieldbackground='white',
                       foreground=self.colors['text_dark'],
                       font=('Yu Gothic UI', 10))

        # Radiobutton, Checkbuttonスタイル
        style.configure('TRadiobutton',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_dark'],
                       font=('Yu Gothic UI', 10))

        style.configure('TCheckbutton',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_dark'],
                       font=('Yu Gothic UI', 10))

    def _validate_yymm_input(self, *args):
        """YYMMの入力値をリアルタイムバリデーション"""
        try:
            from helpers.yymm_policy import _normalize_yymm, _validate_yymm
            
            current_value = self.year_month_var.get()
            if not current_value:
                self.yymm_status_var.set("📋 YYMM入力待ち")
                return

            # 正規化を試行
            normalized = _normalize_yymm(current_value)
            if normalized and _validate_yymm(normalized):
                # 同一値の場合は簡素表示、変換有りの場合は詳細表示
                if current_value == normalized:
                    self.yymm_status_var.set(f"✓ 正常: {normalized}")
                else:
                    self.yymm_status_var.set(f"✓ 正常: {current_value} → {normalized}")

                # 正規化された値を自動保存
                try:
                    self.user_settings.save_yymm_value(normalized)
                except Exception as save_error:
                    self.logger.warning(f"YYMM値保存エラー: {save_error}")
            else:
                self.yymm_status_var.set(f"⚠️ 無効: {current_value} (例: 2508, 25/08, ２５０８)")

        except Exception as e:
            self.yymm_status_var.set(f"❌ エラー: {str(e)}")

    def _save_municipality_settings(self, *args):
        """市町村設定の変更を自動保存"""
        try:
            municipalities = []
            for i in range(1, 6):
                prefecture_var = getattr(self, f'prefecture_var_{i}', None)
                city_var = getattr(self, f'city_var_{i}', None)
                if prefecture_var and city_var:
                    municipalities.append({
                        "prefecture": prefecture_var.get(),
                        "city": city_var.get()
                    })
            
            self.user_settings.save_municipalities(municipalities)
        except Exception as save_error:
            self.logger.warning(f"市町村設定保存エラー: {save_error}")

    def _cleanup_temp_snapshots(self):
        """一時snapshotsディレクトリのクリーンアップ"""
        if hasattr(self, 'temp_snapshots_dir') and self.temp_snapshots_dir:
            try:
                import shutil
                shutil.rmtree(self.temp_snapshots_dir, ignore_errors=True)
                if hasattr(self, 'logger'):
                    self.logger.info(f"一時snapshotsディレクトリ削除完了: {self.temp_snapshots_dir}")
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.warning(f"一時snapshotsディレクトリ削除エラー: {e}")
                # エラーが発生してもプロセス終了を阻害しない

    def _create_ui(self):
        """UIの構築"""
        # メインフレーム（余白を増やす）
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # メインコンテンツ（タブなし）
        self.file_frame = ttk.Frame(main_frame)
        self.file_frame.pack(fill='both', expand=True)
        self._create_file_tab()

        # 処理結果・ログ用のウィンドウ参照（初期はNone）
        self.result_window = None
        self.log_window = None

        # 処理結果・ログ用のTreeview/Text widget参照
        self.result_tree = None
        self.log_text = None

        # 処理結果バッファ（ウィンドウが開かれる前の結果を保持）
        self._result_buffer = []

    def _create_file_tab(self):
        """ファイル選択タブの作成（UI改善版：右側統合レイアウト + フォルダリネーム機能）"""
        # メインフレーム作成
        main_frame = ttk.Frame(self.file_frame)
        main_frame.pack(fill='both', expand=True)

        # 左右分割コンテナ（固定幅、調整不可）
        container = ttk.Frame(main_frame)
        container.pack(fill='both', expand=True, padx=10, pady=10)
        container.columnconfigure(0, weight=1, uniform="col")
        container.columnconfigure(1, weight=1, uniform="col")

        # 左側: フォルダリネーム機能エリア
        left_container = ttk.Frame(container)
        left_container.grid(row=0, column=0, sticky='nsew', padx=(0, 5))

        # 左側タイトル
        left_title_frame = ttk.Frame(left_container)
        left_title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(left_title_frame, text="基本リネーム", style='Heading.TLabel').pack(side='left')
        ttk.Separator(left_container, orient='horizontal').pack(fill='x', pady=(0, 15))

        # 左側パネル作成（完全新規実装）
        self._create_left_rename_panel(left_container)

        # 右側: 全機能統合エリア
        right_container = ttk.Frame(container)
        right_container.grid(row=0, column=1, sticky='nsew', padx=(5, 0))

        # 右側タイトル
        right_title_frame = ttk.Frame(right_container)
        right_title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(right_title_frame, text=" 申告書リネーム", style='Heading.TLabel').pack(side='left')
        ttk.Separator(right_container, orient='horizontal').pack(fill='x', pady=(0, 15))

        # 右側フレーム
        right_frame = ttk.Frame(right_container)
        right_frame.pack(fill='both', expand=True)
        
        # 右側のレイアウト設定
        right_frame.columnconfigure(0, weight=1)

        # === 設定エリア ===
        settings_frame = ttk.LabelFrame(right_frame, text="⚙️ 設定", padding=20)
        settings_frame.pack(fill='x', pady=(0, 15), padx=20)

        # 年月設定（処理プロセスの上に移動）
        year_month_frame = ttk.Frame(settings_frame)
        year_month_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(year_month_frame, text="年月 (YYMM):").pack(side='left')
        self.year_month_var = tk.StringVar(value=self.user_settings.get_yymm_value())
        yymm_entry = ttk.Entry(year_month_frame, textvariable=self.year_month_var, width=10)
        yymm_entry.pack(side='left', padx=(10, 5))
        # Phase 2: ツールチップ追加
        create_tooltip(yymm_entry, "年月を4桁で入力（例: 2501）\nAI分類・リネーム時に使用されます")

        # YYMM設定状態表示
        self.yymm_status_var = tk.StringVar()
        self.yymm_status_label = ttk.Label(
            year_month_frame,
            textvariable=self.yymm_status_var,
            font=('Yu Gothic UI', 9)
        )
        self.yymm_status_label.pack(side='left', padx=(5, 0))
        
        # YYMMバリデーション設定（リアルタイム更新）
        self.year_month_var.trace_add('write', self._validate_yymm_input)
        self._validate_yymm_input()  # 初期バリデーション

        # 処理プロセス選択（YYMMの下）
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill='x', pady=(15, 0))

        ttk.Label(mode_frame, text="処理プロセス:", font=('Yu Gothic UI', 10)).pack(side='left')

        # 前回設定を復元（デフォルトは確定申告）
        saved_mode = self.user_settings.get_setting("process_mode", "確定申告")
        self.process_mode_var = tk.StringVar(value=saved_mode)

        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.process_mode_var,
            values=["確定申告", "中間申告"],
            state='readonly',
            width=25,
            font=('Yu Gothic UI', 10)
        )
        mode_combo.pack(side='left', padx=(10, 5))

        # 選択後にフォーカスを外して背景色をリセット & 設定を保存
        def on_combobox_select(event):
            event.widget.selection_clear()
            self.root.focus()
            # 設定を保存
            self.user_settings.save_setting("process_mode", self.process_mode_var.get())

        mode_combo.bind('<<ComboboxSelected>>', on_combobox_select)
        create_tooltip(mode_combo, "処理モードを選択\n・確定申告: 確定申告書類の処理\n・中間申告: 中間申告書類の処理")

        # 自治体設定
        municipality_frame = ttk.LabelFrame(right_frame, text="🏢 自治体設定", padding=20)
        municipality_frame.pack(fill='x', pady=(15, 15), padx=20)
        self._create_municipality_settings(municipality_frame)

        # リネーム実行ボタン（一番下）
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill='x', pady=(0, 0), padx=20)

        self.right_execute_btn = tk.Button(
            button_frame,
            text="🔄 リネーム実行",
            command=self._start_folder_batch_processing_direct,
            font=('Yu Gothic UI', 11, 'bold'),
            bg='#4B5563',
            fg='white',
            relief='flat',
            padx=10,
            pady=10,
            cursor='hand2',
            activebackground='#374151',
            activeforeground='white'
        )
        self.right_execute_btn.pack(fill='x')
        create_tooltip(self.right_execute_btn,
                      "フォルダを選択してAI分類・リネーム実行\n税務書類を自動分類して適切なファイル名に変換します")
        
        # 進捗表示ラベル（右側）
        right_progress_frame = ttk.Frame(right_frame)
        right_progress_frame.pack(fill='x', pady=(10, 0), padx=20)
        
        self.right_progress_var = tk.StringVar(value="")
        self.right_progress_label = ttk.Label(
            right_progress_frame,
            textvariable=self.right_progress_var,
            font=('Yu Gothic UI', 9),
            foreground='#6B7280'
        )
        self.right_progress_label.pack(side='left')

    def _create_left_rename_panel(self, parent):
        """左側フォルダリネームパネル作成（右側と同じUI構造）"""
        # === 設定エリア ===
        settings_frame = ttk.LabelFrame(parent, text="⚙️ 設定", padding=20)
        settings_frame.pack(fill='x', pady=(0, 15), padx=20)

        # 年月設定（処理プロセスの上）
        year_month_frame = ttk.Frame(settings_frame)
        year_month_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(year_month_frame, text="年月 (YYMM):").pack(side='left')

        # 前回設定を復元
        saved_yymm = self.user_settings.get_setting("left_yymm_value", "")
        self.left_yymm_var = tk.StringVar(value=saved_yymm)

        yymm_entry = ttk.Entry(year_month_frame, textvariable=self.left_yymm_var, width=10)
        yymm_entry.pack(side='left', padx=(10, 5))
        create_tooltip(yymm_entry, "年月を4桁で入力（例: 2501）\nフォルダリネーム時に使用されます")

        # YYMM設定状態表示
        self.left_yymm_status_var = tk.StringVar(value="📋 YYMM入力待ち" if not saved_yymm else f"✓ 正常: {saved_yymm}")
        self.left_yymm_status_label = ttk.Label(
            year_month_frame,
            textvariable=self.left_yymm_status_var,
            font=('Yu Gothic UI', 9)
        )
        self.left_yymm_status_label.pack(side='left', padx=(5, 0))

        # YYMMバリデーション設定（リアルタイム更新）
        self.left_yymm_var.trace_add('write', self._left_validate_yymm)
        self._left_validate_yymm()  # 初期バリデーション

        # 処理プロセス選択（YYMMの下）
        process_frame = ttk.Frame(settings_frame)
        process_frame.pack(fill='x', pady=(15, 0))

        ttk.Label(process_frame, text="処理プロセス:", font=('Yu Gothic UI', 10)).pack(side='left')

        # 前回設定を復元（デフォルトは源泉税）
        saved_process = self.user_settings.get_setting("process_type", "源泉税(帳票:複数、顧客:複数)")
        # 旧設定との互換性を保つ
        process_mapping = {
            "源泉税": "源泉税(帳票:複数、顧客:複数)",
            "申請届出（国税のみ）": "申請届出(帳票:複数、顧客:単一)※国税のみ対応",
            "法定調書": "法定調書(帳票:単一、顧客:複数)",
            "給与支払報告書": "給与支払報告書(帳票:単一、顧客:複数)",
            "償却資産申告書": "償却資産申告書(帳票:単一、顧客:複数)"
        }
        if saved_process in process_mapping:
            saved_process = process_mapping[saved_process]
        self.process_type_var = tk.StringVar(value=saved_process)

        process_combo = ttk.Combobox(
            process_frame,
            textvariable=self.process_type_var,
            values=[
                "源泉税(帳票:複数、顧客:複数)",
                "申請届出(帳票:複数、顧客:単一)※国税のみ対応",
                "法定調書(帳票:単一、顧客:複数)",
                "給与支払報告書(帳票:単一、顧客:複数)",
                "償却資産申告書(帳票:単一、顧客:複数)"
            ],
            state='readonly',
            width=35,
            font=('Yu Gothic UI', 10)
        )
        process_combo.pack(side='left', padx=(10, 5))
        create_tooltip(process_combo,
                      "処理プロセスを選択\n・源泉税(帳票:複数、顧客:複数)\n・申請届出(帳票:複数、顧客:単一)※国税のみ対応\n・法定調書(帳票:単一、顧客:複数)\n・給与支払報告書(帳票:単一、顧客:複数)\n・償却資産申告書(帳票:単一、顧客:複数)")

        # 英語半角変換オプション（settings_frame内の最後）
        normalize_frame_in_settings = ttk.Frame(settings_frame)
        normalize_frame_in_settings.pack(fill='x', pady=(15, 0))

        # 前回設定を復元
        saved_normalize = self.user_settings.get_setting("normalize_english", False)
        self.normalize_english_var = tk.BooleanVar(value=saved_normalize)

        normalize_checkbox = ttk.Checkbutton(
            normalize_frame_in_settings,
            text="英語を半角に変換（例：Ｓｔａｎｄａｒｄ  →  Standard）",
            variable=self.normalize_english_var,
            command=lambda: self.user_settings.save_setting("normalize_english", self.normalize_english_var.get())
        )
        normalize_checkbox.pack(side='left', padx=(0, 0))
        create_tooltip(normalize_checkbox, "会社名の全角英語を半角に変換します\n例：Ｓｔａｎｄａｒｄ  →  Standard")

        # === 接頭辞設定エリア（独立） ===
        prefix_frame = ttk.LabelFrame(parent, text="📝 接頭辞設定（オプション）", padding=15)
        prefix_frame.pack(fill='x', pady=(15, 15), padx=20)
        
        # 本票
        main_prefix_row = ttk.Frame(prefix_frame)
        main_prefix_row.pack(fill='x', pady=(0, 8))
        
        ttk.Label(main_prefix_row, text="本票:", width=8).pack(side='left')
        
        # 前回設定を復元（デフォルトは空欄）
        saved_main_prefix = self.user_settings.get_setting("left_main_prefix_override", "")
        self.left_main_prefix_var = tk.StringVar(value=saved_main_prefix)
        
        main_prefix_entry = ttk.Entry(main_prefix_row, textvariable=self.left_main_prefix_var, width=12)
        main_prefix_entry.pack(side='left', padx=(5, 5))
        create_tooltip(main_prefix_entry, "本票ファイルの接頭辞を指定\n空欄の場合は処理プロセスに応じた既定値を使用\n例: 01, 0001")
        
        ttk.Label(main_prefix_row, text="（空欄で既定値）", font=('Yu Gothic UI', 8), foreground='#6B7280').pack(side='left')
        
        # 受信通知
        receipt_prefix_row = ttk.Frame(prefix_frame)
        receipt_prefix_row.pack(fill='x', pady=(0, 0))
        
        ttk.Label(receipt_prefix_row, text="受信通知:", width=8).pack(side='left')
        
        # 前回設定を復元（デフォルトは空欄）
        saved_receipt_prefix = self.user_settings.get_setting("left_receipt_prefix_override", "")
        self.left_receipt_prefix_var = tk.StringVar(value=saved_receipt_prefix)
        
        receipt_prefix_entry = ttk.Entry(receipt_prefix_row, textvariable=self.left_receipt_prefix_var, width=12)
        receipt_prefix_entry.pack(side='left', padx=(5, 5))
        create_tooltip(receipt_prefix_entry, "受信通知ファイルの接頭辞を指定\n空欄の場合は処理プロセスに応じた既定値を使用\n例: 02, 9001")
        
        ttk.Label(receipt_prefix_row, text="（空欄で既定値）", font=('Yu Gothic UI', 8), foreground='#6B7280').pack(side='left')
        
        # 入力値を保存
        def save_prefix_settings(*args):
            self.user_settings.save_setting("left_main_prefix_override", self.left_main_prefix_var.get())
            self.user_settings.save_setting("left_receipt_prefix_override", self.left_receipt_prefix_var.get())
        
        self.left_main_prefix_var.trace_add('write', save_prefix_settings)
        self.left_receipt_prefix_var.trace_add('write', save_prefix_settings)

        # 処理プロセスに応じて接頭辞を自動設定する関数
        def update_prefixes_based_on_process():
            process = self.process_type_var.get()
            # 設定を保存（接頭辞はユーザー入力を優先）
            self.user_settings.save_setting("process_type", process)

        # 初期化（接頭辞はユーザー入力値を保持）

        # 選択後にフォーカスを外して背景色をリセット & 設定を保存
        def on_process_change(event):
            update_prefixes_based_on_process()
            event.widget.selection_clear()
            self.root.focus()

        process_combo.bind('<<ComboboxSelected>>', on_process_change)



        # リネーム実行ボタン（一番下）
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=(0, 0), padx=20)

        self.left_execute_btn = tk.Button(
            button_frame,
            text="🔄 リネーム実行",
            command=self._left_execute,
            font=('Yu Gothic UI', 11, 'bold'),
            bg='#4B5563',
            fg='white',
            disabledforeground='white',
            relief='flat',
            padx=10,
            pady=10,
            cursor='hand2',
            activebackground='#374151',
            activeforeground='white'
        )
        self.left_execute_btn.pack(fill='x')
        create_tooltip(self.left_execute_btn,
                      "フォルダを選択してリネーム実行\nフォルダ名を自動で標準化されたファイル名に変換します")
        
        # 進捗表示ラベル
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill='x', pady=(10, 0), padx=20)
        
        self.left_progress_var = tk.StringVar(value="")
        self.left_progress_label = ttk.Label(
            progress_frame,
            textvariable=self.left_progress_var,
            font=('Yu Gothic UI', 9),
            foreground='#6B7280'
        )
        self.left_progress_label.pack(side='left')

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

    def _show_result_window(self):
        """処理結果ウィンドウを表示"""
        if self.result_window and self.result_window.winfo_exists():
            # 既に開いている場合は前面に表示
            self.result_window.lift()
            self.result_window.focus_force()
            return

        # 新しいウィンドウを作成
        self.result_window = tk.Toplevel(self.root)
        self.result_window.title("処理結果")
        self.result_window.geometry("1000x600")

        # 結果表示用のTreeview
        ttk.Label(self.result_window, text="処理結果", font=('Yu Gothic UI', 12, 'bold')).pack(pady=(10, 10))

        # Treeviewとスクロールバー
        tree_frame = ttk.Frame(self.result_window)
        tree_frame.pack(fill='both', expand=True, padx=10)

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

        # バッファに溜まっている結果を表示
        print(f"[DEBUG] _show_result_window called")
        print(f"[DEBUG] Has _result_buffer: {hasattr(self, '_result_buffer')}")
        if hasattr(self, '_result_buffer'):
            print(f"[DEBUG] Buffer size: {len(self._result_buffer)}")

        if hasattr(self, '_result_buffer') and self._result_buffer:
            print(f"[DEBUG] Adding {len(self._result_buffer)} results to tree")
            for result_data in self._result_buffer:
                self.result_tree.insert('', 'end', values=result_data['values'])
                print(f"[DEBUG] Added: {result_data['values'][0]}")
        else:
            print(f"[DEBUG] No results in buffer to display")

        # 結果操作ボタン
        result_button_frame = ttk.Frame(self.result_window)
        result_button_frame.pack(fill='x', pady=15, padx=10)

        ttk.Button(result_button_frame, text="出力フォルダを開く",
                  command=self._open_output_folder,
                  style='Secondary.TButton', width=18).pack(side='left', padx=(0, 8))
        ttk.Button(result_button_frame, text="結果をクリア",
                  command=self._clear_results,
                  style='Danger.TButton', width=15).pack(side='left', padx=8)

    def _show_log_window(self):
        """ログウィンドウを表示"""
        if self.log_window and self.log_window.winfo_exists():
            # 既に開いている場合は前面に表示
            self.log_window.lift()
            self.log_window.focus_force()
            return

        # 新しいウィンドウを作成
        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("処理ログ・デバッグ")
        self.log_window.geometry("900x500")

        ttk.Label(self.log_window, text="処理ログ・デバッグ情報", font=('Yu Gothic UI', 12, 'bold')).pack(pady=(10, 10))

        # ログ表示エリア
        log_text_frame = ttk.Frame(self.log_window)
        log_text_frame.pack(fill='both', expand=True, padx=10)

        self.log_text = tk.Text(log_text_frame, wrap='word', font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')

        # バッファに溜まっているログを表示
        if hasattr(self, '_log_buffer') and self._log_buffer:
            for entry in self._log_buffer:
                self.log_text.insert(tk.END, entry)
            self.log_text.see(tk.END)

        # ログ操作ボタン
        log_button_frame = ttk.Frame(self.log_window)
        log_button_frame.pack(fill='x', pady=15, padx=10)

        ttk.Button(log_button_frame, text="🗑️ ログクリア",
                  command=self._clear_log,
                  style='Danger.TButton', width=15).pack(side='left', padx=(0, 8))
        ttk.Button(log_button_frame, text="📋 ログ全体をコピー",
                  command=self._copy_all_log,
                  style='Success.TButton', width=18).pack(side='left', padx=8)

    def _create_municipality_settings(self, parent_frame):
        """自治体設定UIの作成"""
        # 47都道府県リスト
        self.prefectures = [
            "", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]

        # セット1-5のStringVar変数を初期化
        for i in range(1, 6):
            setattr(self, f'prefecture_var_{i}', tk.StringVar())
            setattr(self, f'city_var_{i}', tk.StringVar())
        
        # UI作成
        for i in range(1, 6):
            set_frame = ttk.Frame(parent_frame)
            set_frame.pack(fill='x', pady=2)

            # セット番号ラベル（幅を統一）
            ttk.Label(set_frame, text=f"セット{i}:", width=8).pack(side='left')

            prefecture_var = getattr(self, f'prefecture_var_{i}')
            city_var = getattr(self, f'city_var_{i}')

            # 都道府県はCombobox（プルダウン）で選択
            prefecture_combo = ttk.Combobox(set_frame, textvariable=prefecture_var,
                                           values=self.prefectures, width=10, state='readonly')
            prefecture_combo.pack(side='left', padx=2)

            # Combobox選択後の黒背景問題を修正
            def fix_combobox_selection(event):
                event.widget.selection_clear()
            prefecture_combo.bind('<<ComboboxSelected>>', fix_combobox_selection)

            # 市区町村欄
            city_entry = ttk.Entry(set_frame, textvariable=city_var, width=12)
            city_entry.pack(side='left', padx=2)

            # 市町村設定の変更監視を追加
            prefecture_var.trace_add('write', self._save_municipality_settings)
            if i != 1:
                city_var.trace_add('write', self._save_municipality_settings)
            else:
                # セット1も保存監視（東京都以外の場合に必要）
                city_var.trace_add('write', self._save_municipality_settings)

        # 東京都の設定に関する案内ボックスを追加
        info_frame = ttk.Frame(parent_frame)
        info_frame.pack(fill='x', pady=(10, 5))

        # 背景色付きの案内ボックス（アプリに馴染んだ色）
        info_box = tk.Frame(info_frame, bg=self.colors['bg_light'], relief='solid', borderwidth=1, highlightthickness=1, highlightbackground=self.colors['border'])
        info_box.pack(fill='x', padx=5)

        # テキストを含む内部フレーム
        content_frame = tk.Frame(info_box, bg=self.colors['bg_light'])
        content_frame.pack(fill='x', padx=10, pady=8)

        # 案内テキスト
        info_text_1 = tk.Label(content_frame, text="• 東京都特別区（23区）: セット1に優先して設定し、市町村欄は空欄にして下さい",
                               bg=self.colors['bg_light'], fg=self.colors['text_medium'], anchor='w', font=('', 9), wraplength=550, justify='left')
        info_text_1.pack(fill='x')

        info_text_3 = tk.Label(content_frame, text="• 市区町村の入力形式(23区以外): 「八王子市」「横浜市」「大阪市」「白川村」など",
                               bg=self.colors['bg_light'], fg=self.colors['text_medium'], anchor='w', font=('', 9), wraplength=550, justify='left')
        info_text_3.pack(fill='x')

    # v8.5.12: 東京都でも市町村入力可能にするため、_update_city_field_stateメソッドを削除

    def _setup_default_municipalities(self):
        """ユーザー設定から自治体設定を復元"""
        saved_municipalities = self.user_settings.get_municipalities()

        for i, municipality_data in enumerate(saved_municipalities, 1):
            if i <= 5:
                prefecture_var = getattr(self, f'prefecture_var_{i}', None)
                city_var = getattr(self, f'city_var_{i}', None)
                if prefecture_var and city_var:
                    prefecture_var.set(municipality_data.get("prefecture", ""))
                    city_var.set(municipality_data.get("city", ""))

    def _setup_focus_optimization(self):
        """フォーカスイベント時の再描画最適化"""
        def on_focus_in(event):
            """ウィンドウがフォーカスを取得した時の処理"""
            # 一時的に再描画を抑制してからまとめて更新
            self.root.update_idletasks()

        def on_visibility(event):
            """ウィンドウの可視性が変更された時の処理"""
            if event.state == 'VisibilityUnobscured':
                # ウィンドウが完全に表示される時のみ更新
                self.root.update_idletasks()

        # イベントバインディング
        self.root.bind('<FocusIn>', on_focus_in)
        self.root.bind('<Visibility>', on_visibility)

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
            # 直近で処理したフォルダを記録
            self._last_processed_folder = folder

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
        """v5.4.5 フォルダ一括処理開始（REQ-001/002対応）"""
        # フォルダが指定されていない場合はダイアログで選択
        if not source_folder:
            source_folder = filedialog.askdirectory(title="処理対象フォルダを選択（PDF・CSVファイルが含まれるフォルダ）")
            if not source_folder:
                return
        
        # 【REQ-001】階層制限: 選択フォルダ直下のファイルのみを処理対象とする
        # 【REQ-002】CSV対応: .csv拡張子も処理対象に追加
        target_files = []
        try:
            for file in os.listdir(source_folder):
                file_path = os.path.join(source_folder, file)
                # ファイルのみを対象（ディレクトリは除外）
                if os.path.isfile(file_path):
                    # PDFファイル（既存）
                    if file.lower().endswith('.pdf') and not file.startswith('__split_'):
                        target_files.append(file_path)
                    # CSVファイル（新規追加）
                    elif file.lower().endswith('.csv'):
                        target_files.append(file_path)
        except Exception as e:
            messagebox.showerror("エラー", f"フォルダの読み込みに失敗しました:\n{e}")
            return
        
        if not target_files:
            messagebox.showwarning("警告", f"選択されたフォルダにPDF・CSVファイルが見つかりませんでした:\n{source_folder}")
            return
        
        # 処理中の場合はスキップ
        if self.rename_processing:
            messagebox.showwarning("警告", "処理中です")
            return
        
        # 自治体セットを取得し、キャッシュをクリア（新しい処理開始）
        self._cached_municipality_sets = None  # 前回のキャッシュをクリア
        self.municipality_sets = self._get_municipality_sets()
        
        # YYMMフォルダを作成（処理モードに応じてフォルダ名を生成）
        yymm = self.year_month_var.get()
        process_mode = self.process_mode_var.get()

        # 処理モードに応じてフォルダ名を生成
        if process_mode == "確定申告":
            folder_name = f"{yymm}_確定申告"
        elif process_mode == "中間申告":
            folder_name = f"{yymm}_中間申告"
        else:
            folder_name = yymm

        base_output_folder = os.path.join(source_folder, folder_name)

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
        
        # 【REQ-001】処理済みファイル追跡機能の初期化
        if not hasattr(self, '_processed_files_this_session'):
            self._processed_files_this_session = set()
        else:
            self._processed_files_this_session.clear()
        
        # バックグラウンド処理開始
        self.rename_processing = True
        self._update_button_states()
        
        # 右側の進捗表示を更新
        self.right_progress_var.set("処理中...")
        
        pdf_count = len([f for f in target_files if f.lower().endswith('.pdf')])
        csv_count = len([f for f in target_files if f.lower().endswith('.csv')])
        
        self._log(f"フォルダ一括処理開始: {len(target_files)}件のファイルを処理")
        self._log(f"  - PDFファイル: {pdf_count}件")
        self._log(f"  - CSVファイル: {csv_count}件")
        self._log(f"処理対象フォルダ: {source_folder}")
        self._log(f"出力先: {output_folder}")
        self._log(f"[REQ-001] 階層制限: 直下ファイルのみ処理")
        
        thread = threading.Thread(
            target=self._folder_batch_processing_background,
            args=(target_files, output_folder),
            daemon=True
        )
        thread.start()

    
    def _start_folder_batch_processing_direct(self):
        """UI改善版：Bundle Auto-Split常時有効の直接処理"""
        # フォルダ選択ダイアログ
        from tkinter import filedialog

        source_folder = filedialog.askdirectory(
            title="処理対象フォルダを選択（PDF・CSVファイルが含まれるフォルダ）"
        )
        if not source_folder:
            return

        # 処理モードを取得してリネームエンジンと分類エンジンを作成
        process_mode = self.process_mode_var.get()
        self._log(f"処理モード: {process_mode}")
        self.rename_engine = create_rename_engine(logger=self.logger, process_mode=process_mode)
        # 分類エンジンも処理モードで再初期化
        self.classifier_v5 = DocumentClassifierV5(debug_mode=True, process_mode=process_mode)

        # Bundle Auto-Split設定を常時有効として処理開始
        self._log("UI改善版：Bundle Auto-Split常時有効で処理開始")

        # 既存の処理メソッドを呼び出し（Bundle Auto-Split常時有効）
        self._start_folder_batch_processing(source_folder)

    def _folder_batch_processing_background(self, target_files, output_folder):
        """フォルダ一括処理のバックグラウンド処理（v5.4.5 REQ-001/002対応）"""
        try:
            total_files = len(target_files)
            processed_files = 0
            success_count = 0  # 【追加】成功カウント
            error_count = 0    # 【追加】エラーカウント
            skip_count = 0     # 【追加】スキップカウント

            for i, file_path in enumerate(target_files, 1):
                filename = os.path.basename(file_path)

                # 【REQ-001】処理済みファイル追跡による重複処理完全排除
                if file_path in self._processed_files_this_session:
                    self.root.after(0, lambda f=filename: self._log(f"[REQ-001] 既処理済みスキップ: {f}"))
                    skip_count += 1
                    continue

                # 処理済みファイルとして記録
                self._processed_files_this_session.add(file_path)
                processed_files += 1  # 【修正】処理試行カウント

                self.root.after(0, lambda f=filename, i=i, total=total_files: self._log(f"処理中 ({i}/{total}): {f}"))

                try:
                    # ファイル拡張子による処理分岐
                    if file_path.lower().endswith('.pdf'):
                        # PDF処理（既存ロジック）
                        success = self._process_pdf_file(file_path, output_folder)
                    elif file_path.lower().endswith('.csv'):
                        # 【REQ-002】CSV処理（新規実装）
                        success = self._process_csv_file(file_path, output_folder)
                    else:
                        self.root.after(0, lambda f=filename: self._log(f"未対応ファイル形式: {f}"))
                        skip_count += 1
                        continue

                    if success:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    self.root.after(0, lambda err=str(e), f=filename: self._log(f"ファイル処理エラー {f}: {err}"))
                    error_count += 1
                    continue

            # 【修正】処理統計を保存（ログ表示なし）
            self._last_processing_stats = {
                'total': total_files,
                'success': success_count,
                'error': error_count,
                'skip': skip_count
            }

        except Exception as e:
            self._log(f"v5.4.5リネーム処理エラー: {str(e)}")
        finally:
            self.root.after(0, self._rename_processing_finished)

    def _process_pdf_file(self, file_path: str, output_folder: str) -> bool:
        """PDF ファイル処理（既存ロジック）"""
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
            # Phase 1 診断: Bundle分割チェックのログ追加
            filename_for_log = os.path.basename(file_path)
            self.root.after(0, lambda f=filename_for_log: self._log(f"[DEBUG] Bundle分割チェック開始: {f}"))
            
            split_result = self.pdf_processor.maybe_split_pdf(
                input_pdf_path=file_path,
                out_dir=output_folder,
                force=False,
                processing_callback=None
            )
            
            if split_result['success']:
                # Bundle分割が成功した場合
                filename = os.path.basename(file_path)
                self.root.after(0, lambda f=filename: self._log(f"[DEBUG] Bundle分割成功: {f}"))
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
                                split_filename = os.path.basename(split_file_path)
                                self.root.after(0, lambda sf=split_filename: self._log(f"分割後ファイル処理完了: {sf}"))
                            
                            # 一時ファイル削除処理
                            if os.path.exists(split_file_path) and os.path.basename(split_file_path).startswith("__split_"):
                                try:
                                    # 一時ファイルを削除（未分類移動せず）
                                    os.remove(split_file_path)
                                    split_filename = os.path.basename(split_file_path)
                                    self.root.after(0, lambda sf=split_filename: self._log(f"[cleanup] 一時ファイル削除: {sf}"))
                                except Exception as cleanup_error:
                                    split_filename = os.path.basename(split_file_path)
                                    error_msg = str(cleanup_error)
                                    self.root.after(0, lambda sf=split_filename, err=error_msg:
                                                   self._log(f"[cleanup] 一時ファイル削除失敗 {sf}: {err}"))
                            
                        except Exception as e:
                            split_filename = os.path.basename(split_file_path)
                            error_msg = str(e)
                            self.root.after(0, lambda err=error_msg, sf=split_filename: self._log(f"分割後ファイル処理エラー {sf}: {err}"))
                            # エラー時は一時ファイルを削除
                            try:
                                if os.path.exists(split_file_path):
                                    os.remove(split_file_path)
                                    split_filename = os.path.basename(split_file_path)
                                    self.root.after(0, lambda sf=split_filename: self._log(f"[error-recovery] エラーファイルを削除: {sf}"))
                            except Exception as recovery_error:
                                error_msg = str(recovery_error)
                                self.root.after(0, lambda err=error_msg: self._log(f"[error-recovery] ファイル削除失敗: {err}"))
                
                return True
            else:
                # Bundle分割不要またはスキップ
                filename = os.path.basename(file_path)
                self.root.after(0, lambda f=filename: self._log(f"[DEBUG] Bundle分割スキップ（通常ファイル処理）: {f}"))
                # 通常の単一ファイル処理 - スナップショットを作成してから処理
                user_yymm = self._resolve_yymm_with_policy(file_path, None)
                snapshot = self.pre_extract_engine.build_snapshot(file_path, user_provided_yymm=user_yymm, ui_context=ui_context.to_dict())
                return self._process_single_file_v5_with_snapshot(file_path, output_folder, snapshot)
                
        except Exception as e:
            filename = os.path.basename(file_path)
            error_msg = str(e)
            self.root.after(0, lambda err=error_msg, f=filename: self._log(f"PDF処理エラー {f}: {err}"))
            return False

    def _process_csv_file(self, file_path: str, output_folder: str) -> bool:
        """【REQ-002】CSV ファイル処理（仕訳データ対応）

        【修正】すべてのCSVファイルを5006_仕訳データとして処理
        ファイル名や内容に関わらず、拡張子が.csvの場合は5006として固定分類
        """
        try:
            filename = os.path.basename(file_path)

            # 【修正】すべてのCSVファイルを5006_仕訳データとして処理
            # ファイル名や内容による判定を行わず、常に5006として処理
            yymm = self.year_month_var.get()
            new_filename = f"5006_仕訳データ_{yymm}.csv"
            output_path = os.path.join(output_folder, new_filename)

            # 重複回避処理
            output_path = self._generate_unique_filename(output_path)

            # ファイルコピー
            import shutil
            # 【修正】shutil.copy()を使用して新しいファイルとして作成（タイムスタンプを現在時刻に）
            # copy2はメタデータ（タイムスタンプ）を保持するが、copyは保持しない
            shutil.copy(file_path, output_path)

            self.root.after(0, lambda f=filename, nf=os.path.basename(output_path):
                           self._log(f"[CSV] 仕訳データ処理完了: {f} → {nf}"))
            return True

        except Exception as e:
            filename = os.path.basename(file_path)
            error_msg = str(e)
            self.root.after(0, lambda err=error_msg, f=filename: self._log(f"CSV処理エラー {f}: {err}"))
            return False

    def _is_csv_journal(self, file_path: str) -> bool:
        """CSVファイルが仕訳帳かどうかを判定"""
        try:
            import csv
            import codecs
            
            # ファイル名による判定
            filename = os.path.basename(file_path).lower()
            if '仕訳' in filename or 'journal' in filename:
                return True
            
            # CSV内容による判定（ヘッダー行を確認）
            encodings = ['utf-8', 'shift_jis', 'cp932', 'utf-8-sig']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.reader(f)
                        header = next(reader, None)
                        if header:
                            header_text = ''.join(header).lower()
                            # 仕訳帳特有のキーワードを検索
                            journal_keywords = ['借方', '貸方', 'debit', 'credit', '勘定科目', '仕訳']
                            if any(keyword in header_text for keyword in journal_keywords):
                                return True
                    break  # 正常に読めたらループを抜ける
                except UnicodeDecodeError:
                    continue  # 次のエンコーディングを試す
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False

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
            # 【修正】毎回UIから最新のYYMM値を取得してRunConfigを更新
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
        
        # テキスト抽出（1ページ目のみ - 分類には十分）
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            # 【修正】1ページ目のみ抽出して処理速度を改善
            if len(doc) > 0:
                text = doc[0].get_text()
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
            # 【修正】shutil.copy()を使用して新しいファイルとして作成（タイムスタンプを現在時刻に）
            # copy2はメタデータ（タイムスタンプ）を保持するが、copyは保持しない
            shutil.copy(file_path, output_path)
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
        
        # 分類実行（1ページ目のみ抽出）
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            # 【修正】1ページ目のみ抽出して処理速度を改善
            if len(doc) > 0:
                text = doc[0].get_text()
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
                self._log(f"[v5.4.2] 市町村連番適用: {classification_result.original_doc_type_code} → {final_document_type}")
            else:
                self._log(f"[v5.4.2] 分類結果: {final_document_type}")
        else:
            self._log(f"[v5.4.2] 分類結果: {final_document_type}")
        
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
            # 【修正】shutil.copy()を使用して新しいファイルとして作成（タイムスタンプを現在時刻に）
            # copy2はメタデータ（タイムスタンプ）を保持するが、copyは保持しない
            shutil.copy(file_path, output_path)
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
            self._log("[ERROR] 分類に失敗しました")
            return

        self._log("=" * 60)
        self._log("[詳細分類結果]")
        self._log(f"[ファイル名] {filename}")
        
        # 表示は最終使用コード（ファイル名と一致）を使用
        display_document_type = classification_result.original_doc_type_code if (
            hasattr(classification_result, 'original_doc_type_code') and 
            classification_result.original_doc_type_code
        ) else classification_result.document_type
        
        self._log(f"[分類] 分類結果: {display_document_type}")
        self._log(f"[分類] 信頼度: {classification_result.confidence:.2f}")
        self._log(f"[分類] 判定方法: {classification_result.classification_method}")
        
        # 自治体変更版がある場合のみ表示
        if (hasattr(classification_result, 'original_doc_type_code') and
            classification_result.original_doc_type_code and
            classification_result.original_doc_type_code != classification_result.document_type):
            self._log(f"[自治体変更版] {classification_result.document_type}")

        # マッチしたキーワードの詳細
        if classification_result.matched_keywords:
            self._log(f"[キーワード] {classification_result.matched_keywords}")

        # デバッグステップの詳細（利用可能な場合）
        if hasattr(classification_result, 'debug_steps') and classification_result.debug_steps:
            self._log("[分類ステップ詳細]")
            for i, step in enumerate(classification_result.debug_steps[:3], 1):  # 上位3件のみ表示
                self._log(f"  {i}. {step.document_type}: スコア {step.score:.1f}, キーワード {step.matched_keywords}")
                if step.excluded:
                    self._log(f"     [除外] 理由: {step.exclude_reason}")
        
        # テキスト内容の一部を表示（デバッグ用）
        if text:
            preview = text[:200] + "..." if len(text) > 200 else text
            self._log(f"[抽出テキスト（先頭200字）] {preview}")
        
        # 処理ログがある場合は重要な部分のみ表示
        if hasattr(classification_result, 'processing_log') and classification_result.processing_log:
            important_logs = [log for log in classification_result.processing_log if
                            "最優先AND条件一致" in log or "自治体連番適用" in log or "強制判定" in log]
            if important_logs:
                self._log("[重要な処理ログ]")  # 【修正】絵文字を削除してエンコーディングエラーを回避
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
        """【修正】重複しないファイル名を生成（履歴保存機能削除）"""
        # 【修正】ファイル履歴機能を削除し、シンプルな重複チェックのみ実行
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
        
        # 右側の進捗表示を更新
        self.right_progress_var.set("完了")

        # メッセージボックスをタブ切り替えの前に表示（ウィンドウが隠れないように）
        messagebox.showinfo("完了", "処理が完了しました")
        self.notebook.select(1)  # 結果タブに切り替え

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

        # 結果データを作成
        result_data = {
            'type': 'success',
            'values': (
                os.path.basename(original_file),
                new_filename,
                doc_type,
                method,
                confidence,
                keywords_display,
                "成功"  # 絵文字を除去
            )
        }

        # バッファに追加
        if not hasattr(self, '_result_buffer'):
            self._result_buffer = []
        self._result_buffer.append(result_data)

        # デバッグログ
        print(f"[DEBUG] Result added to buffer. Buffer size: {len(self._result_buffer)}")
        print(f"[DEBUG] Result: {result_data['values'][0]} -> {result_data['values'][1]}")

        # 結果ウィンドウが存在する場合はTreeviewに追加
        if self.result_window and self.result_window.winfo_exists() and self.result_tree:
            try:
                self.result_tree.insert('', 'end', values=result_data['values'])
                print(f"[DEBUG] Result added to tree widget")
            except tk.TclError as e:
                print(f"[DEBUG] Failed to add result to tree: {e}")

    def _add_result_error(self, original_file: str, error: str):
        """エラー結果を追加"""
        # 結果データを作成
        result_data = {
            'type': 'error',
            'values': (
                os.path.basename(original_file),
                "-",
                "-",
                "-",
                "0.00",
                "-",
                f"エラー: {error}"  # 絵文字を除去
            )
        }

        # バッファに追加
        if not hasattr(self, '_result_buffer'):
            self._result_buffer = []
        self._result_buffer.append(result_data)

        # 結果ウィンドウが存在する場合はTreeviewに追加
        if self.result_window and self.result_window.winfo_exists() and self.result_tree:
            try:
                self.result_tree.insert('', 'end', values=result_data['values'])
            except tk.TclError as e:
                print(f"[DEBUG] Failed to add error to tree: {e}")

    def _open_output_folder(self):
        """直近で処理したフォルダを開く"""
        if hasattr(self, '_last_processed_folder') and self._last_processed_folder:
            import os
            import subprocess
            if os.path.exists(self._last_processed_folder):
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(self._last_processed_folder)
                    elif os.name == 'posix':  # macOS/Linux
                        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', self._last_processed_folder])
                    self._log(f"出力フォルダを開きました: {self._last_processed_folder}")
                except Exception as e:
                    messagebox.showerror("エラー", f"フォルダを開けませんでした:\n{str(e)}")
            else:
                messagebox.showwarning("警告", "出力フォルダが見つかりません")
        else:
            messagebox.showinfo("情報", "まだ処理が実行されていません")

    def _clear_results(self):
        """結果をクリア"""
        if self.result_tree and hasattr(self.result_tree, 'get_children'):
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)

    def _log(self, message: str):
        """ログメッセージ追加"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        # ログバッファに追加（ウィンドウが開かれる前のログを保持）
        if not hasattr(self, '_log_buffer'):
            self._log_buffer = []
        self._log_buffer.append(log_entry)

        # ログウィンドウが存在する場合はログに追記
        if self.log_text and hasattr(self.log_text, 'insert'):
            self.root.after(0, lambda: self.log_text.insert(tk.END, log_entry))
            self.root.after(0, lambda: self.log_text.see(tk.END))

        # コンソールにも出力
        print(log_entry.strip())

    def _clear_log(self):
        """ログクリア"""
        if self.log_text and hasattr(self.log_text, 'delete'):
            self.log_text.delete(1.0, tk.END)

    def _copy_all_log(self):
        """ログ全体をクリップボードにコピー"""
        if hasattr(self, 'log_text') and self.log_text:
            log_content = self.log_text.get("1.0", tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            messagebox.showinfo("完了", "ログ全体をクリップボードにコピーしました")
            self._log("ログをクリップボードにコピーしました")
        else:
            messagebox.showinfo("情報", "ログがありません")


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

    def _create_menubar(self):
        """メニューバーの作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル(F)", menu=file_menu)

        # 左側処理（5種類）
        left_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="左側処理", menu=left_menu)
        left_menu.add_command(label="源泉税(帳票:複数、顧客:複数)", command=lambda: self._set_process_and_execute("源泉税(帳票:複数、顧客:複数)"))
        left_menu.add_command(label="申請届出(帳票:複数、顧客:単一)※国税のみ対応", command=lambda: self._set_process_and_execute("申請届出(帳票:複数、顧客:単一)※国税のみ対応"))
        left_menu.add_command(label="法定調書(帳票:単一、顧客:複数)", command=lambda: self._set_process_and_execute("法定調書(帳票:単一、顧客:複数)"))
        left_menu.add_command(label="給与支払報告書(帳票:単一、顧客:複数)", command=lambda: self._set_process_and_execute("給与支払報告書(帳票:単一、顧客:複数)"))
        left_menu.add_command(label="償却資産申告書(帳票:単一、顧客:複数)", command=lambda: self._set_process_and_execute("償却資産申告書(帳票:単一、顧客:複数)"))

        # 右側処理（2種類）
        right_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="右側処理", menu=right_menu)
        right_menu.add_command(label="確定申告", command=lambda: self._set_right_mode_and_execute("確定申告"))
        right_menu.add_command(label="中間申告", command=lambda: self._set_right_mode_and_execute("中間申告"))

        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)

        # 表示メニュー
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="表示(V)", menu=view_menu)
        view_menu.add_command(label="処理結果を表示", command=self._show_result_window, accelerator="Ctrl+1")
        view_menu.add_command(label="ログを表示", command=self._show_log_window, accelerator="Ctrl+2")

        # ツールメニュー
        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール(T)", menu=tool_menu)
        tool_menu.add_command(label="ログをクリア", command=self._clear_log)
        tool_menu.add_command(label="結果をクリア", command=self._clear_results)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ(H)", menu=help_menu)
        help_menu.add_command(label="使い方", command=self._show_help)
        help_menu.add_command(label="バージョン情報", command=self._show_about)

        # キーボードショートカット
        self.root.bind('<Control-1>', lambda e: self._show_result_window())
        self.root.bind('<Control-2>', lambda e: self._show_log_window())

    def _show_help(self):
        """使い方ダイアログ表示"""
        help_window = tk.Toplevel(self.root)
        help_window.title("使い方")
        help_window.geometry("700x650")

        text_widget = tk.Text(help_window, wrap='word', font=('Yu Gothic UI', 10), padx=15, pady=15)
        text_widget.pack(fill='both', expand=True)

        help_text = """税務書類リネームシステム 使い方ガイド

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 画面の使い分け
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【左側】源泉税(帳票:複数、顧客:複数)などのフォルダ整理
　受信通知を自動で分割して、正しいフォルダに振り分けます

【右側】税務書類の自動分類・ファイル名変更
　PDFを読み取って、書類の種類を自動判定します

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 左側の使い方(源泉税(帳票:複数、顧客:複数)フォルダ整理)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ステップ1: 年月を入力
　→ 4桁の数字で入力（例：2025年1月 → 2501）
　→ フォルダリネーム時に使用されます

ステップ2: 処理プロセスを選択
　→ 源泉税(帳票:複数、顧客:複数)・申請届出(帳票:複数、顧客:単一)※国税のみ対応・法定調書(帳票:単一、顧客:複数)：01, 02
　→ 給与支払報告書(帳票:単一、顧客:複数)・償却資産申告書(帳票:単一、顧客:複数)：0001, 9001

ステップ3: 会社名の英語表記（オプション）
　→ 全角の英語を半角にしたい場合はチェック
　　（例：Ｓｔａｎｄａｒｄ  →  Standard）

ステップ4: 実行ボタンをクリック
　→ フォルダを選ぶと自動で処理が始まります

【対応処理タイプ】
　・源泉税(帳票:複数、顧客:複数)
　・申請届出(帳票:複数、顧客:単一)※国税のみ対応
　・法定調書(帳票:単一、顧客:複数)
　・給与支払報告書(帳票:単一、顧客:複数)
　・償却資産申告書(帳票:単一、顧客:複数)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 右側の使い方（書類の自動分類）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ステップ1: 年月を入力
　→ 4桁の数字で入力（例：2025年1月 → 2501）

ステップ2: 処理モードを選択
　→ 確定申告 または 中間申告

ステップ3: 市区町村を設定（該当する場合のみ）
　→ セット1の推奨設定:
　　　• 東京都特別区（23区）: 都道府県に「東京都」、市区町村は空欄
　　　　（優先処理により自動的に先頭に配置されます）
　　　• 東京都の市町村: 都道府県に「東京都」、市区町村に市町村名を入力
　　　　（例: 八王子市、町田市など。通常順序で処理されます）
　→ セット2～5: その他の市区町村

ステップ4: 実行ボタンをクリック
　→ フォルダを選ぶと自動で分類が始まります

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ メニューバーの使い方
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ファイル(F)
　・左側処理：5種類の処理から選択
　　- 源泉税(帳票:複数、顧客:複数)
　　- 申請届出(帳票:複数、顧客:単一)※国税のみ対応
　　- 法定調書(帳票:単一、顧客:複数)
　　- 給与支払報告書(帳票:単一、顧客:複数)
　　- 償却資産申告書(帳票:単一、顧客:複数)
　・右側処理：2種類のモードから選択
　　- 確定申告
　　- 中間申告
　・終了：アプリを閉じる

表示(V)
　・処理結果を表示：何が処理されたか確認
　・ログを表示：詳しい処理内容を確認

ツール(T)
　・ログをクリア：ログを消去
　・結果をクリア：処理結果を消去

ヘルプ(H)
　・使い方：このヘルプを表示
　・バージョン情報：アプリの情報を表示

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 処理結果ウィンドウの機能
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

　・出力フォルダを開く：直近で処理したフォルダを開く
　・結果をクリア：処理結果をクリアする

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ ログウィンドウの機能
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

　・ログクリア：ログを消去する
　・ログ全体をコピー：すべてのログをクリップボードにコピー

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ ショートカットキー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ctrl+1：処理結果ウィンドウを開く
Ctrl+2：ログウィンドウを開く
"""

        text_widget.insert('1.0', help_text)
        text_widget.configure(state='disabled')

        ttk.Button(help_window, text="閉じる", command=help_window.destroy).pack(pady=10)

    def _set_process_and_execute(self, process_type):
        """左側処理タイプを設定して実行"""
        self.process_type_var.set(process_type)
        # 接頭辞を自動設定（旧名称との互換性を保つ）
        if (process_type in ["源泉税", "申請届出（国税のみ）", "法定調書"] or
            process_type in ["源泉税(帳票:複数、顧客:複数)", "申請届出(帳票:複数、顧客:単一)※国税のみ対応", "法定調書(帳票:単一、顧客:複数)"]):
            self.left_main_prefix_var.set("01")
            self.left_receipt_prefix_var.set("02")
        elif (process_type in ["給与支払報告書", "償却資産申告書"] or
              process_type in ["給与支払報告書(帳票:単一、顧客:複数)", "償却資産申告書(帳票:単一、顧客:複数)"]):
            self.left_main_prefix_var.set("0001")
            self.left_receipt_prefix_var.set("9001")
        self._left_execute()

    def _set_right_mode_and_execute(self, mode):
        """右側処理モードを設定して実行"""
        self.process_mode_var.set(mode)
        self._select_folder()

    def _show_about(self):
        """バージョン情報ダイアログ表示"""
        about_window = tk.Toplevel(self.root)
        about_window.title("バージョン情報")
        about_window.geometry("700x600")
        about_window.resizable(True, True)

        content_frame = ttk.Frame(about_window, padding=20)
        content_frame.pack(fill='both', expand=True)

        ttk.Label(content_frame, text="📄", font=('Arial', 48)).pack()
        ttk.Label(content_frame, text="税務書類リネームシステム",
                 font=('Yu Gothic UI', 14, 'bold')).pack(pady=5)
        ttk.Label(content_frame, text="Version 8.6.0",
                 font=('Yu Gothic UI', 10, 'bold')).pack()

        # 更新内容（スクロール可能）
        update_frame = ttk.LabelFrame(content_frame, text="更新履歴", padding=10)
        update_frame.pack(pady=10, fill='both', expand=True)

        # スクロールバー付きテキストウィジェット
        text_widget = tk.Text(update_frame, wrap='word', height=20, width=80, font=('Yu Gothic UI', 8))
        scrollbar = ttk.Scrollbar(update_frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        text_widget.pack(side='left', fill='both', expand=True)

        updates = """【v8.6.1: 受信通知検出ロジック改善】
• 源泉税受信通知の検出精度を向上
  - PDF内の空白・改行を正規化して判定
  - 判定条件を緩和（「メール詳細」+「送信された」で検出）
  - 様々な形式の受信通知PDFに対応
• 「受信.pdf」「jusi.pdf」「受信通知.pdf」など異なるファイル名でも確実に検出
• 法定調書・給与支払報告書・償却資産申告書の処理には影響なし

【v8.6.0: UI改善 - 接頭辞設定独立化と完了表示統一】
• 左側機能の接頭辞設定を独立したフレームに分離
• 本票・受信通知の接頭辞をオプション入力可能に
  - 入力した値を優先使用、空欄時は処理プロセスに応じた既定値を使用
  - ユーザー設定の自動保存機能
• 右側（フォルダ一括処理）に完了メッセージ表示を追加
• 右側の市区町村案内テキストを簡素化
• ラベル表記を「本票接頭辞」→「本票」、「受信通知接頭辞」→「受信通知」に変更
• 左右両側の進捗表示を統一
• Windows ビルド設定の改善（アイコン適用の強化）

【v8.5.14: 中間申告モード対応と東京都特別区処理改善】
• 処理モードを「予定申告」から「中間申告」に統一
• 東京都特別区（23区）の繰り上がりロジック改善
  - 市区町村が空欄の場合のみ繰り上がりを発動
  - 東京都の市町村（八王子市、町田市など）は通常順序で処理
• UI表記を「東京都」から「東京都特別区（23区）」に統一
• 消費税中間申告書の分類精度向上
• ヘルプとエラーメッセージの明確化

【v8.5.13: 自治体設定UI表示改善】
• 市区町村の入力形式の説明文を短縮し、表示切れを解消

【v8.5.12: 東京都市町村入力対応】
• 東京都の市町村入力を有効化

【v8.5.11: UIテーマ統一】
• UIテーマとアイコン色の統一（背景色を#E3F2FDに変更）

【v8.5.10: 完了メッセージ簡素化】
• リネーム完了メッセージをシンプルに改善
• メッセージボックスの表示タイミングを最適化

【v8.5.8: UI統一改善】
• YYMM無効時メッセージの左右統一
• ユーザー入力値を表示して修正方法を明確化

【v8.5.7: 中間申告mode 3003誤検出修正】
• 消費税中間申告の受信通知が0003として誤検出される問題を修正
• exclude_keywordsを強化（"消費税中間申告書"、"納付すべき法人税額"を追加）

【v8.5.6: 地方税バンドル検出修正】
• 地方税.pdfから1003（受信通知）が失われる問題を修正
• "法人税"が"法人事業税"に誤マッチしないよう地方税除外ロジックを追加
• バンドル検出デバッグログとツールを追加

【v8.5.5: CSV分類統一】
• すべてのCSVファイルを5006_仕訳データに固定分類
• セット1のヘルプメッセージを改善（23区内の説明を明確化）

【v8.5.4: 受信通知分類精度改善】
• 国税受信通知（0003/3003）の優先度を150→280に大幅向上
• AND条件の階層的設計による高精度判定を実装
• カスタムアプリケーションアイコンを追加

【v8.5.0-3: コア機能強化】
• Tesseract/OCR依存の完全削除
• コンテンツベース分類への完全移行
• 自動接頭辞判定機能の実装
• 少額減価償却資産明細表の判定精度向上
• 分類精度の大幅向上とパフォーマンス最適化

【v8.2.0: 東京都設定UI改善】
• 東京都設定の案内ボックスを追加（市区町村名の入力形式を明確化）
• 案内ボックスのデザインをアプリに統一
• アプリアイコンの背景色を変更

【v8.1.0: UI改善とユーザビリティ向上】
• 設定の自動保存機能(YYMM/処理種別/接尾辞/処理モード)
• 処理種別による接尾辞の自動選択
• 給与支払報告書/償却資産の受信通知を9001に変更
• 「申請届出」→「申請届出(国税のみ)」に変更
• 「予定申告」→「中間申告」に用語変更
• 処理モードによるフォルダ名自動生成

【v8.0.0: アーキテクチャリファクタリング】
• プロセッサの分離とモジュール化
• 受信通知検出の独立モジュール化
• テストカバレッジの向上"""

        text_widget.insert('1.0', updates)
        text_widget.configure(state='disabled')

        import sys
        ttk.Label(content_frame, text=f"Python {sys.version.split()[0]}",
                 font=('Yu Gothic UI', 9)).pack(pady=5)

        ttk.Label(content_frame, text="© 2025 税務書類リネームシステム",
                 font=('Yu Gothic UI', 9)).pack()

        ttk.Button(content_frame, text="閉じる", command=about_window.destroy).pack(pady=10)

    # ==================== 左側フォルダリネーム機能メソッド ====================

    def _left_validate_yymm(self, *args):
        """左側YYMM入力バリデーション（完全独立）"""
        yymm_value = self.left_yymm_var.get()

        # 空欄チェック
        if not yymm_value:
            self.left_yymm_status_var.set("📋 YYMM入力待ち")
            if hasattr(self, 'left_execute_btn'):
                self.left_execute_btn.config(state='disabled')
            return

        # 4桁数字チェック
        if not re.match(r'^\d{4}$', yymm_value):
            self.left_yymm_status_var.set(f"⚠️ 無効: {yymm_value} (例: 2508, 25/08, ２５０８)")
            if hasattr(self, 'left_execute_btn'):
                self.left_execute_btn.config(state='disabled')
            return

        # 月の妥当性チェック (01-12)
        month = int(yymm_value[2:4])
        if month < 1 or month > 12:
            self.left_yymm_status_var.set(f"⚠️ 無効: {yymm_value} (例: 2508, 25/08, ２５０８)")
            if hasattr(self, 'left_execute_btn'):
                self.left_execute_btn.config(state='disabled')
            return

        # 正常
        self.left_yymm_status_var.set(f"✓ 正常: {yymm_value}")
        if hasattr(self, 'left_execute_btn'):
            self.left_execute_btn.config(state='normal')

        # 設定を保存
        self.user_settings.save_setting("left_yymm_value", yymm_value)

    def _left_execute(self):
        """左側フォルダリネーム実行（統一パラメータ + 個別処理）"""
        yymm_value = self.left_yymm_var.get()

        # プロセスタイプ取得
        process_type = self.process_type_var.get()
        self._log(f"[統一パラメータ] 選択されたプロセス: {process_type}")

        # 最終バリデーション
        if not re.match(r'^\d{4}$', yymm_value):
            messagebox.showerror("エラー", "YYMMは4桁の数字で入力してください")
            return

        month = int(yymm_value[2:4])
        if month < 1 or month > 12:
            messagebox.showerror("エラー", "月は01-12の範囲で入力してください")
            return

        # フォルダ選択
        folder_path = filedialog.askdirectory(title="リネーム対象フォルダを選択")
        if not folder_path:
            return

        # 直近で処理したフォルダを記録
        self._last_processed_folder = folder_path

        # 進捗表示更新
        self.left_progress_var.set("処理中...")
        self.left_execute_btn.config(state='disabled')

        # 🆕 統一パラメータ: 接頭辞、YYMM、全角半角変換（全機能共通）
        # ユーザー入力があればそれを使用、なければプロセスタイプに応じたデフォルト値
        main_prefix = self.left_main_prefix_var.get()
        receipt_prefix = self.left_receipt_prefix_var.get()
        
        # 空欄の場合は処理プロセスに応じたデフォルト値を設定
        if not main_prefix:
            if (process_type in ["源泉税", "申請届出（国税のみ）", "法定調書"] or
                process_type in ["源泉税(帳票:複数、顧客:複数)", "申請届出(帳票:複数、顧客:単一)※国税のみ対応", "法定調書(帳票:単一、顧客:複数)"]):
                main_prefix = "01"
            elif (process_type in ["給与支払報告書", "償却資産申告書"] or
                  process_type in ["給与支払報告書(帳票:単一、顧客:複数)", "償却資産申告書(帳票:単一、顧客:複数)"]):
                main_prefix = "0001"

        if not receipt_prefix:
            if (process_type in ["源泉税", "申請届出（国税のみ）", "法定調書"] or
                process_type in ["源泉税(帳票:複数、顧客:複数)", "申請届出(帳票:複数、顧客:単一)※国税のみ対応", "法定調書(帳票:単一、顧客:複数)"]):
                receipt_prefix = "02"
            elif (process_type in ["給与支払報告書", "償却資産申告書"] or
                  process_type in ["給与支払報告書(帳票:単一、顧客:複数)", "償却資産申告書(帳票:単一、顧客:複数)"]):
                receipt_prefix = "9001"
        
        normalize_english = self.normalize_english_var.get()

        # 🆕 各機能の個別処理を呼び出し（統一パラメータを渡す）
        if process_type in ["源泉税", "源泉税(帳票:複数、顧客:複数)"]:
            target_method = self._process_gensen
            args = (folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english)
        elif process_type in ["法定調書", "法定調書(帳票:単一、顧客:複数)"]:
            target_method = self._process_hoteichosho
            args = (folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english)
        elif process_type in ["申請届出（国税のみ）", "申請届出(帳票:複数、顧客:単一)※国税のみ対応"]:
            target_method = self._process_application
            args = (folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english)
        elif process_type in ["給与支払報告書", "給与支払報告書(帳票:単一、顧客:複数)"]:
            target_method = self._process_payroll_report
            args = (folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english)
        elif process_type in ["償却資産申告書", "償却資産申告書(帳票:単一、顧客:複数)"]:
            target_method = self._process_depreciable_assets
            args = (folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english)
        else:
            # フォールバック
            target_method = self._left_rename_unified
            args = (folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english, process_type)

        # バックグラウンド処理開始（統一パラメータを渡す）
        thread = threading.Thread(
            target=target_method,
            args=args,
            daemon=True
        )
        thread.start()


    def _left_rename_unified(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english, process_type):
        """
        統一リネーム処理（全機能共通）
        
        全ての機能に一律適用:
        - フォルダ名: YYMM_帳票名_会社名（固定でYYMM）
        - 本票ファイル名: main_prefix_帳票名.pdf（01または0001）
        - 受信通知ファイル名: receipt_prefix_受信通知.pdf（02または9999）
        - 全角→半角変換も統一適用
        
        Args:
            folder_path: 処理対象フォルダパス
            yymm: 年月（YYMM形式）
            main_prefix: 本票接頭辞（01または0001）
            receipt_prefix: 受信通知接頭辞（02または9999）
            normalize_english: 全角英語を半角に変換するか
            process_type: 処理プロセス種別（源泉税、申請届出など）
        """
        try:
            # UI更新を強制して黒画面を防ぐ
            self.root.update_idletasks()

            import fitz  # PyMuPDF

            errors = []
            created_folders = []

            # ステップ1: 本表ファイル（任意の番号_で始まるPDF）を収集
            main_files = []
            receipt_pdf_path = None

            # 本表ファイルパターン: 2桁または4桁の数字_で始まる
            main_file_pattern = re.compile(r'^(\d{2,4})_(.+)\.pdf$')

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)

                if not os.path.isfile(file_path):
                    continue

                # 本表ファイル: 数字_で始まるPDFファイル
                match = main_file_pattern.match(filename)
                if match:
                    main_files.append((filename, file_path, match))
                # 受信通知ファイル（テキスト抽出で判定）
                elif filename.endswith('.pdf') and ReceiptDetector.is_receipt_pdf(file_path):
                    receipt_pdf_path = file_path
                    self._log(f"[統一処理] 受信通知検出: {filename}")

            # 本表ファイルがない場合
            if not main_files:
                self.root.after(0, lambda: messagebox.showerror("エラー", "番号_で始まる本表ファイル（PDF）が見つかりません"))
                self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
                return

            # ステップ2: 各本表ファイルからフォルダを作成して移動
            for original_filename, original_file_path, match in main_files:
                # ファイル名から番号と残りの部分を抽出
                old_prefix = match.group(1)  # 元の番号（01, 02, 9999など）
                rest_name = match.group(2)   # 残りの部分（帳票名_顧問先...）

                # 🆕 統一処理: 全角→半角変換を一律適用
                if normalize_english:
                    rest_name = self._normalize_fullwidth_english(rest_name)

                # rest_nameから帳票名と会社名を抽出（顧問先番号を除去）
                # 形式: 帳票名_顧問先番号_会社名 → 帳票名_会社名
                parts = rest_name.split('_')
                if len(parts) >= 3:
                    # 最初の部分が帳票名、最後から2番目が顧問先番号、最後が会社名
                    # 顧問先番号を除去: 帳票名 + 会社名
                    doc_type = '_'.join(parts[:-2])  # 帳票名（複数の_を含む可能性）
                    company_name = parts[-1]          # 会社名

                    # 🆕 統一処理: 全角→半角変換を一律適用
                    if normalize_english:
                        company_name = self._normalize_fullwidth_english(company_name)
                        doc_type = self._normalize_fullwidth_english(doc_type)

                    folder_base_name = f"{doc_type}_{company_name}"
                else:
                    # パースできない場合はそのまま使用
                    folder_base_name = rest_name
                    doc_type = rest_name
                    if normalize_english:
                        folder_base_name = self._normalize_fullwidth_english(folder_base_name)
                        doc_type = self._normalize_fullwidth_english(doc_type)

                # 🆕 統一処理: フォルダ名は必ずYYMM形式（固定）
                # フォルダ名: YYMM_帳票名_会社名
                folder_name = f"{yymm}_{folder_base_name}"
                new_folder_path = os.path.join(folder_path, folder_name)

                # 🆕 統一処理: 本表ファイル名はラジオボタンで選択した接頭辞
                # 新しいファイル名: main_prefix_帳票名.pdf（会社名除去）
                new_filename = f"{main_prefix}_{doc_type}.pdf"

                try:
                    # フォルダ作成
                    os.makedirs(new_folder_path, exist_ok=True)

                    # 本表ファイルをコピーしてフォルダ内に配置（元ファイルは残す）
                    dest_file_path = os.path.join(new_folder_path, new_filename)
                    shutil.copy2(original_file_path, dest_file_path)

                    created_folders.append({
                        'folder_path': new_folder_path,
                        'folder_name': folder_name,
                        'main_file': new_filename
                    })

                    self._log(f"[統一処理] フォルダ作成+コピー: {original_filename} → {folder_name}/{new_filename} (元ファイルは保持)")

                    # 処理結果ウィンドウに追加
                    self._add_result_success(
                        original_file=original_filename,
                        new_filename=f"{folder_name}/{new_filename}",
                        doc_type="フォルダリネーム",
                        method=f"左側処理({process_type})",
                        confidence="100%"
                    )

                except Exception as e:
                    errors.append(f"フォルダ作成エラー ({original_filename}): {str(e)}")

            # ステップ3: 受信通知PDFを分割して各フォルダに配置
            if receipt_pdf_path and created_folders:
                try:
                    doc = fitz.open(receipt_pdf_path)
                    total_pages = len(doc)

                    # 連番方式による受信通知配置
                    matcher = CompanyNameMatcher()
                    folder_names = [f['folder_name'] for f in created_folders]
                    matched_count = 0
                    unmatched_pages = []

                    # 一時フォルダ作成
                    import tempfile
                    temp_dir = tempfile.mkdtemp(prefix="receipt_temp_")
                    self._log(f"[統一処理] 一時フォルダ作成: {temp_dir}")

                    # ステップ1: 全ページを連番付きで一時分割
                    temp_receipt_files = []  # [(temp_path, page_num, company_name), ...]

                    for page_num in range(total_pages):
                        # ページを抽出
                        page_doc = fitz.open()
                        page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

                        # 🆕 統一処理: 受信通知はラジオボタンで選択した接頭辞
                        temp_filename = f"{receipt_prefix}_受信通知_{page_num + 1:02d}.pdf"
                        temp_path = os.path.join(temp_dir, temp_filename)

                        page_doc.save(temp_path)
                        page_doc.close()

                        # 会社名抽出
                        receipt_company = matcher.extract_company_name_from_receipt(receipt_pdf_path, page_num)

                        if receipt_company:
                            temp_receipt_files.append((temp_path, page_num, receipt_company))
                            self._log(f"[統一処理] 一時ファイル作成: {temp_filename} ({receipt_company})")
                        else:
                            self._log(f"[統一処理] 警告: ページ{page_num + 1} - 会社名抽出失敗")
                            unmatched_pages.append((page_num, "会社名抽出失敗"))

                    doc.close()

                    # ステップ2: 各ページを金額マッチングで最適フォルダに配置
                    for temp_path, page_num, receipt_company in temp_receipt_files:
                        # すべてのマッチするフォルダを取得
                        matched_folders = matcher.match_all_folders(receipt_company, folder_names, threshold=0.7)

                        if not matched_folders:
                            unmatched_pages.append((page_num, f"マッチング失敗: {receipt_company}"))
                            self._log(f"[統一処理] 警告: ページ{page_num + 1} - マッチング失敗（{receipt_company}）")
                            continue

                        if len(matched_folders) == 1:
                            # 単一フォルダ: 連番保持で即配置
                            folder_name, score = matched_folders[0]
                            self._log(f"[統一処理] ページ{page_num + 1} - 単一フォルダ: {folder_name} (スコア: {score:.2f})")

                            # フォルダ情報取得
                            folder_info = None
                            for f in created_folders:
                                if f['folder_name'] == folder_name:
                                    folder_info = f
                                    break

                            if folder_info:
                                receipt_filename = os.path.basename(temp_path)
                                receipt_dest_path = os.path.join(folder_info['folder_path'], receipt_filename)
                                shutil.move(temp_path, receipt_dest_path)

                                # 🆕 統一処理: 受信通知の最終ファイル名はラジオボタンで選択した接頭辞
                                final_filename = f"{receipt_prefix}_受信通知.pdf"
                                final_dest_path = os.path.join(folder_info['folder_path'], final_filename)
                                if receipt_dest_path != final_dest_path:
                                    shutil.move(receipt_dest_path, final_dest_path)
                                    self._log(f"[統一処理] 受信通知リネーム: {receipt_filename} → {final_filename}")

                                matched_count += 1
                                self._log(f"[統一処理] 受信通知配置: {final_filename} → {folder_name}")

                                # 処理結果ウィンドウに追加
                                self._add_result_success(
                                    original_file=f"受信通知.pdf (ページ{page_num + 1})",
                                    new_filename=f"{folder_name}/{final_filename}",
                                    doc_type="受信通知分割",
                                    method=f"左側処理({process_type})",
                                    confidence=f"{score:.0%}"
                                )
                            else:
                                unmatched_pages.append((page_num, f"フォルダ情報なし: {folder_name}"))

                        else:
                            # 複数フォルダ: 金額マッチングで最適フォルダ選択
                            self._log(f"[統一処理] ページ{page_num + 1} - 複数フォルダ検出: {len(matched_folders)}件（金額マッチング実行）")
                            
                            # 受信通知から金額抽出
                            receipt_amount = matcher.extract_amount_from_receipt(temp_path, 0)

                            if not receipt_amount:
                                self._log(f"[統一処理] 警告: 受信通知金額抽出失敗 - ページ{page_num + 1}")
                                unmatched_pages.append((page_num, "金額抽出失敗"))
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                                continue

                            self._log(f"[統一処理] 受信通知金額: {receipt_amount:,}円")

                            # 各フォルダの本表金額と比較
                            best_folder = None
                            best_diff = float('inf')

                            for folder_name, score in matched_folders:
                                folder_info = None
                                for f in created_folders:
                                    if f['folder_name'] == folder_name:
                                        folder_info = f
                                        break

                                if not folder_info:
                                    continue

                                # 本表金額抽出
                                main_pdf_path = os.path.join(folder_info['folder_path'], folder_info['main_file'])
                                main_amount = matcher.extract_amount_from_main_pdf(main_pdf_path)

                                if main_amount:
                                    diff = abs(receipt_amount - main_amount)
                                    self._log(f"[統一処理]   {folder_name}: 本表={main_amount:,}円, 差額={diff:,}円")

                                    if diff < best_diff:
                                        best_diff = diff
                                        best_folder = (folder_name, folder_info)

                            # 最適フォルダに配置
                            if best_folder:
                                folder_name, folder_info = best_folder
                                receipt_filename = os.path.basename(temp_path)
                                receipt_dest_path = os.path.join(folder_info['folder_path'], receipt_filename)
                                shutil.move(temp_path, receipt_dest_path)

                                # 🆕 統一処理: 受信通知の最終ファイル名はラジオボタンで選択した接頭辞
                                final_filename = f"{receipt_prefix}_受信通知.pdf"
                                final_dest_path = os.path.join(folder_info['folder_path'], final_filename)
                                if receipt_dest_path != final_dest_path:
                                    shutil.move(receipt_dest_path, final_dest_path)

                                matched_count += 1
                                self._log(f"[統一処理] 金額マッチング成功: {final_filename} → {folder_name} (差額: {best_diff:,}円)")

                                # 処理結果ウィンドウに追加
                                self._add_result_success(
                                    original_file=f"受信通知.pdf (ページ{page_num + 1})",
                                    new_filename=f"{folder_name}/{final_filename}",
                                    doc_type="受信通知分割（金額マッチング）",
                                    method=f"左側処理({process_type})",
                                    confidence=f"差額{best_diff:,}円"
                                )
                            else:
                                unmatched_pages.append((page_num, "金額マッチング失敗"))
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)

                    # マッチング結果サマリー
                    self._log(f"[統一処理] 受信通知マッチング完了: 成功={matched_count}/{total_pages}, 失敗={len(unmatched_pages)}")

                    if unmatched_pages:
                        for page_num, reason in unmatched_pages:
                            errors.append(f"ページ{page_num + 1}: {reason}")

                    # 一時フォルダクリーンアップ
                    try:
                        remaining_files = os.listdir(temp_dir)
                        if remaining_files:
                            for f in remaining_files:
                                os.remove(os.path.join(temp_dir, f))
                        os.rmdir(temp_dir)
                        self._log(f"[統一処理] 一時フォルダ削除完了")
                    except Exception as e:
                        self._log(f"[統一処理] 警告: 一時フォルダ削除エラー: {e}")

                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    errors.append(f"受信通知分割エラー: {str(e)}")
                    self._log(f"[統一処理] ERROR: 受信通知分割エラー詳細:\n{error_detail}")

            # UI更新（メインスレッドで実行）- 必ず実行
            self.root.after(0, self._left_finish, len(created_folders), len(main_files), errors)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("処理エラー", f"予期しないエラーが発生しました:\n{str(e)}"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))

    def _process_main_files_without_receipt(self, folder_path, yymm, main_prefix, normalize_english=False):
        """
        本表ファイルのみ処理してフォルダ作成（受信通知処理なし）
        申請届出用: 顧問先コードを除去
        
        Returns:
            created_folders: [(folder_path, folder_name, application_name), ...]
        """
        import fitz
        created_folders = []
        
        # 本表ファイルパターン: 数字_届出名称_顧問先コード_会社名.pdf
        main_file_pattern = re.compile(r'^(\d{2,4})_(.+)\.pdf$')
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            match = main_file_pattern.match(filename)
            if not match:
                continue
            
            # ファイル名解析
            old_prefix = match.group(1)
            rest_name = match.group(2)  # 例: "届出名称_0801A0094_会社名"
            
            # 顧問先コード除去
            parts = rest_name.split('_')
            if len(parts) >= 3:
                # 真ん中のパートが顧問先コード（数字+英字）かチェック
                middle_part = parts[1]
                if re.match(r'^\d{4}[A-Z]\d{4}$', middle_part):
                    # 顧問先コードを除去: [届出名称, 会社名, ...] に再構成
                    rest_name = '_'.join([parts[0]] + parts[2:])
                    self._log(f"[申請届出] 顧問先コード除去: {middle_part}")
            
            # 英語半角変換
            if normalize_english:
                rest_name = self._normalize_fullwidth_english(rest_name)
            
            # フォルダ名: YYMM_main_prefix_届出名称_会社名
            new_folder_name = f"{yymm}_{main_prefix}_{rest_name}"
            new_folder_path = os.path.join(folder_path, new_folder_name)
            
            # フォルダ作成
            os.makedirs(new_folder_path, exist_ok=True)
            
            # 本表ファイルをコピー
            new_main_filename = f"{main_prefix}_{rest_name}.pdf"
            dest_file = os.path.join(new_folder_path, new_main_filename)
            shutil.copy2(file_path, dest_file)
            
            # 申請名を抽出（届出名称部分）
            application_name = rest_name.split('_')[0] if '_' in rest_name else rest_name
            
            created_folders.append((new_folder_path, new_folder_name, application_name))
            self._log(f"[本表処理] フォルダ作成: {new_folder_name} (申請名: {application_name})")
        
        return created_folders

    def _process_application_receipt(self, receipt_pdf_path, created_folders, receipt_prefix, receipt_type):
        """
        申請届出の受信通知PDF処理（国税または地方税）
        まず1枚ずつ分割してからマッチング
        
        Args:
            receipt_pdf_path: 受信通知PDFのパス
            created_folders: [(folder_path, folder_name, application_name), ...]
            receipt_prefix: 受信通知プレフィックス（"02" or "9999"）
            receipt_type: "国税" or "地方税"
        """
        import fitz
        import tempfile
        import os
        
        try:
            doc = fitz.open(receipt_pdf_path)
            self._log(f"[{receipt_type}受信通知] ページ数: {len(doc)}")
            
            # Step 1: まず全ページを一時ファイルとして分割
            temp_pages = []
            temp_dir = tempfile.mkdtemp()
            
            for page_num in range(len(doc)):
                # 1ページずつ一時PDFを作成
                temp_pdf_path = os.path.join(temp_dir, f"page_{page_num + 1}.pdf")
                single_page_doc = fitz.open()
                single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                single_page_doc.save(temp_pdf_path)
                single_page_doc.close()
                
                # テキスト抽出
                page = doc[page_num]
                text = page.get_text()
                
                temp_pages.append({
                    'page_num': page_num + 1,
                    'pdf_path': temp_pdf_path,
                    'text': text
                })
                
                self._log(f"[{receipt_type}受信通知] Page {page_num + 1}: 分割完了")
            
            doc.close()
            
            # Step 2: 各分割ページから申請名を抽出してマッチング
            for page_info in temp_pages:
                page_num = page_info['page_num']
                temp_pdf = page_info['pdf_path']
                text = page_info['text']
                
                # 申請名を抽出
                application_name = self._extract_application_name_from_receipt(text, receipt_type)
                
                if not application_name:
                    self._log(f"[{receipt_type}受信通知] Page {page_num}: 申請名抽出失敗")
                    os.remove(temp_pdf)
                    continue
                
                self._log(f"[{receipt_type}受信通知] Page {page_num}: 申請名='{application_name}'")
                
                # マッチするフォルダを検索
                matched_folder = self._match_application_folder(application_name, created_folders)
                
                if matched_folder:
                    folder_path, folder_name, _ = matched_folder

                    # 受信通知を該当フォルダにコピー（既存ファイルがある場合は連番追加）
                    base_filename = f"{receipt_prefix}_受信通知"
                    receipt_filename = f"{base_filename}.pdf"
                    dest_path = os.path.join(folder_path, receipt_filename)

                    counter = 2
                    while os.path.exists(dest_path):
                        receipt_filename = f"{base_filename}_{counter:02d}.pdf"
                        dest_path = os.path.join(folder_path, receipt_filename)
                        counter += 1

                    shutil.copy2(temp_pdf, dest_path)
                    self._log(f"[{receipt_type}受信通知] マッチ成功: {folder_name} → {receipt_filename}")
                else:
                    self._log(f"[{receipt_type}受信通知] Page {page_num}: マッチするフォルダが見つかりません")
                
                os.remove(temp_pdf)
            
            # 一時ディレクトリ削除
            os.rmdir(temp_dir)
            
        except Exception as e:
            self._log(f"[{receipt_type}受信通知] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())

    def _extract_application_name_from_receipt(self, text, receipt_type):
        """
        受信通知から申請名を抽出（複数行対応）
        
        Args:
            text: PDFページのテキスト
            receipt_type: "国税" or "地方税"
        
        Returns:
            application_name: 抽出された申請名（正規化済み）
        """
        if receipt_type == "国税":
            # 国税パターン: "種目："の後ろ、次のフィールドまで
            match = re.search(r'種[\s\u3000]*目[\s\u3000]*[:：]?[\s\u3000\n]*(.*?)(?=備考|メッセージ|Page|file:|$)', text, re.DOTALL)
            if match:
                raw_name = match.group(1).strip()
                raw_name = re.sub(r'\s+', '', raw_name)
                if not raw_name:
                    return None
                self._log(f"[国税] 抽出された種目: '{raw_name}'")
                return self._normalize_application_name(raw_name)
        
        elif receipt_type == "地方税":
            # 地方税パターン: "手続名："の後ろ、次のフィールドまで
            match = re.search(r'手続名[\s\u3000]*[:：]?[\s\u3000\n]*(.*?)(?=提出先|受付日|Page|file:|$)', text, re.DOTALL)
            if match:
                raw_name = match.group(1).strip()
                raw_name = re.sub(r'\s+', '', raw_name)
                if not raw_name:
                    return None
                self._log(f"[地方税] 抽出された手続名: '{raw_name}'")
                return self._normalize_application_name(raw_name)
        
        return None

    def _normalize_application_name(self, name):
        """
        申請名を正規化（マッチング用）
        """
        if not name:
            return ""

        # 全角英数字を半角に変換
        normalized = self._normalize_fullwidth_english(name)
        normalized = normalized.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        # 括弧内を除去
        normalized = re.sub(r'[（\(].*?[）\)]', '', normalized)
        normalized = re.sub(r'[【\[].*?[】\]]', '', normalized)

        # 余分な空白・記号を除去
        normalized = re.sub(r'\s+', '', normalized)
        normalized = re.sub(r'[・、。]', '', normalized)

        return normalized

    def _match_application_folder(self, application_name, created_folders):
        """
        申請名に基づいてフォルダをマッチング（部分一致対応）
        """
        normalized_receipt_name = self._normalize_application_name(application_name)
        self._log(f"[マッチング] 受信通知から抽出: '{application_name}' → 正規化後: '{normalized_receipt_name}'")

        candidates = []

        for folder_path, folder_name, folder_app_name in created_folders:
            normalized_folder_name = self._normalize_application_name(folder_app_name)
            self._log(f"[マッチング] フォルダ比較: '{folder_app_name}' → 正規化後: '{normalized_folder_name}'")

            score = 0
            match_type = None

            # 完全一致
            if normalized_receipt_name == normalized_folder_name:
                score = 100
                match_type = "完全一致"
            # 部分一致
            elif normalized_receipt_name in normalized_folder_name or normalized_folder_name in normalized_receipt_name:
                score = 80
                match_type = "部分一致"
            # キーワード一致
            else:
                min_len = min(len(normalized_receipt_name), len(normalized_folder_name))
                if min_len >= 4:
                    match_len = int(min_len * 0.6)
                    if normalized_receipt_name[:match_len] == normalized_folder_name[:match_len]:
                        score = 60
                        match_type = "キーワード一致"

            # 共通キーワード検索
            if score == 0:
                important_keywords = ['申告期限', '延長', '法人設立', '給与支払', '源泉所得', '青色申告',
                                     '納期', '特例', '承認', '開設', '届出']

                receipt_keywords = [kw for kw in important_keywords if kw in normalized_receipt_name]
                folder_keywords = [kw for kw in important_keywords if kw in normalized_folder_name]

                common_keywords = set(receipt_keywords) & set(folder_keywords)
                if common_keywords:
                    score = 40 + len(common_keywords) * 5
                    match_type = f"共通キーワード一致({', '.join(common_keywords)})"

            if score > 0:
                candidates.append((score, match_type, folder_path, folder_name, folder_app_name))

        # スコアが最も高い候補を選択
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, match_type, folder_path, folder_name, folder_app_name = candidates[0]

            if best_score >= 40:
                self._log(f"[マッチング成功] {match_type} (スコア:{best_score}): {folder_name}")
                return (folder_path, folder_name, folder_app_name)

        return None

    # ============================================================
    # 🆕 NEW Phase 3-2: プロセス別処理メソッド（ラッパー方式）
    # ============================================================

    def _process_gensen(self, folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english):
        """源泉税処理（既存処理を呼び出すラッパー）"""
        self._log("[源泉税] 処理を開始")
        # 既存の _left_rename_background をそのまま呼び出す
        self._left_rename_background(folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english)

    def _process_hoteichosho(self, folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english):
        """法定調書処理（既存処理を呼び出すラッパー）"""
        self._log("[法定調書] 処理を開始")
        # 既存の _left_rename_background をそのまま呼び出す
        self._left_rename_background(folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english)

    def _process_application(self, folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english):
        """
        申請届出処理（統一処理ベース + 専用受信通知処理）
        
        処理フロー:
        1. 統一処理でフォルダ作成・本票配置（YYMM形式、接頭辞統一）
        2. 国税受信通知.pdfと地方税受信通知.pdfを別々に処理
        3. 各ページから申請名を抽出してマッチング
        """
        self._log("[申請届出] 処理を開始")
        
        try:
            import fitz
            
            # Step 1: 統一処理でフォルダ作成（一時的に同期実行）
            self._log("[申請届出] Step 1: 統一処理でフォルダ作成開始")
            
            # 統一処理のコアロジックを同期実行
            errors = []
            created_folders = []
            main_files = []
            
            # 本表ファイル収集
            main_file_pattern = re.compile(r'^(\d{2,4})_(.+)\.pdf$')
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if not os.path.isfile(file_path):
                    continue
                match = main_file_pattern.match(filename)
                if match:
                    main_files.append((filename, file_path, match))
            
            if not main_files:
                self.root.after(0, lambda: messagebox.showerror("エラー", "番号_で始まる本表ファイル（PDF）が見つかりません"))
                self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
                return
            
            # 各本表ファイルからフォルダを作成
            for original_filename, original_file_path, match in main_files:
                old_prefix = match.group(1)
                rest_name = match.group(2)
                
                # 統一処理: 全角→半角変換
                if normalize_english:
                    rest_name = self._normalize_fullwidth_english(rest_name)
                
                # 顧問先番号除去
                parts = rest_name.split('_')
                if len(parts) >= 3:
                    doc_type = '_'.join(parts[:-2])
                    company_name = parts[-1]
                    if normalize_english:
                        company_name = self._normalize_fullwidth_english(company_name)
                        doc_type = self._normalize_fullwidth_english(doc_type)
                    folder_base_name = f"{doc_type}_{company_name}"
                else:
                    folder_base_name = rest_name
                    doc_type = rest_name
                    if normalize_english:
                        folder_base_name = self._normalize_fullwidth_english(folder_base_name)
                        doc_type = self._normalize_fullwidth_english(doc_type)
                
                # 統一処理: フォルダ名はYYMM形式（固定）
                folder_name = f"{yymm_value}_{folder_base_name}"
                new_folder_path = os.path.join(folder_path, folder_name)
                
                # 統一処理: 本表ファイル名はラジオボタンで選択した接頭辞
                new_filename = f"{main_prefix}_{doc_type}.pdf"
                
                try:
                    os.makedirs(new_folder_path, exist_ok=True)
                    dest_file_path = os.path.join(new_folder_path, new_filename)
                    shutil.copy2(original_file_path, dest_file_path)
                    
                    # 申請名抽出（届出名称部分）
                    application_name = doc_type
                    
                    created_folders.append({
                        'folder_path': new_folder_path,
                        'folder_name': folder_name,
                        'main_file': new_filename,
                        'application_name': application_name
                    })
                    
                    self._log(f"[申請届出] フォルダ作成: {folder_name} (申請名: {application_name})")
                    
                except Exception as e:
                    errors.append(f"フォルダ作成エラー ({original_filename}): {str(e)}")
            
            if not created_folders:
                self.root.after(0, lambda: messagebox.showerror("エラー", "フォルダ作成に失敗しました"))
                self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
                return
            
            self._log(f"[申請届出] 作成されたフォルダ数: {len(created_folders)}")

            # Step 2: 受信通知ファイルを検索（テキスト抽出で判定）
            kokuzei_receipt = None
            chihou_receipt = None
            # 本表ファイルパターン（除外用）
            main_file_pattern = re.compile(r'^\d{2,4}_')

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                # 本表ファイル（数字_で始まる）は除外
                if main_file_pattern.match(filename):
                    continue
                if os.path.isfile(file_path) and filename.endswith('.pdf') and ReceiptDetector.is_receipt_pdf(file_path):
                    # PDFのテキストを抽出して国税/地方税を判定
                    import fitz
                    try:
                        doc = fitz.open(file_path)
                        first_page_text = doc[0].get_text() if len(doc) > 0 else ""
                        doc.close()

                        # テキスト内容で判定（e-Tax関連キーワードで国税、eLTAX関連で地方税）
                        if "e-Tax" in first_page_text or "国税庁" in first_page_text or "税務署" in first_page_text:
                            kokuzei_receipt = file_path
                            self._log(f"[申請届出] 国税受信通知検出: {filename}")
                        elif "eLTAX" in first_page_text or "都税" in first_page_text or "市区町村" in first_page_text or "市役所" in first_page_text or "区役所" in first_page_text:
                            chihou_receipt = file_path
                            self._log(f"[申請届出] 地方税受信通知検出: {filename}")
                    except Exception as e:
                        self._log(f"[申請届出] PDF読み取りエラー ({filename}): {str(e)}")

            # 国税受信通知を処理
            if kokuzei_receipt:
                self._log("[申請届出] Step 2: 国税受信通知処理開始")
                self._process_application_receipt(
                    kokuzei_receipt, created_folders, receipt_prefix, "国税"
                )
            else:
                self._log("[申請届出] 国税受信通知が見つかりません（スキップ）")

            # 地方税受信通知を処理
            if chihou_receipt:
                self._log("[申請届出] Step 3: 地方税受信通知処理開始")
                self._process_application_receipt(
                    chihou_receipt, created_folders, receipt_prefix, "地方税"
                )
            else:
                self._log("[申請届出] 地方税受信通知が見つかりません（スキップ）")
            
            # 完了
            self.root.after(0, lambda: self.left_progress_var.set("完了"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
            self._log("[申請届出] 処理完了")

            # 完了メッセージ表示
            self.root.after(0, lambda: messagebox.showinfo("完了", "処理が完了しました"))

        except Exception as e:
            self._log(f"[申請届出] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("エラー", f"申請届出処理中にエラーが発生しました:\n{str(e)}"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))

    def _process_payroll_report(self, folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english):
        """
        給与支払報告書処理（個別実装 + 統一パラメータ）

        処理フロー:
        1. 本表ファイル内の受信通知ページ検出・分離
        2. 本表ページのみでフォルダ作成
        3. 受信通知ページを会社名・市区町村名で2段階マッチング
        """
        self._log("[給与支払報告書] 処理を開始")

        try:
            import fitz

            # Step 1: 本表ファイル処理（受信通知ページ検出・分離）
            self._log("[給与支払報告書] Step 1: 本表ファイル処理開始")
            created_folders = self._process_main_files_for_special(
                folder_path, yymm_value, main_prefix, normalize_english
            )

            if not created_folders:
                self.root.after(0, lambda: messagebox.showerror(
                    "エラー", "本表ファイルが見つからないか、フォルダ作成に失敗しました"
                ))
                self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
                return

            self._log(f"[給与支払報告書] 作成されたフォルダ数: {len(created_folders)}")

            # Step 2: 受信通知ファイル処理（テキスト抽出で判定）
            receipt_pdf = None

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path) and filename.endswith('.pdf') and ReceiptDetector.is_receipt_pdf(file_path):
                    receipt_pdf = file_path
                    self._log(f"[給与支払報告書] 受信通知検出: {filename}")
                    break  # 最初に見つかった受信通知を使用

            if receipt_pdf:
                self._log(f"[給与支払報告書] Step 2: 受信通知処理開始 ({os.path.basename(receipt_pdf)})")
                self._process_payroll_receipts_from_file(receipt_pdf, created_folders, receipt_prefix)
            else:
                self._log("[給与支払報告書] 受信通知が見つかりません")

            # Step 3: 本表ファイル内の受信通知ページを2段階マッチング（会社名→会社名+市区町村）
            self._log("[給与支払報告書] Step 3: 本表内受信通知ページ2段階マッチング開始")
            for folder_info in created_folders:
                folder_path_dest = folder_info['folder_path']
                folder_name = folder_info['folder_name']
                receipt_pages = folder_info['receipt_pages']
                doc = folder_info['doc']
                folder_company_name = folder_info['company_name']
                folder_company_name_normalized = folder_info['company_name_normalized']

                if not receipt_pages:
                    self._log(f"[給与支払報告書] {folder_name}: 受信通知ページなし")
                    continue

                # 受信通知ページを2段階マッチング
                for page_num, extracted_company, municipality in receipt_pages:
                    matched = False
                    
                    # Step 1: 会社名でマッチング
                    if extracted_company and extracted_company == folder_company_name_normalized:
                        # 会社名が一致する候補を探す
                        same_company_folders = [f for f in created_folders 
                                               if f['company_name_normalized'] == folder_company_name_normalized]
                        
                        # Step 2: 候補が1つなら、それにマッチ
                        if len(same_company_folders) == 1:
                            matched = True
                            self._log(f"[給与支払報告書] 会社名のみで一意にマッチ: {folder_company_name_normalized}")
                        
                        # Step 3: 候補が複数の場合は、市区町村名でさらに絞り込む
                        elif len(same_company_folders) > 1:
                            self._log(f"[給与支払報告書] 同一会社名が複数({len(same_company_folders)}件): 市区町村名で絞り込み")
                            # フォルダ名に市区町村名が含まれているかチェック
                            if municipality and municipality in folder_name:
                                matched = True
                                self._log(f"[給与支払報告書] 市区町村名でマッチ: {municipality}")
                    
                    if matched:
                        # 受信通知ページを保存
                        receipt_filename = f"{receipt_prefix}_受信通知.pdf"
                        receipt_path = os.path.join(folder_path_dest, receipt_filename)

                        # ページを個別PDFとして保存
                        new_doc = fitz.open()
                        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                        new_doc.save(receipt_path)
                        new_doc.close()

                        self._log(f"[給与支払報告書] 受信通知保存: {folder_name}/{receipt_filename} (会社名: {extracted_company}, 市区町村: {municipality})")
                        
                        # 処理結果を表示
                        self.root.after(0, lambda fn=folder_name, rfn=receipt_filename:
                            self._add_result_success(
                                original_file="本表PDF内受信通知ページ",
                                new_filename=f"{fn}/{rfn}",
                                doc_type="給与支払報告書(受信通知)",
                                method="左側処理",
                                confidence="100%"
                            ))
                        break  # マッチしたら次のフォルダへ
                    else:
                        self._log(f"[給与支払報告書] マッチ失敗: 受信通知={extracted_company}, フォルダ={folder_company_name_normalized}")

                # docをクローズ
                doc.close()

            # 完了
            self.root.after(0, lambda: self.left_progress_var.set("完了"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
            self._log("[給与支払報告書] 処理完了")

            # 完了メッセージ表示
            self.root.after(0, lambda: messagebox.showinfo("完了", "処理が完了しました"))

        except Exception as e:
            self._log(f"[給与支払報告書] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("エラー", f"給与支払報告書処理中にエラーが発生しました:\n{str(e)}"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))

    def _process_depreciable_assets(self, folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english):
        """
        償却資産申告書処理（個別実装 + 統一パラメータ）
        
        処理フロー:
        1. 本表ファイルのリネーム・フォルダ作成（統一パラメータ使用）
        2. 受信通知PDFをテキスト抽出で検出（ファイル名不問）
        3. マッチングしてページを配置
        """
        self._log("[償却資産申告書] 処理を開始")
        
        try:
            import fitz
            
            # Step 1: 本表ファイル処理（統一パラメータでフォルダ作成）
            self._log("[償却資産申告書] Step 1: 本表ファイル処理開始")
            created_folders = self._process_main_files_for_special(
                folder_path, yymm_value, main_prefix, normalize_english
            )
            
            if not created_folders:
                self.root.after(0, lambda: messagebox.showerror(
                    "エラー", "本表ファイルが見つからないか、フォルダ作成に失敗しました"
                ))
                self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
                return
            
            self._log(f"[償却資産申告書] 作成されたフォルダ数: {len(created_folders)}")
            
            # Step 2: 受信通知処理（テキスト抽出で判定、ファイル名は問わない）
            receipt_pdf = None

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path) and filename.endswith('.pdf') and ReceiptDetector.is_receipt_pdf(file_path):
                    receipt_pdf = file_path
                    self._log(f"[償却資産申告書] 受信通知検出: {filename}")
                    break  # 最初に見つかった受信通知を使用

            if receipt_pdf:
                self._log("[償却資産申告書] Step 2: 受信通知処理開始")
                self._process_depreciable_receipts(receipt_pdf, created_folders, receipt_prefix)
            else:
                self._log("[償却資産申告書] 受信通知が見つかりません（スキップ）")
            
            # 完了
            self.root.after(0, lambda: self.left_progress_var.set("完了"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
            self._log("[償却資産申告書] 処理完了")

            # 完了メッセージ表示
            self.root.after(0, lambda: messagebox.showinfo("完了", "処理が完了しました"))

        except Exception as e:
            self._log(f"[償却資産申告書] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("エラー", f"償却資産申告書処理中にエラーが発生しました:\n{str(e)}"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))


    def _process_main_files_for_special(self, folder_path, yymm, main_prefix, normalize_english=False):
        """
        本表ファイル処理(給与支払報告書・償却資産申告書用)

        処理内容:
        1. 全PDFファイルをテキスト抽出して受信通知か本表か判定
        2. 本表ファイル: フォルダ作成
        3. 受信通知ファイル: 各ページを検出して保存用に保持

        Returns:
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'main_file': ..., 'receipt_doc': doc, 'receipt_path': ...}, ...]
        """
        import fitz
        created_folders = []
        receipt_files = []  # [(file_path, doc), ...]

        # 受信通知判定キーワード
        receipt_keywords = [
            "申告受付完了通知",
            "納税者の氏名又は名称",
            "発行元",
            "受付日時"
        ]

        # 本表ファイルパターン: 数字_帳票名_顧問先番号_会社名.pdf
        main_file_pattern = re.compile(r'^(\d{2,4})_(.+)\.pdf$')

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            if not os.path.isfile(file_path):
                continue

            match = main_file_pattern.match(filename)
            if not match:
                continue

            # テキスト抽出で受信通知かどうか判定（AND条件）
            if ReceiptDetector.is_receipt_pdf(file_path):
                self._log(f"[本表処理] 受信通知ファイルをスキップ: {filename}")
                continue

            # ファイル名解析
            old_prefix = match.group(1)
            rest_name = match.group(2)  # 例: "帳票名_顧問先番号_会社名"

            # 統一処理: 全角→半角変換
            if normalize_english:
                rest_name = self._normalize_fullwidth_english(rest_name)

            # 顧問先番号除去
            parts = rest_name.split('_')
            if len(parts) >= 3:
                doc_type = '_'.join(parts[:-2])
                company_name = parts[-1]
                if normalize_english:
                    company_name = self._normalize_fullwidth_english(company_name)
                    doc_type = self._normalize_fullwidth_english(doc_type)
                
                # スペースを除去（フォルダ名・ファイル名用）
                doc_type = re.sub(r'[\s　]+', '', doc_type)
                company_name = re.sub(r'[\s　]+', '', company_name)
                
                # 会社名の正規化（マッチング用）
                company_name_normalized = self._normalize_fullwidth_english(company_name)
                company_name_normalized = company_name_normalized.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
                
                # フォルダ名
                folder_base_name = f"{doc_type}_{company_name_normalized}"
            else:
                folder_base_name = rest_name
                doc_type = rest_name
                company_name = rest_name
                if normalize_english:
                    folder_base_name = self._normalize_fullwidth_english(folder_base_name)
                    doc_type = self._normalize_fullwidth_english(doc_type)
                    company_name = self._normalize_fullwidth_english(company_name)
                
                # スペースを除去（フォルダ名・ファイル名用）
                doc_type = re.sub(r'[\s　]+', '', doc_type)
                company_name = re.sub(r'[\s　]+', '', company_name)
                folder_base_name = re.sub(r'[\s　]+', '', folder_base_name)
                
                # 会社名の正規化（マッチング用）
                company_name_normalized = self._normalize_fullwidth_english(company_name)
                company_name_normalized = company_name_normalized.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

            # PDFを開いて各ページを解析
            doc = fitz.open(file_path)
            main_pages = []  # 本表ページのリスト
            receipt_pages = []  # 受信通知ページのリスト [(page_num, company_name, municipality), ...]

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # 受信通知ページ判定（厳格化）
                # 「納税者の氏名又は名称」AND「発行元」が両方含まれる場合のみ受信通知とする
                is_receipt = ("納税者の氏名又は名称" in text and "発行元" in text)

                if is_receipt:
                    # 受信通知ページ: 会社名と市区町村名を抽出
                    extracted_company, municipality = self._extract_company_and_municipality_from_receipt(text)
                    receipt_pages.append((page_num, extracted_company, municipality))
                    self._log(f"[受信通知検出] {filename} Page {page_num + 1}: 会社名={extracted_company}, 市区町村={municipality}")
                else:
                    # 本表ページ
                    main_pages.append(page_num)

            # 統一処理: フォルダ名はYYMM形式（固定）
            new_folder_name = f"{yymm}_{folder_base_name}"
            new_folder_path = os.path.join(folder_path, new_folder_name)

            # 統一処理: 本表ファイル名はラジオボタンで選択した接頭辞
            new_main_filename = f"{main_prefix}_{doc_type}.pdf"

            # フォルダ作成
            os.makedirs(new_folder_path, exist_ok=True)

            # 本表ページのみを新しいPDFとして保存
            if main_pages:
                new_doc = fitz.open()
                for page_num in main_pages:
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

                dest_file = os.path.join(new_folder_path, new_main_filename)
                new_doc.save(dest_file)
                new_doc.close()
                self._log(f"[本表処理] 本表ページ {len(main_pages)}ページ保存: {new_folder_name}/{new_main_filename}")

                # 処理結果ウィンドウに追加
                self.root.after(0, lambda fn=filename, nfn=f"{new_folder_name}/{new_main_filename}": self._add_result_success(
                    original_file=fn,
                    new_filename=nfn,
                    doc_type="給与支払報告書(本表)",
                    method="左側処理",
                    confidence="100%"
                ))
            else:
                self._log(f"[本表処理] 警告: 本表ページが見つかりません: {filename}")

            created_folders.append({
                'folder_path': new_folder_path,
                'folder_name': new_folder_name,
                'main_file': new_main_filename,
                'receipt_pages': receipt_pages,
                'doc': doc,  # 受信通知ページ抽出用のdocを保持
                'company_name': company_name,  # 元の会社名（フォルダ名用）
                'company_name_normalized': company_name_normalized  # 正規化済み会社名（マッチング用、スペース除去済み）
            })
            self._log(f"[本表処理] フォルダ作成: {new_folder_name} (受信通知: {len(receipt_pages)}ページ, 正規化会社名: {company_name_normalized})")

        return created_folders

    # ============================================================
    # 🆕 NEW Phase 3-3: 申請届出専用ヘルパーメソッド
    # ============================================================

    def _process_main_files_without_receipt(self, folder_path, yymm, main_prefix, normalize_english=False):
        """
        本表ファイルのみ処理してフォルダ作成（受信通知処理なし）
        申請届出用: 顧問先コードを除去
        
        Returns:
            created_folders: [(folder_path, folder_name, application_name), ...]
        """
        import fitz
        created_folders = []
        
        # 本表ファイルパターン: 数字_届出名称_顧問先コード_会社名.pdf
        main_file_pattern = re.compile(r'^(\d{2,4})_(.+)\.pdf$')
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            match = main_file_pattern.match(filename)
            if not match:
                continue
            
            # ファイル名解析
            old_prefix = match.group(1)
            rest_name = match.group(2)  # 例: "届出名称_0801A0094_会社名"
            
            # 🔧 修正: 顧問先コード（数字のみのパート）を除去
            # パターン: 届出名称_顧問先コード_会社名 → 届出名称_会社名
            parts = rest_name.split('_')
            if len(parts) >= 3:
                # 真ん中のパートが顧問先コード（数字+英字）かチェック
                # 例: "0801A0094" のようなパターン
                middle_part = parts[1]
                if re.match(r'^\d{4}[A-Z]\d{4}$', middle_part):
                    # 顧問先コードを除去: [届出名称, 会社名, ...] に再構成
                    rest_name = '_'.join([parts[0]] + parts[2:])
                    self._log(f"[申請届出] 顧問先コード除去: {middle_part}")
            
            # 英語半角変換
            if normalize_english:
                rest_name = self._normalize_fullwidth_english(rest_name)
            
            # フォルダ名: YYMM_新番号_届出名称_会社名
            new_folder_name = f"{yymm}_{main_prefix}_{rest_name}"
            new_folder_path = os.path.join(folder_path, new_folder_name)

            # フォルダ作成
            os.makedirs(new_folder_path, exist_ok=True)

            # 本表ファイルをコピー
            new_main_filename = f"{main_prefix}_{rest_name}.pdf"
            dest_file = os.path.join(new_folder_path, new_main_filename)
            shutil.copy2(file_path, dest_file)

            # 申請名を抽出（届出名称部分）
            application_name = rest_name.split('_')[0] if '_' in rest_name else rest_name

            created_folders.append((new_folder_path, new_folder_name, application_name))
            self._log(f"[本表処理] フォルダ作成: {new_folder_name} (申請名: {application_name})")

            # 処理結果を表示
            self.root.after(0, lambda fn=filename, nfn=f"{new_folder_name}/{new_main_filename}":
                self._add_result_success(
                    original_file=fn,
                    new_filename=nfn,
                    doc_type="申請届出(本表)",
                    method="左側処理",
                    confidence="100%"
                ))

        return created_folders

    def _process_application_receipt(self, receipt_pdf_path, created_folders, receipt_prefix, receipt_type):
        """
        申請届出の受信通知PDF処理（国税または地方税）
        まず1枚ずつ分割してからマッチング
        
        Args:
            receipt_pdf_path: 受信通知PDFのパス
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'application_name': ...}, ...]
            receipt_prefix: 受信通知プレフィックス（"02" or "9999"）
            receipt_type: "国税" or "地方税"
        """
        import fitz
        import tempfile
        import os
        
        try:
            doc = fitz.open(receipt_pdf_path)
            self._log(f"[{receipt_type}受信通知] ページ数: {len(doc)}")
            
            # Step 1: まず全ページを一時ファイルとして分割
            temp_pages = []
            temp_dir = tempfile.mkdtemp()
            
            for page_num in range(len(doc)):
                # 1ページずつ一時PDFを作成
                temp_pdf_path = os.path.join(temp_dir, f"page_{page_num + 1}.pdf")
                single_page_doc = fitz.open()
                single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                single_page_doc.save(temp_pdf_path)
                single_page_doc.close()
                
                # テキスト抽出
                page = doc[page_num]
                text = page.get_text()
                
                temp_pages.append({
                    'page_num': page_num + 1,
                    'pdf_path': temp_pdf_path,
                    'text': text
                })
                
                self._log(f"[{receipt_type}受信通知] Page {page_num + 1}: 分割完了")
            
            doc.close()
            
            # Step 2: 各分割ページから申請名を抽出してマッチング
            for page_info in temp_pages:
                page_num = page_info['page_num']
                temp_pdf = page_info['pdf_path']
                text = page_info['text']
                
                # 申請名を抽出
                application_name = self._extract_application_name_from_receipt(text, receipt_type)
                
                if not application_name:
                    self._log(f"[{receipt_type}受信通知] Page {page_num}: 申請名抽出失敗")
                    os.remove(temp_pdf)
                    continue
                
                self._log(f"[{receipt_type}受信通知] Page {page_num}: 申請名='{application_name}'")
                
                # マッチするフォルダを検索
                matched_folder = self._match_application_folder(application_name, created_folders)

                if matched_folder:
                    folder_info = matched_folder
                    folder_path = folder_info['folder_path']
                    folder_name = folder_info['folder_name']

                    # 統一処理: 受信通知ファイル名はラジオボタンで選択した接頭辞
                    base_filename = f"{receipt_prefix}_受信通知"
                    receipt_filename = f"{base_filename}.pdf"
                    dest_path = os.path.join(folder_path, receipt_filename)

                    # 既存ファイルがある場合は連番追加
                    counter = 2
                    while os.path.exists(dest_path):
                        receipt_filename = f"{base_filename}_{counter:02d}.pdf"
                        dest_path = os.path.join(folder_path, receipt_filename)
                        counter += 1

                    shutil.copy2(temp_pdf, dest_path)
                    self._log(f"[{receipt_type}受信通知] マッチ成功: {folder_name} → {receipt_filename}")

                    # 処理結果を表示
                    self.root.after(0, lambda pn=page_num+1, fn=folder_name, rfn=receipt_filename:
                        self._add_result_success(f"Page {pn}", f"{fn}/{rfn}", f"{receipt_type}受信通知", "フォルダ名マッチ", "高"))
                else:
                    self._log(f"[{receipt_type}受信通知] Page {page_num}: マッチするフォルダが見つかりません")
                
                os.remove(temp_pdf)
            
            # 一時ディレクトリ削除
            os.rmdir(temp_dir)
            
        except Exception as e:
            self._log(f"[{receipt_type}受信通知] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())

    def _extract_application_name_from_receipt(self, text, receipt_type):
        """
        受信通知から申請名を抽出
        🔧 修正: 複数行にまたがる種目/手続名に対応
        
        Args:
            text: PDFページのテキスト
            receipt_type: "国税" or "地方税"
        
        Returns:
            application_name: 抽出された申請名（正規化済み）
        """
        if receipt_type == "国税":
            # 国税パターン: "種目："の後ろ、次のフィールドまで
            # メール詳細形式: "種目 定款の定め等による申告期限の\n延長の特例の申請"
            match = re.search(r'種[\s\u3000]*目[\s\u3000]*[:：]?[\s\u3000\n]*(.*?)(?=備考|メッセージ|Page|file:|$)', text, re.DOTALL)
            if match:
                raw_name = match.group(1).strip()
                # 改行や余分な空白を除去
                raw_name = re.sub(r'\s+', '', raw_name)
                # 空の場合はNone
                if not raw_name:
                    return None
                self._log(f"[国税] 抽出された種目: '{raw_name}'")
                return self._normalize_application_name(raw_name)
        
        elif receipt_type == "地方税":
            # 地方税パターン: "手続名："の後ろ、次のフィールドまで
            # 受付状況照会結果形式: "手続名 法人設立・設置届出書" または複数行
            match = re.search(r'手続名[\s\u3000]*[:：]?[\s\u3000\n]*(.*?)(?=提出先|受付日|Page|file:|$)', text, re.DOTALL)
            if match:
                raw_name = match.group(1).strip()
                # 改行や余分な空白を除去
                raw_name = re.sub(r'\s+', '', raw_name)
                if not raw_name:
                    return None
                self._log(f"[地方税] 抽出された手続名: '{raw_name}'")
                return self._normalize_application_name(raw_name)
        
        return None

    def _normalize_application_name(self, name):
        """
        申請名を正規化（マッチング用）

        - 全角英数字を半角に変換
        - 括弧内の情報を除去
        - 余分な空白・記号を除去
        - 部分一致用に記号類を除去
        """
        if not name:
            return ""

        # 全角英数字を半角に変換
        normalized = self._normalize_fullwidth_english(name)

        # 全角数字を半角数字に変換
        normalized = normalized.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        # 括弧内を除去: （内容）、(内容)、【内容】、[内容]
        normalized = re.sub(r'[（\(].*?[）\)]', '', normalized)
        normalized = re.sub(r'[【\[].*?[】\]]', '', normalized)

        # 余分な空白・記号を除去（部分一致のため、・、書、等も除去）
        normalized = re.sub(r'\s+', '', normalized)
        normalized = re.sub(r'[・、。]', '', normalized)  # 中点、句読点除去

        return normalized

    def _match_application_folder(self, application_name, created_folders):
        """
        申請名に基づいてフォルダをマッチング（部分一致対応）
        
        Args:
            application_name: 受信通知から抽出した申請名
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'application_name': ...}, ...]
        
        Returns:
            matched_folder: folder_info dict or None
        """
        normalized_receipt_name = self._normalize_application_name(application_name)
        self._log(f"[マッチング] 受信通知から抽出: '{application_name}' → 正規化後: '{normalized_receipt_name}'")

        candidates = []

        for folder_info in created_folders:
            folder_path = folder_info['folder_path']
            folder_name = folder_info['folder_name']
            folder_app_name = folder_info['application_name']
            
            normalized_folder_name = self._normalize_application_name(folder_app_name)
            self._log(f"[マッチング] フォルダ比較: '{folder_app_name}' → 正規化後: '{normalized_folder_name}'")

            score = 0
            match_type = None

            # 完全一致
            if normalized_receipt_name == normalized_folder_name:
                score = 100
                match_type = "完全一致"
            # 部分一致
            elif normalized_receipt_name in normalized_folder_name or normalized_folder_name in normalized_receipt_name:
                score = 80
                match_type = "部分一致"
            # キーワード一致
            else:
                min_len = min(len(normalized_receipt_name), len(normalized_folder_name))
                if min_len >= 4:
                    match_len = int(min_len * 0.6)
                    if normalized_receipt_name[:match_len] == normalized_folder_name[:match_len]:
                        score = 60
                        match_type = "キーワード一致"

            # 共通キーワード検索
            if score == 0:
                important_keywords = ['申告期限', '延長', '法人設立', '給与支払', '源泉所得', '青色申告',
                                     '納期', '特例', '承認', '開設', '届出']

                receipt_keywords = [kw for kw in important_keywords if kw in normalized_receipt_name]
                folder_keywords = [kw for kw in important_keywords if kw in normalized_folder_name]

                common_keywords = set(receipt_keywords) & set(folder_keywords)
                if common_keywords:
                    score = 40 + len(common_keywords) * 5
                    match_type = f"共通キーワード一致({', '.join(common_keywords)})"

            if score > 0:
                candidates.append((score, match_type, folder_info))

        # スコアが最も高い候補を選択
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, match_type, folder_info = candidates[0]

            if best_score >= 40:
                self._log(f"[マッチング成功] {match_type} (スコア:{best_score}): {folder_info['folder_name']}")
                return folder_info

        return None

    def _save_receipt_page_to_folder(self, doc, page_num, folder_path, filename):
        """
        受信通知PDFの特定ページをフォルダに保存
        
        Args:
            doc: fitz.Document
            page_num: ページ番号（0-indexed）
            folder_path: 保存先フォルダパス
            filename: 保存ファイル名
        """
        import fitz
        
        # 新しいPDFを作成して1ページだけ追加
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        # 保存
        output_path = os.path.join(folder_path, filename)
        new_doc.save(output_path)
        new_doc.close()

    # ============================================================
    # 🆕 NEW Phase 3-4: 給与支払報告書専用ヘルパーメソッド
    # ============================================================

    def _process_payroll_receipts_from_file(self, receipt_pdf_path, created_folders, receipt_prefix):
        """
        給与支払報告書の受信通知PDF処理（別ファイル版）

        Args:
            receipt_pdf_path: 受信通知.pdfのパス
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'company_name_normalized': ...}, ...]
            receipt_prefix: 受信通知プレフィックス（"02" or "9999"）
        """
        import fitz

        try:
            doc = fitz.open(receipt_pdf_path)
            self._log(f"[給与支払報告書受信通知] ページ数: {len(doc)}")

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # 会社名と市区町村名を抽出
                company_name, municipality = self._extract_company_and_municipality_from_receipt(text)

                if not company_name:
                    self._log(f"[給与支払報告書受信通知] Page {page_num + 1}: 会社名抽出失敗")
                    continue

                self._log(f"[給与支払報告書受信通知] Page {page_num + 1}: 会社名='{company_name}', 市区町村='{municipality}'")

                # マッチするフォルダを検索（正規化済み会社名で比較）
                matched = False
                for folder_info in created_folders:
                    folder_company_normalized = folder_info['company_name_normalized']
                    if company_name == folder_company_normalized:
                        # 受信通知ページを保存
                        receipt_filename = f"{receipt_prefix}_受信通知.pdf"
                        receipt_path = os.path.join(folder_info['folder_path'], receipt_filename)

                        # ページを個別PDFとして保存
                        new_doc = fitz.open()
                        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                        new_doc.save(receipt_path)
                        new_doc.close()

                        self._log(f"[給与支払報告書受信通知] マッチ成功: {folder_info['folder_name']}/{receipt_filename}")

                        # 処理結果ウィンドウに追加
                        self.root.after(0, lambda pn=page_num+1, fn=folder_info['folder_name'], rfn=receipt_filename: self._add_result_success(
                            original_file=f"受信通知.pdf (ページ{pn})",
                            new_filename=f"{fn}/{rfn}",
                            doc_type="給与支払報告書(受信通知)",
                            method="左側処理",
                            confidence="100%"
                        ))

                        matched = True
                        break

                if not matched:
                    self._log(f"[給与支払報告書受信通知] Page {page_num + 1}: マッチするフォルダが見つかりません (会社名={company_name})")

            doc.close()

        except Exception as e:
            self._log(f"[給与支払報告書受信通知] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())

    def _process_payroll_receipts(self, receipt_pdf_path, created_folders, receipt_prefix):
        """
        給与支払報告書の受信通知PDF処理（旧版・互換性用）

        Args:
            receipt_pdf_path: 01_受信通知.pdfのパス
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'main_file': ...}, ...]
                           または [(folder_path, folder_name, application_name), ...]
            receipt_prefix: 受信通知プレフィックス（"02" or "9999"）
        """
        import fitz

        try:
            doc = fitz.open(receipt_pdf_path)
            self._log(f"[給与支払報告書受信通知] ページ数: {len(doc)}")

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # 会社名と市区町村名を抽出
                company_name, municipality = self._extract_company_and_municipality_from_receipt(text)

                if not company_name or not municipality:
                    self._log(f"[給与支払報告書受信通知] Page {page_num + 1}: 抽出失敗 (会社名={company_name}, 市区町村={municipality})")
                    continue

                self._log(f"[給与支払報告書受信通知] Page {page_num + 1}: 会社名='{company_name}', 市区町村='{municipality}'")

                # マッチするフォルダを検索
                matched_folder = self._match_payroll_folder(company_name, municipality, created_folders)
                
                if matched_folder:
                    # 辞書形式とタプル形式の両方に対応
                    if isinstance(matched_folder, dict):
                        folder_path = matched_folder['folder_path']
                        folder_name = matched_folder['folder_name']
                    else:
                        folder_path, folder_name, _ = matched_folder
                    
                    # 統一パラメータ: 受信通知ファイル名はラジオボタンで選択した接頭辞
                    receipt_filename = f"{receipt_prefix}_受信通知.pdf"
                    self._save_receipt_page_to_folder(doc, page_num, folder_path, receipt_filename)
                    self._log(f"[給与支払報告書受信通知] マッチ成功: {folder_name}")
                else:
                    self._log(f"[給与支払報告書受信通知] Page {page_num + 1}: マッチするフォルダが見つかりません")
            
            doc.close()
            
        except Exception as e:
            self._log(f"[給与支払報告書受信通知] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())

    def _extract_company_and_municipality_from_receipt(self, text):
        """
        受信通知から会社名と市区町村名を抽出

        Args:
            text: PDFページのテキスト

        Returns:
            (company_name, municipality): 抽出された会社名と市区町村名（正規化済み）
        """
        company_name = None
        municipality = None

        # 会社名抽出: "納税者の氏名又は名称"の次の行を取得
        # パターン: "納税者の\n氏名又は名称\n株式会社ＳｅａｓｉｄｅＬｉｎｋ"
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if '納税者' in line or '氏名又は名称' in line:
                # 次の行または次の次の行に会社名がある
                for j in range(i + 1, min(i + 4, len(lines))):
                    potential_company = lines[j].strip()
                    # 会社名らしい行を検出（株式会社、合同会社、有限会社などを含む）
                    # 除外キーワード: フォーム項目名や不要な情報
                    exclude_keywords = ['納税者', '氏名又は名称', '住所', '発行元', '電話', 'FAX', 'メール', '(', '）', '（', ')']
                    if potential_company and not any(kw in potential_company for kw in exclude_keywords):
                        company_name = potential_company
                        # 全てのスペースを除去（全角・半角）
                        company_name = re.sub(r'[\s　]+', '', company_name)
                        # 全角英数字を半角に変換
                        company_name = self._normalize_fullwidth_english(company_name)
                        company_name = company_name.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
                        break
                if company_name:
                    break

        # フォールバック: 正規表現でも試行
        if not company_name:
            company_match = re.search(r'納税者の[\s\n]*氏名又は名称[:：]?\s*(.+?)(?:\n|$)', text, re.MULTILINE | re.DOTALL)
            if company_match:
                company_name = company_match.group(1).strip()
                # 全てのスペースを除去（全角・半角）
                company_name = re.sub(r'[\s　]+', '', company_name)
                # 全角英数字を半角に変換
                company_name = self._normalize_fullwidth_english(company_name)
                company_name = company_name.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        # 市区町村名抽出: "発行元："の後ろ
        municipality_match = re.search(r'発行元[:：]\s*(.+?)[\s\n（\(]', text, re.MULTILINE)
        if municipality_match:
            municipality = municipality_match.group(1).strip()
            # 余分な情報を除去
            municipality = self._extract_municipality_name(municipality)

        return company_name, municipality

    def _extract_municipality_name(self, raw_municipality):
        """
        市区町村名を抽出・正規化
        
        Args:
            raw_municipality: 生の市区町村名（例: "藤沢市役所", "船橋市"）
        
        Returns:
            normalized_name: 正規化された市区町村名
        """
        if not raw_municipality:
            return ""
        
        # "〇〇市役所" → "〇〇市"
        # "〇〇区役所" → "〇〇区"
        # "〇〇町役場" → "〇〇町"
        # "〇〇村役場" → "〇〇村"
        
        normalized = raw_municipality
        normalized = re.sub(r'役所$', '', normalized)
        normalized = re.sub(r'役場$', '', normalized)
        
        # 余分な空白を除去
        normalized = re.sub(r'\s+', '', normalized)
        
        return normalized

    def _match_payroll_folder(self, company_name, municipality, created_folders):
        """
        会社名と市区町村名に基づいてフォルダをマッチング
        
        Args:
            company_name: 受信通知から抽出した会社名
            municipality: 受信通知から抽出した市区町村名
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'main_file': ...}, ...]
                           または [(folder_path, folder_name, application_name), ...]
        
        Returns:
            matched_folder: tuple or dict or None
        """
        normalized_company = self._normalize_application_name(company_name)
        normalized_municipality = self._normalize_application_name(municipality)
        
        for folder_info in created_folders:
            # 辞書形式とタプル形式の両方に対応
            if isinstance(folder_info, dict):
                folder_path = folder_info['folder_path']
                folder_name = folder_info['folder_name']
            else:
                folder_path, folder_name, _ = folder_info
            
            # フォルダ名から会社名と市区町村名を抽出
            # フォーマット想定: "YYMM_帳票名_会社名_市区町村名" など
            folder_text = self._normalize_application_name(folder_name)
            
            if normalized_company in folder_text and normalized_municipality in folder_text:
                if isinstance(folder_info, dict):
                    return folder_info
                else:
                    return folder_info
        
        return None

    # ============================================================
    # 🆕 NEW Phase 3-5: 償却資産申告書専用ヘルパーメソッド
    # ============================================================

    def _process_depreciable_receipts(self, receipt_pdf_path, created_folders, receipt_prefix):
        """
        償却資産申告書の受信通知PDF処理
        
        Args:
            receipt_pdf_path: 01_受信通知.pdfのパス
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'main_file': ...}, ...]
                           または [(folder_path, folder_name, application_name), ...]
            receipt_prefix: 受信通知プレフィックス（"02" or "9999"）
        """
        import fitz
        
        try:
            doc = fitz.open(receipt_pdf_path)
            self._log(f"[償却資産受信通知] ページ数: {len(doc)}")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # 会社名と税務署/都税事務所名を抽出
                company_name, tax_office = self._extract_company_and_office_from_receipt(text)
                
                if not company_name or not tax_office:
                    self._log(f"[償却資産受信通知] Page {page_num + 1}: 抽出失敗 (会社名={company_name}, 税務署={tax_office})")
                    continue
                
                self._log(f"[償却資産受信通知] Page {page_num + 1}: 会社名='{company_name}', 税務署='{tax_office}'")
                
                # マッチするフォルダを検索
                matched_folder = self._match_depreciable_folder(company_name, tax_office, created_folders)
                
                if matched_folder:
                    # 辞書形式とタプル形式の両方に対応
                    if isinstance(matched_folder, dict):
                        folder_path = matched_folder['folder_path']
                        folder_name = matched_folder['folder_name']
                    else:
                        folder_path, folder_name, _ = matched_folder
                    
                    # 統一パラメータ: 受信通知ファイル名はラジオボタンで選択した接頭辞
                    receipt_filename = f"{receipt_prefix}_受信通知.pdf"
                    self._save_receipt_page_to_folder(doc, page_num, folder_path, receipt_filename)
                    self._log(f"[償却資産受信通知] マッチ成功: {folder_name}")

                    # 処理結果を表示
                    self.root.after(0, lambda pn=page_num+1, fn=folder_name, rfn=receipt_filename:
                        self._add_result_success(
                            original_file=f"01_受信通知.pdf (ページ{pn})",
                            new_filename=f"{fn}/{rfn}",
                            doc_type="償却資産申告書(受信通知)",
                            method="左側処理",
                            confidence="100%"
                        ))
                else:
                    self._log(f"[償却資産受信通知] Page {page_num + 1}: マッチするフォルダが見つかりません")
            
            doc.close()
            
        except Exception as e:
            self._log(f"[償却資産受信通知] エラー: {str(e)}")
            import traceback
            self._log(traceback.format_exc())

    def _extract_company_and_office_from_receipt(self, text):
        """
        受信通知から会社名と税務署/都税事務所名を抽出
        
        Args:
            text: PDFページのテキスト
        
        Returns:
            (company_name, tax_office): 抽出された会社名と税務署名（正規化済み）
        """
        company_name = None
        tax_office = None
        
        lines = text.split('\n')
        
        # 会社名抽出: 「氏名又は名称」の次の行
        for i, line in enumerate(lines):
            if '氏名又は名称' in line:
                if i + 1 < len(lines):
                    company_name = lines[i + 1].strip()
                    # 改行、空白行、スペースを完全に除去
                    company_name = re.sub(r'[\s　\n\r\t]+', '', company_name)
                    if company_name:  # 空でない場合のみ採用
                        break
        
        # 税務署/都税事務所名抽出: 「発行元」の次の行
        for i, line in enumerate(lines):
            if '発行元' in line:
                if i + 1 < len(lines):
                    tax_office = lines[i + 1].strip()
                    # 改行、空白行、スペースを完全に除去
                    tax_office = re.sub(r'[\s　\n\r\t]+', '', tax_office)
                    if tax_office:  # 空でない場合のみ採用
                        break
        
        return company_name, tax_office

    def _match_depreciable_folder(self, company_name, tax_office, created_folders):
        """
        会社名と税務署名に基づいてフォルダをマッチング（2段階マッチング）
        
        Args:
            company_name: 受信通知から抽出した会社名
            tax_office: 受信通知から抽出した税務署/都税事務所名
            created_folders: [{'folder_path': ..., 'folder_name': ..., 'company_name_normalized': ...}, ...]
                           または [(folder_path, folder_name, application_name), ...]
        
        Returns:
            matched_folder: dict or tuple or None
        """
        # 正規化（スペース除去、全角英数字→半角）
        normalized_company = re.sub(r'[\s　]+', '', company_name)
        normalized_company = self._normalize_fullwidth_english(normalized_company)
        normalized_company = normalized_company.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        
        normalized_office = re.sub(r'[\s　]+', '', tax_office)
        normalized_office = self._normalize_fullwidth_english(normalized_office)
        
        self._log(f"[マッチング] 検索: 会社名='{normalized_company}', 税務署='{normalized_office}'")
        
        # Step 1: 会社名でマッチング候補を絞り込む
        candidates = []
        for folder_info in created_folders:
            # 辞書形式とタプル形式の両方に対応
            if isinstance(folder_info, dict):
                folder_name = folder_info['folder_name']
                company_from_folder = folder_info.get('company_name_normalized', '')
            else:
                folder_path, folder_name, _ = folder_info
                # フォルダ名から会社名を抽出（最後のアンダースコア以降）
                parts = folder_name.split('_')
                company_from_folder = parts[-1] if len(parts) > 0 else ''
            
            # 会社名が一致するかチェック
            if normalized_company == company_from_folder:
                candidates.append(folder_info)
                self._log(f"[マッチング] 会社名一致: {folder_name}")
        
        # Step 2: 候補が1つなら、それを返す
        if len(candidates) == 1:
            self._log(f"[マッチング] 会社名のみで一意にマッチ")
            return candidates[0]
        
        # Step 3: 候補が複数の場合は、税務署/市区町村名でさらに絞り込む
        if len(candidates) > 1:
            self._log(f"[マッチング] 候補が複数({len(candidates)}件): 税務署名で絞り込み")
            for candidate in candidates:
                if isinstance(candidate, dict):
                    folder_name = candidate['folder_name']
                else:
                    _, folder_name, _ = candidate
                
                # フォルダ名に税務署/市区町村名が含まれているかチェック
                if normalized_office in folder_name:
                    self._log(f"[マッチング] 税務署名でマッチ: {folder_name}")
                    return candidate
        
        # マッチしない場合
        if len(candidates) == 0:
            self._log(f"[マッチング] 失敗: 会社名'{normalized_company}'が見つかりません")
        else:
            self._log(f"[マッチング] 失敗: 税務署名'{normalized_office}'で絞り込めませんでした")
        
        return None

    def _get_final_receipt_name(self, receipt_prefix, folder_path, folder_name):
        """
        受信通知の最終ファイル名を決定

        Args:
            receipt_prefix: UIで選択された受信通知のプレフィックス（"02" または "9999"）
            folder_path: 格納先フォルダのパス
            folder_name: フォルダ名（YYMM_帳票名_会社名）

        Returns:
            最終ファイル名（例: "02_受信通知.pdf" または "9999_受信通知.pdf"）
        """
        # UIで選択されたプレフィックスを使用
        return f"{receipt_prefix}_受信通知.pdf"

    # _is_receipt_pdf メソッドは processors/receipt_detector.py に移動されました (Phase D-1)

    def _normalize_fullwidth_english(self, text):
        """全角英字を半角英字に変換"""
        if not text:
            return text

        result = []
        for char in text:
            code = ord(char)
            # 全角英大文字 (Ａ-Ｚ: 0xFF21-0xFF3A)
            if 0xFF21 <= code <= 0xFF3A:
                result.append(chr(code - 0xFEE0))
            # 全角英小文字 (ａ-ｚ: 0xFF41-0xFF5A)
            elif 0xFF41 <= code <= 0xFF5A:
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        return ''.join(result)

    def _left_rename_background(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
        """左側リネーム処理（フォルダ作成+受信通知分割・完全独立）"""
        try:
            # UI更新を強制して黒画面を防ぐ
            self.root.update_idletasks()

            import fitz  # PyMuPDF

            errors = []
            created_folders = []

            # ステップ1: 本表ファイル（任意の番号_で始まるPDF）を収集
            main_files = []
            receipt_pdf_path = None

            # 本表ファイルパターン: 2桁または4桁の数字_で始まる
            main_file_pattern = re.compile(r'^(\d{2,4})_(.+)\.pdf$')

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)

                if not os.path.isfile(file_path):
                    continue

                # 本表ファイル: 数字_で始まるPDFファイル
                match = main_file_pattern.match(filename)
                if match:
                    main_files.append((filename, file_path, match))
                # 受信通知ファイル（テキスト抽出で判定）
                elif filename.endswith('.pdf') and ReceiptDetector.is_receipt_pdf(file_path):
                    receipt_pdf_path = file_path
                    self._log(f"[統一処理] 受信通知検出: {filename}")

            # 本表ファイルがない場合
            if not main_files:
                self.root.after(0, lambda: messagebox.showerror("エラー", "番号_で始まる本表ファイル（PDF）が見つかりません"))
                self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))
                return

            # ステップ2: 各本表ファイルからフォルダを作成して移動
            for original_filename, original_file_path, match in main_files:
                # ファイル名から番号と残りの部分を抽出
                old_prefix = match.group(1)  # 元の番号（01, 02, 9999など）
                rest_name = match.group(2)   # 残りの部分（帳票名_顧問先...）

                # 英語半角変換が有効な場合は適用
                if normalize_english:
                    rest_name = self._normalize_fullwidth_english(rest_name)

                # rest_nameから帳票名と会社名を抽出（顧問先番号を除去）
                # 形式: 帳票名_顧問先番号_会社名 → 帳票名_会社名
                parts = rest_name.split('_')
                if len(parts) >= 3:
                    # 最初の部分が帳票名、最後から2番目が顧問先番号、最後が会社名
                    # 顧問先番号を除去: 帳票名 + 会社名
                    doc_type = '_'.join(parts[:-2])  # 帳票名（複数の_を含む可能性）
                    company_name = parts[-1]          # 会社名

                    # 英語半角変換が有効な場合は適用
                    if normalize_english:
                        company_name = self._normalize_fullwidth_english(company_name)
                        doc_type = self._normalize_fullwidth_english(doc_type)

                    folder_base_name = f"{doc_type}_{company_name}"
                else:
                    # パースできない場合はそのまま使用
                    folder_base_name = rest_name
                    doc_type = rest_name
                    if normalize_english:
                        folder_base_name = self._normalize_fullwidth_english(folder_base_name)
                        doc_type = self._normalize_fullwidth_english(doc_type)

                # 新しいファイル名: 選択した接頭辞_帳票名.pdf（会社名除去）
                new_filename = f"{main_prefix}_{doc_type}.pdf"

                # フォルダ名: YYMM_帳票名_会社名
                folder_name = f"{yymm}_{folder_base_name}"
                new_folder_path = os.path.join(folder_path, folder_name)

                try:
                    # フォルダ作成
                    os.makedirs(new_folder_path, exist_ok=True)

                    # 本表ファイルをコピーしてフォルダ内に配置（元ファイルは残す）
                    dest_file_path = os.path.join(new_folder_path, new_filename)
                    shutil.copy2(original_file_path, dest_file_path)

                    created_folders.append({
                        'folder_path': new_folder_path,
                        'folder_name': folder_name,
                        'main_file': new_filename
                    })

                    self._log(f"[左側] フォルダ作成+コピー: {original_filename} → {folder_name}/{new_filename} (元ファイルは保持)")

                    # 処理結果ウィンドウに追加
                    self._add_result_success(
                        original_file=original_filename,
                        new_filename=f"{folder_name}/{new_filename}",
                        doc_type="フォルダリネーム",
                        method="左側処理",
                        confidence="100%"
                    )

                except Exception as e:
                    errors.append(f"フォルダ作成エラー ({original_filename}): {str(e)}")

            # ステップ3: 受信通知PDFを分割して各フォルダに配置
            if receipt_pdf_path and created_folders:
                try:
                    doc = fitz.open(receipt_pdf_path)
                    total_pages = len(doc)

                    # マルチパターン受信通知検出による配置（v7.2.3-MULTI-PATTERN-RECEIPT）
                    matcher = CompanyNameMatcher()
                    folder_names = [f['folder_name'] for f in created_folders]
                    matched_count = 0
                    unmatched_pages = []

                    # 一時フォルダ作成
                    import tempfile
                    temp_dir = tempfile.mkdtemp(prefix="receipt_temp_")
                    self._log(f"[左側] 一時フォルダ作成: {temp_dir}")

                    # ステップ1: 全ページを連番付きで一時分割
                    temp_receipt_files = []  # [(temp_path, page_num, company_name), ...]

                    for page_num in range(total_pages):
                        # ページを抽出
                        page_doc = fitz.open()
                        page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

                        # 連番付きファイル名で一時保存
                        temp_filename = f"{receipt_prefix}_受信通知_{page_num + 1:02d}.pdf"
                        temp_path = os.path.join(temp_dir, temp_filename)

                        page_doc.save(temp_path)
                        page_doc.close()

                        # 会社名抽出
                        receipt_company = matcher.extract_company_name_from_receipt(receipt_pdf_path, page_num)

                        if receipt_company:
                            temp_receipt_files.append((temp_path, page_num, receipt_company))
                            self._log(f"[左側] 一時ファイル作成: {temp_filename} ({receipt_company})")
                        else:
                            self._log(f"[左側] 警告: ページ{page_num + 1} - 会社名抽出失敗")
                            unmatched_pages.append((page_num, "会社名抽出失敗"))

                    doc.close()

                    # ステップ2: 各ページを金額マッチングで最適フォルダに配置（v7.2.3）
                    for temp_path, page_num, receipt_company in temp_receipt_files:
                        # すべてのマッチするフォルダを取得
                        matched_folders = matcher.match_all_folders(receipt_company, folder_names, threshold=0.7)

                        if not matched_folders:
                            unmatched_pages.append((page_num, f"マッチング失敗: {receipt_company}"))
                            self._log(f"[左側] 警告: ページ{page_num + 1} - マッチング失敗（{receipt_company}）")
                            continue

                        if len(matched_folders) == 1:
                            # 単一フォルダ: 連番保持で即配置
                            folder_name, score = matched_folders[0]
                            self._log(f"[左側] ページ{page_num + 1} - 単一フォルダ: {folder_name} (スコア: {score:.2f})")

                            # フォルダ情報取得
                            folder_info = None
                            for f in created_folders:
                                if f['folder_name'] == folder_name:
                                    folder_info = f
                                    break

                            if folder_info:
                                receipt_filename = os.path.basename(temp_path)
                                receipt_dest_path = os.path.join(folder_info['folder_path'], receipt_filename)
                                shutil.move(temp_path, receipt_dest_path)

                                # 連番を削除してreceipt_prefix_帳票名_会社名.pdfにリネーム
                                final_filename = self._get_final_receipt_name(receipt_prefix, folder_info['folder_path'], folder_name)
                                final_dest_path = os.path.join(folder_info['folder_path'], final_filename)
                                if receipt_dest_path != final_dest_path:
                                    shutil.move(receipt_dest_path, final_dest_path)
                                    self._log(f"[左側] 受信通知リネーム: {receipt_filename} → {final_filename}")

                                matched_count += 1
                                self._log(f"[左側] 受信通知配置: {final_filename} → {folder_name}")

                                # 処理結果ウィンドウに追加
                                self._add_result_success(
                                    original_file=f"受信通知.pdf (ページ{page_num + 1})",
                                    new_filename=f"{folder_name}/{final_filename}",
                                    doc_type="受信通知分割",
                                    method="左側処理",
                                    confidence=f"{score:.0%}"
                                )
                            else:
                                unmatched_pages.append((page_num, f"フォルダ情報なし: {folder_name}"))

                        else:
                            # 複数フォルダ: 金額マッチングで最適フォルダ選択
                            self._log(f"[左側] ページ{page_num + 1} - 複数フォルダ検出: {len(matched_folders)}件（金額マッチング実行）")
                            self._log(f"[左側] 候補フォルダ: {[f[0] for f in matched_folders]}")

                            # 受信通知から金額抽出
                            receipt_amount = matcher.extract_amount_from_receipt(temp_path, 0)

                            if not receipt_amount:
                                self._log(f"[左側] 警告: 受信通知金額抽出失敗 - ページ{page_num + 1}")
                                unmatched_pages.append((page_num, "金額抽出失敗"))
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                                continue

                            self._log(f"[左側] 受信通知金額: {receipt_amount:,}円")

                            # 各フォルダの本表金額と比較
                            best_folder = None
                            best_diff = float('inf')
                            self._log(f"[左側] 金額マッチング開始:")

                            for folder_name, score in matched_folders:
                                # フォルダ情報取得
                                folder_info = None
                                for f in created_folders:
                                    if f['folder_name'] == folder_name:
                                        folder_info = f
                                        break

                                if not folder_info:
                                    self._log(f"[左側]   {folder_name}: フォルダ情報取得失敗")
                                    continue

                                # 本表金額抽出
                                main_pdf_path = os.path.join(folder_info['folder_path'], folder_info['main_file'])
                                self._log(f"[左側]   {folder_name}: 本表PDF={folder_info['main_file']}")
                                main_amount = matcher.extract_amount_from_main_pdf(main_pdf_path)

                                if main_amount:
                                    diff = abs(receipt_amount - main_amount)
                                    self._log(f"[左側]   {folder_name}: 本表={main_amount:,}円, 差額={diff:,}円")

                                    if diff < best_diff:
                                        best_diff = diff
                                        best_folder = (folder_name, folder_info)
                                else:
                                    self._log(f"[左側]   {folder_name}: 本表金額抽出失敗")

                            # 最適フォルダに配置
                            if best_folder:
                                folder_name, folder_info = best_folder
                                receipt_filename = os.path.basename(temp_path)
                                receipt_dest_path = os.path.join(folder_info['folder_path'], receipt_filename)
                                shutil.move(temp_path, receipt_dest_path)

                                # 連番を削除してreceipt_prefix_帳票名_会社名.pdfにリネーム
                                final_filename = self._get_final_receipt_name(receipt_prefix, folder_info['folder_path'], folder_name)
                                final_dest_path = os.path.join(folder_info['folder_path'], final_filename)
                                if receipt_dest_path != final_dest_path:
                                    shutil.move(receipt_dest_path, final_dest_path)
                                    self._log(f"[左側] 受信通知リネーム: {receipt_filename} → {final_filename}")

                                matched_count += 1
                                self._log(f"[左側] 金額マッチング成功: {final_filename} → {folder_name} (差額: {best_diff:,}円)")

                                # 処理結果ウィンドウに追加
                                self._add_result_success(
                                    original_file=f"受信通知.pdf (ページ{page_num + 1})",
                                    new_filename=f"{folder_name}/{final_filename}",
                                    doc_type="受信通知分割（金額マッチング）",
                                    method="左側処理",
                                    confidence=f"差額{best_diff:,}円"
                                )
                            else:
                                self._log(f"[左側] 警告: 金額マッチング失敗 - ページ{page_num + 1}")
                                unmatched_pages.append((page_num, "金額マッチング失敗"))
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)

                    # マッチング結果サマリー
                    self._log(f"[左側] 受信通知マッチング完了: 成功={matched_count}/{total_pages}, 失敗={len(unmatched_pages)}")

                    if unmatched_pages:
                        for page_num, reason in unmatched_pages:
                            errors.append(f"ページ{page_num + 1}: {reason}")

                    # 一時フォルダクリーンアップ
                    try:
                        remaining_files = os.listdir(temp_dir)
                        if remaining_files:
                            self._log(f"[左側] 警告: 一時フォルダに {len(remaining_files)} 件の未処理ファイル")
                            for f in remaining_files:
                                os.remove(os.path.join(temp_dir, f))
                        os.rmdir(temp_dir)
                        self._log(f"[左側] 一時フォルダ削除完了")
                    except Exception as e:
                        self._log(f"[左側] 警告: 一時フォルダ削除エラー: {e}")

                    # 元の受信通知PDFは削除せずに残す
                    self._log(f"[左側] 受信通知PDF分割完了（元ファイルは保持）")

                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    errors.append(f"受信通知分割エラー: {str(e)}")
                    self._log(f"[左側] ERROR: 受信通知分割エラー詳細:\n{error_detail}")
                    # 一時フォルダクリーンアップ
                    try:
                        if 'temp_dir' in locals() and os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                            self._log(f"[左側] エラー時一時フォルダ削除: {temp_dir}")
                    except Exception as cleanup_err:
                        self._log(f"[左側] 一時フォルダ削除失敗: {cleanup_err}")

            # UI更新（メインスレッドで実行）- 必ず実行
            self.root.after(0, self._left_finish, len(created_folders), len(main_files), errors)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("処理エラー", f"予期しないエラーが発生しました:\n{str(e)}"))
            self.root.after(0, lambda: self.left_execute_btn.config(state='normal'))

    def _left_finish(self, processed_count, total_count, errors):
        """左側リネーム処理完了（完全独立）"""
        self._log(f"[左側] _left_finish呼び出し: processed={processed_count}, total={total_count}, errors={len(errors)}")

        # ボタン再有効化
        self.left_execute_btn.config(state='normal')

        # 進捗表示更新
        if total_count == 0:
            self.left_progress_var.set("対象ファイルなし (01_形式)")
            messagebox.showinfo("完了", "01_で始まる本表ファイルが見つかりませんでした")
        else:
            self.left_progress_var.set(f"完了: {processed_count}/{total_count}フォルダ作成")

            # 結果ダイアログ（処理件数は表示しない）
            messagebox.showinfo("完了", "処理が完了しました")

    def run(self):
        """アプリケーション実行"""
        self._log("税務書類リネームシステム v8.6.1 起動 (受信通知検出改善版)")

        # パフォーマンス最適化: UI構築完了後にウィンドウを表示
        try:
            self.root.wm_attributes('-alpha', 1.0)  # 完全に表示
            self.root.update_idletasks()  # 初回描画を完了
        except:
            pass

        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV5()
    app.run()