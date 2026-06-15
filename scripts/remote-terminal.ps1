# LJR.devOS — Remote Terminal
# Starts ttyd (terminal-over-web) + Caddy (basic auth proxy) + ngrok (public tunnel)
# Usage: .\remote-terminal.ps1
# Stop:  .\stop-remote-terminal.ps1
#
# SECURITY: exposes a full PowerShell terminal to the public internet.
# Use only while actively vibecoding. Stop when done.

$ErrorActionPreference = "Stop"

$TOOLS   = "C:\Users\HomePC\tools"
$TTYD    = "$TOOLS\ttyd.exe"
$CADDY   = "$TOOLS\caddy.exe"
$NGROK   = "$TOOLS\ngrok.exe"
$PID_DIR = "$env:TEMP\ljros-remote"

# ── Pre-flight: verify tools exist ────────────────────────────────────
foreach ($exe in @($TTYD, $CADDY, $NGROK)) {
    if (-not (Test-Path $exe)) {
        Write-Host "ERROR: Missing binary: $exe"
        Write-Host "Run setup from ljr-dev-os repo to reinstall tools."
        exit 1
    }
}

# ── Pre-flight: check ngrok is authenticated ──────────────────────────
$ngrokConfig = "$env:LOCALAPPDATA\ngrok\ngrok.yml"
$ngrokHasToken = $false
if (Test-Path $ngrokConfig) {
    $configContent = Get-Content $ngrokConfig -Raw
    $ngrokHasToken = $configContent -match "authtoken"
}
if (-not $ngrokHasToken) {
    Write-Host ""
    Write-Host "================================================"
    Write-Host "  NGROK AUTH TOKEN REQUIRED (one-time setup)"
    Write-Host "================================================"
    Write-Host ""
    Write-Host "1. Sign up free at https://dashboard.ngrok.com/"
    Write-Host "2. Copy your auth token"
    Write-Host "3. Run: $NGROK config add-authtoken YOUR_TOKEN_HERE"
    Write-Host "4. Then re-run remote-terminal.ps1"
    Write-Host ""
    exit 1
}

New-Item -ItemType Directory -Force -Path $PID_DIR | Out-Null

# ── Generate random 8-char hex password ───────────────────────────────
$password = -join ((48..57) + (97..102) | Get-Random -Count 8 | ForEach-Object { [char]$_ })
Write-Host ""
Write-Host "Session password: $password"

# ── Hash password for Caddy basic_auth ────────────────────────────────
$hashedPassword = (& $CADDY hash-password --plaintext $password 2>&1 | Select-Object -Last 1)
Write-Host "Password hashed OK."

# ── Start ttyd serving PowerShell on port 7681 ────────────────────────
Write-Host ""
Write-Host "Starting ttyd :7681..."
$ttydProc = Start-Process -FilePath $TTYD -ArgumentList @("-p", "7681", "powershell.exe") `
    -PassThru -WindowStyle Hidden
$ttydProc.Id | Out-File -Encoding ASCII "$PID_DIR\ttyd.pid"
Start-Sleep -Seconds 1
Write-Host "ttyd started (PID $($ttydProc.Id))"

# ── Write Caddyfile — basic_auth proxy :7682 → :7681 ──────────────────
# header_up Connection + Upgrade: required for Caddy to pass WebSocket
# upgrade requests through to ttyd. Without these, the browser gets
# 101 on the page load but WS reconnect fails ("Press Enter to Reconnect").
@"
:7682 {
    basic_auth /* {
        lebron $hashedPassword
    }
    reverse_proxy localhost:7681 {
        header_up Host {http.reverse_proxy.upstream.hostport}
        header_up Connection {http.request.header.Connection}
        header_up Upgrade {http.request.header.Upgrade}
    }
}
"@ | Out-File -Encoding utf8 "$PID_DIR\Caddyfile"

Write-Host "Starting Caddy :7682..."
$caddyProc = Start-Process -FilePath $CADDY -ArgumentList @("run", "--config", "$PID_DIR\Caddyfile") `
    -PassThru -WindowStyle Hidden
$caddyProc.Id | Out-File -Encoding ASCII "$PID_DIR\caddy.pid"
Start-Sleep -Seconds 2
Write-Host "Caddy started (PID $($caddyProc.Id))"

# ── Start ngrok tunnel ─────────────────────────────────────────────────
Write-Host "Starting ngrok tunnel to :7682..."
$ngrokProc = Start-Process -FilePath $NGROK -ArgumentList @("http", "7682") `
    -PassThru -WindowStyle Hidden
$ngrokProc.Id | Out-File -Encoding ASCII "$PID_DIR\ngrok.pid"

# ── Poll ngrok API for the public URL (up to 15s) ─────────────────────
$publicUrl = $null
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        $t = $tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
        if ($t) { $publicUrl = $t.public_url; break }
    } catch { }
}

if (-not $publicUrl) {
    Write-Host ""
    Write-Host "ERROR: Could not get ngrok URL. Check: http://localhost:4040"
    Write-Host "ngrok may need re-authentication. Run: $NGROK config add-authtoken YOUR_TOKEN"
    exit 1
}

# ── Save session info ──────────────────────────────────────────────────
@{ url=$publicUrl; username="lebron"; password=$password; started=(Get-Date -Format "yyyy-MM-dd HH:mm:ss") } `
    | ConvertTo-Json | Out-File -Encoding utf8 "$PID_DIR\session.json"

# ── Print results ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================"
Write-Host "  REMOTE TERMINAL READY"
Write-Host "============================================"
Write-Host "  URL:      $publicUrl"
Write-Host "  Username: lebron"
Write-Host "  Password: $password"
Write-Host "============================================"
Write-Host ""
Write-Host "QR code (scan from phone):"
Write-Host ""

# QR code — single-line to avoid PowerShell here-string arg issues.
# Explicit UTF-8 wrapper needed for Windows console encoding (cp1252 can't render block chars).
$pyQr = "import qrcode,io,sys; out=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8'); qr=qrcode.QRCode(border=1); qr.add_data('$publicUrl'); qr.make(); qr.print_ascii(invert=True,out=out); out.flush()"
python -c $pyQr

Write-Host ""
Write-Host "Open URL in phone browser → lebron / [password above] → type 'claude'"
Write-Host "Run stop-remote-terminal.ps1 when done."
