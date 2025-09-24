#!/bin/bash
# Setup HTTPS access for MCP server using nginx and Let's Encrypt

SERVER_IP="3.91.170.95"
DOMAIN="hawk-mcp-server.nip.io"
MCP_PORT=8010
HTTPS_PORT=443

echo "🔒 Setting up HTTPS for HAWK MCP Server..."
echo "🌐 Domain: $DOMAIN"
echo "🔗 Target: localhost:$MCP_PORT"
echo ""

# Setup HTTPS reverse proxy
ssh -i agent_hawk.pem ubuntu@$SERVER_IP << 'EOF'
    echo "📦 Installing nginx and certbot..."
    sudo apt update
    sudo apt install -y nginx python3-certbot-nginx

    echo "⚙️ Configuring nginx..."
    sudo tee /etc/nginx/sites-available/mcp-server > /dev/null << 'NGINX_CONFIG'
server {
    listen 80;
    server_name hawk-mcp-server.nip.io;

    location / {
        proxy_pass http://localhost:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers for MCP
        add_header Access-Control-Allow-Origin "https://dify.ai" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "https://dify.ai";
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization";
            return 204;
        }
    }
}
NGINX_CONFIG

    echo "🔗 Enabling site..."
    sudo ln -sf /etc/nginx/sites-available/mcp-server /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx

    echo "📜 Getting SSL certificate..."
    sudo certbot --nginx -d hawk-mcp-server.nip.io --non-interactive --agree-tos --email admin@example.com

    echo "🔧 Testing HTTPS configuration..."
    curl -s https://hawk-mcp-server.nip.io/ | head -3

    echo "✅ HTTPS setup complete!"
    echo "🌐 HTTPS URL: https://hawk-mcp-server.nip.io"
EOF

echo ""
echo "🎯 Testing HTTPS endpoint..."
curl -s https://hawk-mcp-server.nip.io/ | head -5

echo ""
echo "✨ HTTPS MCP Server setup complete!"
echo "🔒 Secure URL: https://hawk-mcp-server.nip.io"
echo "📋 Use this URL in Dify MCP configuration"