#!/bin/bash

# Deploy Unified Smart Backend v5.0.0 to AWS Server
# Server: 3.91.170.95
# SSH Key: agent_hawk.pem

echo "🚀 DEPLOYING UNIFIED SMART BACKEND v5.0.0 TO AWS SERVER"
echo "======================================================"
echo ""

# Server configuration
SERVER_IP="3.91.170.95"
SSH_KEY="agent_hawk.pem"
SERVER_USER="ubuntu"
BACKEND_DIR="/home/ubuntu/unified-backend"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    log_error "SSH key '$SSH_KEY' not found in current directory"
    echo "Please ensure agent_hawk.pem is in the current directory"
    exit 1
fi

log_info "SSH key found: $SSH_KEY"

# Test SSH connection
echo "📡 Testing SSH connection to server..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "echo 'Connection successful'" > /dev/null 2>&1; then
    log_info "SSH connection to server successful"
else
    log_error "Cannot connect to server $SERVER_IP"
    echo "Please check:"
    echo "1. SSH key permissions: chmod 400 agent_hawk.pem"
    echo "2. Server IP and connectivity"
    echo "3. Security group allows SSH from your IP"
    exit 1
fi

# Create backend directory on server
echo "📁 Creating backend directory on server..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "mkdir -p $BACKEND_DIR"
log_info "Backend directory created: $BACKEND_DIR"

# Stop any existing backend processes
echo "🛑 Stopping existing backend processes..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "pkill -f 'python.*unified_smart_backend' || true"
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "pkill -f 'python.*backend' || true"
log_info "Existing processes stopped"

# Upload all Python files
echo "📤 Uploading Python backend files..."
scp -i "$SSH_KEY" \
    unified_smart_backend.py \
    payloads.py \
    prompt_intelligence_engine.py \
    smart_data_extractor.py \
    hedge_management_cache_config.py \
    "$SERVER_USER@$SERVER_IP:$BACKEND_DIR/"

if [ $? -eq 0 ]; then
    log_info "Backend files uploaded successfully"
else
    log_error "Failed to upload backend files"
    exit 1
fi

# Upload configuration and documentation files
echo "📋 Uploading configuration and documentation..."
scp -i "$SSH_KEY" \
    optimized_dify_prompt_v2.txt \
    DEPLOYMENT_SUCCESS_REPORT.md \
    DIFY_TRANSFORMATION_ANALYSIS.md \
    FINAL_INTEGRATION_STEPS.md \
    "$SERVER_USER@$SERVER_IP:$BACKEND_DIR/" 2>/dev/null || log_warning "Some documentation files may not exist locally"

# Install dependencies on server
echo "📦 Installing Python dependencies on server..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" << 'EOF'
cd /home/ubuntu/unified-backend
echo "Installing Python packages..."
pip3 install --user fastapi uvicorn[standard] redis supabase httpx python-multipart pydantic
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install some dependencies"
fi
EOF

# Set environment variables and start backend
echo "🚀 Starting Unified Smart Backend on server..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" << 'EOF'
cd /home/ubuntu/unified-backend

# Set environment variables
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
export DIFY_API_KEY='app-juJAFQ9a8QAghx5tACyTvqqG'

echo "🚀 Starting Unified Smart Backend v5.0.0..."
echo "📊 Features: Universal Prompt Processing + Smart Data Extraction + Redis Cache + Dify Integration"
echo "🎯 Goal: Sub-2 second data preparation for ALL prompt types"
echo "🔗 Main Endpoint: http://3.91.170.95:8004/hawk-agent/process-prompt"

# Start backend in background
nohup python3 unified_smart_backend.py > backend.log 2>&1 &
BACKEND_PID=$!

echo "Backend started with PID: $BACKEND_PID"
echo "📄 Logs: tail -f /home/ubuntu/unified-backend/backend.log"

# Wait a few seconds for startup
sleep 5

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend is running successfully"
    echo "🌐 Backend URL: http://3.91.170.95:8004"
    echo "🏥 Health Check: http://3.91.170.95:8004/health"
    echo "📖 API Docs: http://3.91.170.95:8004/docs"
else
    echo "❌ Backend may have failed to start"
    echo "Check logs: tail -20 backend.log"
fi
EOF

# Test the deployed backend
echo ""
echo "🧪 Testing deployed backend..."
sleep 10  # Wait for backend to fully start

echo "Testing health endpoint..."
if curl -s --connect-timeout 10 "http://$SERVER_IP:8004/health" > /dev/null; then
    log_info "Health endpoint responding"
    
    # Get health status
    HEALTH_RESPONSE=$(curl -s "http://$SERVER_IP:8004/health")
    echo "Health Status:"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    
else
    log_warning "Health endpoint not responding yet"
    echo "Backend may still be starting up. Check logs:"
    echo "ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'tail -20 /home/ubuntu/unified-backend/backend.log'"
fi

echo ""
echo "🎉 DEPLOYMENT SUMMARY"
echo "==================="
log_info "Unified Smart Backend v5.0.0 deployed to AWS server"
echo "🌐 Server: http://$SERVER_IP:8004"
echo "📋 Main Endpoint: http://$SERVER_IP:8004/hawk-agent/process-prompt"
echo "🏥 Health Check: http://$SERVER_IP:8004/health"
echo "📊 System Status: http://$SERVER_IP:8004/system/status" 
echo "💾 Cache Stats: http://$SERVER_IP:8004/cache/stats"
echo "📖 API Docs: http://$SERVER_IP:8004/docs"
echo ""
echo "🔧 Server Management Commands:"
echo "SSH to server: ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP"
echo "Check logs: ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'tail -f /home/ubuntu/unified-backend/backend.log'"
echo "Stop backend: ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'pkill -f unified_smart_backend'"
echo ""
echo "🎯 NEXT STEPS:"
echo "1. Update Angular frontend to use: http://$SERVER_IP:8004/hawk-agent/process-prompt"
echo "2. Test with sample requests from Angular HAWK Agent"
echo "3. Monitor performance and cache hit rates"
echo "4. Enjoy sub-2 second response times! 🚀"
echo ""
log_info "Deployment complete!"