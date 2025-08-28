#!/usr/bin/env python3
"""
v5.0システムで実際の失敗PDFをテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def test_real_pdf():
    """実際の失敗PDFでv5.0テスト"""
    print("=== v5.0システム 実際のPDFテスト ===")
    print()
    
    classifier = DocumentClassifierV5(debug_mode=True)  # デバッグモード有効
    
    # 実際のPDF内容
    pdf_text = """事業者コード：0564M0023 利用者名：メトロノーム株式会社
    メール詳細
    送信されたデータを受け付けました。
    なお、後日、内容の確認のため、担当職員からご連絡させていただく場合があり
    ますので、ご了承ください。
    提出先 芝税務署
    利用者識別番号 2300082330910050
    氏名又は名称 メトロノーム株式会社
    代表者等氏名 島崎 洋輔
    受付番号 20250731185710521215
    受付日時 2025/07/31 18:57:10
    種目 法人税及び地方法人税申告書
    事業年度 自 令和06年06月01日
    事業年度 至 令和07年05月31日
    税目 法人税
    申告の種類 確定
    所得金額又は欠損金額 7,063,438円
    差引確定法人税額 236,500円"""
    
    filename = "0003_受信通知_2508【元々3_国税】.pdf"
    expected = "0003_受信通知_法人税"
    
    print(f"テストファイル: {filename}")
    print(f"期待値: {expected}")
    print("=" * 60)
    
    # 分類実行
    result = classifier.classify_document_v5(pdf_text, filename)
    
    # 結果表示
    is_success = result.document_type == expected
    status = "[SUCCESS]" if is_success else "[FAILED]"
    
    print(f"結果: {result.document_type}")
    print(f"判定方法: {result.classification_method}")
    print(f"信頼度: {result.confidence:.2f}")
    print(f"マッチキーワード: {result.matched_keywords}")
    print(f"ステータス: {status}")
    
    if is_success:
        print("\n✅ 実際のPDFで正しく分類されました！")
        print("v5.0 AND条件判定が実際のデータで機能しています。")
    else:
        print(f"\n❌ 期待値と異なる結果です")
        print(f"期待値: {expected}")
        print(f"実際: {result.document_type}")
    
    return is_success

if __name__ == "__main__":
    test_real_pdf()