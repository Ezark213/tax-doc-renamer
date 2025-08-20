#!/usr/bin/env python3
"""
税務書類リネームシステム v4.5 分割・リネーム精密修正版
v4.2をベース、要件定義に従った厳格な分割判定・2段階処理システム実装
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
    """要件定義準拠分割判定エンジン"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.setup_split_keywords()
        
    def setup_split_keywords(self):
        """分割対象キーワード設定（要件定義通り）"""
        # 要件定義準拠：分割対象判定キーワード
        self.split_keywords = {
            'receipt_notice': ['申告受付完了通知', '受信通知'],
            'payment_info': ['納付情報発行結果', '納付区分番号通知', '納付情報'],
            'tax_types': ['法人税申告書', '消費税申告書', '法人都道府県民税'],
            'document_boundaries': ['税目', '種目', '申告の種類']
        }
        
        # 分割不要書類（厳格な除外）
        self.no_split_patterns = [
            # 要件定義明記：分割不要書類
            '少額減価償却', '少額', 
            '一括償却資産明細', '一括償却',
            '固定資産台帳',
            '決算書', '貸借対照表', '損益計算書',
            '総勘定元帳', '補助元帳', '仕訳帳',
            '勘定科目別税区分集計表', '税区分集計表',
            # 単一書類
            '消費税申告書のみ', '法人税申告書のみ'
        ]
        
    def should_split_pdf(self, pdf_path: str, ocr_text: str) -> bool:
        """厳格な分割判定（要件定義準拠）"""
        filename = os.path.basename(pdf_path).lower()
        
        self.debug_logger.log('INFO', f"分割判定開始: {filename}")
        
        # Step1: 分割除外パターンチェック（最優先）
        for pattern in self.no_split_patterns:
            if pattern in ocr_text or pattern in filename:
                self.debug_logger.log('INFO', f"分割除外: '{pattern}' → 分割不要")
                return False
        
        # Step2: 分割対象指標検出
        split_indicators = 0
        detected_types = set()
        
        for category, keywords in self.split_keywords.items():
            for keyword in keywords:
                if keyword in ocr_text:
                    split_indicators += 1
                    detected_types.add(category)
                    self.debug_logger.log('DEBUG', f"分割指標検出: '{keyword}' ({category})")
        
        # Step3: 要件定義準拠判定
        # 2つ以上の異なる書類種別が検出された場合は分割対象
        should_split = len(detected_types) >= 2 and split_indicators >= 2
        
        self.debug_logger.log('INFO', 
            f"分割判定結果: {should_split} (指標数: {split_indicators}, 種別数: {len(detected_types)})")
        
        return should_split
        
    def detect_split_boundaries(self, pdf_path: str) -> List[int]:
        """分割境界検出（要件定義準拠）"""
        boundaries = []
        
        try:
            doc = fitz.open(pdf_path)
            self.debug_logger.log('INFO', f"境界検出開始: {len(doc)}ページ")
            
            # 最初に分割要否判定
            full_text = ""
            for page_num in range(len(doc)):
                full_text += doc[page_num].get_text() + "\n"
            
            if not self.should_split_pdf(pdf_path, full_text):
                doc.close()
                return []  # 分割不要
            
            # 有効ページ検出（空白ページ除去）
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text().strip()
                
                # 空白ページ判定（テキスト50文字以上で有効）
                if len(text) >= 50:
                    # さらに分割境界キーワード検出
                    has_boundary_keyword = any(
                        keyword in text 
                        for keywords in self.split_keywords.values() 
                        for keyword in keywords
                    )
                    
                    if has_boundary_keyword:
                        boundaries.append(page_num)
                        self.debug_logger.log('DEBUG', 
                            f"分割境界検出: ページ{page_num + 1} ({len(text)}文字)")
                    else:
                        self.debug_logger.log('DEBUG', 
                            f"境界キーワードなし: ページ{page_num + 1}")
                else:
                    self.debug_logger.log('DEBUG', 
                        f"空白ページ除外: ページ{page_num + 1} ({len(text)}文字)")
            
            doc.close()
            self.debug_logger.log('INFO', f"有効境界: {[p+1 for p in boundaries]}")
            return boundaries
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"境界検出エラー: {e}")
            return []

