param(
    [ValidateRange(1, 65535)][int]$ServerPort = 8000,
    [ValidateRange(1, 65535)][int]$WebPort = 5173,
    [string]$DatabasePath,
    [switch]$NoBrowser,
    [switch]$CheckOnly,
    [switch]$SmokeTest
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'apps\web\node_modules\vite\bin\vite.js'
$serverUrl = "http://127.0.0.1:$ServerPort"
$webUrl = "http://127.0.0.1:$WebPort"
$ownedProcesses = @()
$savedEnvironment = @{}
$exitCode = 0

function Test-FreePort([int]$Port) {
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
    try { $listener.Start(); return $true }
    catch [System.Net.Sockets.SocketException] { return $false }
    finally { $listener.Stop() }
}

function Test-AgentServer {
    try {
        $health = Invoke-RestMethod -Uri "$serverUrl/healthz" -TimeoutSec 2
        return ($health.status -eq 'ok' -and $health.database.schema_version -gt 0)
    } catch { return $false }
}

function Test-AgentWeb {
    try {
        $page = Invoke-WebRequest -Uri $webUrl -UseBasicParsing -TimeoutSec 2
        $proxy = Invoke-RestMethod -Uri "$webUrl/healthz" -TimeoutSec 2
        return ($page.Content -match '<title>Agent CF</title>' -and $proxy.status -eq 'ok')
    } catch { return $false }
}

function Wait-Service([System.Diagnostics.Process]$Process, [scriptblock]$Probe, [string]$Name) {
    $deadline = [DateTime]::UtcNow.AddSeconds(40)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($Process.HasExited) { throw "$Name exited during startup. Check the log directory printed above." }
        if (& $Probe) { return }
        Start-Sleep -Milliseconds 250
    }
    throw "$Name did not become ready within 40 seconds. Check its logs."
}

try {
    Set-Location -LiteralPath $projectRoot
    if ($ServerPort -eq $WebPort) { throw 'ServerPort and WebPort must be different.' }
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Missing .venv. Follow docs/development/setup.md to install Python dependencies first.'
    }
    $nodePath = (Get-Command node.exe -ErrorAction Stop).Source
    $nodeVersion = & $nodePath --version
    if ($nodeVersion -notmatch '^v24\.') { throw "Node.js 24 is required. Current version: $nodeVersion" }
    if (-not (Test-Path -LiteralPath $vitePath)) {
        throw 'Missing Web dependencies. Run: npm.cmd --prefix apps/web ci'
    }
    & $pythonPath -c 'import fastapi, uvicorn, temporalio'
    if ($LASTEXITCODE -ne 0) { throw 'Missing Python dependencies. Run: .venv\Scripts\python.exe -m pip install -r requirements.txt' }
    if ($CheckOnly) {
        Write-Host 'Agent CF: Python, Node.js and Web dependencies are ready.'
        return
    }

    $serverFree = Test-FreePort $ServerPort
    $webFree = Test-FreePort $WebPort
    if (-not $serverFree -or -not $webFree) {
        if (-not $serverFree -and -not $webFree -and (Test-AgentServer) -and (Test-AgentWeb)) {
            Write-Host "Agent CF is already running: $webUrl"
            if (-not $NoBrowser -and -not $SmokeTest) { Start-Process $webUrl }
            return
        }
        throw "Port $ServerPort or $WebPort is in use. Close the previous local launcher, or use -ServerPort / -WebPort. No existing process was stopped."
    }

    $logDir = Join-Path $projectRoot ('runtime\local\' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Write-Host "Logs: $logDir"
    $environmentValues = @{
        'PYTHONPATH' = (Join-Path $projectRoot 'apps\server\src')
        'PYTHONUNBUFFERED' = '1'
        'AGENT_CF_SERVER_HOST' = '127.0.0.1'
        'AGENT_CF_SERVER_PORT' = [string]$ServerPort
        'AGENT_CF_SERVER_TEMPORAL_ENABLED' = 'false'
        'AGENT_CF_WEB_SERVER_URL' = $serverUrl
    }
    if ($DatabasePath) {
        $environmentValues['AGENT_CF_SERVER_DATABASE_PATH'] = [System.IO.Path]::GetFullPath($DatabasePath)
        $environmentValues['AGENT_CF_SERVER_ARTIFACTS_DIR'] = Join-Path (Split-Path -Parent $environmentValues['AGENT_CF_SERVER_DATABASE_PATH']) 'artifacts'
    }
    foreach ($name in $environmentValues.Keys) {
        $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $environmentValues[$name], 'Process')
    }

    $serverProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'agent_cf_server.bootstrap.server') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'server.out.log') -RedirectStandardError (Join-Path $logDir 'server.err.log')
    $ownedProcesses += $serverProcess
    Wait-Service $serverProcess { Test-AgentServer } 'Server'

    $webProcess = Start-Process -FilePath $nodePath -ArgumentList @(('"' + $vitePath + '"'), '--host', '127.0.0.1', '--port', [string]$WebPort, '--strictPort') -WorkingDirectory (Join-Path $projectRoot 'apps\web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'web.out.log') -RedirectStandardError (Join-Path $logDir 'web.err.log')
    $ownedProcesses += $webProcess
    Wait-Service $webProcess { Test-AgentWeb } 'Web'

    Write-Host ''
    Write-Host "Agent CF ready: $webUrl" -ForegroundColor Green
    Write-Host "Server:         $serverUrl"
    Write-Host 'Local UI mode: Server + Web. Run execution needs separately configured workers/Client.'
    if ($SmokeTest) {
        Write-Host 'Startup and Web -> Server -> SQLite checks passed.'
    } else {
        if (-not $NoBrowser) { Start-Process $webUrl }
        Read-Host 'Press Enter here to stop Server and Web' | Out-Null
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
} finally {
    # Only terminate processes started by this invocation; never kill a port owner.
    foreach ($process in ($ownedProcesses | Sort-Object Id -Descending)) {
        if (-not $process.HasExited) {
            & taskkill.exe /PID $process.Id /T /F 2>&1 | Out-Null
        }
    }
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
}
exit $exitCode
