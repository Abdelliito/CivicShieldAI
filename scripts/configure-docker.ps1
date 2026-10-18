param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$civicDockerEnv = Join-Path $projectRoot '.env.docker'

function New-CivicRandomHex([int]$Length) {
  $civicBytes = New-Object byte[] $Length
  $civicGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $civicGenerator.GetBytes($civicBytes) } finally { $civicGenerator.Dispose() }
  return ([BitConverter]::ToString($civicBytes)).Replace('-', '').ToLowerInvariant()
}

if (Test-Path -LiteralPath $civicDockerEnv) {
  Write-Host 'Existing .env.docker preserved. Edit it explicitly to change demonstration mode or credentials.'
} else {
  $civicDemoValue = if ($Demo) { 'true' } else { 'false' }
  $civicLines = @(
    ('POSTGRES_PASSWORD=' + (New-CivicRandomHex 32)),
    ('JWT_SECRET=' + (New-CivicRandomHex 48)),
    ('DEMO_MODE=' + $civicDemoValue),
    'CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080',
    'CIVIC_API_PORT=8001',
    'OPENAI_API_KEY=',
    'OPENAI_MODEL=gpt-4.1-mini',
    'VISION_PROVIDER=openai',
    'VISION_MODEL=',
    'VISION_API_KEY=',
    'VISION_ENDPOINT=',
    'VISION_FALLBACK_PROVIDER=',
    'VISION_FALLBACK_MODEL=',
    'VISION_FALLBACK_API_KEY=',
    'VISION_FALLBACK_ENDPOINT=',
    'OLLAMA_ENDPOINT=http://host.docker.internal:11434/api/generate',
    'OLLAMA_MODEL='
  )
  [System.IO.File]::WriteAllLines($civicDockerEnv, $civicLines, (New-Object System.Text.UTF8Encoding $false))
  Write-Host 'Created .env.docker with separate, random Docker credentials.'
}
Write-Host 'Run from the project folder: docker compose --env-file .env.docker up --build -d'
Write-Host 'Docker app: http://localhost:8080 | Docker API docs: http://localhost:8001/docs'
