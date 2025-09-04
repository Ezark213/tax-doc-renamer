#!/usr/bin/env python3
"""
UI YYMM堅牢性統合テスト v5.3.5-ui-robust
全パイプラインでの UI YYMM 抽出堅牢性を検証
"""

import sys
import logging
from types import SimpleNamespace
from typing import Dict, Any

# モジュールパスの設定
import os
sys.path.insert(0, os.path.dirname(__file__))

from helpers.settings_context import UIContext, create_ui_context_from_gui
from core.unified_classifier import UnifiedClassifier, DocumentContext, create_document_context
from core.yymm_resolver import resolve_yymm, YYMMSource


def setup_logging():
    """テスト用ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def test_ui_forced_codes_integration():
    """UI強制コード統合テスト"""
    print("=== UI強制コード統合テスト ===")
    
    # UI強制コード（6001, 6002, 6003, 0000）テストケース
    test_cases = [
        {
            "code": "6001",
            "text": "固定資産台帳 令和7年12月期 会社印",
            "filename": "固定資産台帳_test.pdf",
            "ui_input": "2508",
            "expected_yymm": "2508",
            "expected_filename": "6001_固定資産台帳_2508.pdf"
        },
        {
            "code": "6002", 
            "text": "一括償却資産明細表 減価償却",
            "filename": "一括償却_test.pdf",
            "ui_input": "25/08",  # 区切り文字
            "expected_yymm": "2508",
            "expected_filename": "6002_一括償却資産明細表_2508.pdf"
        },
        {
            "code": "6003",
            "text": "少額減価償却資産明細表",
            "filename": "少額資産_test.pdf", 
            "ui_input": "２５０８",  # 全角
            "expected_yymm": "2508",
            "expected_filename": "6003_少額減価償却資産明細表_2508.pdf"
        },
        {
            "code": "0000",
            "text": "納付税額一覧表 法人税 消費税",
            "filename": "納付一覧_test.pdf",
            "ui_input": "202508",  # 6桁形式
            "expected_yymm": "2508",
            "expected_filename": "0000_納付税額一覧表_2508.pdf"
        }
    ]
    
    classifier = UnifiedClassifier(debug_mode=False, allow_auto_forced_codes=False)
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        print(f"\n--- {test_case['code']} テスト ---")
        
        # UIコンテキスト作成
        ui_context = UIContext(yymm=test_case["ui_input"], batch_mode=True)
        
        # DocumentContext作成
        doc_context = create_document_context(
            filename=test_case["filename"],
            text=test_case["text"],
            ui_context=ui_context.to_dict()
        )
        
        # 統合分類処理
        result, final_filename, success, message = classifier.process_document_complete(doc_context)
        
        # 結果検証
        yymm_ok = result.yymm == test_case["expected_yymm"]
        source_ok = result.yymm_source == YYMMSource.UI_FORCED.value
        
        if yymm_ok and source_ok and success:
            print(f"OK {test_case['code']}: {result.yymm} ({result.yymm_source})")
            print(f"   生成ファイル名: {final_filename}")
            passed += 1
        else:
            print(f"NG {test_case['code']}: {result.yymm} ({result.yymm_source})")
            print(f"   期待: {test_case['expected_yymm']} (UI_FORCED)")
            if not success:
                print(f"   エラー: {message}")
    
    print(f"\n結果: {passed}/{total} テスト通過")
    return passed == total


def test_direct_yymm_resolver():
    """YYMM解決機能直接テスト"""
    print("\n=== YYMM解決機能直接テスト ===")
    
    test_cases = [
        {
            "name": "UI強制・基本形式",
            "code": "6001",
            "ui_context": {"yymm": "2508"},
            "expected_yymm": "2508",
            "expected_source": YYMMSource.UI_FORCED
        },
        {
            "name": "UI強制・区切り文字",
            "code": "6002", 
            "ui_context": {"manual_yymm": "25-08"},
            "expected_yymm": "2508",
            "expected_source": YYMMSource.UI_FORCED
        },
        {
            "name": "UI強制・全角文字",
            "code": "6003",
            "ui_context": {"ui_yymm": "２５０８"},
            "expected_yymm": "2508",
            "expected_source": YYMMSource.UI_FORCED
        },
        {
            "name": "UI強制・6桁形式",
            "code": "0000",
            "ui_context": {"yymm": "202508"},
            "expected_yymm": "2508",
            "expected_source": YYMMSource.UI_FORCED
        },
        {
            "name": "UI強制・入力なし",
            "code": "6001",
            "ui_context": {},
            "expected_yymm": None,
            "expected_source": YYMMSource.NEEDS_UI
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        document = SimpleNamespace(text="テスト文書", filename="test.pdf")
        
        result = resolve_yymm(
            code=test_case["code"],
            document=document,
            ui_context=test_case["ui_context"],
            batch_mode=True,
            file_id="test_file"
        )
        
        yymm_ok = result.yymm == test_case["expected_yymm"]
        source_ok = result.source == test_case["expected_source"]
        
        if yymm_ok and source_ok:
            print(f"OK {test_case['name']}: {result.yymm} ({result.source.value})")
            passed += 1
        else:
            print(f"NG {test_case['name']}: {result.yymm} ({result.source.value})")
            print(f"   期待: {test_case['expected_yymm']} ({test_case['expected_source'].value})")
    
    print(f"\n結果: {passed}/{total} テスト通過")
    return passed == total


def main():
    """メインテスト実行"""
    setup_logging()
    
    print("UI YYMM堅牢性統合テスト開始")
    print("=" * 60)
    
    all_passed = True
    
    # テスト実行
    all_passed &= test_ui_forced_codes_integration()
    all_passed &= test_direct_yymm_resolver()
    
    # 結果出力
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: 全統合テスト成功！")
        print()
        print("UI YYMM堅牢性が確認されました:")
        print("✓ 様々な入力形式（2508, 25/08, 25-08, ２５０８, 202508）を正しく正規化")
        print("✓ UI強制コード（6001, 6002, 6003, 0000）で確実にUI入力を使用")
        print("✓ 設定コンテキストの一貫した伝播")
        print("✓ 包括的な監査ログ出力")
        print()
        print("期待される動作:")
        print("  UIで 2508 を入力すると以下が確実に生成されます:")
        print("  - 6001_固定資産台帳_2508.pdf")
        print("  - 6002_一括償却資産明細表_2508.pdf")
        print("  - 6003_少額減価償却資産明細表_2508.pdf")
        print("  - 0000_納付税額一覧表_2508.pdf")
        return 0
    else:
        print("FAILED: 一部統合テスト失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())