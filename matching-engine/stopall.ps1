# Stop engine, client, and admin started by startall.ps1.
# Uses PID files in .\.run\, falls back to killing by port.
$ErrorActionPreference = 'SilentlyContinue'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunDir = Join-Path $Root '.run'

function Stop-Tree {
    param([int]$ProcessId)
    # taskkill /T kills the whole tree; /F forces after graceful attempt.
    & taskkill.exe /PID $ProcessId /T 2>$null | Out-Null
    Start-Sleep -Seconds 1
    if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        & taskkill.exe /PID $ProcessId /T /F 2>$null | Out-Null
    }
}

function Stop-ByPidFile {
    param([string]$Name)
    $pidFile = Join-Path $RunDir "$Name.pid"
    if (-not (Test-Path $pidFile)) { return }

    $raw = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $raw) { Remove-Item $pidFile -Force; return }
    $target = 0
    if (-not [int]::TryParse($raw.Trim(), [ref]$target)) { Remove-Item $pidFile -Force; return }

    if (Get-Process -Id $target -ErrorAction SilentlyContinue) {
        Write-Host "[$Name] stopping pid $target (+ children)"
        Stop-Tree -ProcessId $target
    } else {
        Write-Host "[$Name] not running (stale pid file)"
    }
    Remove-Item $pidFile -Force
}

function Stop-ByPort {
    param([string]$Name, [int]$Port)
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return }
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    if ($pids) {
        Write-Host "[$Name] port ${Port}: killing $($pids -join ' ')"
        foreach ($p in $pids) { Stop-Tree -ProcessId $p }
    }
}

foreach ($svc in @('engine', 'admin', 'client')) {
    Stop-ByPidFile -Name $svc
}

# Fallback cleanup in case services were started without the script.
Stop-ByPort -Name 'engine-api' -Port 8000
Stop-ByPort -Name 'engine-ws'  -Port 8765
Stop-ByPort -Name 'admin'      -Port 3001
Stop-ByPort -Name 'client'     -Port 5173

Write-Host 'done.'
