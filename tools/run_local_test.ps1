$ErrorActionPreference = 'Stop'
Write-Host "=== Unified Backend Local Test (PowerShell) ===" -ForegroundColor Cyan

function Test-Health {
  try {
    $r = Invoke-WebRequest -UseBasicParsing http://localhost:8004/health
    if ($r.StatusCode -eq 200) {
      Write-Host "OK - Backend is UP" -ForegroundColor Green
      return $true
    }
  } catch {
    Write-Host "Backend not reachable: $($_.Exception.Message)" -ForegroundColor Red
  }
  return $false
}

if (-not (Test-Health)) {
  Write-Host "Start backend with:" -ForegroundColor Yellow
  Write-Host "  python -m uvicorn unified_smart_backend:app --reload --port 8004" -ForegroundColor Yellow
  Write-Host "Ensure env vars: SUPABASE_URL, SUPABASE_ANON_KEY, DIFY_API_KEY" -ForegroundColor Yellow
  exit 1
}

Write-Host "Running streaming smoke test (HKD utilization)..." -ForegroundColor Cyan
python tools/local_smoke_test.py | Write-Output

Write-Host "=== Done ===" -ForegroundColor Cyan

