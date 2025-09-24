#!/bin/bash
cd /home/ubuntu/hedge-agent/hedge-agent

# Stop any existing MCP servers
pkill -f "python.*mcp_server_production" || true
sleep 3

# Set environment variables
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS=http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai

# Install dependencies
pip3 install --user anyio || true

# Start V2 server on port 8009 (replaces V1)
echo "Starting MCP V2 Server..."
nohup python3 "mcp_server_production v2.py" > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid

# Wait and verify
sleep 5
curl -s http://localhost:8009/health || echo "Health check failed"
echo "V2 Server deployed at: https://3-91-170-95.nip.io/mcp/"