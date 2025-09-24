#!/bin/bash
echo "📦 Deploying Shared Modules to Server..."

# Upload the entire shared directory
echo "📤 Uploading shared directory..."
scp -r -i agent_hawk.pem -o StrictHostKeyChecking=no shared/ ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/

# Upload updated backend
echo "📤 Uploading updated backend..."
scp -i agent_hawk.pem -o StrictHostKeyChecking=no unified_smart_backend.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/

echo "🐍 Restarting backend with shared modules..."
ssh -i agent_hawk.pem ubuntu@3.91.170.95 -o StrictHostKeyChecking=no << 'EOF'
    cd /home/ubuntu/hedge-agent
    
    echo "🛑 Stopping existing backend..."
    sudo pkill -f "unified_smart_backend" || true
    sudo pkill -f "uvicorn" || true
    
    echo "📋 Checking shared directory structure..."
    ls -la shared/
    
    echo "🌐 Setting HTTPS CORS environment..."
    export ALLOWED_ORIGINS="https://3-91-170-95.nip.io"
    export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
    
    echo "🚀 Starting backend with shared modules..."
    nohup python3 -m uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004 > backend.log 2>&1 &
    
    sleep 5
    
    echo "🧪 Testing backend..."
    curl -s http://localhost:8004/health || echo "Health check failed - checking logs..."
    tail -10 backend.log
EOF

echo "🌐 Testing HTTPS API endpoint..."
sleep 3
curl -I https://3-91-170-95.nip.io/api/health