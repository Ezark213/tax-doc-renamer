#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 メインテストのみ
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
    classifier = DocumentClassifierV5(debug_mode=False)
    
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

if __name__ == "__main__":
    test_v5_classification()