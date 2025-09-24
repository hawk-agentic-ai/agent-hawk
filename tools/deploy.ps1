<#
  Hedge Agent – One‑Click Deploy Script (PowerShell)

  What it does:
  - Packages the local 'hedge-agent' folder
  - Uploads it to the server via scp
  - Backs up the current remote folder
  - Extracts the new files into /home/ubuntu/hedge-agent
  - Restarts the MCP server (systemd) and reloads FastAPI (uvicorn --reload)
  - Verifies health for both services

  Usage (PowerShell):
  - Open PowerShell in the repo root (C:\Users\vssvi\Downloads)
  - Run:  powershell -ExecutionPolicy Bypass -File .\hedge-agent\tools\deploy.ps1
  (or simply: .\hedge-agent\tools\deploy.ps1)

  Optional overrides:
  - .\hedge-agent\tools\deploy.ps1 -Host ubuntu@3.91.170.95 -KeyPath .\hedge-agent\agent_hawk.pem -ProjectDir .\hedge-agent
#>

param(
  [string]$RemoteHost = 'ubuntu@3.91.170.95',
  [string]$KeyPath = (Join-Path $PSScriptRoot '..\agent_hawk.pem'),
  [string]$ProjectDir = (Join-Path $PSScriptRoot '..'),
  [string]$RemoteDir = '/home/ubuntu/hedge-agent',
  [switch]$SkipVerify
)

$ErrorActionPreference = 'Stop'

function Test-Command($name) {
  $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Require-Command($name) {
  if (-not (Test-Command $name)) {
    throw "Required command '$name' not found in PATH. Please install OpenSSH client and ensure '$name' is available."
  }
}

function Exec($cmd, $msg) {
  Write-Host "`n>>> $msg" -ForegroundColor Cyan
  Write-Host "$cmd" -ForegroundColor DarkGray
  & $cmd
  if ($LASTEXITCODE -ne 0) { throw "Command failed: $cmd" }
}

function Quote($s) {
  return '"' + ($s -replace '"','\"') + '"'
}

# Resolve paths
$KeyPath = (Resolve-Path $KeyPath).Path
$ProjectRoot = (Resolve-Path (Join-Path $ProjectDir '..')).Path
$ProjectPath = (Resolve-Path $ProjectDir).Path

# Validate commands
Require-Command ssh
Require-Command scp
Require-Command tar
Require-Command curl.exe

Write-Host "Host: $RemoteHost" -ForegroundColor Yellow
Write-Host "Key : $KeyPath" -ForegroundColor Yellow
Write-Host "Proj: $ProjectPath" -ForegroundColor Yellow

# Fix key permissions (Windows)
Write-Host "`n>>> Fixing key permissions (icacls)" -ForegroundColor Cyan
icacls $KeyPath /inheritance:r | Out-Null
icacls $KeyPath /grant:r "$($env:USERNAME):R" | Out-Null

# Create tarball in TEMP
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$archive = Join-Path $env:TEMP "hedge-agent-full-$ts.tar.gz"
Write-Host "`n>>> Creating archive: $archive" -ForegroundColor Cyan
Push-Location (Split-Path $ProjectPath -Parent)
try {
  # Use relative path so tar packs the 'hedge-agent' folder
  tar -czf $archive --exclude='hedge-agent/.git' --exclude='hedge-agent/__pycache__' hedge-agent
}
finally {
  Pop-Location
}
Get-Item $archive | Format-Table Name,Length,FullName -AutoSize

# Upload via scp
Exec "scp -i $KeyPath -o StrictHostKeyChecking=no `"$archive`" ${RemoteHost}:/tmp/" "Uploading archive to server"

# Remote steps: backup, extract, chown, restart services
$remote = @"
set -e
TS=\$(date +%Y%m%d-%H%M%S)
ARCH=\$(ls -t /tmp/hedge-agent-full-*.tar.gz | head -n1)
cd /home/ubuntu
echo "Backing up current: /tmp/hedge-agent-backup-$TS.tgz"
sudo tar -czf /tmp/hedge-agent-backup-$TS.tgz hedge-agent || true
echo "Extracting new archive: $ARCH -> $RemoteDir"
sudo tar -xzf "$ARCH" -C /home/ubuntu
sudo chown -R ubuntu:ubuntu $RemoteDir
echo "Restarting MCP service..."
sudo systemctl restart hedge-mcp.service
sleep 1
sudo systemctl is-active hedge-mcp.service
echo "Reloading FastAPI (uvicorn --reload) by touching main file..."
touch $RemoteDir/unified_smart_backend.py
echo "Listeners:"
ss -tlnp | egrep ':8004|:8009' || true
"@

Exec "ssh -i $KeyPath -o StrictHostKeyChecking=no ${RemoteHost} $([scriptblock]::Create($remote))" "Deploying remotely and restarting services"

if (-not $SkipVerify) {
  Write-Host "`n>>> FastAPI health (https://3-91-170-95.nip.io/api/health)" -ForegroundColor Cyan
  curl.exe -sS https://3-91-170-95.nip.io/api/health | Out-String | Write-Host

  Write-Host "`n>>> MCP initialize (https://3-91-170-95.nip.io/mcp/)" -ForegroundColor Cyan
  $init = '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"deploy","version":"1.0"}}}'
  curl.exe -sS -H "Content-Type: application/json" -d $init https://3-91-170-95.nip.io/mcp/ | Out-String | Write-Host

  Write-Host "`n>>> MCP tools/list" -ForegroundColor Cyan
  $list = '{"jsonrpc":"2.0","method":"tools/list","id":2,"params":{}}'
  curl.exe -sS -H "Content-Type: application/json" -d $list https://3-91-170-95.nip.io/mcp/ | Out-String | Write-Host
}

Write-Host "`nDeploy complete." -ForegroundColor Green
