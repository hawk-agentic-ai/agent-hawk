# HAWK Agent - Simplified Deployment Guide

## Quick Start

### Deploy Everything
```bash
./deploy.sh
```

### Deploy Specific Components
```bash
./deploy.sh frontend    # Frontend only
./deploy.sh backend     # Backend only
```

## What This Does

### Frontend Deployment (`./deploy.sh frontend`)
1. **Build**: `npm run build:prod` - Creates optimized Angular build
2. **Package**: Creates `frontend-deployment.tar.gz` from `dist/hedge-accounting-sfx/`
3. **Upload**: SCP to server `/tmp/`
4. **Deploy**: Extracts to `/var/www/13-222-100-183.nip.io/`
5. **Permissions**: Sets `www-data:www-data` ownership
6. **Reload**: Reloads nginx to serve new files
7. **Test**: Verifies deployment with health check

### Backend Deployment (`./deploy.sh backend`)
1. **Upload**: SCP `mcp_server_production_v2.py` and `shared/` folder
2. **Stop**: Kills existing MCP server process
3. **Environment**: Sets Supabase and CORS environment variables
4. **Start**: Launches new MCP server in background
5. **Verify**: Checks process is running and healthy
6. **Test**: Health check on MCP endpoint

## Production Environment
- **URL**: https://13-222-100-183.nip.io
- **Server**: AWS EC2 Ubuntu 22.04
- **SSL**: Let's Encrypt auto-renewing certificates
- **Architecture**: nginx → Angular SPA + API proxies

## File Structure
```
hedge-agent/
├── deploy.sh                    # Main deployment script
├── agent_hawk.pem              # SSH private key
├── DEPLOYMENT_LOG.md            # Detailed deployment history
├── old_deploy_scripts/          # Archived old scripts
├── src/                         # Angular source code
├── dist/                        # Build output (generated)
└── shared/                      # Backend shared modules
```

## Requirements
- Node.js (for Angular builds)
- SSH access to production server
- `agent_hawk.pem` in project root

## Troubleshooting
See `DEPLOYMENT_LOG.md` for detailed troubleshooting guide and recent deployment history.

## Security
- SSH key and environment variables contain sensitive credentials
- Do not commit `agent_hawk.pem` to version control
- Production uses HTTPS with proper CORS configuration