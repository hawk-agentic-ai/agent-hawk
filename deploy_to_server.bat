@echo off
echo ============================================================
echo 🚀 DEPLOYING UNIFIED SMART BACKEND v5.0.0 TO AWS SERVER
echo ============================================================
echo.

set SERVER_IP=3.91.170.95
set SSH_KEY=agent_hawk.pem
set SERVER_USER=ubuntu
set BACKEND_DIR=/home/ubuntu/unified-backend

echo 📡 Testing SSH connection...
ssh -i %SSH_KEY% -o ConnectTimeout=10 %SERVER_USER%@%SERVER_IP% "echo Connection successful"
if %errorlevel% neq 0 (
    echo ❌ Cannot connect to server %SERVER_IP%
    echo Please check SSH key and server connectivity
    pause
    exit /b 1
)

echo ✅ SSH connection successful
echo.

echo 📁 Creating backend directory on server...
ssh -i %SSH_KEY% %SERVER_USER%@%SERVER_IP% "mkdir -p %BACKEND_DIR%"

echo 🛑 Stopping existing backend processes...
ssh -i %SSH_KEY% %SERVER_USER%@%SERVER_IP% "pkill -f 'python.*unified_smart_backend' || true"

echo 📤 Uploading Python backend files...
scp -i %SSH_KEY% unified_smart_backend.py payloads.py prompt_intelligence_engine.py smart_data_extractor.py hedge_management_cache_config.py %SERVER_USER%@%SERVER_IP%:%BACKEND_DIR%/

if %errorlevel% neq 0 (
    echo ❌ Failed to upload backend files
    pause
    exit /b 1
)

echo ✅ Backend files uploaded successfully
echo.

echo 📦 Installing dependencies and starting backend...
ssh -i %SSH_KEY% %SERVER_USER%@%SERVER_IP% "cd %BACKEND_DIR% && pip3 install --user fastapi uvicorn[standard] redis supabase httpx python-multipart pydantic"

echo 🚀 Starting Unified Smart Backend...
ssh -i %SSH_KEY% %SERVER_USER%@%SERVER_IP% "cd %BACKEND_DIR% && export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co' && export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes' && export DIFY_API_KEY='app-juJAFQ9a8QAghx5tACyTvqqG' && nohup python3 unified_smart_backend.py > backend.log 2>&1 &"

echo ⏳ Waiting for backend to start...
timeout /t 10 /nobreak > nul

echo 🧪 Testing deployed backend...
curl -s --connect-timeout 10 "http://%SERVER_IP%:8004/health"

echo.
echo 🎉 DEPLOYMENT COMPLETE!
echo ==================
echo 🌐 Server: http://%SERVER_IP%:8004
echo 📋 Main Endpoint: http://%SERVER_IP%:8004/hawk-agent/process-prompt
echo 🏥 Health Check: http://%SERVER_IP%:8004/health
echo 📖 API Docs: http://%SERVER_IP%:8004/docs
echo.
echo 🔧 To check logs: ssh -i %SSH_KEY% %SERVER_USER%@%SERVER_IP% "tail -f %BACKEND_DIR%/backend.log"
echo 🛑 To stop: ssh -i %SSH_KEY% %SERVER_USER%@%SERVER_IP% "pkill -f unified_smart_backend"
echo.
echo ✅ Unified Smart Backend v5.0.0 is now running on AWS!
echo.
pause