#!/bin/bash

# Debug Backend Script - Run this on your EC2 instance
echo "🔍 Debugging FastAPI Backend Issues..."
echo "===================================="

# Check current directory and files
echo "📁 Current directory and files:"
pwd
ls -la

# Check if we're in the right directory
if [ ! -f "optimized_dify_endpoint.py" ]; then
    echo "❌ Not in hedge-agent directory. Moving..."
    cd /home/ubuntu/hedge-agent
    echo "📁 Now in: $(pwd)"
fi

# Check Python virtual environment
echo ""
echo "🐍 Checking Python environment:"
if [ -d "venv" ]; then
    echo "✅ Virtual environment exists"
    source venv/bin/activate
    echo "✅ Virtual environment activated"
    python --version
    pip list | grep -E "(fastapi|uvicorn|redis|supabase)"
else
    echo "❌ Virtual environment missing - creating new one"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Check .env file
echo ""
echo "⚙️ Checking environment file:"
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    echo "Contents (masked):"
    sed 's/=.*/=***MASKED***/' .env
else
    echo "❌ .env file missing - creating placeholder"
    cat > .env << 'EOF'
DIFY_API_KEY=placeholder-key
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=placeholder-url
SUPABASE_ANON_KEY=placeholder-key
ENVIRONMENT=production
EOF
    echo "✅ .env file created with placeholders"
fi

# Check Redis
echo ""
echo "🗄️ Checking Redis:"
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis not responding - starting it"
    sudo systemctl start redis-server
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis started successfully"
    else
        echo "❌ Redis failed to start"
    fi
fi

# Check PM2 status
echo ""
echo "📊 PM2 Status:"
pm2 status

# Check PM2 logs if process exists
if pm2 list | grep -q "hedge-agent-api"; then
    echo ""
    echo "📜 PM2 Logs for hedge-agent-api:"
    pm2 logs hedge-agent-api --lines 10
fi

# Test manual startup
echo ""
echo "🚀 Testing manual FastAPI startup:"
echo "Starting FastAPI manually to check for errors..."
timeout 5 python -c "
import sys
sys.path.append('.')
try:
    from optimized_dify_endpoint import app
    print('✅ App import successful')
    import uvicorn
    print('✅ Uvicorn import successful')
except Exception as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
"

# Try starting with uvicorn
echo ""
echo "🔧 Attempting uvicorn startup (5 second test):"
timeout 5 uvicorn optimized_dify_endpoint:app --host 0.0.0.0 --port 8000 2>&1 || echo "Startup test completed"

# Check port availability
echo ""
echo "🔌 Checking port 8000:"
if ss -tlnp | grep :8000 > /dev/null 2>&1; then
    echo "✅ Something is running on port 8000"
    ss -tlnp | grep :8000
else
    echo "❌ Nothing running on port 8000"
fi

# Final PM2 restart attempt
echo ""
echo "🔄 Restarting with PM2:"
pm2 delete hedge-agent-api 2>/dev/null || echo "No existing process to delete"
pm2 start "uvicorn optimized_dify_endpoint:app --host 0.0.0.0 --port 8000 --workers 1" --name hedge-agent-api
sleep 3
pm2 status

# Test final connection
echo ""
echo "🧪 Final connection test:"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is responding!"
    curl -s http://localhost:8000/health
else
    echo "❌ Backend still not responding"
    echo "📜 Recent PM2 logs:"
    pm2 logs hedge-agent-api --lines 5
fi

echo ""
echo "🎯 Debug complete! Check the output above for issues."