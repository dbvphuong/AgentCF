param(
    [string] $TemporalBinary = "temporal",
    [string] $DatabasePath = "",
    [ValidateRange(1024, 65535)] [int] $Port = 7233,
    [ValidateRange(1024, 65535)] [int] $UiPort = 8233
)

$ErrorActionPreference = "Stop"
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../.."))
if ([string]::IsNullOrWhiteSpace($DatabasePath)) {
    $DatabasePath = Join-Path $repositoryRoot "runtime/temporal/temporal.sqlite"
}
$resolvedDatabasePath = [System.IO.Path]::GetFullPath($DatabasePath)
$businessDatabasePath = $env:AGENT_CF_SERVER_DATABASE_PATH
if ([string]::IsNullOrWhiteSpace($businessDatabasePath)) {
    $businessDatabasePath = Join-Path (Get-Location).Path "runtime/server/agent_cf.sqlite3"
}
$resolvedBusinessPath = [System.IO.Path]::GetFullPath($businessDatabasePath)
if ([string]::Equals($resolvedDatabasePath, $resolvedBusinessPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Temporal and Agent CF business data must use different database files."
}
$dataDirectory = [System.IO.Path]::GetDirectoryName($resolvedDatabasePath)
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null

# The CLI owns this database. It must never be the Agent CF business database.
Write-Host "Temporal local development database: $resolvedDatabasePath"
& $TemporalBinary server start-dev --ip 127.0.0.1 --port $Port --ui-port $UiPort --db-filename $resolvedDatabasePath
if ($LASTEXITCODE -ne 0) {
    throw "Temporal development server exited with code $LASTEXITCODE"
}
