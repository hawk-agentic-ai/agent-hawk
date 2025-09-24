#!/bin/bash
# Update Nginx configuration to include Discovery SSE routing

echo "🔧 Updating Nginx configuration for Discovery SSE..."

# Backup existing config
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup.$(date +%Y%m%d_%H%M%S)

# Check if discovery location already exists
if grep -q "location /master-discovery/" /etc/nginx/sites-available/default; then
    echo "⚠️ Discovery location already configured"
else
    echo "📝 Adding discovery location to Nginx config..."

    # Add discovery location before the final closing brace
    sudo sed -i '/^[[:space:]]*}[[:space:]]*$/i \
\    # Discovery SSE Server\
\    location /master-discovery/ {\
\        proxy_pass http://127.0.0.1:8008/;\
\        proxy_http_version 1.1;\
\        proxy_set_header Upgrade $http_upgrade;\
\        proxy_set_header Connection '"'"'upgrade'"'"';\
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
' /etc/nginx/sites-available/default
fi

# Test nginx configuration
echo "🧪 Testing Nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    echo "🔄 Reloading Nginx..."
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded successfully"

    # Test the endpoint
    echo "🔍 Testing discovery endpoint..."
    sleep 2
    curl -s http://localhost:8008/health | head -5

    echo ""
    echo "🌐 Discovery SSE endpoint should now be available at:"
    echo "   https://3-91-170-95.nip.io/master-discovery/sse"
else
    echo "❌ Nginx configuration test failed"
    echo "🔄 Restoring backup..."
    sudo cp /etc/nginx/sites-available/default.backup.$(date +%Y%m%d_%H%M%S) /etc/nginx/sites-available/default
fi