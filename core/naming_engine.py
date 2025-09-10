#!/usr/bin/env python3
"""
Comprehensive naming system with prefecture upgrades v5.3.4
包括的命名システム - 県別コードアップグレードと三者一致保証
"""

import re
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from .domain import is_prefecture_tax, is_municipal_tax
from .overlay import PREFECTURE_CODE_MAP, MUNICIPALITY_CODE_MAP, resolve_municipality_label
from .logging_bridge import ClassifyResult, title_of
from .yymm_resolver import NeedsUserInputError, YYMMResult

logger = logging.getLogger(__name__)


@dataclass  
class NamingContext:
    """命名コンテキスト"""
    prefecture: Optional[str] = None
    city: Optional[str] = None
    set_id: Optional[int] = None
    source_filename: Optional[str] = None


class FilenameBuilder:
    """ファイル名構築クラス"""
    
    def __init__(self):
        self.forbidden_suffix_patterns = [
            r'_市町村_(\d{4})$',    # _市町村_YYMM → _YYMM
            r'_都道府県_(\d{4})$',  # _都道府県_YYMM → _YYMM  
            r'_市町村$',           # _市町村 → 削除
            r'_都道府県$'          # _都道府県 → 削除
        ]
    
    def build_filename(self, result: ClassifyResult, context: NamingContext) -> str:
        """
        ファイル名構築（v5.3.4三者一致対応）
        
        Args:
            result: 分類結果
            context: 命名コンテキスト
            
        Returns:
            str: 構築されたファイル名
            
        Raises:
            NeedsUserInputError: UI入力が必要な場合
        """
        logger.debug("Building filename for code: %s", result.display_code)
        
        # YYMM未確定チェック
        if not result.yymm:
            logger.warning("YYMM not available, UI input required for code: %s", result.display_code)
            raise NeedsUserInputError(result.display_code, "YYMM", result.yymm_source or "UNKNOWN")
        
        # 最終コード決定（オーバーレイ優先、最終保険付き）
        final_code = self._determine_final_code(result, context)
        
        # コア部分構築
        core = self._build_core_name(final_code, context, result.title)
        
        # 禁止サフィックス除去
        core = self._remove_forbidden_suffixes(core)
        
        # 最終ファイル名構築
        filename = f"{core}_{result.yymm}.pdf"
        
        logger.info("Built filename: %s", filename)
        return filename
    
    def _determine_final_code(self, result: ClassifyResult, context: NamingContext) -> str:
        """最終コード決定（保険処理付き）"""
        # 基本: オーバーレイ優先
        final_code = result.overlay_code or result.display_code
        
        # 県コードアップグレードの最終保険
        if final_code == "1001" and context.prefecture:
            upgraded = PREFECTURE_CODE_MAP.get(context.prefecture)
            if upgraded and upgraded != "1001":
                logger.info("Final insurance upgrade: %s -> %s (%s)", 
                           final_code, upgraded, context.prefecture)
                final_code = upgraded
        
        return final_code
    
    def _build_core_name(self, final_code: str, context: NamingContext, title: str) -> str:
        """コア名前部分の構築"""
        # 市町村税: 自治体名必須埋め込み
        if is_municipal_tax(final_code):
            return self._build_municipal_name(final_code, context)
        
        # 都道府県税: 都道府県名埋め込み
        if is_prefecture_tax(final_code):
            return self._build_prefecture_name(final_code, context)
        
        # その他: 基本形式
        return f"{final_code}_{title}"
    
    def _build_municipal_name(self, final_code: str, context: NamingContext) -> str:
        """市町村税ファイル名構築"""
        # 市町村ラベル解決（コードベース）
        muni_label = resolve_municipality_label(final_code)
        
        # コンテキストから自治体名を補完
        if context.prefecture and context.city and muni_label == "市町村不詳":
            muni_label = f"{context.prefecture}{context.city}"
            logger.debug("Municipal label from context: %s", muni_label)
        
        core = f"{final_code}_{muni_label}_市町村申告書"
        logger.debug("Municipal core built: %s", core)
        return core
    
    def _build_prefecture_name(self, final_code: str, context: NamingContext) -> str:
        """都道府県税ファイル名構築"""
        prefecture = context.prefecture or "都道府県不詳"
        
        # v5.3.4形式: XXXX_都道府県名_都道府県申告書
        core = f"{final_code}_{prefecture}_都道府県申告書"
        logger.debug("Prefecture core built: %s", core)
        return core
    
    def _remove_forbidden_suffixes(self, core: str) -> str:
        """禁止サフィックス除去"""
        original = core
        
        for pattern in self.forbidden_suffix_patterns:
            if re.search(pattern, core):
                # パターンに応じた置換
                if r'(\d{4})$' in pattern:
                    # _市町村_YYMM → _YYMM 等
                    core = re.sub(pattern, r'_\1', core)
                else:
                    # _市町村 → 削除 等
                    core = re.sub(pattern, '', core)
                
                logger.debug("Suffix removed: %s -> %s (pattern: %s)", original, core, pattern)
                original = core
        
        return core


