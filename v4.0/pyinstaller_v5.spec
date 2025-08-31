# -*- mode: python ; coding: utf-8 -*-
"""
税務書類リネームシステム v5.0 PyInstaller設定ファイル
Tesseract同梱版ビルド用
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['main_v5.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Tesseractリソース
        ('resources/tesseract/bin/tesseract.exe', 'resources/tesseract/bin'),
        ('resources/tesseract/tessdata/jpn.traineddata', 'resources/tesseract/tessdata'),
        ('resources/tesseract/tessdata/eng.traineddata', 'resources/tesseract/tessdata'),
        ('resources/tesseract/README.md', 'resources/tesseract'),
        
        # ライセンスファイル
        ('licenses/TESSERACT_LICENSE', 'licenses'),
        ('licenses/README.md', 'licenses'),
        
        # コアモジュール（必要に応じて）
        ('core', 'core'),
        ('ui', 'ui'),
        
        # ドキュメント（オプション）
        ('README_v5.md', '.'),
        ('V5_運用ガイド.md', '.'),
    ],
    hiddenimports=[
        # PyTesseract関連
        'pytesseract',
        
        # PDF処理
        'PyPDF2',
        'fitz',  # PyMuPDF
        
        # 画像処理
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        
        # その他の依存関係
        'pandas',
        'numpy',
        
        # プロジェクト固有モジュール
        'core.pdf_processor',
        'core.ocr_engine', 
        'core.csv_processor',
        'core.classification_v5',
        'core.runtime_paths',
        'ui.drag_drop',
    ] + collect_submodules('pytesseract'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 不要なモジュールを除外（サイズ最適化）
        'matplotlib',
        'scipy',
        'sklearn',
        'jupyter',
        'IPython',
        'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TaxDocRenamer_v5.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI想定のためFalse。CLIのみならTrueに変更
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # アイコンファイルがあれば指定
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TaxDocRenamer_v5.0',
)

# OneFile版の設定（コメントアウト）
# OneFileビルドする場合は以下のコメントを外し、上記のEXEとCOLLECTをコメントアウト
"""
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TaxDocRenamer_v5.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
"""