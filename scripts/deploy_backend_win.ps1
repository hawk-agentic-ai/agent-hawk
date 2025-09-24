Param(
  [string]$Host = '3.91.170.95',
  [string]$User = 'ec2-user',
  [string]$KeyPath = "$env:USERPROFILE\.ssh\hedge-agent-key.pem",
  [string]$SupabaseUrl = $env:SUPABASE_URL,
  [string]$SupabaseServiceRoleKey = $env:SUPABASE_SERVICE_ROLE_KEY,
  [string]$SupabaseAnonKey = $env:SUPABASE_ANON_KEY,
  [string]$DifyApiKey = $env:DIFY_API_KEY
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "🚀 Deploying Unified Smart Backend to $User@$Host (port 8004)" -ForegroundColor Cyan

# Validate tools
foreach ($tool in @('ssh','scp')) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw "Required tool '$tool' is not available on PATH. Install OpenSSH Client and retry."
  }
}

# Validate key
if (-not (Test-Path $KeyPath)) {
  throw "SSH key not found at: $KeyPath"
}

# Resolve project root (this script lives in hedge-agent/scripts)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Build package directory with needed files
$stamp = (Get-Date).ToString('yyyyMMddHHmmss')
$pkgDir = Join-Path $env:TEMP "unified_backend_pkg_$stamp"
New-Item -ItemType Directory -Force -Path $pkgDir | Out-Null

$candidates = @(
  'unified_smart_backend.py',
  'payloads.py',
  'requirements_fixed_new.txt',
  'requirements.txt',
  'Dockerfile',
  'hedge_management_cache_config.py',
  'prompt_intelligence_engine.py',
  'smart_data_extractor.py',
  'shared'
)

$toCopy = @()
foreach ($rel in $candidates) {
  $src = Join-Path $projectRoot $rel
  if (Test-Path $src) { $toCopy += $rel }
}
if ($toCopy.Count -eq 0) { throw "No package files found; aborting." }

foreach ($rel in $toCopy) {
  $src = Join-Path $projectRoot $rel
  $dst = Join-Path $pkgDir $rel
  if (Test-Path $src -PathType Container) {
    Copy-Item $src -Destination $dst -Recurse -Force
  } else {
    $dstParent = Split-Path -Parent $dst
    if ($dstParent) { New-Item -ItemType Directory -Force -Path $dstParent | Out-Null }
    Copy-Item $src -Destination $dst -Force
  }
}

Write-Host "📦 Package prepared at $pkgDir" -ForegroundColor Green

# Test SSH connectivity
Write-Host "🔗 Testing SSH connectivity..." -ForegroundColor Yellow
ssh -i "$KeyPath" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$User@$Host" "echo 'ok'" | Out-Null

# Upload package (recursive)
Write-Host "📤 Uploading files to server..." -ForegroundColor Yellow
ssh -i "$KeyPath" -o StrictHostKeyChecking=no "$User@$Host" "rm -rf ~/unified_backend_pkg && mkdir -p ~/unified_backend_pkg"
scp -i "$KeyPath" -o StrictHostKeyChecking=no -r "$pkgDir/*" "$User@$Host:~/unified_backend_pkg/"

# Remote deploy steps
$remote = @"
set -e
cd ~/unified_backend_pkg
echo "Stopping existing backend on 8004..."
sudo pkill -f "uvicorn.*8004" || true
sudo pkill -f "python.*unified_smart_backend.py" || true
sleep 2

echo "Installing dependencies..."
if [ -f requirements_fixed_new.txt ]; then
  pip3 install --user -r requirements_fixed_new.txt --quiet
elif [ -f requirements.txt ]; then
  pip3 install --user -r requirements.txt --quiet
fi

echo "Exporting environment variables..."
export SUPABASE_URL='${SupabaseUrl}'
export SUPABASE_SERVICE_ROLE_KEY='${SupabaseServiceRoleKey}'
export SUPABASE_ANON_KEY='${SupabaseAnonKey}'
export DIFY_API_KEY='${DifyApiKey}'

echo "Starting backend with uvicorn (port 8004)..."
nohup ~/.local/bin/uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004 >/home/$USER/unified_backend.log 2>&1 &
sleep 5

echo "Health check..."
curl -s http://localhost:8004/health >/dev/null && echo "OK" || (echo "Health check failed" && tail -n 50 /home/$USER/unified_backend.log)
"@

Write-Host "🚀 Deploying on remote host..." -ForegroundColor Cyan
ssh -i "$KeyPath" -o StrictHostKeyChecking=no "$User@$Host" "$remote"

Write-Host "🎉 Deployment complete. Verify via: curl http://$Host:8004/health" -ForegroundColor Green

