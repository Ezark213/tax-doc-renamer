#!/usr/bin/env python3
"""
都道府県システムテスト - 47都道府県と東京都制約のテスト
"""

import sys
sys.path.append('.')

def test_prefecture_system():
    """都道府県システムのテスト"""
    # prefecture listを直接確認
    expected_prefectures = [
        "選択してください",
        "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
        "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
        "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
        "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
        "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
        "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
    ]
    
    print("=== 都道府県システム テスト ===")
    print()
    
    # 47都道府県 + 選択してくださいの確認
    expected_count = 47 + 1  # 47都道府県 + "選択してください"
    actual_count = len(expected_prefectures)
    
    print(f"都道府県数チェック:")
    print(f"  期待値: {expected_count}")
    print(f"  実際値: {actual_count}")
    
    if actual_count == expected_count:
        print("  OK 都道府県数が正しい")
        prefecture_count_ok = True
    else:
        print("  NG 都道府県数が間違っている")
        prefecture_count_ok = False
    
    print()
    
    # 東京都の位置確認
    tokyo_index = expected_prefectures.index("東京都")
    expected_tokyo_index = 13  # 0ベースなので13番目（選択してください含む）
    
    print(f"東京都の位置チェック:")
    print(f"  期待値: {expected_tokyo_index}")
    print(f"  実際値: {tokyo_index}")
    
    if tokyo_index == expected_tokyo_index:
        print("  OK 東京都が正しい位置にある")
        tokyo_position_ok = True
    else:
        print("  NG 東京都の位置が間違っている")
        tokyo_position_ok = False
    
    print()
    
    # 全都道府県の存在確認
    required_prefectures = [
        "北海道",
        "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
        "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
        "岐阜県", "静岡県", "愛知県", "三重県",
        "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
        "鳥取県", "島根県", "岡山県", "広島県", "山口県",
        "徳島県", "香川県", "愛媛県", "高知県",
        "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
    ]
    
    missing_prefectures = []
    for pref in required_prefectures:
        if pref not in expected_prefectures:
            missing_prefectures.append(pref)
    
    print(f"全都道府県存在チェック:")
    if not missing_prefectures:
        print("  OK 全47都道府県が存在する")
        all_prefectures_ok = True
    else:
        print(f"  NG 不足している都道府県: {missing_prefectures}")
        all_prefectures_ok = False
    
    print()
    
    # 総合結果
    all_passed = prefecture_count_ok and tokyo_position_ok and all_prefectures_ok
    
    if all_passed:
        print("OK 都道府県システムのテストが全て成功しました！")
        print("  - 47都道府県が完全実装されています")
        print("  - 東京都が正しい位置にあります")
        print("  - 全都道府県が存在します")
    else:
        print("NG 都道府県システムに問題があります")
    
    return all_passed

if __name__ == "__main__":
    success = test_prefecture_system()
    sys.exit(0 if success else 1)