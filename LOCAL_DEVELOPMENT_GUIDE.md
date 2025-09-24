# Local Development Setup Guide - Hawk Agent

## 🎯 Overview

This guide will help you set up the complete Hawk Agent development environment on your local machine, including frontend (Angular), backend (Python FastAPI), and all required services.

## 🔧 Prerequisites

### Required Software
```bash
# Install these tools first:
- Python 3.11+ (https://python.org/downloads/)
- Node.js 18+ (https://nodejs.org/)
- Git (https://git-scm.com/)
- VS Code or your preferred IDE
```

### System Requirements
```
- RAM: 8GB minimum, 16GB recommended
- Storage: 5GB free space
- OS: Windows 10+, macOS 10.15+, Ubuntu 20.04+
```

## 📥 Project Setup

### 1. Clone the Repository
```bash
# Clone from GitHub
git clone https://github.com/hawk-agentic-ai/agent-hawk.git
cd agent-hawk

# Or if you already have it downloaded
cd path/to/your/hedge-agent
```

### 2. Environment Configuration
```bash
# The .env file should already exist with production settings
# For local development, create a .env.local file with overrides:

# Create .env.local (optional - for local-specific settings)
cp .env .env.local
```

Edit `.env.local` if you want different local settings:
```bash
# Local Development Overrides (optional)
CORS_ORIGINS=http://localhost:4200,http://localhost:3000,https://cloud.dify.ai
PUBLIC_BASE_URL=http://localhost:8004/

# Keep production Supabase settings (they work for local dev too)
SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
SUPABASE_SERVICE_ROLE_KEY=[use-the-key-from-main-.env-file]
```

## 🐍 Python Backend Setup

### 1. Create Virtual Environment
```bash
# Create virtual environment
python -m venv hedge_agent_env

# Activate virtual environment

# Windows:
hedge_agent_env\Scripts\activate

# macOS/Linux:
source hedge_agent_env/bin/activate

# Verify activation (should show virtual environment name)
which python  # Should point to virtual env
```

### 2. Install Python Dependencies
```bash
# Install all required packages
pip install --upgrade pip
pip install -r requirements.txt

# If you get dependency conflicts, try:
pip install --no-deps -r requirements.txt
pip install fastapi uvicorn supabase httpx redis
```

### 3. Test Python Setup
```bash
# Test basic imports
python -c "
import fastapi
import supabase
import httpx
print('✅ All core dependencies installed successfully')
"

# Test Supabase connection
python -c "
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if url and key:
    client = create_client(url, key)
    result = client.table('hedge_funds').select('count').execute()
    print('✅ Supabase connection successful')
else:
    print('❌ Missing Supabase environment variables')
"
```

### 4. Start Backend Services

#### Option A: Start All Services (Recommended)
```bash
# Terminal 1: Main Smart Backend (Port 8004)
python unified_smart_backend.py

# Terminal 2: MCP Server Production (Port 8009)
python mcp_server_production.py

# Terminal 3: MCP Allocation Server (Port 8010)
python mcp_allocation_server.py
```

#### Option B: Start Individual Services
```bash
# Just the main backend (most common for development)
python unified_smart_backend.py

# Or using uvicorn with auto-reload
uvicorn unified_smart_backend:app --reload --port 8004 --host 0.0.0.0
```

### 5. Verify Backend Services
```bash
# Test main backend
curl http://localhost:8004/api/health

# Expected response:
# {"status":"healthy","version":"5.0.0","services":{"supabase":"connected"}}

# Test MCP server (if running)
curl -X POST http://localhost:8009/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list"}'
```

## 🅰️ Angular Frontend Setup

### 1. Install Node Dependencies
```bash
# Install all npm packages
npm install

# If you get errors, try:
npm install --legacy-peer-deps

# Or clear cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### 2. Start Development Server
```bash
# Start Angular dev server (Port 4200)
npm run start

# Or alternatively
npm run dev

# The application will open at: http://localhost:4200
```

### 3. Verify Frontend
```bash
# The Angular app should load with:
- Dashboard with hedge fund metrics
- HAWK Agent interface
- Navigation to different sections

# Check browser console for any errors
# Open DevTools (F12) and check Console tab
```

## 🔗 Full System Test

### 1. Complete System Verification
```bash
# With all services running, test the complete flow:

# 1. Backend health check
curl http://localhost:8004/api/health

# 2. Frontend loading
# Visit: http://localhost:4200

# 3. HAWK Agent test (through the UI)
# - Go to HAWK Agent page
# - Submit a test query like "Show me fund utilization"
# - Should get a streaming response from the backend
```

### 2. Test Service Integration
```bash
# Test backend API directly
curl -X POST http://localhost:8004/api/hawk/process \
  -H "Content-Type: application/json" \
  -d '{
    "instruction_type": "query",
    "user_prompt": "Show system status",
    "stage": "stage_1a"
  }'
