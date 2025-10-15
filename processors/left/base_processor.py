"""
Base Left Processor - 左側処理の基底クラス

全ての左側プロセッサの共通機能を提供
"""

from typing import Callable, Optional, List, Dict
import os


class BaseLeftProcessor:
    """
    左側処理プロセッサの基底クラス

    全ての左側プロセッサ（源泉税、法定調書、給与、償却資産、申請届出）の
    共通機能を提供します。
    """

    def __init__(self, log_callback: Callable[[str], None],
                 result_callback: Callable[[str, str, str, str, str], None]):
        """
        Args:
            log_callback: ログ出力用コールバック
            result_callback: 結果追加用コールバック
        """
        self.log = log_callback
        self.add_result = result_callback

    def process(self, folder_path: str, yymm: str, main_prefix: str,
                receipt_prefix: str, normalize_english: bool, **kwargs) -> dict:
        """
        処理のエントリーポイント（サブクラスでオーバーライド）

        Args:
            folder_path: 処理対象フォルダパス
            yymm: 年月（YYMM形式）
            main_prefix: 本表接頭辞（01または0001）
            receipt_prefix: 受信通知接頭辞（02または9999）
            normalize_english: 全角英語を半角に変換するか
            **kwargs: 追加パラメータ

        Returns:
            dict: 処理結果 {"success": bool, "processed_count": int, "errors": List[str]}
        """
        raise NotImplementedError("Subclass must implement process()")
