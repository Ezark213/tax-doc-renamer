# 税務書類リネームシステム v4.0 セットアップガイド

## 🚀 別PCでの使用方法

### 1. リポジトリのクローン
```bash
git clone https://github.com/Ezark213/tax-doc-renamer.git
cd tax-doc-renamer/v4.0
```

### 2. Python環境のセットアップ
```bash
# Python 3.8以上が必要
pip install -r ../requirements.txt
```

### 3. Tesseractのインストール
- Windows: https://github.com/UB-Mannheim/tesseract/wiki からダウンロード・インストール
- パスに追加されていることを確認

### 4. 実行方法

#### A. Pythonスクリプトとして実行
```bash
python main.py
```

#### B. ビルド済み実行ファイルを使用
```bash
# distディレクトリの実行ファイルを使用
./dist/TaxDocumentRenamer_v4.0_NewFeaturesComplete.exe
```

#### C. 自分でビルドする場合
```bash
pyinstaller TaxDocumentRenamer_v4.0_BugFixed.spec
```

## ✨ 新機能（v4.0）

### 1. 添付書類分類の修正
- 「添付書類送付書」「添付書類名称」キーワードが含まれる書類は「0002_添付資料」として分類
- 「内国法人の確定申告(青色)」より優先して分類される

### 2. 東京都エラー処理
- 東京都の書類でセット2-5が指定された場合、自動的にセット1に変更
- 都税事務所、東京都キーワードで自動判定

### 3. 都道府県・市町村認識の強化
- **都道府県書類（10系統）**: 県税事務所、都税事務所、道府県民税、法人事業税、特別法人事業税等
- **市町村書類（20系統）**: 市役所、町役場、村役場、法人市民税、市町村民税等

### 4. セット優先順序機能
- セット1 → セット2 → セット3 → セット4 → セット5 の優先順序で自動選択
- 複数のセットが利用可能な場合、最も優先度の高いセットを自動選択

## 🧪 テスト実行
```bash
# 全機能テスト
python test_all_new_features.py

# シンプルテスト
python test_simple.py

# 分類修正テスト
python test_classification_fixes.py
```

## 📁 ディレクトリ構成
```
v4.0/
├── main.py                 # メインアプリケーション
├── core/
│   ├── classification.py   # 分類エンジン（新機能追加済み）
│   ├── ocr_engine.py      # OCR処理
│   └── pdf_processor.py   # PDF処理
├── ui/
│   └── drag_drop.py       # UI コンポーネント
├── tests/                 # テストスイート
├── config/               # 設定ファイル
├── dist/                 # ビルド済み実行ファイル
└── README_SETUP.md       # このファイル
```

## 🔧 トラブルシューティング

### Tesseractが見つからない場合
```python
# main.py または ocr_engine.py で直接パスを指定
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### 依存関係のエラー
```bash
pip install --upgrade pip
pip install -r ../requirements.txt --force-reinstall
```

### 文字化け問題
- システムの言語設定を日本語にする
- フォントの問題の場合は、システムフォントを確認

## 📞 サポート
- GitHub Issues: https://github.com/Ezark213/tax-doc-renamer/issues
- 最新版の確認: `git pull origin main`

---
🤖 Generated with Claude Code