#!/usr/bin/env python3
"""
CSV処理エンジン v4.0
仕訳帳・会計帳簿CSVファイルの完全対応
"""

import pandas as pd
import csv
import chardet
import os
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CSVProcessResult:
    """CSV処理結果を表すデータクラス"""
    filename: str
    document_type: str
    year_month: str
    success: bool
    row_count: int = 0
    columns: List[str] = None
    error_message: Optional[str] = None

class CSVProcessor:
    """CSV処理の完全対応クラス"""
    
    def __init__(self):
        """初期化"""
        # CSV書類分類パターン
        self.csv_patterns = {
            '5005_仕訳帳': {
                'filename_patterns': [r'仕訳帳', r'journal', r'仕訳'],
                'column_patterns': [
                    ['日付', '借方科目', '貸方科目', '金額'],
                    ['date', 'debit', 'credit', 'amount'],
                    ['伝票番号', '日付', '借方', '貸方']
                ],
                'content_keywords': ['借方', '貸方', '仕訳', '日付', '科目']
            },
            '5002_総勘定元帳': {
                'filename_patterns': [r'総勘定元帳', r'general.*ledger', r'元帳'],
                'column_patterns': [
                    ['日付', '科目', '借方', '貸方', '残高'],
                    ['date', 'account', 'debit', 'credit', 'balance'],
                    ['勘定科目', '日付', '摘要', '金額']
                ],
                'content_keywords': ['勘定科目', '総勘定', '残高', '科目', '元帳']
            },
            '5004_残高試算表': {
                'filename_patterns': [r'残高試算表', r'trial.*balance', r'試算表'],
                'column_patterns': [
                    ['科目', '借方残高', '貸方残高'],
                    ['account', 'debit_balance', 'credit_balance'],
                    ['勘定科目', '当月借方', '当月貸方', '残高']
                ],
                'content_keywords': ['残高', '試算表', '借方残高', '貸方残高', '科目']
            },
            '5003_補助元帳': {
                'filename_patterns': [r'補助元帳', r'subsidiary.*ledger', r'補助'],
                'column_patterns': [
                    ['日付', '補助科目', '借方', '貸方'],
                    ['date', 'sub_account', 'debit', 'credit'],
                    ['補助科目', '摘要', '金額']
                ],
                'content_keywords': ['補助元帳', '補助科目', '補助', '元帳']
            }
        }

    def detect_encoding(self, file_path: str) -> str:
        """ファイルエンコーディングを自動検出"""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # 最初の10KBを読み取り
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                
                # 日本語ファイルの一般的なエンコーディングに補正
                if encoding in ['Shift_JIS', 'cp932']:
                    return 'cp932'
                elif encoding in ['UTF-8', 'utf-8']:
                    return 'utf-8'
                elif encoding in ['EUC-JP', 'euc-jp']:
                    return 'euc-jp'
                else:
                    return 'cp932'  # デフォルトはcp932
                    
        except Exception:
            return 'cp932'  # 検出失敗時のデフォルト

    def read_csv_safely(self, file_path: str) -> Tuple[Optional[pd.DataFrame], str]:
        """CSVファイルを安全に読み込み"""
        encoding = self.detect_encoding(file_path)
        
        # 複数の読み込み方法を試行
        read_methods = [
            # 方法1: pandas with detected encoding
            lambda: pd.read_csv(file_path, encoding=encoding),
            
            # 方法2: pandas with different encodings
            lambda: pd.read_csv(file_path, encoding='cp932'),
            lambda: pd.read_csv(file_path, encoding='utf-8'),
            lambda: pd.read_csv(file_path, encoding='shift_jis'),
            
            # 方法3: pandas with error handling
            lambda: pd.read_csv(file_path, encoding=encoding, on_bad_lines='skip'),
            lambda: pd.read_csv(file_path, encoding='cp932', on_bad_lines='skip'),
            
            # 方法4: custom separator detection
            lambda: pd.read_csv(file_path, encoding=encoding, sep=None, engine='python'),
            
            # 方法5: manual CSV reading
            lambda: self._read_csv_manual(file_path, encoding)
        ]
        
        for i, method in enumerate(read_methods):
            try:
                df = method()
                if df is not None and not df.empty:
                    return df, f"成功: 方法{i+1}"
            except Exception as e:
                continue
        
        return None, "全ての読み込み方法が失敗しました"

    def _read_csv_manual(self, file_path: str, encoding: str) -> pd.DataFrame:
        """手動CSVリーダー（最後の手段）"""
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                # CSVの区切り文字を自動検出
                sample = file.read(1024)
                file.seek(0)
                
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                # データを読み込み
                reader = csv.reader(file, delimiter=delimiter)
                data = list(reader)
                
                if data:
                    # DataFrameに変換
                    if len(data) > 1:
                        df = pd.DataFrame(data[1:], columns=data[0])
                    else:
                        df = pd.DataFrame(data)
                    return df
                    
        except Exception as e:
            raise e
        
        return pd.DataFrame()

    def classify_csv_by_filename(self, filename: str) -> Optional[str]:
        """ファイル名による分類"""
        filename_lower = filename.lower()
        
        for doc_type, patterns in self.csv_patterns.items():
            for pattern in patterns['filename_patterns']:
                if re.search(pattern, filename_lower):
                    return doc_type
        
        return None

    def classify_csv_by_content(self, df: pd.DataFrame) -> Optional[str]:
        """CSV内容による分類"""
        if df.empty:
            return None
        
        # カラム名を取得（小文字化）
        columns = [str(col).lower() for col in df.columns]
        
        # 内容の一部を取得（文字列化）
        content_sample = ""
        for col in df.columns:
            content_sample += " ".join(df[col].astype(str).head(10).tolist())
        content_sample = content_sample.lower()
        
        best_match = None
        best_score = 0
        
        for doc_type, patterns in self.csv_patterns.items():
            score = 0
            
            # カラムパターンのマッチング
            for column_pattern in patterns['column_patterns']:
                pattern_matches = sum(1 for pattern_col in column_pattern 
                                    if any(pattern_col.lower() in col for col in columns))
                if pattern_matches > 0:
                    score += pattern_matches * 2
            
            # キーワードマッチング
            keyword_matches = sum(1 for keyword in patterns['content_keywords']
                                if keyword in content_sample)
            score += keyword_matches
            
            if score > best_score:
                best_score = score
                best_match = doc_type
        
        return best_match if best_score > 2 else None

    def extract_year_month_from_csv(self, file_path: str, df: pd.DataFrame) -> str:
        """CSVから年月を抽出"""
        # 1. ファイル名から抽出
        filename = os.path.basename(file_path)
        
        # YYYYMMDD形式を探す
        date_patterns = [
            r'(\d{4})(\d{2})\d{2}',  # YYYYMMDD
            r'(\d{4})-(\d{2})-\d{2}',  # YYYY-MM-DD
            r'(\d{4})/(\d{2})/\d{2}',  # YYYY/MM/DD
            r'(\d{2})(\d{2})\d{2}',    # YYMMDD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                year = match.group(1)
                month = match.group(2)
                
                # 4桁年を2桁に変換
                if len(year) == 4:
                    year = year[2:]
                
                return f"{year}{month}"
        
        # 2. CSV内容から抽出
        if not df.empty:
            date_columns = []
            for col in df.columns:
                if any(keyword in str(col).lower() for keyword in ['日付', 'date', '年月']):
                    date_columns.append(col)
            
            for col in date_columns:
                try:
                    # 最初の有効な日付を取得
                    for value in df[col].dropna().head(10):
                        value_str = str(value)
                        for pattern in date_patterns:
                            match = re.search(pattern, value_str)
                            if match:
                                year = match.group(1)
                                month = match.group(2)
                                if len(year) == 4:
                                    year = year[2:]
                                return f"{year}{month}"
                except Exception:
                    continue
        
        return "YYMM"  # デフォルト値

    def process_csv(self, file_path: str) -> CSVProcessResult:
        """CSV処理のメイン処理"""
        filename = os.path.basename(file_path)
        
        try:
            # CSV読み込み
            df, read_status = self.read_csv_safely(file_path)
            
            if df is None:
                return CSVProcessResult(
                    filename=filename,
                    document_type="unknown",
                    year_month="YYMM",
                    success=False,
                    error_message=f"CSV読み込み失敗: {read_status}"
                )
            
            # 書類分類
            doc_type = self.classify_csv_by_filename(filename)
            if not doc_type:
                doc_type = self.classify_csv_by_content(df)
            
            if not doc_type:
                doc_type = "5005_仕訳帳"  # デフォルト
            
            # 年月抽出
            year_month = self.extract_year_month_from_csv(file_path, df)
            
            return CSVProcessResult(
                filename=filename,
                document_type=doc_type,
                year_month=year_month,
                success=True,
                row_count=len(df),
                columns=list(df.columns),
                error_message=None
            )
            
        except Exception as e:
            return CSVProcessResult(
                filename=filename,
                document_type="unknown",
                year_month="YYMM",
                success=False,
                error_message=f"CSV処理エラー: {str(e)}"
            )

    def generate_csv_filename(self, result: CSVProcessResult) -> str:
        """CSVファイルの新しいファイル名を生成"""
        if not result.success:
            return result.filename
        
        # 書類分類コードから名称を抽出
        doc_code = result.document_type.split('_')[0]
        doc_name = result.document_type.split('_', 1)[1] if '_' in result.document_type else "unknown"
        
        # 拡張子を保持
        original_ext = os.path.splitext(result.filename)[1]
        
        return f"{doc_code}_{doc_name}_{result.year_month}{original_ext}"

if __name__ == "__main__":
    # テスト用
    processor = CSVProcessor()
    print("CSV処理エンジン v4.0 初期化完了")