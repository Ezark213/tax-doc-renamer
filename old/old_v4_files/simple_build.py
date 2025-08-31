#!/usr/bin/env python3
"""
v5.0システム シンプルビルドスクリプト
"""

import os
import shutil
import time
from pathlib import Path

def create_distribution():
    """配布用パッケージを作成"""
    print("税務書類リネームシステム v5.0 配布パッケージ作成")
    print("=" * 50)
    
    # ビルドディレクトリ作成
    build_dir = Path("TaxDocRenamer_v5.0_Distribution")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    
    print("必要ファイルをコピー中...")
    
    # ファイル構造を作成
    (build_dir / "core").mkdir()
    (build_dir / "docs").mkdir()
    (build_dir / "tools").mkdir()
    
    # 必要なファイルをコピー
    files = [
        ("core/classification_v5.py", "core/classification_v5.py"),
        ("main_v5.py", "main_v5.py"),
        ("test_v5.py", "test_v5.py"),
        ("V5_運用ガイド.md", "docs/V5_運用ガイド.md"),
        ("README_v5.md", "docs/README_v5.md"),
        ("CHANGELOG_v5.md", "docs/CHANGELOG_v5.md"),
        ("production_readiness_check.py", "tools/production_readiness_check.py")
    ]
    
    for src, dst in files:
        src_path = Path(src)
        dst_path = build_dir / dst
        
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"  {src} -> {dst}")
        else:
            print(f"  警告: {src} が見つかりません")
    
    # requirements.txt作成
    requirements = """# 税務書類リネームシステム v5.0 必要ライブラリ
PyMuPDF>=1.21.0
"""
    with open(build_dir / "requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)
    
    # 起動バッチファイル作成 (Windows用)
    batch_content = """@echo off
echo 税務書類リネームシステム v5.0 起動中...
python main_v5.py
pause
"""
    with open(build_dir / "start_system.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    # インストール手順書
    install_guide = f"""# インストール手順

## 必要環境
- Python 3.8以上
- PyMuPDF ライブラリ

## インストール手順
1. 必要ライブラリのインストール:
   pip install -r requirements.txt

2. システム起動:
   - Windows: start_system.bat をダブルクリック
   - コマンドライン: python main_v5.py

3. 使用方法:
   - v5.0モードにチェックを入れる
   - PDFフォルダを選択
   - リネーム実行

## テスト実行
python test_v5.py

## ドキュメント
- docs/README_v5.md : システム概要
- docs/V5_運用ガイド.md : 詳細運用マニュアル
- docs/CHANGELOG_v5.md : 変更履歴

## 作成日
{time.strftime("%Y年%m月%d日 %H:%M:%S")}

バージョン: 5.0.0
"""
    
    with open(build_dir / "INSTALL.md", "w", encoding="utf-8") as f:
        f.write(install_guide)
    
    # バージョン情報
    version_content = f"""{{
  "version": "5.0.0",
  "build_date": "{time.strftime('%Y-%m-%d %H:%M:%S')}",
  "description": "税務書類リネームシステム v5.0 - AND条件判定機能搭載版",
  "features": [
    "AND条件判定機能",
    "100%分類精度達成",
    "高速処理対応",
    "本番運用準備完了"
  ]
}}"""
    
    with open(build_dir / "version.json", "w", encoding="utf-8") as f:
        f.write(version_content)
    
    print(f"\n配布パッケージ作成完了!")
    print(f"場所: {build_dir.absolute()}")
    print(f"\n内容物:")
    
    # 作成されたファイル一覧を表示
    for item in sorted(build_dir.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(build_dir)
            print(f"  {rel_path}")
    
    return build_dir

if __name__ == "__main__":
    distribution_dir = create_distribution()
    
    print("\n" + "=" * 50)
    print("配布準備完了!")
    print("=" * 50)
    print("配布手順:")
    print("1. フォルダ全体をZIP圧縮")
    print("2. 配布先で展開")  
    print("3. INSTALL.md の手順に従ってセットアップ")
    print("4. start_system.bat で起動")
    
    print("\n確認方法:")
    print("- python test_v5.py でテスト実行")
    print("- tools/production_readiness_check.py で本番準備確認")