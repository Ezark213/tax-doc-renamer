"""
Receipt Detector Module - 受信通知PDF判定モジュール

v7.2.3で実装されたマルチパターン受信通知検出ロジックを保持します。
このモジュールは、Phase D-1でmain.pyから分離されました。

判定パターン:
1. 給与支払報告/償却資産: 「申告受付完了通知」かつ「送信された申告データを受付けました」
2. 源泉税: 「メール詳細」かつ「送信されたデータを受け付けました」
"""

from typing import Optional
import fitz  # PyMuPDF


class ReceiptDetector:
    """
    受信通知PDF判定クラス

    v7.2.3で実装された受信通知検出ロジックをそのまま保持します。
    PDFファイルの1ページ目のテキストを抽出し、特定のキーワードパターンで
    受信通知かどうかを判定します。

    重要: このロジックはv7.2.3で修正・検証済みのため、変更してはいけません。
    """

    # 判定パターン定義
    PATTERN_PAYROLL_DEPRECIATION = {
        "keyword1": "申告受付完了通知",
        "keyword2": "送信された申告データを受付けました",
        "type": "payroll_depreciation"
    }

    PATTERN_GENSEN = {
        "keyword1": "メール詳細",
        "keyword2": "送信されたデータを受け付けました",
        "type": "gensen"
    }

    @staticmethod
    def is_receipt_pdf(file_path: str) -> bool:
        """
        PDFファイルが受信通知かどうかをテキスト抽出で判定

        v7.2.3のmain.py:4456-4483の_is_receipt_pdfメソッドと同一ロジック。

        判定条件:
        1. 給与支払報告/償却資産: 「申告受付完了通知」かつ「送信された申告データを受付けました」
        2. 源泉税: 「メール詳細」かつ「送信された」（空白・改行・表記ゆれ対応）

        Args:
            file_path: PDF完全パス

        Returns:
            True: 受信通知PDF, False: 通常PDF

        Raises:
            なし（例外は内部でキャッチしFalseを返す）
        """
        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                first_page_text = doc[0].get_text()
                doc.close()

                # 空白・改行を正規化（全て削除）
                import re
                normalized_text = re.sub(r'\s+', '', first_page_text)

                # パターン1: 給与支払報告/償却資産の受信通知
                if "申告受付完了通知" in normalized_text and "送信された申告データを受付けました" in normalized_text:
                    return True

                # パターン2: 源泉税の受信通知（条件緩和）
                # 「メール詳細」かつ「送信された」が含まれていればOK
                if "メール詳細" in normalized_text and "送信された" in normalized_text:
                    return True
            else:
                doc.close()
            return False
        except Exception as e:
            # v7.2.3ではself._logを使っていたが、静的メソッドなので例外情報は記録しない
            # 上位レイヤーで必要に応じてログ出力する
            return False

    @staticmethod
    def get_receipt_type(file_path: str) -> Optional[str]:
        """
        受信通知のタイプを返す

        is_receipt_pdfの判定ロジックを拡張し、どのパターンに一致したかを返します。

        Args:
            file_path: PDF完全パス

        Returns:
            "payroll_depreciation": 給与支払報告/償却資産の受信通知
            "gensen": 源泉税の受信通知
            None: 受信通知でない

        Raises:
            なし（例外は内部でキャッチしNoneを返す）
        """
        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                first_page_text = doc[0].get_text()
                doc.close()

                # 空白・改行を正規化（全て削除）
                import re
                normalized_text = re.sub(r'\s+', '', first_page_text)

                # パターン1: 給与支払報告/償却資産の受信通知
                if "申告受付完了通知" in normalized_text and "送信された申告データを受付けました" in normalized_text:
                    return "payroll_depreciation"

                # パターン2: 源泉税の受信通知（条件緩和）
                if "メール詳細" in normalized_text and "送信された" in normalized_text:
                    return "gensen"
            else:
                doc.close()
            return None
        except Exception:
            return None

    @staticmethod
    def get_detection_details(file_path: str) -> dict:
        """
        受信通知判定の詳細情報を返す（デバッグ・テスト用）

        Args:
            file_path: PDF完全パス

        Returns:
            dict: {
                "is_receipt": bool,
                "receipt_type": Optional[str],
                "detected_keywords": List[str],
                "first_page_text_length": int,
                "error": Optional[str]
            }
        """
        result = {
            "is_receipt": False,
            "receipt_type": None,
            "detected_keywords": [],
            "first_page_text_length": 0,
            "error": None
        }

        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                first_page_text = doc[0].get_text()
                doc.close()

                result["first_page_text_length"] = len(first_page_text)

                # 空白・改行を正規化（全て削除）
                import re
                normalized_text = re.sub(r'\s+', '', first_page_text)

                # キーワード検出
                keywords_found = []

                # パターン1チェック
                if "申告受付完了通知" in normalized_text:
                    keywords_found.append("申告受付完了通知")
                if "送信された申告データを受付けました" in normalized_text:
                    keywords_found.append("送信された申告データを受付けました")

                # パターン2チェック
                if "メール詳細" in normalized_text:
                    keywords_found.append("メール詳細")
                if "送信された" in normalized_text:
                    keywords_found.append("送信された")

                result["detected_keywords"] = keywords_found

                # パターン判定
                if "申告受付完了通知" in normalized_text and "送信された申告データを受付けました" in normalized_text:
                    result["is_receipt"] = True
                    result["receipt_type"] = "payroll_depreciation"
                elif "メール詳細" in normalized_text and "送信された" in normalized_text:
                    result["is_receipt"] = True
                    result["receipt_type"] = "gensen"
            else:
                doc.close()
        except Exception as e:
            result["error"] = str(e)

        return result


# モジュールレベルの便利関数
def is_receipt(file_path: str) -> bool:
    """
    受信通知判定の便利関数

    Args:
        file_path: PDF完全パス

    Returns:
        True: 受信通知PDF, False: 通常PDF
    """
    return ReceiptDetector.is_receipt_pdf(file_path)


def get_type(file_path: str) -> Optional[str]:
    """
    受信通知タイプ取得の便利関数

    Args:
        file_path: PDF完全パス

    Returns:
        "payroll_depreciation" / "gensen" / None
    """
    return ReceiptDetector.get_receipt_type(file_path)
