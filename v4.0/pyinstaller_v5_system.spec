# -*- mode: python ; coding: utf-8 -*-
"""
税務書類リネームシステム v5.0 PyInstaller設定ファイル
システムTesseract依存版（実行ファイルのみビルド）
"""

from PyInstaller.utils.hooks import collect_submodules
import os

block_cipher = None

# システムTesseractのパスを検出
import shutil
tesseract_path = shutil.which("tesseract")
if not tesseract_path:
    print("警告: システムTesseractが見つかりません")
    tesseract_binaries = []
else:
    print(f"システムTesseract発見: {tesseract_path}")
    # Windowsの場合、tesseract.exeとDLLを含める
    tesseract_dir = os.path.dirname(tesseract_path)
    tesseract_binaries = [(tesseract_path, '.')]
    
    # 必要なDLLも含める（存在する場合）
    possible_dlls = [
        'leptonica-1.83.0.dll', 'libgcc_s_seh-1.dll', 'libstdc++-6.dll',
        'libwinpthread-1.dll', 'zlib1.dll'
    ]
    for dll in possible_dlls:
        dll_path = os.path.join(tesseract_dir, dll)
        if os.path.exists(dll_path):
            tesseract_binaries.append((dll_path, '.'))

a = Analysis(
    ['main_v5.py'],
    pathex=['.'],
    binaries=tesseract_binaries,
    datas=[
        # ドキュメント
        ('README_v5.md', '.'),
        ('V5_運用ガイド.md', '.'),
        
        # ライセンス情報
        ('licenses/TESSERACT_LICENSE', 'licenses'),
        ('licenses/README.md', 'licenses'),
        
        # プレースホルダーとガイド（参考用）
        ('resources/tesseract/README.md', 'resources/tesseract'),
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

# OneFile版（推奨）
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TaxDocRenamer_v5.0_SystemTesseract',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI想定のためFalse
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# OneDir版（コメントアウト）
"""
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TaxDocRenamer_v5.0_SystemTesseract',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TaxDocRenamer_v5.0_SystemTesseract',
)
"""