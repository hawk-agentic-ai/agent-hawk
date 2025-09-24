#!/bin/bash
# Start Discovery SSE Server on Cloud Instance

echo "🚀 Starting Discovery SSE Server..."
echo "📡 Target: 3.91.170.95:8008"
echo "🌐 SSE Endpoint: /master-discovery/sse"

# Kill any existing discovery server
pkill -f "master_discovery_server.py" || true
sleep 2

# Start discovery server in background
cd /home/ubuntu/hedge-agent/
echo "🔧 Starting discovery server on port 8008..."
nohup python3 master_discovery_server.py > discovery_server.log 2>&1 &

# Wait for startup
sleep 3

# Test server health
echo "🔍 Testing server health..."
curl -s http://localhost:8008/health | jq . || echo "Server starting up..."

echo "✅ Discovery SSE Server started!"
echo "📋 Logs: tail -f /home/ubuntu/hedge-agent/discovery_server.log"
echo "🌐 Endpoint: https://3-91-170-95.nip.io/master-discovery/sse"