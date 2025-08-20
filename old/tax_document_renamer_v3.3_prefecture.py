#!/usr/bin/env python3
"""
税務書類リネームシステム v3.3 都道府県・市町村対応版
- 47都道府県選択式
- 市町村入力欄
- ファイル選択タブに配置
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import os
import io
import re
import shutil
import logging
import csv
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
    try:
        import pandas as pd
        PANDAS_AVAILABLE = True
    except ImportError:
        PANDAS_AVAILABLE = False
        print("Pandas not available, CSV processing will use basic csv module")
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
        
        # 既存ハンドラークリア
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # ファイルハンドラー
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # フォーマット
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
    def log(self, level, message):
        """ログ出力"""
        try:
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
                self.text_widget.update()
        except Exception as e:
            print(f"ログ出力エラー: {e}")

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
            '一括償却資産明細表': ['一括償却資産明細表', '一括償却資産明細'],
            '少額減価償却資産明細表': ['少額減価償却資産明細表', '少額'],
            
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
                    try:
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
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
            if PANDAS_AVAILABLE:
                df = pd.read_csv(file_path, encoding='utf-8', nrows=10)  # 先頭10行のみ
                csv_text = ' '.join(df.columns.tolist())  # カラム名から判定
            else:
                # pandas未使用の場合、基本的なcsvモジュール使用
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, [])
                    csv_text = ' '.join(headers)
            
            result['processing_details'].append(f"CSV読み込み成功")
            
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

class TaxDocumentRenamerGUI:
    """メインGUIクラス"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v3.3 都道府県・市町村対応版")
        self.root.geometry("1000x800")
        
        self.debug_logger = None
        self.processor = None
        self.files_to_process = []
        self.rename_results = []  # リネーム結果保存用
        
        # 47都道府県リスト
        self.prefectures = [
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        self.setup_ui()
        self.setup_processors()
        
    def setup_ui(self):
        """UI構築"""
        try:
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
            
            # タブ3: リネーム結果
            self.results_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.results_tab, text="リネーム結果")
            self.setup_results_tab()
            
            # タブ4: デバッグログ
            self.debug_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.debug_tab, text="デバッグログ")
            self.setup_debug_tab()
            
        except Exception as e:
            messagebox.showerror("UI設定エラー", f"ユーザーインターフェースの設定に失敗しました:\n{e}")
        
    def setup_file_tab(self):
        """ファイル選択タブ"""
        try:
            # 上部：設定エリア
            settings_frame = ttk.LabelFrame(self.file_tab, text="処理設定")
            settings_frame.pack(fill='x', padx=10, pady=5)
            
            # YYMM入力
            yymm_frame = ttk.Frame(settings_frame)
            yymm_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Label(yymm_frame, text="年月(YYMM):").pack(side='left')
            self.yymm_var = tk.StringVar()
            yymm_entry = ttk.Entry(yymm_frame, textvariable=self.yymm_var, width=10)
            yymm_entry.pack(side='left', padx=(5, 0))
            
            # 都道府県・市町村設定
            location_frame = ttk.Frame(settings_frame)
            location_frame.pack(fill='x', padx=10, pady=5)
            
            # 都道府県選択（複数セット）
            prefecture_label = ttk.Label(location_frame, text="都道府県設定:")
            prefecture_label.pack(anchor='w')
            
            self.prefecture_frames = []
            self.prefecture_vars = []
            self.city_vars = []
            
            for i in range(5):
                frame = ttk.Frame(location_frame)
                frame.pack(fill='x', pady=2)
                
                ttk.Label(frame, text=f"セット{i+1}:").pack(side='left')
                
                # 都道府県選択
                prefecture_var = tk.StringVar()
                self.prefecture_vars.append(prefecture_var)
                prefecture_combo = ttk.Combobox(frame, textvariable=prefecture_var, 
                                              values=self.prefectures, width=15, state="readonly")
                prefecture_combo.pack(side='left', padx=(5, 5))
                
                # 市町村入力
                ttk.Label(frame, text="市町村:").pack(side='left')
                city_var = tk.StringVar()
                self.city_vars.append(city_var)
                city_entry = ttk.Entry(frame, textvariable=city_var, width=20)
                city_entry.pack(side='left', padx=(5, 0))
                
                self.prefecture_frames.append(frame)
            
            # デフォルト設定ボタン
            default_btn_frame = ttk.Frame(location_frame)
            default_btn_frame.pack(fill='x', pady=5)
            ttk.Button(default_btn_frame, text="デフォルト設定", command=self.set_default_locations).pack(side='left')
            ttk.Button(default_btn_frame, text="設定クリア", command=self.clear_locations).pack(side='left', padx=(10, 0))
            
            # ファイル選択エリア
            file_area_frame = ttk.LabelFrame(self.file_tab, text="ファイル選択")
            file_area_frame.pack(fill='both', expand=True, padx=10, pady=5)
            
            # ファイル選択エリア（シンプルなFrame）
            drop_frame = tk.Frame(file_area_frame, bg='lightgray', height=80)
            drop_frame.pack(fill='x', padx=10, pady=10)
            drop_frame.pack_propagate(False)
            
            drop_label = tk.Label(drop_frame, text="ファイル選択エリア（下のボタンでファイル選択）", 
                                 bg='lightgray', font=('Arial', 12))
            drop_label.pack(expand=True)
            
            # ファイル選択ボタン
            btn_frame = ttk.Frame(file_area_frame)
            btn_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Button(btn_frame, text="ファイル選択", command=self.select_files).pack(side='left')
            ttk.Button(btn_frame, text="処理実行", command=self.process_files).pack(side='left', padx=(10, 0))
            ttk.Button(btn_frame, text="クリア", command=self.clear_files).pack(side='left', padx=(10, 0))
            ttk.Button(btn_frame, text="結果保存", command=self.save_results).pack(side='left', padx=(10, 0))
            
            # ファイルリスト
            list_frame = ttk.Frame(file_area_frame)
            list_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            self.file_listbox = tk.Listbox(list_frame)
            scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
            
            self.file_listbox.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=self.file_listbox.yview)
            
            self.file_listbox.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
        except Exception as e:
            messagebox.showerror("ファイルタブエラー", f"ファイル選択タブの設定に失敗しました:\n{e}")
        
    def setup_settings_tab(self):
        """処理設定タブ"""
        try:
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
            
            # 命名規則表示
            rules_frame = ttk.LabelFrame(self.settings_tab, text="命名規則参考")
            rules_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            rules_text = scrolledtext.ScrolledText(rules_frame, height=15)
            rules_text.pack(fill='both', expand=True, padx=5, pady=5)
            
            # 命名規則を表示
            rules_content = """主要な命名規則:

【法人税関連】
• 法人税申告書 → 0001_法人税及び地方法人税申告書_YYMM.pdf
• 添付資料（法人税） → 0002_添付資料_法人税_YYMM.pdf

【消費税関連】
• 消費税申告書 → 3001_消費税申告書_YYMM.pdf
• 添付資料（消費税） → 3002_添付資料_消費税_YYMM.pdf

【決算書類】
• 決算書 → 5001_決算書_YYMM.pdf
• 総勘定元帳 → 5002_総勘定元帳_YYMM.pdf
• 補助元帳 → 5003_補助元帳_YYMM.pdf
• 仕訳帳（PDF） → 5005_仕訳帳_YYMM.pdf
• 仕訳帳（CSV） → 5006_仕訳帳_YYMM.csv

【税区分集計表】
• 勘定科目別税区分集計表 → 7001_勘定科目別税区分集計表_YYMM.pdf
• 税区分集計表 → 7002_税区分集計表_YYMM.pdf

【固定資産】
• 固定資産台帳 → 6001_固定資産台帳_YYMM.pdf
• 一括償却資産明細表 → 6002_一括償却資産明細表_YYMM.pdf
• 少額減価償却資産明細表 → 6003_少額減価償却資産明細表_YYMM.pdf

【地方税】
• 都道府県申告 → 1001_都道府県申告_YYMM.pdf
• 市町村申告 → 2001_市町村申告_YYMM.pdf

【その他】
• 納付税額一覧表 → 0000_納付税額一覧表_YYMM.pdf
• 納付情報 → 2004_納付情報_YYMM.pdf
"""
            rules_text.insert(tk.END, rules_content)
            rules_text.config(state='disabled')
            
        except Exception as e:
            messagebox.showerror("設定タブエラー", f"設定タブの設定に失敗しました:\n{e}")
            
    def setup_results_tab(self):
        """リネーム結果タブ"""
        try:
            # 結果表示エリア
            results_frame = ttk.Frame(self.results_tab)
            results_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Treeview（表形式）
            columns = ("元ファイル名", "新ファイル名", "文書種別", "状態")
            self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
            
            # ヘッダー設定
            for col in columns:
                self.results_tree.heading(col, text=col)
                self.results_tree.column(col, width=200)
                
            # スクロールバー
            results_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.results_tree.yview)
            self.results_tree.configure(yscrollcommand=results_scrollbar.set)
            
            self.results_tree.pack(side='left', fill='both', expand=True)
            results_scrollbar.pack(side='right', fill='y')
            
            # 結果操作ボタン
            results_btn_frame = ttk.Frame(self.results_tab)
            results_btn_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Button(results_btn_frame, text="結果クリア", command=self.clear_results).pack(side='left')
            ttk.Button(results_btn_frame, text="CSV出力", command=self.export_results_csv).pack(side='left', padx=(10, 0))
            ttk.Button(results_btn_frame, text="Excel出力", command=self.export_results_excel).pack(side='left', padx=(10, 0))
            
        except Exception as e:
            messagebox.showerror("結果タブエラー", f"結果タブの設定に失敗しました:\n{e}")
        
    def setup_debug_tab(self):
        """デバッグログタブ"""
        try:
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
            
        except Exception as e:
            messagebox.showerror("デバッグタブエラー", f"デバッグタブの設定に失敗しました:\n{e}")
        
    def setup_processors(self):
        """プロセッサー初期化"""
        try:
            self.debug_logger = DebugLogger(self.debug_text)
            self.processor = DocumentProcessor(self.debug_logger)
            
            self.debug_logger.log('INFO', "税務書類リネームシステム v3.3 都道府県・市町村対応版 起動")
            
        except Exception as e:
            messagebox.showerror("プロセッサー初期化エラー", f"システムの初期化に失敗しました:\n{e}")
    
    def set_default_locations(self):
        """デフォルト都道府県・市町村設定"""
        defaults = [
            ("東京都", "港区"),
            ("愛知県", "蒲郡市"),
            ("福岡県", "福岡市"),
            ("大阪府", "大阪市"),
            ("神奈川県", "横浜市")
        ]
        
        for i, (prefecture, city) in enumerate(defaults):
            if i < len(self.prefecture_vars):
                self.prefecture_vars[i].set(prefecture)
                self.city_vars[i].set(city)
                
        self.debug_logger.log('INFO', "デフォルト都道府県・市町村設定を適用しました")
    
    def clear_locations(self):
        """都道府県・市町村設定クリア"""
        for prefecture_var, city_var in zip(self.prefecture_vars, self.city_vars):
            prefecture_var.set("")
            city_var.set("")
        self.debug_logger.log('INFO', "都道府県・市町村設定をクリアしました")
        
    def select_files(self):
        """ファイル選択"""
        try:
            files = filedialog.askopenfilenames(
                title="処理ファイルを選択",
                filetypes=[("PDFファイル", "*.pdf"), ("CSVファイル", "*.csv"), ("全ファイル", "*.*")]
            )
            
            for file_path in files:
                if file_path not in self.files_to_process:
                    self.files_to_process.append(file_path)
                    self.file_listbox.insert(tk.END, os.path.basename(file_path))
                    
            if files:
                self.debug_logger.log('INFO', f"{len(files)}個のファイルが追加されました")
                
        except Exception as e:
            messagebox.showerror("ファイル選択エラー", f"ファイル選択に失敗しました:\n{e}")
                
    def clear_files(self):
        """ファイルリストクリア"""
        try:
            self.files_to_process.clear()
            self.file_listbox.delete(0, tk.END)
            self.debug_logger.log('INFO', "ファイルリストをクリアしました")
        except Exception as e:
            messagebox.showerror("クリアエラー", f"ファイルリストのクリアに失敗しました:\n{e}")
        
    def select_output_dir(self):
        """出力ディレクトリ選択"""
        try:
            directory = filedialog.askdirectory(title="出力ディレクトリを選択")
            if directory:
                self.output_dir_var.set(directory)
                self.debug_logger.log('INFO', f"出力ディレクトリ設定: {directory}")
        except Exception as e:
            messagebox.showerror("ディレクトリ選択エラー", f"ディレクトリ選択に失敗しました:\n{e}")
            
    def process_files(self):
        """ファイル処理実行"""
        try:
            if not self.files_to_process:
                messagebox.showwarning("警告", "処理するファイルが選択されていません")
                return
                
            user_yymm = self.yymm_var.get().strip()
            
            # 都道府県・市町村設定をログ出力
            for i, (pref_var, city_var) in enumerate(zip(self.prefecture_vars, self.city_vars)):
                pref = pref_var.get()
                city = city_var.get()
                if pref or city:
                    self.debug_logger.log('INFO', f"セット{i+1}: {pref} {city}")
            
            # 結果テーブルクリア
            self.clear_results()
            
            # 処理をバックグラウンドで実行
            threading.Thread(target=self._process_files_thread, args=(user_yymm,), daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("処理開始エラー", f"処理の開始に失敗しました:\n{e}")
        
    def _process_files_thread(self, user_yymm):
        """ファイル処理（スレッド）"""
        try:
            self.debug_logger.log('INFO', f"=== 一括処理開始 ({len(self.files_to_process)}ファイル) ===")
            if user_yymm:
                self.debug_logger.log('INFO', f"ユーザー入力YYMM: {user_yymm}")
            
            success_count = 0
            error_count = 0
            self.rename_results = []
            
            for file_path in self.files_to_process:
                result = self.processor.process_file(file_path, user_yymm)
                
                # 結果を保存
                rename_result = {
                    'original_file': os.path.basename(file_path),
                    'new_file': result.get('new_name', ''),
                    'document_type': result.get('document_type', '不明'),
                    'status': '成功' if result['success'] else 'エラー',
                    'error_message': result.get('error', '')
                }
                self.rename_results.append(rename_result)
                
                # 結果テーブルに追加
                self.root.after(0, lambda r=rename_result: self.add_result_to_table(r))
                
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
                        if self.backup_var.get() and new_path.exists():
                            backup_path = new_path.with_suffix(f".bak{original_path.suffix}")
                            shutil.copy2(new_path, backup_path)
                            self.debug_logger.log('INFO', f"バックアップ作成: {backup_path.name}")
                                
                        # コピー実行
                        shutil.copy2(original_path, new_path)
                        
                        self.debug_logger.log('INFO', f"処理成功: {original_path.name} → {new_path.name}")
                        success_count += 1
                        
                    except Exception as e:
                        self.debug_logger.log('ERROR', f"ファイル操作エラー: {e}")
                        error_count += 1
                        # 結果ステータス更新
                        rename_result['status'] = 'ファイル操作エラー'
                        rename_result['error_message'] = str(e)
                else:
                    self.debug_logger.log('ERROR', f"処理失敗: {os.path.basename(file_path)} - {result['error']}")
                    error_count += 1
                    
            self.debug_logger.log('INFO', f"=== 処理完了 成功:{success_count} エラー:{error_count} ===")
            
            # 結果表示
            self.root.after(0, lambda: messagebox.showinfo(
                "処理完了", 
                f"処理が完了しました。\n成功: {success_count}件\nエラー: {error_count}件\n\n詳細は「リネーム結果」タブをご確認ください。"
            ))
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"処理スレッドエラー: {e}")
            self.root.after(0, lambda: messagebox.showerror("処理エラー", f"処理中にエラーが発生しました:\n{e}"))
    
    def add_result_to_table(self, result):
        """結果テーブルに行追加"""
        try:
            self.results_tree.insert('', 'end', values=(
                result['original_file'],
                result['new_file'],
                result['document_type'],
                result['status']
            ))
        except Exception as e:
            print(f"テーブル追加エラー: {e}")
    
    def clear_results(self):
        """結果テーブルクリア"""
        try:
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.rename_results = []
        except Exception as e:
            messagebox.showerror("結果クリアエラー", f"結果のクリアに失敗しました:\n{e}")
    
    def save_results(self):
        """結果をファイル保存"""
        try:
            if not self.rename_results:
                messagebox.showwarning("警告", "保存する結果がありません")
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("テキストファイル", "*.txt"), ("CSVファイル", "*.csv")],
                title="リネーム結果を保存"
            )
            
            if file_path:
                if file_path.endswith('.csv'):
                    self.export_results_csv(file_path)
                else:
                    self.export_results_txt(file_path)
                    
        except Exception as e:
            messagebox.showerror("保存エラー", f"結果の保存に失敗しました:\n{e}")
    
    def export_results_txt(self, file_path=None):
        """結果をテキスト形式で出力"""
        try:
            if not file_path:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("テキストファイル", "*.txt")],
                    title="リネーム結果をテキスト保存"
                )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("税務書類リネーム結果一覧\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"総件数: {len(self.rename_results)}件\n\n")
                    
                    for i, result in enumerate(self.rename_results, 1):
                        f.write(f"{i:3d}. {result['original_file']}\n")
                        f.write(f"     → {result['new_file']}\n")
                        f.write(f"     文書種別: {result['document_type']}\n")
                        f.write(f"     状態: {result['status']}\n")
                        if result['error_message']:
                            f.write(f"     エラー: {result['error_message']}\n")
                        f.write("\n")
                        
                messagebox.showinfo("保存完了", f"結果を保存しました: {file_path}")
                
        except Exception as e:
            messagebox.showerror("エクスポートエラー", f"テキスト出力に失敗しました:\n{e}")
    
    def export_results_csv(self, file_path=None):
        """結果をCSV形式で出力"""
        try:
            if not file_path:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSVファイル", "*.csv")],
                    title="リネーム結果をCSV保存"
                )
            
            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['元ファイル名', '新ファイル名', '文書種別', '状態', 'エラーメッセージ'])
                    
                    for result in self.rename_results:
                        writer.writerow([
                            result['original_file'],
                            result['new_file'],
                            result['document_type'],
                            result['status'],
                            result['error_message']
                        ])
                        
                messagebox.showinfo("保存完了", f"CSV結果を保存しました: {file_path}")
                
        except Exception as e:
            messagebox.showerror("エクスポートエラー", f"CSV出力に失敗しました:\n{e}")
    
    def export_results_excel(self):
        """結果をExcel形式で出力"""
        try:
            if PANDAS_AVAILABLE:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excelファイル", "*.xlsx")],
                    title="リネーム結果をExcel保存"
                )
                
                if file_path:
                    df = pd.DataFrame(self.rename_results)
                    df.columns = ['元ファイル名', '新ファイル名', '文書種別', '状態', 'エラーメッセージ']
                    df.to_excel(file_path, index=False)
                    messagebox.showinfo("保存完了", f"Excel結果を保存しました: {file_path}")
            else:
                messagebox.showinfo("情報", "Excelエクスポートにはpandasが必要です。CSV形式で保存してください。")
                
        except Exception as e:
            messagebox.showerror("エクスポートエラー", f"Excel出力に失敗しました:\n{e}")
        
    def clear_debug_log(self):
        """デバッグログクリア"""
        try:
            self.debug_text.delete(1.0, tk.END)
        except Exception as e:
            messagebox.showerror("ログクリアエラー", f"ログのクリアに失敗しました:\n{e}")
        
    def save_debug_log(self):
        """デバッグログ保存"""
        try:
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
                
        except Exception as e:
            messagebox.showerror("ログ保存エラー", f"ログの保存に失敗しました:\n{e}")
            
    def run(self):
        """アプリケーション実行"""
        try:
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("実行エラー", f"アプリケーションの実行中にエラーが発生しました:\n{e}")

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