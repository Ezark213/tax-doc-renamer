#!/usr/bin/env python3
"""
税務書類リネームシステム - モダンUIテーマ設定
Phase 1: ttkthemesによるテーマ適用
"""

from ttkthemes import ThemedStyle


# カラーパレット定義（会計ソフト風）
COLORS = {
    'primary': '#4A90E2',      # ブルー（プライマリーアクション）
    'secondary': '#E0E0E0',    # ライトグレー（セカンダリーアクション）
    'danger': '#E74C3C',       # レッド（危険・エラー）
    'success': '#2ECC71',      # グリーン（成功）
    'warning': '#F39C12',      # オレンジ（警告）
    'info': '#3498DB',         # ライトブルー（情報）
    'text': '#333333',         # ダークグレー（メインテキスト）
    'text_light': '#666666',   # ミディアムグレー（サブテキスト）
    'text_muted': '#999999',   # ライトグレー（補助テキスト）
    'bg': '#FFFFFF',           # ホワイト（背景）
    'bg_light': '#F8F9FA',     # 極薄グレー（サブ背景）
}


def apply_modern_theme(root):
    """
    モダンUIテーマの適用

    Args:
        root: tkinterのルートウィンドウ

    Returns:
        ThemedStyle: 適用されたスタイルオブジェクト
    """
    # ttkthemesスタイル初期化
    style = ThemedStyle(root)

    # "arc"テーマを適用（モダンなフラットデザイン）
    style.set_theme("arc")

    # === カスタムスタイル定義 ===

    # Accentボタン（プライマリーアクション用）
    style.configure('Accent.TButton',
                   background=COLORS['primary'],
                   foreground='white',
                   font=('Yu Gothic UI', 10, 'bold'),
                   padding=(10, 5))

    # Secondaryボタン（セカンダリーアクション用）
    style.configure('Secondary.TButton',
                   background=COLORS['secondary'],
                   foreground=COLORS['text'],
                   font=('Yu Gothic UI', 9),
                   padding=(8, 4))

    # Dangerボタン（危険なアクション用）
    style.configure('Danger.TButton',
                   background=COLORS['danger'],
                   foreground='white',
                   font=('Yu Gothic UI', 9, 'bold'),
                   padding=(8, 4))

    # Successボタン（成功アクション用）
    style.configure('Success.TButton',
                   background=COLORS['success'],
                   foreground='white',
                   font=('Yu Gothic UI', 9),
                   padding=(8, 4))

    # LabelFrame（セクション区切り用）
    style.configure('TLabelframe',
                   borderwidth=1,
                   relief='solid')
    style.configure('TLabelframe.Label',
                   font=('Yu Gothic UI', 10, 'bold'),
                   foreground=COLORS['text'])

    # Entry（入力フィールド）
    style.configure('TEntry',
                   fieldbackground='white',
                   font=('Yu Gothic UI', 9),
                   padding=5)

    # Label（テキストラベル）
    style.configure('TLabel',
                   font=('Yu Gothic UI', 9),
                   foreground=COLORS['text'])

    # ヘッダーラベル
    style.configure('Header.TLabel',
                   font=('Yu Gothic UI', 12, 'bold'),
                   foreground=COLORS['text'])

    # サブヘッダーラベル
    style.configure('Subheader.TLabel',
                   font=('Yu Gothic UI', 10, 'bold'),
                   foreground=COLORS['text_light'])

    # 情報ラベル（ブルー）
    style.configure('Info.TLabel',
                   font=('Yu Gothic UI', 8),
                   foreground=COLORS['info'])

    # エラーラベル（レッド）
    style.configure('Error.TLabel',
                   font=('Yu Gothic UI', 8, 'bold'),
                   foreground=COLORS['danger'])

    # 成功ラベル（グリーン）
    style.configure('Success.TLabel',
                   font=('Yu Gothic UI', 8),
                   foreground=COLORS['success'])

    # 警告ラベル（オレンジ）
    style.configure('Warning.TLabel',
                   font=('Yu Gothic UI', 8, 'bold'),
                   foreground=COLORS['warning'])

    # Mutedラベル（グレー）
    style.configure('Muted.TLabel',
                   font=('Yu Gothic UI', 8),
                   foreground=COLORS['text_muted'])

    # Notebook（タブ）
    style.configure('TNotebook',
                   borderwidth=0)
    style.configure('TNotebook.Tab',
                   font=('Yu Gothic UI', 10),
                   padding=(15, 8))

    # Progressbar
    style.configure('TProgressbar',
                   troughcolor=COLORS['bg_light'],
                   background=COLORS['success'],
                   thickness=20)

    return style


def get_color(color_name):
    """
    カラーパレットから色を取得

    Args:
        color_name: 色の名前（'primary', 'danger'等）

    Returns:
        str: カラーコード（例: '#4A90E2'）
    """
    return COLORS.get(color_name, COLORS['text'])


if __name__ == '__main__':
    # テーマのプレビュー
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Theme Preview - 税務書類リネームシステム")
    root.geometry("600x500")

    # テーマ適用
    apply_modern_theme(root)

    # サンプルUI
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill='both', expand=True)

    # ヘッダー
    ttk.Label(main_frame, text="モダンUIテーマプレビュー", style='Header.TLabel').pack(pady=(0, 10))

    # ボタンサンプル
    button_frame = ttk.LabelFrame(main_frame, text="ボタンスタイル", padding=10)
    button_frame.pack(fill='x', pady=5)

    ttk.Button(button_frame, text="Accentボタン", style='Accent.TButton').pack(pady=2)
    ttk.Button(button_frame, text="Secondaryボタン", style='Secondary.TButton').pack(pady=2)
    ttk.Button(button_frame, text="Dangerボタン", style='Danger.TButton').pack(pady=2)
    ttk.Button(button_frame, text="Successボタン", style='Success.TButton').pack(pady=2)

    # ラベルサンプル
    label_frame = ttk.LabelFrame(main_frame, text="ラベルスタイル", padding=10)
    label_frame.pack(fill='x', pady=5)

    ttk.Label(label_frame, text="📘 情報ラベル", style='Info.TLabel').pack(pady=2, anchor='w')
    ttk.Label(label_frame, text="❌ エラーラベル", style='Error.TLabel').pack(pady=2, anchor='w')
    ttk.Label(label_frame, text="✅ 成功ラベル", style='Success.TLabel').pack(pady=2, anchor='w')
    ttk.Label(label_frame, text="⚠️ 警告ラベル", style='Warning.TLabel').pack(pady=2, anchor='w')
    ttk.Label(label_frame, text="📝 Mutedラベル", style='Muted.TLabel').pack(pady=2, anchor='w')

    # Entryサンプル
    entry_frame = ttk.LabelFrame(main_frame, text="入力フィールド", padding=10)
    entry_frame.pack(fill='x', pady=5)

    ttk.Label(entry_frame, text="YYMM入力:").pack(side='left', padx=(0, 10))
    entry_var = tk.StringVar(value="2501")
    ttk.Entry(entry_frame, textvariable=entry_var, width=10).pack(side='left')

    # Progressbarサンプル
    progress_frame = ttk.LabelFrame(main_frame, text="プログレスバー", padding=10)
    progress_frame.pack(fill='x', pady=5)

    progress = ttk.Progressbar(progress_frame, mode='determinate', value=65)
    progress.pack(fill='x')

    root.mainloop()