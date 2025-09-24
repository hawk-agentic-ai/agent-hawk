#!/bin/bash
# Fix Nginx Discovery SSE routing

echo "🔧 Fixing Nginx Discovery SSE routing..."

# Check current nginx config for discovery location
echo "📋 Current discovery location:"
sudo grep -A 15 "location /master-discovery/" /etc/nginx/sites-available/default

echo ""
echo "🛠️ Fixing proxy_pass directive..."

# Fix the proxy_pass to include the correct path
sudo sed -i 's|proxy_pass http://127.0.0.1:8008;|proxy_pass http://127.0.0.1:8008/;|g' /etc/nginx/sites-available/default

# Also need to fix the URL rewriting - the issue is path handling
# Remove the existing location and add the correct one
sudo sed -i '/location \/master-discovery\//,/^[[:space:]]*}[[:space:]]*$/d' /etc/nginx/sites-available/default

# Add the corrected location block before the main location /
sudo sed -i '/location \/ {/i\
\    # Discovery SSE Server (Fixed)\
\    location /master-discovery/ {\
\        proxy_pass http://127.0.0.1:8008/;\
\        proxy_http_version 1.1;\
\        proxy_set_header Upgrade $http_upgrade;\
\        proxy_set_header Connection "upgrade";\
\        proxy_set_header Host $host;\
\        proxy_set_header X-Real-IP $remote_addr;\
\        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
\        proxy_set_header X-Forwarded-Proto $scheme;\
\        proxy_cache_bypass $http_upgrade;\
\\
\        # SSE specific settings\
\        proxy_buffering off;\
\        proxy_cache off;\
\        proxy_read_timeout 24h;\
\        proxy_send_timeout 24h;\
\\
\        # CORS headers for SSE\
\        add_header Access-Control-Allow-Origin "*" always;\
\        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;\
\        add_header Access-Control-Allow-Headers "Content-Type, Authorization, Cache-Control" always;\
\        add_header Cache-Control "no-cache, no-store, must-revalidate" always;\
\        add_header Pragma "no-cache" always;\
\        add_header Expires "0" always;\
\    }\
\
' /etc/nginx/sites-available/default

echo "🧪 Testing nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    echo "🔄 Reloading Nginx..."
    sudo systemctl reload nginx

    echo "⏱️ Waiting for reload..."
    sleep 3

    echo "🔍 Testing discovery SSE endpoint..."
    curl -s https://3-91-170-95.nip.io/master-discovery/sse --max-time 5 | head -10

    echo ""
    echo "✅ Discovery SSE should now be working at:"
    echo "   https://3-91-170-95.nip.io/master-discovery/sse"
else
    echo "❌ Nginx configuration test failed"
    echo "📋 Please check the configuration manually"
fi