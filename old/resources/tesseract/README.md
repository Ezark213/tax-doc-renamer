# Tesseract OCR 同梱リソース

このディレクトリには、税務書類リネームシステムで使用するTesseract OCRの実行ファイルと言語データを配置します。

## 必要なファイル

### bin/tesseract.exe
Windows用のTesseract実行ファイルです。

**取得先:** 
- 公式リリース: https://github.com/UB-Mannheim/tesseract/wiki
- または: https://tesseract-ocr.github.io/tessdoc/Downloads.html

**配置場所:** `bin/tesseract.exe`

### tessdata/jpn.traineddata
日本語認識用の学習済みデータです。

**取得先:** 
- GitHub tessdata_best: https://github.com/tesseract-ocr/tessdata_best/raw/main/jpn.traineddata

**配置場所:** `tessdata/jpn.traineddata`

### tessdata/eng.traineddata
英語認識用の学習済みデータです。

**取得先:** 
- GitHub tessdata_best: https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata

**配置場所:** `tessdata/eng.traineddata`

## 設定手順

1. 上記ファイルを指定の場所にダウンロード・配置
2. `licenses/` ディレクトリにTesseractのApache-2.0ライセンスを配置
3. PyInstallerビルド時に自動で同梱される

## ライセンス

Tesseract OCRはApache License 2.0の下で配布されています。
詳細は `../licenses/TESSERACT_LICENSE` を参照してください。

## ファイルサイズ最適化

このシステムでは以下のファイルのみ使用します：
- jpn.traineddata (約32MB)
- eng.traineddata (約4MB) 

その他の言語データは不要です。