class FilenameValidator:
    """ファイル名妥当性検証"""
    
    @staticmethod
    def validate_filename(filename: str) -> Tuple[bool, str]:
        """
        ファイル名の妥当性検証
        
        Returns:
            Tuple[bool, str]: (有効フラグ, エラーメッセージ)
        """
        if not filename:
            return False, "ファイル名が空です"
        
        # 基本形式チェック: XXXX_..._YYMM.pdf
        basic_pattern = r'^\d{4}_.*_\d{4}\.pdf$'
        if not re.match(basic_pattern, filename):
            return False, "基本形式（XXXX_..._YYMM.pdf）に合致しません"
        
        # YYMMの妥当性
        yymm_match = re.search(r'_(\d{4})\.pdf$', filename)
        if yymm_match:
            yymm = yymm_match.group(1)
            if not FilenameValidator._is_valid_yymm(yymm):
                return False, f"無効なYYMM形式: {yymm}"
        
        # 禁止文字チェック
        forbidden_chars = r'[<>:"|?*\\/]'
        if re.search(forbidden_chars, filename):
            return False, "禁止文字が含まれています"
        
        return True, ""
    
    @staticmethod
    def _is_valid_yymm(yymm: str) -> bool:
        """YYMM形式の妥当性検証"""
        try:
            year = int(yymm[:2])
            month = int(yymm[2:])
            return 1 <= year <= 99 and 1 <= month <= 12
        except (ValueError, IndexError):
            return False


def build_filename_from_result(result: ClassifyResult, context: NamingContext) -> str:
    """分類結果からファイル名を構築（メインAPI）"""
    builder = FilenameBuilder()
    return builder.build_filename(result, context)


def validate_and_build(result: ClassifyResult, context: NamingContext) -> Tuple[str, bool, str]:
    """
    ファイル名構築と妥当性検証
    
    Returns:
        Tuple[str, bool, str]: (ファイル名, 有効フラグ, メッセージ)
    """
    try:
        filename = build_filename_from_result(result, context)
        is_valid, message = FilenameValidator.validate_filename(filename)
        return filename, is_valid, message
    except NeedsUserInputError as e:
        return "", False, f"UI入力必要: {e.kind} for {e.code}"
    except Exception as e:
        logger.error("Filename building failed: %s", str(e))
        return "", False, f"構築エラー: {str(e)}"


def create_naming_examples() -> Dict[str, str]:
    """命名例の生成（ドキュメント用）"""
    examples = {
        # 国税
        "0001_法人税": "0001_法人税及び地方法人税申告書_2507.pdf",
        "0003_受信通知": "0003_受信通知_2507.pdf",
        
        # 地方税（v5.3.4県別コード化）
        "1011_愛知県税": "1011_愛知県_都道府県申告書_2507.pdf",
        "1021_福岡県税": "1021_福岡県_都道府県申告書_2507.pdf",
        "1001_東京都税": "1001_東京都_都道府県申告書_2507.pdf",
        
        "2001_愛知県蒲郡市": "2001_愛知県蒲郡市_市町村申告書_2507.pdf",
        "2011_福岡県福岡市": "2011_福岡県福岡市_市町村申告書_2507.pdf",
        
        # 消費税
        "3001_消費税": "3001_消費税及び地方消費税申告書_2507.pdf",
        "3002_添付資料": "3002_添付資料_消費税_2501.pdf",
        
        # 会計・資産
        "5001_決算書": "5001_決算書_2401.pdf",
        "6003_少額資産": "6003_少額減価償却資産明細表_2401.pdf",
        
        # 集計
        "7001_税区分": "7001_勘定科目別税区分集計表_2401.pdf"
    }
    return examples


if __name__ == "__main__":
    # テスト実行
    import sys
    from .yymm_resolver import YYMMSource
    
    print("包括的命名システム テスト")
    print("=" * 50)
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # テストケース
    test_cases = [
        # 国税（オーバーレイなし）
        (ClassifyResult("0001", None, "2507", "DOC/HEURISTIC", "法人税及び地方法人税申告書"),
         NamingContext(), "国税書類"),
        
        # 地方税（県別コード化）
        (ClassifyResult("1001", "1011", "2507", "DOC/HEURISTIC", "都道府県申告書申告書"),
         NamingContext("愛知県"), "愛知県都道府県税"),
        
        (ClassifyResult("2001", None, "2507", "DOC/HEURISTIC", "市町村申告書申告書"),
         NamingContext("愛知県", "蒲郡市"), "愛知県蒲郡市市民税"),
        
        # UI入力必須（エラーケース）
        (ClassifyResult("6003", None, None, "NONE", "少額減価償却資産明細表"),
         NamingContext(), "UI入力必須ケース"),
    ]
    
    builder = FilenameBuilder()
    
    for result, context, description in test_cases:
        print(f"\n--- {description} ---")
        print(f"Base: {result.display_code}, Overlay: {result.overlay_code}, YYMM: {result.yymm}")
        print(f"Context: pref={context.prefecture}, city={context.city}")
        
        try:
            filename = builder.build_filename(result, context)
            is_valid, msg = FilenameValidator.validate_filename(filename)
            
            print(f"生成ファイル名: {filename}")
            print(f"妥当性: {'✅ 有効' if is_valid else '❌ 無効'}")
            if not is_valid:
                print(f"エラー: {msg}")
                
        except NeedsUserInputError as e:
            print(f"⚠️  {e}")
        except Exception as e:
            print(f"❌ エラー: {e}")
    
    print("\n" + "=" * 50)
    print("命名例:")
    examples = create_naming_examples()
    for key, example in examples.items():
        print(f"  {key}: {example}")
    
    print("\nテスト完了")