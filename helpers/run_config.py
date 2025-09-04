#!/usr/bin/env python3
"""
RunConfig - UI YYMM値の単一点集中管理
実行時コンフィグによる manual_yymm の一元化と全ジョブへの配布
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class RunConfig:
    """実行時設定 - UI YYMM値を単一点で管理"""
    manual_yymm: Optional[str] = None  # '2508' 等、UIから取得した正規化済み値
    override_yymm: bool = True         # UI値を最優先にするかどうか
    batch_mode: bool = True            # バッチ処理モード
    debug_mode: bool = False           # デバッグモード
    
    # メタデータ
    source_origin: str = "GUI"         # 設定の由来（GUI/CLI/API等）
    created_at: Optional[str] = None   # 作成タイムスタンプ
    
    def __post_init__(self):
        """初期化後の検証"""
        if self.manual_yymm:
            self.manual_yymm = self._normalize_yymm(self.manual_yymm)
    
    @staticmethod
    def _normalize_yymm(yymm: str) -> str:
        """YYMM値の正規化（全角対応・厳密チェック）"""
        if not yymm:
            return None
            
        import unicodedata
        
        # 全角→半角・空白除去
        yymm_str = unicodedata.normalize("NFKC", str(yymm)).strip()
        
        # 4桁数字チェック
        if re.fullmatch(r"\d{4}", yymm_str):
            return yymm_str
        
        # 25/08, 25-08 等の変換
        m = re.match(r"^(\d{2})[^\d]?(\d{2})$", yymm_str)
        if m:
            return m.group(1) + m.group(2)
        
        # 2025-08 → 2508 の変換
        m = re.match(r"^(\d{4})[^\d]?(\d{2})$", yymm_str)
        if m:
            return yymm_str[2:4] + yymm_str[-2:]
        
        # 不正な形式
        raise ValueError(f"Invalid YYMM format: {yymm_str}")
    
    def has_manual_yymm(self) -> bool:
        """手動YYMM値が設定されているかチェック"""
        return bool(self.manual_yymm)
    
    def get_yymm_source(self) -> str:
        """YYMM値のソースを返す"""
        return "UI" if self.has_manual_yymm() else "AUTO"
    
    def validate_for_ui_required_codes(self, classification_code: str) -> None:
        """UI必須コードの検証"""
        code4 = classification_code[:4] if classification_code else ""
        ui_required_codes = {"6001", "6002", "6003", "0000"}
        
        if code4 in ui_required_codes and not self.has_manual_yymm():
            raise ValueError(
                f"[FATAL][YYMM] UI value required but missing for {code4}. "
                f"manual_yymm={self.manual_yymm}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "manual_yymm": self.manual_yymm,
            "override_yymm": self.override_yymm,
            "batch_mode": self.batch_mode,
            "debug_mode": self.debug_mode,
            "source_origin": self.source_origin,
            "created_at": self.created_at,
            "has_manual_yymm": self.has_manual_yymm(),
            "yymm_source": self.get_yymm_source()
        }
    
    @classmethod
    def from_ui_input(cls, yymm_input: str, 
                      batch_mode: bool = True, 
                      debug_mode: bool = False) -> 'RunConfig':
        """UI入力からRunConfigを作成"""
        try:
            normalized = cls._normalize_yymm(yymm_input) if yymm_input else None
            return cls(
                manual_yymm=normalized,
                override_yymm=True,
                batch_mode=batch_mode,
                debug_mode=debug_mode,
                source_origin="GUI"
            )
        except ValueError as e:
            logger.error(f"Failed to create RunConfig from UI input: {e}")
            raise
    
    def log_config(self) -> None:
        """設定をログ出力"""
        if self.has_manual_yymm():
            logger.info(f"[RUN_CONFIG] manual_yymm={self.manual_yymm} source=UI override={self.override_yymm}")
        else:
            logger.info(f"[RUN_CONFIG] manual_yymm=None source=AUTO batch_mode={self.batch_mode}")
        
        if self.debug_mode:
            logger.debug(f"[RUN_CONFIG] full_config={self.to_dict()}")


# ユーティリティ関数

def create_run_config_from_gui(yymm_var_value: str, 
                               batch_mode: bool = True,
                               debug_mode: bool = False) -> RunConfig:
    """GUIからRunConfigを作成（便利関数）"""
    return RunConfig.from_ui_input(
        yymm_input=yymm_var_value,
        batch_mode=batch_mode,
        debug_mode=debug_mode
    )


def validate_yymm_format(yymm: str) -> bool:
    """YYMM形式の妥当性チェック"""
    try:
        RunConfig._normalize_yymm(yymm)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    # テスト実行
    import sys
    
    print("RunConfig テスト実行")
    print("=" * 50)
    
    test_cases = [
        {"input": "2508", "expected": "2508"},
        {"input": "25/08", "expected": "2508"},
        {"input": "25-08", "expected": "2508"},
        {"input": "2025-08", "expected": "2508"},
        {"input": "", "expected": None},
        {"input": None, "expected": None}
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nテスト {i}: input='{case['input']}'")
        try:
            config = RunConfig.from_ui_input(case["input"])
            result = config.manual_yymm
            expected = case["expected"]
            status = "OK" if result == expected else "NG"
            print(f"  結果: {result} (期待値: {expected}) [{status}]")
            print(f"  has_manual_yymm: {config.has_manual_yymm()}")
            print(f"  yymm_source: {config.get_yymm_source()}")
        except Exception as e:
            print(f"  エラー: {e}")
    
    # UI必須コードテスト
    print(f"\nUI必須コードテスト")
    config_with_ui = RunConfig.from_ui_input("2508")
    config_without_ui = RunConfig.from_ui_input("")
    
    for code in ["6001", "6002", "6003", "0000", "1001"]:
        print(f"  {code} (UI有り): ", end="")
        try:
            config_with_ui.validate_for_ui_required_codes(code)
            print("OK")
        except ValueError as e:
            print(f"NG - {e}")
        
        print(f"  {code} (UI無し): ", end="")
        try:
            config_without_ui.validate_for_ui_required_codes(code)
            print("OK")
        except ValueError as e:
            print(f"EXPECTED_ERROR - {str(e)[:50]}...")
    
    print("\n" + "=" * 50)
    print("テスト完了")