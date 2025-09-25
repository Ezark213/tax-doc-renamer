#!/usr/bin/env python3
"""
Modern Main Window - PySide6 Implementation with Material Design
Phase 5: Implementation Execution - Modern UI Migration

Enhanced main window with accessibility features, animations, and modern styling.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

try:
    from PySide6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
    from PySide6.QtGui import QIcon, QAction, QFont, QPixmap, QKeySequence
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QFrame, QLabel, QPushButton, QListWidget, QTextEdit, QToolBar,
        QStatusBar, QLineEdit, QComboBox, QCheckBox, QProgressBar,
        QSplitter, QScrollArea, QGroupBox, QSpacerItem, QSizePolicy,
        QTabWidget, QListWidgetItem, QMessageBox
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    class QMainWindow: pass
    class pyqtSignal: pass

from .modern_ui_factory import ModernDropZone, MaterialDesignStyles, MaterialDesignColors

class AccessibleWidget(QWidget):
    """Base widget with accessibility features"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_accessibility()
    
    def _setup_accessibility(self):
        """Setup accessibility features"""
        # Set accessible properties
        self.setFocusPolicy(Qt.TabFocus)
        
    def set_accessible_name(self, name: str):
        """Set accessible name for screen readers"""
        self.setAccessibleName(name)
    
    def set_accessible_description(self, description: str):
        """Set accessible description for screen readers"""
        self.setAccessibleDescription(description)

