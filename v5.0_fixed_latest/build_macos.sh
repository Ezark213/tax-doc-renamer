#!/bin/bash
# 税務書類リネームシステム v5.0 macOSビルドスクリプト
# Tesseract同梱版

set -e  # エラー時に停止

echo "========================================"
echo "税務書類リネームシステム v5.0 macOSビルド"
echo "========================================"

# 現在のディレクトリに移動
cd "$(dirname "$0")"

# システム情報の表示
echo "[0/5] システム情報..."
uname -a
python3 --version
echo "PyInstaller version: $(pyinstaller --version)"

# 必要ファイルの存在確認
echo "[1/5] 必要ファイルの確認..."
if [ ! -f "main_v5.py" ]; then
    echo "エラー: main_v5.py が見つかりません"
    exit 1
fi

# macOS用tesseractバイナリの確認
if [ ! -f "resources/tesseract/bin/tesseract" ]; then
    echo "警告: tesseract (macOS版) が見つかりません"
    echo "resources/tesseract/bin/tesseract を配置してください"
    echo "取得方法:"
    echo "  Intel Mac: brew install tesseract からバイナリをコピー"
    echo "  Apple Silicon: arm64版tesseractをコンパイル"
    echo "詳細は resources/tesseract/README.md を参照"
    exit 1
fi

if [ ! -f "resources/tesseract/tessdata/jpn.traineddata" ]; then
    echo "警告: jpn.traineddata が見つかりません"
    echo "resources/tesseract/tessdata/jpn.traineddata を配置してください"
    exit 1
fi

if [ ! -f "resources/tesseract/tessdata/eng.traineddata" ]; then
    echo "警告: eng.traineddata が見つかりません"
    echo "resources/tesseract/tessdata/eng.traineddata を配置してください"
    exit 1
fi

# アーキテクチャ判定
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    TARGET_ARCH="arm64"
    BUILD_SUFFIX="AppleSilicon"
    echo "Apple Silicon (arm64) ビルドモード"
else
    TARGET_ARCH="x86_64"
    BUILD_SUFFIX="Intel"
    echo "Intel (x86_64) ビルドモード"
fi

echo "[2/5] 古いビルドファイルのクリーンアップ..."
rm -rf build dist "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}"

echo "[3/5] PyInstaller OneFileビルド実行..."
pyinstaller --clean --noconfirm \
  --onefile \
  --name "TaxDocRenamer_v5.0_${BUILD_SUFFIX}" \
  --add-data "resources/tesseract/bin/tesseract:resources/tesseract/bin" \
  --add-data "resources/tesseract/tessdata/jpn.traineddata:resources/tesseract/tessdata" \
  --add-data "resources/tesseract/tessdata/eng.traineddata:resources/tesseract/tessdata" \
  --add-data "resources/tesseract/README.md:resources/tesseract" \
  --add-data "licenses/TESSERACT_LICENSE:licenses" \
  --add-data "licenses/README.md:licenses" \
  --add-data "README_v5.md:." \
  --add-data "V5_運用ガイド.md:." \
  --hidden-import pytesseract \
  --hidden-import PyPDF2 \
  --hidden-import fitz \
  --hidden-import PIL \
  --hidden-import pandas \
  --exclude-module matplotlib \
  --exclude-module scipy \
  --exclude-module sklearn \
  --target-arch "$TARGET_ARCH" \
  --windowed \
  main_v5.py

if [ $? -ne 0 ]; then
    echo "エラー: PyInstallerビルドに失敗しました"
    exit 1
fi

echo "[4/5] macOS版パッケージ作成..."
mkdir -p "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}"

# 実行ファイルの移動
if [ -f "dist/TaxDocRenamer_v5.0_${BUILD_SUFFIX}" ]; then
    mv "dist/TaxDocRenamer_v5.0_${BUILD_SUFFIX}" "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/"
    
    # 実行権限を付与
    chmod +x "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/TaxDocRenamer_v5.0_${BUILD_SUFFIX}"
else
    echo "エラー: ビルドされた実行ファイルが見つかりません"
    exit 1
fi

# ドキュメントファイルの追加
cp "README_v5.md" "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/README.md"
cp "V5_運用ガイド.md" "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/"

# macOS版専用README作成
cat > "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/README_macOS.txt" << EOF
# 税務書類リネームシステム v5.0 macOS版 (${BUILD_SUFFIX})

このフォルダにはTesseract同梱のmacOS版が含まれています。

## 使用方法
1. TaxDocRenamer_v5.0_${BUILD_SUFFIX} をダブルクリック
2. 初回起動時に「開発元を確認できません」が表示される場合:
   - 右クリック → [開く] を選択
   - または: システム環境設定 → セキュリティとプライバシー → [このまま許可]
3. PDFファイルをドラッグ&ドロップまたはファイル選択
4. 自治体情報・年月を入力
5. 分割・分類・リネーム実行

## 特徴
- Tesseract OCR同梱（Homebrew不要）
- 単一実行ファイル
- ${BUILD_SUFFIX} アーキテクチャ対応

## システム要件
- macOS 10.14 Mojave以降
- Python環境不要

## セキュリティについて
このアプリはApple Developer Program未参加のため、初回起動時に警告が表示されます。
安全性は以下で確認できます：

### コード署名情報確認
\`\`\`bash
codesign -dv TaxDocRenamer_v5.0_${BUILD_SUFFIX}
\`\`\`

### ファイルハッシュ確認
\`\`\`bash
shasum -a 256 TaxDocRenamer_v5.0_${BUILD_SUFFIX}
\`\`\`

## サポート
詳細なドキュメントは README.md および V5_運用ガイド.md を参照
EOF

# 実行用スクリプト作成（Gatekeeper対応）
cat > "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/run.sh" << 'EOF'
#!/bin/bash
# Gatekeeper対応起動スクリプト

echo "税務書類リネームシステム v5.0 を起動しています..."

# 実行ファイルのパス
EXEC_FILE="$(dirname "$0")/TaxDocRenamer_v5.0_*"

# quarantine属性を削除（初回実行時のセキュリティ警告を回避）
xattr -d com.apple.quarantine "$EXEC_FILE" 2>/dev/null || true

# アプリを起動
exec "$EXEC_FILE"
EOF

chmod +x "TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/run.sh"

echo "[5/5] クリーンアップ..."
rm -rf build

echo ""
echo "========================================"
echo "✅ macOS版ビルド完了!"
echo "========================================"
echo ""
echo "出力フォルダ: TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/"
echo "実行ファイル: TaxDocRenamer_v5.0_${BUILD_SUFFIX}"
echo "起動スクリプト: run.sh"
echo ""
echo "アーキテクチャ: $ARCH ($TARGET_ARCH)"
echo ""
echo "テスト実行:"
echo "./TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/TaxDocRenamer_v5.0_${BUILD_SUFFIX}"
echo "または:"
echo "./TaxDocRenamer_v5.0_macOS_${BUILD_SUFFIX}/run.sh"
echo ""
echo "注意事項:"
echo "- 初回起動時にGatekeeperの警告が表示される場合があります"
echo "- 右クリック → [開く] で回避可能です"
echo "- codesign/notarize未実施のため配布時は要注意"
echo ""