# LJR.devOS -- Stop Remote Terminal
# Kills watchdog first, then ttyd. Order matters.
# Usage: .\scripts\stop-remote-terminal.ps1

$PID_DIR      = "$env:TEMP\ljros-remote"
$WATCHDOG_PID = "$PID_DIR\watchdog.pid"
$PID_FILE     = "$PID_DIR\ttyd.pid"
$SESSION_FILE = "$PID_DIR\session.json"

$stopped = 0

Write-Host ""
Write-Host "Stopping remote terminal..."
Write-Host ""

# ---- Step 1: Kill watchdog FIRST (prevents restart race) ------------------

$raw = Get-Content $WATCHDOG_PID -ErrorAction SilentlyContinue
if ($raw) {
    $wPid = $raw.Trim()
    $alive = Get-Process -Id $wPid -ErrorAction SilentlyContinue
    if ($alive) {
        Stop-Process -Id $wPid -Force -ErrorAction SilentlyContinue
        Write-Host "  [1] Stopped watchdog    (PID $wPid)"
        $stopped++
    } else {
        Write-Host "  [1] Watchdog not running (PID $wPid was stale)"
    }
} else {
    Write-Host "  [1] No watchdog.pid found"
}

# ---- Step 2: Kill ttyd by saved PID ---------------------------------------

$raw = Get-Content $PID_FILE -ErrorAction SilentlyContinue
if ($raw) {
    $tPid = $raw.Trim()
    $alive = Get-Process -Id $tPid -ErrorAction SilentlyContinue
    if ($alive) {
        Stop-Process -Id $tPid -Force -ErrorAction SilentlyContinue
        Write-Host "  [2] Stopped ttyd         (PID $tPid)"
        $stopped++
    } else {
        Write-Host "  [2] ttyd not running      (PID $tPid was stale)"
    }
} else {
    Write-Host "  [2] No ttyd.pid found"
}

# ---- Step 3: Kill any stray ttyd processes by name ------------------------

$strays = Get-Process -Name "ttyd" -ErrorAction SilentlyContinue
if ($strays) {
    foreach ($s in $strays) {
        Stop-Process -Id $s.Id -Force -ErrorAction SilentlyContinue
        Write-Host "  [3] Killed stray ttyd    (PID $($s.Id))"
        $stopped++
    }
}

# ---- Step 4: Cleanup files ------------------------------------------------

Remove-Item "$PID_DIR\*.pid"  -Force -ErrorAction SilentlyContinue
Remove-Item $SESSION_FILE     -Force -ErrorAction SilentlyContinue

# ---- Summary --------------------------------------------------------------

Write-Host ""
if ($stopped -gt 0) {
    Write-Host "========================================"
    Write-Host "  Remote terminal stopped. ($stopped process(es) killed)"
    Write-Host "========================================"
} else {
    Write-Host "  Nothing was running (already stopped)."
}
Write-Host ""
