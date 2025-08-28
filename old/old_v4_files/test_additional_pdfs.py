#!/usr/bin/env python3
"""
追加の失敗PDFファイルでv5.0テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.classification_v5 import DocumentClassifierV5

def test_additional_failed_pdfs():
    """追加の失敗PDFでv5.0テスト"""
    print("=== v5.0システム 追加失敗PDFテスト ===")
    print()
    
    classifier = DocumentClassifierV5(debug_mode=False)
    
    # 追加テストケース
    additional_cases = [
        {
            "name": "消費税受信通知（元々1_国税）",
            "text": """事業者コード：0564M0023 利用者名：メトロノーム株式会社
            メール詳細
            送信されたデータを受け付けました。
            なお、後日、内容の確認のため、担当職員からご連絡させていただく場合があり
            ますので、ご了承ください。
            提出先 芝税務署
            利用者識別番号 2300082330910050
            氏名又は名称 メトロノーム株式会社
            代表者等氏名 島崎 洋輔
            受付番号 20250731185712915418
            受付日時 2025/07/31 18:57:12
            種目 消費税申告書
            申告の種類 確定
            課税期間 自 令和06年06月01日
            至 令和07年05月31日
            課税標準額 150,823,000円
            消費税及び地方消費税の合計
            （納付又は還付）税額 1,437,300円""",
            "filename": "3003_受信通知_2508【元々1_国税】.pdf",
            "expected": "3003_受信通知_消費税",
            "description": "消費税受信通知のAND条件判定"
        }
    ]
    
    # テスト実行
    print(f"追加テストケース数: {len(additional_cases)}")
    print("=" * 60)
    
    success_count = 0
    
    for i, test_case in enumerate(additional_cases, 1):
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
            # デバッグ情報表示
            print("デバッグ情報を確認してください。")
        
        print("-" * 50)
    
    # 最終結果
    print(f"\n[RESULT SUMMARY]")
    print(f"成功: {success_count}/{len(additional_cases)} ({success_count/len(additional_cases)*100:.1f}%)")
    
    if success_count == len(additional_cases):
        print("追加テストが全て成功しました！")
    else:
        print(f"{len(additional_cases) - success_count}件のテストが失敗しました。")
    
    return success_count == len(additional_cases)

def test_comprehensive_validation():
    """包括的な検証テスト"""
    print("\n" + "=" * 60)
    print("包括的検証テスト - 全パターン")
    print("=" * 60)
    
    classifier = DocumentClassifierV5(debug_mode=False)
    
    # 全体的なテストケース（既存 + 追加）
    all_test_cases = [
        # 国税関連
        {
            "name": "法人税受信通知",
            "content": "メール詳細 種目 法人税及び地方法人税申告書 受付番号 20250731185710521215",
            "expected": "0003_受信通知_法人税"
        },
        {
            "name": "法人税納付情報",
            "content": "メール詳細（納付区分番号通知） 税目 法人税及地方法人税 申告区分（法人税） 確定申告",
            "expected": "0004_納付情報_法人税"
        },
        {
            "name": "消費税受信通知",
            "content": "メール詳細 種目 消費税申告書 受付番号 20250731185712915418",
            "expected": "3003_受信通知_消費税"
        },
        {
            "name": "消費税納付情報",
            "content": "メール詳細（納付区分番号通知） 税目 消費税及地方消費税 申告区分 確定申告",
            "expected": "3004_納付情報_消費税"
        },
        
        # 地方税関連
        {
            "name": "都道府県税納付情報",
            "content": "納付情報発行結果 税目:法人二税・特別税 発行元 地方税共同機構",
            "expected": "1004_納付情報_都道府県"
        },
        {
            "name": "市町村受信通知",
            "content": "申告受付完了通知 法人市民税（法人税割） 申告納付税額 2,900円 蒲郡市役所",
            "expected": "2003_受信通知_市町村"
        },
        
        # 従来の申告書
        {
            "name": "法人税申告書",
            "content": "内国法人の確定申告(青色) 法人税及び地方法人税申告書 差引確定法人税額 236,500円",
            "expected": "0001_法人税及び地方法人税申告書"
        },
        {
            "name": "消費税申告書",
            "content": "消費税及び地方消費税申告(一般・法人) 課税期間分の消費税 基準期間の",
            "expected": "3001_消費税及び地方消費税申告書"
        }
    ]
    
    print(f"総テストケース数: {len(all_test_cases)}")
    print()
    
    success_count = 0
    
    for i, case in enumerate(all_test_cases, 1):
        result = classifier.classify_document_v5(case['content'], f"test_{i}.pdf")
        is_success = result.document_type == case['expected']
        
        status = "[OK]" if is_success else "[NG]"
        print(f"{i:2d}. {case['name']:<20} : {result.document_type:<30} {status}")
        
        if is_success:
            success_count += 1
    
    accuracy = success_count / len(all_test_cases) * 100
    print(f"\n総合結果: {success_count}/{len(all_test_cases)} ({accuracy:.1f}%)")
    
    if accuracy == 100.0:
        print("全てのテストケースで完璧な分類を達成しました！")
        print("v5.0システムは本格運用準備完了です。")
    else:
        print(f"{len(all_test_cases) - success_count}件で問題が発生しています。")
    
    return accuracy == 100.0

if __name__ == "__main__":
    # 追加PDFテスト
    additional_success = test_additional_failed_pdfs()
    
    # 包括的検証
    comprehensive_success = test_comprehensive_validation()
    
    print("\n" + "=" * 60)
    print("最終検証結果")
    print("=" * 60)
    
    if additional_success and comprehensive_success:
        print("🎉 v5.0システムが全ての検証をパスしました！")
        print("✅ 追加失敗PDFテスト: 成功")
        print("✅ 包括的検証テスト: 成功") 
        print("\n🚀 本格運用開始可能です。")
    else:
        print("⚠️ 一部の検証で問題が発生しました:")
        if not additional_success:
            print("❌ 追加失敗PDFテスト: 失敗")
        if not comprehensive_success:
            print("❌ 包括的検証テスト: 失敗")
        print("\n🔧 システム調整が必要です。")
    
    print("=" * 60)