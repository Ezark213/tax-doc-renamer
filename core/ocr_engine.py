#!/usr/bin/env python3
"""
OCR・自治体認識エンジン v4.0
高精度自治体名認識とマッチング機能
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import re
import io
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

@dataclass
class MunicipalityInfo:
    """自治体情報を表すデータクラス"""
    prefecture: Optional[str] = None
    municipality: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0
    position: Tuple[int, int, int, int] = (0, 0, 0, 0)

@dataclass
class MunicipalitySet:
    """手動入力自治体セット"""
    set_number: int
    prefecture: str
    municipality: str

class OCREngine:
    """OCR処理と自治体認識のメインクラス"""
    
    def __init__(self):
        """初期化"""
        # 自治体名認識パターン
        self.prefecture_patterns = [
            r'([^都道府県\s]{1,6}?)県[^税]*県税事務所',  # 愛知県東三河県税事務所
            r'([^都道府県\s]{1,6}?)都[^税]*都税事務所',  # 東京都港都税事務所
            r'([^都道府県\s]{1,6}?)県知事',
            r'([^都道府県\s]{1,6}?)都知事',
            r'([^都道府県\s]{1,6}?)府知事',
            r'([^都道府県\s]{1,6}?)道知事',
            r'([^都道府県\s]{1,6}?)県税事務所',
            r'([^都道府県\s]{1,6}?)都税事務所',
            r'([^都道府県\s]{1,6}?)県',
            r'([^都道府県\s]{1,6}?)都',
            r'([^都道府県\s]{1,6}?)府',
            r'([^都道府県\s]{1,6}?)道'
        ]
        
        self.municipality_patterns = [
            r'([^市町村区\s]{1,10}?)市長',
            r'([^市町村区\s]{1,10}?)町長',
            r'([^市町村区\s]{1,10}?)村長',
            r'([^市町村区\s]{1,10}?)区長',
            r'([^市町村区\s]{1,10}?)市',
            r'([^市町村区\s]{1,10}?)町',
            r'([^市町村区\s]{1,10}?)村',
            r'([^市町村区\s]{1,10}?)区'
        ]
        
        # OCR設定
        self.ocr_config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'

    def extract_municipality_from_pdf(self, pdf_path: str, page_num: int = 0) -> MunicipalityInfo:
        """PDFから自治体情報を抽出（強化版）"""
        try:
            doc = fitz.open(pdf_path)
            
            if page_num >= doc.page_count:
                doc.close()
                return MunicipalityInfo(raw_text="ページが存在しません")
            
            page = doc[page_num]
            
            # ページサイズを取得
            page_rect = page.rect
            
            print(f"DEBUG: OCR処理開始 - ページサイズ: {page_rect.width}x{page_rect.height}")
            
            # 中央上部エリアを定義（ページの上部1/3、左右中央2/3）
            crop_rect = fitz.Rect(
                page_rect.width * 0.17,  # 左端から17%
                0,                        # 上端
                page_rect.width * 0.83,   # 右端まで83%
                page_rect.height * 0.33   # 上部33%
            )
            
            print(f"DEBUG: OCR対象領域: ({crop_rect.x0}, {crop_rect.y0}, {crop_rect.x1}, {crop_rect.y1})")
            
            # 高解像度で画像として描画
            mat = fitz.Matrix(3.0, 3.0)  # 3倍に拡大（OCR精度向上）
            pix = page.get_pixmap(matrix=mat, clip=crop_rect)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # 画像前処理
            img = self._preprocess_image_for_ocr(img)
            
            doc.close()
            
            # OCR実行（複数の設定で試行）
            extracted_text = self._perform_enhanced_ocr(img)
            
            print(f"DEBUG: OCR抽出結果: '{extracted_text}'")
            
            # 自治体情報を解析
            municipality_info = self._parse_municipality_text(extracted_text)
            municipality_info.raw_text = extracted_text
            municipality_info.position = (crop_rect.x0, crop_rect.y0, crop_rect.x1, crop_rect.y1)
            
            print(f"DEBUG: 自治体認識結果 - 都道府県: {municipality_info.prefecture}, 市町村: {municipality_info.municipality}")
            
            return municipality_info
            
        except Exception as e:
            print(f"DEBUG: OCR処理エラー - {str(e)}")
            return MunicipalityInfo(raw_text=f"OCR処理エラー: {e}")

    def _preprocess_image_for_ocr(self, img: Image) -> Image:
        """OCR精度向上のための画像前処理"""
        try:
            # グレースケール変換
            img = img.convert('L')
            
            # コントラスト調整
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # 鮮明化
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)
            
            return img
        except Exception as e:
            print(f"DEBUG: 画像前処理エラー - {str(e)}")
            return img

    def _perform_enhanced_ocr(self, img: Image) -> str:
        """強化されたOCR処理"""
        ocr_configs = [
            '--psm 6 --oem 3',
            '--psm 7 --oem 3', 
            '--psm 8 --oem 3',
            '--psm 13 --oem 3'
        ]
        
        best_result = ""
        best_length = 0
        
        for config in ocr_configs:
            try:
                result = pytesseract.image_to_string(img, lang='jpn', config=config)
                if len(result.strip()) > best_length:
                    best_result = result
                    best_length = len(result.strip())
            except Exception as e:
                print(f"DEBUG: OCR設定 {config} でエラー - {str(e)}")
                continue
        
        return best_result

    def _parse_municipality_text(self, text: str) -> MunicipalityInfo:
        """抽出されたテキストから自治体情報を解析"""
        info = MunicipalityInfo()
        
        # テキストのクリーニング
        cleaned_text = re.sub(r'\s+', '', text)  # 空白を除去
        cleaned_text = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3400-\u4DBF]', '', cleaned_text)  # 日本語文字のみ
        
        # 都道府県名を抽出
        for pattern in self.prefecture_patterns:
            match = re.search(pattern, cleaned_text)
            if match:
                candidate = match.group(1)
                if self._is_valid_prefecture_name(candidate):
                    info.prefecture = candidate
                    info.confidence += 0.3
                    break
        
        # 市町村名を抽出
        for pattern in self.municipality_patterns:
            match = re.search(pattern, cleaned_text)
            if match:
                candidate = match.group(1)
                if self._is_valid_municipality_name(candidate):
                    info.municipality = candidate
                    info.confidence += 0.3
                    break
        
        # 信頼度調整
        if info.prefecture and info.municipality:
            info.confidence += 0.4
        
        return info

    def _is_valid_prefecture_name(self, name: str) -> bool:
        """都道府県名の妥当性をチェック"""
        if not name or len(name) < 2 or len(name) > 6:
            return False
            
        # 一般的な都道府県名パターン
        valid_prefectures = [
            '北海道', '青森', '岩手', '宮城', '秋田', '山形', '福島',
            '茨城', '栃木', '群馬', '埼玉', '千葉', '東京', '神奈川',
            '新潟', '富山', '石川', '福井', '山梨', '長野', '岐阜',
            '静岡', '愛知', '三重', '滋賀', '京都', '大阪', '兵庫',
            '奈良', '和歌山', '鳥取', '島根', '岡山', '広島', '山口',
            '徳島', '香川', '愛媛', '高知', '福岡', '佐賀', '長崎',
            '熊本', '大分', '宮崎', '鹿児島', '沖縄'
        ]
        
        return name in valid_prefectures

    def _is_valid_municipality_name(self, name: str) -> bool:
        """市町村名の妥当性をチェック"""
        if not name or len(name) < 1 or len(name) > 10:
            return False
            
        # 無効な文字パターンをチェック
        invalid_patterns = [
            r'^[0-9]+$',  # 数字のみ
            r'^[あいうえお]+$',  # ひらがな単体
            r'^[アイウエオ]+$',  # カタカナ単体
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, name):
                return False
        
        return True

    def extract_text(self, pdf_path: str) -> str:
        """
        v5.3互換: PDFからテキストを抽出
        """
        try:
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                return ""
            
            # 最初のページのみ処理
            page = doc[0]
            text = page.get_text()
            doc.close()
            
            return text or ""
        except Exception as e:
            print(f"[OCR] extract_text error: {e}")
            return ""
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        旧API互換: extract_textの別名
        """
        return self.extract_text(pdf_path)