```

## 🐛 Troubleshooting

### Common Python Issues

#### Issue: `ModuleNotFoundError`
```bash
# Solution: Install missing package
pip install [package-name]

# Or reinstall all requirements
pip install -r requirements.txt --force-reinstall
```

#### Issue: Port already in use
```bash
# Find process using port
netstat -ano | findstr :8004  # Windows
lsof -i :8004                 # macOS/Linux

# Kill process
taskkill /PID [PID] /F        # Windows
kill -9 [PID]                # macOS/Linux

# Or use different port
uvicorn unified_smart_backend:app --port 8005
```

#### Issue: Supabase connection timeout
```bash
# Check environment variables
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY

# Test internet connection
ping ladviaautlfvpxuadqrb.supabase.co

# Verify .env file is loaded
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('URL:', os.getenv('SUPABASE_URL'))
print('Key exists:', bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY')))
"
```

### Common Node.js Issues

#### Issue: `npm install` fails
```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall with legacy peer deps
npm install --legacy-peer-deps

# Or use yarn instead
yarn install
```

#### Issue: Angular compilation errors
```bash
# Clear Angular cache
ng cache clean

# Update Angular CLI
npm install -g @angular/cli@latest

# Restart dev server
npm run start
```

### Network and CORS Issues

#### Issue: CORS errors in browser
```bash
# Check CORS_ORIGINS in .env
CORS_ORIGINS=http://localhost:4200,http://localhost:3000

# Or start backend with CORS disabled for development
python unified_smart_backend.py --disable-cors
```

#### Issue: Frontend can't reach backend
```bash
# Check if backend is running on correct port
curl http://localhost:8004/api/health

# The proxy.conf.json file should already exist with:
{
  "/api/*": {
    "target": "http://localhost:8004",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/mcp/*": {
    "target": "http://localhost:8009",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/dify/*": {
    "target": "http://localhost:8010",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  }
}

# Angular will automatically use proxy.conf.json when running
npm run start
```

## 🚀 Development Workflow

### Daily Development Routine
```bash
# 1. Activate Python environment
source hedge_agent_env/bin/activate  # macOS/Linux
# or
hedge_agent_env\Scripts\activate     # Windows

# 2. Start backend services
python unified_smart_backend.py

# 3. In new terminal: Start frontend
npm run start

# 4. Start coding!
# - Backend changes: auto-reload with uvicorn --reload
# - Frontend changes: auto-reload with ng serve
```

### Testing Changes
```bash
# Test backend changes
curl http://localhost:8004/api/health

# Test frontend changes
# Visit http://localhost:4200 and test UI

# Test integration
# Use HAWK Agent UI to submit queries
```

### Debugging Tips
```bash
# Backend debugging
# Add print statements or use logging:
import logging
logging.basicConfig(level=logging.DEBUG)

# Frontend debugging
# Use browser DevTools (F12)
# Check Console, Network, and Elements tabs

# Check backend logs in terminal where Python is running
```

## 📚 Additional Resources

### Useful Commands
```bash
# Python environment info
python --version
pip list
pip show [package-name]

# Node.js environment info
node --version
npm --version
npm list

# Git commands
git status
git pull origin main
git log --oneline -10
```

### Development Tools
```bash
# Recommended VS Code extensions:
- Python
- Angular Language Service
- REST Client
- GitLens
- Thunder Client (for API testing)
```

### API Testing Tools
```bash
# Install useful tools for API testing:
pip install httpie  # Better curl alternative

# Test API with httpie:
http GET localhost:8004/api/health
http POST localhost:8004/api/hawk/process instruction_type=query user_prompt="test"
```

## 🔄 Keeping Up to Date

### Sync with Production
```bash
# Pull latest changes
git pull origin main

# Update Python dependencies
pip install -r requirements.txt --upgrade

# Update Node dependencies
npm update

# Restart services
# Kill existing processes and restart them
```

### Environment Variables Updates
```bash
# If .env is updated, restart backend services
# The backend loads .env on startup
```

---

## ✅ Success Checklist

After following this guide, you should have:

- [ ] Python 3.11+ installed and virtual environment activated
- [ ] All Python dependencies installed successfully
- [ ] Node.js 18+ and npm packages installed
- [ ] Environment variables configured (`.env` file)
- [ ] Backend service running on http://localhost:8004
- [ ] Frontend running on http://localhost:4200
- [ ] Supabase connection working
- [ ] HAWK Agent UI responding to queries
- [ ] No CORS errors in browser console

If any item is not working, refer to the Troubleshooting section above.

---

*Last Updated: September 24, 2025*
*Version: 1.0.0*
*Local Development Guide*