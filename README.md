# 税務書類リネームシステム v5.1

[![税務書類](https://img.shields.io/badge/%E7%A8%8E%E5%8B%99%E6%9B%B8%E9%A1%9E-v5.1-blue.svg)](https://github.com/Ezark213/tax-doc-renamer)
[![Python](https://img.shields.io/badge/Python-3.13+-green.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

日本の税務書類を自動的に分類・リネームするシステムです。OCR機能を使用してPDFから文字を読み取り、適切な書類番号とファイル名を自動で割り当てます。

## 🚀 クイックスタート

### 実行ファイル版（推奨）
1. [TaxDocumentRenamer.exe](TaxDocumentRenamer.exe) をダウンロード
2. ダブルクリックで起動
3. PDFファイルをドラッグ&ドロップするだけ！

### Python版
```bash
git clone https://github.com/Ezark213/tax-doc-renamer.git
cd tax-doc-renamer
pip install -r requirements.txt
python main.py
```

## 📋 対応書類一覧

| 分類 | 番号 | 書類名 | 例 |
|------|------|--------|-----|
| **国税** | 0001 | 法人税申告書 | `0001_法人税及び地方法人税申告書_2508.pdf` |
| | 0002 | 添付資料（法人税） | `0002_添付資料_法人税_2508.pdf` |
| | 0003 | 受信通知（法人税） | `0003_受信通知_2508.pdf` |
| | 0004 | 納付情報（法人税） | `0004_納付情報_2508.pdf` |
| **都道府県税** | 1001 | 東京都申告書 | `1001_東京都_法人都道府県民税・事業税・特別法人事業税_2508.pdf` |
| | 1003 | 受信通知（連番対応） | `1003_受信通知_2508.pdf` |
| | 1013 | 受信通知（2番目） | `1013_受信通知_2508.pdf` |
| **市町村税** | 2001 | 蒲郡市申告書 | `2001_愛知県蒲郡市_法人市民税_2508.pdf` |
| | 2003 | 受信通知（連番対応） | `2003_受信通知_2508.pdf` |
| **消費税** | 3001 | 消費税申告書 | `3001_消費税及び地方消費税申告書_2508.pdf` |
| | 3002 | 添付資料（消費税） | `3002_添付資料_消費税_2508.pdf` |
| **会計書類** | 5002 | 総勘定元帳 | `5002_総勘定元帳_2508.pdf` |
| | 5003 | 補助元帳 | `5003_補助元帳_2508.pdf` |

## ✨ 主な機能

- **自動分類**: OCRでPDF内容を読み取り、86種類の書類を自動分類
- **連番対応**: 地方税受信通知の連番システム（1003→1013→1023）
- **動的命名**: 自治体名を自動検出して適切なファイル名を生成
- **優先度システム**: 重要書類は最優先度200で確実に分類
- **GUI操作**: ドラッグ&ドロップで簡単操作
- **バッチ処理**: 複数ファイルの一括処理対応

## 🔧 最新の修正内容（v5.1）

### 修正されたバグ
1. **地方税受信通知の連番処理修正**
   - 都道府県: `1003_受信通知` → `1013_受信通知` → `1023_受信通知`
   - 市町村: `2003_受信通知` → `2013_受信通知` → `2023_受信通知`

2. **添付資料の誤分類防止**
   - `0002_添付資料`が他の書類に誤分類される問題を修正

3. **市民税申告書の分類強化**
   - `2001番台`の市民税申告書の識別精度を向上

### テスト結果
- **成功率**: 100% (5/5項目すべて成功)
- **分類精度**: 信頼度1.00で全項目正常分類
- **実行時間**: 平均0.2秒/ファイル

## 📁 プロジェクト構造

```
tax-doc-renamer/
├── main.py                    # メインプログラム
├── build.py                   # ビルドスクリプト
├── TaxDocumentRenamer.exe     # 実行ファイル（v5.1 最新版）
├── core/                      # コアモジュール
│   ├── classification_v5.py   # 分類エンジン（v5.1バグ修正版）
│   ├── ocr_engine.py          # OCR処理
│   └── pdf_processor.py       # PDF処理
├── ui/                        # ユーザーインターフェース
│   └── drag_drop.py           # ドラッグ&ドロップUI
├── tests/                     # テストファイル
├── resources/                 # リソースファイル
├── requirements.txt           # Python依存関係
└── old/                       # 旧バージョン（アーカイブ）
    ├── v4.0/                  # 開発版バージョン4.0
    ├── v5.0/                  # 初期バージョン5.0
    └── old_v4_files/          # その他古いファイル
```

## 🛠️ 開発者向け

### ビルド方法
```bash
python build.py
```

### テスト実行
```bash
python -c "import sys; sys.path.append('C:/Users/pukur/tax-doc-renamer/v4.0'); exec(open('C:/Users/pukur/Desktop/test_bug_fixes_v5.1.py').read())"
```

### 新機能の追加
1. `core/classification_v5.py` に新しい分類ルールを追加
2. テストケースを作成
3. プルリクエストを送信

## 📊 システム要件

- **OS**: Windows 10/11 (64bit)
- **Python**: 3.13+ (開発時)
- **メモリ**: 4GB以上推奨
- **ストレージ**: 100MB以上の空き容量

## 🔗 関連リンク

- [最新実行ファイル](TaxDocumentRenamer.exe) - v5.1バグ修正版
- [バグ修正テストレポート](https://github.com/Ezark213/tax-doc-renamer/blob/main/old/test_bug_fixes_v5.1.py)
- [システム仕様書](SYSTEM_REQUIREMENTS.md)
- [分類ルール詳細](NUMBERING_SYSTEM_GUIDE.md)

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下でライセンスされています。

## 📞 サポート

問題が発生した場合は、[Issues](https://github.com/Ezark213/tax-doc-renamer/issues)で報告してください。

## 🏗️ 最新アップデート

### v5.1リリース（2025年8月31日）
- 地方税受信通知連番システム完全修正
- バグ修正テスト100%成功確認
- 実行ファイル安定版リリース

---

**税務書類リネームシステム v5.1** - 日本の税務業務を効率化する自動分類システム

🤖 Generated with [Claude Code](https://claude.ai/code)