# V2 MCP Server Deployment Status

## Current Status: READY FOR MANUAL DEPLOYMENT

### ✅ Completed Tasks
- [x] V2 server code prepared and tested locally
- [x] Deployment scripts created
- [x] Environment variables configured
- [x] CORS settings updated for cloud.dify.ai
- [x] Local V2 server verified working (port 8009)
- [x] Cloud port 8009 confirmed available
- [x] All deployment files created

### 🔄 Pending: Manual Cloud Deployment

Due to SSH access limitations, the V2 server needs to be manually deployed on the cloud server.

## Deployment Files Ready

1. **`cloud_deploy_v2.sh`** - Main deployment script
2. **`v2_deploy_remote.sh`** - Alternative deployment script
3. **`mcp_server_production v2.py`** - V2 server code

## Manual Deployment Steps

Connect to cloud server (3.91.170.95) and execute:

```bash
cd /home/ubuntu/hedge-agent/hedge-agent

# Set environment variables
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"

# Stop any existing MCP servers on port 8009
pkill -f "python.*mcp_server_production.py" || true
sleep 3

# Start V2 server
nohup python3 "mcp_server_production v2.py" > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid

# Verify deployment
sleep 8
curl -s http://localhost:8009/health
```

## Expected Endpoints After Deployment

- **Main Endpoint**: https://3-91-170-95.nip.io/mcp/
- **Health Check**: https://3-91-170-95.nip.io/mcp/health
- **Tools List**: https://3-91-170-95.nip.io/mcp/tools/list

## V2 Server Features

### Tools Available (5 total):
1. **process_hedge_prompt** - Stage 1A/2/3 processing with intent inference
2. **query_supabase_data** - CRUD with table validation and caps
3. **get_system_health** - System health and DB probe
4. **manage_cache** - Redis cache operations
5. **generate_agent_report** - Stage-specific agent reports

### Key Improvements:
- ✅ CORS configured for cloud.dify.ai
- ✅ Production security (API docs disabled)
- ✅ Optimized async handling
- ✅ Version 1.2.0 (vs V1's 1.0.0)
- ✅ Same tool functionality as V1

## Current Cloud Architecture

- **Port 80**: Frontend (Angular app) ✅ Running
- **Port 8009**: V2 MCP Server ⏳ Ready for deployment
- **Port 8010**: Allocation Server ✅ Running and healthy

## Verification Commands

After deployment, verify with:
```bash
# Health check
curl -s https://3-91-170-95.nip.io/mcp/health

# Tools list (requires auth)
curl -s -H "Authorization: Bearer your_token" https://3-91-170-95.nip.io/mcp/tools/list
```

## Dify Integration

Use these endpoints in Dify:
- **Server URL**: `https://3-91-170-95.nip.io/mcp/`
- **Authentication**: Bearer token required
- **CORS**: Enabled for cloud.dify.ai

## Next Steps

1. Access cloud server (3.91.170.95)
2. Upload V2 server file if not present
3. Execute deployment commands above
4. Verify endpoints are responding
5. Test with Dify integration