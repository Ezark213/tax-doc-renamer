from pathlib import Path
from typing import Iterable, List
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QListWidget, QTextEdit, QToolBar, QFileDialog,
    QStatusBar, QMessageBox, QLineEdit, QComboBox
)

from .drag_drop import handle_dropped_files

ACCEPT_EXTS = {".pdf", ".csv"}

class DropFrame(QFrame):
    def __init__(self, on_files: callable, parent=None):
        super().__init__(parent)
        self.on_files = on_files
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setStyleSheet("QFrame { border: 2px dashed #8aa; border-radius: 12px; }")
        layout = QVBoxLayout(self)
        title = QLabel("PDFまたはCSVファイルをここにドラッグ＆ドロップ")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("対応: PDF / CSV")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if Path(u.toLocalFile()).suffix.lower() in ACCEPT_EXTS:
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e: QDropEvent):
        paths: List[str] = []
        for u in e.mimeData().urls():
            p = Path(u.toLocalFile())
            if p.suffix.lower() in ACCEPT_EXTS:
                paths.append(str(p))
        if paths:
            self.on_files(paths)
            e.acceptProposedAction()
        else:
            e.ignore()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("税務書類リネームシステム v5.2 - Bundle PDF Auto-Split")
        self.resize(800, 700)

        # メインウィジェット
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 設定セクション
        settings_group = QFrame()
        settings_group.setFrameStyle(QFrame.StyledPanel)
        settings_layout = QVBoxLayout(settings_group)
        
        # タイトル
        title_label = QLabel("設定")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #333; padding: 10px;")
        settings_layout.addWidget(title_label)
        
        # 年月設定
        year_month_layout = QHBoxLayout()
        year_month_label = QLabel("年月設定")
        year_month_label.setStyleSheet("font-weight: bold; color: #555;")
        year_month_layout.addWidget(year_month_label)
        year_month_layout.addStretch()
        settings_layout.addLayout(year_month_layout)
        
        # 手動入力年月
        year_input_layout = QHBoxLayout()
        year_input_label = QLabel("手動入力年月 (YYMM):")
        year_input_label.setMinimumWidth(150)
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("2508")
        self.year_input.setMaximumWidth(100)
        year_input_layout.addWidget(year_input_label)
        year_input_layout.addWidget(self.year_input)
        year_input_layout.addStretch()
        settings_layout.addLayout(year_input_layout)
        
        # 自治体設定
        municipality_title_layout = QHBoxLayout()
        municipality_title = QLabel("自治体設定")
        municipality_title.setStyleSheet("font-weight: bold; color: #555; margin-top: 20px;")
        municipality_title_layout.addWidget(municipality_title)
        municipality_title_layout.addStretch()
        settings_layout.addLayout(municipality_title_layout)
        
        # セット1-5の入力欄
        self.municipality_inputs = []
        prefectures = [
            "", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        for i in range(1, 6):
            set_layout = QHBoxLayout()
            set_label = QLabel(f"セット{i}:")
            set_label.setMinimumWidth(60)
            
            prefecture_combo = QComboBox()
            prefecture_combo.setEditable(True)
            prefecture_combo.addItems(prefectures)
            prefecture_combo.setMinimumWidth(100)
            
            city_input = QLineEdit()
            city_input.setPlaceholderText("市町村名")
            city_input.setMinimumWidth(100)
            
            set_layout.addWidget(set_label)
            set_layout.addWidget(prefecture_combo)
            set_layout.addWidget(city_input)
            set_layout.addStretch()
            
            settings_layout.addLayout(set_layout)
            self.municipality_inputs.append((prefecture_combo, city_input))
        
        # デフォルト値設定（画像に基づいて）
        if len(self.municipality_inputs) >= 3:
            self.municipality_inputs[0][0].setCurrentText("東京都")  # セット1
            self.municipality_inputs[1][0].setCurrentText("愛知県")  # セット2
            self.municipality_inputs[1][1].setText("蒲郡市")
            self.municipality_inputs[2][0].setCurrentText("福岡県")  # セット3
            self.municipality_inputs[2][1].setText("福岡市")
        
        main_layout.addWidget(settings_group)
        
        # ドラッグ&ドロップエリア
        drop_area = DropFrame(self.process_dropped_files)
        main_layout.addWidget(drop_area)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        btn_pick = QPushButton("ファイルを選択")
        btn_pick.clicked.connect(self.pick_files)
        btn_run = QPushButton("一括処理（分割＆出力）")
        btn_run.clicked.connect(self.run_batch)
        btn_test = QPushButton("テスト実行")
        btn_test.clicked.connect(self.run_test)
        
        button_layout.addWidget(btn_pick)
        button_layout.addWidget(btn_run)
        button_layout.addWidget(btn_test)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 結果表示タブエリア
        result_tabs = QTabWidget()
        result_tabs.setMaximumHeight(200)
        
        # 処理結果タブ
        self.result_widget = QWidget()
        result_layout = QVBoxLayout(self.result_widget)
        
        # ファイル一覧
        files_label = QLabel("処理対象ファイル:")
        result_layout.addWidget(files_label)
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(80)
        result_layout.addWidget(self.file_list)
        
        # 処理結果一覧
        results_label = QLabel("処理結果:")
        result_layout.addWidget(results_label)
        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(80)
        result_layout.addWidget(self.result_list)
        
        result_tabs.addTab(self.result_widget, "処理結果")
        
        # ログ・デバッグタブ
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        result_tabs.addTab(self.log_view, "ログ・デバッグ")
        
        main_layout.addWidget(result_tabs)

        self.setCentralWidget(main_widget)

        # --- Statusbar ---
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("準備完了")

        self._pending_paths: List[str] = []

    # ----- UI Actions -----
    def append_log(self, text: str):
        self.log_view.append(text)
        self.log_view.ensureCursorVisible()
    
    def add_result(self, result_text: str):
        """処理結果を結果一覧に追加"""
        self.result_list.addItem(result_text)

    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "ファイルを選択", "", "PDF/CSV (*.pdf *.csv)"
        )
        if files:
            self.process_dropped_files(files)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "フォルダを選択")
        if folder:
            folder_path = Path(folder)
            files = []
            for ext in [".pdf", ".csv"]:
                files.extend(folder_path.glob(f"*{ext}"))
            if files:
                self.process_dropped_files([str(p) for p in files])
            else:
                QMessageBox.information(self, "情報", "対応ファイルが見つかりませんでした。")

    def process_dropped_files(self, paths: Iterable[str]):
        for p in paths:
            self._pending_paths.append(p)
            # ファイル一覧に追加
            self.file_list.addItem(f"📄 {Path(p).name}")
        self.status.showMessage(f"{len(paths)} 件を受け取りました。『一括処理』で実行できます。")
        self.append_log(f"受領: {list(paths)}")

    def get_municipality_settings(self):
        """市町村設定を取得"""
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

    def run_batch(self):
        if not self._pending_paths:
            QMessageBox.information(self, "情報", "処理対象がありません。ドラッグ＆ドロップまたは選択してください。")
            return
        
        # 市町村設定をチェック
        settings = self.get_municipality_settings()
        if not settings['municipality_sets']:
            reply = QMessageBox.question(
                self, "設定確認", 
                "自治体が設定されていません。\n設定セクションで都道府県・市町村を入力してから処理を実行することを推奨します。\n\nそのまま続行しますか？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.status.showMessage("処理中…")
        self.append_log("=== 処理開始 ===")
        self.append_log(f"年月設定: {settings['year_month']}")
        for muni_set in settings['municipality_sets']:
            self.append_log(f"セット{muni_set['set_number']}: {muni_set['prefecture']} {muni_set['city']}")
        
        try:
            ok, ng = handle_dropped_files(self._pending_paths, log=self.append_log, settings=settings)
            self.status.showMessage(f"完了：成功 {ok} 件 / 失敗 {ng} 件")
            self.append_log(f"=== 完了：成功 {ok} 件 / 失敗 {ng} 件 ===")
        except Exception as e:
            self.status.showMessage("処理中にエラーが発生しました")
            self.append_log(f"=== エラー: {e} ===")
            QMessageBox.critical(self, "エラー", f"処理中にエラーが発生しました:\n{e}")
        
        self._pending_paths.clear()
        self.file_list.clear()
        self.result_list.clear()

    def run_test(self):
        self.append_log("=== テスト実行開始 ===")
        self.status.showMessage("テスト実行中...")
        
        try:
            # デモスクリプトの実行をシミュレート
            import subprocess
            import sys
            result = subprocess.run([sys.executable, "demo_auto_split_v5_2.py"], 
                                  capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                self.append_log("テスト実行成功")
                self.append_log(result.stdout)
                self.status.showMessage("テスト完了")
            else:
                self.append_log(f"テスト実行失敗: {result.stderr}")
                self.status.showMessage("テスト失敗")
        
        except Exception as e:
            self.append_log(f"テスト実行エラー: {e}")
            self.status.showMessage("テストエラー")
        
        self.append_log("=== テスト実行終了 ===")