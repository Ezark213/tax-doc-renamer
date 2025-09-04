#!/usr/bin/env python3
"""
グローバル除外機能のテストスクリプト v5.2.1
帳票系書類の分割除外テスト
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from core.pdf_processor import PDFProcessor

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)

def test_text_normalization():
    """テキスト正規化のテスト"""
    logger = setup_logging()
    processor = PDFProcessor(logger)
    
    test_cases = [
        ("一 括 償 却 資 産 明 細 表", "一括償却資産明細表"),
        ("少　額　減価償却資産明細表", "少額減価償却資産明細表"),
        ("資 産 コ ー ド", "資産コード"),
        ("取・得・価・額", "取得価額"),
        ("決算\n調整\n方式", "決算調整方式")
    ]
    
    logger.info("=== テキスト正規化テスト ===")
    all_passed = True
    
    for input_text, expected in test_cases:
        normalized = processor._normalize_text_for_exclude_check(input_text)
        if normalized == expected:
            logger.info(f"✅ '{input_text}' → '{normalized}'")
        else:
            logger.error(f"❌ '{input_text}' → '{normalized}' (expected: '{expected}')")
            all_passed = False
    
    return all_passed

def test_global_exclude_detection():
    """グローバル除外検出のテスト"""
    logger = setup_logging()
    processor = PDFProcessor(logger)
    
    test_cases = [
        {
            "name": "一括償却資産明細表",
            "texts": ["一括償却資産明細表", "決算調整方式", "資産コード: 001", "取得価額: 100,000"],
            "should_exclude": True
        },
        {
            "name": "少額減価償却資産明細表",
            "texts": ["少額減価償却資産明細表", "取得価額", "損金算入限度額"],
            "should_exclude": True
        },
        {
            "name": "通常の税務書類",
            "texts": ["法人税申告書", "受信通知", "納付情報"],
            "should_exclude": False
        },
        {
            "name": "構造ヒントのみ（2個以上）",
            "texts": ["決算調整方式により", "資産コードを入力", "取得価額を記載"],
            "should_exclude": True
        },
        {
            "name": "構造ヒント少数（1個のみ）",
            "texts": ["決算について", "その他の内容"],
            "should_exclude": False
        }
    ]
    
    logger.info("=== グローバル除外検出テスト ===")
    all_passed = True
    
    for case in test_cases:
        result = processor._check_global_excludes(case["texts"])
        expected = case["should_exclude"]
        
        if result == expected:
            status = "✅" if result else "✅ (正常非除外)"
            logger.info(f"{status} {case['name']}: 除外={result}")
        else:
            logger.error(f"❌ {case['name']}: 除外={result} (expected: {expected})")
            all_passed = False
    
    return all_passed

def test_bundle_detection_with_excludes():
    """束ね判定での除外機能テスト（疑似PDFで）"""
    logger = setup_logging()
    processor = PDFProcessor(logger)
    
    logger.info("=== 束ね判定除外テスト（疑似） ===")
    
    # 疑似的なテストケース
    exclude_sample_texts = [
        "一括償却資産明細表",
        "決算調整方式",
        "資産コード: 12345",
        "取得価額: 500,000円",
        "損金算入限度額: 300,000円"
    ]
    
    normal_sample_texts = [
        "法人税申告書",
        "受信通知",
        "申告受付完了",
        "納付情報",
        "1003番書類"
    ]
    
    # 除外されるべきケース
    exclude_result = processor._check_global_excludes(exclude_sample_texts)
    if exclude_result:
        logger.info("✅ 帳票系書類は正常に除外される")
    else:
        logger.error("❌ 帳票系書類が除外されていない")
        return False
    
    # 除外されないべきケース
    normal_result = processor._check_global_excludes(normal_sample_texts)
    if not normal_result:
        logger.info("✅ 通常の税務書類は除外されない")
    else:
        logger.error("❌ 通常の税務書類が誤って除外された")
        return False
    
    return True

def test_configuration_loading():
    """設定ファイル読み込みテスト"""
    logger = setup_logging()
    processor = PDFProcessor(logger)
    
    logger.info("=== 設定ファイル読み込みテスト ===")
    
    # グローバル除外設定が読み込まれているかチェック
    if "global_excludes" in processor.config:
        logger.info("✅ global_excludes設定が読み込まれている")
        
        excludes = processor.config["global_excludes"]
        
        # 必要な設定項目をチェック
        required_keys = ["title_exact_or_fuzzy", "structural_hints", "allow_bundle_if_excluded_hit"]
        for key in required_keys:
            if key in excludes:
                logger.info(f"✅ 設定項目 '{key}' が存在")
            else:
                logger.error(f"❌ 設定項目 '{key}' が不足")
                return False
        
        # タイトルキーワードの確認
        titles = excludes.get("title_exact_or_fuzzy", [])
        if "一括償却資産明細表" in titles and "少額減価償却資産明細表" in titles:
            logger.info("✅ 必要なタイトルキーワードが設定されている")
        else:
            logger.error("❌ タイトルキーワードが不足")
            return False
            
        return True
    else:
        logger.error("❌ global_excludes設定が読み込まれていない")
        return False

def main():
    """メインテスト実行"""
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("  グローバル除外機能テスト v5.2.1")
    logger.info("=" * 60)
    
    tests = [
        ("設定ファイル読み込み", test_configuration_loading),
        ("テキスト正規化", test_text_normalization),
        ("グローバル除外検出", test_global_exclude_detection),
        ("束ね判定除外機能", test_bundle_detection_with_excludes)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 テスト実行: {test_name}")
        logger.info("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"🎉 {test_name}: 成功")
            else:
                logger.error(f"💥 {test_name}: 失敗")
                
        except Exception as e:
            logger.error(f"💥 {test_name}: エラー - {e}")
            results.append((test_name, False))
    
    # 結果サマリー
    logger.info("\n" + "=" * 60)
    logger.info("  テスト結果サマリー")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
    
    logger.info(f"\n総合結果: {passed}/{total} テスト成功")
    
    if passed == total:
        logger.info("🎉 全てのテストが成功しました！")
        return True
    else:
        logger.error("💥 一部のテストが失敗しました")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)