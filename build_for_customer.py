#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顧客納品用ビルドスクリプト
- PyInstallerでアプリをビルド
- 軽量化設定を適用
- ビルド後にショートカットを自動作成
"""

import subprocess
import os
import sys
import shutil
from pathlib import Path

# Windows コンソールのUTF-8対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def create_shortcut(target_path, shortcut_path, icon_path=None):
    """Windowsショートカットを作成"""
    try:
        from win32com.client import Dispatch

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = str(target_path)
        shortcut.WorkingDirectory = str(target_path.parent)
        if icon_path and os.path.exists(icon_path):
            shortcut.IconLocation = str(icon_path)
        shortcut.save()
        return True
    except Exception as e:
        print(f"⚠️  ショートカット作成エラー: {e}")
        print("   pywin32がインストールされていない可能性があります")
        print("   pip install pywin32 を実行してください")
        return False

def main():
    print("=" * 60)
    print("税務書類リネームシステム v8.6.0 - 顧客納品用ビルド")
    print("=" * 60)
    print()

    # プロジェクトルート
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # 既存のビルドフォルダを削除
    print("📁 既存のビルドフォルダをクリーンアップ中...")
    folders_to_clean = ['build', 'dist']
    for folder in folders_to_clean:
        folder_path = project_root / folder
        if folder_path.exists():
            print(f"   削除: {folder}")
            shutil.rmtree(folder_path)
    print("✅ クリーンアップ完了\n")

    # PyInstallerでビルド
    print("🔨 PyInstallerでアプリケーションをビルド中...")
    print("   設定: onedirモード（軽量・高速起動）")
    print("   除外モジュール: matplotlib, scipy, jupyter, pytest, etc.")
    print()

    spec_file = project_root / 'build_app.spec'

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', str(spec_file), '--clean'],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ ビルド成功\n")
    except subprocess.CalledProcessError as e:
        print("❌ ビルド失敗")
        print(f"エラー: {e.stderr}")
        return False

    # 出力フォルダを確認
    dist_folder = project_root / 'dist' / '税務書類リネームシステム'
    exe_path = dist_folder / '税務書類リネームシステム.exe'

    if not exe_path.exists():
        print(f"❌ 実行ファイルが見つかりません: {exe_path}")
        return False

    print(f"📦 ビルド完了: {dist_folder}")
    print(f"   実行ファイル: {exe_path.name}")
    print()

    # ショートカットを作成
    print("🔗 デスクトップショートカットを作成中...")
    shortcut_path = dist_folder / '税務書類リネームシステム.lnk'
    icon_path = dist_folder / 'app_icon.ico'

    if create_shortcut(exe_path, shortcut_path, icon_path if icon_path.exists() else None):
        print(f"✅ ショートカット作成完了: {shortcut_path.name}")
    else:
        print("⚠️  ショートカット作成をスキップ")
    print()

    # ビルド情報を表示
    print("=" * 60)
    print("✅ 顧客納品用パッケージの準備完了")
    print("=" * 60)
    print()
    print(f"📂 納品フォルダ: {dist_folder}")
    print(f"📄 実行ファイル: {exe_path.name}")
    print(f"🔗 ショートカット: {shortcut_path.name}")
    print()

    # フォルダサイズを計算
    total_size = 0
    file_count = 0
    for file in dist_folder.rglob('*'):
        if file.is_file():
            total_size += file.stat().st_size
            file_count += 1

    size_mb = total_size / (1024 * 1024)
    print(f"📊 パッケージ情報:")
    print(f"   ファイル数: {file_count}")
    print(f"   合計サイズ: {size_mb:.1f} MB")
    print()

    print("📝 納品手順:")
    print("   1. dist/税務書類リネームシステム フォルダ全体をZIP圧縮")
    print("   2. 顧客にZIPファイルを送付")
    print("   3. 顧客側で解凍後、.lnkファイルまたは.exeファイルをダブルクリックで起動")
    print()

    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
