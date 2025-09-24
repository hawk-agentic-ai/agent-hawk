#!/bin/bash
echo "🚀 Deploying Backend with HTTPS Configuration..."

# Deploy backend to server with HTTPS CORS settings
ssh -i agent_hawk.pem ubuntu@3.91.170.95 -o StrictHostKeyChecking=no << 'EOF'
    echo "🔧 Stopping any existing backend processes..."
    sudo pkill -f "unified_smart_backend" || true
    sudo pkill -f "uvicorn" || true
    
    echo "📂 Setting up backend directory..."
    cd /home/ubuntu/hedge-agent
    
    echo "🌐 Configuring HTTPS CORS origins..."
    export ALLOWED_ORIGINS="https://3-91-170-95.nip.io"
    export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
    
    echo "🐍 Starting backend with HTTPS support..."
    nohup python3 -m uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004 --reload > backend.log 2>&1 &
    
    echo "✅ Backend started with PID: $!"
    
    echo "⏳ Waiting for backend to start..."
    sleep 5
    
    echo "🧪 Testing backend health..."
    curl -s http://localhost:8004/health || echo "Backend health check failed"
    
    echo "📋 Backend process status:"
    ps aux | grep uvicorn | grep -v grep
EOF

echo "🌐 Testing backend through HTTPS proxy..."
curl -I https://3-91-170-95.nip.io/api/health

echo "🎉 Backend deployment complete!"
echo "🔗 Backend API: https://3-91-170-95.nip.io/api/"