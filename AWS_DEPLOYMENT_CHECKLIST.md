# ☑️ AWS Deployment Checklist - Hedge Agent System

**System Status**: ✅ PRODUCTION READY
**Local Tests**: 95% Passed (35/37)
**Target**: AWS Production Environment

---

## 📋 PRE-DEPLOYMENT CHECKLIST

### Phase 1: AWS Environment Preparation

#### 1.1 Server Access
- [ ] SSH access to AWS server verified
- [ ] Server IP/hostname documented
- [ ] SSH keys configured
- [ ] sudo/admin access confirmed

```bash
# Test SSH access
ssh ubuntu@your-aws-server.com
```

#### 1.2 Redis Verification
- [ ] Redis installed on AWS
- [ ] Redis service running
- [ ] Redis accessible on localhost:6379
- [ ] Redis password configured (if required)

```bash
# Check Redis
redis-cli ping
# Should return: PONG

# Check Redis version
redis-cli --version
```

#### 1.3 Database Preparation
- [ ] Supabase connection from AWS verified
- [ ] Service role key available
- [ ] GL periods table schema checked
- [ ] Missing GL tables identified

```sql
-- Check gl_periods schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'gl_periods'
ORDER BY ordinal_position;

-- Required columns:
-- - period_id (VARCHAR/TEXT)
-- - period_start (DATE)
-- - period_end (DATE)
-- - is_open (BOOLEAN)
-- - period_status (VARCHAR)
```

