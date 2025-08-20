#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
import logging

# ログ設定
logging.basicConfig(
    filename='debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def show_error(error_msg):
    """エラーメッセージを表示"""
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを隠す
    messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\n\n{error_msg}")
    root.destroy()

def test_imports():
    """必要なライブラリのインポートテスト"""
    try:
        logging.info("インポートテスト開始")
        
        import tkinter
        logging.info("tkinter OK")
        
        import pytesseract
        logging.info("pytesseract OK")
        
        import fitz
        logging.info("fitz OK")
        
        from PIL import Image
        logging.info("PIL OK")
        
        import PyPDF2
        logging.info("PyPDF2 OK")
        
        import re
        logging.info("re OK")
        
        import os
        logging.info("os OK")
        
        logging.info("全てのインポートが成功")
        return True
        
    except Exception as e:
        error_msg = f"インポートエラー: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        show_error(error_msg)
        return False

def main():
    try:
        logging.info("アプリケーション開始")
        
        # インポートテスト
        if not test_imports():
            return
            
        # 基本的なGUI作成テスト
        root = tk.Tk()
        root.title("デバッグバージョン - 税務書類リネームツール")
        root.geometry("600x400")
        
        # メインフレーム
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # テスト用ラベル
        status_label = ttk.Label(main_frame, text="✅ アプリケーションが正常に起動しました！")
        status_label.grid(row=0, column=0, pady=20)
        
        info_text = tk.Text(main_frame, height=15, width=70)
        info_text.grid(row=1, column=0, pady=10)
        
        info_text.insert(tk.END, "デバッグ情報:\n\n")
        info_text.insert(tk.END, "✅ tkinter: 正常\n")
        info_text.insert(tk.END, "✅ pytesseract: 正常\n") 
        info_text.insert(tk.END, "✅ fitz (PyMuPDF): 正常\n")
        info_text.insert(tk.END, "✅ PIL: 正常\n")
        info_text.insert(tk.END, "✅ PyPDF2: 正常\n")
        info_text.insert(tk.END, "\n")
        info_text.insert(tk.END, "この画面が表示されていれば、基本的なライブラリは全て正常に動作しています。\n")
        info_text.insert(tk.END, "メインアプリケーションの起動問題は別の原因にあります。\n")
        
        # 閉じるボタン
        close_button = ttk.Button(main_frame, text="閉じる", command=root.quit)
        close_button.grid(row=2, column=0, pady=10)
        
        logging.info("GUI作成完了")
        
        # ウィンドウ中央配置
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
        
        logging.info("アプリケーション開始")
        root.mainloop()
        logging.info("アプリケーション終了")
        
    except Exception as e:
        error_msg = f"メインアプリケーションエラー: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        show_error(error_msg)

if __name__ == "__main__":
    main()