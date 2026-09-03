# 在 PowerShell 中直接执行：.\run_app.ps1
Set-Location $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" -m streamlit run "$PSScriptRoot\app.py" --server.headless true
