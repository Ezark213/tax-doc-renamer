"""
地方税PDF テキスト抽出検証ツール - Debug Local Tax PDF Detection

このスクリプトは、地方税PDFのテキスト抽出と1003/1004検出ロジックを検証します。
Priority 1: ログ拡充による原因特定の一環として作成されました。

使用方法:
    python debug_local_tax_detection.py <PDF_FILE_PATH>

出力:
    - 各ページのテキスト抽出結果
    - キーワード検出状況
    - DocumentClassifierV5による分類結果
    - Bundle判定結果
"""

import sys
import os
from pathlib import Path
import fitz  # PyMuPDF

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.classification_v5 import DocumentClassifierV5


def analyze_pdf(pdf_path: str):
    """PDFファイルを解析してテキスト抽出と分類結果を表示"""

    if not os.path.exists(pdf_path):
        print(f"[ERROR] Error: File not found: {pdf_path}")
        return

    print("=" * 80)
    print(f"地方税PDF テキスト抽出検証")
    print(f"File: {pdf_path}")
    print("=" * 80)

    try:
        # PDFを開く
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        print(f"\n[PDF] Total pages: {num_pages}\n")

        # ClassifierV5を初期化
        classifier = DocumentClassifierV5(debug_mode=True)

        # 地方税bundle検出対象コード
        local_target_codes = ["1003", "1013", "1023", "1004", "2003", "2013", "2023", "2004"]

        # キーワード定義
        receipt_keywords = ["受信通知", "申告受付完了通知", "申告受付完了", "受付完了通知"]
        payment_keywords = ["納付情報", "納付区分番号通知", "納付書", "納付情報発行結果"]
        pref_keywords = ["都道府県", "県税事務所", "都税事務所", "法人事業税", "特別法人事業税",
                        "法人県民税", "法人道府県民税", "法人市民税"]
        specific_local_keywords = ["地方税ポータル", "eLTAX", "eltax"]

        detected_pages = []

        # 各ページを解析
        for page_num in range(num_pages):
            page = doc[page_num]
            page_text = page.get_text()

            print(f"\n{'=' * 80}")
            print(f"[PAGE] Page {page_num + 1}/{num_pages}")
            print(f"{'=' * 80}")

            # テキスト長
            print(f"\n[LENGTH] Text length: {len(page_text)} characters")

            # テキストプレビュー（先頭500文字）
            preview_len = min(500, len(page_text))
            text_preview = page_text[:preview_len].replace('\n', ' ').replace('\r', ' ')
            print(f"\n[PREVIEW] Text preview (first {preview_len} chars):")
            print(f"   {text_preview}")
            if len(page_text) > preview_len:
                print(f"   ... ({len(page_text) - preview_len} more characters)")

            # キーワード検出
            print(f"\n[KEYWORDS] Keyword Detection:")

            found_receipt = [kw for kw in receipt_keywords if kw in page_text]
            found_payment = [kw for kw in payment_keywords if kw in page_text]
            found_pref = [kw for kw in pref_keywords if kw in page_text]
            found_specific = [kw for kw in specific_local_keywords if kw in page_text]

            print(f"   Receipt keywords: {found_receipt if found_receipt else '(none)'}")
            print(f"   Payment keywords: {found_payment if found_payment else '(none)'}")
            print(f"   Prefecture keywords: {found_pref if found_pref else '(none)'}")
            print(f"   Specific local keywords: {found_specific if found_specific else '(none)'}")

            # DocumentClassifierV5による分類
            print(f"\n[CLASSIFICATION] Classification Result:")
            detected_code = classifier.detect_page_doc_code(page_text, prefer_bundle="local")
            print(f"   Detected code: {detected_code}")

            # Bundle検出判定
            if detected_code in local_target_codes:
                detected_pages.append((page_num + 1, detected_code))
                print(f"   [OK] MATCH - This page would be included in bundle detection")
            else:
                print(f"   [NG] NO MATCH - This page would NOT trigger bundle split")

            # 受信通知か納付情報かの判定
            if detected_code:
                if detected_code.endswith("3"):
                    print(f"   [TYPE] Receipt Notification (受信通知)")
                elif detected_code.endswith("4"):
                    print(f"   [TYPE] Payment Information (納付情報)")

        doc.close()

        # Bundle判定結果
        print(f"\n{'=' * 80}")
        print(f"[SUMMARY] Bundle Detection Summary")
        print(f"{'=' * 80}")
        print(f"\nDetected pages with target codes: {len(detected_pages)}")
        for page_num, code in detected_pages:
            print(f"   - Page {page_num}: {code}")

        print(f"\n[RESULT] Bundle Detection Result:")
        if len(detected_pages) >= 2:
            print(f"   [OK] BUNDLE DETECTED - This PDF would be split into bundle")
            print(f"   Reason: {len(detected_pages)} pages have target codes (threshold: 2)")
        else:
            print(f"   [NG] BUNDLE NOT DETECTED - This PDF would NOT be split")
            print(f"   Reason: Only {len(detected_pages)} page(s) have target codes (threshold: 2)")

        print(f"\n{'=' * 80}\n")

    except Exception as e:
        print(f"[ERROR] Error during analysis: {e}")
        import traceback
        traceback.print_exc()


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("Usage: python debug_local_tax_detection.py <PDF_FILE_PATH>")
        print("\nExample:")
        print("  python debug_local_tax_detection.py C:\\path\\to\\地方税.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    analyze_pdf(pdf_path)


if __name__ == "__main__":
    main()
