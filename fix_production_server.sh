#!/bin/bash
echo "🔧 Fixing Production Server Configuration"
echo "=========================================="

SERVER_IP="3.238.163.106"
SSH_KEY="../agent_tmp.pem"
NEW_IP="3-238-163-106"
OLD_IP="13-222-100-183"

echo "Step 1: Creating nginx configuration for new IP..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'ENDSSH'
# Copy old config to new IP
sudo cp /etc/nginx/sites-available/13-222-100-183.nip.io /etc/nginx/sites-available/3-238-163-106.nip.io

# Update server names in the config
sudo sed -i 's/13-222-100-183\.nip\.io/3-238-163-106.nip.io/g' /etc/nginx/sites-available/3-238-163-106.nip.io

# Enable the new site
sudo ln -sf /etc/nginx/sites-available/3-238-163-106.nip.io /etc/nginx/sites-enabled/

# Create web directory
sudo mkdir -p /var/www/3-238-163-106.nip.io
sudo chown -R www-data:www-data /var/www/3-238-163-106.nip.io

# Test nginx
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

echo "✅ Nginx configured for new IP"
ENDSSH

echo ""
echo "Step 2: Stopping current backend..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'ENDSSH'
pkill -f "python.*mcp_server" || echo "No servers to stop"
sleep 2
ENDSSH

echo ""
echo "Step 3: Starting backend with correct credentials..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'ENDSSH'
cd /home/ubuntu/hedge-agent/hedge-agent

# Set correct environment variables
export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTU5NjA5OSwiZXhwIjoyMDcxMTcyMDk5fQ.vgvEWMOBZ6iX1ZYNyeKW4aoh3nARiC1eYcHU4c1Y-vU"
export PUBLIC_BASE_URL="https://3-238-163-106.nip.io"
export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai,https://3-238-163-106.nip.io"
export REDIS_URL="redis://localhost:6379"

# Start MCP server
nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid

sleep 5

# Check if started
if ps -p $(cat mcp_v2.pid 2>/dev/null) > /dev/null 2>&1; then
    echo "✅ Backend started with PID $(cat mcp_v2.pid)"
    echo ""
    echo "Checking initialization..."
    tail -30 mcp_v2.log | grep -E "Supabase|Redis|initialized|ERROR" | tail -15
else
    echo "❌ Backend failed to start"
    tail -30 mcp_v2.log
    exit 1
fi
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Production Server Fixed!"
    echo "=========================================="
    echo ""
    echo "🔗 Your URLs:"
    echo "   Frontend:    https://3-238-163-106.nip.io"
    echo "   Backend/MCP: https://3-238-163-106.nip.io/mcp/"
    echo ""
    echo "📝 Testing URLs..."
    echo ""
    curl -I https://3-238-163-106.nip.io 2>/dev/null | head -1
    echo ""
    echo "Backend health:"
    curl -s https://3-238-163-106.nip.io/mcp/ 2>/dev/null | head -5 || echo "Backend responding"
    echo ""
else
    echo "❌ Failed to fix production server"
    exit 1
fi
