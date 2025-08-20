#!/usr/bin/env python3
"""
税務書類リネームシステム v4.1 修正版
分割結果表示改善・判定ロジック修正
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
import tempfile

# PyInstallerでの実行時のパス取得
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# 必要なライブラリのインポート（エラーハンドリング付き）
try:
    import PyPDF2
    import fitz  # PyMuPDF
    from PIL import Image, ImageTk, ImageEnhance, ImageFilter
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

class KeywordPriorityEngine:
    """キーワード判定優先度エンジン"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.setup_priority_rules()
        
    def setup_priority_rules(self):
        """優先度ルール設定"""
        
        # 高優先度：具体的な書類名（最優先）
        self.high_priority_patterns = {
            '納付税額一覧表': '0000_納付税額一覧表_{yymm}.pdf',
            '納税一覧': '0000_納付税額一覧表_{yymm}.pdf',  # 修正：納税一覧も0000番号
            '総勘定元帳': '5002_総勘定元帳_{yymm}.pdf',
            '仕訳帳': '5005_仕訳帳_{yymm}.pdf',
            '補助元帳': '5003_補助元帳_{yymm}.pdf',
            '固定資産台帳': '6001_固定資産台帳_{yymm}.pdf',
            '一括償却資産明細表': '6002_一括償却資産明細表_{yymm}.pdf',
            '一括償却資産明細': '6002_一括償却資産明細表_{yymm}.pdf',  # 修正：省略形対応
            '少額減価償却資産明細表': '6003_少額減価償却資産明細表_{yymm}.pdf',
            '少額減価償却': '6003_少額減価償却資産明細表_{yymm}.pdf',  # 修正：省略形対応
            '少額': '6003_少額減価償却資産明細表_{yymm}.pdf',  # 修正：更に省略形対応
            
            # 税区分集計表の分離（最優先）
            '勘定科目別税区分集計表': '7001_勘定科目別税区分集計表_{yymm}.pdf',
            '税区分集計表': '7002_税区分集計表_{yymm}.pdf',
        }
        
        # 決算書類のOR条件（複数キーワードのいずれかで判定）
        self.financial_statement_keywords = [
            '決算報告書', '貸借対照表', '損益計算書', '決算書'
        ]
        self.financial_statement_pattern = '5001_決算書_{yymm}.pdf'
        
        # 中優先度：税目別キーワード
        self.medium_priority_patterns = {
            '内国法人の確定申告': '0001_法人税及び地方法人税申告書_{yymm}.pdf',
            '法人税申告書': '0001_法人税及び地方法人税申告書_{yymm}.pdf',
            '消費税申告書': '3001_消費税申告書_{yymm}.pdf',
            '消費税及び地方消費税申告': '3001_消費税申告書_{yymm}.pdf',
            '都道府県民税': '1001_都道府県申告_{yymm}.pdf',
            '法人市民税': '2001_市町村申告_{yymm}.pdf',
            '納付情報': '2004_納付情報_{yymm}.pdf',
        }
        
        # 低優先度：AND条件必須
        self.and_conditions = {
            ('添付書類送付書', '内国法人の確定申告'): '0002_添付資料_法人税_{yymm}.pdf',
            ('添付書類送付書', '消費税及び地方消費税'): '3002_添付資料_消費税_{yymm}.pdf',
            ('添付資料', '法人税'): '0002_添付資料_法人税_{yymm}.pdf',
            ('添付資料', '消費税'): '3002_添付資料_消費税_{yymm}.pdf',
        }
        
        # CSV専用パターン
        self.csv_patterns = {
            '仕訳帳': '5006_仕訳データ_{yymm}.csv',
            '取引No': '5006_仕訳データ_{yymm}.csv',  # A1セル判定用
            '総勘定元帳': '5007_総勘定元帳_{yymm}.csv',
            '補助元帳': '5008_補助元帳_{yymm}.csv',
        }
        
    def determine_document_type(self, text: str, filename: str, file_ext: str) -> Tuple[str, str]:
        """優先度に基づく文書種別判定"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        self.debug_logger.log('DEBUG', f"判定開始 - ファイル: {filename}, 拡張子: {file_ext}")
        self.debug_logger.log('DEBUG', f"抽出テキスト: {text[:200]}...")
        
        # CSV専用判定
        if file_ext == '.csv':
            return self._determine_csv_type(text, filename)
        
        # 高優先度：具体的な書類名（ファイル名も含めて判定）
        for keyword, pattern in self.high_priority_patterns.items():
            if keyword in text or keyword in filename_lower:
                self.debug_logger.log('INFO', f"高優先度判定: '{keyword}' → {pattern}")
                return keyword, pattern
                
        # 決算書類のOR条件判定
        for keyword in self.financial_statement_keywords:
            if keyword in text or keyword in filename_lower:
                self.debug_logger.log('INFO', f"決算書類判定: '{keyword}' → {self.financial_statement_pattern}")
                return '決算書', self.financial_statement_pattern
        
        # 中優先度：税目別キーワード
        for keyword, pattern in self.medium_priority_patterns.items():
            if keyword in text or keyword in filename_lower:
                self.debug_logger.log('INFO', f"中優先度判定: '{keyword}' → {pattern}")
                return keyword, pattern
        
        # 低優先度：AND条件
        for (keyword1, keyword2), pattern in self.and_conditions.items():
            if (keyword1 in text or keyword1 in filename_lower) and (keyword2 in text or keyword2 in filename_lower):
                self.debug_logger.log('INFO', f"AND条件判定: '{keyword1}' AND '{keyword2}' → {pattern}")
                return f"{keyword1}+{keyword2}", pattern
                
        self.debug_logger.log('WARNING', "文書種別判定不可")
        return '不明', ''
        
    def _determine_csv_type(self, text: str, filename: str) -> Tuple[str, str]:
        """CSV専用判定"""
        for keyword, pattern in self.csv_patterns.items():
            if keyword in text or keyword in filename.lower():
                self.debug_logger.log('INFO', f"CSV判定: '{keyword}' → {pattern}")
                return keyword, pattern
        return '不明', ''

class PDFSplitter:
    """PDF分割機能クラス"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        
    def detect_split_points(self, pdf_path: str) -> List[int]:
        """分割ポイント検出"""
        split_points = []
        
        try:
            doc = fitz.open(pdf_path)
            self.debug_logger.log('INFO', f"PDF分割解析開始: {len(doc)}ページ")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # 分割トリガー検出
                if self._is_split_trigger(text, page_num):
                    split_points.append(page_num)
                    self.debug_logger.log('DEBUG', f"分割ポイント検出: ページ{page_num + 1}")
                    
            doc.close()
            
            # 最初のページが分割ポイントでない場合は追加
            if split_points and split_points[0] != 0:
                split_points.insert(0, 0)
                
            self.debug_logger.log('INFO', f"分割ポイント: {[p+1 for p in split_points]}")
            return split_points
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"分割ポイント検出エラー: {e}")
            return []
            
    def _is_split_trigger(self, text: str, page_num: int) -> bool:
        """分割トリガー判定"""
        
        # 連番パターン検出
        number_patterns = [
            r'100[3|4]', r'101[3]', r'102[3]', r'103[3]',  # 国税系列
            r'200[3|4]', r'201[3]', r'202[3]'  # 地方税系列
        ]
        
        for pattern in number_patterns:
            if re.search(pattern, text):
                return True
                
        # 書類種別の変化点検出
        transition_keywords = [
            '内国法人の確定申告',
            '消費税及び地方消費税',
            '都道府県民税',
            '法人市民税'
        ]
        
        for keyword in transition_keywords:
            if keyword in text and page_num > 0:  # 最初のページは除く
                return True
                
        return False
        
    def split_pdf(self, pdf_path: str, split_points: List[int], output_dir: str) -> List[str]:
        """PDF分割実行"""
        split_files = []
        
        if len(split_points) <= 1:
            return [pdf_path]  # 分割不要
            
        try:
            doc = fitz.open(pdf_path)
            base_name = Path(pdf_path).stem
            
            for i in range(len(split_points)):
                start_page = split_points[i]
                end_page = split_points[i + 1] if i + 1 < len(split_points) else len(doc)
                
                # 新しいPDF作成
                new_doc = fitz.open()
                for page_num in range(start_page, end_page):
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                # 一時ファイルとして保存
                temp_path = os.path.join(output_dir, f"{base_name}_split_{i+1}.pdf")
                new_doc.save(temp_path)
                new_doc.close()
                
                split_files.append(temp_path)
                self.debug_logger.log('INFO', f"分割ファイル作成: {temp_path} (ページ{start_page+1}-{end_page})")
                
            doc.close()
            return split_files
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"PDF分割エラー: {e}")
            return [pdf_path]

