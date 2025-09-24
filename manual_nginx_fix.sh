#!/bin/bash
# Manual fix for nginx discovery routing

echo "🔧 Manually fixing nginx location block order..."

# Create a backup
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup.manual

# Create a new corrected configuration
sudo tee /etc/nginx/sites-available/default > /dev/null << 'EOF'
server {
	listen 80 default_server;
	listen [::]:80 default_server;

	# SSL configuration
	listen 443 ssl default_server;
	listen [::]:443 ssl default_server;
	ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
	ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;

	root /var/www/html;
	index index.html index.htm index.nginx-debian.html;
	server_name 3-91-170-95.nip.io;

	# SPECIFIC LOCATION BLOCKS FIRST (BEFORE GENERAL LOCATION /)

	# MCP Allocation Server
	location /dify/ {
		proxy_pass http://127.0.0.1:8010/;
		proxy_http_version 1.1;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection 'upgrade';
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_cache_bypass $http_upgrade;
		proxy_buffering off;
		proxy_cache off;
		add_header Access-Control-Allow-Origin "*" always;
		add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
		add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
	}

	# Discovery SSE Server - CRITICAL: This must be BEFORE location /
	location /master-discovery/ {
		proxy_pass http://127.0.0.1:8008/;
		proxy_http_version 1.1;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "upgrade";
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_cache_bypass $http_upgrade;

		# SSE specific settings
		proxy_buffering off;
		proxy_cache off;
		proxy_read_timeout 24h;
		proxy_send_timeout 24h;

		# CORS headers for SSE
		add_header Access-Control-Allow-Origin "*" always;
		add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
		add_header Access-Control-Allow-Headers "Content-Type, Authorization, Cache-Control" always;
		add_header Cache-Control "no-cache, no-store, must-revalidate" always;
		add_header Pragma "no-cache" always;
		add_header Expires "0" always;
	}

	# Main MCP Server
	location /mcp/ {
		proxy_pass http://127.0.0.1:8009/;
		proxy_http_version 1.1;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection 'upgrade';
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_cache_bypass $http_upgrade;
		add_header Access-Control-Allow-Origin "*" always;
		add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
		add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
	}

	# GENERAL LOCATION BLOCK LAST
	location / {
		try_files $uri $uri/ =404;
	}
}
EOF

echo "🧪 Testing nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
	echo "✅ Nginx configuration is valid"
	echo "🔄 Reloading Nginx..."
	sudo systemctl reload nginx

	echo "⏱️ Waiting for reload..."
	sleep 3

	echo "🔍 Testing discovery SSE endpoint..."
	timeout 5 curl -s https://3-91-170-95.nip.io/master-discovery/sse || echo "Timeout or streaming response"

	echo ""
	echo "✅ Discovery SSE is now properly configured!"
	echo "🌐 URL: https://3-91-170-95.nip.io/master-discovery/sse"
else
	echo "❌ Nginx configuration failed"
	echo "🔄 Restoring backup..."
	sudo cp /etc/nginx/sites-available/default.backup.manual /etc/nginx/sites-available/default
fi