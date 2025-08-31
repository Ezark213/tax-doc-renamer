@echo off
chcp 65001 > nul
cls
echo ===============================================
echo 税務書類リネームシステム v5.0 インストーラー
echo ===============================================
echo.
echo インストールを開始します...
echo.

REM 管理者権限チェック
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 管理者権限が必要です。
    echo 右クリックから「管理者として実行」してください。
    pause
    exit /b 1
)

REM インストール先ディレクトリ作成
set INSTALL_DIR=C:\Program Files\TaxDocRenamer_v5.0
echo インストール先: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM ファイルコピー
echo ファイルをコピー中...
copy /Y "TaxDocRenamer_v5.0.exe" "%INSTALL_DIR%\" >nul
copy /Y "*.md" "%INSTALL_DIR%\" >nul 2>nul

REM デスクトップショートカット作成
echo デスクトップショートカット作成中...
set SHORTCUT_PATH=%USERPROFILE%\Desktop\税務書類リネームシステム v5.0.lnk
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%INSTALL_DIR%\TaxDocRenamer_v5.0.exe'; $Shortcut.Save()"

REM スタートメニューショートカット作成
echo スタートメニューショートカット作成中...
set START_MENU_DIR=%ProgramData%\Microsoft\Windows\Start Menu\Programs\税務書類リネームシステム
if not exist "%START_MENU_DIR%" mkdir "%START_MENU_DIR%"
set START_SHORTCUT_PATH=%START_MENU_DIR%\税務書類リネームシステム v5.0.lnk
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_SHORTCUT_PATH%'); $Shortcut.TargetPath = '%INSTALL_DIR%\TaxDocRenamer_v5.0.exe'; $Shortcut.Save()"

REM レジストリ登録（アンインストール情報）
echo システム登録中...
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TaxDocRenamer_v5.0" /v "DisplayName" /t REG_SZ /d "税務書類リネームシステム v5.0" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TaxDocRenamer_v5.0" /v "DisplayVersion" /t REG_SZ /d "5.0.0" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TaxDocRenamer_v5.0" /v "Publisher" /t REG_SZ /d "税務書類リネームシステム開発チーム" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TaxDocRenamer_v5.0" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TaxDocRenamer_v5.0" /v "UninstallString" /t REG_SZ /d "\""%INSTALL_DIR%\uninstall.bat\"" /f >nul

REM アンインストーラー作成
echo アンインストーラー作成中...
(
echo @echo off
echo chcp 65001 ^> nul
echo cls
echo アンインストールを実行しています...
echo.
echo ファイルを削除中...
echo del /Q "%%USERPROFILE%%\Desktop\税務書類リネームシステム v5.0.lnk" ^> nul 2^>nul
echo rmdir /S /Q "%%ProgramData%%\Microsoft\Windows\Start Menu\Programs\税務書類リネームシステム" ^> nul 2^>nul
echo reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TaxDocRenamer_v5.0" /f ^> nul 2^>nul
echo cd /D C:\
echo rmdir /S /Q "%INSTALL_DIR%" ^> nul 2^>nul
echo.
echo アンインストール完了
echo pause
) > "%INSTALL_DIR%\uninstall.bat"

echo.
echo ===============================================
echo インストール完了！
echo ===============================================
echo.
echo デスクトップのショートカットから起動できます
echo またはスタートメニューから起動してください
echo.
echo アンインストールは以下から実行できます:
echo - コントロールパネル ^> プログラムの追加と削除
echo - または %INSTALL_DIR%\uninstall.bat
echo.
pause
