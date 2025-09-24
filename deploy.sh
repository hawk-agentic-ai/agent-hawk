#!/bin/bash
echo "🚀 HAWK Agent Deployment Script - Single Pathway"
echo "================================================="

# Configuration
SERVER_IP="13.222.100.183"
SSH_KEY="agent_hawk.pem"
FRONTEND_PATH="/var/www/13-222-100-183.nip.io"
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
        sudo rm -rf /var/www/13-222-100-183.nip.io/*
        sudo tar -xzf frontend-deployment.tar.gz -C /var/www/13-222-100-183.nip.io/
        sudo chown -R www-data:www-data /var/www/13-222-100-183.nip.io/
        sudo chmod -R 644 /var/www/13-222-100-183.nip.io/*
        sudo chmod 755 /var/www/13-222-100-183.nip.io/
        sudo find /var/www/13-222-100-183.nip.io/ -type d -exec chmod 755 {} \;
        sudo nginx -t && sudo systemctl reload nginx
        rm /tmp/frontend-deployment.tar.gz
        echo "✅ Frontend deployed successfully"
EOF

    # Clean up local package
    rm frontend-deployment.tar.gz

    echo "🌐 Testing frontend deployment..."
    curl -I https://13-222-100-183.nip.io
}

# Function to deploy backend
deploy_backend() {
    echo "📤 Uploading backend files..."
    scp -i $SSH_KEY -o StrictHostKeyChecking=no mcp_server_production_v2.py ubuntu@$SERVER_IP:$BACKEND_PATH/
    scp -i $SSH_KEY -o StrictHostKeyChecking=no -r shared ubuntu@$SERVER_IP:$BACKEND_PATH/

    echo "🔧 Restarting backend services..."
    ssh -i $SSH_KEY ubuntu@$SERVER_IP -o StrictHostKeyChecking=no << 'EOF'
        cd /home/ubuntu/hedge-agent/hedge-agent

        # Stop existing MCP server
        pkill -f "python.*mcp_server_production_v2.py" || echo "No existing MCP server found"
        sleep 3

        # Set environment variables
        export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
        export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU"
        export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"

        # Start MCP server
        nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &
        echo $! > mcp_v2.pid

        # Wait and check
        sleep 5
        if ps -p $(cat mcp_v2.pid 2>/dev/null) > /dev/null 2>&1; then
            echo "✅ Backend deployed successfully with PID $(cat mcp_v2.pid)"
        else
            echo "❌ Backend deployment failed"
            tail -20 mcp_v2.log
            exit 1
        fi
EOF

    echo "🧪 Testing backend deployment..."
    sleep 3
    curl -s https://13-222-100-183.nip.io/mcp/health | python3 -m json.tool 2>/dev/null || echo "Backend health check completed"
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
echo "🔗 Application: https://13-222-100-183.nip.io"
echo "🔗 MCP Server: https://13-222-100-183.nip.io/mcp/"