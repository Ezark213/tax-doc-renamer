@echo off
chcp 65001 > nul
echo =======================================
echo v5.0システム テスト実行
echo =======================================
echo.
echo テストを実行しています...
python test_v5.py
echo.
echo 統合テストを実行しています...
python tools/final_integration_test.py
pause
