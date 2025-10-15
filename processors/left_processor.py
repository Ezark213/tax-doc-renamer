"""
Left Processor - 左側処理オーケストレーター

Phase D-2で作成。main.pyの左側処理メソッドを統合管理します。
"""

from typing import Callable, Optional
from .receipt_detector import ReceiptDetector


class LeftProcessor:
    """
    左側リネーム処理のオーケストレーター

    源泉税、法定調書、給与支払報告書、償却資産申告書、申請届出の
    各処理を統一的に管理します。

    Phase D-2では、main.pyの既存メソッドを呼び出すラッパーとして実装。
    将来的には各処理を完全に分離したプロセッサクラスに移行します。
    """

    def __init__(self, main_app_instance):
        """
        Args:
            main_app_instance: TaxDocumentRenamerV5のインスタンス
                               （既存のmain.pyメソッドにアクセスするため）
        """
        self.main_app = main_app_instance
        self.receipt_detector = ReceiptDetector

    def process_gensen(self, folder_path: str, yymm: str, main_prefix: str,
                       receipt_prefix: str, normalize_english: bool) -> dict:
        """
        源泉税処理

        Args:
            folder_path: 処理対象フォルダパス
            yymm: 年月（YYMM形式）
            main_prefix: 本表接頭辞（01または0001）
            receipt_prefix: 受信通知接頭辞（02または9999）
            normalize_english: 全角英語を半角に変換するか

        Returns:
            dict: 処理結果
        """
        # Phase D-2: main.pyの既存メソッドを呼び出し
        self.main_app._process_gensen(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)
        return {"success": True, "processor": "gensen"}

    def process_hoteichosho(self, folder_path: str, yymm: str, main_prefix: str,
                             receipt_prefix: str, normalize_english: bool) -> dict:
        """法定調書処理"""
        self.main_app._process_hoteichosho(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)
        return {"success": True, "processor": "hoteichosho"}

    def process_payroll(self, folder_path: str, yymm: str, main_prefix: str,
                        receipt_prefix: str, normalize_english: bool, **kwargs) -> dict:
        """給与支払報告書処理"""
        self.main_app._process_payroll_report(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)
        return {"success": True, "processor": "payroll"}

    def process_depreciable_assets(self, folder_path: str, yymm: str, main_prefix: str,
                                    receipt_prefix: str, normalize_english: bool, **kwargs) -> dict:
        """償却資産申告書処理"""
        self.main_app._process_depreciable_assets(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)
        return {"success": True, "processor": "depreciable_assets"}

    def process_application(self, folder_path: str, yymm: str, main_prefix: str,
                            receipt_prefix: str, normalize_english: bool, **kwargs) -> dict:
        """申請届出処理"""
        self.main_app._process_application(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)
        return {"success": True, "processor": "application"}

    def process(self, process_type: str, **kwargs) -> dict:
        """
        統一エントリーポイント

        Args:
            process_type: 処理タイプ ("gensen", "hoteichosho", "payroll", "depreciable_assets", "application")
            **kwargs: 各処理のパラメータ

        Returns:
            dict: 処理結果
        """
        processors = {
            "gensen": self.process_gensen,
            "hoteichosho": self.process_hoteichosho,
            "payroll": self.process_payroll,
            "depreciable_assets": self.process_depreciable_assets,
            "application": self.process_application
        }

        processor_func = processors.get(process_type)
        if processor_func:
            return processor_func(**kwargs)
        else:
            return {"success": False, "error": f"Unknown process type: {process_type}"}
