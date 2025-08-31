#!/usr/bin/env python3
"""
配布パッケージ作成スクリプト
"""

import os
import shutil
import datetime
from pathlib import Path

def create_package():
    """配布パッケージ作成"""
    
    # パッケージディレクトリ
    package_name = "TaxDocumentRenamer_v5_Fixed_Package"
    package_dir = f"dist/{package_name}"
    
    # 既存のパッケージディレクトリを削除
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    
    # パッケージディレクトリ作成
    os.makedirs(package_dir)
    
    # 実行ファイルコピー
    exe_source = "dist/TaxDocumentRenamer_v5_Fixed.exe"
    exe_dest = f"{package_dir}/TaxDocumentRenamer_v5_Fixed.exe"
    
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, exe_dest)
        print(f"実行ファイルをコピーしました: {exe_dest}")
    else:
        print("実行ファイルが見つかりません")
        return False
    
    # README作成
    readme_content = f"""# 税務書類リネームシステム v5.0 修正版

## バージョン情報
- バージョン: 5.0.1
- ビルド日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 対応システム: Windows 10/11

## 主な機能

### セットベース連番システム
- **セット1 (東京都)**: 1001, 1003, 1004 (市町村コードなし)
- **セット2 (愛知県蒲郡市)**: 1011, 1013, 1014 + 2001, 2003, 2004
- **セット3 (福岡県福岡市)**: 1021, 1023, 1024 + 2011, 2013, 2014

### 連番ルール統一
- **受信通知**: 必ず末尾03 (1003, 1013, 1023, 2003, 2013)
- **納付情報**: 必ず末尾04 (1004, 1014, 1024, 2004, 2014)  
- **申告書**: 必ず末尾01 (1001, 1011, 1021, 2001, 2011)

### OCR突合チェック機能
- セット判定後、OCRテキストとダブルチェック
- 矛盾検出時は自動アラート表示
- 信頼度スコア付きの詳細レポート

## 使用方法

1. **アプリケーション起動**
   - `TaxDocumentRenamer_v5_Fixed.exe` をダブルクリック

2. **ファイル追加**
   - PDFファイルをドラッグ&ドロップ
   - または「ファイル選択」「フォルダ選択」ボタンを使用

3. **設定確認**
   - 年月設定 (YYMM形式、例: 2508)
   - 「セットベース連番モード」をON（推奨）
   - 「OCR突合チェック・アラート機能」をON（推奨）

4. **リネーム実行**
   - 「リネーム実行 (修正版)」ボタンをクリック
   - 処理結果とアラートを確認

## 修正内容（v5.0対応）

### バグ修正
- 受信通知の番号付けエラー解決（1001→1003等）
- 納付情報の認識エラー解決（1001_受信通知→1004_納付情報等）
- 都道府県書類の番号統一（全て1011→適切な1001,1011,1021）
- 市町村書類の名称・番号修正

### 新機能
- セット基準の自動判定システム
- OCRテキストとの矛盾チェック
- 詳細なアラート・警告表示
- 信頼度スコア表示
- 処理結果の詳細レポート

## アラート種類

- **SUCCESS**: 正常処理完了
- **MISMATCH**: OCRテキストと判定結果の矛盾
- **AMBIGUOUS**: 複数セットが同スコアで曖昧
- **NOT_FOUND**: セット検出失敗

## トラブルシューティング

### 一般的な問題
- **セット検出失敗**: 手動でセット確認、キーワード不足の可能性
- **矛盾アラート**: OCRテキストを再確認、手動修正を検討
- **処理エラー**: ログタブでエラー詳細を確認

### サポート
問題が解決しない場合は、ログ情報と共にお問い合わせください。

## 動作環境
- Windows 10 以降
- メモリ: 4GB以上推奨
- ディスク容量: 100MB以上の空き容量

---
開発: 石井公認会計士・税理士事務所
Copyright (C) 2024
"""

    # README.md作成
    with open(f"{package_dir}/README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # 使用方法テキスト作成
    usage_content = """税務書類リネームシステム v5.0 修正版 - クイックスタート

【セット設定】
セット1: 東京都 (1001, 1003, 1004)
セット2: 愛知県蒲郡市 (1011, 1013, 1014) + (2001, 2003, 2004)  
セット3: 福岡県福岡市 (1021, 1023, 1024) + (2011, 2013, 2014)

【基本操作】
1. TaxDocumentRenamer_v5_Fixed.exe を実行
2. PDFファイルをドラッグ&ドロップ
3. 年月設定 (例: 2508)
4. 「セットベース連番モード」ON
5. 「リネーム実行 (修正版)」クリック

【期待される結果例】
- 0003_受信通知_2508【元々3_国税】.pdf → 1003_受信通知_2508.pdf
- 0004_納付情報_2508【元々5_国税】.pdf → 1004_納付情報_2508.pdf
- 1013_受信通知_2508【元々5_地方税】.pdf → 1013_受信通知_2508.pdf
- 2003_受信通知_2508【元々4_地方税】.pdf → 2003_受信通知_2508.pdf

【重要】
アラート表示時は内容を確認し、必要に応じて手動調整してください。
"""
    
    with open(f"{package_dir}/使用方法.txt", "w", encoding="utf-8") as f:
        f.write(usage_content)
    
    print(f"配布パッケージ作成完了: {package_dir}")
    print(f"含まれるファイル:")
    for file in os.listdir(package_dir):
        file_path = os.path.join(package_dir, file)
        size = os.path.getsize(file_path) / (1024*1024)
        print(f"  - {file} ({size:.1f} MB)")
    
    return True

if __name__ == "__main__":
    create_package()