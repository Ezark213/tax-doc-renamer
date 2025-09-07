#!/usr/bin/env python3
"""
税務書類リネームシステム v5.2
Bundle PDF Auto-Split + PySide6 UI
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    """メインアプリケーション起動"""
    app = QApplication(sys.argv)
    app.setApplicationName("税務書類リネームシステム v5.2")
    app.setApplicationVersion("5.2")
    app.setOrganizationName("Bundle PDF Auto-Split")
    
    # メインウィンドウの作成と表示
    window = MainWindow()
    window.show()
    
    # イベントループの開始
    sys.exit(app.exec())

if __name__ == "__main__":
    main()