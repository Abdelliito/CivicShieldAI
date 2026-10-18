$projectRoot = Split-Path -Parent $PSScriptRoot
foreach ($serviceName in @('frontend','backend')) {
  $pidFile = Join-Path $projectRoot ".runtime\$serviceName.pid"
  if (Test-Path -LiteralPath $pidFile) {
    $serviceProcessId = [int](Get-Content -LiteralPath $pidFile)
    $ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $serviceProcessId" -ErrorAction SilentlyContinue
    if ($ownedProcess -and ($ownedProcess.CommandLine -like '*uvicorn app.main:app*' -or $ownedProcess.CommandLine -like '*CivicShieldAI*frontend*node_modules*vite*')) { Stop-Process -Id $serviceProcessId -ErrorAction SilentlyContinue }
  }
}
$pgCtl = Join-Path $projectRoot '.runtime\package\native\bin\pg_ctl.exe'
if (Test-Path -LiteralPath $pgCtl) { & $pgCtl -D (Join-Path $projectRoot '.runtime\pgdata') -m fast -w stop }
