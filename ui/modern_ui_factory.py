#!/usr/bin/env python3
"""
Modern UI Factory - PySide6 Implementation
Phase 5: Implementation Execution - Modern UI Components

Creates modern PySide6-based UI components with Material Design
and enhanced accessibility features.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import sys

try:
    from PySide6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRect
    from PySide6.QtGui import (
        QIcon, QDragEnterEvent, QDropEvent, QAction, QPalette, QColor,
        QFont, QPainter, QPen, QBrush, QPixmap
    )
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
        QFrame, QLabel, QPushButton, QListWidget, QTextEdit, QToolBar, QFileDialog,
        QStatusBar, QMessageBox, QLineEdit, QComboBox, QCheckBox, QProgressBar,
        QSplitter, QScrollArea, QGroupBox, QGridLayout, QSpacerItem, QSizePolicy
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback empty classes
    class QWidget: pass
    class QMainWindow: pass

class MaterialDesignColors:
    """Material Design 3 Color Palette for Tax Document System"""
    
    # Primary colors
    PRIMARY = "#1976D2"           # Blue 700
    PRIMARY_VARIANT = "#1565C0"   # Blue 800
    SECONDARY = "#388E3C"         # Green 700
    SECONDARY_VARIANT = "#2E7D32" # Green 800
    
    # Surface colors
    SURFACE = "#FAFAFA"           # Grey 50
    BACKGROUND = "#FFFFFF"        # White
    CARD = "#F5F5F5"             # Grey 100
    
    # Text colors
    ON_PRIMARY = "#FFFFFF"        # White
    ON_SECONDARY = "#FFFFFF"      # White
    ON_SURFACE = "#212121"        # Grey 900
    ON_BACKGROUND = "#424242"     # Grey 700
    
    # Status colors
    SUCCESS = "#4CAF50"           # Green 500
    WARNING = "#FF9800"           # Orange 500
    ERROR = "#F44336"             # Red 500
    INFO = "#2196F3"              # Blue 500
    
    # Tax-specific colors
    TAX_DOCUMENT = "#3F51B5"      # Indigo 500
    OCR_PROCESSING = "#9C27B0"    # Purple 500
    CLASSIFICATION = "#607D8B"    # Blue Grey 500

class MaterialDesignStyles:
    """Material Design CSS styles for PySide6"""
    
    @staticmethod
    def get_main_window_style() -> str:
        return f"""
        QMainWindow {{
            background-color: {MaterialDesignColors.BACKGROUND};
            color: {MaterialDesignColors.ON_BACKGROUND};
            font-family: 'Yu Gothic UI', 'Segoe UI', sans-serif;
            font-size: 14px;
        }}
        
        QToolBar {{
            background-color: {MaterialDesignColors.PRIMARY};
            color: {MaterialDesignColors.ON_PRIMARY};
            border: none;
            spacing: 8px;
            padding: 8px;
        }}
        
        QStatusBar {{
            background-color: {MaterialDesignColors.SURFACE};
            color: {MaterialDesignColors.ON_SURFACE};
            border-top: 1px solid #E0E0E0;
            padding: 4px 8px;
        }}
        """
    
    @staticmethod
    def get_drop_zone_style() -> str:
        return f"""
        QFrame#dropZone {{
            border: 2px dashed {MaterialDesignColors.PRIMARY};
            border-radius: 12px;
            background-color: {MaterialDesignColors.SURFACE};
            margin: 16px;
            padding: 24px;
        }}
        
        QFrame#dropZone:hover {{
            border-color: {MaterialDesignColors.PRIMARY_VARIANT};
            background-color: #E3F2FD;
        }}
        
        QLabel#dropTitle {{
            color: {MaterialDesignColors.PRIMARY};
            font-size: 18px;
            font-weight: bold;
            padding: 8px;
        }}
        
        QLabel#dropSubtitle {{
            color: {MaterialDesignColors.ON_SURFACE};
            font-size: 14px;
            padding: 4px;
        }}
        """
    
    @staticmethod
    def get_button_style() -> str:
        return f"""
        QPushButton {{
            background-color: {MaterialDesignColors.PRIMARY};
            color: {MaterialDesignColors.ON_PRIMARY};
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 500;
            min-height: 36px;
        }}
        
        QPushButton:hover {{
            background-color: {MaterialDesignColors.PRIMARY_VARIANT};
        }}
        
        QPushButton:pressed {{
            background-color: #1565C0;
        }}
        
        QPushButton:disabled {{
            background-color: #BDBDBD;
            color: #757575;
        }}
        
        QPushButton#secondaryButton {{
            background-color: {MaterialDesignColors.SECONDARY};
            color: {MaterialDesignColors.ON_SECONDARY};
        }}
        
        QPushButton#secondaryButton:hover {{
            background-color: {MaterialDesignColors.SECONDARY_VARIANT};
        }}
        """
    
    @staticmethod
    def get_input_style() -> str:
        return f"""
        QLineEdit {{
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 14px;
            background-color: {MaterialDesignColors.BACKGROUND};
            color: {MaterialDesignColors.ON_BACKGROUND};
        }}
        
        QLineEdit:focus {{
            border-color: {MaterialDesignColors.PRIMARY};
        }}
        
        QComboBox {{
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 14px;
            background-color: {MaterialDesignColors.BACKGROUND};
            min-height: 20px;
        }}
        
        QComboBox:focus {{
            border-color: {MaterialDesignColors.PRIMARY};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        
        QComboBox::down-arrow {{
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iIzc1NzU3NSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
        }}
        """

class ModernDropZone(QFrame):
    """Modern drag-and-drop zone with Material Design and animations"""
    
    def __init__(self, on_files_callback, parent=None):
        super().__init__(parent)
        self.on_files_callback = on_files_callback
        self.animation_timer = QTimer()
        self.hover_animation = None
        
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        
        self._setup_layout()
        self._setup_animations()
        self._apply_styles()
    
    def _setup_layout(self):
        """Setup the layout for drop zone"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        
        # Icon (using text for now, can be replaced with actual icon)
        icon_label = QLabel("📁")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px; padding: 16px;")
        
        # Title
        title_label = QLabel("ファイルをここにドラッグ&ドロップ")
        title_label.setObjectName("dropTitle")
        title_label.setAlignment(Qt.AlignCenter)
        
        # Subtitle
        subtitle_label = QLabel("対応形式: PDF, CSV\n\nクリックでファイル選択")
        subtitle_label.setObjectName("dropSubtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
    
    def _setup_animations(self):
        """Setup hover animations"""
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def _apply_styles(self):
        """Apply Material Design styles"""
        self.setStyleSheet(MaterialDesignStyles.get_drop_zone_style())
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter with visual feedback"""
        if event.mimeData().hasUrls():
            valid_files = False
            for url in event.mimeData().urls():
                file_path = Path(url.toLocalFile())
                if file_path.suffix.lower() in {'.pdf', '.csv'}:
                    valid_files = True
                    break
            
            if valid_files:
                event.acceptProposedAction()
                self._start_hover_effect()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        self._stop_hover_effect()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        """Handle file drop"""
        self._stop_hover_effect()
        
        files = []
        for url in event.mimeData().urls():
            file_path = Path(url.toLocalFile())
            if file_path.suffix.lower() in {'.pdf', '.csv'}:
                files.append(str(file_path))
        
        if files:
            self.on_files_callback(files)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def mousePressEvent(self, event):
        """Handle click to open file dialog"""
        if event.button() == Qt.LeftButton:
            self._open_file_dialog()
        super().mousePressEvent(event)
    
    def _open_file_dialog(self):
        """Open file selection dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "処理するファイルを選択",
            "",
            "対応ファイル (*.pdf *.csv);;PDFファイル (*.pdf);;CSVファイル (*.csv);;すべてのファイル (*.*)"
        )
        
        if files:
            self.on_files_callback(files)
    
    def _start_hover_effect(self):
        """Start hover animation effect"""
        # Add subtle scale effect or border glow
        self.setStyleSheet(self.styleSheet() + """
        QFrame#dropZone {
            border-color: #1565C0;
            background-color: #E3F2FD;
        }
        """)
    
    def _stop_hover_effect(self):
        """Stop hover animation effect"""
        self._apply_styles()

class ModernUIFactory:
    """Factory for creating modern UI components"""
    
    def __init__(self, migration_manager):
        self.migration_manager = migration_manager
        self.app = None
        
        if not PYSIDE6_AVAILABLE:
            raise ImportError("PySide6 not available for modern UI")
    
    def create_application(self) -> QApplication:
        """Create PySide6 application with Material Design theme"""
        if QApplication.instance():
            self.app = QApplication.instance()
        else:
            self.app = QApplication(sys.argv)
        
        # Set application properties
        self.app.setApplicationName("税務書類リネームシステム")
        self.app.setApplicationVersion("v5.4.6-modern")
        self.app.setOrganizationName("Tax Document System")
        
        # Apply Material Design theme
        self._apply_material_theme()
        
        return self.app
    
    def _apply_material_theme(self):
        """Apply Material Design theme to application"""
        # Set application-wide font
        font = QFont("Yu Gothic UI", 10)
        self.app.setFont(font)
        
        # Apply dark mode if enabled
        if self.migration_manager.is_feature_enabled("dark_mode"):
            self._apply_dark_theme()
    
    def _apply_dark_theme(self):
        """Apply dark theme variant"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(33, 33, 33))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(42, 42, 42))
        palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        
        self.app.setPalette(palette)
    
    def create_main_window(self) -> 'ModernMainWindow':
        """Create modern main window"""
        from .modern_main_window import ModernMainWindow
        return ModernMainWindow(self.migration_manager)
    
    def create_drop_zone(self, callback) -> ModernDropZone:
        """Create modern drop zone"""
        return ModernDropZone(callback)
    
    def create_toolbar(self, parent) -> QToolBar:
        """Create modern toolbar"""
        toolbar = QToolBar(parent)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setMovable(False)
        return toolbar
    
    def create_status_bar(self, parent) -> QStatusBar:
        """Create modern status bar"""
        status_bar = QStatusBar(parent)
        return status_bar
    
    def show_message(self, parent, title: str, message: str, msg_type: str = "info"):
        """Show modern message dialog"""
        if msg_type == "error":
            QMessageBox.critical(parent, title, message)
        elif msg_type == "warning":
            QMessageBox.warning(parent, title, message)
        elif msg_type == "question":
            return QMessageBox.question(parent, title, message)
        else:
            QMessageBox.information(parent, title, message)