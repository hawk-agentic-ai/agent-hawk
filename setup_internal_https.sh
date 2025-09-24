#!/bin/bash

# =============================================================================
# Internal HTTPS Setup - Self-Signed Certificate for Testing
# No domain required - works with IP address
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get server IP
SERVER_IP=$(curl -s http://checkip.amazonaws.com/ || echo "3.91.170.95")

print_status "🔒 Setting up HTTPS for Internal Testing"
print_status "Server IP: $SERVER_IP"
print_warning "This uses self-signed certificates (browser will show warning, but traffic is encrypted)"

echo ""
print_status "This will:"
echo "  1. Create self-signed SSL certificate"
echo "  2. Install and configure Nginx"  
echo "  3. Set up reverse proxy for your backend"
echo "  4. Update application to use HTTPS"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Setup cancelled"
    exit 0
fi

# =============================================================================
# STEP 1: INSTALL NGINX
# =============================================================================

print_status "Step 1: Installing Nginx..."

sudo apt update
sudo apt install -y nginx openssl

sudo systemctl enable nginx
sudo systemctl start nginx

print_success "Nginx installed"

# =============================================================================
# STEP 2: CREATE SELF-SIGNED CERTIFICATE
# =============================================================================

print_status "Step 2: Creating self-signed SSL certificate..."

# Create SSL directory
sudo mkdir -p /etc/ssl/private
sudo mkdir -p /etc/ssl/certs

# Generate private key
sudo openssl genrsa -out /etc/ssl/private/hedge-agent.key 2048

# Create certificate signing request config
sudo tee /etc/ssl/hedge-agent.conf > /dev/null <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=US
ST=State
L=City
O=Hedge Agent
OU=Internal Testing
CN=$SERVER_IP

[v3_req]
subjectAltName = @alt_names

[alt_names]
IP.1 = $SERVER_IP
IP.2 = 127.0.0.1
DNS.1 = localhost
EOF

# Generate self-signed certificate
sudo openssl req -new -x509 -key /etc/ssl/private/hedge-agent.key \
    -out /etc/ssl/certs/hedge-agent.crt -days 365 \
    -config /etc/ssl/hedge-agent.conf -extensions v3_req

# Set proper permissions
sudo chmod 600 /etc/ssl/private/hedge-agent.key
sudo chmod 644 /etc/ssl/certs/hedge-agent.crt

print_success "Self-signed certificate created"

# =============================================================================
# STEP 3: CONFIGURE NGINX
# =============================================================================

print_status "Step 3: Configuring Nginx..."

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/hedge-agent > /dev/null <<EOF
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name $SERVER_IP localhost;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $SERVER_IP localhost;
    
    # SSL certificate
    ssl_certificate /etc/ssl/certs/hedge-agent.crt;
    ssl_certificate_key /etc/ssl/private/hedge-agent.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Frontend static files
    root /var/www/hedge-agent;
    index index.html;
    
    # Frontend routing (Angular)
    location / {
        try_files \$uri \$uri/ /index.html;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With' always;
    }
    
    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:8004/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With' always;
        
        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With';
            add_header 'Content-Length' 0;
            add_header 'Content-Type' 'text/plain';
            return 204;
        }
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:8004/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/hedge-agent /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx

print_success "Nginx configured"

# =============================================================================
# STEP 4: UPDATE APPLICATION CONFIGURATION
# =============================================================================

print_status "Step 4: Updating application configuration..."

# Create frontend directory
sudo mkdir -p /var/www/hedge-agent
sudo chown -R ubuntu:ubuntu /var/www/hedge-agent

# Update environment files
if [ -f "src/environments/environment.ts" ]; then
    cat > src/environments/environment.ts <<EOF
export const environment = {
  production: false,
  apiUrl: 'https://$SERVER_IP/api',
  unifiedBackendUrl: 'https://$SERVER_IP/api',
  supabaseUrl: '',
  supabaseAnonKey: '',
  difyApiKey: '',
  
  unifiedBackend: {
    enabled: true,
    streamingEnabled: true,
    smartTemplateDetection: true,
    cacheEnabled: true
  }
};
EOF
fi

