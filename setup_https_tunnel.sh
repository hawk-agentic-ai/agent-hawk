#!/bin/bash
# Setup HTTPS tunnel for MCP server using ngrok or cloudflared

SERVER_IP="3.91.170.95"
MCP_PORT=8010

echo "🔒 Setting up HTTPS tunnel for HAWK MCP Server..."
echo "🎯 Target: localhost:$MCP_PORT"
echo ""

# Install and setup cloudflared tunnel
ssh -i agent_hawk.pem ubuntu@$SERVER_IP << 'EOF'
    echo "📦 Installing cloudflared..."

    # Download and install cloudflared
    if ! command -v cloudflared &> /dev/null; then
        curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
        sudo mv cloudflared /usr/local/bin/
        sudo chmod +x /usr/local/bin/cloudflared
    fi

    echo "🛑 Stopping any existing tunnel..."
    pkill -f "cloudflared tunnel" || true
    sleep 2

    echo "🚀 Starting HTTPS tunnel..."
    nohup cloudflared tunnel --url http://localhost:8010 > tunnel.log 2>&1 &

    echo "⏱️ Waiting for tunnel startup..."
    sleep 10

    echo "🔍 Getting HTTPS URL..."
    grep -o 'https://[^[:space:]]*\.trycloudflare\.com' tunnel.log | tail -1 || echo "Tunnel starting up..."

    echo "✅ HTTPS tunnel setup complete!"
    echo "📋 Logs: tail -f /home/ubuntu/hedge-agent/tunnel.log"
EOF

echo ""
echo "🔗 Getting tunnel URL..."
ssh -i agent_hawk.pem ubuntu@$SERVER_IP "grep -o 'https://[^[:space:]]*\.trycloudflare\.com' tunnel.log | tail -1" || echo "Tunnel still starting..."

echo ""
echo "✨ HTTPS tunnel setup complete!"
echo "📋 Use the HTTPS URL above in Dify MCP configuration"