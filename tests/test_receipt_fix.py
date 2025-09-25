#!/usr/bin/env python3
"""
受信通知連番修正の動作検証テスト
修正前後の動作を比較して正しく動作することを確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.job_context import JobContext
from helpers.seq_policy import ReceiptSequencer

def test_scenario_1_tokyo_with_others():
    """
    シナリオ1: 東京都＋他都道府県の場合
    セット1：東京都（市町村なし）
    セット2：大分県大分市
    セット3：奈良県奈良市

    期待値:
    - 1003 東京都受信通知
    - 1013 大分県受信通知
    - 1023 奈良県受信通知
    - 2003 大分市受信通知（東京都繰り上がりで2003）
    - 2013 奈良市受信通知
    """
    print("\n=== シナリオ1: 東京都＋他都道府県 ===")

    # ジョブコンテキスト作成
    ctx = JobContext(
        job_id="test_1",
        confirmed_yymm="2508",
        yymm_source="UI",
        run_config=None
    )

    # 自治体セット設定
    ctx.current_municipality_sets = {
        1: {'prefecture': '東京都', 'city': ''},
        2: {'prefecture': '大分県', 'city': '大分市'},
        3: {'prefecture': '奈良県', 'city': '奈良市'}
    }

    sequencer = ReceiptSequencer(ctx)

    # 都道府県受信通知のテスト
    tokyo_code = sequencer.assign_pref_seq("1003_受信通知", "東京都")
    oita_code = sequencer.assign_pref_seq("1003_受信通知", "大分県")
    nara_code = sequencer.assign_pref_seq("1003_受信通知", "奈良県")

    print(f"都道府県受信通知:")
    print(f"  東京都: {tokyo_code} (期待値: 1003)")
    print(f"  大分県: {oita_code} (期待値: 1013)")
    print(f"  奈良県: {nara_code} (期待値: 1023)")

    # 市町村受信通知のテスト
    oita_city_code = sequencer.assign_city_seq("2003_受信通知", "大分県", "大分市")
    nara_city_code = sequencer.assign_city_seq("2003_受信通知", "奈良県", "奈良市")

    print(f"市町村受信通知:")
    print(f"  大分市: {oita_city_code} (期待値: 2003) ← 東京都繰り上がり")
    print(f"  奈良市: {nara_city_code} (期待値: 2013)")

    # 検証
    assert tokyo_code == "1003", f"東京都: 期待値1003、実際{tokyo_code}"
    assert oita_code == "1013", f"大分県: 期待値1013、実際{oita_code}"
    assert nara_code == "1023", f"奈良県: 期待値1023、実際{nara_code}"
    assert oita_city_code == "2003", f"大分市: 期待値2003、実際{oita_city_code}"
    assert nara_city_code == "2013", f"奈良市: 期待値2013、実際{nara_city_code}"

    print("シナリオ1 PASSED")

def test_scenario_2_no_tokyo():
    """
    シナリオ2: 東京都なしの場合
    セット1：奈良県奈良市
    セット2：大分県大分市

    期待値:
    - 1003 奈良県受信通知
    - 1013 大分県受信通知
    - 2003 奈良市受信通知（東京都なしで繰り上がりなし）
    - 2013 大分市受信通知
    """
    print("\n=== シナリオ2: 東京都なし ===")

    # ジョブコンテキスト作成
    ctx = JobContext(
        job_id="test_2",
        confirmed_yymm="2508",
        yymm_source="UI",
        run_config=None
    )

    # 自治体セット設定
    ctx.current_municipality_sets = {
        1: {'prefecture': '奈良県', 'city': '奈良市'},
        2: {'prefecture': '大分県', 'city': '大分市'}
    }

    sequencer = ReceiptSequencer(ctx)

    # 都道府県受信通知のテスト
    nara_code = sequencer.assign_pref_seq("1003_受信通知", "奈良県")
    oita_code = sequencer.assign_pref_seq("1003_受信通知", "大分県")

    print(f"都道府県受信通知:")
    print(f"  奈良県: {nara_code} (期待値: 1003)")
    print(f"  大分県: {oita_code} (期待値: 1013)")

    # 市町村受信通知のテスト
    nara_city_code = sequencer.assign_city_seq("2003_受信通知", "奈良県", "奈良市")
    oita_city_code = sequencer.assign_city_seq("2003_受信通知", "大分県", "大分市")

    print(f"市町村受信通知:")
    print(f"  奈良市: {nara_city_code} (期待値: 2003) ← 東京都なしで繰り上がりなし")
    print(f"  大分市: {oita_city_code} (期待値: 2013)")

    # 検証
    assert nara_code == "1003", f"奈良県: 期待値1003、実際{nara_code}"
    assert oita_code == "1013", f"大分県: 期待値1013、実際{oita_code}"
    assert nara_city_code == "2003", f"奈良市: 期待値2003、実際{nara_city_code}"
    assert oita_city_code == "2013", f"大分市: 期待値2013、実際{oita_city_code}"

    print("シナリオ2 PASSED")

def test_scenario_3_tokyo_with_city():
    """
    シナリオ3: 東京都に市町村ありの場合（エッジケース）
    セット1：東京都新宿区
    セット2：大分県大分市

    期待値: 東京都に市町村があるため繰り上がりなし
    - 1003 東京都受信通知
    - 1013 大分県受信通知
    - 2003 新宿区受信通知（繰り上がりなし）
    - 2013 大分市受信通知
    """
    print("\n=== シナリオ3: 東京都に市町村あり（エッジケース） ===")

    # ジョブコンテキスト作成
    ctx = JobContext(
        job_id="test_3",
        confirmed_yymm="2508",
        yymm_source="UI",
        run_config=None
    )

    # 自治体セット設定
    ctx.current_municipality_sets = {
        1: {'prefecture': '東京都', 'city': '新宿区'},
        2: {'prefecture': '大分県', 'city': '大分市'}
    }

    sequencer = ReceiptSequencer(ctx)

    # 都道府県受信通知のテスト
    tokyo_code = sequencer.assign_pref_seq("1003_受信通知", "東京都")
    oita_code = sequencer.assign_pref_seq("1003_受信通知", "大分県")

    print(f"都道府県受信通知:")
    print(f"  東京都: {tokyo_code} (期待値: 1003)")
    print(f"  大分県: {oita_code} (期待値: 1013)")

    # 市町村受信通知のテスト
    shinjuku_code = sequencer.assign_city_seq("2003_受信通知", "東京都", "新宿区")
    oita_city_code = sequencer.assign_city_seq("2003_受信通知", "大分県", "大分市")

    print(f"市町村受信通知:")
    print(f"  新宿区: {shinjuku_code} (期待値: 2003) ← 東京都に市町村ありで繰り上がりなし")
    print(f"  大分市: {oita_city_code} (期待値: 2013)")

    # 検証
    assert tokyo_code == "1003", f"東京都: 期待値1003、実際{tokyo_code}"
    assert oita_code == "1013", f"大分県: 期待値1013、実際{oita_code}"
    assert shinjuku_code == "2003", f"新宿区: 期待値2003、実際{shinjuku_code}"
    assert oita_city_code == "2013", f"大分市: 期待値2013、実際{oita_city_code}"

    print("シナリオ3 PASSED")

if __name__ == "__main__":
    print("受信通知連番修正の動作検証テスト開始")

    try:
        test_scenario_1_tokyo_with_others()
        test_scenario_2_no_tokyo()
        test_scenario_3_tokyo_with_city()

        print("\n全テストケース PASSED - 修正が正常に動作しています！")

    except Exception as e:
        print(f"\nテスト失敗: {e}")
        sys.exit(1)