class CSVProcessor:
    """CSV処理改善クラス"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        
    def read_csv_with_encoding(self, file_path: str) -> Tuple[Optional[str], Optional[object]]:
        """エンコーディング自動判定でCSV読み込み"""
        encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp', 'utf-8-sig']
        
        for encoding in encodings:
            try:
                if PANDAS_AVAILABLE:
                    df = pd.read_csv(file_path, encoding=encoding, nrows=10)
                    content = ' '.join(df.columns.tolist())
                    if df.shape[0] > 0:
                        content += ' ' + ' '.join(str(df.iloc[0, col]) for col in range(min(5, df.shape[1])))
                    self.debug_logger.log('INFO', f"CSV読み込み成功 - エンコーディング: {encoding}")
                    return content, df
                else:
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.reader(f)
                        headers = next(reader, [])
                        first_row = next(reader, [])
                        content = ' '.join(headers + first_row[:5])
                    self.debug_logger.log('INFO', f"CSV読み込み成功 - エンコーディング: {encoding}")
                    return content, None
                    
            except (UnicodeDecodeError, pd.errors.EmptyDataError, csv.Error):
                continue
            except Exception as e:
                self.debug_logger.log('WARNING', f"CSV読み込みエラー ({encoding}): {e}")
                continue
                
        self.debug_logger.log('ERROR', "サポートされていないエンコーディングです")
        return None, None

class OCRProcessor:
    """OCR処理改善クラス"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.setup_tesseract()
        
    def setup_tesseract(self):
        """Tesseract最適化設定"""
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
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """改善されたPDFテキスト抽出"""
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
                        # 高解像度で画像取得
                        mat = fitz.Matrix(2.0, 2.0)  # 2倍解像度
                        pix = page.get_pixmap(matrix=mat)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # 画像前処理
                        processed_img = self._preprocess_image(img)
                        
                        # 最適化されたOCR設定
                        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzぁ-んァ-ヶ一-龯'
                        ocr_text = pytesseract.image_to_string(processed_img, lang='jpn', config=custom_config)
                        text += ocr_text + "\n"
                        self.debug_logger.log('DEBUG', f"OCR抽出テキスト: {ocr_text[:100]}...")
                    except Exception as e:
                        self.debug_logger.log('WARNING', f"OCR処理エラー: {e}")
                        
            doc.close()
            return text
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"PDF読み込みエラー: {e}")
            return ""
            
    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """画像前処理による精度向上"""
        try:
            # グレースケール変換
            img = img.convert('L')
            
            # コントラスト強化
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # ノイズ除去
            img = img.filter(ImageFilter.MedianFilter())
            
            # 二値化
            threshold = 128
            img = img.point(lambda x: 0 if x < threshold else 255, '1')
            
            return img
        except Exception as e:
            self.debug_logger.log('WARNING', f"画像前処理エラー: {e}")
            return img

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
        self.priority_engine = KeywordPriorityEngine(debug_logger)
        self.pdf_splitter = PDFSplitter(debug_logger)
        self.csv_processor = CSVProcessor(debug_logger)
        self.ocr_processor = OCRProcessor(debug_logger)
        self.yymm_processor = YYMMProcessor(debug_logger)
        
    def process_file(self, file_path: str, user_yymm: str = "") -> List[Dict]:
        """ファイル処理（分割対応）"""
        results = []
        
        try:
            self.debug_logger.log('INFO', f"=== ファイル処理開始: {os.path.basename(file_path)} ===")
            
            # ファイル拡張子判定
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # PDF分割処理
                split_points = self.pdf_splitter.detect_split_points(file_path)
                if len(split_points) > 1:
                    # 分割実行
                    temp_dir = tempfile.mkdtemp()
                    split_files = self.pdf_splitter.split_pdf(file_path, split_points, temp_dir)
                    
                    # 各分割ファイルを処理
                    for i, split_file in enumerate(split_files):
                        result = self.process_pdf_file(split_file, user_yymm)
                        result['original_file'] = file_path  # 元ファイルを記録
                        result['split_info'] = f"分割{i+1}/{len(split_files)}"  # 分割情報追加
                        result['split_source'] = os.path.basename(file_path)  # 分割元ファイル名
                        result['is_split'] = True
                        results.append(result)
                        
                    self.debug_logger.log('INFO', f"分割処理完了: {len(split_files)}個のファイルに分割")
                else:
                    # 分割不要の場合
                    result = self.process_pdf_file(file_path, user_yymm)
                    result['split_info'] = "分割なし"
                    result['split_source'] = ""
                    result['is_split'] = False
                    results.append(result)
                    
            elif file_ext == '.csv':
                result = self.process_csv_file(file_path, user_yymm)
                result['split_info'] = "分割なし"
                result['split_source'] = ""
                result['is_split'] = False
                results.append(result)
            else:
                result = {
                    'original_file': file_path,
                    'success': False,
                    'new_name': '',
                    'error': f"未対応のファイル形式: {file_ext}",
                    'document_type': '',
                    'yymm': '',
                    'processing_details': [],
                    'split_info': "分割なし",
                    'split_source': "",
                    'is_split': False
                }
                results.append(result)
                
        except Exception as e:
            result = {
                'original_file': file_path,
                'success': False,
                'new_name': '',
                'error': f"処理エラー: {str(e)}",
                'document_type': '',
                'yymm': '',
                'processing_details': [],
                'split_info': "分割なし",
                'split_source': "",
                'is_split': False
            }
            results.append(result)
            
        return results
        
    def process_pdf_file(self, file_path: str, user_yymm: str) -> Dict:
        """PDF処理"""
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
            # OCRテキスト抽出
            ocr_text = self.ocr_processor.extract_text_from_pdf(file_path)
            result['processing_details'].append(f"テキスト抽出: {len(ocr_text)}文字")
            
            # 文書種別判定（優先度エンジン使用）
            doc_type, pattern = self.priority_engine.determine_document_type(
                ocr_text, os.path.basename(file_path), '.pdf'
            )
            result['document_type'] = doc_type
            result['processing_details'].append(f"文書種別: {doc_type}")
            
            # YYMM判定
            yymm = self.yymm_processor.determine_yymm(user_yymm, os.path.basename(file_path), ocr_text)
            result['yymm'] = yymm
            
            # 新ファイル名生成
            if pattern:
                new_name = pattern.format(yymm=yymm)
                result['new_name'] = new_name
                result['success'] = True
            else:
                result['error'] = f"未対応の文書種別: {doc_type}"
                
        except Exception as e:
            result['error'] = f"PDF処理エラー: {str(e)}"
            
        return result
        
    def process_csv_file(self, file_path: str, user_yymm: str) -> Dict:
        """CSV処理"""
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
            # CSV読み込み（エンコーディング自動判定）
            csv_content, df = self.csv_processor.read_csv_with_encoding(file_path)
            
            if csv_content is None:
                result['error'] = "CSV読み込み失敗"
                return result
                
            result['processing_details'].append("CSV読み込み成功")
            
            # 文書種別判定（優先度エンジン使用）
            doc_type, pattern = self.priority_engine.determine_document_type(
                csv_content, os.path.basename(file_path), '.csv'
            )
            result['document_type'] = doc_type
            
            # YYMM判定
            yymm = self.yymm_processor.determine_yymm(user_yymm, os.path.basename(file_path), csv_content)
            result['yymm'] = yymm
            
            # 新ファイル名生成
            if pattern:
                new_name = pattern.format(yymm=yymm)
                result['new_name'] = new_name
                result['success'] = True
            else:
                result['error'] = f"CSV未対応の文書種別: {doc_type}"
                
        except Exception as e:
            result['error'] = f"CSV処理エラー: {str(e)}"
            
        return result

