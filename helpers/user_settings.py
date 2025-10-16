"""
ユーザー設定の永続化管理モジュール

税務書類リネームシステムにおけるユーザー設定（YYMM値、市町村設定等）の
保存・読み込み・管理を行う。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional


class UserSettingsManager:
    """ユーザー設定の永続化管理クラス"""

    def __init__(self, config_path: str = "config/user_settings.json"):
        """
        初期化

        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """設定ファイルからデータを読み込み"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.logger.info(f"設定ファイル読み込み完了: {self.config_path}")
                    return settings
            else:
                self.logger.info(f"設定ファイルが存在しないため、デフォルト設定を使用: {self.config_path}")
                return self._default_settings()
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"設定ファイル読み込みエラー、デフォルト設定を使用: {e}")
            return self._default_settings()

    def _default_settings(self) -> Dict[str, Any]:
        """デフォルト設定値を返す"""
        return {
            "version": "1.0.0",
            "yymm_value": "2508",
            "left_yymm_value": "2508",  # 左側機能用
            "process_type": "源泉税",  # v5.6.0: 処理種別の自動保存
            "main_prefix": "01",  # v5.6.0: 本票接尾辞の自動保存
            "receipt_prefix": "02",  # v5.6.0: 受信通知接尾辞の自動保存
            "normalize_english": False,  # v8.5.1: 全角英語→半角変換の自動保存
            "process_mode": "確定申告",  # v5.6.0: 処理モードの自動保存
            "municipalities": [
                {"prefecture": "東京都", "city": ""},
                {"prefecture": "愛知県", "city": "蒲郡市"},
                {"prefecture": "福岡県", "city": "福岡市"},
                {"prefecture": "", "city": ""},
                {"prefecture": "", "city": ""}
            ]
        }

    def _save_settings(self):
        """設定をファイルに保存"""
        try:
            # 設定ディレクトリが存在しない場合は作成
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル保存
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)

            self.logger.info(f"設定ファイル保存完了: {self.config_path}")

        except IOError as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")
            raise

    def get_yymm_value(self) -> str:
        """保存されたYYMM値を取得（右側機能用）"""
        return self.settings.get("yymm_value", "2508")

    def save_yymm_value(self, yymm: str):
        """YYMM値を保存（右側機能用）"""
        self.settings["yymm_value"] = yymm
        self._save_settings()

    def get_left_yymm_value(self) -> str:
        """保存された左側YYMM値を取得（左側機能用）"""
        return self.settings.get("left_yymm_value", "2508")

    def save_left_yymm_value(self, yymm: str):
        """左側YYMM値を保存（左側機能用）"""
        self.settings["left_yymm_value"] = yymm
        self._save_settings()

    def get_municipalities(self) -> List[Dict[str, str]]:
        """保存された市町村設定を取得"""
        return self.settings.get("municipalities", self._default_settings()["municipalities"])

    def save_municipalities(self, municipalities: List[Dict[str, str]]):
        """市町村設定を保存"""
        self.settings["municipalities"] = municipalities
        self._save_settings()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """任意の設定値を取得"""
        return self.settings.get(key, default)

    def save_setting(self, key: str, value: Any):
        """任意の設定値を保存"""
        self.settings[key] = value
        self._save_settings()

    def reset_to_defaults(self):
        """設定をデフォルト値にリセット"""
        self.settings = self._default_settings()
        self._save_settings()
        self.logger.info("設定をデフォルト値にリセットしました")


# ユーティリティ関数
def get_user_settings_manager() -> UserSettingsManager:
    """UserSettingsManagerのシングルトンインスタンスを取得"""
    if not hasattr(get_user_settings_manager, '_instance'):
        get_user_settings_manager._instance = UserSettingsManager()
    return get_user_settings_manager._instance