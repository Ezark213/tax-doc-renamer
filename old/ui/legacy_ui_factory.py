#!/usr/bin/env python3
"""
Legacy UI Factory - tkinter Implementation
Phase 5: Implementation Execution - Backward Compatibility

Provides fallback tkinter-based UI factory for legacy mode
and systems without PySide6 support.
"""

import tkinter as tk
import os
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import sys

class LegacyUIFactory:
    """Factory for creating legacy tkinter UI components"""
    
    def __init__(self, migration_manager):
        self.migration_manager = migration_manager
        self.root = None
        
    def create_application(self) -> tk.Tk:
        """Create tkinter application"""
        if self.root is None:
            self.root = tk.Tk()
            self.root.title("税務書類リネームシステム v5.4.6-legacy")
            self.root.geometry("1200x800")
            
            # Apply modern styling to tkinter if available
            self._apply_modern_tkinter_styling()
        
        return self.root
    
    def _apply_modern_tkinter_styling(self):
        """Apply modern styling to tkinter components"""
        try:
            # Use ttk styling for better appearance
            style = ttk.Style()
            
            # Set theme
            available_themes = style.theme_names()
            if 'vista' in available_themes:
                style.theme_use('vista')
            elif 'clam' in available_themes:
                style.theme_use('clam')
            
            # Configure modern colors
            style.configure('TLabel', background='#FAFAFA', foreground='#424242')
            style.configure('TButton', 
                          background='#1976D2', 
                          foreground='white',
                          borderwidth=0,
                          relief='flat')
            style.map('TButton',
                     background=[('active', '#1565C0'),
                               ('pressed', '#0D47A1')])
            
            # Configure frame styling
            style.configure('TFrame', background='#FAFAFA')
            style.configure('TLabelFrame', background='#FAFAFA')
            
        except Exception as e:
            print(f"Warning: Could not apply modern tkinter styling: {e}")
    
    def create_main_window(self) -> 'LegacyMainWindow':
        """Create legacy main window"""
        return LegacyMainWindow(self.migration_manager, self.root)
    
    def create_drop_zone(self, parent, callback) -> 'LegacyDropZone':
        """Create legacy drop zone"""
        return LegacyDropZone(parent, callback)
    
    def show_message(self, parent, title: str, message: str, msg_type: str = "info"):
        """Show legacy message dialog"""
        if msg_type == "error":
            messagebox.showerror(title, message)
        elif msg_type == "warning":
            messagebox.showwarning(title, message)
        elif msg_type == "question":
            return messagebox.askyesno(title, message)
        else:
            messagebox.showinfo(title, message)



