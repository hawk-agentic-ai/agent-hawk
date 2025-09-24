#  MANUAL DEPLOYMENT GUIDE - Unified Smart Backend v5.0.0

**Deploy to AWS Server: 3.91.170.95**

---

##  **STEP-BY-STEP DEPLOYMENT**

### **Step 1: Copy Files to Server**

Open Command Prompt in the hedge-agent folder and run:

```cmd
scp -i agent_hawk.pem unified_smart_backend.py ubuntu@3.91.170.95:/home/ubuntu/
scp -i agent_hawk.pem payloads.py ubuntu@3.91.170.95:/home/ubuntu/
scp -i agent_hawk.pem prompt_intelligence_engine.py ubuntu@3.91.170.95:/home/ubuntu/
scp -i agent_hawk.pem smart_data_extractor.py ubuntu@3.91.170.95:/home/ubuntu/
scp -i agent_hawk.pem hedge_management_cache_config.py ubuntu@3.91.170.95:/home/ubuntu/
```

### **Step 2: Connect to Server**

```cmd
ssh -i agent_hawk.pem ubuntu@3.91.170.95
```

### **Step 3: Install Dependencies**

Once connected to the server:

```bash
# Install Python dependencies
pip3 install fastapi uvicorn[standard] redis supabase httpx python-multipart pydantic

# Verify installation
python3 -c "import fastapi, uvicorn, redis, supabase, httpx; print('All dependencies installed successfully')"
```

### **Step 4: Set Environment Variables**

```bash
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
export DIFY_API_KEY='app-juJAFQ9a8QAghx5tACyTvqqG'
```

### **Step 5: Stop Existing Backends**

```bash
# Stop any existing backend processes
pkill -f "python.*backend" || true
pkill -f "uvicorn" || true

# Check if any are still running
ps aux | grep python
```

### **Step 6: Start Unified Smart Backend**

```bash
# Start the backend in background
nohup python3 unified_smart_backend.py > backend.log 2>&1 &

# Get the process ID
echo "Backend started with PID: $!"

# Check if it's running
ps aux | grep unified_smart_backend
```

### **Step 7: Test the Deployment**

```bash
# Wait a few seconds for startup
sleep 5

# Test health endpoint
curl http://localhost:8004/health

# Test from outside (in new terminal/command prompt)
curl http://3.91.170.95:8004/health
```

---

##  **VERIFICATION TESTS**

### **Health Check:**
```bash
curl http://3.91.170.95:8004/health | python3 -m json.tool
```
Expected: `{"status": "healthy", ...}`

### **System Status:**
```bash
curl http://3.91.170.95:8004/system/status | python3 -m json.tool
```

### **Sample Processing Test:**
```bash
curl -X POST "http://3.91.170.95:8004/hawk-agent/process-prompt" \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Check CNY hedge capacity", "template_category": "hedge_accounting", "currency": "CNY"}'
```

---

##  **MONITORING COMMANDS**

### **View Logs:**
```bash
tail -f backend.log
```

### **Check Process:**
```bash
ps aux | grep unified_smart_backend
```

### **Stop Backend:**
```bash
pkill -f unified_smart_backend
```

### **Restart Backend:**
```bash
pkill -f unified_smart_backend
nohup python3 unified_smart_backend.py > backend.log 2>&1 &
```

---

##  **SECURITY GROUP CONFIGURATION**

Ensure AWS Security Group allows:
- **Inbound**: Port 8004 from your IP addresses
- **Outbound**: Port 443 (HTTPS) for Dify API calls
- **SSH**: Port 22 for management

---

##  **SUCCESS INDICATORS**

 **Health endpoint returns**: `{"status": "healthy"}`
 **Process running**: `unified_smart_backend.py` in process list  
 **Port listening**: `netstat -tlnp | grep 8004`
 **Logs show**: "Uvicorn running on http://0.0.0.0:8004"
 **External access**: Health check works from outside server

---

##  **TROUBLESHOOTING**

### **If Connection Fails:**
```bash
# Check if port is open
sudo netstat -tlnp | grep 8004

# Check firewall
sudo ufw status

# Check logs
tail -20 backend.log
```

### **If Dependencies Fail:**
```bash
# Update pip
python3 -m pip install --upgrade pip

# Install with --user flag
pip3 install --user fastapi uvicorn[standard] redis supabase httpx python-multipart pydantic
```

### **If Import Errors:**
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Verify files are uploaded
ls -la *.py
```

---

##  **DEPLOYMENT COMPLETE**

Once all steps are complete, your **Unified Smart Backend v5.0.0** will be running on:

** Production URL**: `http://3.91.170.95:8004`
** Main Endpoint**: `http://3.91.170.95:8004/hawk-agent/process-prompt`
** Health Check**: `http://3.91.170.95:8004/health`
** API Docs**: `http://3.91.170.95:8004/docs`

### **Next Steps:**
1. Update Angular HAWK Agent to use production URL
2. Test all template categories
3. Monitor performance and cache stats
4. Enjoy sub-2 second responses! 

---

*Unified Smart Backend v5.0.0 - Production Ready* 