# LJR.devOS -- ttyd Firewall Hardening (run as Administrator, once)
# Replaces Windows auto-created broad "ttyd.exe" rules with a scoped rule:
#   - TCP only (not UDP)
#   - Port 7681 only
#   - Source: Tailscale CGNAT range 100.64.0.0/10
#   - Interface: Tailscale adapter only
#
# Without this, ttyd is reachable from any network (Public WiFi, LAN).

$RULE_BROAD  = "ttyd.exe"
$RULE_SCOPED = "ttyd Remote Terminal (Tailscale only)"
$TAILSCALE_SUBNET = "100.64.0.0/10"
$TAILSCALE_IF     = "Tailscale"
$PORT        = 7681
$log         = "$env:TEMP\ljros-firewall-setup.log"

New-Item -ItemType Directory -Force -Path "$env:TEMP\ljros-remote" | Out-Null

function Write-Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $log -Value $line -Encoding UTF8
    Write-Host $line
}

Write-Host ""
Write-Host "========================================"
Write-Host "  ttyd Firewall Hardening"
Write-Host "========================================"

# ---- Admin check ----------------------------------------------------------

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]"Administrator"
)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "ERROR: This script must run as Administrator."
    Write-Host "Right-click PowerShell -> 'Run as administrator', then re-run."
    Write-Host ""
    exit 1
}
Write-Log "Running as Administrator -- OK"

# ---- Verify Tailscale adapter exists --------------------------------------

$tsAdapter = Get-NetAdapter -Name $TAILSCALE_IF -ErrorAction SilentlyContinue
if (-not $tsAdapter) {
    Write-Log "ERROR: Tailscale adapter '$TAILSCALE_IF' not found."
    Write-Log "Ensure Tailscale is installed and connected."
    exit 1
}
Write-Log "Tailscale adapter: $($tsAdapter.Name) -- $($tsAdapter.Status)"

# ---- Remove broad auto-created rules --------------------------------------

$broadRules = Get-NetFirewallRule -DisplayName $RULE_BROAD -ErrorAction SilentlyContinue
if ($broadRules) {
    $count = ($broadRules | Measure-Object).Count
    $broadRules | Remove-NetFirewallRule
    Write-Log "Removed $count broad rule(s): '$RULE_BROAD'"
} else {
    Write-Log "No broad rules found (already cleaned up or never created)"
}

# ---- Remove old scoped rule if re-running ---------------------------------

$oldScoped = Get-NetFirewallRule -DisplayName $RULE_SCOPED -ErrorAction SilentlyContinue
if ($oldScoped) {
    $oldScoped | Remove-NetFirewallRule
    Write-Log "Removed previous scoped rule (re-run detected)"
}

# ---- Create scoped rule ---------------------------------------------------

New-NetFirewallRule `
    -DisplayName  $RULE_SCOPED `
    -Direction    Inbound `
    -Protocol     TCP `
    -LocalPort    $PORT `
    -RemoteAddress $TAILSCALE_SUBNET `
    -InterfaceAlias $TAILSCALE_IF `
    -Action       Allow `
    -Profile      Any `
    -Enabled      True | Out-Null

Write-Log "Created scoped rule: '$RULE_SCOPED'"

# ---- Verify ---------------------------------------------------------------

$scopedRule = Get-NetFirewallRule -DisplayName $RULE_SCOPED -ErrorAction SilentlyContinue
if (-not $scopedRule) {
    Write-Log "ERROR: Scoped rule not found after creation"
    exit 1
}

$filter = $scopedRule | Get-NetFirewallPortFilter
$addrFilter = $scopedRule | Get-NetFirewallAddressFilter
$ifFilter = $scopedRule | Get-NetFirewallInterfaceFilter

Write-Log "Rule verified:"
Write-Log "  Protocol:      $($filter.Protocol)"
Write-Log "  Port:          $($filter.LocalPort)"
Write-Log "  RemoteAddress: $($addrFilter.RemoteAddress)"
Write-Log "  Interface:     $($ifFilter.InterfaceAlias)"
Write-Log "  Profile:       $($scopedRule.Profile)"
Write-Log "  Enabled:       $($scopedRule.Enabled)"

# ---- Confirm no broad rules remain ----------------------------------------

$remaining = Get-NetFirewallRule -DisplayName $RULE_BROAD -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Log "WARNING: Broad rule '$RULE_BROAD' still exists -- manual removal needed"
} else {
    Write-Log "Confirmed: no broad rules remain"
}

# ---- Summary --------------------------------------------------------------

Write-Host ""
Write-Host "========================================"
Write-Host "  DONE"
Write-Host "========================================"
Write-Host "  Removed:  '$RULE_BROAD' (broad, any port, any remote)"
Write-Host "  Created:  '$RULE_SCOPED'"
Write-Host "  TCP only: port $PORT"
Write-Host "  Source:   $TAILSCALE_SUBNET (Tailscale CGNAT)"
Write-Host "  Interface: $TAILSCALE_IF adapter only"
Write-Host "  Profile:  Any (Tailscale handles the perimeter)"
Write-Host ""
Write-Host "  Access from:"
Write-Host "    Tailscale devices -> ALLOWED"
Write-Host "    Public WiFi (no Tailscale) -> BLOCKED"
Write-Host "    Same LAN (no Tailscale) -> BLOCKED"
Write-Host "    Localhost (testing) -> BLOCKED (by design)"
Write-Host ""
Write-Host "  Log: $log"
Write-Host "========================================"
Write-Host ""