class MunicipalityMatcher:
    """自治体名と手動入力セットのマッチング処理"""
    
    def __init__(self, input_sets: List[MunicipalitySet]):
        """初期化"""
        self.input_sets = input_sets
        self.ocr_engine = OCREngine()

    def match_prefecture(self, ocr_text: str, pdf_path: str = None) -> Optional[int]:
        """都道府県のマッチング"""
        # OCRから自治体情報を抽出（pdf_pathが提供された場合）
        if pdf_path:
            municipality_info = self.ocr_engine.extract_municipality_from_pdf(pdf_path)
            ocr_prefecture = municipality_info.prefecture
        else:
            # テキストから直接抽出
            municipality_info = self.ocr_engine._parse_municipality_text(ocr_text)
            ocr_prefecture = municipality_info.prefecture
        
        if not ocr_prefecture:
            return None
        
        # 手動入力セットとマッチング
        for i, muni_set in enumerate(self.input_sets):
            if self._is_prefecture_match(ocr_prefecture, muni_set.prefecture):
                return 1001 + (i * 10)  # 1001, 1011, 1021...
        
        return None

    def match_municipality(self, ocr_text: str, pdf_path: str = None) -> Optional[int]:
        """市町村のマッチング"""
        # OCRから自治体情報を抽出
        if pdf_path:
            municipality_info = self.ocr_engine.extract_municipality_from_pdf(pdf_path)
            ocr_municipality = municipality_info.municipality
        else:
            municipality_info = self.ocr_engine._parse_municipality_text(ocr_text)
            ocr_municipality = municipality_info.municipality
        
        if not ocr_municipality:
            return None
        
        # 手動入力セットとマッチング
        for i, muni_set in enumerate(self.input_sets):
            if self._is_municipality_match(ocr_municipality, muni_set.municipality):
                return 2001 + (i * 10)  # 2001, 2011, 2021...
        
        return None

    def _is_prefecture_match(self, ocr_prefecture: str, input_prefecture: str) -> bool:
        """都道府県名のマッチング判定"""
        if not ocr_prefecture or not input_prefecture:
            return False
        
        # 完全一致
        if ocr_prefecture == input_prefecture:
            return True
        
        # 部分一致（都道府県を除いた部分）
        ocr_base = re.sub(r'[都道府県]$', '', ocr_prefecture)
        input_base = re.sub(r'[都道府県]$', '', input_prefecture)
        
        if ocr_base == input_base and len(ocr_base) >= 2:
            return True
        
        return False

    def _normalize_municipality_name(self, name: str) -> str:
        """市町村名を正規化（表記ゆれ対応）"""
        if not name:
            return ""

        # 1. 市町村区を除去
        normalized = re.sub(r'[市町村区]$', '', name)

        # 2. 旧字体・異体字を新字体に統一
        kanji_variants = {
            '﨑': '崎',  # 崎の異体字
            '﨑': '崎',  # 別の崎の異体字
            '髙': '高',  # 高の異体字
            '﨔': '崎',  # 崎の異体字（別コードポイント）
            '嵜': '崎',  # 崎の別字
            '嶋': '島',  # 島の旧字
            '嶌': '島',  # 島の異体字
            '澤': '沢',  # 沢の旧字
            '濵': '浜',  # 浜の旧字
            '濱': '浜',  # 浜の異体字
            '邊': '辺',  # 辺の旧字
            '邉': '辺',  # 辺の異体字
            '舘': '館',  # 館の異体字
            '廣': '広',  # 広の旧字
            '櫻': '桜',  # 桜の旧字
            '斉': '斎',  # 斎の異体字
            '齋': '斎',  # 斎の旧字
            '鐵': '鉄',  # 鉄の旧字
            '澤': '沢',  # 沢の旧字
            '栁': '柳',  # 柳の異体字
            '萬': '万',  # 万の旧字
        }

        for old_char, new_char in kanji_variants.items():
            normalized = normalized.replace(old_char, new_char)

        # 3. 空白を除去
        normalized = normalized.replace(' ', '').replace('　', '')

        return normalized

    def _is_municipality_match(self, ocr_municipality: str, input_municipality: str) -> bool:
        """市町村名のマッチング判定（表記ゆれ対応強化版）"""
        if not ocr_municipality or not input_municipality:
            return False

        # 完全一致
        if ocr_municipality == input_municipality:
            return True

        # 正規化してマッチング
        ocr_normalized = self._normalize_municipality_name(ocr_municipality)
        input_normalized = self._normalize_municipality_name(input_municipality)

        # 正規化後の完全一致
        if ocr_normalized == input_normalized and len(ocr_normalized) >= 1:
            return True

        # 正規化後の部分一致（前方一致）
        if ocr_normalized and input_normalized:
            if (ocr_normalized.startswith(input_normalized) or
                input_normalized.startswith(ocr_normalized)) and len(min(ocr_normalized, input_normalized)) >= 2:
                return True

        return False

    def get_best_match(self, pdf_path: str) -> Dict[str, Optional[int]]:
        """最適なマッチング結果を取得"""
        municipality_info = self.ocr_engine.extract_municipality_from_pdf(pdf_path)
        
        prefecture_code = None
        municipality_code = None
        
        if municipality_info.prefecture:
            prefecture_code = self.match_prefecture("", pdf_path)
            
        if municipality_info.municipality:
            municipality_code = self.match_municipality("", pdf_path)
        
        return {
            'prefecture_code': prefecture_code,
            'municipality_code': municipality_code,
            'ocr_info': municipality_info,
            'confidence': municipality_info.confidence
        }

