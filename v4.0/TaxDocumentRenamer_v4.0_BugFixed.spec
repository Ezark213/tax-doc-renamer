# -*- mode: python ; coding: utf-8 -*-
# 税務書類リネームシステム v4.0 バグ修正版ビルドスクリプト
# - 都道府県申告書判定エンジンの修正
# - UI分離（分割・リネーム独立ボタン）
# - 分割機能の実装

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'fitz',  # PyMuPDF
        'pytesseract',
        'PIL',
        'PyPDF2',
        'pandas',
        'numpy'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TaxDocumentRenamer_v4.0_NewFeaturesComplete',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI版（コンソールなし）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # アイコンファイルがあれば指定
)