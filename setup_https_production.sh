#!/bin/bash

# =============================================================================
# HTTPS Production Setup Script
# Comprehensive SSL certificate setup with Let's Encrypt and Nginx configuration
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get server IP
SERVER_IP=$(curl -s http://checkip.amazonaws.com/ || echo "3.91.170.95")
BACKEND_PORT=8004
FRONTEND_PORT=80
SSL_PORT=443

print_status "Starting HTTPS Production Setup for Hedge Agent"
print_status "Server IP: $SERVER_IP"

# Get domain name from user
echo ""
read -p "Enter your domain name (e.g., hedgeagent.com): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    print_error "Domain name is required for SSL certificate"
    exit 1
fi

print_status "Domain: $DOMAIN_NAME"
print_status "This script will:"
echo "  1. Install and configure Nginx"
echo "  2. Set up Let's Encrypt SSL certificate"
echo "  3. Configure reverse proxy for backend"
echo "  4. Update application URLs to HTTPS"
echo "  5. Set up automatic SSL renewal"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Setup cancelled by user"
    exit 0
fi

# =============================================================================
# STEP 1: INSTALL NGINX AND DEPENDENCIES
# =============================================================================

print_status "Step 1: Installing Nginx and dependencies..."

# Update package list
sudo apt update

# Install Nginx
sudo apt install -y nginx

# Install Certbot for Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx

# Enable Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

print_success "Nginx and Certbot installed"

# =============================================================================
# STEP 2: CONFIGURE NGINX
# =============================================================================

print_status "Step 2: Configuring Nginx for domain $DOMAIN_NAME..."

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/$DOMAIN_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;
    
    # Temporary root for Let's Encrypt validation
    root /var/www/html;
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;
    
    # SSL certificates (will be added by certbot)
    # ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Frontend static files
    root /var/www/$DOMAIN_NAME;
    index index.html;
    
    # Frontend routing (Angular)
    location / {
        try_files \$uri \$uri/ /index.html;
        
        # CORS headers for frontend
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With' always;
    }
    
    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:$BACKEND_PORT/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
        
        # CORS headers for API
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
    
    # Health check endpoint
    location /health {
        proxy_pass http://localhost:$BACKEND_PORT/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/$DOMAIN_NAME /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

print_success "Nginx configured for domain $DOMAIN_NAME"

# =============================================================================
# STEP 3: GET SSL CERTIFICATE
# =============================================================================

print_status "Step 3: Obtaining SSL certificate from Let's Encrypt..."

# Stop Nginx temporarily for certificate generation
sudo systemctl stop nginx

# Get the certificate
sudo certbot certonly --standalone -d $DOMAIN_NAME -d www.$DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME

if [ $? -eq 0 ]; then
    print_success "SSL certificate obtained successfully"
else
    print_error "Failed to obtain SSL certificate"
    print_warning "Make sure your domain points to $SERVER_IP"
    exit 1
fi

# Update Nginx config with SSL
sudo sed -i "s|# ssl_certificate|ssl_certificate|g" /etc/nginx/sites-available/$DOMAIN_NAME
sudo sed -i "s|# ssl_certificate_key|ssl_certificate_key|g" /etc/nginx/sites-available/$DOMAIN_NAME

# Start Nginx
sudo systemctl start nginx

# Set up automatic renewal
sudo systemctl enable certbot.timer

print_success "SSL certificate configured and auto-renewal enabled"

# =============================================================================
# STEP 4: CREATE FRONTEND DIRECTORY
# =============================================================================

print_status "Step 4: Setting up frontend directory..."

# Create web directory
sudo mkdir -p /var/www/$DOMAIN_NAME

# Set ownership
sudo chown -R ubuntu:ubuntu /var/www/$DOMAIN_NAME

print_success "Frontend directory created at /var/www/$DOMAIN_NAME"

# =============================================================================
# STEP 5: UPDATE APPLICATION CONFIGURATION
# =============================================================================

print_status "Step 5: Updating application configuration for HTTPS..."

# Update Angular environment files
cat > src/environments/environment.ts <<EOF
export const environment = {
  production: false,
  apiUrl: 'https://$DOMAIN_NAME/api',
  unifiedBackendUrl: 'https://$DOMAIN_NAME/api',
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

cat > src/environments/environment.prod.ts <<EOF
export const environment = {
  production: true,
  unifiedBackendUrl: 'https://$DOMAIN_NAME/api',
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

print_success "Angular environment files updated for HTTPS"

# =============================================================================
# STEP 6: UPDATE BACKEND CORS
# =============================================================================

print_status "Step 6: Updating backend CORS configuration..."

# Create updated backend startup script
cat > start_https_backend.sh <<EOF
#!/bin/bash

# HTTPS Production Backend Startup Script

# Set environment variables
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
export DIFY_API_KEY='app-juJAFQ9a8QAghx5tACyTvqqG'

# CORS configuration for HTTPS
export ALLOWED_ORIGINS='https://$DOMAIN_NAME,https://www.$DOMAIN_NAME'

# Start the backend
echo "Starting HTTPS backend on port $BACKEND_PORT..."
python3 unified_smart_backend.py
EOF

chmod +x start_https_backend.sh

print_success "Backend HTTPS startup script created"

# =============================================================================
# STEP 7: BUILD AND DEPLOY FRONTEND
# =============================================================================

print_status "Step 7: Building and deploying frontend..."

# Install Node.js if not present
if ! command -v node &> /dev/null; then
    print_status "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Install dependencies and build
npm install
npm run build:prod

# Copy built files to web directory
sudo cp -r dist/hedge-accounting-sfx/* /var/www/$DOMAIN_NAME/

# Set correct permissions
sudo chown -R www-data:www-data /var/www/$DOMAIN_NAME

print_success "Frontend built and deployed"

# =============================================================================
# STEP 8: FIREWALL CONFIGURATION
# =============================================================================

print_status "Step 8: Configuring firewall..."

# Configure UFW firewall
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw allow $BACKEND_PORT

print_success "Firewall configured"

# =============================================================================
# STEP 9: FINAL VERIFICATION
# =============================================================================

print_status "Step 9: Final verification and testing..."

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Test SSL certificate
echo "Testing SSL certificate..."
if curl -s https://$DOMAIN_NAME/health > /dev/null; then
    print_success "HTTPS is working correctly!"
else
    print_warning "HTTPS test failed - backend might not be running"
fi

# =============================================================================
# COMPLETION SUMMARY
# =============================================================================

print_success "🎉 HTTPS Production Setup Complete!"
echo ""
echo "📋 DEPLOYMENT SUMMARY:"
echo "======================"
echo "🌐 Domain: https://$DOMAIN_NAME"
echo "🔒 SSL Certificate: ✓ Installed with Let's Encrypt"
echo "🔄 Auto-renewal: ✓ Enabled"
echo "🖥️  Frontend: https://$DOMAIN_NAME"
echo "🔗 API: https://$DOMAIN_NAME/api"
echo "💓 Health: https://$DOMAIN_NAME/health"
echo ""
echo "📁 FILES UPDATED:"
echo "=================="
echo "✓ Nginx config: /etc/nginx/sites-available/$DOMAIN_NAME"
echo "✓ Frontend: /var/www/$DOMAIN_NAME"
echo "✓ Environment files: src/environments/"
echo "✓ HTTPS backend script: start_https_backend.sh"
echo ""
echo "🚀 NEXT STEPS:"
echo "=============="
echo "1. Start the backend with HTTPS support:"
echo "   ./start_https_backend.sh"
echo ""
echo "2. Verify your domain DNS points to: $SERVER_IP"
echo ""
echo "3. Test your application:"
echo "   curl https://$DOMAIN_NAME/health"
echo ""
echo "4. Monitor logs:"
echo "   sudo tail -f /var/log/nginx/access.log"
echo "   sudo tail -f /var/log/nginx/error.log"
echo ""
print_success "Your application is now secure with HTTPS! 🔒"