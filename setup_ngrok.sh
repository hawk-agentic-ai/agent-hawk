#!/bin/bash
# Setup ngrok tunnel for cleaner HTTPS URLs

SERVER_IP="3.91.170.95"
MCP_PORT=8010

echo "🔗 Setting up ngrok tunnel for HAWK MCP Server..."
echo "🎯 Target: localhost:$MCP_PORT"
echo ""

ssh -i agent_hawk.pem ubuntu@$SERVER_IP << 'EOF'
    echo "📦 Installing ngrok..."

    # Install ngrok if not present
    if ! command -v ngrok &> /dev/null; then
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
        sudo apt update && sudo apt install ngrok
    fi

    echo "🛑 Stopping any existing tunnels..."
    pkill -f ngrok || true
    pkill -f cloudflared || true
    sleep 2

    echo "🚀 Starting ngrok tunnel..."
    nohup ngrok http 8010 > ngrok.log 2>&1 &

    echo "⏱️ Waiting for tunnel startup..."
    sleep 10

    echo "🔍 Getting HTTPS URL..."
    curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok-free\.app' | head -1 || echo "Tunnel starting up..."

    echo "✅ ngrok tunnel setup complete!"
EOF

echo ""
echo "🔗 Getting tunnel URL..."
ssh -i agent_hawk.pem ubuntu@$SERVER_IP "curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^\"]*\.ngrok-free\.app' | head -1" || echo "Tunnel still starting..."

echo ""
echo "✨ ngrok HTTPS tunnel ready!"