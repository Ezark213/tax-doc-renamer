#!/usr/bin/env python3
"""
v4.0 vs v5.0 性能比較テスト
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def compare_versions():
    """v4.0とv5.0の性能比較"""
    print("=== v4.0 vs v5.0 性能比較テスト ===")
    print()
    
    # 問題のあったテストケース
    problem_cases = [
        {
            "name": "法人税受信通知（消費税キーワード混在）",
            "text": "メール詳細 種目 法人税及び地方法人税申告書 受付番号 20250731185710521215 税目 法人税 消費税",
            "filename": "test.pdf",
            "expected": "0003_受信通知_法人税"
        },
        {
            "name": "消費税納付情報（法人税キーワード混在）",
            "text": "メール詳細（納付区分番号通知） 税目 消費税及地方消費税 申告区分 確定申告 法人税",
            "filename": "test2.pdf", 
            "expected": "3004_納付情報_消費税"
        },
        {
            "name": "市町村受信通知",
            "text": "申告受付完了通知 法人市民税（法人税割） 申告納付税額 2,900円 蒲郡市役所",
            "filename": "test3.pdf",
            "expected": "2003_受信通知_市町村"
        }
    ]
    
    # v4.0テスト
    try:
        from core.classification import DocumentClassifier
        print("v4.0 分類エンジンテスト")
        print("-" * 40)
        
        classifier_v4 = DocumentClassifier(debug_mode=False)
        v4_results = []
        v4_start_time = time.time()
        
        for case in problem_cases:
            result = classifier_v4.classify_document(case['text'], case['filename'])
            correct = result.document_type == case['expected']
            v4_results.append({
                'name': case['name'],
                'result': result.document_type,
                'expected': case['expected'],
                'correct': correct,
                'confidence': result.confidence
            })
            print(f"{case['name']}: {result.document_type} {'[OK]' if correct else '[NG]'}")
        
        v4_time = time.time() - v4_start_time
        v4_accuracy = sum(1 for r in v4_results if r['correct']) / len(v4_results) * 100
        
    except ImportError:
        print("v4.0分類エンジンが見つかりません")
        v4_results = []
        v4_time = 0
        v4_accuracy = 0
    
    print()
    
    # v5.0テスト
    from core.classification_v5 import DocumentClassifierV5
    print("v5.0 分類エンジンテスト")
    print("-" * 40)
    
    classifier_v5 = DocumentClassifierV5(debug_mode=False)
    v5_results = []
    v5_start_time = time.time()
    
    for case in problem_cases:
        result = classifier_v5.classify_document_v5(case['text'], case['filename'])
        correct = result.document_type == case['expected']
        v5_results.append({
            'name': case['name'],
            'result': result.document_type,
            'expected': case['expected'], 
            'correct': correct,
            'confidence': result.confidence
        })
        print(f"{case['name']}: {result.document_type} {'[OK]' if correct else '[NG]'}")
    
    v5_time = time.time() - v5_start_time
    v5_accuracy = sum(1 for r in v5_results if r['correct']) / len(v5_results) * 100
    
    # 結果比較
    print("\n" + "=" * 60)
    print("性能比較結果")
    print("=" * 60)
    
    if v4_results:
        print(f"v4.0 正解率: {v4_accuracy:.1f}% ({sum(1 for r in v4_results if r['correct'])}/{len(v4_results)})")
        print(f"v4.0 処理時間: {v4_time*1000:.1f}ms")
    
    print(f"v5.0 正解率: {v5_accuracy:.1f}% ({sum(1 for r in v5_results if r['correct'])}/{len(v5_results)})")
    print(f"v5.0 処理時間: {v5_time*1000:.1f}ms")
    
    if v4_results:
        improvement = v5_accuracy - v4_accuracy
        print(f"精度向上: +{improvement:.1f}%")
        
        if improvement > 0:
            print("\nv5.0がv4.0の問題を解決しました！")
            print("AND条件判定により、キーワード干渉問題が解決されています。")
        elif improvement == 0:
            print("\n両バージョンで同等の精度です")
        else:
            print("\nv5.0で精度が低下しています（要調査）")
    
    # 詳細分析
    print(f"\n詳細分析")
    print("-" * 30)
    
    for i, case in enumerate(problem_cases):
        print(f"\n{case['name']}:")
        print(f"  期待値: {case['expected']}")
        
        if v4_results:
            v4_result = v4_results[i]
            print(f"  v4.0結果: {v4_result['result']} (信頼度: {v4_result['confidence']:.2f}) {'✓' if v4_result['correct'] else '✗'}")
        
        v5_result = v5_results[i]
        print(f"  v5.0結果: {v5_result['result']} (信頼度: {v5_result['confidence']:.2f}) {'✓' if v5_result['correct'] else '✗'}")
    
    return v5_accuracy == 100.0

if __name__ == "__main__":
    success = compare_versions()
    
    print("\n" + "=" * 60)
    if success:
        print("v5.0システムが全てのテストケースで正解しました！")
        print("本格運用の準備が整っています。")
    else:
        print("一部のテストで問題が残っています。要調整。")
    print("=" * 60)