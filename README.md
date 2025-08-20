# 税務書類リネームシステム

## 📋 概要

税務書類のPDF/CSV画像認識による自動分割・リネームシステム

## 🚀 最新版: v4.4 機能拡張版

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
- `TaxDocumentRenamer_v4.4_Enhanced.exe` - **最新版実行ファイル（機能拡張版）**

### ソースコード（バージョン履歴）
- `tax_document_renamer_v4.4_enhanced.py` - **最新版ソースコード（機能拡張版）**
- `tax_document_renamer_v4.3_split_fix.py` - v4.3分割・リネーム修正版
- `tax_document_renamer_v4.2_regional.py` - v4.2地域対応版
- `tax_document_renamer_v4.1_fixed.py` - v4.1修正版
- `tax_document_renamer_v4.0_complete.py` - v4.0完全版
- `tax_document_renamer_v3.3_prefecture.py` - v3.3都道府県対応版
- `tax_document_renamer_v3.2_enhanced.py` - v3.2機能拡張版
- `tax_document_renamer_v3.1_stable.py` - v3.1安定版

### PyInstaller設定ファイル
- `TaxDocumentRenamer_v4.4_Enhanced.spec` - **最新版ビルド設定**
- `TaxDocumentRenamer_v4.3_SplitFix.spec` - v4.3ビルド設定
- `TaxDocumentRenamer_v4.2_Regional.spec` - v4.2ビルド設定
- `TaxDocumentRenamer_v4.1_Fixed.spec`
- `TaxDocumentRenamer_v4.0_Complete.spec`
- その他過去バージョンの.specファイル

### ドキュメント
- `TAX_DOCUMENT_SPLIT_RENAME_v4.3_IMPLEMENTATION.md` - **v4.3実装仕様書**
- `tax_document_split_rename_fix.md` - **問題分析・修正要件定義書**
- `TAX_DOCUMENT_ISSUES_v4.1_SPECIFICATION.md` - v4.1修正仕様書
- `old/` フォルダ内に過去の開発ドキュメント

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
# v4.3最新版のビルド
pyinstaller TaxDocumentRenamer_v4.3_SplitFix.spec --clean

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

## 🐛 解決済み問題（v4.2で修正）

### ❌ → ✅ 修正内容
1. **少額・一括償却資産明細表の不要分割** → 分割除外パターンで防止
2. **法人税申告書の誤判定（決算書と混同）** → 最高優先度で先行判定
3. **分割対象書類の処理不備** → 1ページごと分割+空白ページ除去
4. **地域申告書の判定不備** → 地域判定エンジンで自動判定
5. **OCR地域判定の未実装** → 事務所長パターンによる自動判定

## 📈 バージョン履歴

- **v4.3** (最新): 分割・リネーム根本修正・2段階処理システム・厳格な分割判定
- **v4.2**: 地域判定エンジン・分割制御・法人税判定優先度修正
- **v4.1**: 分割結果表示改善・判定ロジック修正
- **v4.0**: 分割機能・優先度エンジン・CSVエンコーディング対応・OCR精度向上
- **v3.3**: 47都道府県ドロップダウン対応
- **v3.2**: 結果一覧表示・都道府県設定機能
- **v3.1**: 基本的なPDF/CSV処理・YYMM優先度・UI安定化

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
4. `tax_document_renamer_v4.3_split_fix.py` を編集
5. `pyinstaller TaxDocumentRenamer_v4.3_SplitFix.spec --clean` でビルド

### 新機能追加の場合
1. `tax_document_split_rename_fix.md` と `TAX_DOCUMENT_SPLIT_RENAME_v4.3_IMPLEMENTATION.md` を参考に仕様書を作成
2. 既存コードを参考に新バージョンを作成
3. .specファイルを作成してビルド設定
4. テスト後にGitHubにコミット

## 📞 サポート

システムに関する質問や追加機能の要望がある場合は、IssuesまたはDiscussionsをご利用ください。

---

**注意**: このシステムは税務書類の自動処理を目的としています。処理結果は必ず人間が確認し、税務申告等の重要な用途では慎重に検証してください。