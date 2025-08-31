#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 テストスクリプト
AND条件判定の動作確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def test_v5_classification():
    """v5.0 分類エンジンのテスト"""
    print("=== 税務書類リネームシステム v5.0 テスト ===")
    print()
    
    # v5.0 分類エンジン初期化
    classifier = DocumentClassifierV5(debug_mode=False)  # デバッグログを簡潔に
    
    # テストケース（今回失敗した書類のパターン）
    test_cases = [
        {
            "name": "法人税受信通知",
            "text": """事業者コード：0564M0023 利用者名：メトロノーム株式会社
            メール詳細
            送信されたデータを受け付けました。
            提出先 芝税務署
            受付番号 20250731185710521215
            受付日時 2025/07/31 18:57:10
            種目 法人税及び地方法人税申告書
            税目 法人税
            申告の種類 確定""",
            "filename": "3_国税.pdf",
            "expected": "0003_受信通知_法人税",
            "description": "メール詳細+種目法人税のAND条件"
        },
        {
            "name": "法人税納付情報",
            "text": """事業者コード：0564M0023 利用者名：メトロノーム株式会社
            メール詳細（納付区分番号通知）
            納付内容を確認し、以下のボタンより納付してください。
            納付先 芝税務署
            税目 法人税及地方法人税
            申告区分（法人税） 確定申告
            納付区分 7126889728""",
            "filename": "5_国税.pdf",
            "expected": "0004_納付情報_法人税",
            "description": "納付区分番号通知+法人税及地方法人税のAND条件"
        },
        {
            "name": "消費税受信通知",
            "text": """事業者コード：0564M0023 利用者名：メトロノーム株式会社
            メール詳細
            送信されたデータを受け付けました。
            提出先 芝税務署
            受付番号 20250731185712915418
            受付日時 2025/07/31 18:57:12
            種目 消費税申告書
            課税期間 自 令和06年06月01日
            消費税及び地方消費税の合計税額 1,437,300円""",
            "filename": "1_国税.pdf",
            "expected": "3003_受信通知_消費税",
            "description": "メール詳細+種目消費税申告書のAND条件"
        },
        {
            "name": "消費税納付情報",
            "text": """事業者コード：0564M0023 利用者名：メトロノーム株式会社
            メール詳細（納付区分番号通知）
            納付内容を確認し、以下のボタンより納付してください。
            納付先 芝税務署
            税目 消費税及地方消費税
            申告区分 確定申告
            納付区分 7426893372""",
            "filename": "2_国税.pdf",
            "expected": "3004_納付情報_消費税",
            "description": "納付区分番号通知+消費税及地方消費税のAND条件"
        },
        {
            "name": "都道府県税納付情報",
            "text": """発信日時 2025/07/31 19:05:34
            事業者コード：0564M0023 利用者名：メトロノーム株式会社
            納付情報発行結果
            納付情報が発行され、納付が可能になりました。
            税目:法人二税・特別税
            納税者の氏名（名称）:メトロノーム 株式会社
            発行元 地方税共同機構
            手続名 法人都道府県民税・事業税・特別法人事業税又は地方法人特別税確定申告""",
            "filename": "2_地方税.pdf",
            "expected": "1004_納付情報_都道府県",
            "description": "納付情報発行結果+法人二税・特別税のAND条件"
        },
        {
            "name": "市町村受信通知（蒲郡市）",
            "text": """発信日時 2025/07/31 18:46:42
            事業者コード：0564M0023 利用者名：メトロノーム 株式会社
            申告受付完了通知
            送信された申告データを受付けました。
            法人市民税（法人税割） 課税標準総額 847,000円
            法人市民税（法人税割） 申告納付税額 2,900円
            法人市民税（均等割） 申告納付税額 25,000円
            発行元 蒲郡市役所
            手続名 法人市町村民税 確定申告""",
            "filename": "4_地方税.pdf",
            "expected": "2003_受信通知_市町村",
            "description": "申告受付完了通知+法人市町村民税のAND条件"
        },
        {
            "name": "従来の申告書（AND条件なし）",
            "text": """内国法人の確定申告(青色)
            法人税及び地方法人税申告書
            事業年度分の法人税申告書
            差引確定法人税額 236,500円""",
            "filename": "01_内国法人の確定申告(青色)_メトロノーム株式会社.pdf",
            "expected": "0001_法人税及び地方法人税申告書",
            "description": "従来の最優先キーワード判定"
        }
    ]
    
    # テスト実行
    print(f"テストケース数: {len(test_cases)}")
    print("=" * 80)
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[TEST {i}] {test_case['name']}")
        print(f"説明: {test_case['description']}")
        print(f"期待値: {test_case['expected']}")
        
        # v5.0 分類実行
        result = classifier.classify_document_v5(test_case['text'], test_case['filename'])
        
        # 結果判定
        is_success = result.document_type == test_case['expected']
        status = "[SUCCESS]" if is_success else "[FAILED]"
        
        print(f"結果: {result.document_type}")
        print(f"判定方法: {result.classification_method}")
        print(f"信頼度: {result.confidence:.2f}")
        print(f"マッチキーワード: {result.matched_keywords}")
        print(f"ステータス: {status}")
        
        if is_success:
            success_count += 1
        else:
            print(f"期待値と異なる結果です")
        
        print("-" * 50)
    
    # 最終結果
    print(f"\n[RESULT SUMMARY]")
    print(f"成功: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
    
    if success_count == len(test_cases):
        print("すべてのテストが成功しました！v5.0 AND条件判定は正常に動作しています。")
    else:
        print(f"{len(test_cases) - success_count}件のテストが失敗しました。判定条件の見直しが必要です。")
    
    return success_count == len(test_cases)

def test_performance_comparison():
    """v4.0とv5.0の性能比較テスト"""
    print("\n" + "=" * 80)
    print("v4.0 vs v5.0 性能比較テスト")
    print("=" * 80)
    
    try:
        from core.classification import DocumentClassifier  # v4.0
        
        # テストデータ
        problem_text = """メール詳細 種目 法人税及び地方法人税申告書 受付番号 20250731185710521215 税目 法人税 消費税"""
        problem_filename = "test.pdf"
        
        # v4.0テスト
        classifier_v4 = DocumentClassifier(debug_mode=False)
        result_v4 = classifier_v4.classify_document(problem_text, problem_filename)
        
        # v5.0テスト  
        classifier_v5 = DocumentClassifierV5(debug_mode=False)
        result_v5 = classifier_v5.classify_document_v5(problem_text, problem_filename)
        
        print(f"テストデータ: 法人税受信通知（消費税キーワード混在）")
        print(f"v4.0結果: {result_v4.document_type} (信頼度: {result_v4.confidence:.2f})")
        print(f"v5.0結果: {result_v5.document_type} (信頼度: {result_v5.confidence:.2f})")
        
        # 期待される結果
        expected = "0003_受信通知_法人税"
        v4_correct = result_v4.document_type == expected
        v5_correct = result_v5.document_type == expected
        
        print(f"v4.0正解: {'OK' if v4_correct else 'NG'}")
        print(f"v5.0正解: {'OK' if v5_correct else 'NG'}")
        
        if v5_correct and not v4_correct:
            print("v5.0がv4.0の問題を解決しました！")
        elif v4_correct and v5_correct:
            print("両バージョンとも正解です")
        elif not v5_correct:
            print("v5.0でも問題が残っています")
            
    except ImportError:
        print("v4.0分類エンジンが見つからないため、比較テストをスキップします")

if __name__ == "__main__":
    # メインテスト実行
    success = test_v5_classification()
    
    print(f"\n{'='*80}")
    if success:
        print("v5.0システムの準備が完了しました！本格運用を開始できます。")
    else:
        print("v5.0システムに調整が必要です。ログを確認して条件を見直してください。")
    print("="*80)