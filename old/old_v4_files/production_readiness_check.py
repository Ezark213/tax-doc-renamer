#!/usr/bin/env python3
"""
本番環境準備確認チェックリスト
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def production_readiness_check():
    """本番環境準備確認"""
    print("=" * 70)
    print("v5.0システム 本番環境準備確認チェック")
    print("=" * 70)
    print()
    
    checks = []
    
    # 1. 必要ファイルの存在確認
    print("Phase 1: 必要ファイル確認")
    print("-" * 40)
    
    required_files = [
        "core/classification_v5.py",
        "main_v5.py", 
        "test_v5.py",
        "V5_運用ガイド.md"
    ]
    
    for file_path in required_files:
        exists = os.path.exists(file_path)
        status = "OK" if exists else "NG"
        print(f"  {file_path:<30}: {status}")
        checks.append(("ファイル存在", file_path, exists))
    
    # 2. インポート確認
    print("\nPhase 2: モジュールインポート確認")
    print("-" * 40)
    
    try:
        from core.classification_v5 import DocumentClassifierV5
        print("  DocumentClassifierV5: OK")
        import_ok = True
        checks.append(("インポート", "DocumentClassifierV5", True))
    except ImportError as e:
        print(f"  DocumentClassifierV5: NG ({e})")
        import_ok = False
        checks.append(("インポート", "DocumentClassifierV5", False))
    
    # 3. 基本機能確認
    print("\nPhase 3: 基本機能確認")
    print("-" * 40)
    
    if import_ok:
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            test_result = classifier.classify_document_v5("テスト", "test.pdf")
            basic_function_ok = hasattr(test_result, 'document_type')
            print(f"  基本分類機能: {'OK' if basic_function_ok else 'NG'}")
            checks.append(("基本機能", "分類処理", basic_function_ok))
            
            # AND条件機能確認
            and_test = classifier.classify_document_v5("メール詳細 種目 法人税及び地方法人税申告書", "test.pdf")
            and_function_ok = and_test.document_type == "0003_受信通知_法人税"
            print(f"  AND条件機能: {'OK' if and_function_ok else 'NG'}")
            checks.append(("基本機能", "AND条件判定", and_function_ok))
            
        except Exception as e:
            print(f"  基本機能確認: NG ({e})")
            checks.append(("基本機能", "分類処理", False))
            checks.append(("基本機能", "AND条件判定", False))
    
    # 4. パフォーマンス確認
    print("\nPhase 4: パフォーマンス確認")
    print("-" * 40)
    
    if import_ok:
        try:
            classifier = DocumentClassifierV5(debug_mode=False)
            test_text = "メール詳細 種目 法人税及び地方法人税申告書 受付番号"
            
            # 処理時間測定
            start_time = time.time()
            for i in range(100):  # 100回テスト
                result = classifier.classify_document_v5(test_text, f"perf_test_{i}.pdf")
            end_time = time.time()
            
            total_time = (end_time - start_time) * 1000  # ミリ秒
            avg_time = total_time / 100
            performance_ok = avg_time < 50  # 50ms以内
            
            print(f"  100件処理時間: {total_time:.1f}ms")
            print(f"  平均処理時間: {avg_time:.1f}ms")
            print(f"  パフォーマンス: {'OK' if performance_ok else 'NG'} (目標: <50ms)")
            checks.append(("パフォーマンス", "処理速度", performance_ok))
            
        except Exception as e:
            print(f"  パフォーマンス確認: NG ({e})")
            checks.append(("パフォーマンス", "処理速度", False))
    
    # 5. 主要分類パターン確認
    print("\nPhase 5: 主要分類パターン確認")
    print("-" * 40)
    
    if import_ok:
        key_patterns = [
            ("法人税受信通知", "メール詳細 種目 法人税及び地方法人税申告書", "0003_受信通知_法人税"),
            ("消費税受信通知", "メール詳細 種目 消費税申告書", "3003_受信通知_消費税"),
            ("市町村受信通知", "申告受付完了通知 法人市民税", "2003_受信通知_市町村"),
            ("法人税申告書", "内国法人の確定申告 法人税及び地方法人税申告書", "0001_法人税及び地方法人税申告書"),
            ("消費税申告書", "消費税及び地方消費税申告 課税期間分", "3001_消費税及び地方消費税申告書")
        ]
        
        pattern_success = 0
        for name, content, expected in key_patterns:
            try:
                result = classifier.classify_document_v5(content, "pattern_test.pdf")
                success = result.document_type == expected
                print(f"  {name:<15}: {'OK' if success else 'NG'}")
                checks.append(("分類パターン", name, success))
                if success:
                    pattern_success += 1
            except Exception as e:
                print(f"  {name:<15}: NG ({e})")
                checks.append(("分類パターン", name, False))
        
        pattern_rate = pattern_success / len(key_patterns) * 100
        print(f"  パターン成功率: {pattern_rate:.1f}%")
    
    # 総合評価
    print("\n" + "=" * 70)
    print("総合評価")
    print("=" * 70)
    
    total_checks = len(checks)
    passed_checks = sum(1 for check in checks if check[2])
    pass_rate = passed_checks / total_checks * 100 if total_checks > 0 else 0
    
    print(f"チェック項目: {total_checks}")
    print(f"合格項目: {passed_checks}")
    print(f"合格率: {pass_rate:.1f}%")
    print()
    
    # カテゴリ別評価
    categories = {}
    for category, item, result in checks:
        if category not in categories:
            categories[category] = []
        categories[category].append(result)
    
    for category, results in categories.items():
        category_pass = sum(results)
        category_total = len(results)
        category_rate = category_pass / category_total * 100
        status = "PASS" if category_rate >= 80 else "CAUTION" if category_rate >= 60 else "FAIL"
        print(f"{category}: {category_pass}/{category_total} ({category_rate:.1f}%) [{status}]")
    
    print()
    
    # 最終判定
    if pass_rate >= 95:
        print("🎉 本番環境準備完了！")
        print("✅ v5.0システムは本格運用可能です。")
        readiness_status = "READY"
    elif pass_rate >= 85:
        print("⚠️ ほぼ準備完了ですが、軽微な課題があります。")
        print("🔧 問題修正後、本格運用推奨。")
        readiness_status = "MOSTLY_READY"
    else:
        print("❌ 本番環境準備に問題があります。")
        print("🔧 重要な修正が必要です。")
        readiness_status = "NOT_READY"
    
    print(f"\n本番準備状況: {readiness_status}")
    print("=" * 70)
    
    return readiness_status == "READY"

def generate_deployment_checklist():
    """デプロイメントチェックリスト生成"""
    print("\n" + "=" * 70)
    print("デプロイメントチェックリスト")
    print("=" * 70)
    
    checklist = [
        "□ v5.0システムファイル配置確認",
        "□ main_v5.pyでv5.0モード有効化",
        "□ 自治体設定（連番対応）確認",
        "□ テストスイート実行・全合格確認",
        "□ バックアップ体制確立",
        "□ 初回バッチ処理での動作確認",
        "□ 分類結果の目視確認",
        "□ 例外ケース対応手順確認",
        "□ 運用チームへの引き継ぎ完了",
        "□ 本格運用開始"
    ]
    
    for item in checklist:
        print(f"  {item}")
    
    print("\n運用開始後の定期確認:")
    print("  • 週次: 分類精度確認")
    print("  • 月次: テストスイート実行")
    print("  • 必要時: 新規書類パターン追加")

if __name__ == "__main__":
    ready = production_readiness_check()
    generate_deployment_checklist()
    
    if ready:
        print("\n🚀 v5.0システム本番運用開始準備OK！")
    else:
        print("\n🔧 修正完了後、再度確認してください。")