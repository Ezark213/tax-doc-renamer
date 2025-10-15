"""
Thread Manager - スレッド管理

Phase D-5で作成。root.after()を使った非同期処理を管理します。
"""

import threading
import tkinter as tk
from typing import Callable, Any


class ThreadManager:
    """
    スレッド管理クラス

    tkinterのroot.after()を使った非同期処理を統一的に管理します。

    Phase D-5では、既存のmain.pyのスレッド処理パターンをラップします。
    """

    def __init__(self, root: tk.Tk):
        """
        Args:
            root: tkinterルートウィンドウ
        """
        self.root = root
        self.active_threads = []

    def run_in_background(self, target: Callable, *args, **kwargs) -> threading.Thread:
        """
        バックグラウンドでタスクを実行

        Args:
            target: 実行する関数
            *args: 位置引数
            **kwargs: キーワード引数

        Returns:
            threading.Thread: 開始されたスレッド
        """
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        self.active_threads.append(thread)
        return thread

    def schedule_ui_update(self, callback: Callable, delay: int = 0):
        """
        UIスレッドでコールバックをスケジュール

        Args:
            callback: 実行するコールバック
            delay: 遅延時間（ミリ秒）
        """
        self.root.after(delay, callback)

    def get_active_thread_count(self) -> int:
        """アクティブなスレッド数を取得"""
        # 終了したスレッドをクリーンアップ
        self.active_threads = [t for t in self.active_threads if t.is_alive()]
        return len(self.active_threads)