class CompanyNameMatcher:
    """会社名マッチングクラス（受信通知とフォルダの紐付け）"""

    def __init__(self):
        """初期化"""
        # 会社名正規化用の記号・文字マッピング
        self.normalize_map = {
            # 法人格表記の統一
            '株式会社': '',
            '(株)': '',
            '（株）': '',
            '有限会社': '',
            '(有)': '',
            '（有）': '',
            '合同会社': '',
            '(同)': '',
            '（同）': '',
            '一般社団法人': '',
            '一般財団法人': '',
            '医療法人': '',
            '社会福祉法人': '',
            '学校法人': '',
            # 全角・半角統一
            'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J',
            'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T',
            'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y', 'Ｚ': 'Z',
            'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
            'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o', 'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r', 'ｓ': 's', 'ｔ': 't',
            'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y', 'ｚ': 'z',
            '０': '0', '１': '1', '２': '2', '３': '3', '４': '4', '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
            '－': '-', '‐': '-', '‑': '-', '‒': '-', '–': '-', '—': '-', '―': '-',
            # 旧字体・異体字を新字体に統一（市町村名正規化と同じ）
            '﨑': '崎', '髙': '高', '嶋': '島', '澤': '沢', '濵': '浜', '濱': '浜',
            '邊': '辺', '邉': '辺', '舘': '館', '廣': '広', '櫻': '桜', '斉': '斎',
            '齋': '斎', '鐵': '鉄', '栁': '柳', '萬': '万',
        }

        # OCR設定（既存OCREngineと同じ）
        self.ocr_config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'

    def extract_company_name_from_folder(self, folder_name: str) -> Optional[str]:
        """
        フォルダ名から会社名を抽出

        フォルダ名形式: YYMM_接頭辞_帳票名_顧問先番号_顧問先名/
        例: 2511_01_給与所得・退職所得等の所得税徴収高計算書(一般)_0413K0063_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ/

        Args:
            folder_name: フォルダ名

        Returns:
            抽出された会社名（正規化前）、失敗時はNone
        """
        if not folder_name:
            return None

        # パターン: YYMM_接頭辞_帳票名_顧問先番号_顧問先名
        # 最後のアンダースコア以降が会社名
        pattern = r'^(?:\d{4})_(?:\d{2,4})_[^_]+_[^_]+_(.+?)/?$'
        match = re.match(pattern, folder_name)

        if match:
            company_name = match.group(1)
            return company_name

        return None

    def extract_company_name_from_receipt(self, pdf_path: str, page_num: int = 0) -> Optional[str]:
        """
        受信通知PDFから会社名をOCR抽出

        Args:
            pdf_path: 受信通知PDFのパス
            page_num: ページ番号（0始まり）

        Returns:
            抽出された会社名（正規化前）、失敗時はNone
        """
        try:
            doc = fitz.open(pdf_path)

            if page_num >= doc.page_count:
                doc.close()
                return None

            page = doc[page_num]
            page_rect = page.rect

            # 会社名は中央エリアに記載されている想定（ページの中央40%、上部50%）
            crop_rect = fitz.Rect(
                page_rect.width * 0.30,   # 左端から30%
                page_rect.height * 0.15,  # 上端から15%
                page_rect.width * 0.70,   # 右端まで70%
                page_rect.height * 0.65   # 上部65%まで
            )

            # 高解像度で画像として描画
            mat = fitz.Matrix(3.0, 3.0)
            pix = page.get_pixmap(matrix=mat, clip=crop_rect)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # 画像前処理（既存OCREngineのメソッドを流用）
            ocr_engine = OCREngine()
            img = ocr_engine._preprocess_image_for_ocr(img)

            # OCR実行
            ocr_text = pytesseract.image_to_string(img, lang='jpn', config=self.ocr_config)

            doc.close()

            # 会社名抽出パターン
            company_patterns = [
                r'([^\s]{2,30}?)(?:様|殿|御中)',  # "株式会社ABC様"
                r'([^\s]{2,30}?)(?:\s*納税者)',    # "株式会社ABC 納税者"
                r'([^\s]{2,30}?)(?:\s*宛)',        # "株式会社ABC 宛"
            ]

            for pattern in company_patterns:
                matches = re.findall(pattern, ocr_text)
                if matches:
                    # 最初にマッチした会社名を返す
                    company_name = matches[0].strip()
                    return company_name

            return None

        except Exception as e:
            print(f"ERROR: 受信通知OCR失敗: {pdf_path} page={page_num}, error={e}")
            return None

    def normalize_company_name(self, company_name: str) -> str:
        """
        会社名を正規化

        Args:
            company_name: 正規化前の会社名

        Returns:
            正規化後の会社名
        """
        if not company_name:
            return ""

        normalized = company_name

        # 1. マッピングテーブルによる置換
        for old_char, new_char in self.normalize_map.items():
            normalized = normalized.replace(old_char, new_char)

        # 2. 空白・記号を除去
        normalized = re.sub(r'[\s\u3000\-－‐‑‒–—―・]', '', normalized)

        # 3. 小文字に統一
        normalized = normalized.lower()

        return normalized

    def match_folder(self, receipt_company_name: str, folder_names: List[str],
                     threshold: float = 0.7) -> Optional[Tuple[str, float]]:
        """
        受信通知の会社名に最も近いフォルダを検索

        Args:
            receipt_company_name: 受信通知から抽出した会社名
            folder_names: フォルダ名のリスト
            threshold: マッチング閾値（0.0-1.0）

        Returns:
            (マッチしたフォルダ名, 類似度スコア) または None
        """
        if not receipt_company_name or not folder_names:
            return None

        # 受信通知の会社名を正規化
        receipt_normalized = self.normalize_company_name(receipt_company_name)

        if not receipt_normalized:
            return None

        best_match = None
        best_score = 0.0

        for folder_name in folder_names:
            # フォルダ名から会社名を抽出
            folder_company = self.extract_company_name_from_folder(folder_name)

            if not folder_company:
                continue

            # 正規化
            folder_normalized = self.normalize_company_name(folder_company)

            if not folder_normalized:
                continue

            # スコア計算
            # 1. 完全一致
            if receipt_normalized == folder_normalized:
                return (folder_name, 1.0)

            # 2. 部分一致（前方・後方）
            if receipt_normalized in folder_normalized or folder_normalized in receipt_normalized:
                # 共通部分の長さでスコア計算
                common_length = min(len(receipt_normalized), len(folder_normalized))
                max_length = max(len(receipt_normalized), len(folder_normalized))
                score = common_length / max_length

                if score > best_score:
                    best_score = score
                    best_match = folder_name

        # 閾値以上のスコアのみ返す
        if best_match and best_score >= threshold:
            return (best_match, best_score)

        return None


if __name__ == "__main__":
    # テスト用
    ocr_engine = OCREngine()
    print("OCR・自治体認識エンジン v4.0 初期化完了")