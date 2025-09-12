#!/usr/bin/env python3
"""
ドラッグ&ドロップ機能 v5.2
直感的ファイル選択インターフェース + 束ねPDF限定オート分割対応
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import List, Callable, Optional, Dict, Any
from pathlib import Path

class DragDropWidget:
    """ドラッグ&ドロップ機能を提供するウィジェット"""
    
    def __init__(self, parent_widget: tk.Widget, callback: Callable[[List[str]], None]):
        """
        初期化
        
        Args:
            parent_widget: ドロップを受け付ける親ウィジェット
            callback: ファイルドロップ時に呼ばれるコールバック関数
        """
        self.parent = parent_widget
        self.callback = callback
        self.supported_extensions = {'.pdf', '.csv'}
        
        # ドラッグ&ドロップの設定
        self._setup_drag_drop()
        
        # 視覚効果用の変数
        self.original_bg = None
        self.is_dragging_over = False

    def _setup_drag_drop(self):
        """ドラッグ&ドロップイベントの設定"""
        try:
            # Windowsの場合のドラッグ&ドロップ設定
            if os.name == 'nt':
                self._setup_windows_drag_drop()
            else:
                # Unix系の場合（基本的なバインド）
                self._setup_unix_drag_drop()
                
        except Exception as e:
            print(f"ドラッグ&ドロップ設定エラー: {e}")

    def _setup_windows_drag_drop(self):
        """Windows用ドラッグ&ドロップ設定"""
        try:
            # tkinterdndライブラリを使用（利用可能な場合）
            try:
                from tkinterdnd2 import DND_FILES, TkinterDnD
                
                # 親ウィンドウをTkinterDnDに変換
                if hasattr(self.parent, 'tk'):
                    root = self.parent.tk
                    if not isinstance(root, TkinterDnD.Tk):
                        # 既存のTkをTkinterDnDに変換
                        pass
                
                # ドロップイベントの登録
                self.parent.drop_target_register(DND_FILES)
                self.parent.dnd_bind('<<Drop>>', self._on_drop)
                self.parent.dnd_bind('<<DragEnter>>', self._on_drag_enter)
                self.parent.dnd_bind('<<DragLeave>>', self._on_drag_leave)
                
            except ImportError:
                # tkinterdndが利用できない場合は代替手段
                self._setup_alternative_drag_drop()
                
        except Exception as e:
            print(f"Windows D&D設定エラー: {e}")
            self._setup_alternative_drag_drop()

    def _setup_unix_drag_drop(self):
        """Unix系用ドラッグ&ドロップ設定"""
        # 基本的なマウスイベントバインド
        self.parent.bind('<Button-1>', self._on_click)
        self.parent.bind('<B1-Motion>', self._on_drag)
        self.parent.bind('<ButtonRelease-1>', self._on_release)

    def _setup_alternative_drag_drop(self):
        """代替ドラッグ&ドロップ設定"""
        # クリックイベントでファイル選択ダイアログを開く
        self.parent.bind('<Button-1>', self._on_click_fallback)
        self.parent.bind('<Double-Button-1>', self._on_double_click_fallback)

    def _on_drop(self, event):
        """ファイルドロップイベント処理"""
        try:
            files = event.data.split()
            valid_files = self._filter_valid_files(files)
            
            if valid_files:
                self.callback(valid_files)
            else:
                self._show_invalid_files_message(files)
                
        except Exception as e:
            print(f"ドロップ処理エラー: {e}")
        finally:
            self._reset_visual_state()

    def _on_drag_enter(self, event):
        """ドラッグエンター時の視覚効果"""
        self.is_dragging_over = True
        self._update_visual_state()

    def _on_drag_leave(self, event):
        """ドラッグリーブ時の視覚効果"""
        self.is_dragging_over = False
        self._reset_visual_state()

    def _on_click(self, event):
        """クリックイベント（Unix系）"""
        pass

    def _on_drag(self, event):
        """ドラッグイベント（Unix系）"""
        pass

    def _on_release(self, event):
        """リリースイベント（Unix系）"""
        pass

    def _on_click_fallback(self, event):
        """代替クリックイベント"""
        from tkinter import filedialog
        
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
            valid_files = self._filter_valid_files(list(files))
            if valid_files:
                self.callback(valid_files)

    def _on_double_click_fallback(self, event):
        """代替ダブルクリックイベント（フォルダ選択）"""
        from tkinter import filedialog
        
        folder = filedialog.askdirectory(title="フォルダを選択")
        if folder:
            files = self._get_files_from_folder(folder)
            valid_files = self._filter_valid_files(files)
            if valid_files:
                self.callback(valid_files)

    def _filter_valid_files(self, files: List[str]) -> List[str]:
        """有効なファイルをフィルタリング"""
        valid_files = []
        
        for file_path in files:
            try:
                # ファイルパスのクリーニング
                cleaned_path = file_path.strip('{}').strip('"').strip("'")
                
                if os.path.isfile(cleaned_path):
                    ext = os.path.splitext(cleaned_path)[1].lower()
                    if ext in self.supported_extensions:
                        valid_files.append(cleaned_path)
                elif os.path.isdir(cleaned_path):
                    # ディレクトリの場合、中のファイルを取得
                    folder_files = self._get_files_from_folder(cleaned_path)
                    valid_files.extend(self._filter_valid_files(folder_files))
                    
            except Exception as e:
                print(f"ファイル処理エラー: {e}")
                continue
        
        return valid_files

    def _get_files_from_folder(self, folder_path: str) -> List[str]:
        """フォルダ内の対応ファイルを取得"""
        files = []
        try:
            for root, dirs, filenames in os.walk(folder_path):
                for filename in filenames:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in self.supported_extensions:
                        files.append(os.path.join(root, filename))
        except Exception as e:
            print(f"フォルダ読み取りエラー: {e}")
        
        return files

    def _update_visual_state(self):
        """ドラッグオーバー時の視覚状態更新"""
        try:
            if self.is_dragging_over:
                if self.original_bg is None:
                    self.original_bg = self.parent.cget('bg')
                self.parent.config(bg='lightblue', relief='sunken')
        except Exception:
            pass

    def _reset_visual_state(self):
        """視覚状態をリセット"""
        try:
            if self.original_bg is not None:
                self.parent.config(bg=self.original_bg, relief='flat')
            self.is_dragging_over = False
        except Exception:
            pass

    def _show_invalid_files_message(self, files: List[str]):
        """無効ファイルのメッセージ表示"""
        from tkinter import messagebox
        
        invalid_extensions = set()
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in self.supported_extensions:
                invalid_extensions.add(ext if ext else '拡張子なし')
        
        if invalid_extensions:
            ext_list = ', '.join(invalid_extensions)
            messagebox.showwarning(
                "対応していないファイル",
                f"以下の拡張子には対応していません: {ext_list}\n\n"
                f"対応ファイル: PDF, CSV"
            )

class DropZoneFrame(ttk.Frame):
    """ドロップゾーン専用フレーム"""
    
    def __init__(self, parent, callback: Callable[[List[str]], None], **kwargs):
        """初期化"""
        super().__init__(parent, **kwargs)
        
        self.callback = callback
        
        # ドロップゾーンの外観設定
        self.configure(relief='solid', borderwidth=2)
        
        # ラベル表示
        self.label = ttk.Label(
            self, 
            text="📁 ファイルをここにドラッグ&ドロップ\n\n対応形式: PDF, CSV\n\nクリックでファイル選択",
            font=('Arial', 12),
            anchor='center',
            justify='center'
        )
        self.label.pack(expand=True, fill='both', padx=20, pady=20)
        
        # ドラッグ&ドロップ機能を追加
        self.drag_drop = DragDropWidget(self, self.callback)
        
        # ホバー効果
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.label.bind('<Enter>', self._on_enter)
        self.label.bind('<Leave>', self._on_leave)

    def _on_enter(self, event):
        """マウスオーバー時の効果"""
        self.configure(relief='solid', borderwidth=2)

    def _on_leave(self, event):
        """マウスアウト時の効果"""
        self.configure(relief='solid', borderwidth=2)

class AutoSplitControlFrame(ttk.Frame):
    """フォルダ処理制御フレーム（簡素化版）"""
    
    def __init__(self, parent, **kwargs):
        """初期化"""
        super().__init__(parent, **kwargs)
        
        # コールバック関数
        self.folder_process_callback = None
        
        # 選択されたフォルダパス
        self.selected_folder = None
        
        self._create_controls()
    
    def _create_controls(self):
        """制御UI作成"""
        # タイトル
        title_label = ttk.Label(self, text="税務書類自動処理", 
                               font=('Arial', 11, 'bold'), foreground='blue')
        title_label.pack(pady=(0, 10))
        
        # フォルダ選択セクション
        folder_frame = ttk.LabelFrame(self, text="処理フォルダ")
        folder_frame.pack(fill='x', pady=(0, 10))
        
<<<<<<< HEAD
        # 自動分割トグル
        auto_split_cb = ttk.Checkbutton(
            settings_frame, 
            text="アップロード時に束ねPDFを自動分割 (推奨)", 
            variable=self.auto_split_bundles
        )
        auto_split_cb.pack(anchor='w', padx=10, pady=5)
        
        # デバッグモード（必要時のみ表示）
        debug_cb = ttk.Checkbutton(
            settings_frame,
            text="詳細ログ出力 (Debug)",
            variable=self.debug_mode
        )
        debug_cb.pack(anchor='w', padx=10, pady=2)
        
        # 情報テキスト
        info_text = ("対象: 地方税系(1003/1013/1023 + 1004/2004)、国税系(0003/0004 + 3003/3004)の束ね")
        info_label = ttk.Label(settings_frame, text=info_text, 
                              font=('Arial', 8), foreground='gray')
        info_label.pack(anchor='w', padx=10, pady=2)
        
        # アクションボタンセクション - v5.4.2 簡素化版
        action_frame = ttk.LabelFrame(self, text="ワンボタン処理")
        action_frame.pack(fill='x', pady=(0, 10))
        
        # メイン処理ボタン: フォルダ選択→リネーム一括処理
        self.batch_button = ttk.Button(
            action_frame,
            text="🚀 フォルダ選択→一括リネーム実行",
            command=self._on_batch_process,
            style='Accent.TButton'
        )
        self.batch_button.pack(fill='x', padx=10, pady=10)
        
        # 簡素化: その他のボタンは削除済み
=======
        # フォルダ選択ボタン
        self.folder_button = ttk.Button(
            folder_frame,
            text="📁 フォルダを選択",
            command=self._select_folder,
            style='Accent.TButton'
        )
        self.folder_button.pack(fill='x', padx=10, pady=5)
        
        # 選択されたフォルダパスの表示
        self.folder_path_var = tk.StringVar(value="フォルダが選択されていません")
        folder_path_label = ttk.Label(
            folder_frame, 
            textvariable=self.folder_path_var,
            font=('Arial', 8), 
            foreground='gray'
        )
        folder_path_label.pack(anchor='w', padx=10, pady=2)
        
        # 処理説明
        info_text = "フォルダ内のPDF・CSVファイルを自動分割・リネームし、YYMMフォルダに保存します"
        info_label = ttk.Label(folder_frame, text=info_text, 
                              font=('Arial', 8), foreground='gray',
                              wraplength=350)
        info_label.pack(anchor='w', padx=10, pady=2)
>>>>>>> f34e0637937544d25d4c233cbbe444a7219a2349
        
        # プログレス表示エリア
        self.progress_var = tk.StringVar(value="待機中...")
        self.progress_label = ttk.Label(self, textvariable=self.progress_var,
                                       font=('Arial', 9), foreground='green')
        self.progress_label.pack(pady=5)
    
    def _select_folder(self):
        """フォルダ選択ダイアログを開く"""
        from tkinter import filedialog
        
        folder_path = filedialog.askdirectory(title="処理するフォルダを選択してください")
        if folder_path:
            self.selected_folder = folder_path
            self.folder_path_var.set(f"選択: {folder_path}")
            
            # フォルダが選択されたら自動処理を開始
            if self.folder_process_callback:
                self.folder_process_callback(folder_path)
    
<<<<<<< HEAD
    # 簡素化: 分割のみ・強制分割ボタンは削除
    
    def set_callbacks(self, batch_callback=None):
        """コールバック関数を設定 - v5.4.2 簡素化版"""
        self.batch_process_callback = batch_callback
=======
    def set_callbacks(self, folder_callback=None):
        """コールバック関数を設定"""
        self.folder_process_callback = folder_callback
>>>>>>> f34e0637937544d25d4c233cbbe444a7219a2349
    
    def update_progress(self, message: str, color: str = 'green'):
        """プログレス表示更新"""
        self.progress_var.set(message)
        self.progress_label.config(foreground=color)
    
    def get_settings(self) -> Dict[str, Any]:
        """現在の設定を取得（機能常時有効のため固定値）"""
        return {
            'auto_split_bundles': True,
            'debug_mode': False
        }
    
    def set_button_states(self, enabled: bool):
        """ボタンの有効/無効を設定 - v5.4.2 簡素化版"""
        state = 'normal' if enabled else 'disabled'
<<<<<<< HEAD
        self.batch_button.config(state=state)
=======
        self.folder_button.config(state=state)
>>>>>>> f34e0637937544d25d4c233cbbe444a7219a2349



