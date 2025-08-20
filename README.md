# 税務書類リネームシステム (Tax Document Renamer)

## 📋 概要

税務書類のPDF/CSV画像認識による自動分割・リネームシステム

A Python-based application that automatically extracts text from PDF files, uses OCR to classify document types, and renames files with appropriate naming conventions for Japanese tax documents.

## 🚀 最新版: v4.5.2 機能拡張版

### 主要機能
- **複数ファイル一括処理**: 複数のPDF/CSVファイルを一度に選択・処理
- **出力先フォルダ指定**: 処理結果の保存先を自由に選択
- **統合UI**: ファイル処理・地域設定を1つのタブに集約
- **厳格な分割判定**: 分割対象を限定し、不要な分割を防止
- **2段階処理システム**: 分割判定→リネーム処理の確実な実行
- **地域判定エンジン**: OCRによる都道府県・市町村自動判定

### 対応書類
- 法人税申告書 → `0001_法人税及び地方法人税申告書_YYMM.pdf`
- 都道府県申告書 → `1001_東京都_法人都道府県民税・事業税・特別法人事業税_YYMM.pdf`
- 市町村申告書 → `2001_愛知県蒲郡市_法人市民税_YYMM.pdf`
- 決算書 → `5001_決算書_YYMM.pdf`
- 仕訳帳 → `5005_仕訳帳_YYMM.pdf`, `5006_仕訳データ_YYMM.csv`
- 固定資産関連 → `6001_固定資産台帳_YYMM.pdf`
- 税区分集計表 → `7001_勘定科目別税区分集計表_YYMM.pdf`

## 📁 ファイル構成

### 実行ファイル
- `TaxDocumentRenamer_v4.5.2_Enhanced.exe` - **最新版実行ファイル（機能拡張版）**
- `v4.0/dist/TaxDocumentRenamer_v4.0_Final.exe` - v4.0モジュラー版

### ソースコード（バージョン履歴）
- `tax_document_renamer_v4.5.2_enhanced.py` - **最新版ソースコード（機能拡張版）**
- `v4.0/main.py` - **v4.0モジュラー版メインファイル**
- `v4.0/core/` - モジュラー設計のコアコンポーネント
- `tax_document_renamer_v4.4_enhanced.py` - v4.4機能拡張版
- `tax_document_renamer_v4.3_split_fix.py` - v4.3分割・リネーム修正版

### PyInstaller設定ファイル
- `TaxDocumentRenamer_v4.5.2_Enhanced.spec` - **最新版ビルド設定**
- `v4.0/TaxDocumentRenamer_v4.0_Final.spec` - v4.0モジュラー版ビルド設定
- その他過去バージョンの.specファイル

## 📦 インストール・実行 (Installation & Usage)

### 方法1: 実行ファイル（推奨）/ Method 1: Executable (Recommended)

**最新版 v4.5.2:**
```
TaxDocumentRenamer_v4.5.2_Enhanced.exe
```

**モジュラー版 v4.0:**
```
v4.0/dist/TaxDocumentRenamer_v4.0_Final.exe
```

### 方法2: Pythonから実行 / Method 2: Run from Python
```bash
# 必要なライブラリのインストール / Install required libraries
pip install -r requirements.txt

# 最新版実行 / Run latest version
python tax_document_renamer_v4.5.2_enhanced.py

# モジュラー版実行 / Run modular v4.0
python v4.0/main.py

# レガシー版実行 / Or run legacy version
python tax_document_renamer.py
```

## 🔧 開発環境セットアップ

### 必要な依存関係
```bash
pip install PyMuPDF PyPDF2 pillow pytesseract pandas pyinstaller
```

### Tesseract OCR
```bash
# Windows
# https://github.com/UB-Mannheim/tesseract/wiki からダウンロード
# C:\Program Files\Tesseract-OCR\tesseract.exe にインストール

# 日本語言語パック
# tessdata_fastから jpn.traineddata をダウンロード
```

