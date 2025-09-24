Restored the real FastAPI backend locally on port 8004 and the production MCP server on port 8009. Frontend should work again against FastAPI; MCP tooling is now full‑capability (not the mock stub).
Cloud deployment is pending; I added a PowerShell deploy script and provided exact steps but didn’t push from this sandbox due to missing AWS/SSH access.
Current State

Unified backend: uvicorn unified_smart_backend:app --port 8004 (local OK; http://localhost:8004/health returns healthy).
MCP server: uvicorn mcp_server_production:app --port 8009 (local OK; nginx public path /mcp/).
Nginx proxies:
/api → 8004 (nginx_config_updated.conf:23)
/mcp/ → 8009 (nginx_config_updated.conf:35)
Frontend configured to call /api (src/environments/environment.prod.ts:1), so with FastAPI back the UI should submit and stream normally.
What We Did

Fixed VS runtime issues and started servers:
Installed Python deps in venv and ran backend: fastapi, uvicorn, httpx, redis, supabase.
Exported env vars and started backend on 8004; killed stray processes occupying the port.
Exported env vars and started MCP server on 8009; replaced the stub.
Hardened backend to run even without optional libs:
unified_smart_backend.py:17 added optional httpx import with requests fallback for streaming.
Optional redis handling to avoid startup failure if Redis lib/service missing.
Similar fallbacks in shared/data_extractor.py:1 and shared/supabase_client.py:6.
Verified:
GET /health healthy with Supabase/Redis initialized.
MCP server advertises "serverInfo": { "name": "hedge-fund-mcp", "version": "1.0.1" } (mcp_server_production.py:565, tools list at mcp_server_production.py:403 and _tools_list_result).
Prepared deployment:
Added Windows deploy script to push backend to EC2: hedge-agent/scripts/deploy_backend_win.ps1:1.
Reviewed existing Linux script hedge-agent/deploy_fixed_backend_to_aws.sh:1.
Where It Broke (Root Causes)

Frontend appeared “dead” because it was hitting a “quick” stub quick_backend.py that streamed plain answer text without expected Dify event metadata; Angular’s stream parser only updates on event: message/agent_message.
MCP moved to a pure HTTP stub dify_compatible_mcp_server.py that returns canned JSON and bypasses real Supabase/stage logic, so Dify calls weren’t executing real workflows.
What’s Fixed

FastAPI backend is restored locally (8004). Angular UI should now stream properly against /api/hawk-agent/process-prompt.
MCP server is running the full FastAPI app (8009) with the real tools wired into shared.hedge_processor.
Remaining Gaps / Why We’re Stuck

Cloud deployment not executed from this environment due to lack of AWS CLI/SSH access. Needs to be run from your machine.
Secrets are present in scripts and .env.production; recommend rotation and moving to environment store (AWS SSM/Secrets Manager) after deploy.
Next Steps

Deploy backend to EC2 (8004):
PowerShell (with OpenSSH installed):
cd C:\Users\vssvi\Downloads\hedge-agent\hedge-agent
Set envs: $env:SUPABASE_URL=...; $env:SUPABASE_SERVICE_ROLE_KEY=...; $env:DIFY_API_KEY=...
Run: .\scripts\deploy_backend_win.ps1 -KeyPath "$env:USERPROFILE\.ssh\hedge-agent-key.pem"
Or Linux script: ./deploy_fixed_backend_to_aws.sh
Start/daemonize MCP on EC2 (8009):
SSH: ssh -i "<key>" ec2-user@3.91.170.95
In repo venv: uvicorn mcp_server_production:app --host 0.0.0.0 --port 8009
Optionally create systemd units for both services.
Verify public endpoints:
Backend: https://3-91-170-95.nip.io/health
MCP JSON‑RPC init: POST https://3-91-170-95.nip.io/mcp/ with {"jsonrpc":"2.0","method":"initialize","id":1,...}
Frontend smoke tests:
Template and Agent modes: submit prompts, confirm streaming tokens render, confirm real DB-backed results.
Security hygiene:
Rotate keys used in scripts; move secrets to env store; scrub committed plaintexts.
Command Reference

Start unified backend (local):
uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004
Start MCP server (local):
uvicorn mcp_server_production:app --host 0.0.0.0 --port 8009
Kill port listeners (PowerShell):
netstat -ano | findstr :8004 then Stop-Process -Id <PID> -Force
netstat -ano | findstr :8009 then Stop-Process -Id <PID> -Force
SSH quick test (per project docs):
Backend box: ssh -i "$env:USERPROFILE\.ssh\hedge-agent-key.pem" ec2-user@3.91.170.95 "echo ok"
Frontend/Ubuntu box: ssh -i "C:\Users\vssvi\Downloads\hedge-agent\hedge-agent\agent_hawk.pem" ubuntu@3.91.170.95 "echo ok"

Local (your machine)

Unified Backend (FastAPI): http://localhost:8004
Runs via uvicorn unified_smart_backend:app (unified_smart_backend.py:1)
MCP Server (FastAPI): http://localhost:8009
Runs via uvicorn mcp_server_production:app (mcp_server_production.py:1)
Cloud (EC2 3.91.170.95)

Nginx (HTTPS): https://3-91-170-95.nip.io
Proxies /api → backend on port 8004 (nginx_config_updated.conf:23)
Proxies /mcp/ → MCP on port 8009 (nginx_config_updated.conf:35)
Backend processes on EC2: not redeployed in this session (status pending).