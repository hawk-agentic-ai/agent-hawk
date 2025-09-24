#!/bin/bash
# Fix MCP routing to point to allocation server on port 8010

SERVER_IP="3.91.170.95"

echo "🔧 Updating nginx to route /mcp/ to allocation server..."

ssh -i agent_hawk.pem ubuntu@$SERVER_IP << 'EOF'
    # Backup current nginx config
    sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

    # Update nginx config to point /mcp/ to port 8010 (allocation server)
    sudo sed -i 's|proxy_pass http://localhost:8009/;|proxy_pass http://localhost:8010/;|' /etc/nginx/sites-available/default

    # Test nginx config
    sudo nginx -t

    if [ $? -eq 0 ]; then
        echo "✅ Nginx config updated successfully"
        sudo systemctl reload nginx
        echo "🔄 Nginx reloaded"
    else
        echo "❌ Nginx config test failed, restoring backup"
        sudo cp /etc/nginx/sites-available/default.backup /etc/nginx/sites-available/default
    fi
EOF

echo "🎯 Testing updated MCP routing..."
curl -s https://3-91-170-95.nip.io/mcp/ | head -3

echo "🔍 Testing MCP SSE endpoint..."
curl -s -m 2 https://3-91-170-95.nip.io/mcp/sse 2>/dev/null | head -2

echo "✨ MCP routing fix complete!"
echo "📝 Use URL: https://3-91-170-95.nip.io/mcp/"