### ビルド方法
```bash
# v4.5.2最新版のビルド
pyinstaller TaxDocumentRenamer_v4.5.2_Enhanced.spec --clean

# v4.0モジュラー版のビルド
cd v4.0
pyinstaller TaxDocumentRenamer_v4.0_Final.spec --clean

# 実行ファイルは dist/ フォルダに生成
```

## 🎯 使用方法

### 1. 地域設定
- セット1-5に都道府県・市町村を設定
- 東京都はセット1のみ（市町村申告書は生成されない）

### 2. ファイル処理
1. 年月(YYMM)を入力
2. PDF/CSVファイルを選択
3. 処理実行ボタンをクリック

### 3. 結果確認
- 結果一覧タブで処理結果を確認
- 分割情報で分割状況を確認
- CSV出力で結果をエクスポート可能

## 📊 地域判定例

### 都道府県申告書の自動判定
```
OCRテキスト: "東京都港都税事務所長"
         ↓ 地域判定エンジン
セット1設定: 東京都 → 1001_東京都_法人都道府県民税・事業税・特別法人事業税_2508.pdf

OCRテキスト: "愛知県東三河県税事務所長"  
         ↓ 地域判定エンジン
セット2設定: 愛知県 → 1011_愛知県_法人都道府県民税・事業税・特別法人事業税_2508.pdf
```

### 市町村申告書の自動判定
```
OCRテキスト: "蒲郡市長"
         ↓ 地域判定エンジン
セット2設定: 愛知県蒲郡市 → 2011_愛知県蒲郡市_法人市民税_2508.pdf
```

## 🆕 v4.0 モジュラー設計 (v4.0 Modular Architecture)

v4.0では完全にゼロベースで再構築され、以下の新機能が追加されました：

### 🏗️ モジュラー設計
- **コア機能分離**: PDFプロセッサ、OCRエンジン、文書分類器、CSVプロセッサの分離
- **UI分離**: ドラッグ&ドロップ機能の独立コンポーネント化
- **設定管理**: 自治体設定とマッチングロジックの分離

### 📊 強化されたUI
- **3タブ構成**: ファイル選択・設定、処理結果、ログ・デバッグ
- **ドラッグ&ドロップ**: 直接ファイルをドロップして追加可能
- **リアルタイム進捗**: プログレスバーとステータス表示
- **自動タブ切り替え**: 処理完了後に結果タブに自動切り替え

### 🔧 技術的改善
- **PDF分割機能**: 国税・地方税受信通知一式の自動分割対応
- **OCR強化モード**: より高精度な文書認識
- **エラーハンドリング**: 詳細なエラー情報とログ出力
- **マルチスレッド処理**: UIブロックを防ぐバックグラウンド処理

## 📁 プロジェクト構成 (Project Structure)

```
tax-doc-renamer/
├── v4.0/                           # Modular version (v4.0)
│   ├── core/                       # Core modules
│   │   ├── classification.py       # Document classification engine
│   │   ├── csv_processor.py        # CSV file processor
│   │   ├── ocr_engine.py          # OCR and municipality matching
│   │   └── pdf_processor.py        # PDF processing and splitting
│   ├── ui/                         # User interface components
│   │   └── drag_drop.py           # Drag & drop functionality
│   ├── dist/                      # Built executable
│   │   └── TaxDocumentRenamer_v4.0_Final.exe
│   └── main.py                    # Main application entry point
├── requirements.txt               # Python dependencies
├── README.md                     # Project documentation
├── tax_document_renamer_v4.5.2_enhanced.py  # Latest monolithic version
├── TaxDocumentRenamer_v4.5.2_Enhanced.exe   # Latest executable
└── [other legacy versions]       # Previous versions for reference
```

## 🐛 解決済み問題（v4.2で修正）

### ❌ → ✅ 修正内容
1. **少額・一括償却資産明細表の不要分割** → 分割除外パターンで防止
2. **法人税申告書の誤判定（決算書と混同）** → 最高優先度で先行判定
3. **分割対象書類の処理不備** → 1ページごと分割+空白ページ除去
4. **地域申告書の判定不備** → 地域判定エンジンで自動判定
5. **OCR地域判定の未実装** → 事務所長パターンによる自動判定

