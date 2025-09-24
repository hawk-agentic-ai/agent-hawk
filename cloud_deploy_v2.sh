#!/bin/bash
cd /home/ubuntu/hedge-agent/hedge-agent

echo "Stopping any existing MCP servers on port 8009..."
pkill -f "python.*mcp_server_production.py" || true
sleep 3

echo "Setting environment variables..."
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dWxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"

echo "Starting V2 MCP server on port 8009..."
nohup python3 "mcp_server_production v2.py" > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid

echo "Waiting for startup..."
sleep 8

echo "Testing health..."
curl -s http://localhost:8009/health

echo "V2 deployment complete!"
echo "Server available at: https://3-91-170-95.nip.io/mcp/"