#!/usr/bin/env python3
"""
税務書類リネームシステム v4.4 機能拡張版
①複数ファイル選択 ②地域設定統合 ③出力先選択機能 実装
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

class SplitJudgmentEngine:
    """分割判定エンジン（v4.4継承）"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        
        # 分割対象キーワード（厳格な定義）
        self.SPLIT_TARGET_KEYWORDS = {
            'receipt_notice': [
                '申告受付完了通知', '受信通知', 
                '申告書等送信票', '送信結果',
                '申告受信通知書', '電子申告受付通知'
            ],
            'payment_info': [
                '納付情報発行結果', '納付区分番号通知',
                '納付税額通知書', '納付書', '納付情報',
                '国税納付', '地方税納付'
            ],
            'tax_authority_patterns': [
                '税務署長', '都道府県知事', '市町村長',
                '県税事務所長', '都税事務所長'
            ]
        }
        
        # 分割不要書類（単一処理対象）
        self.NO_SPLIT_PATTERNS = [
            # 申告書類
            '消費税及び地方消費税申告書', '消費税申告書',
            '法人税及び地方法人税申告書', '法人税申告書',
            '納付税額一覧表',
            '添付資料',
            
            # 都道府県・市町村申告書
            '法人都道府県民税', '法人事業税', '特別法人事業税',
            '法人市民税',
            
            # 会計書類（5000番台）
            '決算書', '貸借対照表', '損益計算書',
            '総勘定元帳', '補助元帳', '仕訳帳',
            '残高試算表', '仕訳データ',
            
            # 固定資産関連（6000番台）
            '固定資産台帳',
            '一括償却資産明細表', '一括償却',
            '少額減価償却資産明細表', '少額減価償却', '少額',
            
            # 税区分関連（7000番台）
            '勘定科目別税区分集計表', '税区分集計表'
        ]
        
    def should_split_document(self, ocr_text: str, filename: str) -> bool:
        """分割判定（v4.4継承版）"""
        self.debug_logger.log('INFO', "=== 分割判定開始（v4.4継承版） ===")
        
        # Step 1: 分割不要書類の判定（最優先）
        if self._is_no_split_document(ocr_text, filename):
            self.debug_logger.log('INFO', "分割不要書類として判定：分割処理をスキップ")
            return False
            
        # Step 2: 分割対象キーワードの検出
        split_indicators = self._count_split_indicators(ocr_text)
        
        # Step 3: セット判定（複数の書類種別が検出された場合のみ分割）
        if split_indicators >= 2:
            self.debug_logger.log('INFO', f"分割対象として判定：検出指標数={split_indicators}")
            return True
        else:
            self.debug_logger.log('INFO', f"単一書類として判定：検出指標数={split_indicators}")
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
            category_found = False
            for keyword in keywords:
                if keyword in text:
                    if not category_found:  # カテゴリごとに1回のみカウント
                        indicators += 1
                        category_found = True
                        self.debug_logger.log('DEBUG', f"分割対象キーワード検出: {keyword} (カテゴリ: {category})")
                    break
                    
        return indicators

