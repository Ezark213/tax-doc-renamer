#!/usr/bin/env python3
"""
税務書類リネームシステム v4.3 Lite版
分割・リネーム修正の軽量テスト版
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import os
import re
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import threading

# 必要なライブラリのインポート（エラーハンドリング付き）
try:
    import PyPDF2
    import fitz  # PyMuPDF
    from PIL import Image
    import pytesseract
except ImportError as e:
    print(f"必要なライブラリがインストールされていません: {e}")
    sys.exit(1)

class DebugLogger:
    """デバッグログ管理クラス"""
    
    def __init__(self, text_widget=None):
        self.text_widget = text_widget
        
    def log(self, level, message):
        """ログ出力"""
        try:
            # GUI表示
            if self.text_widget:
                timestamp = datetime.now().strftime('%H:%M:%S')
                log_line = f"[{timestamp}] {level}: {message}\n"
                self.text_widget.insert(tk.END, log_line)
                self.text_widget.see(tk.END)
                self.text_widget.update()
        except Exception as e:
            print(f"ログ出力エラー: {e}")

class SplitJudgmentEngine:
    """分割判定エンジン（v4.3 厳格版）"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        
        # 分割対象キーワード（厳格な定義）
        self.SPLIT_TARGET_KEYWORDS = {
            'receipt_notice': [
                '申告受付完了通知', '受信通知', 
                '申告書等送信票', '送信結果'
            ],
            'payment_info': [
                '納付情報発行結果', '納付区分番号通知',
                '納付税額通知書', '納付書'
            ]
        }
        
        # 分割不要書類
        self.NO_SPLIT_PATTERNS = [
            '消費税申告書', '法人税申告書',
            '決算書', '固定資産台帳',
            '少額減価償却', '一括償却',
            '税区分集計表'
        ]
        
    def should_split_document(self, ocr_text: str, filename: str) -> bool:
        """分割判定（厳格版）"""
        self.debug_logger.log('INFO', "=== 分割判定開始（v4.3厳格版） ===")
        
        # Step 1: 分割不要書類の判定
        if self._is_no_split_document(ocr_text, filename):
            self.debug_logger.log('INFO', "分割不要書類として判定")
            return False
            
        # Step 2: 分割対象キーワードの検出
        split_indicators = self._count_split_indicators(ocr_text)
        
        # Step 3: 複数指標が検出された場合のみ分割
        if split_indicators >= 2:
            self.debug_logger.log('INFO', f"分割対象として判定：指標数={split_indicators}")
            return True
        else:
            self.debug_logger.log('INFO', f"単一書類として判定：指標数={split_indicators}")
            return False
            
    def _is_no_split_document(self, text: str, filename: str) -> bool:
        """分割不要書類の判定"""
        combined_text = text + " " + filename
        
        for pattern in self.NO_SPLIT_PATTERNS:
            if pattern in combined_text:
                self.debug_logger.log('DEBUG', f"分割不要パターン検出: {pattern}")
                return True
        return False
        
    def _count_split_indicators(self, text: str) -> int:
        """分割対象指標のカウント"""
        indicators = 0
        
        for category, keywords in self.SPLIT_TARGET_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    indicators += 1
                    self.debug_logger.log('DEBUG', f"分割対象キーワード検出: {keyword}")
                    break  # カテゴリごとに1回のみカウント
                    
        return indicators