class AnimatedButton(QPushButton):
    """Button with hover animations"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.hover_animation = None
        self.original_size = None
        self._setup_animation()
    
    def _setup_animation(self):
        """Setup hover animation"""
        self.hover_animation = QPropertyAnimation(self, b"size")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        if self.original_size is None:
            self.original_size = self.size()
        
        target_size = QSize(
            self.original_size.width() + 4,
            self.original_size.height() + 2
        )
        
        self.hover_animation.setStartValue(self.size())
        self.hover_animation.setEndValue(target_size)
        self.hover_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        if self.original_size:
            self.hover_animation.setStartValue(self.size())
            self.hover_animation.setEndValue(self.original_size)
            self.hover_animation.start()
        
        super().leaveEvent(event)

class ModernSettingsPanel(AccessibleWidget):
    """Modern settings panel with Material Design"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.municipality_inputs = []
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Setup the settings UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title_label = QLabel("設定")
        title_label.setObjectName("sectionTitle")
        title_label.setAccessibleName("設定セクション")
        layout.addWidget(title_label)
        
        # Year/Month settings group
        year_group = self._create_year_settings_group()
        layout.addWidget(year_group)
        
        # Municipality settings group
        municipality_group = self._create_municipality_settings_group()
        layout.addWidget(municipality_group)
        
        # Add stretch to push content to top
        layout.addStretch()
    
    def _create_year_settings_group(self) -> QGroupBox:
        """Create year/month settings group"""
        group = QGroupBox("年月設定")
        group.setAccessibleName("年月設定グループ")
        layout = QVBoxLayout(group)
        
        # Manual input
        input_layout = QHBoxLayout()
        
        label = QLabel("手動入力年月 (YYMM):")
        label.setMinimumWidth(150)
        
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("2508")
        self.year_input.setMaximumWidth(120)
        self.year_input.setAccessibleName("年月入力")
        self.year_input.setAccessibleDescription("YYMM形式で年月を入力してください")
        
        input_layout.addWidget(label)
        input_layout.addWidget(self.year_input)
        input_layout.addStretch()
        
        layout.addLayout(input_layout)
        
        return group
    
    def _create_municipality_settings_group(self) -> QGroupBox:
        """Create municipality settings group"""
        group = QGroupBox("自治体設定")
        group.setAccessibleName("自治体設定グループ")
        layout = QVBoxLayout(group)
        
        # Prefecture list
        prefectures = [
            "", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        # Create 5 municipality sets
        grid_layout = QGridLayout()
        grid_layout.setSpacing(12)
        
        for i in range(1, 6):
            # Set label
            set_label = QLabel(f"セット{i}:")
            set_label.setMinimumWidth(70)
            
            # Prefecture combo
            prefecture_combo = QComboBox()
            prefecture_combo.setEditable(True)
            prefecture_combo.addItems(prefectures)
            prefecture_combo.setMinimumWidth(120)
            prefecture_combo.setAccessibleName(f"セット{i} 都道府県")
            
            # City input
            city_input = QLineEdit()
            city_input.setPlaceholderText("市町村名")
            city_input.setMinimumWidth(120)
            city_input.setAccessibleName(f"セット{i} 市町村名")
            
            # Add to grid
            row = i - 1
            grid_layout.addWidget(set_label, row, 0)
            grid_layout.addWidget(prefecture_combo, row, 1)
            grid_layout.addWidget(city_input, row, 2)
            
            self.municipality_inputs.append((prefecture_combo, city_input))
        
        layout.addLayout(grid_layout)
        
        # Set default values
        self._set_default_municipality_values()
        
        return group
    
    def _set_default_municipality_values(self):
        """Set default municipality values"""
        if len(self.municipality_inputs) >= 3:
            self.municipality_inputs[0][0].setCurrentText("東京都")
            self.municipality_inputs[1][0].setCurrentText("愛知県")
            self.municipality_inputs[1][1].setText("蒲郡市")
            self.municipality_inputs[2][0].setCurrentText("福岡県")
            self.municipality_inputs[2][1].setText("福岡市")
    
    def _apply_styles(self):
        """Apply Material Design styles"""
        style = f"""
        QLabel#sectionTitle {{
            font-size: 20px;
            font-weight: bold;
            color: {MaterialDesignColors.PRIMARY};
            padding: 0px 0px 16px 0px;
        }}
        
        QGroupBox {{
            font-size: 16px;
            font-weight: 500;
            color: {MaterialDesignColors.ON_SURFACE};
            border: 2px solid {MaterialDesignColors.PRIMARY};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 8px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px 0 8px;
            color: {MaterialDesignColors.PRIMARY};
            background-color: {MaterialDesignColors.BACKGROUND};
        }}
        """
        
        self.setStyleSheet(style + MaterialDesignStyles.get_input_style())
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings"""
        settings = {
            'year_month': self.year_input.text(),
            'municipality_sets': []
        }
        
        for i, (prefecture_combo, city_input) in enumerate(self.municipality_inputs, 1):
            prefecture = prefecture_combo.currentText()
            city = city_input.text()
            if prefecture and city:
                settings['municipality_sets'].append({
                    'set_number': i,
                    'prefecture': prefecture,
                    'city': city
                })
        
        return settings

class ModernProcessingPanel(AccessibleWidget):
    """Modern processing panel with progress tracking"""
    
    files_processed = pyqtSignal(list)  # Signal for processed files
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_files = []
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Setup processing panel UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Drop zone
        self.drop_zone = ModernDropZone(self._on_files_dropped)
        self.drop_zone.setAccessibleName("ファイルドロップゾーン")
        layout.addWidget(self.drop_zone)
        
        # File list
        file_list_group = QGroupBox("処理対象ファイル")
        file_list_layout = QVBoxLayout(file_list_group)
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        self.file_list.setAccessibleName("処理対象ファイル一覧")
        file_list_layout.addWidget(self.file_list)
        
        layout.addWidget(file_list_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.pick_files_btn = AnimatedButton("📁 ファイル選択")
        self.pick_files_btn.setAccessibleName("ファイル選択ボタン")
        self.pick_files_btn.clicked.connect(self._pick_files)
        
        self.process_btn = AnimatedButton("⚡ 一括処理")
        self.process_btn.setObjectName("primaryButton")
        self.process_btn.setAccessibleName("一括処理実行ボタン")
        self.process_btn.clicked.connect(self._process_files)
        
        self.test_btn = AnimatedButton("🧪 テスト実行")
        self.test_btn.setObjectName("secondaryButton")
        self.test_btn.setAccessibleName("テスト実行ボタン")
        self.test_btn.clicked.connect(self._run_test)
        
        button_layout.addWidget(self.pick_files_btn)
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setAccessibleName("処理進行状況")
        layout.addWidget(self.progress_bar)
    
    def _apply_styles(self):
        """Apply Material Design styles"""
        style = MaterialDesignStyles.get_button_style() + f"""
        QListWidget {{
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            background-color: {MaterialDesignColors.SURFACE};
            font-size: 14px;
            padding: 8px;
        }}
        
        QListWidget::item {{
            border-bottom: 1px solid #F0F0F0;
            padding: 8px;
            margin: 2px 0px;
        }}
        
        QListWidget::item:selected {{
            background-color: {MaterialDesignColors.PRIMARY};
            color: {MaterialDesignColors.ON_PRIMARY};
        }}
        
        QProgressBar {{
            border: 2px solid {MaterialDesignColors.PRIMARY};
            border-radius: 8px;
            text-align: center;
            background-color: {MaterialDesignColors.SURFACE};
        }}
        
        QProgressBar::chunk {{
            background-color: {MaterialDesignColors.PRIMARY};
            border-radius: 6px;
        }}
        """
        
        self.setStyleSheet(style)
    
    def _on_files_dropped(self, files: List[str]):
        """Handle dropped files"""
        for file_path in files:
            if file_path not in self._pending_files:
                self._pending_files.append(file_path)
                
                # Add to list widget
                item = QListWidgetItem(f"📄 {Path(file_path).name}")
                item.setData(Qt.UserRole, file_path)
                self.file_list.addItem(item)
        
        self._update_button_states()
    
    def _pick_files(self):
        """Open file picker dialog"""
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "処理するファイルを選択",
            "",
            "対応ファイル (*.pdf *.csv);;PDFファイル (*.pdf);;CSVファイル (*.csv);;すべてのファイル (*.*)"
        )
        
        if files:
            self._on_files_dropped(files)
    
    def _process_files(self):
        """Process files"""
        if not self._pending_files:
            QMessageBox.information(
                self, 
                "情報", 
                "処理対象がありません。\nファイルをドラッグ&ドロップまたは選択してください。"
            )
            return
        
        # Emit signal with files to process
        self.files_processed.emit(self._pending_files.copy())
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self._pending_files))
        
        # Clear pending files
        self._pending_files.clear()
        self.file_list.clear()
        self._update_button_states()
    
    def _run_test(self):
        """Run test execution"""
        # Placeholder for test functionality
        QMessageBox.information(self, "テスト", "テスト機能は実装中です。")
    
    def _update_button_states(self):
        """Update button enabled states"""
        has_files = len(self._pending_files) > 0
        self.process_btn.setEnabled(has_files)
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress bar"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
        if message:
            self.progress_bar.setFormat(f"{message} ({current}/{total})")
        
        if current >= total:
            QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))

class ModernMainWindow(QMainWindow):
    """Modern main window with Material Design and accessibility"""
    
    def __init__(self, migration_manager):
        super().__init__()
        self.migration_manager = migration_manager
        self._setup_window()
        self._setup_ui()
        self._setup_menu_and_toolbar()
        self._setup_status_bar()
        self._apply_styles()
        self._setup_accessibility()
    
    def _setup_window(self):
        """Setup main window properties"""
        self.setWindowTitle("税務書類リネームシステム v5.4.6-modern")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Set window icon (placeholder)
        # self.setWindowIcon(QIcon("path/to/icon.png"))
    
    def _setup_ui(self):
        """Setup main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Settings
        self.settings_panel = ModernSettingsPanel()
        self.settings_panel.setMaximumWidth(400)
        main_splitter.addWidget(self.settings_panel)
        
        # Right panel - Processing
        self.processing_panel = ModernProcessingPanel()
        self.processing_panel.files_processed.connect(self._handle_file_processing)
        main_splitter.addWidget(self.processing_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([350, 650])
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_splitter)
        
        # Results area (tabbed)
        self._setup_results_area(layout)
    
    def _setup_results_area(self, parent_layout):
        """Setup results and log area"""
        results_tabs = QTabWidget()
        results_tabs.setMaximumHeight(200)
        
        # Processing results tab
        self.results_widget = QListWidget()
        self.results_widget.setAccessibleName("処理結果一覧")
        results_tabs.addTab(self.results_widget, "📊 処理結果")
        
        # Log/Debug tab
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setAccessibleName("ログ表示エリア")
        results_tabs.addTab(self.log_view, "📝 ログ・デバッグ")
        
        parent_layout.addWidget(results_tabs)
    
    def _setup_menu_and_toolbar(self):
        """Setup menu bar and toolbar"""
        # Menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("ファイル(&F)")
        
        open_action = QAction("ファイルを開く(&O)", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.processing_panel._pick_files)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("表示(&V)")
        
        if self.migration_manager.is_feature_enabled("dark_mode"):
            dark_mode_action = QAction("ダークモード", self)
            dark_mode_action.setCheckable(True)
            view_menu.addAction(dark_mode_action)
        
        # Help menu
        help_menu = menubar.addMenu("ヘルプ(&H)")
        
        about_action = QAction("バージョン情報(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # Toolbar
        toolbar = self.addToolBar("メインツールバー")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        toolbar.addAction(open_action)
        toolbar.addSeparator()
        
        process_action = QAction("⚡ 一括処理", self)
        process_action.triggered.connect(self.processing_panel._process_files)
        toolbar.addAction(process_action)
    
    def _setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("準備完了 - Modern UI")
    
    def _apply_styles(self):
        """Apply Material Design styles"""
        self.setStyleSheet(MaterialDesignStyles.get_main_window_style())
    
    def _setup_accessibility(self):
        """Setup accessibility features"""
        # Set main window accessible name
        self.setAccessibleName("税務書類リネームシステム メインウィンドウ")
        
        # Setup keyboard navigation
        self.setTabOrder(self.settings_panel, self.processing_panel)
    
    def _handle_file_processing(self, files: List[str]):
        """Handle file processing request"""
        settings = self.settings_panel.get_settings()
        
        # Check if settings are configured
        if not settings['municipality_sets']:
            reply = QMessageBox.question(
                self,
                "設定確認",
                "自治体が設定されていません。\n"
                "設定セクションで都道府県・市町村を入力してから処理を実行することを推奨します。\n\n"
                "そのまま続行しますか？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Start processing
        self.status_bar.showMessage("処理中...")
        self.append_log("=== 処理開始 ===")
        self.append_log(f"年月設定: {settings['year_month']}")
        
        for muni_set in settings['municipality_sets']:
            self.append_log(f"セット{muni_set['set_number']}: {muni_set['prefecture']} {muni_set['city']}")
        
        try:
            # Import the actual processing function
            from ui.file_processor import handle_dropped_files
            
            ok, ng = handle_dropped_files(files, log=self.append_log, settings=settings)
            
            self.status_bar.showMessage(f"完了：成功 {ok} 件 / 失敗 {ng} 件")
            self.append_log(f"=== 完了：成功 {ok} 件 / 失敗 {ng} 件 ===")
            
            # Add results to results widget
            result_item = QListWidgetItem(f"✅ 処理完了: 成功 {ok} 件, 失敗 {ng} 件")
            self.results_widget.addItem(result_item)
            
        except Exception as e:
            self.status_bar.showMessage("処理中にエラーが発生しました")
            self.append_log(f"=== エラー: {e} ===")
            QMessageBox.critical(self, "エラー", f"処理中にエラーが発生しました:\n{e}")
            
            # Add error to results
            error_item = QListWidgetItem(f"❌ エラー: {str(e)}")
            self.results_widget.addItem(error_item)
    
    def append_log(self, text: str):
        """Append text to log view"""
        self.log_view.append(text)
        self.log_view.ensureCursorVisible()
    
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "バージョン情報",
            "税務書類リネームシステム v5.4.6-modern\n\n"
            "Modern UI with Material Design\n"
            "Powered by PySide6\n\n"
            "© 2025 Tax Document System"
        )