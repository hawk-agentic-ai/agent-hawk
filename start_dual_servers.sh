#!/bin/bash
echo "🚀 Starting Dual Protocol Hedge Fund Servers..."

# Configuration
FASTAPI_PORT=8004
MCP_PORT=8005
PROJECT_DIR="/home/ubuntu/hedge-agent"

echo "📋 Configuration:"
echo "  FastAPI Server: Port $FASTAPI_PORT (HTTP/HTTPS via nginx)"
echo "  MCP Server: Port $MCP_PORT (stdio protocol)"
echo "  Project Directory: $PROJECT_DIR"

# Set environment variables
export ALLOWED_ORIGINS="https://3-91-170-95.nip.io"
export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
export MCP_SERVER_PORT=$MCP_PORT
export MCP_SERVER_HOST="0.0.0.0"
export ENABLE_MCP_SERVER="true"

echo "🌐 Environment configured for HTTPS and MCP"

# Stop any existing servers
echo "🛑 Stopping existing servers..."
sudo pkill -f "unified_smart_backend" || true
sudo pkill -f "mcp_server" || true
sudo pkill -f "uvicorn" || true

sleep 2

# Start FastAPI server (Port 8004)
echo "🔥 Starting FastAPI Server on port $FASTAPI_PORT..."
cd $PROJECT_DIR
nohup python3 -m uvicorn unified_smart_backend:app \
    --host 0.0.0.0 \
    --port $FASTAPI_PORT \
    --reload > fastapi.log 2>&1 &

FASTAPI_PID=$!
echo "  ✅ FastAPI PID: $FASTAPI_PID"

# Wait for FastAPI to start
sleep 5

# Test FastAPI health
echo "🧪 Testing FastAPI health..."
HEALTH_RESPONSE=$(curl -s http://localhost:$FASTAPI_PORT/health || echo "FAILED")

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo "  ✅ FastAPI: Healthy"
else
    echo "  ❌ FastAPI: Health check failed"
    echo "  📋 FastAPI logs (last 10 lines):"
    tail -10 fastapi.log
fi

# Start MCP Server (stdio protocol - for Dify integration)
echo "🔧 Starting MCP Server..."

# Create MCP server startup script
cat > start_mcp.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/hedge-agent
export PYTHONPATH="/home/ubuntu/hedge-agent:$PYTHONPATH"
python3 mcp_server.py
EOF

chmod +x start_mcp.sh

# Start MCP server in background for testing
nohup ./start_mcp.sh > mcp.log 2>&1 &
MCP_PID=$!
echo "  ✅ MCP Server PID: $MCP_PID"

# Wait for MCP server to initialize
sleep 3

# Test MCP server (basic startup check)
echo "🧪 Testing MCP Server initialization..."
if ps -p $MCP_PID > /dev/null; then
    echo "  ✅ MCP Server: Process running"
    echo "  📋 MCP logs (last 5 lines):"
    tail -5 mcp.log
else
    echo "  ❌ MCP Server: Process not running"
    echo "  📋 MCP logs (all):"
    cat mcp.log
fi

echo ""
echo "📊 Server Status Summary:"
echo "─────────────────────────────────────"

# FastAPI Status
if ps -p $FASTAPI_PID > /dev/null; then
    echo "✅ FastAPI Server: Running (PID: $FASTAPI_PID)"
    echo "   🔗 HTTP: http://localhost:$FASTAPI_PORT"
    echo "   🔗 HTTPS: https://3-91-170-95.nip.io/api/"
else
    echo "❌ FastAPI Server: Not running"
fi

# MCP Status
if ps -p $MCP_PID > /dev/null; then
    echo "✅ MCP Server: Running (PID: $MCP_PID)"
    echo "   🔗 Protocol: stdio (for Dify integration)"
    echo "   🛠️  Tools: process_hedge_prompt, query_supabase_data, get_system_health, manage_cache"
else
    echo "❌ MCP Server: Not running"
fi

echo ""
echo "🔍 Integration Status:"
echo "─────────────────────────────────────"
echo "📱 Angular Frontend: https://3-91-170-95.nip.io (uses FastAPI via nginx proxy)"
echo "🤖 Dify AI Integration: Ready for MCP stdio connection"
echo "🔄 Shared Business Logic: Both servers use same core processing"

echo ""
echo "📋 Process Management:"
echo "─────────────────────────────────────"
echo "Monitor logs:"
echo "  tail -f fastapi.log  # FastAPI server logs"
echo "  tail -f mcp.log      # MCP server logs"
echo ""
echo "Stop servers:"
echo "  sudo pkill -f unified_smart_backend  # Stop FastAPI"
echo "  sudo pkill -f mcp_server            # Stop MCP server"
echo ""

# Save PIDs for later management
echo "$FASTAPI_PID" > fastapi.pid
echo "$MCP_PID" > mcp.pid

echo "✅ Dual server startup complete!"
echo "🚀 Ready for both Angular UI (FastAPI) and Dify AI (MCP) integration"