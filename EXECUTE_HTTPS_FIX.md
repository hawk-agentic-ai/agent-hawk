# 🚀 Execute HTTPS Fix - Copy & Paste Commands

## Step 1: Connect to Your Server
```bash
ssh -i agent_hawk.pem ubuntu@3.91.170.95
```

## Step 2: Navigate to Project
```bash
cd /home/ubuntu/hedge-agent || cd /var/www/hedge-agent || find /home -name "hedge-agent" -type d 2>/dev/null | head -1 | xargs cd
```

## Step 3: Download Latest Scripts (if needed)
```bash
# If you don't have the latest scripts, download them:
curl -O https://raw.githubusercontent.com/your-repo/hedge-agent/main/setup_https_production.sh
curl -O https://raw.githubusercontent.com/your-repo/hedge-agent/main/deploy_https_simple.sh
chmod +x *.sh
```

## Step 4: Run HTTPS Setup
```bash
# Make sure scripts are executable
chmod +x setup_https_production.sh deploy_https_simple.sh

# Run the simple setup (will ask for your domain)
./deploy_https_simple.sh
```

## Alternative: Manual Step-by-Step

If the script doesn't work, run these commands one by one:

### Install Nginx & Certbot
```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Get Your Domain Ready
Replace `your-domain.com` with your actual domain:
```bash
DOMAIN_NAME="your-domain.com"  # CHANGE THIS!
```

### Get SSL Certificate
```bash
sudo systemctl stop nginx
sudo certbot certonly --standalone -d $DOMAIN_NAME -d www.$DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
sudo systemctl start nginx
```

### Configure Nginx
```bash
sudo tee /etc/nginx/sites-available/$DOMAIN_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;
    
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Frontend
    root /var/www/$DOMAIN_NAME;
    index index.html;
    
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8004/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With' always;
    }
    
    location /health {
        proxy_pass http://localhost:8004/health;
        proxy_set_header Host \$host;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/$DOMAIN_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Update Backend Environment
```bash
export ALLOWED_ORIGINS="https://$DOMAIN_NAME,https://www.$DOMAIN_NAME"
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
export DIFY_API_KEY='app-juJAFQ9a8QAghx5tACyTvqqG'
```

### Start Backend with HTTPS Support
```bash
# Stop existing backend
pkill -f unified_smart_backend.py || true

# Start with HTTPS environment
nohup python3 unified_smart_backend.py > backend.log 2>&1 &
```

### Build & Deploy Frontend
```bash
# Install Node.js if needed
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Build frontend
npm install
npm run build:prod

# Deploy to web directory
sudo mkdir -p /var/www/$DOMAIN_NAME
sudo cp -r dist/hedge-accounting-sfx/* /var/www/$DOMAIN_NAME/
sudo chown -R www-data:www-data /var/www/$DOMAIN_NAME
```

### Configure Firewall
```bash
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw allow 8004
```

### Test Everything
```bash
# Test SSL
curl -I https://$DOMAIN_NAME

# Test health endpoint
curl https://$DOMAIN_NAME/health

# Test API
curl https://$DOMAIN_NAME/api/system/status
```

## 🎉 Final Result

After running these commands, your application will be available at:
- **Frontend**: `https://your-domain.com` 🔒
- **API**: `https://your-domain.com/api` 🔒
- **Health**: `https://your-domain.com/health` 🔒

No more "Not Secure" warnings! ✅