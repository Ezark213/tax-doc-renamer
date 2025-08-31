# 税務書類リネームシステム v5.0 PowerShell起動スクリプト
Write-Host "税務書類リネームシステム v5.0 起動中..." -ForegroundColor Green

# スクリプトのディレクトリに移動
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptPath

try {
    # Pythonでメインスクリプトを実行
    python main_v5.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "エラーが発生しました。" -ForegroundColor Red
        Write-Host "Pythonがインストールされているか確認してください。" -ForegroundColor Yellow
        Read-Host "続行するにはEnterキーを押してください"
    }
}
catch {
    Write-Host "予期しないエラーが発生しました: $_" -ForegroundColor Red
    Read-Host "続行するにはEnterキーを押してください"
}