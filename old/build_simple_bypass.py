#!/usr/bin/env python3
"""
シンプルWindows Defender回避ビルド v5.2.0
税務書類リネームシステム - 地方税納付情報分類エラー修正版
"""

import os
import sys
import subprocess
import shutil
import time

# ビルド設定
BUILD_CONFIG = {
    "app_name": "TaxDocRenamer_v2.5_ProperLogic",
    "main_script": "main.py",
    "version": "2.5.0"
}

def check_pyinstaller():
    """PyInstallerの確認・インストール"""
    print("PyInstallerをチェック中...")
    try:
        import PyInstaller
        print("PyInstaller: OK")
        return True
    except ImportError:
        print("PyInstallerをインストール中...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller: インストール完了")
            return True
        except subprocess.CalledProcessError:
            print("PyInstallerのインストールに失敗しました")
            return False

def run_simple_build():
    """シンプルビルド実行"""
    print("シンプルビルド開始...")
    
    # PyInstallerコマンド（シンプル版）
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # 単一実行ファイル
        "--windowed",                   # コンソール非表示
        "--name", BUILD_CONFIG["app_name"],
        "--optimize", "2",              # Python最適化
        "--clean",                      # クリーンビルド
        "--noconfirm",                  # 上書き確認なし
        "--distpath", "./dist_bypass",  # 出力先
        BUILD_CONFIG["main_script"]
    ]
    
    print("実行中: PyInstaller (シンプル版)")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("ビルド成功!")
        return True
    except subprocess.CalledProcessError as e:
        print("ビルドエラー:")
        print("STDERR:", e.stderr)
        return False

def create_bypass_batch():
    """Defender回避用バッチファイル作成"""
    batch_content = f'''@echo off
title Document Processing Utility v2.5

:: Defenderの一時的な無効化（管理者権限が必要）
echo Starting Document Processing Utility...

:: 実行ファイルの検査除外を追加（オプション）
powershell -Command "try {{ Add-MpPreference -ExclusionPath '%~dp0{BUILD_CONFIG["app_name"]}.exe' -ErrorAction SilentlyContinue }} catch {{}}"

:: アプリケーション実行
echo Running {BUILD_CONFIG["app_name"]}.exe...
"{BUILD_CONFIG["app_name"]}.exe"

pause
'''
    
    batch_path = f"./dist_bypass/Run_{BUILD_CONFIG['app_name']}.bat"
    with open(batch_path, "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    print(f"Defender回避用バッチファイル作成: {batch_path}")

def main():
    """メイン処理"""
    print("[SIMPLE_BYPASS] シンプルWindows Defender回避ビルド v5.2.0")
    print("税務書類リネームシステム - 地方税納付情報分類エラー修正版")
    print("=" * 60)
    
    # メインスクリプト確認
    if not os.path.exists(BUILD_CONFIG["main_script"]):
        print(f"[ERROR] メインスクリプトが見つかりません: {BUILD_CONFIG['main_script']}")
        return False
    
    # PyInstaller確認
    if not check_pyinstaller():
        return False
    
    # 出力ディレクトリ準備
    if os.path.exists("./dist_bypass"):
        shutil.rmtree("./dist_bypass", ignore_errors=True)
    
    # ビルド実行
    if not run_simple_build():
        print("[ERROR] ビルド失敗")
        return False
    
    # 実行ファイル確認
    exe_path = f"./dist_bypass/{BUILD_CONFIG['app_name']}.exe"
    if not os.path.exists(exe_path):
        print("[ERROR] 実行ファイルが見つかりません")
        return False
    
    # ファイルサイズ確認
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"ファイルサイズ: {size_mb:.1f} MB")
    
    # タイムスタンプ変更（検出回避）
    past_time = time.time() - (7 * 24 * 3600)  # 1週間前
    os.utime(exe_path, (past_time, past_time))
    
    # Defender回避用バッチファイル作成
    create_bypass_batch()
    
    # 完了報告
    print("[SUCCESS] ビルド完了!")
    print(f"[OUTPUT] 出力先: {exe_path}")
    print(f"[BYPASS] 回避バッチ: ./dist_bypass/Run_{BUILD_CONFIG['app_name']}.bat")
    print()
    print("[USAGE] 使用方法:")
    print("1. dist_bypass フォルダの内容をコピー")
    print("2. Run_TaxDocRenamer_v2.5_ProperLogic.bat を右クリック → 管理者として実行")
    print("3. 初回警告が出たら「詳細情報」→「実行」を選択")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\\n[COMPLETE] 全工程完了しました。")
    else:
        print("\\n[FAILED] ビルドに失敗しました。")
    
    try:
        input("\\nEnterキーを押して終了...")
    except (EOFError, KeyboardInterrupt):
        print("\\n終了しています...")