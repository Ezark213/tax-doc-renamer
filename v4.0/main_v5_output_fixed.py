#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 出力先選択機能付き
出力先フォルダ選択機能を追加したバージョン
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Optional

class TaxDocumentRenamerV5Output:
    """税務書類リネームシステム v5.0 出力先選択機能付き"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.0 出力先選択対応版")
        self.root.geometry("1100x800")
        
        # システム変数
        self.files_list = []
        self.output_folder = ""
        self.processing = False
        self.processing_results = []
        
        # 自治体セット設定
        self.municipality_sets = {
            1: {"name": "東京都", "pref_code": 1001, "muni_code": None},
            2: {"name": "愛知県蒲郡市", "pref_code": 1011, "muni_code": 2001},
            3: {"name": "福岡県福岡市", "pref_code": 1021, "muni_code": 2011}
        }
        
        # UI構築
        self._create_ui()
        self._log("税務書類リネームシステム v5.0 出力先選択対応版を起動しました")

    def _create_ui(self):
        """メインUI作成"""
        # メインコンテナ
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="税務書類リネームシステム v5.0 出力先選択対応版",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # タブコントロール
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # メインタブ
        self._create_main_tab()
        
        # 結果タブ
        self._create_results_tab()
        
        # ログタブ
        self._create_log_tab()

    def _create_main_tab(self):
        """メインタブ作成"""
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="🏠 メイン")
        
        # 左右分割
        paned = ttk.PanedWindow(self.main_frame, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 左側フレーム（ファイル選択）
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        # 右側フレーム（設定・処理）
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # === 左側: ファイル選択 ===
        # ファイル選択エリア
        file_select_frame = ttk.LabelFrame(left_frame, text="📁 ファイル選択")
        file_select_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # ドラッグ&ドロップエリア
        drop_label = ttk.Label(
            file_select_frame,
            text="ここにPDFファイルをドラッグ&ドロップ\\nまたはボタンでファイルを選択",
            background='lightgray',
            anchor='center',
            font=('Arial', 12)
        )
        drop_label.pack(fill='both', expand=True, padx=10, pady=10, ipady=30)
        drop_label.bind('<Button-1>', self._select_files)
        file_select_frame.bind('<Button-1>', self._select_files)
        
        # ファイル操作ボタン
        file_buttons = ttk.Frame(left_frame)
        file_buttons.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(file_buttons, text="📁 ファイル追加", command=self._select_files).pack(side='left', padx=(0, 5))
        ttk.Button(file_buttons, text="📂 フォルダから追加", command=self._select_folder).pack(side='left', padx=5)
        ttk.Button(file_buttons, text="🗑️ クリア", command=self._clear_files).pack(side='left', padx=5)
        
        # === 出力先フォルダ選択エリア ===
        output_select_frame = ttk.LabelFrame(left_frame, text="📤 出力先フォルダ")
        output_select_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        # 出力先表示
        self.output_var = tk.StringVar(value="未選択（元のファイルと同じフォルダ）")
        output_display = ttk.Label(
            output_select_frame,
            textvariable=self.output_var,
            background='white',
            relief='sunken',
            anchor='w'
        )
        output_display.pack(fill='x', padx=5, pady=(5, 5))
        
        # 出力先選択ボタン
        output_buttons = ttk.Frame(output_select_frame)
        output_buttons.pack(fill='x', padx=5, pady=(0, 10))
        
        ttk.Button(output_buttons, text="📁 出力先選択", command=self._select_output_folder).pack(side='left', padx=(0, 5))
        ttk.Button(output_buttons, text="🔄 リセット", command=self._reset_output_folder).pack(side='left', padx=5)
        
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
        
        # 自治体セット表示
        set_frame = ttk.LabelFrame(right_frame, text="自治体セット")
        set_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.set_info_text = tk.Text(set_frame, height=8, font=('Arial', 8), state='disabled')
        self.set_info_text.pack(fill='x', padx=5, pady=5)
        self._update_set_display()
        
        # 処理オプション
        options_frame = ttk.LabelFrame(right_frame, text="処理オプション")
        options_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.copy_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="元ファイルを残す（コピーモード）", variable=self.copy_mode_var).pack(anchor='w', padx=5, pady=2)
        
        self.set_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="セットベース連番モード", variable=self.set_mode_var).pack(anchor='w', padx=5, pady=2)
        
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="デバッグモード", variable=self.debug_mode_var).pack(anchor='w', padx=5, pady=2)
        
        # 処理実行
        process_frame = ttk.Frame(right_frame)
        process_frame.pack(fill='x', padx=5, pady=10)
        
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

    def _create_results_tab(self):
        """結果タブ作成"""
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="📊 処理結果")
        
        # ボタンエリア
        results_buttons = ttk.Frame(self.results_frame)
        results_buttons.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(results_buttons, text="💾 CSV保存", command=self._save_results).pack(side='left', padx=(0, 5))
        ttk.Button(results_buttons, text="🗑️ クリア", command=self._clear_results).pack(side='left', padx=5)
        
        # 結果表示
        results_container = ttk.Frame(self.results_frame)
        results_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # TreeView
        columns = ('original', 'new', 'set', 'status')
        self.results_tree = ttk.Treeview(results_container, columns=columns, show='headings')
        
        # ヘッダー設定
        self.results_tree.heading('original', text='元ファイル名')
        self.results_tree.heading('new', text='新ファイル名')
        self.results_tree.heading('set', text='セット')
        self.results_tree.heading('status', text='ステータス')
        
        # スクロールバー
        results_scrollbar = ttk.Scrollbar(results_container, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        results_scrollbar.pack(side='right', fill='y')

    def _create_log_tab(self):
        """ログタブ作成"""
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="📝 ログ")
        
        # ボタンエリア
        log_buttons = ttk.Frame(self.log_frame)
        log_buttons.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(log_buttons, text="🗑️ クリア", command=self._clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(log_buttons, text="💾 ログ保存", command=self._save_log).pack(side='left', padx=5)
        
        # ログ表示
        log_container = ttk.Frame(self.log_frame)
        log_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.log_text = tk.Text(log_container, font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')

    def _select_output_folder(self):
        """出力先フォルダ選択"""
        folder = filedialog.askdirectory(
            title="出力先フォルダを選択してください"
        )
        if folder:
            self.output_folder = folder
            self.output_var.set(folder)
            self._log(f"出力先フォルダを設定しました: {folder}")

    def _reset_output_folder(self):
        """出力先フォルダリセット"""
        self.output_folder = ""
        self.output_var.set("未選択（元のファイルと同じフォルダ）")
        self._log("出力先フォルダをリセットしました")

    def _select_files(self, event=None):
        """ファイル選択"""
        files = filedialog.askopenfilenames(
            title="PDFファイルを選択",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        for file in files:
            if file not in self.files_list:
                self.files_list.append(file)
                self.files_listbox.insert(tk.END, os.path.basename(file))
        
        if files:
            self._log(f"{len(files)}個のファイルを追加しました")

    def _select_folder(self):
        """フォルダからファイル選択"""
        folder = filedialog.askdirectory(title="PDFファイルを含むフォルダを選択")
        if not folder:
            return
        
        pdf_files = []
        for file in os.listdir(folder):
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(folder, file)
                if full_path not in self.files_list:
                    self.files_list.append(full_path)
                    self.files_listbox.insert(tk.END, file)
                    pdf_files.append(file)
        
        if pdf_files:
            self._log(f"フォルダから{len(pdf_files)}個のPDFファイルを追加しました")
        else:
            messagebox.showinfo("情報", "選択したフォルダにPDFファイルが見つかりませんでした")

    def _clear_files(self):
        """ファイルリストクリア"""
        self.files_list.clear()
        self.files_listbox.delete(0, tk.END)
        self._log("ファイルリストをクリアしました")

    def _update_set_display(self):
        """自治体セット表示更新"""
        self.set_info_text.config(state='normal')
        self.set_info_text.delete('1.0', tk.END)
        
        content = "現在の自治体セット設定:\\n\\n"
        for set_num, info in self.municipality_sets.items():
            content += f"セット{set_num}: {info['name']}\\n"
            content += f"  都道府県コード: {info['pref_code']}\\n"
            if info['muni_code']:
                content += f"  市町村コード: {info['muni_code']}\\n"
            content += "\\n"
        
        self.set_info_text.insert('1.0', content)
        self.set_info_text.config(state='disabled')

    def _log(self, message):
        """ログ出力"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\\n"
        
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            print(log_entry)  # コンソール出力も

    def _start_processing(self):
        """処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.processing:
            return
        
        self.processing = True
        self.process_button.config(state='disabled')
        self.status_var.set("処理中...")
        self.progress.config(mode='indeterminate')
        self.progress.start()
        
        # バックグラウンドで処理実行
        thread = threading.Thread(target=self._process_files)
        thread.daemon = True
        thread.start()

    def _process_files(self):
        """ファイル処理（バックグラウンド）"""
        try:
            year_month = self.year_month_var.get()
            copy_mode = self.copy_mode_var.get()
            
            self._log(f"処理開始: {len(self.files_list)}個のファイル")
            self._log(f"年月: {year_month}")
            self._log(f"出力先: {self.output_folder if self.output_folder else '元のファイルと同じフォルダ'}")
            self._log(f"コピーモード: {'有効' if copy_mode else '無効'}")
            
            processed_count = 0
            
            for file_path in self.files_list:
                try:
                    # ファイル名取得
                    original_name = os.path.basename(file_path)
                    
                    # 新しいファイル名生成（デモ用）
                    new_name = self._generate_new_filename(original_name, year_month)
                    
                    # 出力先決定
                    if self.output_folder:
                        output_path = os.path.join(self.output_folder, new_name)
                    else:
                        output_dir = os.path.dirname(file_path)
                        output_path = os.path.join(output_dir, new_name)
                    
                    # ファイル操作
                    if copy_mode:
                        shutil.copy2(file_path, output_path)
                        operation = "コピー"
                    else:
                        shutil.move(file_path, output_path)
                        operation = "移動"
                    
                    # 結果記録
                    result = {
                        'original': original_name,
                        'new': new_name,
                        'set': '自動判定',
                        'status': f'{operation}完了'
                    }
                    self.processing_results.append(result)
                    
                    # 結果表示に追加
                    self.root.after(0, lambda r=result: self._add_result_to_tree(r))
                    
                    processed_count += 1
                    self._log(f"処理完了: {original_name} → {new_name} ({operation})")
                    
                except Exception as e:
                    error_result = {
                        'original': os.path.basename(file_path),
                        'new': 'エラー',
                        'set': '-',
                        'status': f'エラー: {str(e)}'
                    }
                    self.processing_results.append(error_result)
                    self.root.after(0, lambda r=error_result: self._add_result_to_tree(r))
                    self._log(f"処理エラー: {file_path} - {str(e)}")
            
            self._log(f"全処理完了: {processed_count}個のファイルを処理しました")
            
        except Exception as e:
            self._log(f"処理中にエラーが発生しました: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("エラー", f"処理中にエラーが発生しました:\\n{str(e)}"))
        
        finally:
            # UI更新
            self.root.after(0, self._processing_finished)

    def _generate_new_filename(self, original_name, year_month):
        """新しいファイル名生成（デモ用）"""
        # デモ用の簡単な判定ロジック
        name_lower = original_name.lower()
        
        if '法人税' in original_name:
            return f"0001_法人税及び地方法人税申告書_{year_month}.pdf"
        elif '消費税' in original_name:
            return f"3001_消費税及び地方消費税申告書_{year_month}.pdf"
        elif '受信通知' in original_name:
            return f"0003_受信通知_{year_month}.pdf"
        elif '納付' in original_name:
            return f"0004_納付情報_{year_month}.pdf"
        else:
            return f"9999_未分類_{year_month}.pdf"

    def _add_result_to_tree(self, result):
        """結果をTreeViewに追加"""
        self.results_tree.insert('', 'end', values=(
            result['original'],
            result['new'],
            result['set'],
            result['status']
        ))

    def _processing_finished(self):
        """処理終了"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.stop()
        self.progress.config(mode='determinate', value=0)
        self.status_var.set("処理完了")

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
            title="結果を保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['元ファイル名', '新ファイル名', 'セット', 'ステータス'])
                    for result in self.processing_results:
                        writer.writerow([result['original'], result['new'], result['set'], result['status']])
                
                messagebox.showinfo("完了", f"結果を保存しました: {file_path}")
                self._log(f"結果を保存しました: {file_path}")
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
            filetypes=[("Text files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("完了", f"ログを保存しました: {file_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"ログ保存に失敗: {str(e)}")

    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    try:
        app = TaxDocumentRenamerV5Output()
        app.run()
    except Exception as e:
        print(f"アプリケーション起動エラー: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\\n{str(e)}")

if __name__ == "__main__":
    main()