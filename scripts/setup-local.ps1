$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -r backend/requirements-lock.txt
& '.\.venv\Scripts\python.exe' scripts/bootstrap_local.py
Push-Location frontend
npm ci
Pop-Location
npm ci
Write-Host 'Setup complete. Run .\scripts\start.ps1'
