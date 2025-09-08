#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受信通知分類時の連番処理強制実行 - 問題再現・修正検証テスト
根本的なアーキテクチャ問題の解決を検証
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from core.classification_v5 import DocumentClassifierV5, ClassificationResult
from helpers.job_context import JobContext
from helpers.seq_policy import is_receipt_notice, is_pref_receipt, is_city_receipt
from core.models import RenameFields


def create_test_job_context():
    """テスト用JobContextを作成（修正指示書の自治体セット）"""
    job_ctx = JobContext(
        job_id="test_classification_receipt", 
        confirmed_yymm="2508",
        yymm_source="UI",
        run_config=None
    )
    
    job_ctx.set_sample_municipality_sets()
    return job_ctx


def test_current_issue_reproduction():
    """Step 1: 現在の問題を再現"""
    print("\n=== Step 1: 現在の問題再現テスト ===")
    
    classifier = DocumentClassifierV5(debug_mode=True)
    job_ctx = create_test_job_context()
    
    # 受信通知のテストケース
    test_cases = [
        {
            "name": "東京都受信通知",
            "ocr_text": "発行元 東京都××都税事務所 受信通知 申告受付完了",
            "expected_base": "1003",  # 基本分類
            "expected_final": "1003",  # 現在は基本のまま（問題）
            "expected_after_fix": "1003"  # 東京都は連番1番目なので1003のまま
        },
        {
            "name": "愛知県受信通知",
            "ocr_text": "発行元 愛知県××県税事務所 受信通知 申告受付完了",
            "expected_base": "1003",  # 基本分類
            "expected_final": "1003",  # 現在は基本のまま（問題）
            "expected_after_fix": "1013"  # 修正後：愛知県は2番目なので1013
        },
        {
            "name": "福岡市受信通知",
            "ocr_text": "福岡市役所 受信通知 申告受付完了",
            "expected_base": "2003",  # 基本分類
            "expected_final": "2003",  # 現在は基本のまま（問題）
            "expected_after_fix": "2013"  # 修正後：福岡市は3番目だが東京都スキップで2013
        }
    ]
    
    print("修正後の動作検証:")
    for case in test_cases:
        try:
            # 修正後の分類（連番処理強制実行）
            result = classifier.classify_document_v5(case["ocr_text"], 
                                                   filename=f"test_{case['name']}.pdf",
                                                   job_context=job_ctx)
            
            actual_code = result.document_type.split("_")[0] if "_" in result.document_type else result.document_type
            expected_code = case["expected_after_fix"]
            status = "[OK]" if actual_code == expected_code else "[ISSUE]"
            
            print(f"  {status} {case['name']}: '{actual_code}' (期待値: {expected_code})")
            
            if actual_code == expected_code:
                print(f"    ✅ 修正成功：連番処理が正常に実行された")
            else:
                print(f"    ❌ 修正必要：期待された連番が出力されていない")
            
        except Exception as e:
            print(f"  [ERROR] {case['name']}: {e}")
    
    return test_cases


def test_is_receipt_detection():
    """受信通知判定のテスト"""
    print("\n=== 受信通知判定機能テスト ===")
    
    test_cases = [
        ("1003_受信通知", True, "pref"),
        ("1013_受信通知", True, "pref"),
        ("2003_受信通知", True, "city"),
        ("2013_受信通知", True, "city"),
        ("1001_法人都道府県民税", False, None),
        ("3001_消費税申告書", False, None),
    ]
    
    for code, should_be_receipt, receipt_type in test_cases:
        is_receipt = is_receipt_notice(code)
        status = "[OK]" if is_receipt == should_be_receipt else "[NG]"
        print(f"  {status} {code} -> 受信通知判定: {is_receipt}")
        
        if is_receipt:
            if receipt_type == "pref":
                is_pref = is_pref_receipt(code)
                print(f"    都道府県受信通知: {is_pref}")
            elif receipt_type == "city":
                is_city = is_city_receipt(code)
                print(f"    市町村受信通知: {is_city}")


def test_simplified_numbering_logic():
    """簡素化された連番ロジックの検証（実装予定）"""
    print("\n=== 簡素化連番ロジック検証（実装後テスト用） ===")
    
    # サンプル自治体セット
    municipality_sets = {
        1: {'prefecture': '東京都', 'city': ''}, 
        2: {'prefecture': '愛知県', 'city': '蒲郡市'}, 
        3: {'prefecture': '福岡県', 'city': '福岡市'}
    }
    
    print("想定される連番計算結果:")
    
    # 都道府県受信通知の連番計算例
    pref_cases = [
        ("東京都", 1, "1003"),
        ("愛知県", 2, "1013"),
        ("福岡県", 3, "1023"),
    ]
    
    for pref, set_num, expected in pref_cases:
        # 連番計算式: 1003 + (set_num - 1) * 10
        calculated = 1003 + (set_num - 1) * 10
        result = f"{calculated:04d}"
        status = "[OK]" if result == expected else "[NG]"
        print(f"  {status} {pref}(セット{set_num}): 1003 + ({set_num}-1)*10 = {result} (期待値: {expected})")
    
    # 市町村受信通知の連番計算例（東京都スキップ）
    city_cases = [
        ("蒲郡市", 2, 1, "2003"),  # セット2だが東京都スキップで調整1
        ("福岡市", 3, 2, "2013"),  # セット3だが東京都スキップで調整2
    ]
    
    print("\n  市町村受信通知（東京都スキップ適用）:")
    for city, original_set, adjusted_set, expected in city_cases:
        # 連番計算式: 2003 + (adjusted_set - 1) * 10
        calculated = 2003 + (adjusted_set - 1) * 10
        result = f"{calculated:04d}"
        status = "[OK]" if result == expected else "[NG]"
        print(f"  {status} {city}(セット{original_set}→調整{adjusted_set}): 2003 + ({adjusted_set}-1)*10 = {result} (期待値: {expected})")


def run_reproduction_tests():
    """問題再現テストを実行"""
    print("=" * 60)
    print("受信通知分類時連番処理 - 問題再現テスト")
    print("=" * 60)
    
    try:
        test_cases = test_current_issue_reproduction()
        test_is_receipt_detection()
        test_simplified_numbering_logic()
        
        print("\n" + "=" * 60)
        print("問題再現テスト完了")
        print("次のステップ: classification_v5.py の修正実装")
        print("=" * 60)
        
        return test_cases
        
    except Exception as e:
        print(f"\nテスト実行中にエラーが発生しました: {e}")
        import traceback
        print(traceback.format_exc())
        return []


if __name__ == "__main__":
    run_reproduction_tests()