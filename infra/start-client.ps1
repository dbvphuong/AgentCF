param([string]$ConnectionUri)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$installed = Join-Path $env:LOCALAPPDATA 'AgentCF\Client\CF Client.exe'
if (Test-Path -LiteralPath $installed) {
    $executable = $installed
    $arguments = @('--desktop')
} else {
    $executable = Join-Path $workspace '.venv\Scripts\pythonw.exe'
    $entry = Join-Path $workspace 'apps\client\src\agent_cf_client\desktop\entry.py'
    if (-not (Test-Path -LiteralPath $executable)) { throw 'CF Client chua cai. Tai CF Client Setup.exe tu Connect PC tren Web.' }
    $arguments = @(('"' + $entry + '"'), '--desktop')
}
if ($ConnectionUri) {
    if ($ConnectionUri.Contains('"') -or $ConnectionUri.Contains("`r") -or $ConnectionUri.Contains("`n")) { throw 'Lien ket khong hop le' }
    $arguments += @('--connect', ('"' + $ConnectionUri + '"'))
}
Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $workspace -WindowStyle Hidden | Out-Null
