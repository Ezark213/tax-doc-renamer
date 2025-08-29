#!/usr/bin/env python3
"""
実行時パス解決ユーティリティ
PyInstaller実行時（sys._MEIPASS）と通常実行の双方に対応
"""

import os
import sys
from pathlib import Path


def get_resource_path(relpath: str) -> str:
    """
    リソースファイルの絶対パスを取得
    
    Args:
        relpath (str): リソースファイルの相対パス（例: "resources/tesseract/bin/tesseract.exe"）
    
    Returns:
        str: リソースファイルの絶対パス
    
    Note:
        PyInstaller使用時は sys._MEIPASS から、
        通常実行時は v4.0 ディレクトリを基準とする
    """
    try:
        # PyInstaller使用時のベースパス（一時展開先）
        base_path = sys._MEIPASS
    except AttributeError:
        # 通常実行時のベースパス（v4.0ディレクトリ）
        # このファイル（core/runtime_paths.py）から見た v4.0 の位置
        current_file = Path(__file__).resolve()
        base_path = current_file.parent.parent  # core/ の親の親 = v4.0/
    
    # 相対パスと結合
    full_path = os.path.normpath(os.path.join(str(base_path), relpath))
    return full_path


def get_tesseract_executable_path() -> str:
    """
    同梱tesseract.exeの絶対パスを取得
    
    Returns:
        str: tesseract.exeの絶対パス
    """
    return get_resource_path("resources/tesseract/bin/tesseract.exe")


def get_tessdata_dir_path() -> str:
    """
    同梱tessdataディレクトリの絶対パスを取得
    
    Returns:
        str: tessdataディレクトリの絶対パス
    """
    return get_resource_path("resources/tesseract/tessdata")


def validate_tesseract_resources() -> bool:
    """
    必要なTesseractリソースが存在するかチェック
    
    Returns:
        bool: すべてのリソースが存在する場合True
    """
    tesseract_exe = get_tesseract_executable_path()
    tessdata_dir = get_tessdata_dir_path()
    jpn_data = get_resource_path("resources/tesseract/tessdata/jpn.traineddata")
    eng_data = get_resource_path("resources/tesseract/tessdata/eng.traineddata")
    
    missing_files = []
    
    if not os.path.isfile(tesseract_exe):
        missing_files.append(f"tesseract.exe: {tesseract_exe}")
    
    if not os.path.isdir(tessdata_dir):
        missing_files.append(f"tessdata directory: {tessdata_dir}")
    
    if not os.path.isfile(jpn_data):
        missing_files.append(f"jpn.traineddata: {jpn_data}")
    
    if not os.path.isfile(eng_data):
        missing_files.append(f"eng.traineddata: {eng_data}")
    
    if missing_files:
        print("Missing Tesseract resources:")
        for missing in missing_files:
            print(f"  - {missing}")
        return False
    
    return True


def get_debug_info() -> dict:
    """
    デバッグ用：パス解決情報を取得
    
    Returns:
        dict: パス情報の辞書
    """
    try:
        meipass = sys._MEIPASS
        is_bundled = True
    except AttributeError:
        meipass = None
        is_bundled = False
    
    current_file = Path(__file__).resolve()
    
    return {
        "is_bundled_executable": is_bundled,
        "sys._MEIPASS": meipass,
        "current_file": str(current_file),
        "calculated_base": str(current_file.parent.parent) if not is_bundled else meipass,
        "tesseract_exe": get_tesseract_executable_path(),
        "tessdata_dir": get_tessdata_dir_path(),
        "resources_valid": validate_tesseract_resources()
    }


if __name__ == "__main__":
    """デバッグ用実行"""
    print("=== Runtime Paths Debug Info ===")
    info = get_debug_info()
    for key, value in info.items():
        print(f"{key}: {value}")
    
    print("\n=== Resource Validation ===")
    if validate_tesseract_resources():
        print("✅ All Tesseract resources are available")
    else:
        print("❌ Some Tesseract resources are missing")
        print("\nPlease check:")
        print("1. tesseract.exe is placed in resources/tesseract/bin/")
        print("2. jpn.traineddata is placed in resources/tesseract/tessdata/")
        print("3. eng.traineddata is placed in resources/tesseract/tessdata/")
        print("\nSee resources/tesseract/README.md for download instructions.")