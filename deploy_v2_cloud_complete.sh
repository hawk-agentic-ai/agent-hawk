#!/bin/bash
echo "🛑 Stopping all existing MCP servers on cloud..."

# SSH to cloud and stop all MCP servers, then deploy V2
ssh ubuntu@3.91.170.95 << 'REMOTE_SCRIPT'
cd /home/ubuntu/hedge-agent/hedge-agent

echo "🔍 Finding and stopping all MCP processes..."
# Kill all MCP server processes
pkill -f "python.*mcp_server" || true
pkill -f "python.*allocation" || true
pkill -f "uvicorn.*800" || true
sleep 5

# Show what's still running
echo "📋 Remaining Python processes:"
ps aux | grep python | grep -v grep || echo "No Python processes found"

echo "📦 Creating V2 server file..."
cat > "mcp_server_production_v2.py" << 'PYEOF'
$(cat "mcp_server_production v2.py")
PYEOF

echo "🔧 Setting environment variables..."
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"

echo "📦 Installing dependencies..."
pip3 install --user anyio || true

echo "🚀 Starting V2 MCP server..."
nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid

echo "⏳ Waiting for server startup..."
sleep 8

echo "🏥 Health check..."
curl -s http://localhost:8009/health || echo "❌ Health check failed"

echo "✅ V2 Server deployment complete!"
echo "📍 Available at: https://3-91-170-95.nip.io/mcp/"

tail -10 mcp_v2.log
REMOTE_SCRIPT

echo "✅ V2 deployment script executed"