#!/bin/bash
echo "🚀 Deploying Backend Updates to Production Server..."

# Create a backup of current files
echo "📦 Creating backup of current server files..."
ssh -i agent_hawk.pem ubuntu@13.222.100.183 -o StrictHostKeyChecking=no << 'EOF'
    cd /home/ubuntu/hedge-agent/hedge-agent
    # Create backup directory with timestamp
    backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup current files
    if [ -f "mcp_server_production_v2.py" ]; then
        cp mcp_server_production_v2.py "$backup_dir/"
    fi
    if [ -d "shared" ]; then
        cp -r shared "$backup_dir/"
    fi

    echo "✅ Backup created in $backup_dir"
EOF

# Upload updated files
echo "📤 Uploading updated MCP server..."
scp -i agent_hawk.pem -o StrictHostKeyChecking=no mcp_server_production_v2.py ubuntu@13.222.100.183:/home/ubuntu/hedge-agent/hedge-agent/

echo "📤 Uploading shared modules..."
scp -i agent_hawk.pem -o StrictHostKeyChecking=no -r shared ubuntu@13.222.100.183:/home/ubuntu/hedge-agent/hedge-agent/

# Install any missing dependencies and restart the MCP server
echo "🔧 Installing dependencies and restarting MCP server..."
ssh -i agent_hawk.pem ubuntu@13.222.100.183 -o StrictHostKeyChecking=no << 'EOF'
    cd /home/ubuntu/hedge-agent/hedge-agent

    # Install any missing Python dependencies
    pip3 install -r requirements_mcp.txt 2>/dev/null || echo "Requirements file not found, skipping pip install"

    # Stop existing MCP server on port 8009
    echo "🛑 Stopping existing MCP server..."
    pkill -f "python.*mcp_server_production_v2.py" || echo "No existing MCP server found"
    sleep 3

    # Start the updated MCP server
    echo "▶️ Starting updated MCP server..."
    export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
    export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU"
    export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"

    nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &
    echo $! > mcp_v2.pid

    # Wait a moment and check if it started successfully
    sleep 5
    if ps -p $(cat mcp_v2.pid 2>/dev/null) > /dev/null 2>&1; then
        echo "✅ MCP server started successfully with PID $(cat mcp_v2.pid)"
    else
        echo "❌ MCP server failed to start"
        tail -20 mcp_v2.log
        exit 1
    fi
EOF

# Test the deployment
echo "🧪 Testing MCP server deployment..."
sleep 3
echo "📊 Health check:"
curl -s https://13-222-100-183.nip.io/mcp/health | python3 -m json.tool || echo "Health check failed"

echo "🎉 Backend deployment complete!"
echo "🔗 MCP Server: https://13-222-100-183.nip.io/mcp/"