$projectRoot = Split-Path -Parent $PSScriptRoot
foreach ($serviceName in @('frontend','backend')) {
  $pidFile = Join-Path $projectRoot ".runtime\$serviceName.pid"
  if (Test-Path -LiteralPath $pidFile) {
    $serviceProcessId = [int](Get-Content -LiteralPath $pidFile)
    $ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $serviceProcessId" -ErrorAction SilentlyContinue
    $civicPythonPattern = '*' + $projectRoot + '\.venv\Scripts\python.exe*'
    $civicVitePattern = '*' + $projectRoot + '\frontend\node_modules\vite*'
    if ($ownedProcess -and (($ownedProcess.CommandLine -like $civicPythonPattern -and $ownedProcess.CommandLine -like '*uvicorn app.main:app*') -or $ownedProcess.CommandLine -like $civicVitePattern)) {
      # A Windows venv launcher creates a base-Python child. Stop the verified
      # application process tree so it cannot keep port 8000 after its parent exits.
      & taskkill.exe /PID $serviceProcessId /T /F | Out-Null
    }
  }
}
$pgCtl = Join-Path $projectRoot '.runtime\package\native\bin\pg_ctl.exe'
if (Test-Path -LiteralPath $pgCtl) { & $pgCtl -D (Join-Path $projectRoot '.runtime\pgdata') -m fast -w stop }