class SimpleProcessor:
    """簡易処理クラス（v4.3 Lite）"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.split_engine = SplitJudgmentEngine(debug_logger)
        
    def process_document(self, file_path: str, user_yymm: str = "") -> List[Dict]:
        """文書処理（簡易版）"""
        results = []
        
        try:
            self.debug_logger.log('INFO', f"=== 処理開始: {os.path.basename(file_path)} ===")
            
            # PDFでない場合はそのまま処理
            if not file_path.lower().endswith('.pdf'):
                result = {
                    'original_name': os.path.basename(file_path),
                    'new_name': f"processed_{user_yymm or '0000'}_{os.path.basename(file_path)}",
                    'document_type': 'non-pdf',
                    'split_info': 'PDF以外のファイル',
                    'status': 'success'
                }
                results.append(result)
                return results
            
            # OCR実行
            ocr_text = self._extract_text_from_pdf(file_path)
            filename = os.path.basename(file_path)
            
            # 分割判定
            should_split = self.split_engine.should_split_document(ocr_text, filename)
            
            if should_split:
                # 分割処理（簡易版）
                self.debug_logger.log('INFO', "分割処理実行")
                result = {
                    'original_name': filename,
                    'new_name': f"split_result_{user_yymm or '0000'}.pdf",
                    'document_type': '分割対象書類',
                    'split_info': '分割実行（簡易版）',
                    'status': 'success'
                }
            else:
                # 単一処理
                self.debug_logger.log('INFO', "単一書類として処理")
                doc_type = self._classify_document(ocr_text)
                result = {
                    'original_name': filename,
                    'new_name': f"{doc_type}_{user_yymm or '0000'}.pdf",
                    'document_type': doc_type,
                    'split_info': '単一書類処理',
                    'status': 'success'
                }
            
            results.append(result)
            self.debug_logger.log('INFO', "処理完了")
            
            return results
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"処理エラー: {e}")
            return [{
                'original_name': os.path.basename(file_path),
                'new_name': '',
                'document_type': 'error',
                'split_info': f'エラー: {e}',
                'status': 'error'
            }]
            
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDFテキスト抽出（簡易版）"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(min(3, len(doc))):  # 最初の3ページのみ
                page = doc[page_num]
                page_text = page.get_text()
                text += page_text + "\n"
                
            doc.close()
            return text
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"PDF読み込みエラー: {e}")
            return ""
            
    def _classify_document(self, text: str) -> str:
        """文書分類（簡易版）"""
        # 基本的な分類
        if '消費税' in text:
            return '3001_消費税申告書'
        elif '法人税' in text:
            return '0001_法人税申告書'
        elif '決算書' in text:
            return '5001_決算書'
        elif '固定資産' in text:
            return '6001_固定資産台帳'
        else:
            return '9999_未分類'

class TaxDocumentRenamerApp:
    """メインアプリケーションクラス（v4.3 Lite）"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("税務書類リネームシステム v4.3 Lite（分割修正テスト版）")
        self.root.geometry("800x600")
        
        # 処理エンジン
        self.processor = None
        
        # UI構築
        self.setup_ui()
        
        # 処理エンジン初期化
        self.debug_logger = DebugLogger(self.debug_text)
        self.processor = SimpleProcessor(self.debug_logger)
        
        self.debug_logger.log('INFO', "税務書類リネームシステム v4.3 Lite 起動")
        
    def setup_ui(self):
        """UI構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # YYMM入力
        yymm_frame = ttk.LabelFrame(main_frame, text="年月設定（YYMM形式）")
        yymm_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(yymm_frame, text="年月(YYMM):").pack(side=tk.LEFT, padx=5)
        self.yymm_entry = ttk.Entry(yymm_frame, width=10)
        self.yymm_entry.pack(side=tk.LEFT, padx=5)
        
        # ファイル選択
        file_frame = ttk.LabelFrame(main_frame, text="ファイル選択")
        file_frame.pack(fill=tk.X, pady=5)
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="ファイル選択", command=self.select_file).pack(side=tk.RIGHT, padx=5)
        
        # 処理実行
        process_frame = ttk.Frame(main_frame)
        process_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(process_frame, text="処理実行", command=self.process_file, width=20).pack()
        
        # 結果表示
        results_frame = ttk.LabelFrame(main_frame, text="処理結果")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 結果Treeview
        columns = ('original', 'new_name', 'type', 'split_info', 'status')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=8)
        
        # ヘッダー設定
        self.results_tree.heading('original', text='元ファイル名')
        self.results_tree.heading('new_name', text='新ファイル名')
        self.results_tree.heading('type', text='書類種別')
        self.results_tree.heading('split_info', text='分割情報')
        self.results_tree.heading('status', text='処理状況')
        
        # 列幅設定
        self.results_tree.column('original', width=150)
        self.results_tree.column('new_name', width=150)
        self.results_tree.column('type', width=100)
        self.results_tree.column('split_info', width=100)
        self.results_tree.column('status', width=80)
        
        self.results_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ログ表示
        log_frame = ttk.LabelFrame(main_frame, text="処理ログ")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.debug_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.debug_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def select_file(self):
        """ファイル選択"""
        file_path = filedialog.askopenfilename(
            title="処理するファイルを選択",
            filetypes=[
                ("PDFファイル", "*.pdf"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if file_path:
            self.file_path_var.set(file_path)
            
    def process_file(self):
        """ファイル処理実行"""
        file_path = self.file_path_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("エラー", "有効なファイルを選択してください")
            return
            
        user_yymm = self.yymm_entry.get().strip()
        
        # 処理実行（スレッド化）
        def process_thread():
            try:
                self.debug_logger.log('INFO', "処理開始...")
                
                # 処理実行
                results = self.processor.process_document(file_path, user_yymm)
                
                # 結果表示
                self.display_results(results)
                
                self.debug_logger.log('INFO', f"処理完了: {len(results)}件")
                
            except Exception as e:
                self.debug_logger.log('ERROR', f"処理エラー: {e}")
                messagebox.showerror("エラー", f"処理中にエラーが発生しました: {e}")
                
        threading.Thread(target=process_thread, daemon=True).start()
        
    def display_results(self, results):
        """結果表示"""
        # 既存結果クリア
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        # 結果追加
        for result in results:
            self.results_tree.insert('', tk.END, values=(
                result.get('original_name', ''),
                result.get('new_name', ''),
                result.get('document_type', ''),
                result.get('split_info', ''),
                result.get('status', '')
            ))

def main():
    """メイン関数"""
    root = tk.Tk()
    app = TaxDocumentRenamerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()