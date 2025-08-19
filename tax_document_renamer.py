# =============================================================================
# 税務書類リネームシステム exe版
# =============================================================================

#!/usr/bin/env python3
"""
税務書類画像認識・分割・リネームシステム
exe化対応版
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import os
import io
import re
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import csv

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
    print("pip install PyPDF2 PyMuPDF pytesseract Pillow を実行してください")
    sys.exit(1)

# Tesseractのパス設定（exe化対応）
def setup_tesseract():
    """Tesseractの設定"""
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract"
    ]
    
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True
    
    # システムPATHから検索
    try:
        import subprocess
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
        return True
    except:
        pass
    
    return False

class DocumentProcessor:
    """書類処理のメインクラス"""
    
    def __init__(self):
        self.setup_patterns()
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定"""
        log_dir = os.path.join(os.path.expanduser("~"), "TaxDocumentRenamer")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "tax_document_renamer.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def setup_patterns(self):
        """判定キーワードパターンの設定"""
        self.document_patterns = {
            # 都道府県申告書パターン（強化）
            '1001_都道府県申告': [
                '法人都道府県民税・事業税・特別法人事業税',
                '都道府県民税',
                '法人事業税',
                '特別法人事業税',
                '県税事務所',
                '都税事務所',
                '道税事務所',
                '府税事務所'
            ],
            
            # 市町村申告書パターン（2001番台強化）
            '2001_市町村申告': [
                '法人市町村民税',
                '法人市民税',
                '市町村民税',
                '市民税',
                '市役所',
                '市税事務所',
                '町役場',
                '村役場'
            ],
            
            # 固定資産関連（6002/6003番台強化）
            '6002_一括償却資産明細表': [
                '一括償却資産明細表',
                '一括償却資産明細',
                '一括償却明細表',
                '一括償却'
            ],
            
            '6003_少額減価償却資産明細表': [
                '少額減価償却資産明細表',
                '少額減価償却資産明細',
                '少額減価償却明細表',
                '少額減価償却',
                '少額'
            ],
            
            # 地方税関連
            '2004_納付情報': ['税目:法人住民税', '法人住民税'],
            '1004_納付情報': ['税目:法人二税・特別税', '法人二税'],
            '2003_受信通知': ['法人市町村民税 確定申告', '市町村民税 確定申告'],
            
            # 国税関連
            '3003_受信通知': ['種目 消費税申告書'],
            '3004_納付情報': ['税目 消費税及地方消費税'],
            '0003_受信通知': ['種目 法人税及び地方法人税申告書'],
            '0004_納付情報': ['税目 法人税及地方法人税'],
            
            # 申告書類
            '0000_納付税額一覧表': ['納付税額一覧表'],
            '0001_法人税申告書': ['事業年度分の法人税申告書', '課税事業年度分の地方法人税申告書'],
            '0002_添付資料_法人税': ['添付書類送付書', '内国法人の確定申告'],
            '3001_消費税申告書': ['この申告書による消費税の税額の計算'],
            '3002_添付資料_消費税': ['添付書類送付書', '消費税及び地方消費税'],
            
            # 会計書類
            '5001_決算書': ['決算報告書', '貸借対照表', '損益計算書'],
            '5002_総勘定元帳': ['総勘定元帳'],
            '5003_補助元帳': ['補助元帳'],
            '5004_残高試算表': ['残高試算表'],
            '5005_仕訳帳': ['仕訳帳'],
            '6001_固定資産台帳': ['固定資産台帳'],
            '7001_税区分集計表': ['勘定科目別税区分集計表', '税区分集計表']
        }
        
        # 都道府県パターン
        self.prefecture_patterns = [
            '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
            '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
            '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
            '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
            '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
            '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
            '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """PDFからテキストを抽出"""
        pages_text = []
        
        try:
            # まずPyMuPDFでテキスト抽出を試行
            doc = fitz.open(pdf_path)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                # テキストが少ない場合やOCRが必要な場合はOCRを実行
                if len(text.strip()) < 100:  # 閾値を上げてOCRを積極的に使用
                    try:
                        # ページを画像に変換（高解像度）
                        mat = fitz.Matrix(3.0, 3.0)  # 解像度をさらに上げる
                        pix = page.get_pixmap(matrix=mat)
                        img_data = pix.tobytes("png")
                        
                        # PILでImage作成
                        img = Image.open(io.BytesIO(img_data))
                        
                        # OCR設定を最適化（シンプル版）
                        custom_config = r'--oem 3 --psm 6'
                        
                        # OCR実行（設定を最適化）
                        ocr_text = pytesseract.image_to_string(img, lang='jpn', config=custom_config)
                        
                        # OCR結果を常に追加（既存テキストと組み合わせ）
                        combined_text = text + "\n" + ocr_text
                        text = combined_text if len(combined_text.strip()) > len(text.strip()) else text
                        
                    except Exception as ocr_error:
                        logging.warning(f"OCR処理エラー (page {page_num}): {str(ocr_error)}")
                
                pages_text.append(text)
            
            doc.close()
            
        except Exception as e:
            logging.error(f"PDF読み込みエラー: {pdf_path}, {str(e)}")
            
            # フォールバック: PyPDF2で試行
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        pages_text.append(text)
            except Exception as fallback_error:
                logging.error(f"フォールバック読み込みも失敗: {str(fallback_error)}")
        
        return pages_text
    
    def detect_document_type(self, text: str) -> tuple:
        """書類種別を判定（マッチしたキーワードも返す）"""
        matched_keywords = []
        
        # 完全一致を優先
        for doc_type, keywords in self.document_patterns.items():
            if all(keyword in text for keyword in keywords):
                matched_keywords = [k for k in keywords if k in text]
                return doc_type, matched_keywords
        
        # 部分一致で判定
        for doc_type, keywords in self.document_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    matched_keywords.append(keyword)
                    return doc_type, matched_keywords
        
        return '不明', []
    
    def extract_prefecture_city(self, text: str) -> Tuple[str, str]:
        """都道府県と市町村を抽出（強化版）"""
        prefecture = ''
        city = ''
        
        # 税事務所パターンによる都道府県抽出（最優先）
        tax_office_patterns = {
            r'愛知県[^県]*県税事務所': '愛知県',
            r'福岡県[^県]*県税事務所': '福岡県',
            r'東京都[^都]*都税事務所': '東京都',
            r'大阪府[^府]*府税事務所': '大阪府',
            r'京都府[^府]*府税事務所': '京都府',
            r'北海道[^道]*道税事務所': '北海道',
            r'([^県府道都]{2,4}県)[^県]*県税事務所': None,  # 汎用県パターン
            r'([^県府道都]{2,4}府)[^府]*府税事務所': None,  # 汎用府パターン
        }
        
        for pattern, pref_name in tax_office_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                if pref_name:
                    prefecture = pref_name
                    break
                else:
                    # 汎用パターンの場合、マッチした内容から都道府県名を抽出
                    if isinstance(matches[0], str):
                        prefecture = matches[0]
                        break
        
        # 税事務所パターンで見つからない場合、直接的な都道府県名検索
        if not prefecture:
            matched_prefs = []
            for pref in self.prefecture_patterns:
                if pref in text:
                    matched_prefs.append(pref)
            
            # 最も長い（具体的な）都道府県名を選択
            if matched_prefs:
                prefecture = max(matched_prefs, key=len)
        
        # 市町村長パターンによる市町村抽出（最優先）
        mayor_patterns = [
            r'([^県府道都]{2,10}市)長',
            r'([^県府道都]{2,10}町)長', 
            r'([^県府道都]{2,10}村)長',
            r'([^県府道都]{2,10}区)長'
        ]
        
        for pattern in mayor_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # 都道府県名を含まない市町村名を選択
                for match in matches:
                    if not any(pref_name[:-1] in match for pref_name in self.prefecture_patterns):
                        city = match
                        break
                if city:
                    break
        
        # 市町村長パターンで見つからない場合、一般的な市町村パターン
        if not city and prefecture and prefecture != '東京都':
            city_patterns = [
                r'([^県府道都\s]{2,10}[市町村区])',
            ]
            
            for pattern in city_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    # 都道府県名を含まない市町村名を選択
                    for match in matches:
                        if not any(pref_name[:-1] in match for pref_name in self.prefecture_patterns):
                            city = match
                            break
                    if city:
                        break
        
        return prefecture, city
    
    def extract_year_month(self, text: str) -> str:
        """年月を抽出してYYMM形式に変換"""
        # 令和年表記のパターン（複数パターン対応）
        reiwa_patterns = [
            r'R0?([0-9]{1,2})[年/\-.]0?([0-9]{1,2})',
            r'令和0?([0-9]{1,2})[年]0?([0-9]{1,2})[月]',
            r'令和([0-9]{1,2})[年/\-.]([0-9]{1,2})'
        ]
        
        for pattern in reiwa_patterns:
            match = re.search(pattern, text)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                if 1 <= month <= 12:  # 月の妥当性チェック
                    # 令和年を西暦下2桁に変換（令和6年 = 2024年）
                    western_year = (2018 + year) % 100
                    return f"{western_year:02d}{month:02d}"
        
        # 西暦パターン
        western_patterns = [
            r'20([0-9]{2})[年/\-.]0?([0-9]{1,2})[月]?',
            r'([0-9]{4})[年/\-.]0?([0-9]{1,2})[月]?'
        ]
        
        for pattern in western_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.group(1)) == 2:
                    year = int(match.group(1))
                else:
                    year = int(match.group(1)) % 100
                month = int(match.group(2))
                if 1 <= month <= 12:  # 月の妥当性チェック
                    return f"{year:02d}{month:02d}"
        
        return ''

