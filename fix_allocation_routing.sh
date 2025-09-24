#!/bin/bash
# Fix allocation routing - revert MCP and create dedicated allocation path

SERVER_IP="3.91.170.95"

echo "🔄 Reverting MCP routing and creating dedicated allocation path..."

ssh -i agent_hawk.pem ubuntu@$SERVER_IP << 'EOF'
    # Restore original MCP routing to port 8009
    sudo sed -i 's|proxy_pass http://localhost:8010/;|proxy_pass http://localhost:8009/;|' /etc/nginx/sites-available/default

    # Add dedicated allocation path right after the MCP section
    sudo sed -i '/location \/mcp\/ {/,/}/a\\n      # Allocation MCP Server proxy\n      location /allocation/ {\n          add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;\n          proxy_pass http://localhost:8010/;\n          proxy_http_version 1.1;\n          proxy_buffering off;\n          proxy_set_header Host $host;\n          proxy_set_header X-Real-IP $remote_addr;\n          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n          proxy_set_header X-Forwarded-Proto $scheme;\n          proxy_set_header X-Forwarded-Prefix /allocation;\n          proxy_set_header X-Public-Base $scheme://$host/allocation/;\n          proxy_set_header X-Original-URI $request_uri;\n          proxy_set_header Authorization $http_authorization;\n          proxy_cache_bypass $http_upgrade;\n          proxy_read_timeout 86400;\n          add_header '"'"'Access-Control-Allow-Origin'"'"' '"'"'*'"'"' always;\n          add_header '"'"'Access-Control-Allow-Methods'"'"' '"'"'GET, POST, OPTIONS, PUT, DELETE'"'"' always;\n          add_header '"'"'Access-Control-Allow-Headers'"'"' '"'"'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization'"'"' always;\n          \n          if ($request_method = '"'"'OPTIONS'"'"') {\n              add_header '"'"'Access-Control-Max-Age'"'"' 86400 always;\n              return 204;\n          }\n      }' /etc/nginx/sites-available/default

    # Test nginx config
    sudo nginx -t

    if [ $? -eq 0 ]; then
        echo "✅ Nginx config updated successfully"
        sudo systemctl reload nginx
        echo "🔄 Nginx reloaded"
    else
        echo "❌ Nginx config test failed"
        exit 1
    fi
EOF

echo "🎯 Testing allocation routing..."
curl -s https://3-91-170-95.nip.io/allocation/ | head -3

echo "🔍 Testing allocation SSE endpoint..."
curl -s -m 2 https://3-91-170-95.nip.io/allocation/sse 2>/dev/null | head -2

echo "✨ Allocation routing fix complete!"
echo "📝 Use URL: https://3-91-170-95.nip.io/allocation/"