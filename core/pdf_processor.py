#!/usr/bin/env python3
"""
PDF分割・処理エンジン v5.2
国税・地方税受信通知の自動分割機能 + 束ねPDF限定オート分割
"""

import fitz  # PyMuPDF
import os
import re
import yaml
import logging
from typing import List, Optional, Dict, Tuple, Union, Callable
from dataclasses import dataclass
from pathlib import Path
from pypdf import PdfReader, PdfWriter

@dataclass
class SplitResult:
    """分割結果を表すデータクラス"""
    filename: str
    pages: List[int]
    content_type: str
    success: bool
    error_message: Optional[str] = None

@dataclass
class PageContent:
    """ページ内容解析結果"""
    page_num: int
    text: str
    is_blank: bool
    keywords: List[str]

@dataclass
class BundleDetectionResult:
    """束ねPDF判定結果"""
    is_bundle: bool
    bundle_type: Optional[str]  # "local" or "national"
    confidence: float
    matched_elements: Dict[str, List[str]]  # {"receipt": [...], "payment": [...], "codes": [...]}
    debug_info: List[str]

# v5.2 Bundle detection constants
BUNDLE_SCAN_PAGES = 10
LOCAL_CODES = {"1003", "1013", "1023", "1004", "2003", "2013", "2023", "2004"}
NATIONAL_NOTICE = {"0003", "3003"}
NATIONAL_PAYMENT = {"0004", "3004"}

