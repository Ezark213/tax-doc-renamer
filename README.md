# 税務書類リネームシステム

自動でPDF書類を分類・リネームするシステムです。

## 🚀 現在の最新版: v4.0

**v4.0フォルダ**を使用してください。すべての最新機能が含まれています。

### 📁 ディレクトリ構成
```
tax-doc-renamer/
├── README.md           # このファイル
├── requirements.txt    # Python依存関係
├── v4.0/              # ★ 最新版（使用推奨）
│   ├── README_SETUP.md # セットアップガイド
│   ├── main.py        # メインアプリ
│   ├── core/          # コアモジュール
│   ├── ui/            # UIコンポーネント
│   ├── tests/         # テストスイート
│   └── dist/          # ビルド済み実行ファイル
└── old/               # 古いバージョン（参考用）
```

## ✨ v4.0 新機能
- **添付書類分類修正**: 添付書類送付書/添付書類名称の優先分類
- **東京都エラー処理**: セット2-5自動セット1変換
- **認識強化**: 都道府県・市町村書類の認識精度向上
- **セット優先順序**: 自動で最適なセット番号を選択
- **包括的テスト**: 100%パス率のテストスイート

## 🛠️ クイックスタート

### 1. Python環境で実行
```bash
cd v4.0
python main.py
```

### 2. 実行ファイルを使用
```bash
cd v4.0/dist
./TaxDocumentRenamer_v4.0_NewFeaturesComplete.exe
```

## 📖 詳細セットアップ
詳しいセットアップ手順は `v4.0/README_SETUP.md` をご覧ください。

## 🔧 システム要件
- Python 3.8以上
- Tesseract OCR
- Windows 10/11

## 📞 サポート
- GitHub Issues: [税務書類リネームシステム Issues](https://github.com/Ezark213/tax-doc-renamer/issues)
- 最新版確認: `git pull origin main`

---
**注意**: 古いバージョン（v1.0-v3.0、v4.1-v4.5等）は `old/` フォルダに移動済みです。  
現在は **v4.0のみ** をご使用ください。

🤖 Generated with Claude Code