# LJR.devOS -- Remote Terminal (ttyd + Tailscale)
# Starts ttyd serving PowerShell on port 7681, accessible via Tailscale only.
# Usage: .\scripts\start-remote-terminal.ps1
# Stop:  .\scripts\stop-remote-terminal.ps1

# ---- Config ---------------------------------------------------------------

$TTYD         = "C:\Users\HomePC\tools\ttyd.exe"
$PORT         = 7681
$TTYD_USER    = "ljr"
$TAILSCALE_IP = "100.116.49.59"
$WORK_DIR     = "C:\Users\HomePC\ljr-dev-os"
$PID_DIR      = "$env:TEMP\ljros-remote"
$PID_FILE     = "$PID_DIR\ttyd.pid"
$WATCHDOG_PID = "$PID_DIR\watchdog.pid"
$SESSION_FILE = "$PID_DIR\session.json"
$LOG_FILE     = "$PID_DIR\ttyd.log"

# ---- Log function ---------------------------------------------------------

function Write-Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
    Write-Host $line
}

# ---- Pre-flight: ttyd binary ----------------------------------------------

if (-not (Test-Path $TTYD)) {
    Write-Host "ERROR: ttyd.exe not found at $TTYD"
    Write-Host "Binary should be at C:\Users\HomePC\tools\ttyd.exe"
    exit 1
}

# ---- Create PID dir -------------------------------------------------------

New-Item -ItemType Directory -Force -Path $PID_DIR | Out-Null

# ---- Double-start guard ---------------------------------------------------

$raw = Get-Content $WATCHDOG_PID -ErrorAction SilentlyContinue
if ($raw) {
    $existingPid = $raw.Trim()
    $alive = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($alive) {
        Write-Host ""
        Write-Host "Remote terminal already running (watchdog PID $existingPid)."
        Write-Host "URL: http://${TAILSCALE_IP}:${PORT}"
        Write-Host "To stop: .\scripts\stop-remote-terminal.ps1"
        Write-Host ""
        exit 0
    }
}

# ---- Save watchdog PID (this process) -------------------------------------

"$PID" | Out-File -Encoding ASCII $WATCHDOG_PID

# ---- Password resolution --------------------------------------------------

if ($env:TTYD_PASSWORD) {
    $password = $env:TTYD_PASSWORD
    $pwSource = "env var"
} else {
    $password = -join ((48..57) + (97..102) | Get-Random -Count 12 | ForEach-Object { [char]$_ })
    $pwSource = "generated"
}

# ---- Write session.json ---------------------------------------------------

$session = @{
    url      = "http://${TAILSCALE_IP}:${PORT}"
    username = $TTYD_USER
    password = $password
    started  = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    source   = $pwSource
}
$session | ConvertTo-Json | Out-File -Encoding UTF8 $SESSION_FILE

# ---- Print banner ---------------------------------------------------------

Write-Host ""
Write-Host "========================================"
Write-Host "  REMOTE TERMINAL STARTING"
Write-Host "========================================"
Write-Host "  URL:      http://${TAILSCALE_IP}:${PORT}"
Write-Host "  Username: $TTYD_USER"
Write-Host "  Password: $password  ($pwSource)"
Write-Host "  Log:      $LOG_FILE"
Write-Host "  Session:  $SESSION_FILE"
Write-Host "========================================"
Write-Host ""

Write-Log "Watchdog started (PID $PID)"
Write-Log "Password source: $pwSource"

# ---- Build ttyd argument list ---------------------------------------------

$ttydArgs = @(
    "-p", "$PORT",
    "-c", "${TTYD_USER}:${password}",
    "-W",
    "-m", "2",
    "-t", "fontSize=14",
    "-t", "disableLeaveAlert=true",
    "-w", $WORK_DIR,
    "powershell.exe",
    "-NoLogo"
)

# ---- Watchdog loop --------------------------------------------------------

$restartCount = 0

while ($true) {
    $restartCount++
    Write-Log "Starting ttyd (run #$restartCount)..."

    # Check if port is already in use before each start
    $portBusy = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
    if ($portBusy) {
        Write-Log "WARNING: port $PORT already in use by PID $($portBusy.OwningProcess)"
    }

    $proc = Start-Process `
        -FilePath $TTYD `
        -ArgumentList $ttydArgs `
        -PassThru `
        -WindowStyle Hidden

    "$($proc.Id)" | Out-File -Encoding ASCII $PID_FILE
    Write-Log "ttyd started (PID $($proc.Id))"

    # Block until ttyd exits
    $proc.WaitForExit()

    $exitCode = $proc.ExitCode
    Write-Log "ttyd exited (code: $exitCode). Restarting in 5 seconds..."
    Start-Sleep 5
}