if [ -f "src/environments/environment.prod.ts" ]; then
    cat > src/environments/environment.prod.ts <<EOF
export const environment = {
  production: true,
  unifiedBackendUrl: 'https://$SERVER_IP/api',
  supabaseUrl: '',
  supabaseAnonKey: '',
  difyApiKey: '',
  
  unifiedBackend: {
    enabled: true,
    streamingEnabled: true,
    smartTemplateDetection: true,
    cacheEnabled: true
  }
};
EOF
fi

print_success "Application configuration updated"

# =============================================================================
# STEP 5: CREATE BACKEND STARTUP SCRIPT
# =============================================================================

print_status "Step 5: Creating HTTPS backend startup script..."

cat > start_internal_https_backend.sh <<EOF
#!/bin/bash

# Internal HTTPS Backend Startup Script

# Set environment variables
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
export DIFY_API_KEY='app-juJAFQ9a8QAghx5tACyTvqqG'

# CORS configuration for HTTPS
export ALLOWED_ORIGINS='https://$SERVER_IP,https://localhost,https://127.0.0.1'

# Stop any existing backend
pkill -f unified_smart_backend.py || true
sleep 2

# Start the backend
echo "Starting HTTPS backend on port 8004..."
echo "CORS origins: \$ALLOWED_ORIGINS"
nohup python3 unified_smart_backend.py > backend.log 2>&1 &

echo "Backend started. Check logs with: tail -f backend.log"
EOF

chmod +x start_internal_https_backend.sh

print_success "Backend startup script created"

# =============================================================================
# STEP 6: BUILD AND DEPLOY FRONTEND
# =============================================================================

print_status "Step 6: Building and deploying frontend..."

# Install Node.js if needed
if ! command -v node &> /dev/null; then
    print_status "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Build frontend if possible
if [ -f "package.json" ]; then
    npm install
    npm run build:prod
    
    if [ -d "dist/hedge-accounting-sfx" ]; then
        sudo cp -r dist/hedge-accounting-sfx/* /var/www/hedge-agent/
        sudo chown -R www-data:www-data /var/www/hedge-agent
        print_success "Frontend deployed"
    else
        print_warning "Frontend build not found - you may need to build manually"
    fi
else
    print_warning "No package.json found - skipping frontend build"
fi

# =============================================================================
# STEP 7: CONFIGURE FIREWALL
# =============================================================================

print_status "Step 7: Configuring firewall..."

sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8004

print_success "Firewall configured"

# =============================================================================
# COMPLETION
# =============================================================================

print_success "🎉 Internal HTTPS Setup Complete!"
echo ""
echo "📋 SETUP SUMMARY:"
echo "=================="
echo "🔒 SSL Certificate: Self-signed (for internal testing)"
echo "🌐 HTTPS URL: https://$SERVER_IP"
echo "🔗 API: https://$SERVER_IP/api"
echo "💓 Health: https://$SERVER_IP/health"
echo ""
echo "⚠️  BROWSER WARNING:"
echo "===================="
echo "Your browser will show a security warning because this uses"
echo "a self-signed certificate. This is NORMAL for internal testing."
echo ""
echo "To bypass the warning:"
echo "1. Click 'Advanced' or 'More info'"
echo "2. Click 'Proceed to $SERVER_IP (unsafe)' or 'Accept risk'"
echo "3. The connection is still encrypted!"
echo ""
echo "🚀 NEXT STEPS:"
echo "=============="
echo "1. Start the backend:"
echo "   ./start_internal_https_backend.sh"
echo ""
echo "2. Test the setup:"
echo "   curl -k https://$SERVER_IP/health"
echo "   (The -k flag ignores certificate warnings)"
echo ""
echo "3. Open in browser:"
echo "   https://$SERVER_IP"
echo "   (Accept the security warning)"
echo ""
echo "4. Monitor logs:"
echo "   tail -f backend.log"
echo "   sudo tail -f /var/log/nginx/error.log"
echo ""
print_success "Your internal HTTPS testing environment is ready! 🔒"