class TaxDocumentGUI:
    """GUI管理クラス"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v2.0")
        self.root.geometry("1400x900")
        
        # アイコン設定（exe化対応）
        try:
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                icon_path = 'icon.ico'
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # Tesseract設定チェック
        if not setup_tesseract():
            messagebox.showwarning(
                "警告", 
                "Tesseract OCRが見つかりません。\n"
                "OCR機能が制限される可能性があります。\n\n"
                "https://github.com/UB-Mannheim/tesseract/wiki\n"
                "からTesseractをインストールしてください。"
            )
        
        self.processor = DocumentProcessor()
        self.files = []
        self.municipalities = [{'prefecture': '', 'city': ''} for _ in range(5)]
        self.year_month = ''
        self.results = []
        
        self.setup_gui()
        self.setup_styles()
    
    def setup_styles(self):
        """弥生会計風スタイル設定"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 弥生会計風カラー（青系ビジネステーマ）
        # メインカラー: #2E5984 (ダークブルー)
        # アクセント: #4A90C2 (ライトブルー)
        # 背景: #F8F9FA (明るいグレー)
        
        # カスタムスタイル
        style.configure('Title.TLabel', 
                       font=('Meiryo UI', 18, 'bold'), 
                       foreground='#2E5984',
                       background='#F8F9FA')
        style.configure('Heading.TLabel', 
                       font=('Meiryo UI', 12, 'bold'),
                       foreground='#2E5984')
        style.configure('Success.TLabel', foreground='#28A745')
        style.configure('Warning.TLabel', foreground='#FFC107')
        style.configure('Error.TLabel', foreground='#DC3545')
        
        # ノートブック（タブ）スタイル
        style.configure('TNotebook', background='#F8F9FA')
        style.configure('TNotebook.Tab', 
                       font=('Meiryo UI', 10, 'bold'),
                       padding=[12, 8],
                       focuscolor='none')
        
        # ボタンスタイル
        style.configure('Action.TButton',
                       font=('Meiryo UI', 10, 'bold'),
                       foreground='white',
                       background='#2E5984')
        
        # フレームスタイル
        style.configure('TLabelFrame', background='#F8F9FA')
        style.configure('TLabelFrame.Label', 
                       font=('Meiryo UI', 11, 'bold'),
                       foreground='#2E5984')
    
    def setup_gui(self):
        """GUI構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ウィンドウのリサイズ対応
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # タイトル
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(1, weight=1)
        
        title_label = ttk.Label(title_frame, text="税務書類リネームシステム", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        version_label = ttk.Label(title_frame, text="Version 2.1 - 弥生風デザイン版",
                                 font=('Meiryo UI', 10), foreground='#6C757D')
        version_label.grid(row=0, column=1, sticky=tk.E)
        
        # タブノートブック
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 各タブの作成
        self.setup_input_tab()
        self.setup_results_tab()
        self.setup_debug_tab()
        
        # ステータスバー
        self.setup_statusbar()
    
    def setup_input_tab(self):
        """入力タブの設定"""
        input_frame = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(input_frame, text="📁 ファイル選択・設定")
        
        # ウィンドウのリサイズ対応
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)
        
        # スクロール可能フレーム
        canvas = tk.Canvas(input_frame)
        scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # ファイル選択セクション
        self.setup_file_section(scrollable_frame)
        
        # 自治体情報セクション
        self.setup_municipality_section(scrollable_frame)
        
        # 年月入力セクション
        self.setup_datetime_section(scrollable_frame)
        
        # 処理ボタン
        self.setup_process_section(scrollable_frame)
    
    def setup_results_tab(self):
        """結果タブの設定"""
        results_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(results_frame, text="📊 処理結果")
        
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # 結果表示セクション
        self.setup_results_section(results_frame)
    
    def setup_debug_tab(self):
        """デバッグタブの設定"""
        debug_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(debug_frame, text="🔧 開発者ログ")
        
        debug_frame.columnconfigure(0, weight=1)
        debug_frame.rowconfigure(0, weight=1)
        
        # ログ表示セクション
        self.setup_log_section(debug_frame)
    
    def setup_file_section(self, parent):
        """ファイル選択セクション"""
        file_frame = ttk.LabelFrame(parent, text="1. PDFファイル選択", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        file_frame.columnconfigure(0, weight=1)
        
        # ボタンフレーム
        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="PDFファイルを選択", 
                  command=self.select_files).grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(button_frame, text="フォルダを選択", 
                  command=self.select_folder).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(button_frame, text="クリア", 
                  command=self.clear_files).grid(row=0, column=2)
        
        # ファイル数表示
        self.file_count_label = ttk.Label(button_frame, text="選択ファイル: 0件")
        self.file_count_label.grid(row=0, column=3, padx=(20, 0))
        
        # ファイルリスト
        list_frame = ttk.Frame(file_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        list_frame.columnconfigure(0, weight=1)
        
        self.file_listbox = tk.Listbox(list_frame, height=6)
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
    
    def setup_municipality_section(self, parent):
        """自治体情報セクション"""
        muni_frame = ttk.LabelFrame(parent, text="2. 自治体情報入力（任意）", padding="10")
        muni_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # 5つのセット（2列レイアウト）
        self.muni_vars = []
        for i in range(5):
            row = i // 2
            col = i % 2
            
            set_frame = ttk.LabelFrame(muni_frame, text=f"セット{i+1}", padding="5")
            set_frame.grid(row=row, column=col, sticky=(tk.W, tk.E), padx=5, pady=2)
            
            # 都道府県
            ttk.Label(set_frame, text="都道府県:").grid(row=0, column=0, sticky=tk.W)
            pref_var = tk.StringVar()
            pref_combo = ttk.Combobox(set_frame, textvariable=pref_var, 
                                    values=self.processor.prefecture_patterns,
                                    width=12, state="readonly")
            pref_combo.grid(row=0, column=1, padx=(5, 0), pady=2)
            
            # 市町村
            ttk.Label(set_frame, text="市町村:").grid(row=1, column=0, sticky=tk.W)
            city_var = tk.StringVar()
            city_entry = ttk.Entry(set_frame, textvariable=city_var, width=15)
            city_entry.grid(row=1, column=1, padx=(5, 0), pady=2)
            
            self.muni_vars.append({
                'pref': pref_var, 
                'city': city_var, 
                'city_entry': city_entry
            })
            
            # 東京都の場合の制御
            def on_pref_change(event, idx=i):
                if self.muni_vars[idx]['pref'].get() == '東京都':
                    self.muni_vars[idx]['city'].set('')
                    self.muni_vars[idx]['city_entry'].config(state='disabled')
                else:
                    self.muni_vars[idx]['city_entry'].config(state='normal')
            
            pref_combo.bind('<<ComboboxSelected>>', on_pref_change)
    
    def setup_datetime_section(self, parent):
        """年月入力セクション"""
        date_frame = ttk.LabelFrame(parent, text="3. 年月入力（任意）", padding="10")
        date_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        info_frame = ttk.Frame(date_frame)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(info_frame, text="YYMM形式:").grid(row=0, column=0, padx=(0, 10))
        
        self.year_month_var = tk.StringVar()
        self.year_month_var.set("2507")  # デフォルト値を設定
        year_month_entry = ttk.Entry(info_frame, textvariable=self.year_month_var, width=10)
        year_month_entry.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(info_frame, text="例: 2507 (2025年7月)").grid(row=0, column=2, padx=(0, 20))
        
        ttk.Label(info_frame, text="※ 手動入力が優先、空欄の場合は自動抽出", 
                 font=('Meiryo UI', 9), foreground='gray').grid(row=0, column=3)
    
    def setup_process_section(self, parent):
        """処理ボタンセクション"""
        process_frame = ttk.Frame(parent)
        process_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        # プログレスバー
        self.progress = ttk.Progressbar(process_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # ボタン（弥生会計風）
        self.process_btn = ttk.Button(process_frame, text="■ 処理実行", 
                                     style='Action.TButton',
                                     command=self.process_documents)
        self.process_btn.grid(row=1, column=0, padx=(0, 10))
        
        self.save_btn = ttk.Button(process_frame, text="💾 結果保存", 
                                  command=self.save_results, state='disabled')
        self.save_btn.grid(row=1, column=1, padx=(0, 10))
        
        self.rename_btn = ttk.Button(process_frame, text="📁 ファイルリネーム実行", 
                                    command=self.execute_rename, state='disabled')
        self.rename_btn.grid(row=1, column=2, padx=(0, 10))
        
        ttk.Button(process_frame, text="❓ ヘルプ", 
                  command=self.show_help).grid(row=1, column=3)
    
    def setup_results_section(self, parent):
        """結果表示セクション"""
        results_frame = ttk.LabelFrame(parent, text="処理結果", padding="10")
        results_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # ツリービューで結果表示
        tree_frame = ttk.Frame(results_frame)
        tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        columns = ('original', 'new', 'type', 'prefecture', 'city', 'status')
        self.results_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10)
        
        # ヘッダー設定
        self.results_tree.heading('original', text='元ファイル名')
        self.results_tree.heading('new', text='新ファイル名')
        self.results_tree.heading('type', text='書類種別')
        self.results_tree.heading('prefecture', text='都道府県')
        self.results_tree.heading('city', text='市町村')
        self.results_tree.heading('status', text='状態')
        
        # 列幅設定
        self.results_tree.column('original', width=200)
        self.results_tree.column('new', width=350)
        self.results_tree.column('type', width=120)
        self.results_tree.column('prefecture', width=80)
        self.results_tree.column('city', width=100)
        self.results_tree.column('status', width=60)
        
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # スクロールバー
        results_scrollbar_v = ttk.Scrollbar(tree_frame, orient="vertical", 
                                          command=self.results_tree.yview)
        results_scrollbar_v.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_tree.configure(yscrollcommand=results_scrollbar_v.set)
        
        results_scrollbar_h = ttk.Scrollbar(tree_frame, orient="horizontal", 
                                          command=self.results_tree.xview)
        results_scrollbar_h.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.results_tree.configure(xscrollcommand=results_scrollbar_h.set)
    
    def setup_log_section(self, parent):
        """ログ表示セクション"""
        log_frame = ttk.LabelFrame(parent, text="処理ログ", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # ログ表示エリア（弥生会計風）
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=100,
                                                 font=('Consolas', 10),
                                                 background='#FFFFFF',
                                                 foreground='#333333',
                                                 wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ログテキストのタグ設定（色分け）
        self.log_text.tag_configure('header', foreground='#2E5984', font=('Consolas', 10, 'bold'))
        self.log_text.tag_configure('success', foreground='#28A745')
        self.log_text.tag_configure('warning', foreground='#FFC107')
        self.log_text.tag_configure('error', foreground='#DC3545')
        self.log_text.tag_configure('info', foreground='#17A2B8')
        self.log_text.tag_configure('keyword', foreground='#6F42C1', font=('Consolas', 10, 'bold'))
        
        # ログクリアボタン
        ttk.Button(log_frame, text="ログクリア", 
                  command=lambda: self.log_text.delete(1.0, tk.END)).grid(
                      row=1, column=0, sticky=tk.E, pady=(5, 0))
    
    def setup_statusbar(self):
        """ステータスバー"""
        self.status_var = tk.StringVar()
        self.status_var.set("準備完了")
        
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(status_frame, textvariable=self.status_var, 
                 relief=tk.SUNKEN, anchor=tk.W).grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        status_frame.columnconfigure(0, weight=1)
    
    def update_file_count(self):
        """ファイル数表示更新"""
        count = len(self.files)
        self.file_count_label.config(text=f"選択ファイル: {count}件")
        self.status_var.set(f"{count}個のファイルが選択されています")
    
    def select_files(self):
        """ファイル選択"""
        filetypes = [("PDF files", "*.pdf"), ("All files", "*.*")]
        filenames = filedialog.askopenfilenames(title="PDFファイルを選択", filetypes=filetypes)
        
        for filename in filenames:
            if filename not in self.files:
                self.files.append(filename)
                self.file_listbox.insert(tk.END, os.path.basename(filename))
        
        self.update_file_count()
    
    def select_folder(self):
        """フォルダ選択"""
        folder_path = filedialog.askdirectory(title="PDFファイルが含まれるフォルダを選択")
        if folder_path:
            pdf_files = list(Path(folder_path).glob("*.pdf"))
            added_count = 0
            for pdf_file in pdf_files:
                if str(pdf_file) not in self.files:
                    self.files.append(str(pdf_file))
                    self.file_listbox.insert(tk.END, pdf_file.name)
                    added_count += 1
            
            if added_count > 0:
                self.log_text.insert(tk.END, f"フォルダから{added_count}個のPDFファイルを追加しました\n")
            
            self.update_file_count()
    
    def clear_files(self):
        """ファイルリストクリア"""
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.update_file_count()
        self.log_text.insert(tk.END, "ファイルリストをクリアしました\n")
    
    def validate_municipalities(self) -> List[str]:
        """自治体情報のバリデーション"""
        errors = []
        
        # 東京都の位置チェック
        tokyo_indices = []
        for i, muni_var in enumerate(self.muni_vars):
            if muni_var['pref'].get() == '東京都':
                tokyo_indices.append(i)
        
        if tokyo_indices and min(tokyo_indices) > 0:
            errors.append("東京都は1番目（セット1）に入力してください")
        
        return errors
    
    def generate_filename(self, doc_type, prefecture: str = '', city: str = '', 
                         index: int = 0, year_month: str = '') -> str:
        """ファイル名生成"""
        # doc_typeがタプルの場合は最初の要素を使用
        if isinstance(doc_type, tuple):
            doc_type = doc_type[0]
        doc_type = str(doc_type)
        
        ym = year_month or self.year_month_var.get() or 'YYMM'
        
        # 都道府県申告書の連番処理（10番飛び）
        if '1001_' in doc_type and prefecture:
            # 都道府県申告書は1001, 1011, 1021, 1031, 1041...
            prefix = f"{1001 + (index * 10)}"
            return f"{prefix}_{prefecture}_法人都道府県民税・事業税・特別法人事業税_{ym}.pdf"
        
        # 市町村申告書の連番処理（10番飛び）
        if '2001_' in doc_type:
            # 市町村申告書は2001, 2011, 2021, 2031, 2041...
            prefix = f"{2001 + (index * 10)}"
            if prefecture and city:
                return f"{prefix}_{prefecture}{city}_法人市民税_{ym}.pdf"
            else:
                return f"{prefix}_市町村申告_{ym}.pdf"
        
        # 受信通知の連番処理
        if '2003_' in doc_type:
            prefix_map = ['2003', '2013', '2023', '2033', '2043']
            prefix = prefix_map[min(index, 4)]
            return f"{prefix}_受信通知_{ym}.pdf"
        
        # その他の書類
        base_name = doc_type.replace('_', '_', 1)
        return f"{base_name}_{ym}.pdf"
    
    def process_documents(self):
        """書類処理メイン"""
        if not self.files:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        # バリデーション
        errors = self.validate_municipalities()
        if errors:
            messagebox.showerror("エラー", "\n".join(errors))
            return
        
        # UI状態更新
        self.process_btn.config(state='disabled')
        self.progress.start()
        self.status_var.set("処理実行中...")
        
        # 結果クリア
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        self.results = []
        self.log_text.insert(tk.END, f"\n", 'header')
        self.log_text.insert(tk.END, f"{'🚀'*20} 処理開始 {'🚀'*20}\n", 'header')
        self.log_text.insert(tk.END, f"📅 開始時刻: ", 'info')
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", 'success')
        self.log_text.insert(tk.END, f"📊 対象ファイル数: ", 'info')
        self.log_text.insert(tk.END, f"{len(self.files)}件\n", 'success')
        self.log_text.insert(tk.END, f"{'='*60}\n", 'header')
        self.root.update()
        
        # 自治体情報取得
        active_municipalities = []
        for muni_var in self.muni_vars:
            pref = muni_var['pref'].get()
            city = muni_var['city'].get()
            if pref:
                active_municipalities.append({'prefecture': pref, 'city': city})
        
        try:
            total_files = len(self.files)
            # 書類種別カウンター
            prefecture_doc_count = 0
            municipality_doc_count = 0
            
            for i, file_path in enumerate(self.files):
                file_name = os.path.basename(file_path)
                self.log_text.insert(tk.END, f"\n[{i+1}/{total_files}] 処理中: {file_name}\n")
                self.status_var.set(f"処理中: {file_name} ({i+1}/{total_files})")
                self.root.update()
                
                # PDFからテキスト抽出
                self.log_text.insert(tk.END, "  テキスト抽出中...\n")
                self.root.update()
                
                pages_text = self.processor.extract_text_from_pdf(file_path)
                if not pages_text:
                    self.log_text.insert(tk.END, "  エラー: テキスト抽出失敗\n")
                    self.results.append({
                        'original': file_name,
                        'new': f"ERROR_{file_name}",
                        'type': 'エラー',
                        'prefecture': '(処理失敗)',
                        'city': '(処理失敗)',
                        'status': 'エラー',
                        'file_path': file_path
                    })
                    continue
                
                # 全ページのテキストを結合
                full_text = '\n'.join(pages_text)
                
                # 書類種別判定
                self.log_text.insert(tk.END, "  書類種別判定中...\n")
                self.root.update()
                
                doc_type = self.processor.detect_document_type(full_text)
                self.log_text.insert(tk.END, f"  判定結果: {doc_type}\n")
                
                # 自治体情報抽出（自動）
                auto_pref, auto_city = self.processor.extract_prefecture_city(full_text)
                if auto_pref:
                    self.log_text.insert(tk.END, f"  自動抽出: {auto_pref} {auto_city or ''}\n")
                
                # 年月抽出（自動）
                auto_year_month = self.processor.extract_year_month(full_text)
                if auto_year_month:
                    self.log_text.insert(tk.END, f"  年月抽出: {auto_year_month}\n")
                
                # 複数自治体対応の書類（タプル形式に対応）
                doc_type_str = doc_type[0] if isinstance(doc_type, tuple) else doc_type
                
                # デバッグログ
                self.log_text.insert(tk.END, f"  🔍 書類種別チェック: {doc_type_str}\n", 'info')
                self.log_text.insert(tk.END, f"  🔍 手動入力自治体数: {len(active_municipalities)}\n", 'info')
                
                if doc_type_str in ['1001_都道府県申告', '2001_市町村申告', '2003_受信通知']:
                    self.log_text.insert(tk.END, f"  ✅ 複数自治体対応書類として処理開始\n", 'success')
                    if active_municipalities:
                        # 手動入力を最優先 - 書類の順番に自治体を割り当て
                        # 現在の書類インデックス（0から開始）
                        current_doc_index = i
                        
                        # 手動入力のマッチング処理
                        matched = False
                        
                        # 都道府県申告書の場合：入力された全ての都道府県を順番に処理
                        if doc_type_str == '1001_都道府県申告':
                            if prefecture_doc_count < len(active_municipalities):
                                municipality = active_municipalities[prefecture_doc_count]
                                
                                if municipality['prefecture']:  # 手動入力がある場合
                                    use_pref = municipality['prefecture']
                                    use_city = ''  # 都道府県申告書では市町村は使用しない
                                    
                                    # 手動年月を優先
                                    use_year_month = self.year_month_var.get() or auto_year_month
                                    
                                    self.log_text.insert(tk.END, f"  🏛️ 都道府県申告書 - 手動入力適用: ", 'success')
                                    self.log_text.insert(tk.END, f"都道府県書類{prefecture_doc_count + 1} → 自治体{prefecture_doc_count + 1}「{use_pref}」\n", 'success')
                                    
                                    # 補助的な確認：自動抽出結果との比較
                                    if auto_pref:
                                        if auto_pref == use_pref:
                                            self.log_text.insert(tk.END, f"    ✅ 自動抽出と一致: {auto_pref}\n", 'success')
                                        else:
                                            self.log_text.insert(tk.END, f"    ⚠️ 自動抽出と相違: 自動「{auto_pref}」vs 手動「{use_pref}」\n", 'warning')
                                    else:
                                        self.log_text.insert(tk.END, f"    ℹ️ 自動抽出なし（手動入力を使用）\n", 'info')
                                    
                                    new_filename = self.generate_filename(
                                        doc_type_str, 
                                        use_pref, 
                                        use_city, 
                                        prefecture_doc_count, 
                                        use_year_month
                                    )
                                    
                                    result = {
                                        'original': file_name,
                                        'new': new_filename,
                                        'type': '都道府県申告',
                                        'prefecture': use_pref,
                                        'city': '(なし)',
                                        'status': '成功',
                                        'file_path': file_path
                                    }
                                    self.results.append(result)
                                    self.log_text.insert(tk.END, f"    📝 生成: ", 'info')
                                    self.log_text.insert(tk.END, f"{new_filename}\n", 'success')
                                    matched = True
                                    prefecture_doc_count += 1  # カウンターをインクリメント
                        
                        # 市町村申告書の場合：市町村が入力されているもののみ処理
                        elif doc_type_str == '2001_市町村申告':
                            # 市町村が入力されている自治体リストを作成
                            municipalities_with_city = []
                            for municipality in active_municipalities:
                                if municipality['prefecture'] and municipality['city']:
                                    municipalities_with_city.append(municipality)
                            
                            # 現在の市町村申告書に対応する自治体を選択
                            if municipality_doc_count < len(municipalities_with_city):
                                municipality = municipalities_with_city[municipality_doc_count]
                                use_pref = municipality['prefecture']
                                use_city = municipality['city']
                                
                                # 手動年月を優先
                                use_year_month = self.year_month_var.get() or auto_year_month
                                
                                self.log_text.insert(tk.END, f"  🏛️ 市町村申告書 - 手動入力適用: ", 'success')
                                self.log_text.insert(tk.END, f"市町村書類{municipality_doc_count + 1} → 自治体「{use_pref}{use_city}」\n", 'success')
                                
                                # 補助的な確認：自動抽出結果との比較
                                if auto_pref:
                                    if auto_pref == use_pref:
                                        self.log_text.insert(tk.END, f"    ✅ 自動抽出と一致: {auto_pref}\n", 'success')
                                    else:
                                        self.log_text.insert(tk.END, f"    ⚠️ 自動抽出と相違: 自動「{auto_pref}」vs 手動「{use_pref}」\n", 'warning')
                                else:
                                    self.log_text.insert(tk.END, f"    ℹ️ 自動抽出なし（手動入力を使用）\n", 'info')
                                
                                new_filename = self.generate_filename(
                                    doc_type_str, 
                                    use_pref, 
                                    use_city, 
                                    municipality_doc_count,  # 市町村のカウンターを使用
                                    use_year_month
                                )
                                
                                result = {
                                    'original': file_name,
                                    'new': new_filename,
                                    'type': '市町村申告',
                                    'prefecture': use_pref,
                                    'city': use_city,
                                    'status': '成功',
                                    'file_path': file_path
                                }
                                self.results.append(result)
                                self.log_text.insert(tk.END, f"    📝 生成: ", 'info')
                                self.log_text.insert(tk.END, f"{new_filename}\n", 'success')
                                matched = True
                                municipality_doc_count += 1  # カウンターをインクリメント
                        
                        # マッチしなかった場合は補完的に自動抽出を使用
                        if not matched:
                            self.log_text.insert(tk.END, f"  📋 補完的処理: 手動入力なし/不足 → 自動抽出使用\n", 'warning')
                            use_year_month = self.year_month_var.get() or auto_year_month
                            new_filename = self.generate_filename(doc_type_str, auto_pref, auto_city, 0, use_year_month)
                            result = {
                                'original': file_name,
                                'new': new_filename,
                                'type': doc_type_str.split('_')[1] if '_' in doc_type_str else str(doc_type_str),
                                'prefecture': auto_pref or '(自動検出失敗)',
                                'city': auto_city or '(なし)',
                                'status': '要確認',
                                'file_path': file_path
                            }
                            self.results.append(result)
                            self.log_text.insert(tk.END, f"    📝 生成: ", 'info')
                            self.log_text.insert(tk.END, f"{new_filename}\n", 'warning')
                    else:
                        self.log_text.insert(tk.END, f"  📋 手動入力なし: 自動抽出のみで処理\n", 'info')
                        use_year_month = self.year_month_var.get() or auto_year_month
                        new_filename = self.generate_filename(doc_type_str, auto_pref, auto_city, 0, use_year_month)
                        result = {
                            'original': file_name,
                            'new': new_filename,
                            'type': doc_type_str.split('_')[1] if '_' in doc_type_str else str(doc_type_str),
                            'prefecture': auto_pref or '(自動検出失敗)',
                            'city': auto_city or '(なし)',
                            'status': '要確認' if not auto_pref else '成功',
                            'file_path': file_path
                        }
                        self.results.append(result)
                        self.log_text.insert(tk.END, f"    📝 生成: ", 'info')
                        self.log_text.insert(tk.END, f"{new_filename}\n", 'success')
                else:
                    self.log_text.insert(tk.END, f"  ⚠️ 非対応書類種別: 自動抽出で処理\n", 'warning')
                    # 自動抽出結果を使用（手動年月を優先）
                    use_year_month = self.year_month_var.get() or auto_year_month
                    new_filename = self.generate_filename(doc_type_str, auto_pref, auto_city, 0, use_year_month)
                    result = {
                        'original': file_name,
                        'new': new_filename,
                        'type': doc_type_str.split('_')[1] if '_' in doc_type_str else str(doc_type_str),
                        'prefecture': auto_pref or '(自動検出失敗)',
                        'city': auto_city or '(なし)',
                        'status': '要確認' if not auto_pref else '成功',
                        'file_path': file_path
                    }
                    self.results.append(result)
                    self.log_text.insert(tk.END, f"    📝 生成: ", 'info')
                    self.log_text.insert(tk.END, f"{new_filename}\n", 'success')
                
                self.root.update()
        
        except Exception as e:
            error_msg = f"処理エラー: {str(e)}"
            self.log_text.insert(tk.END, f"\n{error_msg}\n")
            logging.error(error_msg)
            messagebox.showerror("エラー", error_msg)
        
        finally:
            # UI状態復元
            self.progress.stop()
            self.process_btn.config(state='normal')
            
            # 結果表示
            success_count = sum(1 for r in self.results if r['status'] == '成功')
            warning_count = sum(1 for r in self.results if r['status'] == '要確認')
            error_count = sum(1 for r in self.results if r['status'] == 'エラー')
            
            for result in self.results:
                # ステータスに応じた色分け
                tags = ()
                if result['status'] == '成功':
                    tags = ('success',)
                elif result['status'] == 'エラー':
                    tags = ('error',)
                else:
                    tags = ('warning',)
                
                item = self.results_tree.insert('', 'end', values=(
                    result['original'],
                    result['new'],
                    result['type'],
                    result['prefecture'],
                    result['city'],
                    result['status']
                ), tags=tags)
            
            # タグの色設定
            self.results_tree.tag_configure('success', background='#d4edda')
            self.results_tree.tag_configure('warning', background='#fff3cd')
            self.results_tree.tag_configure('error', background='#f8d7da')
            
            self.log_text.insert(tk.END, f"\n", 'header')
            self.log_text.insert(tk.END, f"{'🎉'*20} 処理完了 {'🎉'*20}\n", 'header')
            self.log_text.insert(tk.END, f"📅 完了時刻: ", 'info')
            self.log_text.insert(tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", 'success')
            self.log_text.insert(tk.END, f"📈 処理結果: ", 'info')
            self.log_text.insert(tk.END, f"✅成功: {success_count}件 ", 'success')
            self.log_text.insert(tk.END, f"⚠️要確認: {warning_count}件 ", 'warning')
            self.log_text.insert(tk.END, f"❌エラー: {error_count}件\n", 'error')
            self.log_text.insert(tk.END, f"{'='*60}\n", 'header')
            self.log_text.see(tk.END)
            
            self.status_var.set(f"処理完了 - 成功: {success_count}, 要確認: {warning_count}, エラー: {error_count}")
            
            # ボタン状態更新
            if self.results:
                self.save_btn.config(state='normal')
                self.rename_btn.config(state='normal')
            
            messagebox.showinfo("完了", 
                              f"処理が完了しました\n\n"
                              f"成功: {success_count}件\n"
                              f"要確認: {warning_count}件\n"
                              f"エラー: {error_count}件")
    
    def save_results(self):
        """結果をCSVで保存"""
        if not self.results:
            messagebox.showwarning("警告", "保存する結果がありません")
            return
        
        filename = filedialog.asksaveasfilename(
            title="結果を保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialname=f"tax_document_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ['original', 'new', 'type', 'prefecture', 'city', 'status']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for result in self.results:
                        writer.writerow({k: v for k, v in result.items() if k in fieldnames})
                
                self.log_text.insert(tk.END, f"結果をCSVファイルに保存しました: {filename}\n")
                messagebox.showinfo("完了", f"結果を保存しました\n{filename}")
            except Exception as e:
                error_msg = f"保存に失敗しました: {str(e)}"
                self.log_text.insert(tk.END, f"{error_msg}\n")
                messagebox.showerror("エラー", error_msg)
    
    def execute_rename(self):
        """実際のファイルリネーム実行"""
        if not self.results:
            messagebox.showwarning("警告", "リネームする結果がありません")
            return
        
        # エラー状態の結果を除外
        valid_results = [r for r in self.results if r['status'] != 'エラー']
        if not valid_results:
            messagebox.showwarning("警告", "リネーム可能な結果がありません")
            return
        
        output_dir = filedialog.askdirectory(title="出力フォルダを選択")
        if not output_dir:
            return
        
        confirm_msg = (f"{len(valid_results)}件のファイルを\n"
                      f"{output_dir}\n"
                      f"にリネームして保存しますか？\n\n"
                      f"※ 元ファイルは変更されません（コピー保存）")
        
        if not messagebox.askyesno("確認", confirm_msg):
            return
        
        self.status_var.set("ファイルリネーム実行中...")
        self.progress.start()
        self.rename_btn.config(state='disabled')
        
        try:
            success_count = 0
            error_count = 0
            
            for i, result in enumerate(valid_results):
                try:
                    source_path = result['file_path']
                    new_path = os.path.join(output_dir, result['new'])
                    
                    # ファイル名重複チェック
                    counter = 1
                    base_path = new_path
                    while os.path.exists(new_path):
                        name, ext = os.path.splitext(base_path)
                        new_path = f"{name}_{counter:02d}{ext}"
                        counter += 1
                    
                    # ファイルコピー
                    shutil.copy2(source_path, new_path)
                    success_count += 1
                    
                    final_name = os.path.basename(new_path)
                    self.log_text.insert(tk.END, f"[{i+1}/{len(valid_results)}] {result['original']} -> {final_name}\n")
                    self.status_var.set(f"リネーム中: {i+1}/{len(valid_results)}")
                    self.root.update()
                    
                except Exception as file_error:
                    error_count += 1
                    error_msg = f"ファイルコピーエラー ({result['original']}): {str(file_error)}"
                    self.log_text.insert(tk.END, f"エラー: {error_msg}\n")
                    logging.error(error_msg)
            
            self.log_text.insert(tk.END, f"\nリネーム完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_text.insert(tk.END, f"成功: {success_count}件, エラー: {error_count}件\n")
            self.log_text.see(tk.END)
            
            result_msg = f"ファイルリネームが完了しました\n\n成功: {success_count}件\nエラー: {error_count}件"
            if error_count > 0:
                result_msg += f"\n\nエラーの詳細はログを確認してください"
            
            messagebox.showinfo("完了", result_msg)
            
        except Exception as e:
            error_msg = f"リネーム処理でエラーが発生しました: {str(e)}"
            self.log_text.insert(tk.END, f"\n{error_msg}\n")
            messagebox.showerror("エラー", error_msg)
        
        finally:
            self.progress.stop()
            self.rename_btn.config(state='normal')
            self.status_var.set("リネーム完了")
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
税務書類リネームシステム v2.0 使用方法

【基本的な使い方】
1. PDFファイルを選択（個別選択またはフォルダ一括選択）
2. 必要に応じて自治体情報を入力
3. 必要に応じて年月を入力（YYMM形式）
4. 「処理実行」ボタンをクリック
5. 結果を確認後、「ファイルリネーム実行」で実際のリネームを実行

【対応書類】
• 地方税関連: 納付情報、受信通知、申告書
• 国税関連: 法人税・消費税の受信通知、納付情報
• 申告書類: 納付税額一覧表、各種申告書、添付資料
• 会計書類: 決算書、総勘定元帳、補助元帳、仕訳帳等

【自動機能】
• OCR による日本語テキスト認識
• 書類種別の自動判定
• 都道府県・市町村の自動抽出
• 年月の自動抽出（令和年対応）

【注意事項】
• Tesseract OCRがインストールされている必要があります
• 元ファイルは変更されません（コピー保存）
• ファイル名重複時は自動的に連番が付加されます
• 処理ログは自動的に保存されます

【サポート】
問題が発生した場合は、処理ログを確認してください。
ログファイルは以下に保存されます：
{os.path.join(os.path.expanduser("~"), "TaxDocumentRenamer", "tax_document_renamer.log")}
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("ヘルプ")
        help_window.geometry("600x500")
        help_window.resizable(True, True)
        
        # ヘルプテキスト表示
        help_frame = ttk.Frame(help_window, padding="10")
        help_frame.pack(fill=tk.BOTH, expand=True)
        
        help_text_widget = scrolledtext.ScrolledText(help_frame, wrap=tk.WORD)
        help_text_widget.pack(fill=tk.BOTH, expand=True)
        help_text_widget.insert(tk.END, help_text)
        help_text_widget.config(state=tk.DISABLED)
        
        # 閉じるボタン
        ttk.Button(help_frame, text="閉じる", 
                  command=help_window.destroy).pack(pady=(10, 0))
    
    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    try:
        app = TaxDocumentGUI()
        app.run()
    except Exception as e:
        logging.error(f"アプリケーション開始エラー: {str(e)}")
        try:
            messagebox.showerror("エラー", f"アプリケーションの開始に失敗しました:\n{str(e)}")
        except:
            print(f"Critical Error: {str(e)}")

if __name__ == "__main__":
    main()

# =============================================================================
# requirements.txt ファイル内容:
# =============================================================================
"""
PyPDF2==3.0.1
PyMuPDF==1.23.8
pytesseract==0.3.10
Pillow==10.1.0
"""

# =============================================================================
# build_exe.py - exe化スクリプト
# =============================================================================
"""
import os
import subprocess
import sys