class EnhancedProcessor:
    """拡張処理クラス（v4.4）"""
    
    def __init__(self, debug_logger, output_directory=None):
        self.debug_logger = debug_logger
        self.split_engine = SplitJudgmentEngine(debug_logger)
        self.output_directory = output_directory
        self.temp_dir = None
        
    def set_output_directory(self, output_dir: str):
        """出力ディレクトリ設定"""
        self.output_directory = output_dir
        self.debug_logger.log('INFO', f"出力ディレクトリ設定: {output_dir}")
        
    def process_multiple_files(self, file_paths: List[str], user_yymm: str = "", regional_settings: Dict = None) -> List[Dict]:
        """複数ファイル処理（v4.4新機能）"""
        all_results = []
        
        try:
            self.debug_logger.log('INFO', f"=== 複数ファイル処理開始: {len(file_paths)}件 ===")
            
            for i, file_path in enumerate(file_paths, 1):
                self.debug_logger.log('INFO', f"--- ファイル {i}/{len(file_paths)}: {os.path.basename(file_path)} ---")
                
                # 個別ファイル処理
                file_results = self.process_single_file(file_path, user_yymm, regional_settings)
                all_results.extend(file_results)
                
            self.debug_logger.log('INFO', f"複数ファイル処理完了：総計{len(all_results)}件の処理結果")
            
            return all_results
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"複数ファイル処理エラー: {e}")
            return []
        finally:
            # 一時ファイルクリーンアップ
            self._cleanup_temp_files()
            
    def process_single_file(self, file_path: str, user_yymm: str = "", regional_settings: Dict = None) -> List[Dict]:
        """単一ファイル処理"""
        results = []
        
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # PDF処理
                results = self._process_pdf_file(file_path, user_yymm, regional_settings)
            elif file_ext == '.csv':
                # CSV処理
                results = self._process_csv_file(file_path, user_yymm)
            else:
                # その他ファイル
                result = {
                    'original_name': os.path.basename(file_path),
                    'new_name': f"unsupported_{user_yymm or '0000'}_{os.path.basename(file_path)}",
                    'document_type': 'unsupported',
                    'split_info': 'サポート外形式',
                    'status': 'warning',
                    'file_path': file_path
                }
                results.append(result)
                
            return results
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"ファイル処理エラー: {e}")
            return [{
                'original_name': os.path.basename(file_path),
                'new_name': '',
                'document_type': 'error',
                'split_info': f'エラー: {e}',
                'status': 'error',
                'file_path': file_path
            }]
            
    def _process_pdf_file(self, file_path: str, user_yymm: str, regional_settings: Dict) -> List[Dict]:
        """PDF処理"""
        # OCR実行
        ocr_text = self._extract_text_from_pdf(file_path)
        filename = os.path.basename(file_path)
        
        # 分割判定
        should_split = self.split_engine.should_split_document(ocr_text, filename)
        
        if should_split:
            # 分割処理
            return self._execute_split_process(file_path, user_yymm, regional_settings)
        else:
            # 単一処理
            return self._execute_single_process(file_path, user_yymm, regional_settings, ocr_text)
            
    def _process_csv_file(self, file_path: str, user_yymm: str) -> List[Dict]:
        """CSV処理"""
        try:
            output_name = f"5006_仕訳データ_{user_yymm or '0000'}.csv"
            output_path = self._generate_output_path(output_name)
            
            # ファイルコピー
            shutil.copy2(file_path, output_path)
            
            return [{
                'original_name': os.path.basename(file_path),
                'new_name': os.path.basename(output_path),
                'document_type': '5006_仕訳データ',
                'split_info': 'CSV処理',
                'status': 'success',
                'file_path': output_path
            }]
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"CSV処理エラー: {e}")
            return [{
                'original_name': os.path.basename(file_path),
                'new_name': '',
                'document_type': 'csv_error',
                'split_info': f'CSVエラー: {e}',
                'status': 'error',
                'file_path': file_path
            }]
            
    def _execute_split_process(self, file_path: str, user_yymm: str, regional_settings: Dict) -> List[Dict]:
        """分割処理実行"""
        self.debug_logger.log('INFO', "分割処理実行")
        
        try:
            # 分割境界検出
            boundaries = self._detect_split_boundaries(file_path)
            
            if len(boundaries) <= 1:
                # 実際には分割不要
                return self._execute_single_process(file_path, user_yymm, regional_settings, 
                                                  self._extract_text_from_pdf(file_path))
                
            # PDF分割実行
            split_files = self._split_pdf_by_boundaries(file_path, boundaries)
            
            # 各分割ファイルを処理
            results = []
            for i, split_file in enumerate(split_files):
                ocr_text = self._extract_text_from_pdf(split_file)
                doc_type = self._classify_document(ocr_text, regional_settings)
                yymm = self._determine_yymm(user_yymm, os.path.basename(split_file), ocr_text)
                
                final_filename = self._generate_final_filename(doc_type, yymm, regional_settings, ocr_text)
                final_path = self._generate_output_path(final_filename)
                
                # ファイル移動
                shutil.move(split_file, final_path)
                
                results.append({
                    'original_name': os.path.basename(file_path),
                    'new_name': final_filename,
                    'document_type': doc_type,
                    'split_info': f"分割 {i+1}/{len(split_files)}",
                    'status': 'success',
                    'file_path': final_path
                })
                
            return results
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"分割処理エラー: {e}")
            return []
            
    def _execute_single_process(self, file_path: str, user_yymm: str, regional_settings: Dict, ocr_text: str) -> List[Dict]:
        """単一処理実行"""
        try:
            doc_type = self._classify_document(ocr_text, regional_settings)
            yymm = self._determine_yymm(user_yymm, os.path.basename(file_path), ocr_text)
            
            final_filename = self._generate_final_filename(doc_type, yymm, regional_settings, ocr_text)
            final_path = self._generate_output_path(final_filename)
            
            # ファイルコピー
            shutil.copy2(file_path, final_path)
            
            return [{
                'original_name': os.path.basename(file_path),
                'new_name': final_filename,
                'document_type': doc_type,
                'split_info': '単一書類処理',
                'status': 'success',
                'file_path': final_path
            }]
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"単一処理エラー: {e}")
            return []
            
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDFテキスト抽出"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                text += page_text + "\n"
                
            doc.close()
            return text
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"PDF読み込みエラー: {e}")
            return ""
            
    def _detect_split_boundaries(self, pdf_path: str) -> List[int]:
        """分割境界検出"""
        try:
            doc = fitz.open(pdf_path)
            boundaries = [0]  # 最初のページは常に境界
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                # 新しい書類の開始を示すキーワード検出
                if self._is_document_start(page_text) and page_num > 0:
                    boundaries.append(page_num)
                    self.debug_logger.log('DEBUG', f"分割境界検出: ページ {page_num + 1}")
                    
            doc.close()
            
            # 重複除去とソート
            boundaries = sorted(list(set(boundaries)))
            self.debug_logger.log('INFO', f"分割境界: {boundaries}")
            
            return boundaries
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"分割境界検出エラー: {e}")
            return [0]
            
    def _is_document_start(self, page_text: str) -> bool:
        """新しい書類の開始判定"""
        start_indicators = [
            '税務署長', '都道府県知事', '市町村長',
            '申告受付完了通知', '納付情報発行結果',
            '申告書等送信票', '受信通知書'
        ]
        
        for indicator in start_indicators:
            if indicator in page_text:
                return True
        return False
        
    def _split_pdf_by_boundaries(self, pdf_path: str, boundaries: List[int]) -> List[str]:
        """PDF分割実行"""
        split_files = []
        
        try:
            # 一時ディレクトリ作成
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp(prefix="tax_doc_split_")
                
            pdf_reader = PyPDF2.PdfReader(pdf_path)
            
            for i, start_page in enumerate(boundaries):
                end_page = boundaries[i + 1] if i + 1 < len(boundaries) else len(pdf_reader.pages)
                
                # 一時ファイル名生成
                temp_filename = os.path.join(self.temp_dir, f"temp_split_{i+1:03d}.pdf")
                
                # PDF分割
                pdf_writer = PyPDF2.PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                # ファイル書き出し
                with open(temp_filename, 'wb') as output_file:
                    pdf_writer.write(output_file)
                    
                split_files.append(temp_filename)
                self.debug_logger.log('DEBUG', f"分割ファイル作成: {temp_filename}")
                
            return split_files
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"PDF分割エラー: {e}")
            return []
            
    def _classify_document(self, text: str, regional_settings: Dict = None) -> str:
        """文書分類"""
        # 基本的な分類パターン
        classification_patterns = {
            # 最高優先度：受信通知・納付情報
            '0003_受信通知': ['法人税', '申告受付完了通知', '法人税申告書', '受信通知'],
            '0004_納付情報': ['法人税', '納付情報発行結果', '納付区分番号', '法人税納付'],
            '3003_受信通知': ['消費税', '申告受付完了通知', '消費税申告書', '受信通知'],
            '3004_納付情報': ['消費税', '納付情報発行結果', '納付区分番号', '消費税納付'],
            
            # 高優先度：申告書
            '0001_法人税及び地方法人税申告書': ['法人税申告書', '法人税及び地方法人税', '内国法人の確定申告'],
            '3001_消費税及び地方消費税申告書': ['消費税申告書', '消費税及び地方消費税'],
            
            # 地方税関連
            '1001_法人都道府県民税': ['法人都道府県民税', '法人事業税', '特別法人事業税'],
            '2001_法人市民税': ['法人市民税'],
            
            # その他
            '0000_納付税額一覧表': ['納付税額一覧表'],
            '5001_決算書': ['決算書', '貸借対照表', '損益計算書'],
            '6001_固定資産台帳': ['固定資産台帳'],
            '6002_一括償却資産明細表': ['一括償却資産明細表', '一括償却'],
            '6003_少額減価償却資産明細表': ['少額減価償却資産明細表', '少額減価償却', '少額'],
        }
        
        for doc_type, keywords in classification_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    self.debug_logger.log('DEBUG', f"文書分類: {doc_type} (キーワード: {keyword})")
                    return doc_type
                    
        return '9999_未分類'
        
    def _determine_yymm(self, user_input: str, filename: str, ocr_text: str) -> str:
        """YYMM決定（優先度適用）"""
        # 1. ユーザー入力最優先
        if user_input and user_input.strip():
            return user_input.strip()
            
        # 2. ファイル名から推定
        filename_yymm = self._extract_yymm_from_filename(filename)
        if filename_yymm:
            return filename_yymm
            
        # 3. OCR結果から推定（補完的）
        ocr_yymm = self._extract_yymm_from_text(ocr_text)
        if ocr_yymm:
            return ocr_yymm
            
        # 4. デフォルト
        return "0000"
        
    def _extract_yymm_from_filename(self, filename: str) -> Optional[str]:
        """ファイル名からYYMM抽出"""
        patterns = [
            r'(\d{4})(?:\D|$)',  # 4桁数字
            r'_(\d{4})[._]',     # アンダースコア区切り
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        return None
        
    def _extract_yymm_from_text(self, text: str) -> Optional[str]:
        """テキストからYYMM抽出"""
        patterns = [
            r'令和(\d+)年(\d+)月',
            r'(\d{4})年(\d+)月',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if '令和' in pattern:
                    year = int(match.group(1)) + 18  # 令和→西暦変換簡易版
                    month = int(match.group(2))
                    return f"{year:02d}{month:02d}"
                else:
                    return match.group(1)[:2] + match.group(2).zfill(2)
        return None
        
    def _generate_final_filename(self, doc_type: str, yymm: str, regional_settings: Dict, ocr_text: str) -> str:
        """最終ファイル名生成"""
        if doc_type == '9999_未分類':
            return f"未分類_{yymm}.pdf"
            
        # 地域情報の適用（地方税関連の場合）
        if doc_type.startswith('1001_') and regional_settings:
            # 都道府県税の場合
            prefecture = self._detect_prefecture_from_settings_and_text(ocr_text, regional_settings)
            if prefecture:
                return f"1001_{prefecture}_法人都道府県民税・事業税・特別法人事業税_{yymm}.pdf"
        elif doc_type.startswith('2001_') and regional_settings:
            # 市町村税の場合
            prefecture, city = self._detect_prefecture_city_from_settings_and_text(ocr_text, regional_settings)
            if prefecture and city and prefecture != '東京都':
                return f"2001_{prefecture}{city}_法人市民税_{yymm}.pdf"
            
        # 基本ファイル名
        base_name = doc_type.replace('_', '_', 1)  # 最初のアンダースコアのみ保持
        
        return f"{base_name}_{yymm}.pdf"
        
    def _detect_prefecture_from_settings_and_text(self, text: str, regional_settings: Dict) -> Optional[str]:
        """地域設定とOCRテキストから都道府県検出"""
        if not regional_settings:
            return None
            
        # 設定された都道府県とOCRテキストのマッチング
        for i in range(5):  # セット1-5
            pref_key = f'prefecture_{i}'
            if pref_key in regional_settings and regional_settings[pref_key]:
                prefecture = regional_settings[pref_key]
                if prefecture in text:
                    return prefecture
                    
        return None
        
    def _detect_prefecture_city_from_settings_and_text(self, text: str, regional_settings: Dict) -> Tuple[Optional[str], Optional[str]]:
        """地域設定とOCRテキストから都道府県・市町村検出"""
        if not regional_settings:
            return None, None
            
        # 設定された都道府県・市町村とOCRテキストのマッチング
        for i in range(5):  # セット1-5
            pref_key = f'prefecture_{i}'
            city_key = f'city_{i}'
            
            if (pref_key in regional_settings and regional_settings[pref_key] and
                city_key in regional_settings and regional_settings[city_key]):
                
                prefecture = regional_settings[pref_key]
                city = regional_settings[city_key]
                
                if prefecture in text and city in text:
                    return prefecture, city
                    
        return None, None
        
    def _generate_output_path(self, filename: str) -> str:
        """出力パス生成"""
        if self.output_directory:
            output_path = os.path.join(self.output_directory, filename)
        else:
            # デフォルトは現在のディレクトリ
            output_path = filename
            
        # 同名ファイル存在チェック
        if os.path.exists(output_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(output_path):
                new_filename = f"{base}_{counter:03d}{ext}"
                output_path = os.path.join(self.output_directory or '', new_filename)
                counter += 1
                
        return output_path
        
    def _cleanup_temp_files(self):
        """一時ファイルクリーンアップ"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.debug_logger.log('DEBUG', f"一時ディレクトリ削除: {self.temp_dir}")
            except Exception as e:
                self.debug_logger.log('WARNING', f"一時ディレクトリ削除エラー: {e}")

class TaxDocumentRenamerApp:
    """メインアプリケーションクラス（v4.4機能拡張版）"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("税務書類リネームシステム v4.4 機能拡張版")
        self.root.geometry("1000x800")
        
        # デバッグログ用
        self.debug_text = None
        self.debug_logger = None
        
        # 処理エンジン
        self.processor = None
        
        # ファイル選択関連
        self.selected_files = []
        self.output_directory_var = tk.StringVar()
        
        # 地域設定（統合版）
        self.regional_vars = {}
        
        # 設定ファイル
        self.config_file = os.path.join(os.path.expanduser("~"), "TaxDocumentRenamer", "config.txt")
        
        # UI構築
        self.setup_ui()
        self.setup_logger()
        
        # 設定読み込み
        self.load_settings()
        
        # 処理エンジン初期化
        self.initialize_processor()
        
    def setup_ui(self):
        """UI構築"""
        # ノートブック作成
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # タブ作成
        self.setup_main_tab()
        self.setup_results_tab()
        self.setup_debug_tab()
        
    def setup_main_tab(self):
        """メインタブ構築（v4.4統合版）"""
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="ファイル処理・地域設定")
        
        # スクロール可能フレーム
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # YYMM入力
        yymm_frame = ttk.LabelFrame(scrollable_frame, text="年月設定（YYMM形式）")
        yymm_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(yymm_frame, text="年月(YYMM):").pack(side=tk.LEFT, padx=5)
        self.yymm_entry = ttk.Entry(yymm_frame, width=10)
        self.yymm_entry.pack(side=tk.LEFT, padx=5)
        
        # ファイル選択（複数対応）
        file_frame = ttk.LabelFrame(scrollable_frame, text="ファイル選択（複数選択可能）")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # ファイル選択ボタン
        file_button_frame = ttk.Frame(file_frame)
        file_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_button_frame, text="ファイル選択", command=self.select_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_button_frame, text="クリア", command=self.clear_files).pack(side=tk.LEFT, padx=5)
        
        # 選択ファイル一覧
        files_list_frame = ttk.Frame(file_frame)
        files_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.files_listbox = tk.Listbox(files_list_frame, height=4, selectmode=tk.EXTENDED)
        files_scrollbar = ttk.Scrollbar(files_list_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=files_scrollbar.set)
        
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 出力先フォルダ選択
        output_frame = ttk.LabelFrame(scrollable_frame, text="出力先フォルダ")
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        output_button_frame = ttk.Frame(output_frame)
        output_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Entry(output_button_frame, textvariable=self.output_directory_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_button_frame, text="フォルダ選択", command=self.select_output_directory).pack(side=tk.RIGHT, padx=5)
        
        # 地域設定（統合版）
        regional_frame = ttk.LabelFrame(scrollable_frame, text="地域設定（5セット）")
        regional_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 5つの地域設定セット
        for i in range(5):
            self.create_regional_set(regional_frame, i + 1)
            
        # 処理実行
        process_frame = ttk.Frame(scrollable_frame)
        process_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(process_frame, text="処理実行", command=self.process_files, width=20).pack()
        
        # 処理状況表示
        self.status_label = ttk.Label(scrollable_frame, text="ファイルを選択して処理を実行してください")
        self.status_label.pack(pady=5)
        
        # スクロールバー配置
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_regional_set(self, parent, set_num):
        """地域設定セット作成"""
        set_frame = ttk.Frame(parent)
        set_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(set_frame, text=f"セット{set_num}:").pack(side=tk.LEFT, padx=5)
        
        # 都道府県選択
        ttk.Label(set_frame, text="都道府県:").pack(side=tk.LEFT)
        pref_var = tk.StringVar()
        pref_combo = ttk.Combobox(set_frame, textvariable=pref_var, width=12)
        pref_combo['values'] = self.get_prefecture_list()
        pref_combo.pack(side=tk.LEFT, padx=2)
        self.regional_vars[f'prefecture_{set_num-1}'] = pref_var
        
        # 市町村入力
        ttk.Label(set_frame, text="市町村:").pack(side=tk.LEFT, padx=(10,0))
        city_var = tk.StringVar()
        city_entry = ttk.Entry(set_frame, textvariable=city_var, width=12)
        city_entry.pack(side=tk.LEFT, padx=2)
        self.regional_vars[f'city_{set_num-1}'] = city_var
        
    def get_prefecture_list(self):
        """47都道府県リスト"""
        return [
            '', '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
            '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
            '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
            '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
            '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
            '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
            '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
        ]
        
    def setup_results_tab(self):
        """結果一覧タブ構築"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="結果一覧")
        
        # 結果表示用Treeview
        columns = ('original', 'new_name', 'type', 'split_info', 'status')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        
        # ヘッダー設定
        self.results_tree.heading('original', text='元ファイル名')
        self.results_tree.heading('new_name', text='新ファイル名')
        self.results_tree.heading('type', text='書類種別')
        self.results_tree.heading('split_info', text='分割情報')
        self.results_tree.heading('status', text='処理状況')
        
        # 列幅設定
        self.results_tree.column('original', width=200)
        self.results_tree.column('new_name', width=200)
        self.results_tree.column('type', width=150)
        self.results_tree.column('split_info', width=150)
        self.results_tree.column('status', width=100)
        
        # スクロールバー
        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        # パック
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # CSV出力ボタン
        export_frame = ttk.Frame(results_frame)
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(export_frame, text="結果をCSV出力", command=self.export_results).pack()
        
    def setup_debug_tab(self):
        """デバッグタブ構築"""
        debug_frame = ttk.Frame(self.notebook)
        self.notebook.add(debug_frame, text="ログ")
        
        # デバッグテキストエリア
        self.debug_text = scrolledtext.ScrolledText(debug_frame, wrap=tk.WORD)
        self.debug_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def setup_logger(self):
        """ログ設定"""
        self.debug_logger = DebugLogger(self.debug_text)
        self.debug_logger.log('INFO', "税務書類リネームシステム v4.4 機能拡張版 起動")
        
    def initialize_processor(self):
        """処理エンジン初期化"""
        output_dir = self.output_directory_var.get() if self.output_directory_var.get() else None
        self.processor = EnhancedProcessor(self.debug_logger, output_dir)
        
    def select_files(self):
        """ファイル選択（複数対応）"""
        file_paths = filedialog.askopenfilenames(
            title="処理するファイルを選択（複数選択可能）",
            filetypes=[
                ("PDFファイル", "*.pdf"),
                ("CSVファイル", "*.csv"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if file_paths:
            self.selected_files = list(file_paths)
            self.update_files_display()
            
    def clear_files(self):
        """ファイル選択クリア"""
        self.selected_files = []
        self.update_files_display()
        
    def update_files_display(self):
        """ファイル表示更新"""
        # リストボックスクリア
        self.files_listbox.delete(0, tk.END)
        
        # ファイル追加
        for file_path in self.selected_files:
            self.files_listbox.insert(tk.END, os.path.basename(file_path))
            
        # ステータス更新
        if self.selected_files:
            self.status_label.config(text=f"選択ファイル: {len(self.selected_files)}件")
        else:
            self.status_label.config(text="ファイルを選択して処理を実行してください")
            
    def select_output_directory(self):
        """出力先フォルダ選択"""
        directory = filedialog.askdirectory(title="出力先フォルダを選択")
        
        if directory:
            self.output_directory_var.set(directory)
            self.debug_logger.log('INFO', f"出力先フォルダ設定: {directory}")
            
            # 処理エンジンに反映
            if self.processor:
                self.processor.set_output_directory(directory)
                
    def process_files(self):
        """ファイル処理実行（複数対応）"""
        if not self.selected_files:
            messagebox.showerror("エラー", "処理するファイルを選択してください")
            return
            
        user_yymm = self.yymm_entry.get().strip()
        
        # 地域設定取得
        regional_settings = {}
        for key, var in self.regional_vars.items():
            regional_settings[key] = var.get()
            
        # 出力先設定
        if self.output_directory_var.get():
            self.processor.set_output_directory(self.output_directory_var.get())
            
        # 処理実行（スレッド化）
        def process_thread():
            try:
                self.status_label.config(text="処理中...")
                self.root.update()
                
                # 複数ファイル処理実行
                results = self.processor.process_multiple_files(
                    self.selected_files, user_yymm, regional_settings
                )
                
                # 結果表示
                self.display_results(results)
                
                self.status_label.config(text=f"処理完了: {len(results)}件の処理結果")
                
            except Exception as e:
                self.debug_logger.log('ERROR', f"処理エラー: {e}")
                self.status_label.config(text="処理エラーが発生しました")
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
            
    def export_results(self):
        """結果CSV出力"""
        try:
            # 結果データ取得
            results_data = []
            for child in self.results_tree.get_children():
                values = self.results_tree.item(child)['values']
                results_data.append(values)
                
            if not results_data:
                messagebox.showwarning("警告", "出力する結果がありません")
                return
                
            # CSV出力先選択
            output_file = filedialog.asksaveasfilename(
                title="結果CSV出力先を選択",
                defaultextension=".csv",
                filetypes=[("CSVファイル", "*.csv")]
            )
            
            if output_file:
                # CSV書き出し
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['元ファイル名', '新ファイル名', '書類種別', '分割情報', '処理状況'])
                    writer.writerows(results_data)
                    
                self.debug_logger.log('INFO', f"結果CSV出力完了: {output_file}")
                messagebox.showinfo("完了", f"結果をCSVファイルに出力しました:\n{output_file}")
                
        except Exception as e:
            self.debug_logger.log('ERROR', f"CSV出力エラー: {e}")
            messagebox.showerror("エラー", f"CSV出力中にエラーが発生しました: {e}")
            
    def load_settings(self):
        """設定読み込み"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            if key == 'output_directory':
                                self.output_directory_var.set(value)
                            elif key.startswith(('prefecture_', 'city_')) and key in self.regional_vars:
                                self.regional_vars[key].set(value)
        except Exception as e:
            self.debug_logger.log('WARNING', f"設定読み込みエラー: {e}")
            
    def save_settings(self):
        """設定保存"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(f"output_directory={self.output_directory_var.get()}\n")
                for key, var in self.regional_vars.items():
                    f.write(f"{key}={var.get()}\n")
                    
        except Exception as e:
            self.debug_logger.log('WARNING', f"設定保存エラー: {e}")
            
    def on_closing(self):
        """アプリケーション終了時"""
        self.save_settings()
        self.root.destroy()

def main():
    """メイン関数"""
    root = tk.Tk()
    app = TaxDocumentRenamerApp(root)
    
    # 終了時の処理
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()