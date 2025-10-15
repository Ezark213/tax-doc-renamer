#!/usr/bin/env python3
"""
会社名マッチングモジュール
受信通知とフォルダの紐付け処理
"""

import fitz  # PyMuPDF
import re
import os
from typing import List, Optional, Tuple


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
            # 旧字体・異体字を新字体に統一
            '﨑': '崎', '髙': '高', '嶋': '島', '澤': '沢', '濵': '浜', '濱': '浜',
            '邊': '辺', '邉': '辺', '舘': '館', '廣': '広', '櫻': '桜', '斉': '斎',
            '齋': '斎', '鐵': '鉄', '栁': '柳', '萬': '万',
        }

    def extract_company_name_from_folder(self, folder_name: str) -> Optional[str]:
        """
        フォルダ名から会社名を抽出

        フォルダ名形式: YYMM_帳票名_会社名/
        例: 2501_給与所得・退職所得等の所得税徴収高計算書(一般)_株式会社Ｘ－Ｒｅｇｕｌａｔｉｏｎ/

        Args:
            folder_name: フォルダ名

        Returns:
            抽出された会社名（正規化前）、失敗時はNone
        """
        if not folder_name:
            return None

        # パターン: YYMM_帳票名_会社名
        # 最後のアンダースコア以降が会社名
        pattern = r'^(?:\d{4})_[^_]+_(.+?)/?$'
        match = re.match(pattern, folder_name)

        if match:
            company_name = match.group(1)
            return company_name

        return None

    def extract_company_name_from_receipt(self, pdf_path: str, page_num: int = 0) -> Optional[str]:
        """
        受信通知PDFから会社名をテキスト抽出（OCR不要）

        受信通知PDFはテキストベースの電子フォームのため、
        OCRではなくPyMuPDFのget_text()で直接抽出する。
        これにより100%の精度と高速処理を実現。

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

            # テキストを直接抽出（OCR不要）
            text = page.get_text()

            doc.close()

            # 会社名抽出パターン（受信通知専用）
            company_patterns = [
                r'氏名又は名称\s+(.+?)(?:\n|代表者)',  # "氏名又は名称 むかしむかし株式会社"
                r'氏名又は名称\s*\n\s*(.+?)(?:\n|$)',  # 改行がある場合
            ]

            for pattern in company_patterns:
                match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
                if match:
                    company_name = match.group(1).strip()
                    return company_name

            return None

        except Exception as e:
            print(f"ERROR: 受信通知テキスト抽出失敗: {pdf_path} page={page_num}, error={e}")
            return None

    def extract_amount_from_main_pdf(self, pdf_path: str) -> Optional[int]:
        """
        本表PDFから金額を抽出（LINE-BASED）

        Args:
            pdf_path: 本表PDFのパス

        Returns:
            抽出された金額（整数）、失敗時はNone
        """
        try:
            doc = fitz.open(pdf_path)

            if doc.page_count == 0:
                doc.close()
                return None

            page = doc[0]
            text = page.get_text()
            doc.close()

            # 方法1: キーワードベースの抽出
            patterns = [
                (r'納付税額[^\d]*([\d\s,]+)', '納付税額'),
                (r'本税[^\d]*([\d\s,]+)', '本税'),
                (r'納付すべき税額[^\d]*([\d\s,]+)', '納付すべき税額'),
                (r'差引納付税額[^\d]*([\d\s,]+)', '差引納付税額'),
            ]

            for pattern, label in patterns:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    amount_str = match.group(1).replace(',', '').replace(' ', '').replace('\u3000', '')
                    if len(amount_str) >= 3:
                        try:
                            amount = int(amount_str)
                            if amount > 0:
                                print(f"DEBUG: 本表金額抽出成功: {amount:,}円 (パターン: {label})")
                                return amount
                        except ValueError:
                            continue

            # 方法2: 行ベースの金額抽出（フォールバック）
            all_amounts = []
            for line in text.split('\n'):
                # カンマを含む行のみ処理
                if ',' in line:
                    cleaned = line.replace(',', '').replace(' ', '').replace('\u3000', '').strip()
                    if cleaned.isdigit() and len(cleaned) >= 3:
                        amount = int(cleaned)
                        if 100 <= amount <= 100000000:  # 100円〜1億円の範囲
                            all_amounts.append(amount)

            if all_amounts:
                # 重複する金額があれば、それを返す（通常、納付税額は繰り返し表示される）
                from collections import Counter
                counter = Counter(all_amounts)
                most_common = counter.most_common(1)
                if most_common and most_common[0][1] >= 2:  # 2回以上出現
                    amount = most_common[0][0]
                    print(f"DEBUG: 本表金額抽出成功（重複パターン）: {amount:,}円 (出現回数: {most_common[0][1]})")
                    return amount

                # 重複がなければ最後の金額を返す
                amount = all_amounts[-1]
                print(f"DEBUG: 本表金額抽出成功（最終金額）: {amount:,}円")
                return amount

            print(f"WARNING: 本表金額抽出失敗: {os.path.basename(pdf_path)}")
            print(f"DEBUG: テキスト抽出（最初の500文字）:\n{text[:500]}")
            return None

        except Exception as e:
            print(f"ERROR: 本表金額抽出失敗: {pdf_path}, error={e}")
            return None

    def extract_amount_from_receipt(self, pdf_path: str, page_num: int) -> Optional[int]:
        """
        受信通知PDFから金額を抽出（IMPROVED-PATTERN）

        Args:
            pdf_path: 受信通知PDFのパス
            page_num: ページ番号（0始まり）

        Returns:
            抽出された金額（整数）、失敗時はNone
        """
        try:
            doc = fitz.open(pdf_path)

            if page_num >= doc.page_count:
                doc.close()
                return None

            page = doc[page_num]
            text = page.get_text()
            doc.close()

            # 金額抽出パターン（空白を考慮）
            patterns = [
                (r'合計金額[^\d]*([\d\s,]+)', '合計金額'),
                (r'納付金額[^\d]*([\d\s,]+)', '納付金額'),
                (r'納付税額[^\d]*([\d\s,]+)', '納付税額'),
                (r'納付すべき税額[^\d]*([\d\s,]+)', '納付すべき税額'),
                (r'本税[^\d]*([\d\s,]+)', '本税'),
            ]

            for pattern, label in patterns:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    amount_str = match.group(1)
                    # 空白とカンマを除去
                    amount_str_cleaned = amount_str.replace(',', '').replace(' ', '').replace('\u3000', '')

                    # 3桁以上の数字のみ（誤抽出防止）
                    if len(amount_str_cleaned) >= 3:
                        try:
                            amount = int(amount_str_cleaned)
                            if amount > 0:  # 0円は無効
                                print(f"DEBUG: 受信通知金額抽出成功: {amount:,}円 (パターン: {label})")
                                return amount
                        except ValueError:
                            continue

            print(f"WARNING: 受信通知金額抽出失敗: {os.path.basename(pdf_path)} page={page_num}")
            print(f"DEBUG: テキスト抽出（最初の500文字）:\n{text[:500]}")
            return None

        except Exception as e:
            print(f"ERROR: 受信通知金額抽出失敗: {pdf_path} page={page_num}, error={e}")
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

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        2つの文字列の類似度を計算（0.0～1.0）

        Args:
            str1: 比較文字列1（正規化済み）
            str2: 比較文字列2（正規化済み）

        Returns:
            類似度スコア（0.0～1.0）
        """
        if not str1 or not str2:
            return 0.0

        # 完全一致
        if str1 == str2:
            return 1.0

        # 部分一致チェック
        if str1 in str2 or str2 in str1:
            # 短い方の文字列の長さを基準に類似度を計算
            shorter = min(len(str1), len(str2))
            longer = max(len(str1), len(str2))
            return shorter / longer

        # Levenshtein距離ベースの類似度計算
        distance = self._levenshtein_distance(str1, str2)
        max_len = max(len(str1), len(str2))

        if max_len == 0:
            return 0.0

        # 類似度 = 1 - (編集距離 / 最大長)
        similarity = 1.0 - (distance / max_len)
        return max(0.0, similarity)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Levenshtein距離（編集距離）を計算

        Args:
            s1: 文字列1
            s2: 文字列2

        Returns:
            編集距離
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # 挿入、削除、置換のコストを計算
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def match_all_folders(self, receipt_company_name: str, folder_names: List[str],
                          threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        受信通知の会社名にマッチするすべてのフォルダを検索

        同じ会社の複数フォルダに対応するため、閾値以上のすべてのフォルダを返す

        Args:
            receipt_company_name: 受信通知から抽出した会社名
            folder_names: フォルダ名のリスト
            threshold: マッチング閾値（0.0-1.0）

        Returns:
            [(フォルダ名, 類似度スコア), ...] のリスト（スコア降順）
        """
        if not receipt_company_name or not folder_names:
            return []

        # 受信通知の会社名を正規化
        receipt_normalized = self.normalize_company_name(receipt_company_name)

        if not receipt_normalized:
            return []

        matches = []

        for folder_name in folder_names:
            # フォルダ名から会社名を抽出
            folder_company = self.extract_company_name_from_folder(folder_name)

            if not folder_company:
                continue

            # フォルダ会社名を正規化
            folder_normalized = self.normalize_company_name(folder_company)

            if not folder_normalized:
                continue

            # 類似度計算
            score = self.calculate_similarity(receipt_normalized, folder_normalized)

            if score >= threshold:
                matches.append((folder_name, score))

        # スコア降順でソート
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

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
