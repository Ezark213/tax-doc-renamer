@echo off
title Document Processing Utility v2.5

:: Defenderの一時的な無効化（管理者権限が必要）
echo Starting Document Processing Utility...

:: 実行ファイルの検査除外を追加（オプション）
powershell -Command "try { Add-MpPreference -ExclusionPath '%~dp0TaxDocRenamer_v2.5_ProperLogic.exe' -ErrorAction SilentlyContinue } catch {}"

:: アプリケーション実行
echo Running TaxDocRenamer_v2.5_ProperLogic.exe...
"TaxDocRenamer_v2.5_ProperLogic.exe"

pause