class LegacySettingsPanel(ttk.Frame):
    """Legacy settings panel using tkinter"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.municipality_inputs = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup settings UI"""
        # Main container with scrollbar if needed
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Year/Month settings
        year_frame = ttk.LabelFrame(scrollable_frame, text="年月設定", padding=10)
        year_frame.pack(fill='x', padx=10, pady=5)
        
        year_input_frame = ttk.Frame(year_frame)
        year_input_frame.pack(fill='x')
        
        ttk.Label(year_input_frame, text="手動入力年月 (YYMM):").pack(side='left')
        self.year_input = ttk.Entry(year_input_frame, width=10)
        self.year_input.insert(0, "2508")
        self.year_input.pack(side='left', padx=(10, 0))
        
        # Municipality settings
        municipality_frame = ttk.LabelFrame(scrollable_frame, text="自治体設定", padding=10)
        municipality_frame.pack(fill='x', padx=10, pady=5)
        
        # Prefecture list
        prefectures = [
            "", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        # Create 5 municipality sets
        for i in range(1, 6):
            set_frame = ttk.Frame(municipality_frame)
            set_frame.pack(fill='x', pady=2)
            
            ttk.Label(set_frame, text=f"セット{i}:", width=10).pack(side='left')
            
            prefecture_combo = ttk.Combobox(set_frame, values=prefectures, width=15)
            prefecture_combo.pack(side='left', padx=5)
            
            city_entry = ttk.Entry(set_frame, width=15)
            city_entry.pack(side='left', padx=5)
            
            self.municipality_inputs.append((prefecture_combo, city_entry))
        
        # Set default values
        if len(self.municipality_inputs) >= 3:
            self.municipality_inputs[0][0].set("東京都")
            self.municipality_inputs[1][0].set("愛知県")
            self.municipality_inputs[1][1].insert(0, "蒲郡市")
            self.municipality_inputs[2][0].set("福岡県")
            self.municipality_inputs[2][1].insert(0, "福岡市")
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings"""
        settings = {
            'year_month': self.year_input.get(),
            'municipality_sets': []
        }
        
        for i, (prefecture_combo, city_entry) in enumerate(self.municipality_inputs, 1):
            prefecture = prefecture_combo.get()
            city = city_entry.get()
            if prefecture and city:
                settings['municipality_sets'].append({
                    'set_number': i,
                    'prefecture': prefecture,
                    'city': city
                })
        
        return settings

class LegacyMainWindow:
    """Legacy main window using tkinter"""
    
    def __init__(self, migration_manager, root):
        self.migration_manager = migration_manager
        self.root = root

        
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
    
    def _setup_ui(self):
        """Setup main UI"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create paned window for resizable layout
        paned_window = ttk.PanedWindow(main_frame, orient='horizontal')
        paned_window.pack(fill='both', expand=True)
        
        # Left panel - Empty for future use
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        left_placeholder = ttk.Label(left_frame, text="将来拡張用エリア")
        left_placeholder.configure(foreground='gray')
        left_placeholder.pack(expand=True)
        
        # Right panel - All functionality
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=3)
        
        # Settings Panel (moved from left side)
        self.settings_panel = LegacySettingsPanel(right_frame)
        self.settings_panel.pack(fill='x', pady=10)
        

        
        # Main action button
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill='x', pady=20)
        
        self.process_btn = ttk.Button(button_frame, 
                                    text="⚡ フォルダ一括処理（分割&出力）", 
                                    command=self._select_folder_and_process)
        self.process_btn.pack(fill='x', ipady=10)
        
        # Results area
        results_notebook = ttk.Notebook(right_frame)
        results_notebook.pack(fill='both', expand=True, pady=10)
        
        # Results tab - 詳細一覧表示
        results_frame = ttk.Frame(results_notebook)
        
        # 処理結果詳細タイトル
        results_title = ttk.Label(results_frame, text="処理結果詳細", font=('Yu Gothic UI', 12, 'bold'))
        results_title.pack(pady=(5, 10))
        
        # Treeview for detailed results
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill='both', expand=True)
        
        columns = ('元ファイル名', '新ファイル名', '分類', '判定方法', '信頼度', 'マッチしたキーワード', '状態')
        self.result_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10)
        
        # カラムの設定
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
        
        # スクロールバー
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.result_tree.pack(side='left', fill='both', expand=True)
        tree_scrollbar.pack(side='right', fill='y')
        
        # 結果操作ボタン
        result_button_frame = ttk.Frame(results_frame)
        result_button_frame.pack(fill='x', pady=5)
        
        ttk.Button(result_button_frame, text="📁 出力フォルダを開く", command=self._open_output_folder).pack(side='left', padx=(0, 5))
        ttk.Button(result_button_frame, text="🔄 結果をクリア", command=self._clear_results).pack(side='left', padx=5)
        
        results_notebook.add(results_frame, text="📊 処理結果")
        
        # Log tab
        log_frame = ttk.Frame(results_notebook)
        self.log_text = tk.Text(log_frame, wrap='word')
        log_scroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scroll.pack(side='right', fill='y')
        results_notebook.add(log_frame, text="📝 ログ・デバッグ")

    
    def _setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="フォルダを選択", command=self._select_folder_and_process, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self._select_folder_and_process())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
    
    def _setup_status_bar(self):
        """Setup status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("準備完了 - Legacy UI")
        
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken', anchor='w')
        status_bar.pack(side='bottom', fill='x')
    

    
    def _select_folder_and_process(self):
        """フォルダ選択と一括処理を実行"""
        from tkinter import filedialog
        
        folder_path = filedialog.askdirectory(title="処理するフォルダを選択してください")
        if folder_path:
            self._process_folder(folder_path)
    
    def _process_folder(self, folder_path: str):
        """フォルダ処理を実行"""
        settings = self.settings_panel.get_settings()
        
        # Check settings
        if not settings['municipality_sets']:
            reply = messagebox.askyesno(
                "設定確認",
                "自治体が設定されていません。\n"
                "設定セクションで都道府県・市町村を入力してから処理を実行することを推奨します。\n\n"
                "そのまま続行しますか？"
            )
            if not reply:
                return
        
        self.status_var.set("処理中...")
        self.append_log("=== フォルダ一括処理開始 ===")
        self.append_log(f"対象フォルダ: {folder_path}")
        
        # 出力フォルダ情報を保存（ボタン用）
        yymm = settings.get('year_month', '2508')
        base_output_folder = os.path.join(folder_path, yymm)
        self._last_output_folder = base_output_folder
        
        try:
            # Import processing function
            from ui.file_processor import handle_folder_processing
            
            # 処理結果コールバックを定義
            def add_success_result(original_file, new_filename, doc_type, method, confidence, keywords):
                self.add_result_success(original_file, new_filename, doc_type, method, confidence, keywords)
            
            def add_error_result(original_file, error):
                self.add_result_error(original_file, error)
            
            ok, ng = handle_folder_processing(
                folder_path, 
                log=self.append_log, 
                settings=settings,
                success_callback=add_success_result,
                error_callback=add_error_result
            )
            
            self.status_var.set(f"完了：成功 {ok} 件 / 失敗 {ng} 件")
            self.append_log(f"=== 完了：成功 {ok} 件 / 失敗 {ng} 件 ===")
            
        except Exception as e:
            self.status_var.set("エラーが発生しました")
            self.append_log(f"=== エラー: {e} ===")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")
    

    
    def append_log(self, text: str):
        """Append to log"""
        self.log_text.insert('end', text + '\n')
        self.log_text.see('end')

    def add_result_success(self, original_file: str, new_filename: str, doc_type: str, method: str, confidence: str, matched_keywords: list = None):
        """成功結果を処理結果一覧に追加"""
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

    def add_result_error(self, original_file: str, error: str):
        """エラー結果を処理結果一覧に追加"""
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
        try:
            import subprocess
            import platform
            
            # 最後に処理したフォルダを開く（簡易実装）
            if hasattr(self, '_last_output_folder') and self._last_output_folder:
                if platform.system() == "Windows":
                    subprocess.run(f'explorer "{self._last_output_folder}"', shell=True)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", self._last_output_folder])
                else:  # Linux
                    subprocess.run(["xdg-open", self._last_output_folder])
            else:
                self.migration_manager.ui_factory.show_message(
                    self.root, "情報", "出力フォルダが見つかりません。", "info"
                )
        except Exception as e:
            self.migration_manager.ui_factory.show_message(
                self.root, "エラー", f"フォルダを開けませんでした: {e}", "error"
            )

    def _clear_results(self):
        """処理結果一覧をクリア"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.append_log("処理結果一覧をクリアしました")
    
    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "バージョン情報",
            "税務書類リネームシステム v5.4.6-legacy\n\n"
            "Legacy UI with tkinter\n"
            "Backward compatibility mode\n\n"
            "© 2025 Tax Document System"
        )