class RegionalDetectionEngine:
    """地域判定エンジン（v4.2継承）"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.setup_prefectures()
        self.setup_detection_patterns()
        
    def setup_prefectures(self):
        """都道府県マスタ設定"""
        self.prefectures = [
            '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
            '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
            '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
            '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
            '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
            '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
            '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
        ]
        
    def setup_detection_patterns(self):
        """検出パターン設定"""
        # 事務所長パターン（地域判定用）
        self.office_patterns = {
            '都道府県': r'([^市区町村]+(?:県|都|府|道))[^市区町村]*事務所長',
            '税務署': r'([^市区町村]+(?:県|都|府|道))[^市区町村]*税務署長',
            '県税': r'([^市区町村]+(?:県|都|府|道))[^市区町村]*県税',
        }
        
        # 市町村パターン
        self.city_patterns = {
            '市長': r'([^県都府道]+市)長',
            '町長': r'([^県都府道]+町)長',
            '村長': r'([^県都府道]+村)長',
        }
        
    def detect_prefecture_from_text(self, text: str) -> Optional[str]:
        """テキストから都道府県検出"""
        for prefecture in self.prefectures:
            if prefecture in text:
                self.debug_logger.log('DEBUG', f"都道府県検出: {prefecture}")
                return prefecture
        return None
        
    def detect_city_from_text(self, text: str) -> Optional[str]:
        """テキストから市町村検出"""
        for pattern_type, pattern in self.city_patterns.items():
            match = re.search(pattern, text)
            if match:
                city = match.group(1)
                self.debug_logger.log('DEBUG', f"市町村検出: {city}")
                return city
        return None
        
    def get_prefecture_set_number(self, prefecture_selections: List[str], 
                                   detected_prefecture: str) -> Optional[int]:
        """都道府県セット番号取得"""
        for i, prefecture in enumerate(prefecture_selections):
            if prefecture == detected_prefecture:
                return i + 1  # 1-indexed
        return None
        
    def get_city_set_info(self, prefecture_selections: List[str], 
                          city_selections: List[str], 
                          detected_city: str) -> Optional[Tuple[int, str]]:
        """市町村セット情報取得"""
        for i, city in enumerate(city_selections):
            if detected_city in city:
                prefecture = prefecture_selections[i] if i < len(prefecture_selections) else None
                if prefecture:
                    return i + 1, prefecture  # 1-indexed, prefecture
        return None
        
    def generate_regional_filename(self, doc_type: str, prefecture: str, 
                                   city: str, set_number: int, yymm: str) -> Optional[str]:
        """地域別ファイル名生成"""
        if doc_type == "都道府県申告":
            code = f"10{set_number-1:02d}"  # 1001, 1011, 1021...
            return f"{code}_{prefecture}_法人都道府県民税・事業税・特別法人事業税_{yymm}.pdf"
        elif doc_type == "市町村申告":
            code = f"20{set_number-1:02d}"  # 2001, 2011, 2021...
            return f"{code}_{prefecture}{city}_法人市民税_{yymm}.pdf"
        return None

class KeywordPriorityEngine:
    """キーワード優先度エンジン（v4.2ベース・5001以降保護）"""
    
    def __init__(self, debug_logger, regional_engine, prefecture_selections=None, city_selections=None):
        self.debug_logger = debug_logger
        self.regional_engine = regional_engine
        self.prefecture_selections = prefecture_selections or []
        self.city_selections = city_selections or []
        self.setup_priority_rules()
        
    def setup_priority_rules(self):
        """優先度ルール設定（5001以降は完全保護）"""
        
        # 最高優先度：法人税申告書（修正：決算書より優先）
        self.supreme_priority_patterns = {
            '内国法人の確定申告': '0001_法人税及び地方法人税申告書_{yymm}.pdf',
            '法人税申告書': '0001_法人税及び地方法人税申告書_{yymm}.pdf',
            '法人税及び地方法人税申告': '0001_法人税及び地方法人税申告書_{yymm}.pdf',
        }
        
        # 高優先度：0000-4999範囲の具体的な書類名のみ
        self.high_priority_patterns = {
            '納付税額一覧表': '0000_納付税額一覧表_{yymm}.pdf',
            '納税一覧': '0000_納付税額一覧表_{yymm}.pdf',
        }
        
        # 【重要】5001以降の書類は完全保護（v4.2の動作を完全継承）
        self.protected_5000_patterns = {
            # 5001-5999: 会計書類（完全保護）
            '決算報告書': '5001_決算書_{yymm}.pdf',
            '貸借対照表': '5001_決算書_{yymm}.pdf', 
            '損益計算書': '5001_決算書_{yymm}.pdf',
            '決算書': '5001_決算書_{yymm}.pdf',
            '総勘定元帳': '5002_総勘定元帳_{yymm}.pdf',
            '仕訳帳': '5005_仕訳帳_{yymm}.pdf',
            '補助元帳': '5003_補助元帳_{yymm}.pdf',
            '残高試算表': '5004_残高試算表_{yymm}.pdf',
            
            # 6001-6999: 固定資産関連（完全保護）
            '固定資産台帳': '6001_固定資産台帳_{yymm}.pdf',
            '一括償却資産明細表': '6002_一括償却資産明細表_{yymm}.pdf',
            '一括償却資産明細': '6002_一括償却資産明細表_{yymm}.pdf',
            '少額減価償却資産明細表': '6003_少額減価償却資産明細表_{yymm}.pdf',
            '少額減価償却': '6003_少額減価償却資産明細表_{yymm}.pdf',
            '少額': '6003_少額減価償却資産明細表_{yymm}.pdf',
            
            # 7001-7999: 税区分集計表（完全保護）
            '勘定科目別税区分集計表': '7001_勘定科目別税区分集計表_{yymm}.pdf',
            '税区分集計表': '7002_税区分集計表_{yymm}.pdf',
        }
        
        # 中優先度：税目別キーワード
        self.medium_priority_patterns = {
            '消費税申告書': '3001_消費税申告書_{yymm}.pdf',
            '消費税及び地方消費税申告': '3001_消費税申告書_{yymm}.pdf',
        }
        
        # 受信通知・納付情報（要件定義準拠）
        self.receipt_payment_patterns = {
            # 国税関連
            '法人税.*受信通知': '0003_受信通知_{yymm}.pdf',
            '法人税.*納付情報': '0004_納付情報_{yymm}.pdf',
            '消費税.*受信通知': '3003_受信通知_{yymm}.pdf', 
            '消費税.*納付情報': '3004_納付情報_{yymm}.pdf',
            # 地方税関連（動的生成）
            '都道府県.*受信通知': '1003_受信通知_{yymm}.pdf',  # デフォルト
            '市町村.*受信通知': '2003_受信通知_{yymm}.pdf',   # デフォルト
            '地方税.*納付情報': '1004_納付情報_{yymm}.pdf',
        }
        
        # CSV専用パターン（完全保護）
        self.csv_patterns = {
            '仕訳帳': '5006_仕訳データ_{yymm}.csv',
            '取引No': '5006_仕訳データ_{yymm}.csv',
            '総勘定元帳': '5007_総勘定元帳_{yymm}.csv',
            '補助元帳': '5008_補助元帳_{yymm}.csv',
        }
        
    def determine_document_type(self, text: str, filename: str, file_ext: str) -> Tuple[str, str]:
        """優先度に基づく文書種別判定（5001以降完全保護）"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        self.debug_logger.log('DEBUG', f"判定開始 - ファイル: {filename}, 拡張子: {file_ext}")
        
        # CSV専用判定（完全保護）
        if file_ext == '.csv':
            return self._determine_csv_type(text, filename)
        
        # 【最重要】5001以降の書類判定（完全保護）
        for keyword, pattern in self.protected_5000_patterns.items():
            if keyword in text or keyword in filename_lower:
                self.debug_logger.log('INFO', f"5000番台判定（保護）: '{keyword}' → {pattern}")
                return keyword, pattern
        
        # 地域判定（地方税関連）
        regional_result = self._determine_regional_type(text)
        if regional_result[0] != '不明':
            return regional_result
        
        # 最高優先度：法人税申告書
        for keyword, pattern in self.supreme_priority_patterns.items():
            if keyword in text or keyword in filename_lower:
                self.debug_logger.log('INFO', f"最高優先度判定: '{keyword}' → {pattern}")
                return keyword, pattern
        
        # 受信通知・納付情報パターン（要件定義準拠）
        for keyword, pattern in self.receipt_payment_patterns.items():
            if re.search(keyword, text) or re.search(keyword, filename_lower):
                self.debug_logger.log('INFO', f"受信通知・納付情報判定: '{keyword}' → {pattern}")
                return keyword, pattern
        
        # 高優先度：具体的な書類名（0000-4999のみ）
        for keyword, pattern in self.high_priority_patterns.items():
            if keyword in text or keyword in filename_lower:
                self.debug_logger.log('INFO', f"高優先度判定: '{keyword}' → {pattern}")
                return keyword, pattern
        
        # 中優先度：税目別キーワード
        for keyword, pattern in self.medium_priority_patterns.items():
            if keyword in text or keyword in filename_lower:
                self.debug_logger.log('INFO', f"中優先度判定: '{keyword}' → {pattern}")
                return keyword, pattern
                
        self.debug_logger.log('WARNING', "文書種別判定不可")
        return '不明', ''
        
    def _determine_regional_type(self, text: str) -> Tuple[str, str]:
        """地域判定による文書種別決定"""
        
        # 都道府県判定
        detected_prefecture = self.regional_engine.detect_prefecture_from_text(text)
        if detected_prefecture:
            set_number = self.regional_engine.get_prefecture_set_number(self.prefecture_selections, detected_prefecture)
            if set_number:
                filename = self.regional_engine.generate_regional_filename(
                    "都道府県申告", detected_prefecture, "", set_number, "{yymm}"
                )
                if filename:
                    self.debug_logger.log('INFO', f"都道府県申告判定: {detected_prefecture} → {filename}")
                    return '都道府県申告', filename
        
        # 市町村判定
        detected_city = self.regional_engine.detect_city_from_text(text)
        if detected_city:
            city_info = self.regional_engine.get_city_set_info(
                self.prefecture_selections, self.city_selections, detected_city
            )
            if city_info:
                set_number, prefecture = city_info
                filename = self.regional_engine.generate_regional_filename(
                    "市町村申告", prefecture, detected_city, set_number, "{yymm}"
                )
                if filename:
                    self.debug_logger.log('INFO', f"市町村申告判定: {prefecture}{detected_city} → {filename}")
                    return '市町村申告', filename
        
        return '不明', ''
        
    def _determine_csv_type(self, text: str, filename: str) -> Tuple[str, str]:
        """CSV専用判定（完全保護）"""
        for keyword, pattern in self.csv_patterns.items():
            if keyword in text or keyword in filename.lower():
                self.debug_logger.log('INFO', f"CSV判定（保護）: '{keyword}' → {pattern}")
                return keyword, pattern
        return '不明', ''

