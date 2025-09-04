#!/usr/bin/env python3
"""
YYMM Hotfix 検証スクリプト - UI値最優先
"""

from helpers.yymm_policy import resolve_yymm_by_policy, FORCE_UI_YYMM_CODES
from types import SimpleNamespace

print("YYMM Hotfix 検証開始")
print("=" * 50)

# テスト設定
settings_with_ui = {"yymm": "2508"}
settings_empty = {}
ctx = SimpleNamespace(log=SimpleNamespace(info=print))

for code in ["6001", "6002", "6003", "0000"]:
    print(f"\n--- {code} テスト ---")
    
    # UI値ありのテスト
    try:
        yymm, source = resolve_yymm_by_policy(code, ctx, settings_with_ui)
        print(f"OK {code}: {yymm} ({source})")
    except Exception as e:
        print(f"NG {code}: {e}")
    
    # UI値なしのテスト（FATAL期待）
    try:
        yymm, source = resolve_yymm_by_policy(code, ctx, settings_empty)
        print(f"WARN {code} (empty): {yymm} ({source})")
    except ValueError as e:
        print(f"OK {code} (empty): FATAL期待通り - {e}")

print("\n" + "=" * 50)
print("期待される結果:")
print("- UI値あり: すべて 2508 (UI_FORCED)")
print("- UI値なし: すべて FATAL エラー")