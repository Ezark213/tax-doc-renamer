#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受信通知連番システムバグ修正の検証テスト
修正指示書に基づく検証項目
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from helpers.seq_policy import ReceiptSequencer, is_receipt_notice, is_pref_receipt, is_city_receipt
from helpers.job_context import JobContext
from helpers.run_config import RunConfig
from core.rename_engine import RenameEngine
from core.models import RenameFields


def create_test_job_context():
    """修正指示書に基づくテスト用JobContextを作成"""
    job_ctx = JobContext(
        job_id="test_receipt_fix", 
        confirmed_yymm="2508",
        yymm_source="UI",
        run_config=None
    )
    
    # 修正指示書のサンプル自治体セット設定を適用
    job_ctx.set_sample_municipality_sets()
    
    return job_ctx


def test_ocr_extraction():
    """OCR抽出ロジックのテスト"""
    print("\n=== OCR抽出ロジックテスト ===")
    
    rename_engine = RenameEngine()
    
    # 都道府県抽出テスト
    test_cases_pref = [
        ("○○県××県税事務所", "○○県"),
        ("東京都××都税事務所", "東京都"),  
        ("発行元 愛知県××県税事務所", "愛知県"),
        ("福岡県にある何かの文書", "福岡県"),
    ]
    
    for ocr_text, expected in test_cases_pref:
        result = rename_engine._extract_prefecture_from_ocr(ocr_text)
        status = "[OK]" if result == expected else "[NG]"
        print(f"{status} OCR都道府県抽出: '{ocr_text}' -> '{result}' (期待値: '{expected}')")
    
    # 市町村抽出テスト
    test_cases_city = [
        ("××市役所 愛知県蒲郡市", ("愛知県", "蒲郡市")),
        ("発行元 福岡市", ("福岡県", "福岡市")),
        ("提出先名 蒲郡市長", ("愛知県", "蒲郡市")),
    ]
    
    for ocr_text, (expected_pref, expected_city) in test_cases_city:
        result_pref, result_city = rename_engine._extract_prefecture_city_from_ocr(ocr_text)
        status = "[OK]" if result_pref == expected_pref and result_city == expected_city else "[NG]"
        print(f"{status} OCR市町村抽出: '{ocr_text}' -> ('{result_pref}', '{result_city}') (期待値: ('{expected_pref}', '{expected_city}'))")


def test_sequencing_logic():
    """連番計算ロジックのテスト"""
    print("\n=== 連番計算ロジックテスト ===")
    
    job_ctx = create_test_job_context()
    sequencer = ReceiptSequencer(job_ctx)
    
    # 都道府県受信通知の連番テスト
    test_cases_pref = [
        ("東京都", "1003"),  # セット1: 1003 + (1-1)*10 = 1003
        ("愛知県", "1013"),  # セット2: 1003 + (2-1)*10 = 1013  
        ("福岡県", "1023"),  # セット3: 1003 + (3-1)*10 = 1023
    ]
    
    print("都道府県受信通知連番:")
    for ocr_pref, expected in test_cases_pref:
        try:
            result = sequencer.assign_pref_seq("1003_受信通知", ocr_pref)
            status = "[OK]" if result == expected else "[NG]"
            print(f"  {status} {ocr_pref} -> {result} (期待値: {expected})")
        except Exception as e:
            print(f"  [ERROR] {ocr_pref} -> エラー: {e}")
    
    # 市町村受信通知の連番テスト（東京都スキップ考慮）
    test_cases_city = [
        ("愛知県", "蒲郡市", "2003"),  # セット2だが東京都スキップで調整1: 2003 + (1-1)*10 = 2003
        ("福岡県", "福岡市", "2013"),  # セット3だが東京都スキップで調整2: 2003 + (2-1)*10 = 2013
    ]
    
    print("市町村受信通知連番:")
    for ocr_pref, ocr_city, expected in test_cases_city:
        try:
            result = sequencer.assign_city_seq("2003_受信通知", ocr_pref, ocr_city)
            status = "[OK]" if result == expected else "[NG]"
            print(f"  {status} {ocr_pref} {ocr_city} -> {result} (期待値: {expected})")
        except Exception as e:
            print(f"  [ERROR] {ocr_pref} {ocr_city} -> エラー: {e}")


def test_tokyo_constraint():
    """東京都制約のテスト"""
    print("\n=== 東京都制約テスト ===")
    
    # 正常ケース: 東京都がセット1
    try:
        job_ctx = create_test_job_context()
        job_ctx.validate_tokyo_constraint()
        print("[OK] 東京都制約: 正常ケース（東京都がセット1）")
    except ValueError as e:
        print(f"[ERROR] 東京都制約: 正常ケースでエラー - {e}")
    
    # 異常ケース: 東京都がセット2
    try:
        job_ctx = JobContext(
            job_id="test_tokyo_violation", 
            confirmed_yymm="2508",
            yymm_source="UI",
            run_config=None
        )
        job_ctx.current_municipality_sets = {
            1: {'prefecture': '愛知県', 'city': '蒲郡市'}, 
            2: {'prefecture': '東京都', 'city': ''},  # 違反: 東京都がセット2
            3: {'prefecture': '福岡県', 'city': '福岡市'}
        }
        job_ctx.validate_tokyo_constraint()
        print("[NG] 東京都制約: 異常ケースで検出されず")
    except ValueError as e:
        print(f"[OK] 東京都制約: 異常ケースを正しく検出 - {e}")


def test_integration():
    """統合テスト"""
    print("\n=== 統合テスト ===")
    
    job_ctx = create_test_job_context()
    rename_engine = RenameEngine()
    
    # テスト用のRenameFieldsを作成
    test_cases = [
        {
            "code": "1003_受信通知",
            "ocr_text": "発行元 愛知県××県税事務所 受信通知",
            "expected_code": "1013",
            "description": "愛知県都道府県受信通知"
        },
        {
            "code": "2003_受信通知", 
            "ocr_text": "福岡市役所 受信通知",
            "expected_code": "2013",
            "description": "福岡市市町村受信通知"
        }
    ]
    
    for case in test_cases:
        try:
            # RenameFieldsを作成
            fields = RenameFields()
            fields.document_text = case["ocr_text"]
            
            result = rename_engine._apply_receipt_numbering_hook(
                case["code"], fields, job_ctx
            )
            
            status = "[OK]" if result == case["expected_code"] else "[NG]"
            print(f"  {status} {case['description']}: {case['code']} -> {result} (期待値: {case['expected_code']})")
            
        except Exception as e:
            print(f"  [ERROR] {case['description']}: エラー - {e}")


def run_all_tests():
    """全テストの実行"""
    print("="*60)
    print("受信通知連番システムバグ修正 検証テスト")
    print("="*60)
    
    try:
        test_ocr_extraction()
        test_sequencing_logic()
        test_tokyo_constraint()
        test_integration()
        
        print("\n" + "="*60)
        print("テスト完了")
        print("="*60)
        
    except Exception as e:
        print(f"\nテスト実行中にエラーが発生しました: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    run_all_tests()