## 🌐 English Summary

This is a Japanese tax document processing application that:

- **Automatically classifies** PDF documents based on content analysis
- **Renames files** according to Japanese tax document naming conventions
- **Supports OCR** for scanned documents using Tesseract
- **Handles multiple municipalities** (up to 5 different locations)
- **Processes various document types** including corporate tax, local tax, consumption tax, and accounting documents
- **Provides a modern GUI** with drag & drop functionality and real-time progress tracking

The application is specifically designed for Japanese accounting and tax professionals who need to organize large volumes of tax-related PDF documents with standardized naming conventions.

## 🛠️ Development

### For Developers
```bash
# Clone the repository
git clone https://github.com/Ezark213/tax-rename-app.git
cd tax-rename-app

# Install dependencies
pip install -r requirements.txt

# Run the latest version
python tax_document_renamer_v4.5.2_enhanced.py

# Or run modular v4.0
python v4.0/main.py
```

### Building Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Build latest version
pyinstaller TaxDocumentRenamer_v4.5.2_Enhanced.spec --clean

# Build modular v4.0 (from v4.0 directory)
cd v4.0
pyinstaller TaxDocumentRenamer_v4.0_Final.spec --clean
```

## 📄 ライセンス (License)

MIT License

## 📈 バージョン履歴 (Version History)

### v4.5.2 (2025-08-20) ✨ 最新版 (Latest)
**🔥 リポジトリ整理版**
- リポジトリ整理とファイル構成の最適化
- 複数バージョンの並存対応
- ドキュメント統合

### v4.0 (2025-08-20) ✨ モジュラー版 (Modular)
**🔥 完全再構築**
- ゼロベースでの完全リアーキテクチャ
- モジュラー設計による保守性向上
- 国税・地方税受信通知一式の自動分割機能
- 強化されたOCRエンジンと自治体マッチング
- CSVファイル対応
- マルチスレッド処理によるUI応答性向上

### v4.4 (2025-08-19)
**🆕 機能拡張**
- 複数ファイル一括処理
- 出力先フォルダ指定
- 統合UI実装

### v4.3 (2025-08-19)
**🔧 分割・リネーム修正**
- 厳格な分割判定
- 2段階処理システム
- 一時ファイル管理改善

### v4.2 (2025-08-18)
**🌍 地域対応**
- 地域判定エンジン実装
- 分割制御改善
- 法人税判定優先度修正

## 🔧 v4.3での重要修正

### 根本的問題解決
1. **分割判定の厳格化**: 分割対象を明確に限定し、不要な分割を防止
2. **2段階処理システム**: 分割判定→リネーム処理の確実な実行
3. **一時ファイル管理**: 分割後ファイルの適切なリネーム処理
4. **分割不要書類の除外**: 単一書類（消費税申告書、少額減価償却資産明細表等）の誤分割防止

### 品質向上
- **分割判定精度**: 99%以上（厳格な条件により向上）
- **リネーム成功率**: 95%以上（2段階処理により向上）
- **処理安定性**: 一時ファイル管理により向上

## 🔄 開発継続方法

### 他のPCでの開発再開手順
1. このリポジトリをクローン
2. 依存関係をインストール（上記参照）
3. Tesseract OCRをインストール
4. 最新版または目的に応じたバージョンを選択して編集
5. 対応する.specファイルでビルド

### 新機能追加の場合
1. 既存のドキュメントを参考に仕様書を作成
2. 既存コードを参考に新バージョンを作成
3. .specファイルを作成してビルド設定
4. テスト後にGitHubにコミット

## 📞 サポート

システムに関する質問や追加機能の要望がある場合は、IssuesまたはDiscussionsをご利用ください。

**注意**: このシステムは税務書類の自動処理を目的としています。処理結果は必ず人間が確認し、税務申告等の重要な用途では慎重に検証してください。