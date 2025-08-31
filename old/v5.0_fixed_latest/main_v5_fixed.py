#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 修正版メインアプリケーション
セットベース連番システム + 画像認識突合チェック対応
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
from core.ocr_engine import OCREngine
from core.csv_processor import CSVProcessor
from core.classification_v5_fixed import DocumentClassifierV5Fixed, ValidationAlert  # 修正版を使用
from ui.drag_drop import DropZoneFrame

class TaxDocumentRenamerV5Fixed:
    """税務書類リネームシステム v5.0 修正版メインクラス"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.0 修正版 (セットベース連番)")
        self.root.geometry("1200x800")
        
        # v5.0 修正版 コアエンジンの初期化
        self.pdf_processor = PDFProcessor()
        self.ocr_engine = OCREngine()
        self.csv_processor = CSVProcessor()
        self.classifier_v5_fixed = DocumentClassifierV5Fixed(debug_mode=True, log_callback=self._log)
        
        # UI変数
        self.files_list = []
        self.split_processing = False
        self.rename_processing = False
        self.processing_results = []
        self.validation_alerts = []
        
        # UI構築
        self._create_ui()

    def _create_ui(self):
        """UIの構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="税務書類リネームシステム v5.0 修正版 (セットベース連番)", 
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # v5.0 修正版 新機能の説明
        info_label = ttk.Label(
            main_frame,
            text="✨ 修正版機能: セットベース連番・OCR突合チェック・アラート機能",
            font=('Arial', 10),
            foreground='blue'
        )
        info_label.pack(pady=(0, 10))
        
        # セット情報表示
        set_info_frame = ttk.LabelFrame(main_frame, text="自治体セット設定")
        set_info_frame.pack(fill='x', pady=(0, 10))
        
        set_info_text = tk.Text(set_info_frame, height=4, width=80, state='disabled', font=('Consolas', 9))
        set_info_text.pack(padx=5, pady=5)
        
        # セット情報を表示
        set_info_text.config(state='normal')
        set_info_text.insert('end', "セット1: 東京都 (1001, 1003, 1004) - 市町村なし\\n")
        set_info_text.insert('end', "セット2: 愛知県蒲郡市 (1011, 1013, 1014) + (2001, 2003, 2004)\\n")
        set_info_text.insert('end', "セット3: 福岡県福岡市 (1021, 1023, 1024) + (2011, 2013, 2014)\\n")
        set_info_text.insert('end', "※OCR画像認識と突合チェックでアラート表示")
        set_info_text.config(state='disabled')
        
        # ノートブック（タブ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # タブ1: ファイル選択・設定
        self.file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_frame, text="📁 ファイル選択・設定")
        self._create_file_tab()
        
        # タブ2: 処理結果・アラート
        self.result_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.result_frame, text="📊 処理結果・アラート")
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
        
        # 処理オプション
        options_frame = ttk.LabelFrame(right_frame, text="処理オプション")
        options_frame.pack(fill='x', pady=(0, 10))
        
        self.auto_split_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="PDF自動分割", variable=self.auto_split_var).pack(anchor='w')
        
        self.ocr_enhanced_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="OCR強化モード", variable=self.ocr_enhanced_var).pack(anchor='w')
        
        # 修正版専用オプション
        self.set_based_var = tk.BooleanVar(value=True)
        set_checkbox = ttk.Checkbutton(
            options_frame, 
            text="セットベース連番モード（推奨）", 
            variable=self.set_based_var
        )
        set_checkbox.pack(anchor='w')
        
        self.alert_enabled_var = tk.BooleanVar(value=True)
        alert_checkbox = ttk.Checkbutton(
            options_frame, 
            text="OCR突合チェック・アラート機能", 
            variable=self.alert_enabled_var
        )
        alert_checkbox.pack(anchor='w')
        
        # 処理ボタン
        process_frame = ttk.Frame(right_frame)
        process_frame.pack(fill='x', pady=20)
        
        # リネーム実行ボタン（修正版）
        self.rename_button = ttk.Button(
            process_frame, 
            text="✏️ リネーム実行 (修正版)", 
            command=self._start_rename_processing,
            style='Accent.TButton'
        )
        self.rename_button.pack(fill='x', pady=(0, 5))
        
        # プログレスバー
        self.progress = ttk.Progressbar(process_frame, mode='determinate')
        self.progress.pack(fill='x', pady=(10, 0))

    def _create_result_tab(self):
        """処理結果・アラートタブの作成"""
        # 上下分割
        paned = ttk.PanedWindow(self.result_frame, orient='vertical')
        paned.pack(fill='both', expand=True)
        
        # 上部: 処理結果
        result_frame = ttk.LabelFrame(paned, text="処理結果")
        paned.add(result_frame, weight=1)
        
        # 処理結果表示用のTreeview
        columns = ('元ファイル名', '新ファイル名', 'セット', '信頼度', 'ステータス')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings')
        
        for col in columns:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=150)
        
        result_scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_tree.pack(side='left', fill='both', expand=True)
        result_scrollbar.pack(side='right', fill='y')
        
        # 下部: アラート表示
        alert_frame = ttk.LabelFrame(paned, text="アラート・警告")
        paned.add(alert_frame, weight=1)
        
        self.alert_text = tk.Text(alert_frame, height=10, wrap='word', font=('Consolas', 9))
        alert_scrollbar = ttk.Scrollbar(alert_frame, orient='vertical', command=self.alert_text.yview)
        self.alert_text.configure(yscrollcommand=alert_scrollbar.set)
        
        self.alert_text.pack(side='left', fill='both', expand=True)
        alert_scrollbar.pack(side='right', fill='y')

    def _create_log_tab(self):
        """ログ・デバッグタブの作成"""
        log_frame = ttk.Frame(self.log_frame)
        log_frame.pack(fill='both', expand=True)
        
        ttk.Label(log_frame, text="デバッグログ", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        self.log_text = tk.Text(log_frame, wrap='word', font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # ログ制御ボタン
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(log_button_frame, text="🗑️ ログクリア", command=self._clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(log_button_frame, text="💾 ログ保存", command=self._save_log).pack(side='left')

    def _log(self, message: str):
        """ログメッセージの表示"""
        if hasattr(self, 'log_text'):
            self.log_text.insert('end', message + '\\n')
            self.log_text.see('end')

    def _on_files_dropped(self, files):
        """ファイルドロップ時の処理"""
        self.files_list.extend(files)
        self._update_files_listbox()

    def _select_files(self):
        """ファイル選択ダイアログ"""
        files = filedialog.askopenfilenames(
            title="PDFファイルを選択",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if files:
            self.files_list.extend(files)
            self._update_files_listbox()

    def _select_folder(self):
        """フォルダ選択ダイアログ"""
        folder = filedialog.askdirectory(title="PDFファイルが含まれるフォルダを選択")
        if folder:
            pdf_files = list(Path(folder).glob("*.pdf"))
            self.files_list.extend([str(f) for f in pdf_files])
            self._update_files_listbox()

    def _clear_files(self):
        """ファイルリストクリア"""
        self.files_list.clear()
        self._update_files_listbox()

    def _update_files_listbox(self):
        """ファイルリストボックス更新"""
        self.files_listbox.delete(0, 'end')
        for file_path in self.files_list:
            self.files_listbox.insert('end', os.path.basename(file_path))

    def _start_rename_processing(self):
        """リネーム処理開始（修正版）"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルがありません。")
            return
        
        if self.rename_processing:
            messagebox.showinfo("情報", "既に処理中です。")
            return
        
        # UI無効化
        self.rename_button.config(state='disabled')
        self.rename_processing = True
        
        # 結果・アラートクリア
        self._clear_results()
        
        # 別スレッドで処理実行
        thread = threading.Thread(target=self._process_files_fixed)
        thread.daemon = True
        thread.start()

    def _process_files_fixed(self):
        """ファイル処理（修正版）"""
        try:
            total_files = len(self.files_list)
            self.progress.config(maximum=total_files)
            
            for i, file_path in enumerate(self.files_list):
                self._log(f"処理中: {os.path.basename(file_path)}")
                
                # OCRテキスト抽出
                extracted_text = self.pdf_processor.extract_text_from_pdf(file_path)
                
                # セットベース分類（修正版）
                if self.set_based_var.get():
                    document_type, alerts = self.classifier_v5_fixed.classify_document_v5_fixed(
                        extracted_text, os.path.basename(file_path)
                    )
                else:
                    # 従来版も利用可能
                    classification_result = self.classifier_v5_fixed._check_highest_priority_conditions(
                        extracted_text, os.path.basename(file_path)
                    )
                    document_type = classification_result.document_type if classification_result else "0000_未分類"
                    alerts = []
                
                # 年月付与
                year_month = self.year_month_var.get()
                final_filename = f"{document_type}_{year_month}.pdf"
                
                # 結果記録
                detected_set = self._extract_set_info_from_alerts(alerts)
                confidence = self._calculate_overall_confidence(alerts)
                status = self._determine_status(alerts)
                
                result = {
                    'original': os.path.basename(file_path),
                    'new': final_filename,
                    'set': detected_set,
                    'confidence': confidence,
                    'status': status,
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
            self.root.after(0, lambda: self._show_error(f"処理中にエラーが発生しました: {str(e)}"))
        finally:
            self.root.after(0, self._processing_finished)

    def _extract_set_info_from_alerts(self, alerts: List[ValidationAlert]) -> str:
        """アラートからセット情報抽出"""
        for alert in alerts:
            if "セット" in alert.message:
                import re
                match = re.search(r'セット(\d+)', alert.message)
                if match:
                    return f"セット{match.group(1)}"
        return "不明"

    def _calculate_overall_confidence(self, alerts: List[ValidationAlert]) -> str:
        """全体信頼度計算"""
        if not alerts:
            return "0%"
        
        total_confidence = sum(alert.confidence for alert in alerts) / len(alerts)
        return f"{int(total_confidence * 100)}%"

    def _determine_status(self, alerts: List[ValidationAlert]) -> str:
        """ステータス判定"""
        has_mismatch = any(alert.alert_type == "MISMATCH" for alert in alerts)
        has_ambiguous = any(alert.alert_type == "AMBIGUOUS" for alert in alerts)
        
        if has_mismatch:
            return "⚠️ 要確認"
        elif has_ambiguous:
            return "⚠️ 曖昧"
        else:
            return "✅ 正常"

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
        alert_message = f"🔔 {os.path.basename(file_path)}: {alert.message}\\n"
        if alert.suggestions:
            alert_message += f"   💡 提案: {', '.join(alert.suggestions)}\\n"
        alert_message += "\\n"
        
        self.alert_text.insert('end', alert_message)
        self.alert_text.see('end')

    def _clear_results(self):
        """結果・アラートクリア"""
        self.processing_results.clear()
        self.validation_alerts.clear()
        
        # TreeViewクリア
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # アラートテキストクリア
        self.alert_text.delete('1.0', 'end')

    def _processing_complete(self):
        """処理完了"""
        self._log("✅ 全ファイルの処理が完了しました")
        messagebox.showinfo("完了", "リネーム処理が完了しました。")

    def _processing_finished(self):
        """処理終了時のUI復旧"""
        self.rename_processing = False
        self.rename_button.config(state='normal')
        self.progress.config(value=0)

    def _show_error(self, error_message: str):
        """エラー表示"""
        self._log(f"❌ エラー: {error_message}")
        messagebox.showerror("エラー", error_message)

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
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            self._log(f"ログを保存しました: {file_path}")

    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

if __name__ == "__main__":
    app = TaxDocumentRenamerV5Fixed()
    app.run()