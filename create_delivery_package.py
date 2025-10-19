#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顧客納品用ZIPパッケージ作成スクリプト
"""

import sys
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

# Windows コンソールのUTF-8対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def create_delivery_package():
    """顧客納品用パッケージを作成"""
    print("=" * 60)
    print("顧客納品用ZIPパッケージ作成")
    print("=" * 60)
    print()

    project_root = Path(__file__).parent
    dist_folder = project_root / 'dist' / '税務書類リネームシステム'

    if not dist_folder.exists():
        print("❌ エラー: ビルドフォルダが見つかりません")
        print(f"   {dist_folder}")
        print("\n先にビルドを実行してください: python build_for_customer.py")
        return False

    # ZIPファイル名（日付付き）
    date_str = datetime.now().strftime("%Y%m%d")
    zip_name = f"税務書類リネームシステム_v8.6.0_{date_str}.zip"
    zip_path = project_root / zip_name

    # 既存のZIPを削除
    if zip_path.exists():
        print(f"🗑️  既存のZIPファイルを削除: {zip_name}")
        zip_path.unlink()

    print(f"📦 ZIPパッケージを作成中: {zip_name}")
    print()

    # ZIPファイルを作成
    total_files = 0
    total_size = 0

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for file_path in dist_folder.rglob('*'):
            if file_path.is_file():
                # ZIP内のパス（税務書類リネームシステム/から始まる）
                arcname = file_path.relative_to(dist_folder.parent)
                zipf.write(file_path, arcname)
                total_files += 1
                total_size += file_path.stat().st_size

                if total_files % 100 == 0:
                    print(f"   処理中... {total_files} ファイル")

    zip_size = zip_path.stat().st_size
    original_mb = total_size / (1024 * 1024)
    compressed_mb = zip_size / (1024 * 1024)
    compression_ratio = (1 - zip_size / total_size) * 100

    print()
    print("=" * 60)
    print("✅ ZIPパッケージ作成完了")
    print("=" * 60)
    print()
    print(f"📄 ファイル名: {zip_name}")
    print(f"📂 保存場所: {project_root}")
    print()
    print(f"📊 パッケージ情報:")
    print(f"   圧縮前: {original_mb:.1f} MB ({total_files} ファイル)")
    print(f"   圧縮後: {compressed_mb:.1f} MB")
    print(f"   圧縮率: {compression_ratio:.1f}%")
    print()
    print("📝 納品手順:")
    print(f"   1. {zip_name} を顧客に送付")
    print("   2. 顧客側で解凍")
    print("   3. '税務書類リネームシステム.lnk' または '税務書類リネームシステム.exe' をダブルクリックで起動")
    print()
    print("✅ 納品準備完了！")
    print()

    return True

if __name__ == '__main__':
    success = create_delivery_package()
    sys.exit(0 if success else 1)
