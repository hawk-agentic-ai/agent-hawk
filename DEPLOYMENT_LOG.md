# HAWK Agent Deployment Log

## Production Environment
- **Server IP**: 13.222.100.183 (AWS EC2)
- **Domain**: https://13-222-100-183.nip.io
- **SSL**: Let's Encrypt certificates
- **Web Server**: nginx
- **Frontend Path**: /var/www/13-222-100-183.nip.io/
- **Backend Path**: /home/ubuntu/hedge-agent/hedge-agent/

## Current Deployment Process

### Prerequisites
1. SSH Key: `agent_hawk.pem` (in project root)
2. Node.js environment for Angular builds
3. Access to production server

### Single Deployment Command
```bash
# Deploy everything
./deploy.sh

# Deploy only frontend
./deploy.sh frontend

# Deploy only backend
./deploy.sh backend
```

## Recent Deployment History

### 2025-09-19 - Delete Confirmation Dialog Fix
**Problem**: Delete confirmation dialog not appearing in conversation management
**Build Hash**: 27aa246b2d30bdd7
**Component**: 875.bf05894ed2c33abc.js

**Detailed Steps Taken**:

1. **Issue Identification**:
   - User reported dialog implemented but not appearing
   - Found event propagation conflicts
   - Document click listener interfering with dialog display

2. **Code Fixes Applied**:
   ```typescript
   // Fixed event propagation
   (click)="confirmDeleteConversation(conversation.conversation_id, conversation.title); $event.stopPropagation()"

   // Fixed document click guard
   if (this.activeConversationMenu && !this.showDeleteConfirmation) {
     this.activeConversationMenu = null;
   }

   // Added explicit z-index
   style="z-index: 9999 !important;"
   ```

3. **Build Process**:
   ```bash
   npm run build:prod
   # Generated: Build at: 2025-09-19T02:24:10.609Z - Hash: 27aa246b2d30bdd7
   # Component: 875.bf05894ed2c33abc.js (112.08 kB)
   ```

4. **Deployment to Cloud**:
   ```bash
   ./deploy_frontend_final.sh
   # Created frontend-deployment.tar.gz
   # Uploaded via SCP to /tmp/
   # Extracted to /var/www/13-222-100-183.nip.io/
   # Set permissions: www-data:www-data
   # Reloaded nginx
   ```

5. **Critical Issue Found**:
   - nginx configuration had `root /var/www/html;`
   - Files were deployed to `/var/www/13-222-100-183.nip.io/`
   - **Mismatch prevented new files from being served**

6. **Nginx Configuration Fix**:
   ```bash
   # Fixed nginx root path
   sudo sed -i 's|root /var/www/html;|root /var/www/13-222-100-183.nip.io;|' /etc/nginx/sites-available/13-222-100-183.nip.io
   sudo nginx -t && sudo systemctl reload nginx
   ```

7. **Verification**:
   ```bash
   curl -I https://13-222-100-183.nip.io/875.bf05894ed2c33abc.js
   # HTTP/1.1 200 OK
   # Content-Type: application/javascript
   # Content-Length: 112080
   # Last-Modified: Fri, 19 Sep 2025 02:24:41 GMT
   ```

**Result**: Delete confirmation dialog now works correctly in production

### 2025-09-19 - Deployment Cleanup
**Problem**: 20+ deployment scripts causing confusion
**Solution**: Consolidated to single `deploy.sh` script

**Actions Taken**:
1. Moved old scripts to `old_deploy_scripts/` folder
2. Created unified `deploy.sh` with frontend/backend/all options
3. Documented clear deployment pathway
4. Updated project documentation

## Environment Variables (Production)
```bash
SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"
```

## Services Running on Production
- **Port 443**: nginx (HTTPS frontend + proxies)
- **Port 8004**: Main backend API
- **Port 8009**: MCP Data Server
- **Port 8010**: Dify Adapter

## nginx Configuration
Location: `/etc/nginx/sites-available/13-222-100-183.nip.io`
- SSL termination with Let's Encrypt
- Static file serving from `/var/www/13-222-100-183.nip.io/`
- API proxy to localhost:8004
- MCP proxy to localhost:8009
- Dify proxy to localhost:8010

## Troubleshooting Guide

### Frontend Not Updating
1. Check if files deployed to correct path: `/var/www/13-222-100-183.nip.io/`
2. Verify nginx root path matches deployment path
3. Check file permissions: `www-data:www-data`
4. Test direct JS file access: `curl -I https://13-222-100-183.nip.io/[component].js`
5. Clear browser cache: Ctrl+F5

### Backend Issues
1. Check if process is running: `ps aux | grep mcp_server`
2. Check logs: `tail -f mcp_v2.log`
3. Verify environment variables are set
4. Test health endpoint: `curl https://13-222-100-183.nip.io/mcp/health`

## Security Notes
- SSH key `agent_hawk.pem` contains private credentials
- Supabase service role key in environment variables
- SSL certificates auto-renew via Let's Encrypt
- CORS configured for specific origins only