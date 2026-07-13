# Ferrari IoT Postdoc Lab — start Windows
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$Root\python_server"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host "Ferrari Lab: http://127.0.0.1:8001"
& .\.venv\Scripts\python.exe app.py
