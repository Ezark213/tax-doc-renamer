#!/usr/bin/env python3
"""
PDF分割・処理エンジン v4.0
国税・地方税受信通知の自動分割機能
"""

import fitz  # PyMuPDF
import os
import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

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

class PDFProcessor:
    """PDF分割・処理のメインクラス"""
    
    def __init__(self):
        """初期化"""
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
                    
                    # 保存
                    new_doc.save(output_path)
                    new_doc.close()
                    
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
            return split_results
            
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
                
                # 保存
                new_doc.save(output_path)
                new_doc.close()
                
                print(f"DEBUG: 分割完了 - {output_filename} (ページ{page_num}, 種別: {page_type})")
                
                split_results.append(SplitResult(
                    filename=output_filename,
                    pages=[page_num],
                    content_type=page_type,
                    success=True
                ))
            
            doc.close()
            return split_results
            
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

if __name__ == "__main__":
    # テスト用
    processor = PDFProcessor()
    print("PDF分割処理エンジン v4.0 初期化完了")