class PrefectureValidator:
    """都道府県入力制御クラス"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        
    def validate_tokyo_input(self, prefecture_selections: List[str]) -> Tuple[bool, str]:
        """東京都のセット1限定入力制御"""
        tokyo_positions = []
        
        for i, prefecture in enumerate(prefecture_selections):
            if prefecture == "東京都":
                tokyo_positions.append(i + 1)  # 1ベースで記録
                
        if len(tokyo_positions) == 0:
            return True, ""  # 東京都未選択は問題なし
        elif len(tokyo_positions) == 1 and tokyo_positions[0] == 1:
            return True, ""  # セット1のみは問題なし
        elif len(tokyo_positions) == 1 and tokyo_positions[0] != 1:
            return False, f"東京都はセット1に入力してください（現在：セット{tokyo_positions[0]}）"
        else:
            return False, f"東京都が複数のセットに入力されています：セット{', '.join(map(str, tokyo_positions))}"

class TaxDocumentRenamerGUI:
    """メインGUIクラス"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v4.1 修正版")
        self.root.geometry("1100x800")
        
        self.debug_logger = None
        self.processor = None
        self.prefecture_validator = None
        self.files_to_process = []
        self.result_data = []  # 結果表示用
        
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
            
            # タブ3: 結果一覧
            self.result_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.result_tab, text="結果一覧")
            self.setup_result_tab()
            
            # タブ4: デバッグログ
            self.debug_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.debug_tab, text="デバッグログ")
            self.setup_debug_tab()
            
        except Exception as e:
            messagebox.showerror("UI設定エラー", f"ユーザーインターフェースの設定に失敗しました:\n{e}")
        
    def setup_file_tab(self):
        """ファイル選択タブ"""
        try:
            # YYMM入力
            yymm_frame = ttk.Frame(self.file_tab)
            yymm_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Label(yymm_frame, text="年月(YYMM):").pack(side='left')
            self.yymm_var = tk.StringVar()
            yymm_entry = ttk.Entry(yymm_frame, textvariable=self.yymm_var, width=10)
            yymm_entry.pack(side='left', padx=(5, 0))
            
            # 都道府県・市町村入力エリア
            prefecture_frame = ttk.LabelFrame(self.file_tab, text="都道府県・市町村設定")
            prefecture_frame.pack(fill='x', padx=10, pady=10)
            
            self.setup_prefecture_inputs(prefecture_frame)
            
            # ファイル選択エリア
            drop_frame = tk.Frame(self.file_tab, bg='lightgray', relief='solid', bd=2, height=150)
            drop_frame.pack(fill='x', padx=10, pady=10)
            drop_frame.pack_propagate(False)
            
            drop_label = tk.Label(drop_frame, text="ファイルを選択してください\n（下のボタンでファイル選択）", 
                                 bg='lightgray', font=('Arial', 12))
            drop_label.pack(expand=True)
            
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
            
        except Exception as e:
            messagebox.showerror("ファイルタブエラー", f"ファイル選択タブの設定に失敗しました:\n{e}")
            
    def setup_prefecture_inputs(self, parent):
        """都道府県入力設定"""
        try:
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
            
            self.prefecture_vars = []
            self.city_vars = []
            
            # 5セット作成
            for i in range(5):
                set_frame = ttk.Frame(parent)
                set_frame.pack(fill='x', padx=5, pady=2)
                
                ttk.Label(set_frame, text=f"セット{i+1}:").pack(side='left')
                
                # 都道府県ドロップダウン
                prefecture_var = tk.StringVar()
                prefecture_combo = ttk.Combobox(set_frame, textvariable=prefecture_var, 
                                              values=[""] + self.prefectures, width=10, state='readonly')
                prefecture_combo.pack(side='left', padx=(5, 5))
                self.prefecture_vars.append(prefecture_var)
                
                # 市町村入力
                ttk.Label(set_frame, text="市町村:").pack(side='left')
                city_var = tk.StringVar()
                city_entry = ttk.Entry(set_frame, textvariable=city_var, width=15)
                city_entry.pack(side='left', padx=(5, 0))
                self.city_vars.append(city_var)
                
        except Exception as e:
            messagebox.showerror("都道府県設定エラー", f"都道府県設定に失敗しました:\n{e}")
        
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
            
            self.split_enable_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(options_frame, text="PDF自動分割を有効にする", variable=self.split_enable_var).pack(anchor='w')
            
        except Exception as e:
            messagebox.showerror("設定タブエラー", f"設定タブの設定に失敗しました:\n{e}")
            
    def setup_result_tab(self):
        """結果一覧タブ"""
        try:
            # 結果表示エリア
            result_frame = ttk.Frame(self.result_tab)
            result_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Treeview作成（分割情報カラム追加）
            columns = ('元ファイル', '分割情報', '新ファイル名', '文書種別', 'YYMM', 'ステータス')
            self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=15)
            
            # カラム設定
            column_widths = {'元ファイル': 200, '分割情報': 100, '新ファイル名': 200, '文書種別': 150, 'YYMM': 80, 'ステータス': 150}
            for col in columns:
                self.result_tree.heading(col, text=col)
                self.result_tree.column(col, width=column_widths.get(col, 150))
                
            # スクロールバー
            result_scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=self.result_tree.yview)
            self.result_tree.configure(yscrollcommand=result_scrollbar.set)
            
            self.result_tree.pack(side='left', fill='both', expand=True)
            result_scrollbar.pack(side='right', fill='y')
            
            # 結果制御ボタン
            result_btn_frame = ttk.Frame(self.result_tab)
            result_btn_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Button(result_btn_frame, text="結果クリア", command=self.clear_results).pack(side='left')
            ttk.Button(result_btn_frame, text="CSV出力", command=self.export_results).pack(side='left', padx=(10, 0))
            
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
            self.prefecture_validator = PrefectureValidator(self.debug_logger)
            
            self.debug_logger.log('INFO', "税務書類リネームシステム v4.1 修正版 起動")
            
        except Exception as e:
            messagebox.showerror("プロセッサー初期化エラー", f"システムの初期化に失敗しました:\n{e}")
            
    def validate_prefecture_settings(self) -> bool:
        """都道府県設定の検証"""
        try:
            prefecture_selections = [var.get() for var in self.prefecture_vars]
            is_valid, error_msg = self.prefecture_validator.validate_tokyo_input(prefecture_selections)
            
            if not is_valid:
                messagebox.showerror("東京都入力エラー", error_msg)
                return False
                
            return True
        except Exception as e:
            messagebox.showerror("都道府県検証エラー", f"都道府県設定の検証に失敗しました:\n{e}")
            return False
        
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
                
            # 都道府県設定検証
            if not self.validate_prefecture_settings():
                return
                
            user_yymm = self.yymm_var.get().strip()
            
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
            all_results = []
            
            for file_path in self.files_to_process:
                results = self.processor.process_file(file_path, user_yymm)
                
                for result in results:
                    all_results.append(result)
                    
                    if result['success']:
                        # ファイルリネーム実行
                        try:
                            source_path = Path(result['original_file'])  # 修正：分割ファイルのパスを使用
                            new_path = Path(self.output_dir_var.get()) / result['new_name']
                            
                            # 同名ファイル確認
                            if new_path.exists() and not self.overwrite_var.get():
                                self.debug_logger.log('WARNING', f"スキップ（同名ファイル存在）: {new_path.name}")
                                continue
                                
                            # バックアップ
                            if self.backup_var.get() and new_path.exists():
                                backup_path = new_path.with_suffix(f".bak{source_path.suffix}")
                                shutil.copy2(new_path, backup_path)
                                self.debug_logger.log('INFO', f"バックアップ作成: {backup_path.name}")
                                    
                            # コピー実行
                            shutil.copy2(source_path, new_path)
                            
                            self.debug_logger.log('INFO', f"処理成功: {source_path.name} → {new_path.name}")
                            success_count += 1
                            
                        except Exception as e:
                            self.debug_logger.log('ERROR', f"ファイル操作エラー: {e}")
                            error_count += 1
                    else:
                        self.debug_logger.log('ERROR', f"処理失敗: {os.path.basename(result.get('split_source', result['original_file']))} - {result['error']}")
                        error_count += 1
                        
            # 結果をGUIに反映
            self.root.after(0, lambda: self.update_result_display(all_results))
                    
            self.debug_logger.log('INFO', f"=== 処理完了 成功:{success_count} エラー:{error_count} ===")
            
            # 結果表示
            self.root.after(0, lambda: messagebox.showinfo(
                "処理完了", 
                f"処理が完了しました。\n成功: {success_count}件\nエラー: {error_count}件"
            ))
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"処理スレッドエラー: {e}")
            self.root.after(0, lambda: messagebox.showerror("処理エラー", f"処理中にエラーが発生しました:\n{e}"))
            
    def update_result_display(self, results):
        """結果表示更新"""
        try:
            self.result_data = results
            
            # Treeviewクリア
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
                
            # 結果追加
            for result in results:
                # 元ファイル名の表示を修正
                if result.get('is_split', False):
                    original_file = result.get('split_source', os.path.basename(result['original_file']))
                else:
                    original_file = os.path.basename(result['original_file'])
                    
                split_info = result.get('split_info', '分割なし')
                new_name = result.get('new_name', '未設定')
                doc_type = result.get('document_type', '不明')
                yymm = result.get('yymm', '不明')
                status = '成功' if result['success'] else f"エラー: {result['error']}"
                
                self.result_tree.insert('', 'end', values=(original_file, split_info, new_name, doc_type, yymm, status))
                
        except Exception as e:
            messagebox.showerror("結果表示エラー", f"結果の表示に失敗しました:\n{e}")
            
    def clear_results(self):
        """結果クリア"""
        try:
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            self.result_data = []
        except Exception as e:
            messagebox.showerror("結果クリアエラー", f"結果のクリアに失敗しました:\n{e}")
            
    def export_results(self):
        """結果CSV出力"""
        try:
            if not self.result_data:
                messagebox.showwarning("警告", "出力する結果がありません")
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSVファイル", "*.csv")],
                title="結果CSV保存"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['元ファイル', '分割情報', '新ファイル名', '文書種別', 'YYMM', 'ステータス', 'エラー詳細'])
                    
                    for result in self.result_data:
                        original_file = result.get('split_source', os.path.basename(result['original_file'])) if result.get('is_split', False) else os.path.basename(result['original_file'])
                        
                        writer.writerow([
                            original_file,
                            result.get('split_info', '分割なし'),
                            result.get('new_name', '未設定'),
                            result.get('document_type', '不明'),
                            result.get('yymm', '不明'),
                            '成功' if result['success'] else 'エラー',
                            result.get('error', '')
                        ])
                        
                messagebox.showinfo("出力完了", f"結果を保存しました: {file_path}")
                
        except Exception as e:
            messagebox.showerror("CSV出力エラー", f"結果の出力に失敗しました:\n{e}")
        
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