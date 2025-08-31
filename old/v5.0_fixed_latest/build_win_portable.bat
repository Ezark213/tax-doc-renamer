@echo off
REM 税務書類リネームシステム v5.0 Portable版ビルドスクリプト (Windows)
REM Tesseract同梱版

echo ========================================
echo 税務書類リネームシステム v5.0 Portable版ビルド
echo ========================================

cd /d "%~dp0"

REM 必要ファイルの存在確認
echo [1/5] 必要ファイルの確認...
if not exist "main_v5.py" (
    echo エラー: main_v5.py が見つかりません
    pause
    exit /b 1
)

if not exist "resources\tesseract\bin\tesseract.exe" (
    echo 警告: tesseract.exe が見つかりません
    echo resources\tesseract\bin\tesseract.exe を配置してください
    echo 詳細は resources\tesseract\README.md を参照
    pause
    exit /b 1
)

if not exist "resources\tesseract\tessdata\jpn.traineddata" (
    echo 警告: jpn.traineddata が見つかりません  
    echo resources\tesseract\tessdata\jpn.traineddata を配置してください
    pause
    exit /b 1
)

if not exist "resources\tesseract\tessdata\eng.traineddata" (
    echo 警告: eng.traineddata が見つかりません
    echo resources\tesseract\tessdata\eng.traineddata を配置してください  
    pause
    exit /b 1
)

echo [2/5] 古いビルドファイルのクリーンアップ...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "TaxDocRenamer_v5.0_Portable" rmdir /s /q "TaxDocRenamer_v5.0_Portable"

echo [3/5] PyInstaller OneFileビルド実行...
pyinstaller --clean --noconfirm ^
  --onefile ^
  --name TaxDocRenamer_v5.0 ^
  --add-data "resources\tesseract\bin\tesseract.exe;resources\tesseract\bin" ^
  --add-data "resources\tesseract\tessdata\jpn.traineddata;resources\tesseract\tessdata" ^
  --add-data "resources\tesseract\tessdata\eng.traineddata;resources\tesseract\tessdata" ^
  --add-data "resources\tesseract\README.md;resources\tesseract" ^
  --add-data "licenses\TESSERACT_LICENSE;licenses" ^
  --add-data "licenses\README.md;licenses" ^
  --add-data "README_v5.md;." ^
  --add-data "V5_運用ガイド.md;." ^
  --hidden-import pytesseract ^
  --hidden-import PyPDF2 ^
  --hidden-import fitz ^
  --hidden-import PIL ^
  --hidden-import pandas ^
  --exclude-module matplotlib ^
  --exclude-module scipy ^
  --exclude-module sklearn ^
  --windowed ^
  main_v5.py

if errorlevel 1 (
    echo エラー: PyInstallerビルドに失敗しました
    pause
    exit /b 1
)

echo [4/5] Portable版パッケージ作成...
if not exist "TaxDocRenamer_v5.0_Portable" mkdir "TaxDocRenamer_v5.0_Portable"

REM 実行ファイルの移動
if exist "dist\TaxDocRenamer_v5.0.exe" (
    move "dist\TaxDocRenamer_v5.0.exe" "TaxDocRenamer_v5.0_Portable\"
) else (
    echo エラー: ビルドされた実行ファイルが見つかりません
    pause
    exit /b 1
)

REM ドキュメントファイルの追加
copy "README_v5.md" "TaxDocRenamer_v5.0_Portable\README.md"
copy "V5_運用ガイド.md" "TaxDocRenamer_v5.0_Portable\"

REM Portable版専用README作成
(
echo # 税務書類リネームシステム v5.0 Portable版
echo.
echo このフォルダにはTesseract同梱のPortable版が含まれています。
echo.
echo ## 使用方法
echo 1. TaxDocRenamer_v5.0.exe をダブルクリック
echo 2. PDFファイルをドラッグ&ドロップまたはファイル選択
echo 3. 自治体情報・年月を入力
echo 4. 分割・分類・リネーム実行
echo.
echo ## 特徴
echo - Tesseract OCR同梱（外部インストール不要^)
echo - 単一実行ファイル
echo - レジストリ不使用
echo.
echo ## システム要件
echo - Windows 10/11
echo - Python環境不要
echo.
echo ## サポート
echo 詳細なドキュメントは README.md および V5_運用ガイド.md を参照
) > "TaxDocRenamer_v5.0_Portable\README_PORTABLE.txt"

echo [5/5] クリーンアップ...
if exist "build" rmdir /s /q "build"

echo.
echo ========================================
echo ✅ Portable版ビルド完了!
echo ========================================
echo.
echo 出力フォルダ: TaxDocRenamer_v5.0_Portable\
echo 実行ファイル: TaxDocRenamer_v5.0.exe
echo.
echo テスト実行: TaxDocRenamer_v5.0_Portable\TaxDocRenamer_v5.0.exe
echo.
pause