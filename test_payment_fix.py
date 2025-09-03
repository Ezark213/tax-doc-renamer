#!/usr/bin/env python3
"""
地方税納付情報分類エラー修正テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.domain import code_domain, is_overlay_allowed
from helpers.final_label_resolver import finalize_label, FinalLabelResult

def test_payment_codes():
    """納付情報コードのオーバーレイ禁止テスト"""
    print("=== Payment Code Overlay Protection Test ===")
    
    # テスト対象の納付情報コード
    payment_codes = ["1004", "2004"]
    
    for code in payment_codes:
        domain = code_domain(code)
        overlay_allowed = is_overlay_allowed(code)
        
        print(f"Code: {code}")
        print(f"  Domain: {domain}")
        print(f"  Overlay Allowed: {overlay_allowed}")
        
        # overlay_allowed が False であることを確認
        assert not overlay_allowed, f"Payment code {code} should not allow overlay"
        print(f"  [OK] Protection working correctly")
        print()

def test_finalize_label():
    """最終ラベル確定処理テスト"""
    print("=== Final Label Resolution Test ===")
    
    # モックオブジェクト
    class MockContext:
        def __init__(self):
            self.gui_yymm = "2508"
            self.last_class = None
            self.jurisdiction_hint = None
            self.selected_set_id = None
            self.yymm_source = None
    
    class MockSettings:
        def __init__(self):
            self.gui_yymm = "2508"
    
    ctx = MockContext()
    settings = MockSettings()
    
    # 納付情報コードのテスト
    test_cases = [
        ("1004_納付情報", "1004_納付情報_2508.pdf"),
        ("2004_納付情報", "2004_納付情報_2508.pdf"),
        ("1001_申告書", "1001_申告書_2508.pdf"),  # 通常の地方税はそのまま
    ]
    
    for base_class, expected_filename in test_cases:
        result = finalize_label(base_class, ctx, settings)
        
        print(f"Base Class: {base_class}")
        print(f"  Final Label: {result.final_label}")
        print(f"  Expected: {expected_filename}")
        print(f"  Overlay Applied: {result.overlay_applied}")
        
        # 納付情報コードの場合、オーバーレイが適用されないことを確認
        if base_class.endswith("_納付情報"):
            assert not result.overlay_applied, f"Payment code should not have overlay applied"
            print(f"  [OK] No overlay applied correctly")
        
        assert result.final_label == expected_filename, f"Expected {expected_filename}, got {result.final_label}"
        print(f"  [OK] Final label correct")
        print()

if __name__ == "__main__":
    try:
        test_payment_codes()
        test_finalize_label()
        print("[SUCCESS] All tests passed!")
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()