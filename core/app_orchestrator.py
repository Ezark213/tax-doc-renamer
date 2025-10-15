"""
Application Orchestrator - アプリケーション全体調整

Phase D-5で作成。UI、左側処理、右側処理を統合管理します。
"""

import tkinter as tk
from typing import Optional
from processors.left_processor import LeftProcessor
from processors.right_processor import RightProcessor


class AppOrchestrator:
    """
    アプリケーション全体の調整役

    UI、左側処理、右側処理、スレッド管理を統合し、
    main.pyを薄いエントリーポイントに変えます。

    Phase D-5での実装は、既存のmain.pyインスタンスをラップする形で、
    段階的な移行を実現します。
    """

    def __init__(self, main_app_instance):
        """
        Args:
            main_app_instance: TaxDocumentRenamerV5のインスタンス
        """
        self.main_app = main_app_instance
        self.root = main_app_instance.root if hasattr(main_app_instance, 'root') else None

        # プロセッサ初期化
        self.left_processor = LeftProcessor(main_app_instance)
        self.right_processor = RightProcessor(main_app_instance)

    def start_left_processing(self, process_type: str, **kwargs):
        """
        左側処理を開始

        Args:
            process_type: 処理タイプ
            **kwargs: 処理パラメータ
        """
        return self.left_processor.process(process_type, **kwargs)

    def start_right_processing(self, files: list, settings: dict):
        """
        右側処理を開始

        Args:
            files: ファイルリスト
            settings: 設定辞書
        """
        return self.right_processor.process_files(files, settings)

    def get_version(self) -> str:
        """アプリケーションバージョンを取得"""
        return "8.0.0-REFACTORED (Phase D-5)"
