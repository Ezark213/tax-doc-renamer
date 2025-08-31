# サードパーティライセンス

このディレクトリには、税務書類リネームシステムで使用するサードパーティソフトウェアのライセンス情報を含みます。

## Tesseract OCR

- **ライセンス:** Apache License 2.0
- **ファイル:** `TESSERACT_LICENSE`
- **出典:** https://github.com/tesseract-ocr/tesseract
- **著作権:** Copyright 2006 Google Inc., Copyright 2007-2021 The Tesseract contributors

### 使用コンポーネント

1. **tesseract.exe** - Tesseract OCRエンジンの実行ファイル（Windows版）
2. **jpn.traineddata** - 日本語OCR用学習済みデータ
3. **eng.traineddata** - 英語OCR用学習済みデータ

### 配布ポリシー

このシステムにはTesseract OCRが同梱されており、外部インストールは不要です。
Apache License 2.0に基づき、ソースコードの改変なしで配布しています。

### 参考リンク

- Tesseract公式: https://tesseract-ocr.github.io/
- GitHub: https://github.com/tesseract-ocr/tesseract
- Windows版バイナリ: https://github.com/UB-Mannheim/tesseract/wiki
- 学習済みデータ: https://github.com/tesseract-ocr/tessdata_best