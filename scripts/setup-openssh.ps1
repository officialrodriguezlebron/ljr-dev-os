# LJR.devOS — OpenSSH Server Setup (run as Administrator)

$log = "$env:TEMP\openssh-setup.log"
"[$(Get-Date -Format 'HH:mm:ss')] Starting OpenSSH Server setup..." | Tee-Object $log

# 1. Install OpenSSH Server capability
Write-Host "Installing OpenSSH Server..."
$cap = Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
"[$(Get-Date -Format 'HH:mm:ss')] Capability install: $($cap.Online)" | Tee-Object $log -Append

# 2. Start sshd service
Write-Host "Starting sshd..."
Start-Service sshd
"[$(Get-Date -Format 'HH:mm:ss')] sshd started" | Tee-Object $log -Append

# 3. Set to auto-start on boot
Set-Service -Name sshd -StartupType Automatic
"[$(Get-Date -Format 'HH:mm:ss')] sshd set to Automatic" | Tee-Object $log -Append

# 4. Ensure firewall rule exists
$fwRule = Get-NetFirewallRule -Name *ssh* -ErrorAction SilentlyContinue
if (-not $fwRule) {
    Write-Host "Creating firewall rule for port 22..."
    New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
    "[$(Get-Date -Format 'HH:mm:ss')] Firewall rule created" | Tee-Object $log -Append
} else {
    "[$(Get-Date -Format 'HH:mm:ss')] Firewall rule already exists: $($fwRule.Name)" | Tee-Object $log -Append
}

# 5. Set default shell to PowerShell 5.1
$pwshPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value $pwshPath -PropertyType String -Force | Out-Null
"[$(Get-Date -Format 'HH:mm:ss')] Default shell set to $pwshPath" | Tee-Object $log -Append

# 6. Restart sshd to apply shell change
Restart-Service sshd
"[$(Get-Date -Format 'HH:mm:ss')] sshd restarted" | Tee-Object $log -Append

# 7. Final status
$svc = Get-Service sshd
"[$(Get-Date -Format 'HH:mm:ss')] DONE. sshd status: $($svc.Status), StartType: $($svc.StartType)" | Tee-Object $log -Append
Write-Host ""
Write-Host "============================================"
Write-Host "  OpenSSH Server setup complete"
Write-Host "  sshd: $($svc.Status) / $($svc.StartType)"
Write-Host "  Shell: PowerShell 5.1"
Write-Host "  Log: $log"
Write-Host "============================================"
Write-Host ""
Write-Host "Test with: ssh $env:USERNAME@localhost"
Write-Host "Phone: ssh $env:USERNAME@100.116.49.59"
Write-Host ""
Read-Host "Press Enter to close"
