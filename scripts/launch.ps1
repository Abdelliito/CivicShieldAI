$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'start.ps1')
$deadline = [DateTime]::UtcNow.AddSeconds(25)
$ready = $false
while ([DateTime]::UtcNow -lt $deadline) {
  try {
    $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
    $page = Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2
    if ($health.service -eq 'CivicShield AI' -and $page.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep -Milliseconds 300 }
}
if (-not $ready) { throw 'CivicShield services did not become ready. Check the .runtime log files.' }
Start-Process 'http://127.0.0.1:5173'
