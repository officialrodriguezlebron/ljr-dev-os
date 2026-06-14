# One-time ngrok auth setup
# Run this once after getting your token from https://dashboard.ngrok.com/

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$NGROK = "C:\Users\HomePC\tools\ngrok.exe"

if (-not (Test-Path $NGROK)) {
    Write-Host "ERROR: ngrok.exe not found at $NGROK"
    exit 1
}

Write-Host "Configuring ngrok auth token..."
& $NGROK config add-authtoken $Token

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "ngrok authenticated. You can now run remote-terminal.ps1"
} else {
    Write-Host "ERROR: Token configuration failed. Check the token and try again."
    exit 1
}
