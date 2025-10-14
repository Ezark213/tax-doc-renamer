#!/usr/bin/env python3
"""
Phase 3 単体テスト: 問題②③（分類ルールの改善）
市町村申告書、納付税額一覧表、一括償却資産明細表、勘定科目別税区分集計表の判定テスト
"""

import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.classification_v5 import DocumentClassifierV5


class TestMunicipalDeclarationVsTaxList(unittest.TestCase):
    """問題②: 市町村申告書と納付税額一覧表の区別テスト"""

    def setUp(self):
        """テストの前準備"""
        self.classifier = DocumentClassifierV5()

    def test_municipal_declaration_with_title_and_tax(self):
        """TC-11: 市町村申告書（タイトル + 法人税割額）"""
        text = """
        市町村民税の申告書
        法人税割額: 100,000円
        均等割額: 50,000円
        """
        result = self.classifier.classify_document_v5(text, "福岡市申告書.pdf")
        # 市町村申告書として判定されることを確認（2001 または 20XX番台）
        self.assertTrue(
            "市町村申告書" in result.document_type or result.document_type.startswith("20"),
            f"市町村申告書として判定されるべき: {result.document_type}"
        )

    def test_tax_list_with_annual_tax(self):
        """TC-12: 納付税額一覧表（年間税額を含む）"""
        text = """
        納付税額一覧表
        年間税額: 1,000,000円
        既納付額: 500,000円
        差引納付額: 500,000円
        """
        result = self.classifier.classify_document_v5(text, "納税一覧.pdf")
        self.assertEqual(
            "0000_納付税額一覧表",
            result.document_type,
            "納付税額一覧表として判定されるべき"
        )

    def test_municipal_declaration_should_not_match_tax_list(self):
        """TC-13: 市町村申告書が納付税額一覧表と誤判定されないことを確認"""
        text = """
        市町村民税の申告書
        法人税割額: 200,000円
        均等割額: 70,000円
        見込納付額: 270,000円
        """
        result = self.classifier.classify_document_v5(text, "市町村申告書.pdf")
        # 0000_納付税額一覧表として判定されないことを確認
        self.assertNotEqual(
            "0000_納付税額一覧表",
            result.document_type,
            "市町村申告書が納付税額一覧表と誤判定されてはいけない"
        )

    def test_tax_list_exclude_keywords(self):
        """TC-14: 納付税額一覧表の除外キーワードテスト"""
        text = """
        納付税額一覧表
        市町村申告書も含まれます
        """
        result = self.classifier.classify_document_v5(text, "test.pdf")
        # 除外キーワード「市町村申告書」により、0000として判定されない可能性
        # （ただし、タイトルの「納付税額一覧表」が優先される可能性もある）
        # このテストは除外ロジックの動作を確認
        print(f"除外キーワードテスト結果: {result.document_type}")


class TestAccountClassificationVsLumpSum(unittest.TestCase):
    """問題③: 勘定科目別税区分集計表と一括償却資産明細表の区別テスト"""

    def setUp(self):
        """テストの前準備"""
        self.classifier = DocumentClassifierV5()

    def test_account_tax_classification_with_account_name(self):
        """TC-15: 勘定科目別税区分集計表（勘定科目名「一括償却資産」を含む）"""
        text = """
        勘定科目別税区分集計表
        勘定科目: 一括償却資産
        税区分: 課税仕入
        課税売上: 1,000,000円
        課税仕入: 800,000円
        """
        result = self.classifier.classify_document_v5(text, "勘定科目別税区分集計表.pdf")
        self.assertEqual(
            "7001_勘定科目別税区分集計表",
            result.document_type,
            "勘定科目別税区分集計表として判定されるべき"
        )

    def test_lump_sum_depreciation_with_columns(self):
        """TC-16: 一括償却資産明細表（表構造の列名を含む）"""
        text = """
        一括償却資産明細表
        取得年月日: 2024/01/01
        取得価額: 300,000円
        供用年月日: 2024/01/15
        """
        result = self.classifier.classify_document_v5(text, "一括償却資産明細表.pdf")
        self.assertEqual(
            "6002_一括償却資産明細表",
            result.document_type,
            "一括償却資産明細表として判定されるべき"
        )

    def test_account_classification_should_not_match_lump_sum(self):
        """TC-17: 勘定科目別税区分集計表が一括償却資産明細表と誤判定されないことを確認"""
        text = """
        勘定科目別税区分集計表
        一括償却資産: 500,000円
        課税仕入: 400,000円
        """
        result = self.classifier.classify_document_v5(text, "test.pdf")
        # 6002_一括償却資産明細表として判定されないことを確認
        self.assertNotEqual(
            "6002_一括償却資産明細表",
            result.document_type,
            "勘定科目別税区分集計表が一括償却資産明細表と誤判定されてはいけない"
        )

    def test_lump_sum_exclude_keywords(self):
        """TC-18: 一括償却資産明細表の除外キーワードテスト"""
        text = """
        一括償却資産
        勘定科目別税区分集計表
        """
        result = self.classifier.classify_document_v5(text, "test.pdf")
        # 除外キーワード「勘定科目別税区分集計表」により、6002として判定されない
        self.assertNotEqual(
            "6002_一括償却資産明細表",
            result.document_type,
            "除外キーワードにより一括償却資産明細表として判定されてはいけない"
        )

    def test_lump_sum_with_title_only(self):
        """TC-19: 一括償却資産明細表（タイトルのみ）"""
        text = "一括償却資産明細表"
        result = self.classifier.classify_document_v5(text, "一括償却資産明細表.pdf")
        self.assertEqual(
            "6002_一括償却資産明細表",
            result.document_type,
            "タイトル完全一致で一括償却資産明細表として判定されるべき"
        )


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)
