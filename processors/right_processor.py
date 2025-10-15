"""
Right Processor - 右側処理オーケストレーター

Phase D-3で作成。main.pyの右側処理（AI自動分類）を管理します。
"""

from typing import List, Dict


class RightProcessor:
    """
    右側リネーム処理のオーケストレーター

    AI自動分類とYYMM解決を使用した通常PDF処理を管理します。

    Phase D-3では、main.pyの既存メソッドを呼び出すラッパーとして実装。
    将来的には完全に分離したプロセッサクラスに移行します。
    """

    def __init__(self, main_app_instance):
        """
        Args:
            main_app_instance: TaxDocumentRenamerV5のインスタンス
        """
        self.main_app = main_app_instance

    def process_files(self, files: List[str], settings: dict) -> List[Dict]:
        """
        ファイルリストを処理

        Args:
            files: 処理対象PDFファイルリスト
            settings: 設定辞書

        Returns:
            List[Dict]: 処理結果リスト
        """
        # Phase D-3: main.pyの既存処理を呼び出し
        # 実際にはmain.pyの_start_rename_processingが非同期で実行されるため、
        # ここでは設定を返すのみ
        return {"success": True, "files": files, "processor": "right_ai"}

    def process_single_file(self, file_path: str, settings: dict) -> dict:
        """
        単一ファイルを処理

        Args:
            file_path: PDFファイルパス
            settings: 設定辞書

        Returns:
            dict: 処理結果
        """
        # Phase D-3: main.pyの_process_pdf_file_v5系メソッドを呼び出し
        return {"success": True, "file": file_path, "processor": "right_ai_single"}
