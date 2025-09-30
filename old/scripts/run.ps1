Set-Location "$PSScriptRoot\.."

Write-Output "=== Run tests ==="
python -m pytest tests/test_yymm_policy.py -v

Write-Output "=== Run main ==="
python src\main.py