class PDFProcessor:
    """2段階処理システム対応PDFプロセッサー"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
        self.split_engine = SplitJudgmentEngine(debug_logger)
        
    def split_pdf_to_temp_files(self, pdf_path: str, output_dir: str) -> List[str]:
        """Stage1: PDF分割（一時ファイル生成）"""
        temp_files = []
        
        # 分割境界検出
        boundaries = self.split_engine.detect_split_boundaries(pdf_path)
        
        if len(boundaries) <= 1:
            # 分割不要の場合は元ファイルを返す
            return [pdf_path]
        
        try:
            doc = fitz.open(pdf_path)
            base_name = Path(pdf_path).stem
            
            # 各境界で分割（1ページずつ）
            for i, page_num in enumerate(boundaries):
                # 新しいPDF作成
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                # 一時ファイルとして保存（temp_001.pdf形式）
                temp_filename = os.path.join(output_dir, f"temp_{i+1:03d}.pdf")
                new_doc.save(temp_filename)
                new_doc.close()
                
                temp_files.append(temp_filename)
                self.debug_logger.log('INFO', f"一時ファイル生成: {temp_filename}")
            
            doc.close()
            return temp_files
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"PDF分割エラー: {e}")
            return [pdf_path]
    
    def rename_temp_files_to_final(self, temp_files: List[str], 
                                   priority_engine: KeywordPriorityEngine,
                                   yymm_processor,
                                   user_yymm: str) -> List[Dict]:
        """Stage2: 一時ファイル→最終ファイル名変換"""
        results = []
        
        for temp_file in temp_files:
            try:
                # OCR実行
                ocr_text = self.extract_text_from_pdf(temp_file)
                filename = os.path.basename(temp_file)
                
                # YYMM決定
                yymm = yymm_processor.determine_yymm(user_yymm, filename, ocr_text)
                
                # 文書種別判定
                doc_type, pattern = priority_engine.determine_document_type(
                    ocr_text, filename, '.pdf'
                )
                
                if pattern:
                    # 最終ファイル名生成
                    final_filename = pattern.format(yymm=yymm)
                    final_path = os.path.join(os.path.dirname(temp_file), final_filename)
                    
                    # リネーム実行
                    shutil.move(temp_file, final_path)
                    
                    results.append({
                        'original_file': temp_file,
                        'new_file': final_path,
                        'document_type': doc_type,
                        'processing_status': 'success'
                    })
                    
                    self.debug_logger.log('INFO', f"リネーム成功: {filename} → {final_filename}")
                else:
                    # 判定失敗
                    fallback_filename = f"未分類_{yymm}.pdf"
                    fallback_path = os.path.join(os.path.dirname(temp_file), fallback_filename)
                    shutil.move(temp_file, fallback_path)
                    
                    results.append({
                        'original_file': temp_file,
                        'new_file': fallback_path,
                        'document_type': '不明',
                        'processing_status': 'fallback'
                    })
                    
                    self.debug_logger.log('WARNING', f"判定失敗: {filename} → {fallback_filename}")
                    
            except Exception as e:
                self.debug_logger.log('ERROR', f"リネーム処理エラー: {e}")
                results.append({
                    'original_file': temp_file,
                    'new_file': temp_file,
                    'document_type': 'エラー',
                    'processing_status': 'error'
                })
        
        return results
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
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

class OCRProcessor:
    """OCR処理クラス（v4.2継承）"""
    
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

class YYMMProcessor:
    """YYMM判定処理クラス（v4.2継承）"""
    
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

class CSVProcessor:
    """CSV処理クラス（v4.2継承）"""
    
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

class EnhancedProcessor:
    """v4.5統合プロセッサー（2段階処理システム）"""
    
    def __init__(self, debug_logger, prefecture_selections=None, city_selections=None):
        self.debug_logger = debug_logger
        self.prefecture_selections = prefecture_selections or []
        self.city_selections = city_selections or []
        
        # 各処理エンジンの初期化
        self.regional_engine = RegionalDetectionEngine(debug_logger)
        self.priority_engine = KeywordPriorityEngine(
            debug_logger, self.regional_engine, 
            self.prefecture_selections, self.city_selections
        )
        self.pdf_processor = PDFProcessor(debug_logger)
        self.csv_processor = CSVProcessor(debug_logger)
        self.ocr_processor = OCRProcessor(debug_logger)
        self.yymm_processor = YYMMProcessor(debug_logger)
        
    def process_single_file(self, file_path: str, user_yymm: str = "") -> List[Dict]:
        """単一ファイル処理（2段階処理システム）"""
        results = []
        
        try:
            self.debug_logger.log('INFO', f"=== 単一ファイル処理開始: {os.path.basename(file_path)} ===")
            
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # Stage1: PDF分割処理
                temp_dir = tempfile.mkdtemp(prefix="tax_split_")
                temp_files = self.pdf_processor.split_pdf_to_temp_files(file_path, temp_dir)
                
                # Stage2: 一時ファイル→最終リネーム
                results = self.pdf_processor.rename_temp_files_to_final(
                    temp_files, self.priority_engine, self.yymm_processor, user_yymm
                )
                
                # 一時ディレクトリクリーンアップ
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.debug_logger.log('WARNING', f"一時ディレクトリ削除失敗: {e}")
                
            elif file_ext == '.csv':
                # CSV処理（分割不要）
                result = self.process_csv_file(file_path, user_yymm)
                results.append(result)
            
            else:
                self.debug_logger.log('ERROR', f"サポートされていないファイル形式: {file_ext}")
                results.append({
                    'original_file': file_path,
                    'new_file': file_path,
                    'document_type': 'サポート外',
                    'processing_status': 'error'
                })
            
            return results
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"ファイル処理エラー: {e}")
            return [{
                'original_file': file_path,
                'new_file': file_path,
                'document_type': 'エラー',
                'processing_status': 'error'
            }]
    
    def process_csv_file(self, file_path: str, user_yymm: str = "") -> Dict:
        """CSV処理（v4.2継承）"""
        try:
            # CSV読み込み
            content, df = self.csv_processor.read_csv_with_encoding(file_path)
            
            if content is None:
                raise Exception("CSV読み込み失敗")
            
            filename = os.path.basename(file_path)
            
            # YYMM決定
            yymm = self.yymm_processor.determine_yymm(user_yymm, filename, content)
            
            # 文書種別判定
            doc_type, pattern = self.priority_engine.determine_document_type(
                content, filename, '.csv'
            )
            
            if pattern:
                # 最終ファイル名生成
                final_filename = pattern.format(yymm=yymm)
                final_path = os.path.join(os.path.dirname(file_path), final_filename)
                
                # リネーム実行
                shutil.move(file_path, final_path)
                
                return {
                    'original_file': file_path,
                    'new_file': final_path,
                    'document_type': doc_type,
                    'processing_status': 'success'
                }
            else:
                # 判定失敗
                fallback_filename = f"未分類_{yymm}.csv"
                fallback_path = os.path.join(os.path.dirname(file_path), fallback_filename)
                shutil.move(file_path, fallback_path)
                
                return {
                    'original_file': file_path,
                    'new_file': fallback_path,
                    'document_type': '不明',
                    'processing_status': 'fallback'
                }
                
        except Exception as e:
            self.debug_logger.log('ERROR', f"CSV処理エラー: {e}")
            return {
                'original_file': file_path,
                'new_file': file_path,
                'document_type': 'エラー',
                'processing_status': 'error'
            }
    
    def process_multiple_files(self, file_paths: List[str], user_yymm: str = "") -> List[Dict]:
        """複数ファイル処理（v4.4から継承）"""
        all_results = []
        
        try:
            self.debug_logger.log('INFO', f"=== 複数ファイル処理開始: {len(file_paths)}件 ===")
            
            for i, file_path in enumerate(file_paths, 1):
                self.debug_logger.log('INFO', f"--- ファイル {i}/{len(file_paths)}: {os.path.basename(file_path)} ---")
                
                # 個別ファイル処理
                file_results = self.process_single_file(file_path, user_yymm)
                all_results.extend(file_results)
                
            self.debug_logger.log('INFO', f"=== 複数ファイル処理完了: {len(all_results)}件処理 ===")
            return all_results
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"複数ファイル処理エラー: {e}")
            return all_results

class TaxDocumentRenamerApp:
    """税務書類リネームアプリケーション v4.5 分割・リネーム精密修正版"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("税務書類リネームシステム v4.5 分割・リネーム精密修正版")
        self.root.geometry("1200x800")
        
        # UI変数初期化
        self.yymm_var = tk.StringVar()
        self.selected_files = []
        
        # 地域設定変数（5セット）
        self.regional_vars = {}
        for i in range(1, 6):
            self.regional_vars[f'prefecture_{i}'] = tk.StringVar()
            self.regional_vars[f'city_{i}'] = tk.StringVar()
        
        # デバッグロガー初期化
        self.debug_logger = None
        
        # プロセッサー初期化
        self.processor = None
        
        # UI構築
        self.setup_ui()
        
        # 設定ファイル読み込み
        self.load_settings()
        
        self.debug_logger.log('INFO', "税務書類リネームシステム v4.5 起動完了")
        
    def setup_ui(self):
        """UI構築"""
        # ノートブックウィジェット
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # メインタブ
        self.setup_main_tab()
        
        # 結果一覧タブ
        self.setup_results_tab()
        
        # ログタブ
        self.setup_log_tab()
        
    def setup_main_tab(self):
        """メインタブ構築（v4.4統合版継承）"""
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
        
        # レイアウト
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # === 年月設定 ===
        yymm_frame = ttk.LabelFrame(scrollable_frame, text="年月設定")
        yymm_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(yymm_frame, text="年月(YYMM):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(yymm_frame, textvariable=self.yymm_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(yymm_frame, text="例: 2508", foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # === ファイル選択 ===
        file_frame = ttk.LabelFrame(scrollable_frame, text="ファイル選択")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # ファイル選択ボタン
        file_button_frame = ttk.Frame(file_frame)
        file_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_button_frame, text="複数ファイル選択", command=self.select_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_button_frame, text="クリア", command=self.clear_files).pack(side=tk.LEFT, padx=5)
        
        # ファイル一覧
        self.file_listbox = tk.Listbox(file_frame, height=5)
        self.file_listbox.pack(fill=tk.X, padx=5, pady=5)
        
        # === 地域設定 ===
        regional_frame = ttk.LabelFrame(scrollable_frame, text="地域設定（5セット）")
        regional_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 47都道府県リスト
        prefectures = [
            '', '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
            '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
            '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
            '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
            '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
            '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
            '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
        ]
        
        for i in range(1, 6):
            set_frame = ttk.Frame(regional_frame)
            set_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(set_frame, text=f"セット{i}:", width=8).pack(side=tk.LEFT, padx=5)
            
            pref_combo = ttk.Combobox(set_frame, 
                textvariable=self.regional_vars[f'prefecture_{i}'], 
                values=prefectures, width=12)
            pref_combo.pack(side=tk.LEFT, padx=5)
            
            ttk.Entry(set_frame, 
                textvariable=self.regional_vars[f'city_{i}'], 
                width=15).pack(side=tk.LEFT, padx=5)
        
        # === 処理実行 ===
        process_frame = ttk.Frame(scrollable_frame)
        process_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(process_frame, text="処理実行", command=self.start_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(process_frame, text="設定保存", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        
        # ステータス
        self.status_var = tk.StringVar(value="準備完了")
        ttk.Label(process_frame, textvariable=self.status_var).pack(side=tk.RIGHT, padx=5)
        
    def setup_results_tab(self):
        """結果一覧タブ"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="結果一覧")
        
        # 結果表示用Treeview
        columns = ('元ファイル名', '新ファイル名', '書類種別', '分割情報', '処理状況')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=150)
        
        # スクロールバー
        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # CSV出力ボタン
        export_frame = ttk.Frame(results_frame)
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(export_frame, text="結果をCSV出力", command=self.export_results).pack()
        
    def setup_log_tab(self):
        """ログタブ"""
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="ログ")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=100)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # デバッグロガー初期化（ログテキストウィジェット設定）
        self.debug_logger = DebugLogger(self.log_text)
        
    def select_files(self):
        """複数ファイル選択"""
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
            self.update_file_listbox()
            self.status_var.set(f"選択ファイル: {len(self.selected_files)}件")
    
    def clear_files(self):
        """ファイル選択クリア"""
        self.selected_files = []
        self.update_file_listbox()
        self.status_var.set("準備完了")
    
    def update_file_listbox(self):
        """ファイル一覧更新"""
        self.file_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(file_path))
    
    def start_processing(self):
        """処理開始"""
        if not self.selected_files:
            messagebox.showwarning("警告", "ファイルが選択されていません")
            return
        
        # 別スレッドで処理実行
        self.status_var.set("処理中...")
        processing_thread = threading.Thread(target=self.process_files)
        processing_thread.daemon = True
        processing_thread.start()
    
    def process_files(self):
        """ファイル処理メイン"""
        try:
            # 地域設定取得
            prefecture_selections = []
            city_selections = []
            
            for i in range(1, 6):
                pref = self.regional_vars[f'prefecture_{i}'].get()
                city = self.regional_vars[f'city_{i}'].get()
                prefecture_selections.append(pref)
                city_selections.append(city)
            
            # プロセッサー初期化
            self.processor = EnhancedProcessor(
                self.debug_logger, 
                prefecture_selections, 
                city_selections
            )
            
            # 複数ファイル処理
            results = self.processor.process_multiple_files(
                self.selected_files, 
                self.yymm_var.get()
            )
            
            # 結果表示更新
            self.root.after(0, lambda: self.update_results_display(results))
            self.root.after(0, lambda: self.status_var.set(f"処理完了: {len(results)}件"))
            
        except Exception as e:
            self.debug_logger.log('ERROR', f"処理エラー: {e}")
            self.root.after(0, lambda: self.status_var.set("処理エラー"))
    
    def update_results_display(self, results: List[Dict]):
        """結果表示更新"""
        # 既存項目クリア
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # 新結果追加
        for result in results:
            original_name = os.path.basename(result.get('original_file', ''))
            new_name = os.path.basename(result.get('new_file', ''))
            doc_type = result.get('document_type', '不明')
            split_info = result.get('split_info', '単一書類処理')
            status = result.get('processing_status', 'unknown')
            
            self.results_tree.insert('', 'end', values=(original_name, new_name, doc_type, split_info, status))
    
    def export_results(self):
        """結果CSV出力"""
        if not self.results_tree.get_children():
            messagebox.showinfo("情報", "出力する結果がありません")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSVファイル", "*.csv")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    # ヘッダー
                    writer.writerow(['元ファイル名', '新ファイル名', '書類種別', '分割情報', '処理状況'])
                    
                    # データ
                    for item in self.results_tree.get_children():
                        values = self.results_tree.item(item)['values']
                        writer.writerow(values)
                
                messagebox.showinfo("完了", f"結果をCSVファイルに出力しました:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"CSV出力エラー: {e}")
    
    def load_settings(self):
        """設定読み込み"""
        config_file = os.path.join(os.path.expanduser("~"), "TaxDocumentRenamer", "settings.txt")
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            if key in self.regional_vars:
                                self.regional_vars[key].set(value)
                            elif key == 'yymm':
                                self.yymm_var.set(value)
        except Exception as e:
            if self.debug_logger:
                self.debug_logger.log('WARNING', f"設定読み込みエラー: {e}")
    
    def save_settings(self):
        """設定保存"""
        config_dir = os.path.join(os.path.expanduser("~"), "TaxDocumentRenamer")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "settings.txt")
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(f"yymm={self.yymm_var.get()}\n")
                for key, var in self.regional_vars.items():
                    f.write(f"{key}={var.get()}\n")
            
            messagebox.showinfo("完了", "設定を保存しました")
            
        except Exception as e:
            messagebox.showerror("エラー", f"設定保存エラー: {e}")

def main():
    """メイン実行"""
    root = tk.Tk()
    app = TaxDocumentRenamerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
