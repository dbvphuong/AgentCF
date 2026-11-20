$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
Push-Location $workspace
try {
    & (Join-Path $workspace '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'build_client.py')
    if ($LASTEXITCODE -ne 0) { throw 'Build CF Client failed' }
} finally { Pop-Location }
