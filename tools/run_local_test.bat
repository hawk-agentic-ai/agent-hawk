@echo off
setlocal ENABLEDELAYEDEXPANSION
echo === Unified Backend Local Test (Windows) ===

REM Check backend health
echo Checking backend at http://localhost:8004/health ...
powershell -Command "$ErrorActionPreference='SilentlyContinue'; $r=Invoke-WebRequest -UseBasicParsing http://localhost:8004/health; if ($r.StatusCode -eq 200) { Write-Host 'OK - Backend is UP' } else { Write-Host 'FAIL - Backend not responding'; exit 1 }" 1>nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo Backend not reachable.
  echo Start it with:
  echo   python -m uvicorn unified_smart_backend:app --reload --port 8004
  echo Make sure SUPABASE_URL, SUPABASE_ANON_KEY, DIFY_API_KEY are set.
  pause
  exit /b 1
)

echo Running streaming smoke test (HKD utilization)...
call tools\local_smoke_test.bat

echo.
echo === Done ===
pause

