#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox

def main():
    root = tk.Tk()
    root.title("テスト用アプリ")
    root.geometry("400x200")
    
    label = ttk.Label(root, text="アプリが正常に起動しました！")
    label.pack(pady=50)
    
    button = ttk.Button(root, text="閉じる", command=root.quit)
    button.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    main()