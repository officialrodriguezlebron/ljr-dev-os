# LJR.devOS -- Task Scheduler setup for Remote Terminal (run once)
# Registers ONLOGON trigger: ttyd starts automatically after login.
# Safe to re-run -- /Force overwrites existing task.

$SCRIPT   = "C:\Users\HomePC\ljr-dev-os\scripts\start-remote-terminal.ps1"
$taskName = "LJR-RemoteTerminal"
$log      = "$env:TEMP\ljros-remote-task-setup.log"

New-Item -ItemType Directory -Force -Path "$env:TEMP\ljros-remote" | Out-Null

function Write-Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $log -Value $line -Encoding UTF8
    Write-Host $line
}

Write-Host ""
Write-Host "========================================"
Write-Host "  Remote Terminal -- Task Scheduler Setup"
Write-Host "========================================"

# ---- Verify start script exists ------------------------------------------

if (-not (Test-Path $SCRIPT)) {
    Write-Log "ERROR: start script not found: $SCRIPT"
    Write-Log "Run from ljr-dev-os repo root."
    exit 1
}
Write-Log "Start script found: $SCRIPT"

# ---- Build task components -----------------------------------------------

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -NonInteractive -File `"$SCRIPT`"" `
    -WorkingDirectory "C:\Users\HomePC\ljr-dev-os"

# AtLogOn trigger for the current user
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

# 1-minute delay after logon (Tailscale routes settle)
$trigger.Delay = "PT1M"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit 0 `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

# ---- Remove existing task if present -------------------------------------

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Log "Removed existing task: $taskName"
}

# ---- Register task -------------------------------------------------------

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Limited `
    -Force | Out-Null

Write-Log "Task registered: $taskName"

# ---- Verify ---------------------------------------------------------------

$registeredTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $registeredTask) {
    Write-Log "ERROR: Task registration failed -- task not found after create"
    exit 1
}

Write-Log "State:   $($registeredTask.State)"
Write-Log "Trigger: $($registeredTask.Triggers[0].CimClass.CimClassName)"
Write-Log "Delay:   $($registeredTask.Triggers[0].Delay)"

# ---- Summary --------------------------------------------------------------

Write-Host ""
Write-Host "========================================"
Write-Host "  DONE"
Write-Host "========================================"
Write-Host "  Task:    $taskName  (State: $($registeredTask.State))"
Write-Host "  Trigger: At logon ($env:USERDOMAIN\$env:USERNAME)"
Write-Host "  Delay:   1 minute after login"
Write-Host "  Script:  $SCRIPT"
Write-Host "  Log:     $log"
Write-Host ""
Write-Host "  Test now (no need to log off):"
Write-Host "    Start-ScheduledTask -TaskName '$taskName'"
Write-Host ""
Write-Host "  Remove:"
Write-Host "    Unregister-ScheduledTask -TaskName '$taskName' -Confirm:$false"
Write-Host "========================================"
Write-Host ""
