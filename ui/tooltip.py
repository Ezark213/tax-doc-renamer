#!/usr/bin/env python3
"""
税務書類リネームシステム - ツールチップモジュール
Phase 2: ユーザビリティ向上のためのツールチップ機能
"""

import tkinter as tk


class ToolTip:
    """
    ウィジェットにツールチップ（ホバー時のヘルプ表示）を追加するクラス
    """

    def __init__(self, widget, text, delay=500):
        """
        Args:
            widget: ツールチップを表示するウィジェット
            text: 表示するテキスト
            delay: 表示遅延時間（ミリ秒、デフォルト500ms）
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None

        # イベントバインディング
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Button>", self.on_leave)  # クリック時は非表示

    def on_enter(self, event=None):
        """マウスがウィジェットに入ったときの処理"""
        self.schedule_tooltip()

    def on_leave(self, event=None):
        """マウスがウィジェットから離れたときの処理"""
        self.cancel_tooltip()
        self.hide_tooltip()

    def schedule_tooltip(self):
        """ツールチップの表示をスケジュール"""
        self.cancel_tooltip()
        self.after_id = self.widget.after(self.delay, self.show_tooltip)

    def cancel_tooltip(self):
        """ツールチップのスケジュールをキャンセル"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show_tooltip(self):
        """ツールチップを表示"""
        if self.tooltip_window:
            return

        # ウィジェットの位置を取得
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # ツールチップウィンドウを作成
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # ウィンドウ装飾なし
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # ツールチップラベルを作成
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="#FFFFCC",  # 薄い黄色背景
            foreground="#333333",  # ダークグレー文字
            relief="solid",
            borderwidth=1,
            font=('Yu Gothic UI', 9),
            padx=5,  # Phase 2: padding → padx/pady修正
            pady=5,
            justify='left'
        )
        label.pack()

    def hide_tooltip(self):
        """ツールチップを非表示"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def create_tooltip(widget, text, delay=500):
    """
    ウィジェットにツールチップを作成する便利関数

    Args:
        widget: ツールチップを表示するウィジェット
        text: 表示するテキスト
        delay: 表示遅延時間（ミリ秒、デフォルト500ms）

    Returns:
        ToolTip: 作成されたツールチップオブジェクト
    """
    return ToolTip(widget, text, delay)


if __name__ == '__main__':
    # ツールチップのテスト
    root = tk.Tk()
    root.title("Tooltip Test")
    root.geometry("400x300")

    # テストボタン1
    btn1 = tk.Button(root, text="ボタン1", width=15)
    btn1.pack(pady=20)
    create_tooltip(btn1, "これはボタン1です\nクリックすると何かが起こります")

    # テストボタン2
    btn2 = tk.Button(root, text="ボタン2", width=15)
    btn2.pack(pady=20)
    create_tooltip(btn2, "これはボタン2です\n別の動作をします", delay=300)

    # テストEntry
    entry = tk.Entry(root, width=20)
    entry.pack(pady=20)
    create_tooltip(entry, "4桁の数字を入力してください\n例: 2501")

    root.mainloop()