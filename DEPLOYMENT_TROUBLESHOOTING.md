# Deployment Troubleshooting Guide - Hawk Agent

## 🎯 Overview

This guide provides comprehensive troubleshooting steps for common deployment issues encountered when managing the Hawk Agent system across local development and AWS production environments.

## 🏗️ System Architecture Quick Reference

```
Production Environment: 3.238.163.106
├── Nginx (Port 80/443) → SSL Termination
├── Angular App (Port 8000) → 4 worker processes
├── Smart Backend (Port 8004) → Core API services
├── MCP Server (Port 8009) → Model Context Protocol
└── MCP Allocation (Port 8010) → Fund management
```

## 🚨 Common Issues & Solutions

### 1. Service Connection Issues

#### **Issue**: Services not responding on expected ports
```bash
# Symptom
curl: (7) Failed to connect to 3.238.163.106 port 8009: Connection refused
```

**Diagnosis Steps:**
```bash
# Check service status
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "pm2 status"

# Check port bindings
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "netstat -tulpn | grep :800"

# Check process list
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "ps aux | grep python"
```

**Solutions:**
```bash
# Restart specific service
pm2 restart mcp_server_production

# Restart all services
pm2 restart all

# If services won't start, check logs
pm2 logs mcp_server_production --lines 50

# Force kill and restart
pm2 delete mcp_server_production
pm2 start mcp_server_production.py --name mcp_server_production
```

#### **Issue**: SSL/HTTPS certificate problems
```bash
# Symptom
curl: (60) SSL certificate problem: certificate has expired
```

**Solution:**
```bash
# Check certificate status
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "sudo certbot certificates"

# Renew certificates
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "sudo certbot renew --dry-run"
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "sudo certbot renew"

# Reload nginx
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "sudo systemctl reload nginx"
```

### 2. Database Connection Issues

#### **Issue**: Supabase connection failures
```python
# Symptom
supabase.exceptions.APIError: Connection timeout
```

**Diagnosis:**
```bash
# Test database connectivity
python3 -c "
import os
from supabase import create_client
client = create_client(
    'https://ladviaautlfvpxuadqrb.supabase.co',
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)
print('Database connection:', client.table('hedge_funds').select('count').execute())
"
```

**Solutions:**
```bash
# Check environment variables
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "env | grep SUPABASE"

# Update environment variables
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='your-service-key'
pm2 restart all
"

# Test connection from production
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "
cd /home/ubuntu/hedge-agent/production/backend/
python3 -c 'from shared.data_extractor import test_supabase_connection; test_supabase_connection()'
"
```

### 3. File Synchronization Issues

#### **Issue**: Local and cloud files out of sync
```bash
# Symptom
git status shows different files between environments
```

**Diagnosis:**
```bash
# Check git status on both environments
git status
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "cd /home/ubuntu/hedge-agent && git status"

# Compare file checksums
md5sum unified_smart_backend.py
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "cd /home/ubuntu/hedge-agent/production/backend && md5sum unified_smart_backend.py"
```

**Solutions:**
```bash
# Method 1: Pull from cloud to local
scp -i agent_tmp.pem ubuntu@3.238.163.106:/home/ubuntu/hedge-agent/production/backend/unified_smart_backend.py ./

# Method 2: Push from local to cloud
scp -i agent_tmp.pem ./unified_smart_backend.py ubuntu@3.238.163.106:/home/ubuntu/hedge-agent/production/backend/

# Method 3: Force sync via Git
git add .
git commit -m "Sync local changes"
git push origin main

ssh -i agent_tmp.pem ubuntu@3.238.163.106 "
cd /home/ubuntu/hedge-agent
git pull origin main
pm2 restart all
"
```

### 4. Memory and Performance Issues

#### **Issue**: High memory usage or slow responses
```bash
# Symptom
Response times > 5 seconds, out of memory errors
```

**Diagnosis:**
```bash
# Check memory usage
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "free -h"

# Check disk usage
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "df -h"

# Monitor process memory
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "top -p \$(pgrep -f python)"

# Check PM2 memory usage
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "pm2 monit"
```

**Solutions:**
```bash
# Restart services to clear memory leaks
pm2 restart all

# Clear system cache
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Optimize PM2 configuration
pm2 start mcp_server_production.py --max-memory-restart 500M
```

### 5. CORS and Security Issues

#### **Issue**: CORS errors blocking frontend requests
```javascript
// Symptom
Access to fetch at 'https://3-238-163-106.nip.io:8009/' from origin 'https://cloud.dify.ai'
has been blocked by CORS policy
```

**Solution:**
```python
# Check CORS configuration in Python services
# In unified_smart_backend.py or mcp_server_production.py

ALLOWED_ORIGINS = [
    "https://cloud.dify.ai",
    "https://3-238-163-106.nip.io",
    "http://localhost:4200",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

```bash
# Update and restart services
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "
cd /home/ubuntu/hedge-agent/production/backend
# Edit CORS settings
pm2 restart all
"
```

### 6. GitHub and Git Issues

#### **Issue**: Git authentication failures
```bash
# Symptom
git@github.com: Permission denied (publickey)
```

**Solutions:**
```bash
# Check SSH key
ssh -T git@github.com

# Add SSH key if missing
ssh-add ~/.ssh/agent_tmp.pem  # or appropriate key

