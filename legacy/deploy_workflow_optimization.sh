#!/bin/bash

# =====================================================================
# HAWK Agent Workflow-Optimized Deployment Script
# Deploy precision-tuned backend for 11 core hedge accounting workflows
# =====================================================================

set -e  # Exit on any error

echo "🚀 Starting HAWK Agent Workflow-Optimized Deployment..."
echo "======================================================"

# Configuration
DEPLOYMENT_DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="/home/ubuntu/hawk_backups/$DEPLOYMENT_DATE"
PROJECT_DIR="/home/ubuntu/hawk_backend"
SERVICE_NAME="hawk-workflow-backend"
PYTHON_ENV="/home/ubuntu/hawk_venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =====================================================================
# 1. PRE-DEPLOYMENT BACKUP
# =====================================================================

backup_existing_deployment() {
    print_status "Creating backup of existing deployment..."
    
    if [ -d "$PROJECT_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        cp -r "$PROJECT_DIR" "$BACKUP_DIR/hawk_backend_backup"
        print_success "Backup created at $BACKUP_DIR"
    else
        print_warning "No existing deployment found to backup"
    fi
}

# =====================================================================
# 2. ENVIRONMENT PREPARATION
# =====================================================================

prepare_environment() {
    print_status "Preparing deployment environment..."
    
    # Create project directory
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # Create Python virtual environment if it doesn't exist
    if [ ! -d "$PYTHON_ENV" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv "$PYTHON_ENV"
    fi
    
    # Activate virtual environment
    source "$PYTHON_ENV/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Environment prepared"
}

# =====================================================================
# 3. INSTALL DEPENDENCIES
# =====================================================================

install_dependencies() {
    print_status "Installing workflow-optimized dependencies..."
    
    source "$PYTHON_ENV/bin/activate"
    
    # Core dependencies for workflow optimization
    pip install \
        fastapi==0.104.1 \
        uvicorn[standard]==0.24.0 \
        supabase==2.3.4 \
        redis==5.0.1 \
        pydantic==2.5.2 \
        python-multipart==0.0.6 \
        python-jose[cryptography]==3.3.0 \
        passlib[bcrypt]==1.7.4 \
        httpx==0.24.1 \
        asyncio-mqtt==0.13.0 \
        python-dotenv==1.0.0 \
        psycopg2-binary==2.9.9 \
        pandas==2.1.4 \
        numpy==1.26.2 \
        asyncpg==0.29.0
    
    print_success "Dependencies installed"
}

# =====================================================================
# 4. DEPLOY WORKFLOW-OPTIMIZED BACKEND
# =====================================================================

deploy_backend() {
    print_status "Deploying workflow-optimized backend..."
    
    # Copy the workflow-optimized backend file
    if [ -f "$HOME/workflow_optimized_backend.py" ]; then
        cp "$HOME/workflow_optimized_backend.py" "$PROJECT_DIR/main.py"
        print_success "Backend application deployed"
    elif [ -f "workflow_optimized_backend.py" ]; then
        cp "workflow_optimized_backend.py" "$PROJECT_DIR/main.py"
        print_success "Backend application deployed"
    else
        print_error "workflow_optimized_backend.py not found in current directory or home directory!"
        echo "Current directory: $(pwd)"
        echo "Home directory: $HOME"
        echo "Looking for files:"
        ls -la *.py 2>/dev/null || echo "No Python files found"
        exit 1
    fi
    
    # Create requirements.txt
    source "$PYTHON_ENV/bin/activate"
    pip freeze > "$PROJECT_DIR/requirements.txt"
    
    # Create configuration directory
    mkdir -p "$PROJECT_DIR/config"
    
    # Create environment file template
    cat > "$PROJECT_DIR/.env.template" << EOF
# HAWK Agent Workflow-Optimized Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
HAWK_ENV=production
LOG_LEVEL=INFO
MAX_CACHE_SIZE=1000000
CACHE_DEFAULT_TTL=3600

# Performance tuning
UVICORN_WORKERS=4
UVICORN_MAX_REQUESTS=10000
UVICORN_TIMEOUT=300
UVICORN_KEEPALIVE=2

# Database connection pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
EOF
    
    print_success "Backend configuration prepared"
}

# =====================================================================
# 5. DEPLOY MATERIALIZED VIEWS
# =====================================================================

deploy_database_optimizations() {
    print_status "Deploying database materialized views..."
    
    if [ -f "materialized_views.sql" ]; then
        cp materialized_views.sql "$PROJECT_DIR/database/"
        mkdir -p "$PROJECT_DIR/database"
        
        print_status "Materialized views SQL script deployed"
        print_warning "Run the materialized_views.sql script in your Supabase SQL editor to create performance views"
    else
        print_warning "materialized_views.sql not found - skipping database optimizations"
    fi
}

# =====================================================================
# 6. CONFIGURE SYSTEMD SERVICE
# =====================================================================

configure_systemd_service() {
    print_status "Configuring systemd service for workflow backend..."
    
    # Create systemd service file
    sudo tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null << EOF
[Unit]
Description=HAWK Agent Workflow-Optimized Backend
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PYTHON_ENV/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PYTHON_ENV/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --access-log --reload
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=hawk-workflow-backend

# Resource limits for performance
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    print_success "Systemd service configured"
}

# =====================================================================
# 7. CONFIGURE NGINX REVERSE PROXY
# =====================================================================

configure_nginx() {
    print_status "Configuring NGINX reverse proxy for workflow backend..."
    
    # Create NGINX configuration
    sudo tee "/etc/nginx/sites-available/hawk-workflow-backend" > /dev/null << EOF
# HAWK Agent Workflow-Optimized Backend
server {
    listen 80;
    server_name _;
    
    # Rate limiting for API protection
    limit_req_zone \$binary_remote_addr zone=hawk_api:10m rate=100r/s;
    limit_req_status 429;
    
    # Main API routes
    location /api/ {
        limit_req zone=hawk_api burst=200 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeout settings for long-running queries
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffer settings for large responses
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # Enable gzip compression
        gzip on;
        gzip_types
            text/plain
            text/css
            text/js
            text/xml
            text/javascript
            application/javascript
            application/json
            application/xml+rss;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/api/v2/health;
        proxy_set_header Host \$host;
        access_log off;
    }
    
    # Cache performance endpoint  
    location /cache-stats {
        proxy_pass http://127.0.0.1:8000/api/v2/cache/stats;
        proxy_set_header Host \$host;
        
        # Cache this response for 30 seconds
        proxy_cache_valid 200 30s;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # CORS headers for frontend
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;
    
    # Handle preflight requests
    location ~* \.(options)$ {
        add_header Access-Control-Allow-Origin "*";
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
        add_header Access-Control-Max-Age 1728000;
        add_header Content-Type "text/plain; charset=utf-8";
        add_header Content-Length 0;
        return 204;
    }
}
EOF
    
    # Enable the site
    sudo ln -sf /etc/nginx/sites-available/hawk-workflow-backend /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload NGINX
    sudo nginx -t
    sudo systemctl reload nginx
    
    print_success "NGINX reverse proxy configured"
}

# =====================================================================
# 8. CONFIGURE REDIS FOR CACHING
# =====================================================================

configure_redis() {
    print_status "Optimizing Redis for workflow caching..."
    
    # Create Redis configuration for HAWK
    sudo tee "/etc/redis/redis-hawk.conf" > /dev/null << EOF
# HAWK Agent Redis Configuration
port 6379
bind 127.0.0.1
timeout 300

# Memory optimization for caching
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence for workflow cache
save 900 1
save 300 10
save 60 10000

# Performance tuning
tcp-keepalive 300
tcp-nodelay yes
databases 16

# Logging
loglevel notice
logfile /var/log/redis/redis-hawk.log

# Security
protected-mode yes
requirepass hawk_cache_2024

# Clients and connections
timeout 0
tcp-keepalive 300
maxclients 1000
EOF
    
    # Restart Redis with new configuration
    sudo systemctl restart redis-server
    sudo systemctl enable redis-server
    
    print_success "Redis optimized for workflow caching"
}

# =====================================================================
# 9. PERFORMANCE MONITORING SETUP
# =====================================================================

setup_monitoring() {
    print_status "Setting up performance monitoring..."
    
    # Create monitoring directory
    mkdir -p "$PROJECT_DIR/monitoring"
    
    # Create performance monitoring script
    cat > "$PROJECT_DIR/monitoring/hawk_monitor.py" << 'EOF'
#!/usr/bin/env python3
"""
HAWK Agent Performance Monitor
Real-time monitoring for workflow-optimized backend
"""

import asyncio
import redis
import requests
import json
import time
from datetime import datetime

class HawkMonitor:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.backend_url = 'http://localhost:8000'
        
    async def check_cache_performance(self):
        """Monitor cache hit ratios and performance"""
        try:
            response = requests.get(f'{self.backend_url}/api/v2/cache/stats')
            if response.status_code == 200:
                stats = response.json()
                hit_ratio = stats.get('hit_ratio', {}).get('ratio', 0)
                
                print(f"[{datetime.now()}] Cache Hit Ratio: {hit_ratio:.2%}")
                return stats
        except Exception as e:
            print(f"Cache monitoring error: {e}")
            return None
    
    async def check_backend_health(self):
        """Monitor backend health and response times"""
        try:
            start_time = time.time()
            response = requests.get(f'{self.backend_url}/api/v2/health')
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                health = response.json()
                print(f"[{datetime.now()}] Backend Health: {health.get('status')} ({response_time:.2f}ms)")
                return health
        except Exception as e:
            print(f"Health check error: {e}")
            return None
    
    async def monitor_redis_memory(self):
        """Monitor Redis memory usage"""
        try:
            info = self.redis_client.info('memory')
            used_memory = info.get('used_memory_human', '0B')
            max_memory = info.get('maxmemory_human', 'unlimited')
            
            print(f"[{datetime.now()}] Redis Memory: {used_memory} / {max_memory}")
            return info
        except Exception as e:
            print(f"Redis monitoring error: {e}")
            return None
    
    async def run_monitoring(self, interval=30):
        """Run continuous monitoring"""
        print("🔍 Starting HAWK Agent Performance Monitoring...")
        
        while True:
            await self.check_backend_health()
            await self.check_cache_performance()
            await self.monitor_redis_memory()
            print("-" * 60)
            
            await asyncio.sleep(interval)

if __name__ == '__main__':
    monitor = HawkMonitor()
    asyncio.run(monitor.run_monitoring())
EOF
    
    chmod +x "$PROJECT_DIR/monitoring/hawk_monitor.py"
    
    # Create monitoring service
    sudo tee "/etc/systemd/system/hawk-monitor.service" > /dev/null << EOF
[Unit]
Description=HAWK Agent Performance Monitor
After=network.target hawk-workflow-backend.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$PROJECT_DIR/monitoring
Environment=PATH=$PYTHON_ENV/bin
ExecStart=$PYTHON_ENV/bin/python3 hawk_monitor.py
Restart=always
RestartSec=30
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=hawk-monitor

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable hawk-monitor
    
    print_success "Performance monitoring configured"
}

# =====================================================================
# 10. START SERVICES
# =====================================================================

start_services() {
    print_status "Starting optimized HAWK services..."
    
    # Stop existing services if running
    sudo systemctl stop hawk-workflow-backend 2>/dev/null || true
    sudo systemctl stop hawk-monitor 2>/dev/null || true
    
    # Start services in order
    sudo systemctl start redis-server
    sudo systemctl start "$SERVICE_NAME"
    sudo systemctl start hawk-monitor
    sudo systemctl reload nginx
    
    # Wait a moment for services to start
    sleep 5
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "HAWK Workflow Backend is running"
    else
        print_error "Failed to start HAWK Workflow Backend"
        sudo systemctl status "$SERVICE_NAME"
        exit 1
    fi
    
    if systemctl is-active --quiet hawk-monitor; then
        print_success "Performance Monitor is running"
    else
        print_warning "Performance Monitor failed to start"
    fi
}

# =====================================================================
# 11. DEPLOYMENT VERIFICATION
# =====================================================================

verify_deployment() {
    print_status "Verifying deployment..."
    
    # Test health endpoint
    sleep 10  # Give services time to fully start
    
    if curl -s "http://localhost/health" | grep -q "healthy"; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        curl -s "http://localhost/health" || echo "Connection failed"
    fi
    
    # Test cache stats endpoint
    if curl -s "http://localhost/api/v2/cache/stats" | grep -q "hit_ratio"; then
        print_success "Cache system operational"
    else
        print_warning "Cache system may not be fully operational"
    fi
    
    # Display service status
    echo ""
    echo "=== Service Status ==="
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
    
    echo ""
    echo "=== Performance Monitoring ==="
    sudo systemctl status hawk-monitor --no-pager -l
}

# =====================================================================
# 12. POST-DEPLOYMENT INFORMATION
# =====================================================================

display_deployment_info() {
    echo ""
    echo "========================================================"
    echo -e "${GREEN}🎉 HAWK Workflow-Optimized Deployment Complete!${NC}"
    echo "========================================================"
    echo ""
    echo "📋 Deployment Summary:"
    echo "  • Backend URL: http://$(curl -s http://checkip.amazonaws.com)/"
    echo "  • Health Check: http://$(curl -s http://checkip.amazonaws.com)/health"
    echo "  • Cache Stats: http://$(curl -s http://checkip.amazonaws.com)/api/v2/cache/stats"
    echo "  • Project Directory: $PROJECT_DIR"
    echo "  • Python Environment: $PYTHON_ENV"
    echo ""
    echo "🔧 Configuration Files:"
    echo "  • Environment: $PROJECT_DIR/.env (needs configuration)"
    echo "  • Systemd Service: /etc/systemd/system/$SERVICE_NAME.service"
    echo "  • NGINX Config: /etc/nginx/sites-available/hawk-workflow-backend"
    echo "  • Redis Config: /etc/redis/redis-hawk.conf"
    echo ""
    echo "🚨 Next Steps:"
    echo "  1. Configure environment variables in $PROJECT_DIR/.env"
    echo "  2. Run materialized_views.sql in Supabase SQL editor"
    echo "  3. Test API endpoints for your 11 core workflows"
    echo "  4. Monitor performance using: sudo journalctl -u hawk-monitor -f"
    echo ""
    echo "📊 API Endpoints for Core Workflows:"
    echo "  • Hedge Instructions: POST /api/v2/hedge-instructions/validate"
    echo "  • Available Amounts: POST /api/v2/available-amounts/calculate" 
    echo "  • Deal Bookings: POST /api/v2/deal-bookings/by-order"
    echo "  • USD PB Capacity: POST /api/v2/usd-pb-deposits/capacity-check"
    echo "  • Hedge Adjustments: GET /api/v2/gl-entries/hedge-adjustments/{currency}"
    echo ""
    echo "📈 Performance Features:"
    echo "  • Multi-tier Redis caching (3min to 24hr TTL)"
    echo "  • 9 materialized views for complex queries"
    echo "  • Parallel database queries with asyncio"
    echo "  • Real-time cache performance monitoring"
    echo "  • Workflow-specific optimization for 11 core operations"
    echo ""
    echo -e "${BLUE}Deployment completed at: $(date)${NC}"
    echo "========================================================"
}

# =====================================================================
# MAIN DEPLOYMENT FLOW
# =====================================================================

main() {
    echo "Starting HAWK Agent Workflow-Optimized Deployment..."
    
    backup_existing_deployment
    prepare_environment
    install_dependencies
    deploy_backend
    deploy_database_optimizations
    configure_systemd_service
    configure_nginx
    configure_redis
    setup_monitoring
    start_services
    verify_deployment
    display_deployment_info
    
    print_success "HAWK Agent Workflow-Optimized Backend deployed successfully! 🚀"
}

# Run main deployment
main "$@"