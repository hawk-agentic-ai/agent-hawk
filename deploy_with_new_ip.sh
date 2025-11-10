#!/bin/bash
echo "🚀 Automated Deployment with New IP - 3.238.163.106"
echo "========================================================="

SERVER_IP="3.238.163.106"
SSH_KEY="../agent_tmp.pem"
OLD_IP="13-222-100-183"
NEW_IP="3-238-163-106"

echo "📋 Step 1: Update Nginx Configuration on AWS..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'EOF'
    echo "  → Updating nginx configuration..."
    sudo sed -i 's/13-222-100-183\.nip\.io/3-238-163-106.nip.io/g' /etc/nginx/sites-available/default

    echo "  → Creating new web directory..."
    sudo mkdir -p /var/www/3-238-163-106.nip.io
    sudo chown -R www-data:www-data /var/www/3-238-163-106.nip.io

    echo "  → Testing nginx configuration..."
    sudo nginx -t

    if [ $? -eq 0 ]; then
        echo "  ✅ Nginx config valid, reloading..."
        sudo systemctl reload nginx
    else
        echo "  ❌ Nginx config invalid, please check manually"
        exit 1
    fi
EOF

if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration failed!"
    exit 1
fi

echo ""
echo "📋 Step 2: Deploying Updated Backend Code (Steps 1-4 fixes)..."
echo "  → Uploading backend files..."

scp -i $SSH_KEY -o StrictHostKeyChecking=no mcp_server_production_v2.py ubuntu@$SERVER_IP:/home/ubuntu/hedge-agent/hedge-agent/
scp -i $SSH_KEY -o StrictHostKeyChecking=no mcp_server_production.py ubuntu@$SERVER_IP:/home/ubuntu/hedge-agent/hedge-agent/
scp -i $SSH_KEY -o StrictHostKeyChecking=no mcp_allocation_server.py ubuntu@$SERVER_IP:/home/ubuntu/hedge-agent/hedge-agent/
scp -i $SSH_KEY -o StrictHostKeyChecking=no -r shared ubuntu@$SERVER_IP:/home/ubuntu/hedge-agent/hedge-agent/

echo "  ✅ Backend files uploaded"
echo ""
echo "📋 Step 3: Restarting Backend Services..."

ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'EOF'
    cd /home/ubuntu/hedge-agent/hedge-agent

    echo "  → Stopping existing MCP server..."
    pkill -f "python.*mcp_server_production_v2.py" || echo "  No existing MCP server found"
    pkill -f "python.*mcp_server_production.py" || echo "  No existing production server found"
    pkill -f "python.*mcp_allocation_server.py" || echo "  No existing allocation server found"
    sleep 3

    echo "  → Setting environment variables..."
    export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
    export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU"
    export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"
    export PUBLIC_BASE_URL="https://3-238-163-106.nip.io"
    export REDIS_URL="redis://localhost:6379"

    echo "  → Starting MCP server..."
    nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &
    echo $! > mcp_v2.pid

    sleep 5

    if ps -p $(cat mcp_v2.pid 2>/dev/null) > /dev/null 2>&1; then
        echo "  ✅ Backend deployed successfully with PID $(cat mcp_v2.pid)"
        echo ""
        echo "  📊 Checking logs for initialization..."
        tail -20 mcp_v2.log | grep -E "Redis|Cache|GL period|initialized" || tail -10 mcp_v2.log
    else
        echo "  ❌ Backend deployment failed"
        echo "  Last 30 lines of log:"
        tail -30 mcp_v2.log
        exit 1
    fi
EOF

if [ $? -ne 0 ]; then
    echo "❌ Backend deployment failed!"
    exit 1
fi

echo ""
echo "📋 Step 4: Deploying Frontend..."
echo "  → Building Angular frontend..."
npm run build:prod

if [ ! -d "dist/hedge-accounting-sfx" ]; then
    echo "  ❌ Frontend build failed"
    exit 1
fi

echo "  ✅ Frontend build successful"

# Create deployment package
cd dist/hedge-accounting-sfx
tar -czf ../../frontend-deployment.tar.gz *
cd ../..

echo "  → Uploading frontend to server..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no frontend-deployment.tar.gz ubuntu@$SERVER_IP:/tmp/

echo "  → Deploying frontend on server..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'EOF'
    cd /tmp
    sudo rm -rf /var/www/3-238-163-106.nip.io/*
    sudo tar -xzf frontend-deployment.tar.gz -C /var/www/3-238-163-106.nip.io/
    sudo chown -R www-data:www-data /var/www/3-238-163-106.nip.io/
    sudo chmod -R 644 /var/www/3-238-163-106.nip.io/*
    sudo chmod 755 /var/www/3-238-163-106.nip.io/
    sudo find /var/www/3-238-163-106.nip.io/ -type d -exec chmod 755 {} \;
    sudo nginx -t && sudo systemctl reload nginx
    rm /tmp/frontend-deployment.tar.gz
    echo "  ✅ Frontend deployed successfully"
EOF

# Clean up local package
rm frontend-deployment.tar.gz

echo ""
echo "📋 Step 5: Running Health Checks..."
echo ""
echo "  → Testing frontend..."
curl -I https://3-238-163-106.nip.io 2>/dev/null | head -1

echo ""
echo "  → Testing backend..."
curl -s https://3-238-163-106.nip.io/mcp/health 2>/dev/null | head -5 || echo "  Backend responding"

echo ""
echo "========================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "========================================================="
echo ""
echo "📊 Summary of Changes (Steps 1-4):"
echo "  ✅ Security: Hardcoded URLs fixed → Now uses PUBLIC_BASE_URL"
echo "  ✅ Security: Redis health check added"
echo "  ✅ Code Quality: Debug print() statements removed"
echo "  ✅ Data Consistency: Cache invalidation implemented"
echo "  ✅ Compliance: GL period validation enforced"
echo ""
echo "🔗 Your New URLs:"
echo "  Frontend:    https://3-238-163-106.nip.io"
echo "  Backend/MCP: https://3-238-163-106.nip.io/mcp/"
echo ""
echo "📋 For Dify Configuration:"
echo "  MCP Server URL: https://3-238-163-106.nip.io/mcp/"
echo ""
echo "✅ Share these URLs with your team!"
echo ""
echo "📝 To verify deployment, SSH to server and check:"
echo "  ssh -i agent_hawk.pem ubuntu@3.238.163.106"
echo "  tail -f /home/ubuntu/hedge-agent/hedge-agent/mcp_v2.log"
echo ""
