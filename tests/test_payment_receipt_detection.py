#!/usr/bin/env python3
"""
Phase 3 単体テスト: 問題①（納付情報・受信通知判定）
正規表現による高精度判定のテスト
"""

import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.classification_v5 import DocumentClassifierV5


class TestPaymentReceiptDetection(unittest.TestCase):
    """納付情報・受信通知判定のテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.classifier = DocumentClassifierV5()

    def test_payment_info_title_exact_match(self):
        """TC-1: 法人税納付情報（タイトル完全一致）"""
        text = "メール詳細（納付区分番号通知）\n納付内容を確認してください"
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertTrue(result, "タイトル完全一致で納付情報と判定されるべき")

    def test_receipt_notification_normal(self):
        """TC-2: 法人税受信通知（正常系）"""
        text = "送信されたデータを受け付けました\n受付番号: 12345"
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertFalse(result, "受信通知パターンで納付情報から除外されるべき")

    def test_receipt_notification_with_remark(self):
        """TC-3: 受信通知の備考欄（境界ケース）"""
        text = """
        送信されたデータを受け付けました
        受付番号: 12345

        備考: 納付区分番号通知もあわせて確認ください
        """
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertFalse(result, "備考欄での言及は納付情報から除外されるべき")

    def test_receipt_notification_with_space_insertion(self):
        """TC-4: スペース挿入（エッジケース）"""
        text = "送信された     データを   受け付けました"
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertFalse(result, "スペース挿入があっても受信通知パターンで判定されるべき")

    def test_payment_info_composite_pattern(self):
        """TC-5: 納付情報の複合パターン"""
        text = "納付区分番号通知\n納付内容を確認し、以下のボタンより納付してください"
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertTrue(result, "複合パターンで納付情報と判定されるべき")

    def test_receipt_notification_method_normal(self):
        """TC-6: 受信通知メソッドの正常系テスト"""
        text = "送信されたデータを受け付けました\n受付番号: 12345\n税目: 法人税"
        result = self.classifier._is_receipt_notification(text, "test.pdf")
        self.assertTrue(result, "受信通知として判定されるべき")

    def test_receipt_notification_method_with_payment_keyword(self):
        """TC-7: 納付キーワードを含む場合の除外テスト"""
        text = "送信されたデータを受け付けました\n納付区分番号通知もご確認ください"
        result = self.classifier._is_receipt_notification(text, "test.pdf")
        # 注: このケースでは「送信されたデータを受け付けました」が受信通知パターンとして検出されるが、
        # _is_payment_info の備考欄除外パターンがマッチしないため、
        # _is_payment_info が False を返し、結果として _is_receipt_notification が True を返す
        # これは期待される動作（受信通知の本文に納付区分番号通知への言及がある場合）
        self.assertTrue(result, "受信通知パターンが優先され、受信通知として判定されるべき")

    def test_payment_info_single_keyword_fallback(self):
        """TC-8: 単独キーワードによるフォールバック"""
        text = "納付区分番号通知"
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertTrue(result, "単独キーワードで納付情報と判定されるべき（フォールバック）")

    def test_receipt_notification_with_newline(self):
        """TC-9: 改行を含む受信通知パターン"""
        text = """送信された
        データを
        受け付けました"""
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertFalse(result, "改行があっても受信通知パターンで判定されるべき")

    def test_payment_info_with_button_phrase(self):
        """TC-10: 「以下のボタンより納付」を含む納付情報"""
        text = "納付区分番号通知\n以下のボタンより納付手続きを行ってください"
        result = self.classifier._is_payment_info(text, "test.pdf")
        self.assertTrue(result, "ボタンフレーズを含む納付情報と判定されるべき")


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)
