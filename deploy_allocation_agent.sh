#!/bin/bash
echo "🎯 Deploying Backend with Allocation Agent Configuration..."

# Copy backend files and deploy with allocation agent environment variables
scp -i agent_hawk.pem unified_smart_backend.py shared/* ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/ -o StrictHostKeyChecking=no

echo "🚀 Deploying to production server..."
ssh -i agent_hawk.pem ubuntu@3.91.170.95 -o StrictHostKeyChecking=no << 'EOF'
    echo "🔧 Stopping any existing backend processes..."
    sudo pkill -f "unified_smart_backend" || true
    sudo pkill -f "uvicorn" || true
    
    echo "📂 Setting up backend directory..."
    cd /home/ubuntu/hedge-agent
    
    echo "🌐 Configuring environment variables..."
    export ALLOWED_ORIGINS="https://3-91-170-95.nip.io"
    export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
    
    # Allocation Agent Configuration
    export DIFY_API_KEY_ALLOCATION="app-cxzVbRQUUDofTjx1nDfajpRX"
    export DIFY_API_URL_ALLOCATION="https://api.dify.ai/v1"
    
    # Also add to system environment file for persistence
    echo "export DIFY_API_KEY_ALLOCATION=app-cxzVbRQUUDofTjx1nDfajpRX" | sudo tee -a /etc/environment
    echo "export DIFY_API_URL_ALLOCATION=https://api.dify.ai/v1" | sudo tee -a /etc/environment
    
    echo "🐍 Starting backend with allocation agent support..."
    nohup python3 -m uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004 --reload > backend.log 2>&1 &
    
    echo "✅ Backend started with PID: $!"
    
    echo "⏳ Waiting for backend to start..."
    sleep 8
    
    echo "🧪 Testing backend health..."
    curl -s http://localhost:8004/health || echo "Backend health check failed"
    
    echo "📋 Backend process status:"
    ps aux | grep uvicorn | grep -v grep
    
    echo "🔍 Checking environment variables..."
    echo "DIFY_API_KEY_ALLOCATION: ${DIFY_API_KEY_ALLOCATION:+SET}"
    echo "DIFY_API_URL_ALLOCATION: ${DIFY_API_URL_ALLOCATION:+SET}"
EOF

echo "🌐 Testing backend through HTTPS proxy..."
curl -I https://3-91-170-95.nip.io/api/health

echo "🎉 Allocation Agent deployment complete!"
echo "🔗 Backend API: https://3-91-170-95.nip.io/api/"
echo "🤖 Allocation Agent: Now available via agent dropdown"