#!/usr/bin/env python3
"""
汎用Tokyo skip logic包括的テスト
市町村受信通知連番の東京都繰り上げロジック検証
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.seq_policy import (
    analyze_prefecture_sets,
    generate_receipt_number_generic
)

def test_tokyo_skip_scenario_1():
    """
    テストパターン1: 東京都 + 他県市
    期待結果: 東京都スキップで市町村が繰り上がり
    """
    print("\n=== テストパターン1: 東京都 + 他県市 ===")

    set_config = {
        1: {'prefecture': '東京都', 'city': ''},
        2: {'prefecture': '愛知県', 'city': '蒲郡市'},
        3: {'prefecture': '福岡県', 'city': '福岡市'}
    }

    # セット解析テスト
    prefecture_list, municipality_list, has_tokyo, tokyo_position = analyze_prefecture_sets(set_config)

    print(f"セット解析結果:")
    print(f"  都道府県リスト: {prefecture_list}")
    print(f"  市町村リスト: {[f\"{m['prefecture']} {m['city']}\" for m in municipality_list]}")
    print(f"  東京都存在: {has_tokyo}, 位置: {tokyo_position}")

    # 都道府県受信通知テスト
    tokyo_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '東京都'},
        set_config
    )
    aichi_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '愛知県'},
        set_config
    )
    fukuoka_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '福岡県'},
        set_config
    )

    print(f"\n都道府県受信通知:")
    print(f"  東京都: {tokyo_receipt} (期待値: 1003)")
    print(f"  愛知県: {aichi_receipt} (期待値: 1013)")
    print(f"  福岡県: {fukuoka_receipt} (期待値: 1023)")

    # 市町村受信通知テスト（Tokyo skip適用）
    gamagori_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '愛知県', 'city': '蒲郡市'},
        set_config
    )
    fukuoka_city_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '福岡県', 'city': '福岡市'},
        set_config
    )

    print(f"\n市町村受信通知（Tokyo skip適用）:")
    print(f"  蒲郡市: {gamagori_receipt} (期待値: 2003) ← 東京都スキップで繰り上がり")
    print(f"  福岡市: {fukuoka_city_receipt} (期待値: 2013)")

    # 検証
    assert tokyo_receipt == "1003", f"東京都都道府県: 期待値1003、実際{tokyo_receipt}"
    assert aichi_receipt == "1013", f"愛知県都道府県: 期待値1013、実際{aichi_receipt}"
    assert fukuoka_receipt == "1023", f"福岡県都道府県: 期待値1023、実際{fukuoka_receipt}"
    assert gamagori_receipt == "2003", f"蒲郡市: 期待値2003、実際{gamagori_receipt}"
    assert fukuoka_city_receipt == "2013", f"福岡市: 期待値2013、実際{fukuoka_city_receipt}"

    print("テストパターン1 PASSED ✅")

def test_tokyo_skip_scenario_2():
    """
    テストパターン2: 東京都なし（複数県市）
    期待結果: Tokyo skipなし、通常の連番
    """
    print("\n=== テストパターン2: 東京都なし（複数県市） ===")

    set_config = {
        1: {'prefecture': '愛知県', 'city': '名古屋市'},
        2: {'prefecture': '福岡県', 'city': '福岡市'}
    }

    # セット解析テスト
    prefecture_list, municipality_list, has_tokyo, tokyo_position = analyze_prefecture_sets(set_config)

    print(f"セット解析結果:")
    print(f"  都道府県リスト: {prefecture_list}")
    print(f"  市町村リスト: {[f\"{m['prefecture']} {m['city']}\" for m in municipality_list]}")
    print(f"  東京都存在: {has_tokyo}, 位置: {tokyo_position}")

    # 都道府県受信通知テスト
    aichi_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '愛知県'},
        set_config
    )
    fukuoka_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '福岡県'},
        set_config
    )

    print(f"\n都道府県受信通知:")
    print(f"  愛知県: {aichi_receipt} (期待値: 1003)")
    print(f"  福岡県: {fukuoka_receipt} (期待値: 1013)")

    # 市町村受信通知テスト（Tokyo skipなし）
    nagoya_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '愛知県', 'city': '名古屋市'},
        set_config
    )
    fukuoka_city_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '福岡県', 'city': '福岡市'},
        set_config
    )

    print(f"\n市町村受信通知（Tokyo skipなし）:")
    print(f"  名古屋市: {nagoya_receipt} (期待値: 2003)")
    print(f"  福岡市: {fukuoka_city_receipt} (期待値: 2013)")

    # 検証
    assert aichi_receipt == "1003", f"愛知県都道府県: 期待値1003、実際{aichi_receipt}"
    assert fukuoka_receipt == "1013", f"福岡県都道府県: 期待値1013、実際{fukuoka_receipt}"
    assert nagoya_receipt == "2003", f"名古屋市: 期待値2003、実際{nagoya_receipt}"
    assert fukuoka_city_receipt == "2013", f"福岡市: 期待値2013、実際{fukuoka_city_receipt}"

    print("テストパターン2 PASSED ✅")

def test_tokyo_skip_scenario_3():
    """
    テストパターン3: 東京都に市町村あり（エッジケース）
    期待結果: Tokyo skipなし（東京都に区があるため）
    """
    print("\n=== テストパターン3: 東京都に市町村あり（エッジケース） ===")

    set_config = {
        1: {'prefecture': '東京都', 'city': '新宿区'},
        2: {'prefecture': '愛知県', 'city': '蒲郡市'}
    }

    # セット解析テスト
    prefecture_list, municipality_list, has_tokyo, tokyo_position = analyze_prefecture_sets(set_config)

    print(f"セット解析結果:")
    print(f"  都道府県リスト: {prefecture_list}")
    print(f"  市町村リスト: {[f\"{m['prefecture']} {m['city']}\" for m in municipality_list]}")
    print(f"  東京都存在: {has_tokyo}, 位置: {tokyo_position}")

    # 都道府県受信通知テスト
    tokyo_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '東京都'},
        set_config
    )
    aichi_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '愛知県'},
        set_config
    )

    print(f"\n都道府県受信通知:")
    print(f"  東京都: {tokyo_receipt} (期待値: 1003)")
    print(f"  愛知県: {aichi_receipt} (期待値: 1013)")

    # 市町村受信通知テスト（Tokyo skipなし：東京都に区がある）
    shinjuku_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '東京都', 'city': '新宿区'},
        set_config
    )
    gamagori_receipt = generate_receipt_number_generic(
        "municipality_receipt",
        {'prefecture': '愛知県', 'city': '蒲郡市'},
        set_config
    )

    print(f"\n市町村受信通知（Tokyo skipなし：東京都に区がある）:")
    print(f"  新宿区: {shinjuku_receipt} (期待値: 2003)")
    print(f"  蒲郡市: {gamagori_receipt} (期待値: 2013)")

    # 検証
    assert tokyo_receipt == "1003", f"東京都都道府県: 期待値1003、実際{tokyo_receipt}"
    assert aichi_receipt == "1013", f"愛知県都道府県: 期待値1013、実際{aichi_receipt}"
    assert shinjuku_receipt == "2003", f"新宿区: 期待値2003、実際{shinjuku_receipt}"
    assert gamagori_receipt == "2013", f"蒲郡市: 期待値2013、実際{gamagori_receipt}"

    print("テストパターン3 PASSED ✅")

def test_tokyo_skip_scenario_4():
    """
    テストパターン4: 県のみ（市町村なし）
    期待結果: 市町村受信通知は生成されない
    """
    print("\n=== テストパターン4: 県のみ（市町村なし） ===")

    set_config = {
        1: {'prefecture': '北海道', 'city': ''},
        2: {'prefecture': '沖縄県', 'city': ''}
    }

    # セット解析テスト
    prefecture_list, municipality_list, has_tokyo, tokyo_position = analyze_prefecture_sets(set_config)

    print(f"セット解析結果:")
    print(f"  都道府県リスト: {prefecture_list}")
    print(f"  市町村リスト: {[f\"{m['prefecture']} {m['city']}\" for m in municipality_list]}")
    print(f"  東京都存在: {has_tokyo}, 位置: {tokyo_position}")

    # 都道府県受信通知テスト
    hokkaido_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '北海道'},
        set_config
    )
    okinawa_receipt = generate_receipt_number_generic(
        "prefecture_receipt",
        {'prefecture': '沖縄県'},
        set_config
    )

    print(f"\n都道府県受信通知:")
    print(f"  北海道: {hokkaido_receipt} (期待値: 1003)")
    print(f"  沖縄県: {okinawa_receipt} (期待値: 1013)")

    # 市町村受信通知は生成されない（市町村リストが空）
    print(f"\n市町村受信通知: 生成対象なし（市町村リストが空）")

    # 検証
    assert hokkaido_receipt == "1003", f"北海道都道府県: 期待値1003、実際{hokkaido_receipt}"
    assert okinawa_receipt == "1013", f"沖縄県都道府県: 期待値1013、実際{okinawa_receipt}"
    assert len(municipality_list) == 0, f"市町村リスト: 期待値0件、実際{len(municipality_list)}件"

    print("テストパターン4 PASSED ✅")

def test_error_handling():
    """
    エラーハンドリングテスト
    """
    print("\n=== エラーハンドリングテスト ===")

    set_config = {
        1: {'prefecture': '東京都', 'city': ''},
        2: {'prefecture': '愛知県', 'city': '蒲郡市'}
    }

    # 存在しない都道府県
    try:
        generate_receipt_number_generic(
            "prefecture_receipt",
            {'prefecture': '存在しない県'},
            set_config
        )
        assert False, "存在しない都道府県でエラーが発生するべき"
    except ValueError as e:
        print(f"✅ 存在しない都道府県エラー正常: {e}")

    # 存在しない市町村
    try:
        generate_receipt_number_generic(
            "municipality_receipt",
            {'prefecture': '愛知県', 'city': '存在しない市'},
            set_config
        )
        assert False, "存在しない市町村でエラーが発生するべき"
    except ValueError as e:
        print(f"✅ 存在しない市町村エラー正常: {e}")

    # 不正なdocument_type
    try:
        generate_receipt_number_generic(
            "invalid_type",
            {'prefecture': '東京都'},
            set_config
        )
        assert False, "不正なタイプでエラーが発生するべき"
    except ValueError as e:
        print(f"✅ 不正なタイプエラー正常: {e}")

    print("エラーハンドリングテスト PASSED ✅")

if __name__ == "__main__":
    print("汎用Tokyo skip logic包括的テスト開始")

    try:
        test_tokyo_skip_scenario_1()
        test_tokyo_skip_scenario_2()
        test_tokyo_skip_scenario_3()
        test_tokyo_skip_scenario_4()
        test_error_handling()

        print("\n🚀 全テストケース PASSED - 汎用Tokyo skip logic正常動作確認！")
        print("✅ 東京都繰り上げロジックが市町村受信通知で正しく適用されています")

    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)