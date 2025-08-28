#!/usr/bin/env python3
"""
v5.0システム最終統合テスト
全てのテストスイートを実行して最終検証
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def run_final_integration_test():
    """最終統合テスト実行"""
    print("=" * 70)
    print("税務書類リネームシステム v5.0 最終統合テスト")
    print("=" * 70)
    print()
    
    # テスト開始時刻
    start_time = time.time()
    
    # 統合テストスイート
    all_tests = []
    
    # 1. 基本機能テスト
    print("Phase 1: 基本機能テスト")
    print("-" * 40)
    basic_tests = run_basic_functionality_test()
    all_tests.extend(basic_tests)
    
    # 2. 失敗ケース修正テスト  
    print("\nPhase 2: 失敗ケース修正テスト")
    print("-" * 40)
    failed_case_tests = run_failed_case_correction_test()
    all_tests.extend(failed_case_tests)
    
    # 3. エッジケーステスト
    print("\nPhase 3: エッジケーステスト")
    print("-" * 40)
    edge_case_tests = run_edge_case_test()
    all_tests.extend(edge_case_tests)
    
    # 4. 性能テスト
    print("\nPhase 4: 性能テスト")
    print("-" * 40)
    performance_tests = run_performance_test()
    all_tests.extend(performance_tests)
    
    # 総合結果
    end_time = time.time()
    total_time = end_time - start_time
    
    success_count = sum(1 for test in all_tests if test['success'])
    total_count = len(all_tests)
    success_rate = success_count / total_count * 100 if total_count > 0 else 0
    
    print("\n" + "=" * 70)
    print("最終統合テスト結果")
    print("=" * 70)
    print(f"実行テスト数: {total_count}")
    print(f"成功テスト数: {success_count}")
    print(f"成功率: {success_rate:.1f}%")
    print(f"実行時間: {total_time:.2f}秒")
    print()
    
    # フェーズ別結果
    phases = {
        "基本機能": basic_tests,
        "失敗ケース修正": failed_case_tests, 
        "エッジケース": edge_case_tests,
        "性能": performance_tests
    }
    
    for phase_name, tests in phases.items():
        phase_success = sum(1 for test in tests if test['success'])
        phase_total = len(tests)
        phase_rate = phase_success / phase_total * 100 if phase_total > 0 else 0
        status = "PASS" if phase_rate == 100.0 else "FAIL"
        print(f"{phase_name}テスト: {phase_success}/{phase_total} ({phase_rate:.1f}%) [{status}]")
    
    print()
    
    # 最終判定
    if success_rate == 100.0:
        print("🎉 全てのテストに合格しました！")
        print("✅ v5.0システムは本格運用可能です。")
        print("✅ AND条件判定機能が完璧に動作しています。")
        print("✅ 従来の問題が全て解決されています。")
    elif success_rate >= 90.0:
        print("⚠️ 大部分のテストに合格していますが、一部問題があります。")
        print("🔧 軽微な調整後に運用可能です。")
    else:
        print("❌ 重大な問題が発見されました。")
        print("🔧 システム調整が必要です。")
    
    print("\n" + "=" * 70)
    
    return success_rate == 100.0

def run_basic_functionality_test():
    """基本機能テスト"""
    classifier = DocumentClassifierV5(debug_mode=False)
    tests = []
    
    basic_cases = [
        ("法人税申告書", "内国法人の確定申告(青色) 法人税及び地方法人税申告書", "0001_法人税及び地方法人税申告書"),
        ("消費税申告書", "消費税及び地方消費税申告(一般・法人) 課税期間分", "3001_消費税及び地方消費税申告書"),
        ("都道府県税申告書", "法人都道府県民税・事業税・特別法人事業税 確定申告", "1001_都道府県_法人都道府県民税・事業税・特別法人事業税"),
        ("市町村税申告書", "法人市民税申告書 均等割 法人税割", "2001_市町村_法人市民税")
    ]
    
    for name, content, expected in basic_cases:
        result = classifier.classify_document_v5(content, "test.pdf")
        success = result.document_type == expected
        tests.append({
            'name': name,
            'success': success,
            'result': result.document_type,
            'expected': expected
        })
        print(f"  {name}: {'PASS' if success else 'FAIL'}")
    
    return tests

def run_failed_case_correction_test():
    """失敗ケース修正テスト"""
    classifier = DocumentClassifierV5(debug_mode=False)
    tests = []
    
    # 元々失敗していたケース
    failed_cases = [
        ("法人税受信通知", "メール詳細 種目 法人税及び地方法人税申告書 受付番号", "0003_受信通知_法人税"),
        ("法人税納付情報", "メール詳細（納付区分番号通知） 税目 法人税及地方法人税", "0004_納付情報_法人税"),
        ("消費税受信通知", "メール詳細 種目 消費税申告書 受付日時", "3003_受信通知_消費税"),
        ("消費税納付情報", "メール詳細（納付区分番号通知） 税目 消費税及地方消費税", "3004_納付情報_消費税"),
        ("都道府県納付情報", "納付情報発行結果 税目:法人二税・特別税", "1004_納付情報_都道府県"),
        ("市町村受信通知", "申告受付完了通知 法人市民税 蒲郡市役所", "2003_受信通知_市町村")
    ]
    
    for name, content, expected in failed_cases:
        result = classifier.classify_document_v5(content, "test.pdf")
        success = result.document_type == expected
        tests.append({
            'name': name,
            'success': success,
            'result': result.document_type,
            'expected': expected
        })
        print(f"  {name}: {'PASS' if success else 'FAIL'}")
    
    return tests

def run_edge_case_test():
    """エッジケーステスト"""
    classifier = DocumentClassifierV5(debug_mode=False)
    tests = []
    
    edge_cases = [
        ("キーワード混在1", "メール詳細 法人税 消費税 種目 法人税及び地方法人税申告書", "0003_受信通知_法人税"),
        ("キーワード混在2", "消費税申告書 法人税 メール詳細 種目 消費税申告書", "3003_受信通知_消費税"),
        ("複数税目", "法人税及び地方法人税申告書 消費税及び地方消費税申告書 内国法人", "0001_法人税及び地方法人税申告書"),
        ("短いテキスト", "法人税申告書", "0001_法人税及び地方法人税申告書"),
        ("空白文字", "   メール詳細   種目 法人税及び地方法人税申告書   ", "0003_受信通知_法人税")
    ]
    
    for name, content, expected in edge_cases:
        result = classifier.classify_document_v5(content, "test.pdf")
        success = result.document_type == expected
        tests.append({
            'name': name,
            'success': success,
            'result': result.document_type,
            'expected': expected
        })
        print(f"  {name}: {'PASS' if success else 'FAIL'}")
    
    return tests

def run_performance_test():
    """性能テスト"""
    classifier = DocumentClassifierV5(debug_mode=False)
    tests = []
    
    # 大量テキストでの処理速度テスト
    large_text = "メール詳細 " * 100 + "種目 法人税及び地方法人税申告書 " * 50 + "受付番号 " * 30
    
    start_time = time.time()
    result = classifier.classify_document_v5(large_text, "large_test.pdf")
    end_time = time.time()
    
    processing_time = (end_time - start_time) * 1000  # ミリ秒
    success = result.document_type == "0003_受信通知_法人税" and processing_time < 1000  # 1秒以内
    
    tests.append({
        'name': f"大量テキスト処理({processing_time:.1f}ms)",
        'success': success,
        'result': result.document_type,
        'expected': "0003_受信通知_法人税"
    })
    
    print(f"  大量テキスト処理: {'PASS' if success else 'FAIL'} ({processing_time:.1f}ms)")
    
    # 連続処理テスト
    batch_start = time.time()
    batch_results = []
    test_content = "メール詳細 種目 消費税申告書"
    
    for i in range(10):
        result = classifier.classify_document_v5(test_content, f"batch_{i}.pdf")
        batch_results.append(result.document_type == "3003_受信通知_消費税")
    
    batch_end = time.time()
    batch_time = (batch_end - batch_start) * 1000
    batch_success = all(batch_results) and batch_time < 5000  # 5秒以内
    
    tests.append({
        'name': f"連続処理10件({batch_time:.1f}ms)",
        'success': batch_success,
        'result': f"{sum(batch_results)}/10 correct",
        'expected': "10/10 correct"
    })
    
    print(f"  連続処理10件: {'PASS' if batch_success else 'FAIL'} ({batch_time:.1f}ms)")
    
    return tests

if __name__ == "__main__":
    success = run_final_integration_test()
    
    if success:
        print("\n🚀 v5.0システム最終検証完了！本格運用開始準備OK！")
    else:
        print("\n🔧 最終調整が必要です。")