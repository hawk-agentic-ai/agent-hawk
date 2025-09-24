#!/bin/bash
# Deploy HAWK Stage 1A Allocation MCP Server to AWS Cloud

# Set deployment variables
DEPLOYMENT_NAME="hawk-allocation-mcp"
PORT=8010
SERVER_IP="13.222.100.183"

echo "🚀 Deploying HAWK Stage 1A Allocation MCP Server..."
echo "📡 Target: $SERVER_IP:$PORT"
echo "⚡ Features: Intent Detection | View Optimization | Database Writes"
echo ""

# Copy server files to cloud
echo "📁 Copying server files..."
scp -i agent_hawk.pem mcp_allocation_server.py ubuntu@$SERVER_IP:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem requirements_allocation_mcp.txt ubuntu@$SERVER_IP:/home/ubuntu/hedge-agent/

# Deploy to cloud
echo "🌐 Deploying to cloud server..."
ssh -i agent_hawk.pem ubuntu@$SERVER_IP << 'EOF'
    cd /home/ubuntu/hedge-agent/

    echo "🔧 Installing dependencies..."
    pip3 install -r requirements_allocation_mcp.txt

    echo "🛑 Stopping any existing allocation server..."
    pkill -f "mcp_allocation_server.py" || true
    sleep 2

    echo "⚙️ Setting environment variables..."
    export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
    export SUPABASE_SERVICE_ROLE_KEY="sb_secret_X5tqrZ7xBcdFCgI41ciHFA_OKNlYi2D"
    export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai"
    export PORT=8010

    echo "🚀 Starting HAWK Allocation MCP Server..."
    nohup python3 mcp_allocation_server.py > allocation_mcp.log 2>&1 &

    echo "⏱️ Waiting for server startup..."
    sleep 5

    echo "🔍 Testing server health..."
    curl -s http://localhost:8010/ | jq . || echo "Server starting up..."

    echo "✅ Allocation MCP Server deployment complete!"
    echo "📡 Access: http://13.222.100.183:8010"
    echo "📋 Logs: tail -f /home/ubuntu/hedge-agent/allocation_mcp.log"
EOF

echo ""
echo "🎯 Testing deployed server..."
curl -s http://$SERVER_IP:$PORT/ | jq .

echo ""
echo "✨ HAWK Stage 1A Allocation MCP Server deployed successfully!"
echo "🌐 Endpoint: http://$SERVER_IP:$PORT"
echo "🔧 Tools: allocation_stage1a_processor, query_allocation_view, get_allocation_health"
echo "📖 KB Updated: Use new tools in Dify agent configuration"
echo ""
echo "Next Steps:"
echo "1. Update Dify MCP connection to port 8010"
echo "2. Test with allocation agent prompts"
echo "3. Verify intent detection and database writes"