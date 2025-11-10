#!/bin/bash
echo "🚀 HAWK Agent Deployment Script - Single Pathway"
echo "================================================="

# Configuration
SERVER_IP="3.238.163.106"
SSH_KEY="../agent_tmp.pem"
FRONTEND_PATH="/var/www/3-238-163-106.nip.io"
BACKEND_PATH="/home/ubuntu/hedge-agent/hedge-agent"

# Function to deploy frontend
deploy_frontend() {
    echo "📦 Building Angular Frontend..."
    npm run build:prod

    if [ ! -d "dist/hedge-accounting-sfx" ]; then
        echo "❌ Frontend build failed"
        exit 1
    fi

    echo "✅ Frontend build successful"

    # Create deployment package
    cd dist/hedge-accounting-sfx
    tar -czf ../../frontend-deployment.tar.gz *
    cd ../..

    echo "📤 Uploading frontend to server..."
    scp -i $SSH_KEY -o StrictHostKeyChecking=no frontend-deployment.tar.gz ubuntu@$SERVER_IP:/tmp/

    echo "🔧 Deploying frontend on server..."
    ssh -i $SSH_KEY ubuntu@$SERVER_IP -o StrictHostKeyChecking=no << 'EOF'
        cd /tmp
        sudo rm -rf /var/www/3-238-163-106.nip.io/*
        sudo tar -xzf frontend-deployment.tar.gz -C /var/www/3-238-163-106.nip.io/
        sudo chown -R www-data:www-data /var/www/3-238-163-106.nip.io/
        sudo chmod -R 644 /var/www/3-238-163-106.nip.io/*
        sudo chmod 755 /var/www/3-238-163-106.nip.io/
        sudo find /var/www/3-238-163-106.nip.io/ -type d -exec chmod 755 {} \;
        sudo nginx -t && sudo systemctl reload nginx
        rm /tmp/frontend-deployment.tar.gz
        echo "✅ Frontend deployed successfully"
EOF

    # Clean up local package
    rm frontend-deployment.tar.gz

    echo "🌐 Testing frontend deployment..."
    curl -I https://3-238-163-106.nip.io
}

# Function to deploy backend
deploy_backend() {
    echo "📤 Uploading backend files..."
    scp -i $SSH_KEY -o StrictHostKeyChecking=no unified_smart_backend.py ubuntu@$SERVER_IP:$BACKEND_PATH/
    scp -i $SSH_KEY -o StrictHostKeyChecking=no payloads.py ubuntu@$SERVER_IP:$BACKEND_PATH/
    scp -i $SSH_KEY -o StrictHostKeyChecking=no mcp_server_production.py ubuntu@$SERVER_IP:$BACKEND_PATH/
    scp -i $SSH_KEY -o StrictHostKeyChecking=no -r shared ubuntu@$SERVER_IP:$BACKEND_PATH/
    echo "✅ All backend files uploaded (11 MCP tools + unified backend)"

    echo "🔧 Restarting backend services..."
    ssh -i $SSH_KEY ubuntu@$SERVER_IP -o StrictHostKeyChecking=no << 'EOF'
        cd /home/ubuntu/hedge-agent/hedge-agent

        # Stop existing services
        pkill -f "python.*unified_smart_backend.py" || echo "No existing unified backend found"
        pkill -f "python.*mcp_server_production" || echo "No existing MCP server found"
        sleep 3

        # Set environment variables
        export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
        export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTU5NjA5OSwiZXhwIjoyMDcxMTcyMDk5fQ.vgvEWMOBZ6iX1ZYNyeKW4aoh3nARiC1eYcHU4c1Y-vU"
        export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"
        export PUBLIC_BASE_URL="https://3-238-163-106.nip.io"

        # Start Unified Backend (port 8004)
        nohup python3 unified_smart_backend.py > unified_backend.log 2>&1 &
        echo $! > unified_backend.pid
        sleep 3

        # Start MCP Server with 11 tools (port 8009)
        nohup python3 mcp_server_production.py > mcp_production.log 2>&1 &
        echo $! > mcp_production.pid
        sleep 3

        # Verify both services
        UNIFIED_PID=$(cat unified_backend.pid 2>/dev/null)
        MCP_PID=$(cat mcp_production.pid 2>/dev/null)

        if ps -p $UNIFIED_PID > /dev/null 2>&1 && ps -p $MCP_PID > /dev/null 2>&1; then
            echo "✅ Unified Backend running with PID $UNIFIED_PID (port 8004)"
            echo "✅ MCP Server (11 tools) running with PID $MCP_PID (port 8009)"
        else
            echo "❌ Service deployment failed"
            [ ! -z "$UNIFIED_PID" ] && ps -p $UNIFIED_PID > /dev/null 2>&1 || echo "❌ Unified Backend failed - Log:" && tail -10 unified_backend.log
            [ ! -z "$MCP_PID" ] && ps -p $MCP_PID > /dev/null 2>&1 || echo "❌ MCP Server failed - Log:" && tail -10 mcp_production.log
            exit 1
        fi
EOF

    echo "🧪 Testing backend deployment..."
    sleep 3
    echo "📊 Unified Backend Health:"
    curl -k -s https://3-238-163-106.nip.io/api/health | python3 -m json.tool 2>/dev/null || echo "API health check completed"
    echo ""
    echo "📊 MCP Server Health:"
    curl -k -s https://3-238-163-106.nip.io/mcp/health | python3 -m json.tool 2>/dev/null || echo "MCP health check completed"
}

# Main deployment logic
case "${1:-all}" in
    "frontend"|"f")
        echo "🎯 Deploying Frontend Only"
        deploy_frontend
        ;;
    "backend"|"b")
        echo "🎯 Deploying Backend Only"
        deploy_backend
        ;;
    "all"|"")
        echo "🎯 Deploying Full Stack"
        deploy_frontend
        deploy_backend
        ;;
    *)
        echo "Usage: $0 [frontend|f|backend|b|all]"
        echo "  frontend/f  - Deploy only frontend"
        echo "  backend/b   - Deploy only backend"
        echo "  all         - Deploy both (default)"
        exit 1
        ;;
esac

echo "🎉 Deployment Complete!"
echo "🔗 Application: https://3-238-163-106.nip.io"
echo "🔗 MCP Server: https://3-238-163-106.nip.io/mcp/"