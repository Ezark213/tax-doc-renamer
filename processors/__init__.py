"""
Processors Package - リファクタリング後の処理モジュール群

このパッケージは、tax-doc-renamer v8.0のリファクタリングで作成されました。
main.pyから分離された各種処理ロジックを格納します。
"""

__version__ = "8.0.0"

from .receipt_detector import ReceiptDetector

__all__ = ["ReceiptDetector"]
