@echo off
REM 税務書類リネームシステム v5.0 インストーラー版ビルドスクリプト (Windows)
REM Tesseract同梱版

echo ========================================
echo 税務書類リネームシステム v5.0 インストーラー版ビルド
echo ========================================

cd /d "%~dp0"

REM 必要ファイルの存在確認
echo [1/6] 必要ファイルの確認...
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

echo [2/6] 古いビルドファイルのクリーンアップ...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "TaxDocRenamer_v5.0_Installer" rmdir /s /q "TaxDocRenamer_v5.0_Installer"

echo [3/6] PyInstaller OneDirビルド実行...
pyinstaller --clean --noconfirm ^
  --onedir ^
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

echo [4/6] インストーラー版パッケージ作成...
if not exist "TaxDocRenamer_v5.0_Installer" mkdir "TaxDocRenamer_v5.0_Installer"

REM アプリケーションファイルの移動
if exist "dist\TaxDocRenamer_v5.0" (
    xcopy /e/y "dist\TaxDocRenamer_v5.0" "TaxDocRenamer_v5.0_Installer\app\"
) else (
    echo エラー: ビルドされたアプリフォルダが見つかりません
    pause
    exit /b 1
)

echo [5/6] インストーラー関連ファイル作成...

REM インストールスクリプト
(
echo @echo off
echo REM 税務書類リネームシステム v5.0 インストーラー
echo.
echo echo ========================================
echo echo 税務書類リネームシステム v5.0 インストーラー
echo echo ========================================
echo.
echo set INSTALL_DIR=%%PROGRAMFILES%%\TaxDocRenamer_v5.0
echo set DESKTOP_SHORTCUT=%%USERPROFILE%%\Desktop\税務書類リネームシステム v5.0.lnk
echo set STARTMENU_DIR=%%APPDATA%%\Microsoft\Windows\Start Menu\Programs
echo.
echo echo インストール先: %%INSTALL_DIR%%
echo echo.
echo REM 管理者権限チェック
echo net session ^>nul 2^>^&1
echo if errorlevel 1 (
echo     echo エラー: 管理者権限で実行してください
echo     echo 右クリック -^> [管理者として実行]
echo     pause
echo     exit /b 1
echo ^)
echo.
echo REM インストールディレクトリ作成
echo if not exist "%%INSTALL_DIR%%" mkdir "%%INSTALL_DIR%%"
echo.
echo REM ファイルのコピー
echo echo ファイルをコピー中...
echo xcopy /e/y "app\*" "%%INSTALL_DIR%%\"
echo.
echo REM デスクトップショートカット作成
echo echo ショートカットを作成中...
echo powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%%DESKTOP_SHORTCUT%%'^); $Shortcut.TargetPath = '%%INSTALL_DIR%%\TaxDocRenamer_v5.0.exe'; $Shortcut.Save(^)"
echo.
echo REM スタートメニューショートカット作成
echo if not exist "%%STARTMENU_DIR%%\税務書類リネームシステム" mkdir "%%STARTMENU_DIR%%\税務書類リネームシステム"
echo powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%%STARTMENU_DIR%%\税務書類リネームシステム\税務書類リネームシステム v5.0.lnk'^); $Shortcut.TargetPath = '%%INSTALL_DIR%%\TaxDocRenamer_v5.0.exe'; $Shortcut.Save(^)"
echo.
echo echo ========================================
echo echo ✅ インストール完了!
echo echo ========================================
echo echo.
echo echo デスクトップショートカット: 税務書類リネームシステム v5.0
echo echo インストール場所: %%INSTALL_DIR%%
echo echo.
echo pause
) > "TaxDocRenamer_v5.0_Installer\install.bat"

REM アンインストールスクリプト
(
echo @echo off
echo REM 税務書類リネームシステム v5.0 アンインストーラー
echo.
echo echo ========================================
echo echo 税務書類リネームシステム v5.0 アンインストール
echo echo ========================================
echo.
echo set INSTALL_DIR=%%PROGRAMFILES%%\TaxDocRenamer_v5.0
echo set DESKTOP_SHORTCUT=%%USERPROFILE%%\Desktop\税務書類リネームシステム v5.0.lnk
echo set STARTMENU_DIR=%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\税務書類リネームシステム
echo.
echo REM 管理者権限チェック
echo net session ^>nul 2^>^&1
echo if errorlevel 1 (
echo     echo エラー: 管理者権限で実行してください
echo     echo 右クリック -^> [管理者として実行]
echo     pause
echo     exit /b 1
echo ^)
echo.
echo REM ファイル削除
echo echo ファイルを削除中...
echo if exist "%%INSTALL_DIR%%" rmdir /s /q "%%INSTALL_DIR%%"
echo.
echo REM ショートカット削除
echo echo ショートカットを削除中...
echo if exist "%%DESKTOP_SHORTCUT%%" del "%%DESKTOP_SHORTCUT%%"
echo if exist "%%STARTMENU_DIR%%" rmdir /s /q "%%STARTMENU_DIR%%"
echo.
echo echo ========================================
echo echo ✅ アンインストール完了!
echo echo ========================================
echo pause
) > "TaxDocRenamer_v5.0_Installer\uninstall.bat"

REM インストール手順
(
echo # 税務書類リネームシステム v5.0 インストール手順
echo.
echo このフォルダにはTesseract同梱のインストーラー版が含まれています。
echo.
echo ## インストール方法
echo 1. `install.bat` を右クリック
echo 2. [管理者として実行] を選択
echo 3. 画面の指示に従ってインストール
echo.
echo ## インストール後
echo - デスクトップに「税務書類リネームシステム v5.0」のショートカットが作成されます
echo - スタートメニューからも起動可能です
echo.
echo ## アンインストール方法
echo 1. `uninstall.bat` を右クリック
echo 2. [管理者として実行] を選択
echo.
echo ## インストール場所
echo `C:\Program Files\TaxDocRenamer_v5.0\`
echo.
echo ## 特徴
echo - Tesseract OCR同梱（外部インストール不要^)
echo - システムインストール
echo - デスクトップ・スタートメニューショートカット自動作成
echo.
echo ## システム要件
echo - Windows 10/11
echo - 管理者権限（インストール時のみ^)
echo - Python環境不要
) > "TaxDocRenamer_v5.0_Installer\インストール手順.txt"

REM README
copy "README_v5.md" "TaxDocRenamer_v5.0_Installer\README.md"
copy "V5_運用ガイド.md" "TaxDocRenamer_v5.0_Installer\"

echo [6/6] クリーンアップ...
if exist "build" rmdir /s /q "build"

echo.
echo ========================================
echo ✅ インストーラー版ビルド完了!
echo ========================================
echo.
echo 出力フォルダ: TaxDocRenamer_v5.0_Installer\
echo インストーラー: install.bat
echo アンインストーラー: uninstall.bat
echo.
echo 注意: インストールには管理者権限が必要です
echo.
echo より高度なインストーラーが必要な場合は、以下を検討してください:
echo - Inno Setup: https://jrsoftware.org/isinfo.php
echo - NSIS: https://nsis.sourceforge.io/
echo.
pause