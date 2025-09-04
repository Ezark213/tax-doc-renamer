#!/usr/bin/env python3
"""
UI YYMM堅牢性テスト v5.3.5-ui-robust
UI YYMMの様々な入力形式をテスト
"""

import sys
import logging
from typing import Dict, Any

# モジュールパスの設定
import os
sys.path.insert(0, os.path.dirname(__file__))

from helpers.yymm_policy import require_ui_yymm, _normalize_yymm, resolve_yymm_by_policy
from core.yymm_resolver import resolve_yymm, YYMMSource


def setup_logging():
    """テスト用ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def test_normalize_yymm():
    """YYMM正規化テスト"""
    print("=== YYMM正規化テスト ===")
    
    test_cases = [
        # 基本形式
        ("2508", "2508"),
        ("25-08", "2508"),
        ("25/08", "2508"),
        ("25.08", "2508"),
        
        # 全角文字
        ("２５０８", "2508"),
        ("２５－０８", "2508"),
        ("２５／０８", "2508"),
        
        # 6桁フォーマット
        ("202508", "2508"),
        ("202412", "2412"),
        
        # 数値型
        (2508, "2508"),
        (202508, "2508"),
        
        # 無効な形式
        ("25", None),
        ("2513", None),  # 13月は無効
        ("abcd", None),
        ("", None),
        (None, None),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_val, expected in test_cases:
        result = _normalize_yymm(input_val)
        status = "OK" if result == expected else "NG"
        print(f"{status} {input_val} -> {result} (期待: {expected})")
        if result == expected:
            passed += 1
    
    print(f"\n結果: {passed}/{total} テスト通過\n")
    return passed == total


def test_require_ui_yymm():
    """UI YYMM要求テスト"""
    print("=== UI YYMM要求テスト ===")
    
    test_cases = [
        {
            "name": "基本yymm",
            "settings": {"yymm": "2508"},
            "expected_yymm": "2508",
            "expected_source": "UI_FORCED"
        },
        {
            "name": "ui.yymm階層",
            "settings": {"ui": {"yymm": "2507"}},
            "expected_yymm": "2507",
            "expected_source": "UI_FORCED"
        },
        {
            "name": "manual_yymm",
            "settings": {"manual_yymm": "2506"},
            "expected_yymm": "2506",
            "expected_source": "UI_FORCED"
        },
        {
            "name": "全角入力",
            "settings": {"yymm": "２５０５"},
            "expected_yymm": "2505",
            "expected_source": "UI_FORCED"
        },
        {
            "name": "区切り文字",
            "settings": {"yymm": "25-04"},
            "expected_yymm": "2504",
            "expected_source": "UI_FORCED"
        },
        {
            "name": "6桁形式",
            "settings": {"yymm": "202503"},
            "expected_yymm": "2503",
            "expected_source": "UI_FORCED"
        },
        {
            "name": "SimpleNamespace型",
            "settings": type('obj', (), {"yymm": "2502"})(),
            "expected_yymm": "2502",
            "expected_source": "UI_FORCED"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        try:
            yymm, source, meta = require_ui_yymm(test_case["settings"])
            expected_yymm = test_case["expected_yymm"]
            expected_source = test_case["expected_source"]
            
            if yymm == expected_yymm and source == expected_source:
                print(f"OK {test_case['name']}: {yymm} ({source})")
                passed += 1
            else:
                print(f"NG {test_case['name']}: {yymm} ({source}) - 期待: {expected_yymm} ({expected_source})")
        except ValueError as e:
            print(f"NG {test_case['name']}: エラー - {e}")
    
    # 失敗ケース
    try:
        require_ui_yymm({})
        print("NG 空辞書: 例外が発生すべき")
    except ValueError:
        print("OK 空辞書: 正常に例外発生")
        passed += 1
        total += 1
    
    print(f"\n結果: {passed}/{total} テスト通過\n")
    return passed == total


def test_policy_resolution():
    """ポリシー解決テスト"""
    print("=== ポリシー解決テスト ===")
    
    test_cases = [
        {
            "name": "UI強制コード・UI入力あり",
            "code": "6001",
            "settings": {"yymm": "2508"},
            "detected": None,
            "expected_yymm": "2508",
            "expected_source": "UI_FORCED"
        },
        {
            "name": "UI強制コード・UI入力なし",
            "code": "6001",
            "settings": {},
            "detected": None,
            "expected_yymm": None,
            "expected_source": "NEEDS_UI"
        },
        {
            "name": "通常コード・文書検出",
            "code": "0001",
            "settings": {},
            "detected": "2507",
            "expected_yymm": "2507",
            "expected_source": "DOC/HEURISTIC"
        },
        {
            "name": "通常コード・UIフォールバック",
            "code": "0001",
            "settings": {"yymm": "2506"},
            "detected": None,
            "expected_yymm": "2506",
            "expected_source": "UI_FALLBACK"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        yymm, source = resolve_yymm_by_policy(
            class_code=test_case["code"],
            ctx={"default_yymm": None},
            settings=test_case["settings"],
            detected=test_case["detected"]
        )
        
        expected_yymm = test_case["expected_yymm"]
        expected_source = test_case["expected_source"]
        
        if yymm == expected_yymm and source == expected_source:
            print(f"OK {test_case['name']}: {yymm} ({source})")
            passed += 1
        else:
            print(f"NG {test_case['name']}: {yymm} ({source}) - 期待: {expected_yymm} ({expected_source})")
    
    print(f"\n結果: {passed}/{total} テスト通過\n")
    return passed == total


def test_integrated_resolver():
    """統合リゾルバテスト"""
    print("=== 統合リゾルバテスト ===")
    
    from types import SimpleNamespace
    
    test_cases = [
        {
            "name": "UI強制コード・UI入力確認",
            "code": "6001",
            "ui_context": {"yymm": "2508"},
            "document": SimpleNamespace(text="固定資産台帳", filename="test.pdf"),
            "expected_yymm": "2508",
            "expected_source": YYMMSource.UI_FORCED
        },
        {
            "name": "UI強制コード・様々な入力形式",
            "code": "6002", 
            "ui_context": {"ui_yymm": "25/08"},
            "document": SimpleNamespace(text="一括償却資産", filename="test.pdf"),
            "expected_yymm": "2508",
            "expected_source": YYMMSource.UI_FORCED
        },
        {
            "name": "UI強制コード・全角入力",
            "code": "6003",
            "ui_context": {"manual_yymm": "２５０８"},
            "document": SimpleNamespace(text="少額減価償却", filename="test.pdf"),
            "expected_yymm": "2508", 
            "expected_source": YYMMSource.UI_FORCED
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        result = resolve_yymm(
            code=test_case["code"],
            document=test_case["document"],
            ui_context=test_case["ui_context"],
            batch_mode=True,
            file_id="test_file"
        )
        
        expected_yymm = test_case["expected_yymm"]
        expected_source = test_case["expected_source"]
        
        if result.yymm == expected_yymm and result.source == expected_source:
            print(f"OK {test_case['name']}: {result.yymm} ({result.source.value})")
            passed += 1
        else:
            print(f"NG {test_case['name']}: {result.yymm} ({result.source.value}) - 期待: {expected_yymm} ({expected_source.value})")
    
    print(f"\n結果: {passed}/{total} テスト通過\n")
    return passed == total


def main():
    """メインテスト実行"""
    setup_logging()
    
    print("UI YYMM堅牢性テスト開始")
    print("=" * 60)
    
    all_passed = True
    
    # テスト実行
    all_passed &= test_normalize_yymm()
    all_passed &= test_require_ui_yymm()
    all_passed &= test_policy_resolution()
    all_passed &= test_integrated_resolver()
    
    # 結果出力
    print("=" * 60)
    if all_passed:
        print("SUCCESS: 全テスト成功！UI YYMM堅牢性が確認されました")
        print("OK UIで 2508 を入力していれば以下が確実に生成されます:")
        print("   - 6001_固定資産台帳_2508.pdf")
        print("   - 6002_一括償却資産明細表_2508.pdf") 
        print("   - 6003_少額減価償却資産明細表_2508.pdf")
        print("   - 0000_納付税額一覧表_2508.pdf")
        return 0
    else:
        print("FAILED: 一部テスト失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())