class PDFProcessor:
    """PDF分割・処理のメインクラス v5.2"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """初期化"""
        self.logger = logger or logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_split_config()
        
        # v5.1 existing keywords (preserved)
        self.national_tax_keywords = {
            "法人税_受信通知": ["法人税", "受信通知", "国税電子申告"],
            "法人税_納付情報": ["法人税", "納付情報", "納付書"],
            "消費税_受信通知": ["消費税", "受信通知", "国税電子申告"],
            "消費税_納付情報": ["消費税", "納付情報", "納付書"]
        }
        
        self.local_tax_keywords = {
            "都道府県_受信通知1": ["都道府県", "受信通知", "法人事業税"],
            "都道府県_受信通知2": ["都道府県", "受信通知", "法人県民税"],
            "都道府県_納付情報": ["都道府県", "納付情報", "納付書"],
            "市町村_受信通知1": ["市町村", "法人市民税", "受信通知"],
            "市町村_受信通知2": ["市町村", "法人市民税", "受信通知"],
            "市町村_受信通知3": ["市町村", "法人市民税", "受信通知"],
            "市町村_納付情報": ["市町村", "納付情報", "納付書"]
        }

    def _load_split_config(self) -> Dict:
        """分割設定ファイルを読み込み"""
        try:
            config_path = Path(__file__).parent.parent / "resources" / "split_rules.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # Fallback default config
                return self._get_default_config()
        except Exception as e:
            if self.logger:
                self.logger.warning(f"設定ファイル読み込みエラー、デフォルト設定を使用: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """デフォルト設定を返す"""
        return {
            "bundle_detection": {
                "scan_pages": 10,
                "thresholds": {"receipt_notifications": 1, "payment_info": 1, "target_codes": 1}
            },
            "target_codes": {
                "local_tax": {
                    "receipt_notifications": ["1003", "1013", "1023", "2003", "2013", "2023"],
                    "payment_info": ["1004", "2004"]
                },
                "national_tax": {
                    "receipt_notifications": ["0003", "3003"],
                    "payment_info": ["0004", "3004"]
                }
            },
            "keywords": {
                "receipt_notification": ["受信通知", "申告受付完了通知", "受信結果"],
                "payment_info": ["納付情報", "納付区分番号通知", "納付書"],
                "tax_categories": {
                    "national": ["法人税", "消費税", "国税電子申告"],
                    "local": ["都道府県", "市町村", "地方税電子申告"]
                }
            }
        }

    def analyze_pdf_content(self, pdf_path: str) -> List[PageContent]:
        """PDFの全ページを解析"""
        try:
            doc = fitz.open(pdf_path)
            pages_content = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                # 空白ページ判定
                is_blank = len(text.strip()) < 50
                
                # キーワード抽出
                keywords = self._extract_keywords(text)
                
                pages_content.append(PageContent(
                    page_num=page_num,
                    text=text,
                    is_blank=is_blank,
                    keywords=keywords
                ))
            
            doc.close()
            return pages_content
            
        except Exception as e:
            print(f"PDF解析エラー: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        keywords = []
        text_lower = text.lower()
        
        # 主要キーワードのチェック
        key_phrases = [
            "法人税", "消費税", "受信通知", "納付情報", "納付書",
            "都道府県", "市町村", "法人事業税", "法人県民税", "法人市民税",
            "国税電子申告", "地方税電子申告"
        ]
        
        for phrase in key_phrases:
            if phrase in text:
                keywords.append(phrase)
                
        return keywords

    def is_national_tax_notification_bundle(self, pdf_path: str) -> bool:
        """国税受信通知一式かどうかを判定"""
        pages_content = self.analyze_pdf_content(pdf_path)
        
        # 4書類+空白ページの典型的パターンをチェック
        if len(pages_content) < 4:
            return False
            
        # 必要なキーワードの存在確認
        all_text = " ".join([p.text for p in pages_content if not p.is_blank])
        
        required_patterns = [
            ("法人税", "受信通知"),
            ("法人税", "納付情報"),
            ("消費税", "受信通知"),
            ("消費税", "納付情報")
        ]
        
        matches = 0
        for pattern in required_patterns:
            if all(keyword in all_text for keyword in pattern):
                matches += 1
                
        return matches >= 3  # 4つ中3つ以上マッチすれば該当とみなす

    def is_local_tax_notification_bundle(self, pdf_path: str) -> bool:
        """地方税受信通知一式かどうかを判定"""
        pages_content = self.analyze_pdf_content(pdf_path)
        
        if len(pages_content) < 5:  # 最低5ページは必要
            return False
            
        all_text = " ".join([p.text for p in pages_content if not p.is_blank])
        
        # 地方税特有のキーワード確認
        local_tax_keywords = [
            "都道府県", "市町村", "法人事業税", "法人県民税", "法人市民税"
        ]
        
        matches = sum(1 for keyword in local_tax_keywords if keyword in all_text)
        return matches >= 3

    def split_national_tax_notifications(self, pdf_path: str, output_dir: str, year_month: str = "YYMM") -> List[SplitResult]:
        """国税受信通知一式を4つに分割（完全再実装）"""
        split_results = []
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            
            print(f"DEBUG: 国税受信通知分割開始 - 総ページ数: {total_pages}")
            
            # 空白ページを除外して有効ページを特定
            valid_pages = []
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text().strip()
                if len(text) > 50:  # 50文字以上を有効ページとみなす
                    valid_pages.append(page_num)
            
            print(f"DEBUG: 有効ページ: {valid_pages}")
            
            # 固定の4分割を実行（最初の4ページ）
            if len(valid_pages) >= 4:
                split_configs = [
                    {"page": valid_pages[0], "code": "0003", "name": "受信通知_法人税", "type": "法人税_受信通知"},
                    {"page": valid_pages[1], "code": "0004", "name": "納付情報_法人税", "type": "法人税_納付情報"},
                    {"page": valid_pages[2], "code": "3003", "name": "受信通知_消費税", "type": "消費税_受信通知"},
                    {"page": valid_pages[3], "code": "3004", "name": "納付情報_消費税", "type": "消費税_納付情報"}
                ]
                
                for config in split_configs:
                    page_num = config["page"]
                    
                    # 1ページのPDFを作成
                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    
                    # ファイル名生成
                    output_filename = f"{config['code']}_{config['name']}_{year_month}.pdf"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 保存前に空白ページチェック
                    if self._is_blank_page_content(new_doc[0]):
                        print(f"DEBUG: 空白ページのためスキップ - {output_filename} (ページ{page_num})")
                        new_doc.close()
                        continue
                    
                    # 保存
                    new_doc.save(output_path)
                    new_doc.close()
                    
                    # 保存後に追加で空白チェック（確実な削除のため）
                    if self._is_blank_saved_file(output_path):
                        print(f"DEBUG: 保存後空白ファイル削除 - {output_filename}")
                        try:
                            os.remove(output_path)
                            continue
                        except Exception as e:
                            print(f"DEBUG: ファイル削除エラー - {e}")
                    
                    print(f"DEBUG: 分割完了 - {output_filename} (ページ{page_num})")
                    
                    split_results.append(SplitResult(
                        filename=output_filename,
                        pages=[page_num],
                        content_type=config['type'],
                        success=True
                    ))
            else:
                return [SplitResult("", [], "error", False, f"有効ページが不足: {len(valid_pages)}ページ（4ページ必要）")]
            
            doc.close()
            
            # 空白ページを削除した結果をフィルタリング
            valid_results = [result for result in split_results if result.success]
            print(f"DEBUG: 最終結果 - 有効ファイル数: {len(valid_results)}")
            
            return valid_results
            
        except Exception as e:
            print(f"DEBUG: 国税分割エラー - {str(e)}")
            return [SplitResult("", [], "error", False, f"分割処理エラー: {e}")]

    def _identify_national_tax_splits(self, pages_content: List[PageContent]) -> List[Dict]:
        """国税受信通知の分割ポイントを特定"""
        splits = []
        current_pages = []
        current_type = None
        
        for i, page in enumerate(pages_content):
            if page.is_blank:
                continue
                
            # ページ内容による書類種別判定
            page_type = self._classify_national_tax_page(page)
            
            if page_type != current_type and current_pages:
                # 前の書類を完成
                if current_type:
                    splits.append({
                        'pages': current_pages.copy(),
                        'type': current_type,
                        'code': self._get_national_tax_code(current_type),
                        'name': self._get_national_tax_name(current_type)
                    })
                current_pages = [i]
                current_type = page_type
            else:
                current_pages.append(i)
        
        # 最後の書類
        if current_type and current_pages:
            splits.append({
                'pages': current_pages,
                'type': current_type,
                'code': self._get_national_tax_code(current_type),
                'name': self._get_national_tax_name(current_type)
            })
            
        return splits

    def _classify_national_tax_page(self, page: PageContent) -> str:
        """国税書類ページの種別を分類"""
        text = page.text.lower()
        
        if "法人税" in text and "受信通知" in text:
            return "法人税_受信通知"
        elif "法人税" in text and ("納付" in text or "納税" in text):
            return "法人税_納付情報"
        elif "消費税" in text and "受信通知" in text:
            return "消費税_受信通知"
        elif "消費税" in text and ("納付" in text or "納税" in text):
            return "消費税_納付情報"
        else:
            return "unknown"

    def _get_national_tax_code(self, doc_type: str) -> str:
        """国税書類の分類コードを取得"""
        codes = {
            "法人税_受信通知": "0003",
            "法人税_納付情報": "0004",
            "消費税_受信通知": "3003",
            "消費税_納付情報": "3004"
        }
        return codes.get(doc_type, "0000")

    def _get_national_tax_name(self, doc_type: str) -> str:
        """国税書類の名称を取得"""
        names = {
            "法人税_受信通知": "受信通知_法人税",
            "法人税_納付情報": "納付情報_法人税",
            "消費税_受信通知": "受信通知_消費税",
            "消費税_納付情報": "納付情報_消費税"
        }
        return names.get(doc_type, "unknown")

    def split_local_tax_notifications(self, pdf_path: str, output_dir: str, year_month: str = "YYMM") -> List[SplitResult]:
        """地方税受信通知一式を1ページごとに分割（完全再実装）"""
        split_results = []
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            
            print(f"DEBUG: 地方税受信通知分割開始 - 総ページ数: {total_pages}")
            
            # 全ページを1ページずつ分割
            prefecture_notification_count = 0
            municipality_notification_count = 0
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text().strip()
                
                # 空白ページをスキップ
                if len(text) < 50:
                    print(f"DEBUG: ページ{page_num}をスキップ（空白ページ）")
                    continue
                
                # ページ内容による分類
                page_type = self._classify_local_tax_page(text)
                
                if page_type == "都道府県_納付情報":
                    code = "1004"
                    name = "納付情報_都道府県"
                elif page_type == "市町村_納付情報":
                    code = "2004"
                    name = "納付情報_市町村"
                elif page_type == "都道府県_受信通知":
                    # 連番生成: 1003, 1013, 1023, 1033...
                    code = f"10{3 + prefecture_notification_count * 10:02d}"
                    name = "受信通知_都道府県"
                    prefecture_notification_count += 1
                elif page_type == "市町村_受信通知":
                    # 連番生成: 2003, 2013, 2023, 2033...
                    code = f"20{3 + municipality_notification_count * 10:02d}"
                    name = "受信通知_市町村"
                    municipality_notification_count += 1
                else:
                    # デフォルト：受信通知として処理
                    if "都道府県" in text or "県" in text:
                        code = f"10{3 + prefecture_notification_count * 10:02d}"
                        name = "受信通知_都道府県"
                        prefecture_notification_count += 1
                    else:
                        code = f"20{3 + municipality_notification_count * 10:02d}"
                        name = "受信通知_市町村"
                        municipality_notification_count += 1
                
                # 1ページのPDFを作成
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                # ファイル名生成
                output_filename = f"{code}_{name}_{year_month}.pdf"
                output_path = os.path.join(output_dir, output_filename)
                
                # 保存前に空白ページチェック
                if self._is_blank_page_content(new_doc[0]):
                    print(f"DEBUG: 空白ページのためスキップ - {output_filename} (ページ{page_num})")
                    new_doc.close()
                    continue
                
                # 保存
                new_doc.save(output_path)
                new_doc.close()
                
                # 保存後に追加で空白チェック（確実な削除のため）
                if self._is_blank_saved_file(output_path):
                    print(f"DEBUG: 保存後空白ファイル削除 - {output_filename}")
                    try:
                        os.remove(output_path)
                        continue
                    except Exception as e:
                        print(f"DEBUG: ファイル削除エラー - {e}")
                
                print(f"DEBUG: 分割完了 - {output_filename} (ページ{page_num}, 種別: {page_type})")
                
                split_results.append(SplitResult(
                    filename=output_filename,
                    pages=[page_num],
                    content_type=page_type,
                    success=True
                ))
            
            doc.close()
            
            # 空白ページを削除した結果をフィルタリング
            valid_results = [result for result in split_results if result.success]
            print(f"DEBUG: 最終結果 - 有効ファイル数: {len(valid_results)}")
            
            return valid_results
            
        except Exception as e:
            print(f"DEBUG: 地方税分割エラー - {str(e)}")
            return [SplitResult("", [], "error", False, f"地方税分割処理エラー: {e}")]

    def _classify_local_tax_page(self, text: str) -> str:
        """地方税ページの種別を分類"""
        text_lower = text.lower()
        
        if "納付情報" in text or "納付書" in text:
            if "都道府県" in text or "県税" in text or "事業税" in text:
                return "都道府県_納付情報"
            elif "市町村" in text or "市民税" in text or "市長" in text:
                return "市町村_納付情報"
            else:
                return "都道府県_納付情報"  # デフォルト
        else:
            # 受信通知
            if "都道府県" in text or "県税" in text or "事業税" in text or "県知事" in text:
                return "都道府県_受信通知"
            elif "市町村" in text or "市民税" in text or "市長" in text:
                return "市町村_受信通知"
            else:
                return "都道府県_受信通知"  # デフォルト

    def _identify_local_tax_splits(self, pages_content: List[PageContent]) -> List[Dict]:
        """地方税受信通知の分割ポイントを特定"""
        splits = []
        
        # 簡単な実装（実際にはより複雑な判定が必要）
        prefecture_notification_1 = []
        prefecture_notification_2 = []
        prefecture_payment = []
        municipality_notification_1 = []
        municipality_notification_2 = []
        municipality_notification_3 = []
        municipality_payment = []
        
        for i, page in enumerate(pages_content):
            if page.is_blank:
                continue
                
            text = page.text.lower()
            
            # 簡易的な分類（実際にはより精密な判定が必要）
            if "都道府県" in text and "受信通知" in text:
                if len(prefecture_notification_1) == 0:
                    prefecture_notification_1.append(i)
                elif len(prefecture_notification_2) == 0:
                    prefecture_notification_2.append(i)
            elif "都道府県" in text and "納付" in text:
                prefecture_payment.append(i)
            elif "市町村" in text and "受信通知" in text:
                if len(municipality_notification_1) == 0:
                    municipality_notification_1.append(i)
                elif len(municipality_notification_2) == 0:
                    municipality_notification_2.append(i)
                elif len(municipality_notification_3) == 0:
                    municipality_notification_3.append(i)
            elif "市町村" in text and "納付" in text:
                municipality_payment.append(i)
        
        # 分割結果を構築
        local_splits = [
            {'pages': prefecture_notification_1, 'code': '1003', 'name': '受信通知_都道府県', 'type': '都道府県_受信通知1'},
            {'pages': prefecture_notification_2, 'code': '1013', 'name': '受信通知_都道府県', 'type': '都道府県_受信通知2'},
            {'pages': prefecture_payment, 'code': '1004', 'name': '納付情報_都道府県', 'type': '都道府県_納付情報'},
            {'pages': municipality_notification_1, 'code': '2003', 'name': '受信通知_市町村', 'type': '市町村_受信通知1'},
            {'pages': municipality_notification_2, 'code': '2013', 'name': '受信通知_市町村', 'type': '市町村_受信通知2'},
            {'pages': municipality_notification_3, 'code': '2023', 'name': '受信通知_市町村', 'type': '市町村_受信通知3'},
            {'pages': municipality_payment, 'code': '2004', 'name': '納付情報_市町村', 'type': '市町村_納付情報'}
        ]
        
        return [split for split in local_splits if split['pages']]
    
    def _is_blank_page_content(self, page) -> bool:
        """ページの中身が空白か判定する（税務書類特化チェック）"""
        try:
            # テキスト抽出
            text = page.get_text().strip()
            
            print(f"DEBUG: ページチェック - テキスト長: {len(text)} 文字")
            print(f"DEBUG: テキスト内容サンプル: {text[:100]}..." if len(text) > 100 else f"DEBUG: テキスト全体: {text}")
            
            # 文字数チェック（非常に厳しい基準）
            if len(text) < 50:
                print("DEBUG: 文字数不足で空白判定")
                return True
            
            # 税務書類特化の重要キーワードチェック
            essential_tax_keywords = [
                # 申告関連
                "申告受付完了通知",
                "申告受付完了",
                "申告受付",
                "受付完了通知",
                "受付完了",
                # 納付関連
                "納付情報発行結果",
                "納付情報発行",
                "納付情報",
                "納付書",
                "納付金額",
                # メール関連
                "メール詳細",
                "納付区分番号通知",
                "納付区分番号",
                # 受信関連
                "受信通知",
                "受信結果",
                "受信",
                # 税目関連
                "法人税",
                "消費税",
                "地方法人税",
                "都道府県民税",
                "市町村民税",
                "事業税",
                # 金額関連
                "税額",
                "金額",
                "円",
                # 日付関連
                "年月日",
                "期限",
                # 会社情報
                "住所",
                "所在地",
                "名称",
                "代表者",
                # 其他重要キーワード
                "電子申告",
                "Ｅ－Ｔａｘ",
                "税務署"
            ]
            
            # キーワードマッチング
            matched_keywords = []
            for keyword in essential_tax_keywords:
                if keyword in text:
                    matched_keywords.append(keyword)
            
            print(f"DEBUG: マッチしたキーワード: {matched_keywords}")
            
            # 重要キーワードが一つもない場合は空白と判定
            if not matched_keywords:
                print("DEBUG: 重要キーワードがないため空白判定")
                return True
            
            print(f"DEBUG: 有効なコンテンツと判定 - マッチ数: {len(matched_keywords)}")
            return False
            
        except Exception as e:
            print(f"DEBUG: ページ空白チェックエラー - {e}")
            return False
    
    def _is_blank_saved_file(self, file_path: str) -> bool:
        """保存済みファイルが空白か判定する（税務書類特化）"""
        try:
            if not os.path.exists(file_path):
                print(f"DEBUG: ファイルが存在しない: {file_path}")
                return True
                
            # ファイルサイズチェック（税務書類の最低サイズを考慮）
            file_size = os.path.getsize(file_path)
            print(f"DEBUG: ファイルサイズチェック: {file_size} bytes - {file_path}")
            
            # 10KB未満は空白の可能性が高い（より緩い基準）
            if file_size < 10000:  # 10KB未満
                print(f"DEBUG: ファイルサイズが小さいため詳細チェック実行: {file_size} bytes")
                
                # PDFを開いて中身を再チェック
                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    print("DEBUG: ページ数が0のため空白判定")
                    doc.close()
                    return True
                    
                page = doc[0]
                is_blank = self._is_blank_page_content(page)
                doc.close()
                
                if is_blank:
                    print(f"DEBUG: 中身チェックで空白判定: {file_path}")
                else:
                    print(f"DEBUG: 中身チェックで有効判定: {file_path}")
                
                return is_blank
            else:
                print(f"DEBUG: ファイルサイズが十分なため有効判定: {file_size} bytes")
                return False
            
        except Exception as e:
            print(f"DEBUG: 保存ファイル空白チェックエラー - {e}")
            # エラーの場合は安全のため削除しない
            return False

    # ===== v5.2 New Bundle Detection and Auto-Split Methods =====
    
    def maybe_split_pdf(self, input_pdf_path: str, out_dir: str, force: bool = False, 
                       processing_callback: Optional[Callable] = None) -> bool:
        """
        Bundle PDF Auto-Split Main Function
        束ねPDF限定オート分割のメイン関数
        
        Args:
            input_pdf_path: 入力PDFのパス
            out_dir: 出力ディレクトリ
            force: 強制分割フラグ (判定結果を無視して分割実行)
            processing_callback: 分割後各ページの処理コールバック関数
            
        Returns:
            bool: 分割実行された場合True、対象外や失敗の場合False
        """
        self.logger.info(f"[split] Bundle detection started: {os.path.basename(input_pdf_path)}")
        
        try:
            # Step 1: Bundle detection
            detection_result = self._detect_bundle_type(input_pdf_path)
            
            if not detection_result.is_bundle and not force:
                self.logger.info(f"[split] Skip (non-bundle): {os.path.basename(input_pdf_path)}")
                self.logger.debug(f"[split] Detection details: {detection_result.debug_info}")
                return False
            
            bundle_type = detection_result.bundle_type or "unknown"
            self.logger.info(f"[split] Bundle detected: type={bundle_type}, confidence={detection_result.confidence:.2f}")
            
            if force and not detection_result.is_bundle:
                self.logger.info(f"[split] Force split enabled - proceeding despite non-bundle detection")
                
            # Step 2: Full page splitting
            return self._execute_bundle_split(input_pdf_path, out_dir, bundle_type, processing_callback)
            
        except Exception as e:
            self.logger.error(f"[split] Bundle split error: {input_pdf_path} - {e}")
            return False
    
    def _detect_bundle_type(self, pdf_path: str) -> BundleDetectionResult:
        """
        束ねPDFの種別を判定
        
        Args:
            pdf_path: PDFファイルのパス
            
        Returns:
            BundleDetectionResult: 判定結果
        """
        debug_info = []
        matched_elements = {"receipt": [], "payment": [], "codes": []}
        
        try:
            # Quick sample scan using PyMuPDF (fast mode)
            doc = fitz.open(pdf_path)
            scan_pages = min(doc.page_count, self.config["bundle_detection"]["scan_pages"])
            
            sample_texts = []
            for i in range(scan_pages):
                page = doc[i]
                text = page.get_text()
                sample_texts.append(text)
                debug_info.append(f"Page {i+1}: {len(text)} chars")
            
            doc.close()
            
            # Combine all sample text
            combined_text = " ".join(sample_texts)
            debug_info.append(f"Combined sample text: {len(combined_text)} chars")
            
            # Check for local tax bundle
            local_result = self._is_bundle_local(sample_texts, matched_elements, debug_info)
            if local_result:
                return BundleDetectionResult(
                    is_bundle=True,
                    bundle_type="local",
                    confidence=0.9,
                    matched_elements=matched_elements,
                    debug_info=debug_info
                )
            
            # Check for national tax bundle
            national_result = self._is_bundle_national(sample_texts, matched_elements, debug_info)
            if national_result:
                return BundleDetectionResult(
                    is_bundle=True,
                    bundle_type="national", 
                    confidence=0.9,
                    matched_elements=matched_elements,
                    debug_info=debug_info
                )
                
            return BundleDetectionResult(
                is_bundle=False,
                bundle_type=None,
                confidence=0.0,
                matched_elements=matched_elements,
                debug_info=debug_info
            )
            
        except Exception as e:
            debug_info.append(f"Detection error: {e}")
            return BundleDetectionResult(
                is_bundle=False,
                bundle_type=None,
                confidence=0.0,
                matched_elements=matched_elements,
                debug_info=debug_info
            )
    
    def _is_bundle_local(self, texts: List[str], matched_elements: Dict, debug_info: List[str]) -> bool:
        """地方税束ね判定 - OCR内容ベースの書類判定"""
        from .classification_v5 import DocumentClassifierV5
        
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            local_target_codes = ["1003", "1013", "1023", "1004", "2003", "2013", "2023", "2004"]  # 地方税対象コード
            detected_pages = []
            
            debug_info.append(f"OCR-based local bundle detection started for {len(texts)} pages")
            
            # 各ページを個別にOCR分析して書類判定
            for i, page_text in enumerate(texts):
                if len(page_text.strip()) < 50:  # 空白ページスキップ
                    continue
                
                # ページごとの書類コード推定
                detected_code = classifier.detect_page_doc_code(page_text, prefer_bundle="local")
                
                if detected_code in local_target_codes:
                    detected_pages.append((i+1, detected_code))
                    matched_elements["codes"].append(f"Page{i+1}:{detected_code}")
                    debug_info.append(f"Page {i+1}: detected target code {detected_code}")
                else:
                    debug_info.append(f"Page {i+1}: no target code (detected: {detected_code})")
            
            # Bundle判定: 2枚以上の対象書類が含まれている場合
            is_bundle = len(detected_pages) >= 2
            
            if is_bundle:
                # 受信通知と納付情報の両方があるかチェック
                receipt_codes = [code for page, code in detected_pages if code in ["1003", "1013", "1023", "2003", "2013", "2023"]]
                payment_codes = [code for page, code in detected_pages if code in ["1004", "2004"]]
                
                matched_elements["receipt"].extend([f"Page{p}:{c}" for p, c in detected_pages if c in ["1003", "1013", "1023", "2003", "2013", "2023"]])
                matched_elements["payment"].extend([f"Page{p}:{c}" for p, c in detected_pages if c in ["1004", "2004"]])
                
                debug_info.append(f"Local bundle detected: {len(detected_pages)} target pages")
                debug_info.append(f"Receipt pages: {len(receipt_codes)}, Payment pages: {len(payment_codes)}")
            else:
                debug_info.append(f"Not a local bundle: only {len(detected_pages)} target pages found (need ≥2)")
            
            return is_bundle
            
        except Exception as e:
            debug_info.append(f"Local bundle detection error: {e}")
            return False
    
    def _is_bundle_national(self, texts: List[str], matched_elements: Dict, debug_info: List[str]) -> bool:
        """国税束ね判定 - OCR内容ベースの書類判定"""
        from .classification_v5 import DocumentClassifierV5
        
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            national_target_codes = ["0003", "3003", "0004", "3004"]  # 国税対象コード
            detected_pages = []
            
            debug_info.append(f"OCR-based national bundle detection started for {len(texts)} pages")
            
            # 各ページを個別にOCR分析して書類判定
            for i, page_text in enumerate(texts):
                if len(page_text.strip()) < 50:  # 空白ページスキップ
                    continue
                
                # ページごとの書類コード推定
                detected_code = classifier.detect_page_doc_code(page_text, prefer_bundle="national")
                
                if detected_code in national_target_codes:
                    detected_pages.append((i+1, detected_code))
                    matched_elements["codes"].append(f"Page{i+1}:{detected_code}")
                    debug_info.append(f"Page {i+1}: detected target code {detected_code}")
                else:
                    debug_info.append(f"Page {i+1}: no target code (detected: {detected_code})")
            
            # Bundle判定: 2枚以上の対象書類が含まれている場合
            is_bundle = len(detected_pages) >= 2
            
            if is_bundle:
                # 受信通知と納付情報の両方があるかチェック
                receipt_codes = [code for page, code in detected_pages if code in ["0003", "3003"]]
                payment_codes = [code for page, code in detected_pages if code in ["0004", "3004"]]
                
                matched_elements["receipt"].extend([f"Page{p}:{c}" for p, c in detected_pages if c in ["0003", "3003"]])
                matched_elements["payment"].extend([f"Page{p}:{c}" for p, c in detected_pages if c in ["0004", "3004"]])
                
                debug_info.append(f"National bundle detected: {len(detected_pages)} target pages")
                debug_info.append(f"Receipt pages: {len(receipt_codes)}, Payment pages: {len(payment_codes)}")
            else:
                debug_info.append(f"Not a national bundle: only {len(detected_pages)} target pages found (need ≥2)")
            
            return is_bundle
            
        except Exception as e:
            debug_info.append(f"National bundle detection error: {e}")
            return False
    
    def _execute_bundle_split(self, input_pdf_path: str, out_dir: str, bundle_type: str,
                             processing_callback: Optional[Callable] = None) -> bool:
        """
        束ねPDFの実際の分割処理を実行
        
        Args:
            input_pdf_path: 入力PDFパス
            out_dir: 出力ディレクトリ
            bundle_type: 束ね種別 ("local", "national", "unknown")
            processing_callback: 各ページ処理後のコールバック関数
            
        Returns:
            bool: 分割成功した場合True
        """
        try:
            # Use pypdf for splitting
            reader = PdfReader(input_pdf_path)
            total_pages = len(reader.pages)
            
            self.logger.info(f"[split] Executing split: {total_pages} pages, type={bundle_type}")
            
            temp_files = []
            
            for i, page in enumerate(reader.pages, start=1):
                # Create single-page PDF
                writer = PdfWriter()
                writer.add_page(page)
                
                # Generate unique temporary filename with timestamp
                import time
                timestamp = int(time.time() * 1000000)  # microsecond precision
                temp_pattern = self.config.get("output", {}).get("temp_file_pattern", "__split_{page:03d}_{timestamp}.pdf")
                temp_filename = temp_pattern.format(page=i, timestamp=timestamp + i)
                temp_path = os.path.join(out_dir, temp_filename)
                
                # Write temporary file
                with open(temp_path, "wb") as output_file:
                    writer.write(output_file)
                
                temp_files.append(temp_path)
                
                # Log page split with hint from classification if available
                from .classification_v5 import DocumentClassifierV5
                try:
                    classifier = DocumentClassifierV5(debug_mode=False)
                    # Get text from page for classification hint
                    doc = fitz.open(temp_path)
                    page_text = doc[0].get_text()
                    doc.close()
                    
                    code_hint = classifier.detect_page_doc_code(page_text, prefer_bundle=bundle_type)
                    self.logger.debug(f"[split] Page {i:03d}: hint={code_hint}")
                except Exception as e:
                    self.logger.debug(f"[split] Page {i:03d}: classification hint failed - {e}")
                
                # Call processing callback if provided (integrates with existing pipeline)
                if processing_callback:
                    try:
                        processing_callback(temp_path, i, bundle_type)
                    except Exception as e:
                        self.logger.error(f"[split] Processing callback error for page {i}: {e}")
            
            # Cleanup temporary files if configured
            if self.config.get("output", {}).get("auto_cleanup_temp", True):
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception as e:
                        self.logger.warning(f"[split] Cleanup warning: {temp_file} - {e}")
            
            self.logger.info(f"[split] Split completed: {input_pdf_path} -> {total_pages} pages (bundle={bundle_type})")
            return True
            
        except Exception as e:
            self.logger.error(f"[split] Split execution error: {e}")
            return False

if __name__ == "__main__":
    # テスト用
    processor = PDFProcessor()
    print("PDF分割処理エンジン v5.2 初期化完了")