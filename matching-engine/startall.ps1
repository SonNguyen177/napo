# Start exchange engine, client, and admin. Logs and PIDs go to .\.run\
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunDir = Join-Path $Root '.run'
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Test-PidAlive {
    param([int]$ProcessId)
    try { $null = Get-Process -Id $ProcessId -ErrorAction Stop; return $true }
    catch { return $false }
}

function Start-AppService {
    param(
        [string]$Name,
        [string]$WorkDir,
        [string]$Cmd
    )
    $pidFile = Join-Path $RunDir "$Name.pid"
    $logFile = Join-Path $RunDir "$Name.log"

    if (Test-Path $pidFile) {
        $existing = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        $existingPid = 0
        if ($existing -and [int]::TryParse($existing.Trim(), [ref]$existingPid) -and (Test-PidAlive -ProcessId $existingPid)) {
            Write-Host "[$Name] already running (pid $existingPid)"
            return
        }
    }

    Write-Host "[$Name] starting..."
    # Clear previous log
    Set-Content -Path $logFile -Value '' -Encoding utf8

    # Launch via cmd /c so we can redirect both streams and detach.
    $proc = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', $Cmd `
        -WorkingDirectory $WorkDir `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError  "$logFile.err" `
        -WindowStyle Hidden `
        -PassThru

    $proc.Id | Out-File -FilePath $pidFile -Encoding ascii
    Start-Sleep -Seconds 2

    if (Test-PidAlive -ProcessId $proc.Id) {
        Write-Host "[$Name] pid $($proc.Id), log: $logFile"
    } else {
        Write-Host "[$Name] FAILED to start - see $logFile"
    }
}

Start-AppService -Name 'engine' -WorkDir (Join-Path $Root 'exchange\engine') -Cmd 'uv run python -m engine.main'
Start-AppService -Name 'admin'  -WorkDir (Join-Path $Root 'exchange\admin')  -Cmd 'npm run dev'
Start-AppService -Name 'client' -WorkDir (Join-Path $Root 'client')          -Cmd 'npm run dev'

Write-Host ''
Write-Host 'URLs:'
Write-Host '  Admin UI:         http://localhost:3001'
Write-Host '  Client UI:        http://localhost:5173'
Write-Host '  Engine API:       http://localhost:8000'
Write-Host '  Engine client WS: ws://localhost:8765'
Write-Host '  Engine admin WS:  ws://localhost:8000/ws/admin'
Write-Host ''
Write-Host "Tail logs:  Get-Content $RunDir\engine.log -Wait"
Write-Host 'Stop all:   .\stopall.ps1'
