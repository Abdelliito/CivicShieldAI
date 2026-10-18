$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$logRoot = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$pgCtl = Join-Path $logRoot 'package\native\bin\pg_ctl.exe'
if (Test-Path -LiteralPath $pgCtl) {
  & $pgCtl -D (Join-Path $logRoot 'pgdata') status | Out-Null
  if ($LASTEXITCODE -ne 0) { & $pgCtl -D (Join-Path $logRoot 'pgdata') -l (Join-Path $logRoot 'postgres.log') -o '-p 54329 -h 127.0.0.1' -w start }
}
try { Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 | Out-Null } catch {
  $pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
  $apiProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'backend.log') -RedirectStandardError (Join-Path $logRoot 'backend-error.log')
  $apiProcess.Id | Set-Content (Join-Path $logRoot 'backend.pid')
}
try { Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2 | Out-Null } catch {
  $nodeExe = (Get-Command node).Source
  $viteScript = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
  $uiProcess = Start-Process -FilePath $nodeExe -ArgumentList @(('"' + $viteScript + '"'),'--host','127.0.0.1','--port','5173','--strictPort') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'frontend.log') -RedirectStandardError (Join-Path $logRoot 'frontend-error.log')
  $uiProcess.Id | Set-Content (Join-Path $logRoot 'frontend.pid')
}
Write-Host 'Frontend http://127.0.0.1:5173 | API docs http://127.0.0.1:8000/docs'
