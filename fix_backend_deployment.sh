#!/bin/bash
echo "🔧 Fixing Backend Deployment..."

# First, upload the Python backend files to the server
echo "📤 Uploading backend files..."
scp -i agent_hawk.pem -o StrictHostKeyChecking=no unified_smart_backend.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no payloads.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no prompt_intelligence_engine.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no smart_data_extractor.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no hedge_management_cache_config.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no requirements.txt ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/

echo "🐍 Installing dependencies and starting backend..."
ssh -i agent_hawk.pem ubuntu@3.91.170.95 -o StrictHostKeyChecking=no << 'EOF'
    cd /home/ubuntu/hedge-agent
    
    echo "🛑 Stopping existing backend..."
    sudo pkill -f "unified_smart_backend" || true
    sudo pkill -f "uvicorn" || true
    
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
    
    echo "📋 Listing Python files..."
    ls -la *.py
    
    echo "🌐 Setting HTTPS CORS environment..."
    export ALLOWED_ORIGINS="https://3-91-170-95.nip.io"
    export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
    
    echo "🚀 Starting backend with correct working directory..."
    nohup python3 -m uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004 > backend.log 2>&1 &
    
    sleep 5
    
    echo "🧪 Testing backend..."
    curl -s http://localhost:8004/health || echo "Health check failed - checking logs..."
    tail -10 backend.log
EOF

echo "🌐 Testing HTTPS API endpoint..."
sleep 3
curl -I https://3-91-170-95.nip.io/api/health