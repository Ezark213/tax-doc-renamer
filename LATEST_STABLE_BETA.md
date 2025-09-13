# 最新安定版ベータ - v5.4.4-beta

**現在の最新版**: `v5.4.4-beta` (2025-01-14)

## 🔧 修正済みの重要な問題

### ✅ PyMuPDF互換性の修正
- すべてのファイルでPyMuPDFインポート文を修正
- `import fitz` → `import pymupdf as fitz`
- PDF処理エラーが完全に解決

### ✅ 受信通知分類の修正  
- **問題**: 1003系・2003系の受信通知が未分類フォルダに移動
- **原因**: `_generate_receipt_number`メソッドが存在しない
- **解決**: メソッドを追加し、動的番号生成システムを実装
  - 都道府県: 1003 → 1013 → 1023 → ...
  - 市町村: 2003 → 2013 → 2023 → ...

## 📋 動作確認済み機能

- ✅ アプリケーション起動
- ✅ PDF処理とOCR
- ✅ 文書分類システム
- ✅ バンドルPDF分割
- ✅ 受信通知の正確な分類と番号付け

## 🚀 使用方法

```bash
git checkout v5.4.4-beta
.venv\Scripts\activate
python main.py
```

## 📝 技術的詳細

### 修正されたファイル
- `core/classification_v5.py` - 受信通知分類メソッド追加
- `main.py` - PyMuPDF互換性修正
- `core/ocr_engine.py` - PyMuPDF互換性修正
- `core/pdf_processor.py` - PyMuPDF互換性修正
- `core/pre_extract.py` - PyMuPDF互換性修正

### 新規追加メソッド
```python
def _generate_receipt_number(self, jurisdiction_type: str, set_number: int) -> str:
    """受信通知の連番を生成"""
    # 都道府県: 1003 + (セット番号-1) * 10
    # 市町村: 2003 + (セット番号-1) * 10
```

---
**注意**: これは最新の安定したベータ版です。すべての既知の問題が修正されています。