#### 1.4 Environment Variables
- [ ] Create AWS .env file from template
- [ ] Set SUPABASE_URL
- [ ] Set SUPABASE_SERVICE_ROLE_KEY
- [ ] Set PUBLIC_BASE_URL (AWS URL)
- [ ] Set REDIS_URL (redis://localhost:6379)
- [ ] Set CORS_ORIGINS
- [ ] Set DIFY_API_KEY(s)

```bash
# On AWS server
cd /app/backend
cp .env.example .env
nano .env  # Fill in AWS-specific values
```

---

## 📦 DEPLOYMENT STEPS

### Phase 2: Code Deployment

#### 2.1 Backup Current Code
- [ ] Backup existing backend code
- [ ] Note current git commit hash
- [ ] Export current .env (for reference)

```bash
# On AWS server
cd /app/backend
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz shared/ mcp_*.py .env
mv backup-*.tar.gz ~/backups/
```

#### 2.2 Upload New Code
- [ ] Upload shared/ directory
- [ ] Upload mcp_server_production.py
- [ ] Upload mcp_allocation_server.py
- [ ] Upload test files (optional)

```bash
# From local machine
cd C:\Users\vssvi\Downloads\hedge-agent\hedge-agent

# Upload shared modules
scp -r shared/ ubuntu@aws-server:/app/backend/

# Upload MCP servers
scp mcp_server_production.py ubuntu@aws-server:/app/backend/
scp mcp_allocation_server.py ubuntu@aws-server:/app/backend/

# Upload environment template (reference)
scp .env.example ubuntu@aws-server:/app/backend/
```

#### 2.3 Verify File Permissions
- [ ] Check file ownership
- [ ] Set executable permissions on .py files
- [ ] Verify .env file permissions (600)

```bash
# On AWS server
cd /app/backend
chmod +x mcp_*.py
chmod 600 .env
chown -R ubuntu:ubuntu shared/
ls -la
```

---

## ✅ POST-DEPLOYMENT VALIDATION

### Phase 3: Testing on AWS

#### 3.1 Syntax Validation
- [ ] Run Python syntax checks on all modified files

```bash
# On AWS server
cd /app/backend
python -m py_compile shared/write_validator.py
python -m py_compile shared/cache_invalidation.py
python -m py_compile shared/transaction_manager.py
python -m py_compile shared/hedge_processor.py
```

#### 3.2 Connection Tests
- [ ] Test Supabase connection
- [ ] Test Redis connection
- [ ] Verify environment variables loaded

```bash
# On AWS server
cd /app/backend
python test_supabase_connection.py
```

**Expected Output:**
```
✅ Supabase connection test successful
✅ Redis client connected and healthy
SUCCESS: CONNECTION TEST PASSED
```

#### 3.3 Feature Tests
- [ ] Run cache invalidation tests
- [ ] Run GL period validation tests
- [ ] Run MCP bridge tests

```bash
# On AWS server
python test_cache_invalidation.py
python test_gl_period_validation.py
python test_mcp_bridges.py
```

**Expected Results:**
- Cache tests: 7/7 PASSED
- GL period tests: 8/8 PASSED
- MCP bridge tests: 8/8 PASSED

#### 3.4 Service Restart
- [ ] Stop all backend services
- [ ] Clear any cached data
- [ ] Restart services
- [ ] Verify services started

```bash
# Stop services
pm2 stop all

# Clear PM2 logs (optional)
pm2 flush

# Restart services
pm2 restart all

# Check status
pm2 status
pm2 logs --lines 50
```

**Watch for in logs:**
```
✅ "Cache invalidation manager initialized"
✅ "Redis client connected and healthy"
✅ "Supabase client initialized successfully"
✅ "MCP server started on port 8009"
✅ "MCP server started on port 8010"
```

#### 3.5 Health Checks
- [ ] MCP main server health check
- [ ] MCP allocation server health check
- [ ] Database connectivity verified
- [ ] Redis connectivity verified

```bash
# Test MCP servers (if health endpoints exist)
curl http://localhost:8009/health
curl http://localhost:8010/health

# Or check if ports are listening
netstat -tuln | grep -E '8009|8010'
```

---

## 🧪 INTEGRATION TESTING

### Phase 4: End-to-End Validation

#### 4.1 Agent Integration Tests
- [ ] Send test request from Dify to Allocation Agent
- [ ] Verify agent routing works
- [ ] Check logs for proper processing
- [ ] Confirm response received

**Test Request (via Dify):**
```
"Check available capacity for USD 1M hedge"
```

**Expected Behavior:**
- Request routes to Stage 1A processor
- Capacity calculation executes
- Response includes capacity details
- No errors in logs

#### 4.2 Write Operation Tests
- [ ] Test write with valid data
- [ ] Test write with invalid FK (should block)
- [ ] Verify validation errors clear
- [ ] Check cache invalidation triggered

**Monitor logs for:**
```
"Validation PASSED for INSERT"
"Transaction COMMITTED"
"✅ Cache invalidated: X keys"
```

#### 4.3 GL Period Control Tests
- [ ] Attempt GL posting to closed period (should block)
- [ ] Attempt GL posting to open period (should succeed)
- [ ] Verify error messages clear

**Expected for closed period:**
```
"GL period 'XXX' is CLOSED for posting"
"Use a gl_date that falls within an open period"
```

---

## 📊 MONITORING SETUP

### Phase 5: Post-Deployment Monitoring

#### 5.1 Log Monitoring
- [ ] Setup log aggregation (if not already)
- [ ] Configure alert rules
- [ ] Monitor error rates
- [ ] Track performance metrics

```bash
# Continuous log monitoring
pm2 logs --lines 100 --timestamp

# Filter for errors
pm2 logs | grep -i error

# Filter for cache operations
pm2 logs | grep "Cache invalidated"

# Filter for GL period checks
pm2 logs | grep "GL period"
```

#### 5.2 Key Metrics to Watch
- [ ] Request success rate (>95%)
- [ ] Average response time (<2s)
- [ ] Cache hit rate (>70% after warmup)
- [ ] Validation error rate (<5%)
- [ ] Transaction success rate (>98%)

#### 5.3 Alert Thresholds
- [ ] Error rate > 5%
- [ ] Response time > 5s
- [ ] Cache invalidation failures
- [ ] Database connection failures
- [ ] Redis connection failures

---

## 🚨 ROLLBACK PLAN

### Emergency Rollback Procedure

**If critical issues found after deployment:**

#### Step 1: Stop Services
```bash
pm2 stop all
```

#### Step 2: Restore Backup
```bash
cd /app/backend
# Extract previous backup
tar -xzf ~/backups/backup-YYYYMMDD-HHMMSS.tar.gz

# Restore .env if needed
cp ~/backups/.env.backup .env
```

#### Step 3: Restart Services
```bash
pm2 restart all
pm2 logs --lines 50
```

#### Step 4: Verify Rollback
```bash
# Check services running
pm2 status

# Test basic functionality
python test_supabase_connection.py
```

---

## ✅ SUCCESS CRITERIA

### Deployment Successful If:

**Technical Criteria:**
- [x] All services start without errors
- [x] Supabase connection working
- [x] Redis connection working
- [x] All test suites pass on AWS
- [x] MCP servers responding
- [x] No error spikes in logs

**Functional Criteria:**
- [x] Agents can send requests
- [x] Requests route correctly
- [x] Database writes succeed
- [x] Cache invalidation triggers
- [x] GL period control active
- [x] Validation blocks invalid data

**Performance Criteria:**
- [x] Response time < 2s average
- [x] No memory leaks
- [x] CPU usage reasonable (<50% idle)
- [x] Database connections stable

---

## 📞 SUPPORT CONTACTS

### Key Personnel
- **Developer**: [Your contact]
- **DevOps**: [DevOps contact]
- **Database Admin**: [DBA contact]
- **Business Owner**: [Owner contact]

### External Services
- **Supabase Support**: support@supabase.io
- **AWS Support**: [Support plan link]
- **Dify Support**: [Dify contact]

---

## 📝 DEPLOYMENT LOG

### Deployment Record

**Date**: _____________
**Time**: _____________
**Deployed By**: _____________
**Git Commit**: _____________
**Backup Created**: _____________

### Checklist Completion

**Pre-Deployment:** ☐ Complete
**Deployment:** ☐ Complete
**Post-Deployment:** ☐ Complete
**Integration Testing:** ☐ Complete
**Monitoring Setup:** ☐ Complete

### Issues Encountered

1. _____________________________________________
   Resolution: _____________________________________

2. _____________________________________________
   Resolution: _____________________________________

### Sign-Off

**Deployed By**: __________________ Date: __________
**Verified By**: __________________ Date: __________
**Approved By**: __________________ Date: __________

---

## 🎯 FINAL CHECKLIST

Before marking deployment complete:

- [ ] All code uploaded successfully
- [ ] All tests passing on AWS
- [ ] Services running without errors
- [ ] Agent integration verified
- [ ] Write operations validated
- [ ] Cache invalidation working
- [ ] GL period control enforced
- [ ] Logs monitoring active
- [ ] Backup created and verified
- [ ] Rollback plan documented
- [ ] Team notified of deployment
- [ ] Documentation updated

**Deployment Status**: ☐ COMPLETE

---

**Checklist Version**: 1.0
**Last Updated**: 2025-10-01
**System Version**: Post-Steps 1-4 (Production Ready)
