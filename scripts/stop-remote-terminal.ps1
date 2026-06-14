# LJR.devOS — Stop Remote Terminal
# Kills ttyd, Caddy, and ngrok processes started by remote-terminal.ps1

$PID_DIR = "$env:TEMP\ljros-remote"
$stopped = 0

foreach ($name in @("ttyd", "caddy", "ngrok")) {
    $pidFile = "$PID_DIR\$name.pid"
    if (Test-Path $pidFile) {
        $procId = (Get-Content $pidFile).Trim()
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host "Stopped $name (PID $procId)"
            $stopped++
        } catch {
            Write-Host "$name PID $procId already gone"
        }
        Remove-Item $pidFile -Force
    }
    # Fallback: kill any stray processes by name
    Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Killed stray $name (PID $($_.Id))"
        $stopped++
    }
}

# Clean up session file
$sessionFile = "$PID_DIR\session.json"
if (Test-Path $sessionFile) { Remove-Item $sessionFile -Force }
$caddyFile = "$PID_DIR\Caddyfile"
if (Test-Path $caddyFile) { Remove-Item $caddyFile -Force }

if ($stopped -gt 0) {
    Write-Host ""
    Write-Host "Remote terminal stopped. Session ended."
} else {
    Write-Host "No remote terminal processes found (already stopped?)."
}