def build_exe():
    print("税務書類リネームシステム exe化開始...")
    
    # PyInstallerコマンド構築
    cmd = [
        "pyinstaller",
        "--onefile",                    # 単一実行ファイル
        "--windowed",                   # コンソールウィンドウを非表示
        "--name=TaxDocumentRenamer",    # 実行ファイル名
        "--icon=icon.ico",              # アイコンファイル（オプション）
        "--add-data=icon.ico;.",        # アイコンを含める（オプション）
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--collect-all=pytesseract",
        "tax_document_renamer.py"
    ]
    
    try:
        # PyInstaller実行
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("exe化完了!")
        print("dist/TaxDocumentRenamer.exe が生成されました")
        
        # Tesseractのインストール案内
        print("\n" + "="*50)
        print("重要: Tesseract OCRのインストールが必要です")
        print("https://github.com/UB-Mannheim/tesseract/wiki")
        print("からTesseractをダウンロードしてインストールしてください")
        print("="*50)
        
    except subprocess.CalledProcessError as e:
        print(f"exe化失敗: {e}")
        print(f"エラー出力: {e.stderr}")
    except FileNotFoundError:
        print("PyInstallerがインストールされていません")
        print("pip install pyinstaller を実行してください")

if __name__ == "__main__":
    build_exe()
"""

# =============================================================================
# setup.bat - Windows用セットアップスクリプト
# =============================================================================
"""
@echo off
echo 税務書類リネームシステム セットアップ
echo.

echo 1. 必要なライブラリをインストール中...
pip install PyPDF2 PyMuPDF pytesseract Pillow pyinstaller

echo.
echo 2. exe化を実行中...
python build_exe.py

echo.
echo セットアップ完了
echo dist/TaxDocumentRenamer.exe を実行してください
pause
"""