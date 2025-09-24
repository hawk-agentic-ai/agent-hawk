#!/bin/bash
echo "🔍 Checking Backend Status..."

ssh -i agent_hawk.pem ubuntu@3.91.170.95 -o StrictHostKeyChecking=no << 'EOF'
    echo "📋 Backend process status:"
    ps aux | grep uvicorn | grep -v grep
    
    echo -e "\n📄 Backend logs (last 20 lines):"
    tail -20 /home/ubuntu/hedge-agent/backend.log
    
    echo -e "\n🧪 Direct backend test:"
    curl -s http://localhost:8004/health | head -5
    
    echo -e "\n🐍 Python dependencies check:"
    cd /home/ubuntu/hedge-agent
    python3 -c "import fastapi, uvicorn; print('FastAPI and Uvicorn available')" 2>/dev/null || echo "Missing dependencies"
EOF