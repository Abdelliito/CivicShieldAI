$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
  python -m venv .venv
  if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed. Install Python 3.10+ and enable Add Python to PATH.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r backend/requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed. Review the package error above.' }
& '.\.venv\Scripts\python.exe' scripts/bootstrap_local.py
if ($LASTEXITCODE -ne 0) { throw 'Local database setup failed. Review the error above.' }
Push-Location frontend
try {
  npm.cmd ci
  if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed. Review the npm error above.' }
} finally { Pop-Location }
npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'Browser test dependency installation failed. Review the npm error above.' }
Write-Host 'Setup complete. Run .\scripts\start.ps1'
