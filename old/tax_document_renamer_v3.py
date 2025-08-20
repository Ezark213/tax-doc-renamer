#!/usr/bin/env python3
"""
税務書類リネームシステム v3.1
ゼロベース構築版 - 全要件対応
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.dnd as dnd
import sys
import os
import io
import re
import shutil
import logging
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import threading

# PyInstallerでの実行時のパス取得
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# 必要なライブラリのインポート（エラーハンドリング付き）
try:
    import PyPDF2
    import fitz  # PyMuPDF
    from PIL import Image, ImageTk
    import pytesseract
except ImportError as e:
    print(f"必要なライブラリがインストールされていません: {e}")
    sys.exit(1)

class DebugLogger:
    """デバッグログ管理クラス"""
    
    def __init__(self, text_widget=None):
        self.text_widget = text_widget
        self.setup_logging()
        
    def setup_logging(self):
        """ログ設定"""
        log_dir = os.path.join(os.path.expanduser("~"), "TaxDocumentRenamer")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"tax_document_renamer_{datetime.now().strftime('%Y%m%d')}.log")
        
        # ロガー設定
        self.logger = logging.getLogger('TaxDocRenamer')
        self.logger.setLevel(logging.DEBUG)
        
        # ファイルハンドラー
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # フォーマット
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
    def log(self, level, message):
        """ログ出力"""
        if level == 'DEBUG':
            self.logger.debug(message)
        elif level == 'INFO':
            self.logger.info(message)
        elif level == 'WARNING':
            self.logger.warning(message)
        elif level == 'ERROR':
            self.logger.error(message)
            
        # GUI表示
        if self.text_widget:
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_line = f"[{timestamp}] {level}: {message}\n"
            self.text_widget.insert(tk.END, log_line)
            self.text_widget.see(tk.END)

class FileNamingRules:
    """ファイル命名規則管理クラス"""
    
    def __init__(self):
        self.setup_rules()
        
    def setup_rules(self):
        """命名規則の設定"""
        # PDF書類の命名規則
        self.pdf_patterns = {
            # 法人税関連
            '内国法人の確定申告': '0001_法人税及び地方法人税申告書_{yymm}.pdf',
            '法人税申告書': '0001_法人税及び地方法人税申告書_{yymm}.pdf',
            
            # 消費税関連  
            '消費税申告書': '3001_消費税申告書_{yymm}.pdf',
            '消費税及び地方消費税申告': '3001_消費税申告書_{yymm}.pdf',
            
            # 添付資料
            '添付資料_法人税': '0002_添付資料_法人税_{yymm}.pdf',
            '添付資料_消費税': '3002_添付資料_消費税_{yymm}.pdf',
            
            # 決算書類
            '決算書': '5001_決算書_{yymm}.pdf',
            '総勘定元帳': '5002_総勘定元帳_{yymm}.pdf',
            '補助元帳': '5003_補助元帳_{yymm}.pdf',
            '仕訳帳': '5005_仕訳帳_{yymm}.pdf',  # PDFの仕訳帳
            
            # 税区分集計表（重要：分離）
            '勘定科目別税区分集計表': '7001_勘定科目別税区分集計表_{yymm}.pdf',
            '税区分集計表': '7002_税区分集計表_{yymm}.pdf',
            
            # 固定資産
            '固定資産台帳': '6001_固定資産台帳_{yymm}.pdf',
            '一括償却資産明細表': '6002_一括償却資産明細表_{yymm}.pdf',
            '少額減価償却資産明細表': '6003_少額減価償却資産明細表_{yymm}.pdf',
            
            # 納付関連
            '納税一覧': '0000_納付税額一覧表_{yymm}.pdf',
            '納付情報': '2004_納付情報_{yymm}.pdf',
            
            # 都道府県・市町村
            '都道府県民税': '1001_都道府県申告_{yymm}.pdf',
            '法人市民税': '2001_市町村申告_{yymm}.pdf',
        }
        
        # CSV書類の命名規則
        self.csv_patterns = {
            '仕訳帳': '5006_仕訳帳_{yymm}.csv',  # CSVの仕訳帳（PDFと区別）
            '総勘定元帳': '5007_総勘定元帳_{yymm}.csv',
            '補助元帳': '5008_補助元帳_{yymm}.csv',
        }
        
        # キーワードパターン（優先度順）
        self.detection_keywords = {
            # 税区分集計表の分離（最優先）
            '勘定科目別税区分集計表': ['勘定科目別税区分集計表'],
            '税区分集計表': ['税区分集計表'],
            
            # 法人税
            '内国法人の確定申告': ['内国法人の確定申告', '法人税申告書'],
            
            # 消費税
            '消費税申告書': ['消費税申告書', '消費税及び地方消費税申告'],
            
            # 添付資料
            '添付資料_法人税': ['添付資料', '法人税'],
            '添付資料_消費税': ['添付資料', '消費税'],
            
            # 決算書類
            '決算書': ['決算書'],
            '総勘定元帳': ['総勘定元帳'],
            '補助元帳': ['補助元帳'],
            '仕訳帳': ['仕訳帳'],
            
            # 固定資産
            '固定資産台帳': ['固定資産台帳'],
            '一括償却資産明細表': ['一括償却資産明細表'],
            '少額減価償却資産明細表': ['少額減価償却資産明細表'],
            
            # 納付関連
            '納税一覧': ['納税一覧', '納付税額一覧表'],
            '納付情報': ['納付情報'],
            
            # 地方税
            '都道府県民税': ['都道府県民税', '法人都道府県民税', '事業税'],
            '法人市民税': ['法人市民税', '市民税'],
        }

class OCRProcessor:
    """OCR処理クラス"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.setup_tesseract()
        
    def setup_tesseract(self):
        """Tesseract設定"""
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
        ]
        
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                self.debug_logger.log('INFO', f"Tesseract設定: {path}")
                return True
                
        self.debug_logger.log('WARNING', "Tesseractが見つかりません")
        return False
        
    def extract_text_from_pdf(self, pdf_path):
        """PDFからテキスト抽出"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            # 最初の数ページのみ処理（効率化）
            max_pages = min(3, len(doc))
            
            for page_num in range(max_pages):
                page = doc[page_num]
                
                # テキスト抽出
                page_text = page.get_text()
                text += page_text + "\n"
                
                # OCR用画像作成（テキストが少ない場合）
                if len(page_text.strip()) < 50:
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    try:
                        ocr_text = pytesseract.image_to_string(img, lang='jpn')
                        text += ocr_text + "\n"
                        self.debug_logger.log('DEBUG', f"OCR抽出テキスト: {ocr_text[:100]}...")
                    except Exception as e:
                        self.debug_logger.log('WARNING', f"OCR処理エラー: {e}")
                        
            doc.close()
            return text
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"PDF読み込みエラー: {e}")
            return ""

class YYMMProcessor:
    """YYMM判定処理クラス"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        
    def determine_yymm(self, user_input: str, filename: str, ocr_text: str) -> str:
        """YYMM決定（優先順位適用）"""
        self.debug_logger.log('INFO', "=== YYMM判定開始 ===")
        
        # 1. ユーザー入力最優先
        if user_input and user_input.strip():
            yymm = user_input.strip()
            self.debug_logger.log('INFO', f"ユーザー入力YYMM使用: {yymm}")
            return yymm
            
        # 2. ファイル名から推定
        filename_yymm = self.extract_yymm_from_filename(filename)
        if filename_yymm:
            self.debug_logger.log('INFO', f"ファイル名からYYMM抽出: {filename_yymm}")
            return filename_yymm
            
        # 3. OCR結果から推定（補完的）
        ocr_yymm = self.extract_yymm_from_text(ocr_text)
        if ocr_yymm:
            self.debug_logger.log('INFO', f"OCRからYYMM抽出（補完）: {ocr_yymm}")
            return ocr_yymm
            
        # 4. デフォルト
        self.debug_logger.log('WARNING', "YYMM判定不可、デフォルト使用: 0000")
        return "0000"
        
    def extract_yymm_from_filename(self, filename: str) -> Optional[str]:
        """ファイル名からYYMM抽出"""
        patterns = [
            r'(\d{4})(?:\D|$)',  # 4桁数字
            r'_(\d{4})[._]',     # アンダースコア区切り
            r'(\d{2})(\d{2})',   # 年月分離
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                if len(match.groups()) == 1:
                    return match.group(1)
                else:
                    return match.group(1) + match.group(2)
        return None
        
    def extract_yymm_from_text(self, text: str) -> Optional[str]:
        """テキストからYYMM抽出"""
        # 一般的な年月パターン
        patterns = [
            r'令和(\d+)年(\d+)月',
            r'(\d{4})年(\d+)月',
            r'(\d{2})(\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if '令和' in pattern:
                    year = int(match.group(1)) + 18  # 令和→西暦変換簡易版
                    month = int(match.group(2))
                    return f"{year:02d}{month:02d}"
                else:
                    return match.group(1) + match.group(2).zfill(2)
        return None

class DocumentProcessor:
    """文書処理メインクラス"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.naming_rules = FileNamingRules()
        self.ocr_processor = OCRProcessor(debug_logger)
        self.yymm_processor = YYMMProcessor(debug_logger)
        
    def process_file(self, file_path: str, user_yymm: str = "") -> Dict:
        """ファイル処理"""
        result = {
            'original_file': file_path,
            'success': False,
            'new_name': '',
            'error': '',
            'document_type': '',
            'yymm': '',
            'processing_details': []
        }
        
        try:
            self.debug_logger.log('INFO', f"=== ファイル処理開始: {os.path.basename(file_path)} ===")
            
            # ファイル拡張子判定
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                return self.process_pdf_file(file_path, user_yymm, result)
            elif file_ext == '.csv':
                return self.process_csv_file(file_path, user_yymm, result)
            else:
                result['error'] = f"未対応のファイル形式: {file_ext}"
                self.debug_logger.log('ERROR', result['error'])
                return result
                
        except Exception as e:
            result['error'] = f"処理エラー: {str(e)}"
            self.debug_logger.log('ERROR', result['error'])
            return result
            
    def process_pdf_file(self, file_path: str, user_yymm: str, result: Dict) -> Dict:
        """PDF処理"""
        # OCRテキスト抽出
        ocr_text = self.ocr_processor.extract_text_from_pdf(file_path)
        result['processing_details'].append(f"テキスト抽出: {len(ocr_text)}文字")
        
        # 文書種別判定
        doc_type = self.determine_document_type(ocr_text, os.path.basename(file_path))
        result['document_type'] = doc_type
        result['processing_details'].append(f"文書種別: {doc_type}")
        
        # YYMM判定
        yymm = self.yymm_processor.determine_yymm(user_yymm, os.path.basename(file_path), ocr_text)
        result['yymm'] = yymm
        
        # 新ファイル名生成
        if doc_type in self.naming_rules.pdf_patterns:
            new_name = self.naming_rules.pdf_patterns[doc_type].format(yymm=yymm)
            result['new_name'] = new_name
            result['success'] = True
        else:
            result['error'] = f"未対応の文書種別: {doc_type}"
            
        return result
        
    def process_csv_file(self, file_path: str, user_yymm: str, result: Dict) -> Dict:
        """CSV処理"""
        try:
            # CSVファイル読み込み
            df = pd.read_csv(file_path, encoding='utf-8', nrows=10)  # 先頭10行のみ
            csv_text = ' '.join(df.columns.tolist())  # カラム名から判定
            
            result['processing_details'].append(f"CSV読み込み: {len(df.columns)}カラム")
            
            # 文書種別判定
            doc_type = self.determine_document_type(csv_text, os.path.basename(file_path))
            result['document_type'] = doc_type
            
            # YYMM判定
            yymm = self.yymm_processor.determine_yymm(user_yymm, os.path.basename(file_path), csv_text)
            result['yymm'] = yymm
            
            # CSV専用命名規則適用
            if doc_type in self.naming_rules.csv_patterns:
                new_name = self.naming_rules.csv_patterns[doc_type].format(yymm=yymm)
                result['new_name'] = new_name
                result['success'] = True
            else:
                result['error'] = f"CSV未対応の文書種別: {doc_type}"
                
        except Exception as e:
            result['error'] = f"CSV読み込みエラー: {str(e)}"
            
        return result
        
    def determine_document_type(self, text: str, filename: str) -> str:
        """文書種別判定"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # 税区分集計表の分離（最優先）
        if '勘定科目別税区分集計表' in text or '勘定科目別税区分集計表' in filename:
            return '勘定科目別税区分集計表'
        elif '税区分集計表' in text or '税区分集計表' in filename:
            return '税区分集計表'
            
        # その他のキーワード判定
        for doc_type, keywords in self.naming_rules.detection_keywords.items():
            for keyword in keywords:
                if keyword in text or keyword in filename:
                    self.debug_logger.log('DEBUG', f"キーワード '{keyword}' で '{doc_type}' 判定")
                    return doc_type
                    
        return '不明'

class DragDropFrame(tk.Frame):
    """ドラッグ&ドロップ対応フレーム"""
    
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.setup_ui()
        self.setup_drag_drop()
        
    def setup_ui(self):
        """UI設定"""
        self.config(bg='lightgray', relief='dashed', bd=2)
        
        label = tk.Label(self, text="ファイルをここにドラッグ&ドロップ\nまたは下のボタンでファイル選択", 
                        bg='lightgray', font=('Arial', 12))
        label.pack(expand=True)
        
    def setup_drag_drop(self):
        """ドラッグ&ドロップ設定"""
        self.drop_target_register(dnd.FILE)
        self.dnd_bind('<<Drop>>', self.on_drop)
        
    def on_drop(self, event):
        """ドロップ時の処理"""
        files = event.data.split()
        self.callback(files)

class TaxDocumentRenamerGUI:
    """メインGUIクラス"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v3.1")
        self.root.geometry("900x700")
        
        self.debug_logger = None
        self.processor = None
        self.files_to_process = []
        
        self.setup_ui()
        self.setup_processors()
        
    def setup_ui(self):
        """UI構築"""
        # タブ作成
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タブ1: ファイル選択
        self.file_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.file_tab, text="ファイル選択")
        self.setup_file_tab()
        
        # タブ2: 処理設定
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="処理設定")
        self.setup_settings_tab()
        
        # タブ3: デバッグログ
        self.debug_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.debug_tab, text="デバッグログ")
        self.setup_debug_tab()
        
    def setup_file_tab(self):
        """ファイル選択タブ"""
        # YYMM入力
        yymm_frame = ttk.Frame(self.file_tab)
        yymm_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(yymm_frame, text="年月(YYMM):").pack(side='left')
        self.yymm_var = tk.StringVar()
        yymm_entry = ttk.Entry(yymm_frame, textvariable=self.yymm_var, width=10)
        yymm_entry.pack(side='left', padx=(5, 0))
        
        # ドラッグ&ドロップエリア
        drop_frame = DragDropFrame(self.file_tab, self.on_files_dropped)
        drop_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ファイル選択ボタン
        btn_frame = ttk.Frame(self.file_tab)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="ファイル選択", command=self.select_files).pack(side='left')
        ttk.Button(btn_frame, text="処理実行", command=self.process_files).pack(side='left', padx=(10, 0))
        ttk.Button(btn_frame, text="クリア", command=self.clear_files).pack(side='left', padx=(10, 0))
        
        # ファイルリスト
        list_frame = ttk.Frame(self.file_tab)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.file_listbox = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
        
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)
        
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
    def setup_settings_tab(self):
        """処理設定タブ"""
        # 出力ディレクトリ設定
        dir_frame = ttk.LabelFrame(self.settings_tab, text="出力設定")
        dir_frame.pack(fill='x', padx=10, pady=10)
        
        self.output_dir_var = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        ttk.Label(dir_frame, text="出力ディレクトリ:").pack(anchor='w')
        dir_entry_frame = ttk.Frame(dir_frame)
        dir_entry_frame.pack(fill='x', pady=5)
        
        ttk.Entry(dir_entry_frame, textvariable=self.output_dir_var).pack(side='left', fill='x', expand=True)
        ttk.Button(dir_entry_frame, text="参照", command=self.select_output_dir).pack(side='right', padx=(5, 0))
        
        # 処理オプション
        options_frame = ttk.LabelFrame(self.settings_tab, text="処理オプション")
        options_frame.pack(fill='x', padx=10, pady=10)
        
        self.overwrite_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="同名ファイルを上書き", variable=self.overwrite_var).pack(anchor='w')
        
        self.backup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="元ファイルをバックアップ", variable=self.backup_var).pack(anchor='w')
        
    def setup_debug_tab(self):
        """デバッグログタブ"""
        # ログ表示エリア
        log_frame = ttk.Frame(self.debug_tab)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.debug_text = scrolledtext.ScrolledText(log_frame, height=20)
        self.debug_text.pack(fill='both', expand=True)
        
        # ログ制御ボタン
        btn_frame = ttk.Frame(self.debug_tab)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="ログクリア", command=self.clear_debug_log).pack(side='left')
        ttk.Button(btn_frame, text="ログ保存", command=self.save_debug_log).pack(side='left', padx=(10, 0))
        
    def setup_processors(self):
        """プロセッサー初期化"""
        self.debug_logger = DebugLogger(self.debug_text)
        self.processor = DocumentProcessor(self.debug_logger)
        
        self.debug_logger.log('INFO', "税務書類リネームシステム v3.1 起動")
        
    def on_files_dropped(self, files):
        """ファイルドロップ時の処理"""
        for file_path in files:
            if file_path not in self.files_to_process:
                self.files_to_process.append(file_path)
                self.file_listbox.insert(tk.END, os.path.basename(file_path))
                
        self.debug_logger.log('INFO', f"{len(files)}個のファイルが追加されました")
        
    def select_files(self):
        """ファイル選択"""
        files = filedialog.askopenfilenames(
            title="処理ファイルを選択",
            filetypes=[("PDFファイル", "*.pdf"), ("CSVファイル", "*.csv"), ("全ファイル", "*.*")]
        )
        
        for file_path in files:
            if file_path not in self.files_to_process:
                self.files_to_process.append(file_path)
                self.file_listbox.insert(tk.END, os.path.basename(file_path))
                
    def clear_files(self):
        """ファイルリストクリア"""
        self.files_to_process.clear()
        self.file_listbox.delete(0, tk.END)
        
    def select_output_dir(self):
        """出力ディレクトリ選択"""
        directory = filedialog.askdirectory(title="出力ディレクトリを選択")
        if directory:
            self.output_dir_var.set(directory)
            
    def process_files(self):
        """ファイル処理実行"""
        if not self.files_to_process:
            messagebox.showwarning("警告", "処理するファイルが選択されていません")
            return
            
        user_yymm = self.yymm_var.get().strip()
        
        # 処理をバックグラウンドで実行
        threading.Thread(target=self._process_files_thread, args=(user_yymm,), daemon=True).start()
        
    def _process_files_thread(self, user_yymm):
        """ファイル処理（スレッド）"""
        self.debug_logger.log('INFO', f"=== 一括処理開始 ({len(self.files_to_process)}ファイル) ===")
        
        success_count = 0
        error_count = 0
        
        for file_path in self.files_to_process:
            result = self.processor.process_file(file_path, user_yymm)
            
            if result['success']:
                # ファイルリネーム実行
                try:
                    original_path = Path(file_path)
                    new_path = Path(self.output_dir_var.get()) / result['new_name']
                    
                    # 同名ファイル確認
                    if new_path.exists() and not self.overwrite_var.get():
                        self.debug_logger.log('WARNING', f"スキップ（同名ファイル存在）: {new_path.name}")
                        continue
                        
                    # バックアップ
                    if self.backup_var.get():
                        backup_path = new_path.with_suffix(f".bak{original_path.suffix}")
                        if new_path.exists():
                            shutil.copy2(new_path, backup_path)
                            
                    # コピー実行
                    shutil.copy2(original_path, new_path)
                    
                    self.debug_logger.log('INFO', f"処理成功: {original_path.name} → {new_path.name}")
                    success_count += 1
                    
                except Exception as e:
                    self.debug_logger.log('ERROR', f"ファイル操作エラー: {e}")
                    error_count += 1
            else:
                self.debug_logger.log('ERROR', f"処理失敗: {os.path.basename(file_path)} - {result['error']}")
                error_count += 1
                
        self.debug_logger.log('INFO', f"=== 処理完了 成功:{success_count} エラー:{error_count} ===")
        
        # 結果表示
        self.root.after(0, lambda: messagebox.showinfo(
            "処理完了", 
            f"処理が完了しました。\n成功: {success_count}件\nエラー: {error_count}件"
        ))
        
    def clear_debug_log(self):
        """デバッグログクリア"""
        self.debug_text.delete(1.0, tk.END)
        
    def save_debug_log(self):
        """デバッグログ保存"""
        log_content = self.debug_text.get(1.0, tk.END)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt")],
            title="ログファイル保存"
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            messagebox.showinfo("保存完了", f"ログを保存しました: {file_path}")
            
    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    try:
        app = TaxDocumentRenamerGUI()
        app.run()
    except Exception as e:
        print(f"アプリケーション起動エラー: {e}")
        messagebox.showerror("エラー", f"アプリケーションの起動に失敗しました:\n{e}")

if __name__ == "__main__":
    main()