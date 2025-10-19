# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# データファイルの収集
datas = [
    ('app_icon.ico', '.'),  # アプリケーションアイコンをルートに配置
]

# 隠れたインポートを明示的に指定
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'PIL',
    'PIL._tkinter_finder',
    'pypdf',
    're',
    'pathlib',
    'typing',
    'dataclasses',
]

# 除外するモジュール（軽量化のため）
# 注意: pandasはcsv_processor.pyで使用されているため除外しない
excludes = [
    'matplotlib',
    'scipy',
    'IPython',
    'jupyter',
    'notebook',
    'pytest',
    'sphinx',
    'setuptools',
    'wheel',
    'pip',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedirモード（起動が速い）
    name='税務書類リネームシステム',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX圧縮を無効化（Python 3.13互換性のため）
    console=False,  # コンソールウィンドウを非表示
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,  # 管理者権限は不要
    icon='app_icon.ico',  # アプリケーションアイコン（exe, ショートカット, 実行時すべてに適用）
    version_file=None,  # version_info.txtを使用する場合はここに指定
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # UPX圧縮を無効化（Python 3.13互換性のため）
    upx_exclude=[],
    name='税務書類リネームシステム',
)