# Update git remote URL
git remote set-url origin git@github.com:hawk-agentic-ai/agent-hawk.git

# Or use HTTPS with token
git remote set-url origin https://github.com/hawk-agentic-ai/agent-hawk.git
```

#### **Issue**: Git push rejection
```bash
# Symptom
! [rejected] main -> main (fetch first)
```

**Solutions:**
```bash
# Force push (if safe)
git push --force-with-lease origin main

# Or merge first
git pull origin main --rebase
git push origin main
```

## 🔧 Deployment Commands Reference

### Health Checks
```bash
# Complete system health check
curl -f https://3-238-163-106.nip.io/api/health || echo "Main API DOWN"
curl -f https://3-238-163-106.nip.io:8009/ || echo "MCP Server DOWN"
curl -f https://3-238-163-106.nip.io:8010/ || echo "Allocation Server DOWN"

# Service status check
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "pm2 status | grep -E '(online|stopped|errored)'"
```

### Quick Deployment
```bash
# Full deployment pipeline
git add . && git commit -m "Deploy: $(date)" && git push origin main

ssh -i agent_tmp.pem ubuntu@3.238.163.106 "
cd /home/ubuntu/hedge-agent &&
git pull origin main &&
pm2 restart all &&
sleep 5 &&
curl -f https://3-238-163-106.nip.io/api/health
"
```

### Emergency Recovery
```bash
# If all services are down
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "
pm2 kill
pm2 start /home/ubuntu/hedge-agent/production/backend/unified_smart_backend.py --name unified_smart_backend
pm2 start /home/ubuntu/hedge-agent/production/backend/mcp_server_production.py --name mcp_server_production
pm2 start /home/ubuntu/hedge-agent/production/backend/mcp_allocation_server.py --name mcp_allocation_server
pm2 save
sudo systemctl restart nginx
"
```

## 🎯 Monitoring & Alerts

### Log Monitoring
```bash
# Real-time log monitoring
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "pm2 logs --lines 20 --raw | grep -E '(ERROR|WARN|Exception)'"

# Nginx error logs
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "sudo tail -f /var/log/nginx/error.log"

# System logs
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "sudo journalctl -u nginx -f"
```

### Performance Monitoring
```bash
# CPU and Memory usage
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "
echo 'CPU Usage:' && top -bn1 | grep 'Cpu(s)' &&
echo 'Memory Usage:' && free -h &&
echo 'Disk Usage:' && df -h /
"

# Process monitoring
ssh -i agent_tmp.pem ubuntu@3.238.163.106 "ps aux | grep python | grep -v grep"
```

## 🛠️ Debugging Tools

### Python Debugging
```python
# Add debugging to Python services
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    # Your code here
    pass
except Exception as e:
    logger.error(f"Error occurred: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    raise
```

### Network Debugging
```bash
# Test specific ports
telnet 3.238.163.106 8009

# Check SSL certificate
openssl s_client -connect 3-238-163-106.nip.io:443 -servername 3-238-163-106.nip.io

# DNS resolution
nslookup 3-238-163-106.nip.io
dig 3-238-163-106.nip.io

# Network connectivity
ping 3.238.163.106
traceroute 3.238.163.106
```

### Database Debugging
```sql
-- Check database connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Monitor slow queries
SELECT query, mean_time, calls FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 📋 Troubleshooting Checklist

### Pre-Deployment Checklist
- [ ] Local changes committed and pushed to GitHub
- [ ] Environment variables properly configured
- [ ] SSH key access to production server confirmed
- [ ] Database connectivity tested
- [ ] All required dependencies installed

### Post-Deployment Checklist
- [ ] All PM2 processes showing as 'online'
- [ ] Health endpoints responding successfully
- [ ] Nginx status is active and running
- [ ] SSL certificates are valid and not expired
- [ ] Database connections established
- [ ] Log files show no critical errors

### Emergency Response Checklist
- [ ] Identify failing service(s)
- [ ] Check recent changes in Git history
- [ ] Review error logs for root cause
- [ ] Implement quick fix or rollback
- [ ] Verify system functionality restored
- [ ] Document incident and resolution

## 🔄 Common Recovery Procedures

### Service Recovery
```bash
# Restart individual service
pm2 restart service_name

# Full system restart
sudo reboot

# Reset PM2 processes
pm2 kill
pm2 resurrect
```

### Database Recovery
```bash
# Test database connection
python3 -c "from shared.data_extractor import test_connection; test_connection()"

# Clear connection pools
pm2 restart all

# Check database locks
SELECT * FROM pg_locks WHERE NOT granted;
```

### File System Recovery
```bash
# Check disk space
df -h

# Clean temporary files
sudo apt-get autoclean
sudo apt-get autoremove

# Clean PM2 logs
pm2 flush
```

## 📞 Support Escalation

### Contact Information
- **GitHub Issues**: https://github.com/hawk-agentic-ai/agent-hawk/issues
- **AWS Support**: Enterprise support for infrastructure issues
- **Supabase Support**: Database-related issues

### Escalation Criteria
1. **Critical**: Complete system outage > 5 minutes
2. **High**: Single service down > 15 minutes
3. **Medium**: Performance degradation > 30 minutes
4. **Low**: Non-critical features affected

---

*Last Updated: September 24, 2025*
*Version: 1.0.0*
*Emergency Hotline: GitHub Issues*