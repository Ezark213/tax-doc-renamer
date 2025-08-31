@echo off
chcp 65001 > nul
echo ====================================
echo 税務書類リネームシステム v5.0 起動中
echo 5000-7000番台分類対応版
echo ====================================
cd /d "%~dp0"
python main_v5.py
if errorlevel 1 (
    echo.
    echo エラーが発生しました。
    echo Pythonがインストールされているか確認してください。
    echo.
    echo 代替起動方法：
    echo 1. OneDir版: dist\TaxDocRenamer_v5_OneDir\TaxDocRenamer_v5_System.exe
    echo 2. PowerShell版: launch_tax_renamer.ps1
    pause
)