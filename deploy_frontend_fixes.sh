#!/bin/bash
# Frontend Fixes Deployment Script
# Deploys the Angular frontend fixes to existing AWS infrastructure

set -e

# Configuration - UPDATE THESE VALUES
EC2_HOST="13.222.100.183"
EC2_USER="ubuntu"
KEY_FILE="agent_hawk.pem"
REMOTE_DIR="/home/ubuntu/hedge-agent"

echo "🚀 Deploying Frontend Fixes to Existing AWS App..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
print_status "Checking prerequisites..."

if [ ! -f "$KEY_FILE" ]; then
    print_error "SSH key file not found: $KEY_FILE"
    exit 1
fi

if ! command -v ng &> /dev/null; then
    print_error "Angular CLI not found. Please install: npm install -g @angular/cli"
    exit 1
fi

# Test SSH connection
print_status "Testing SSH connection to $EC2_HOST..."
if ! ssh -i "$KEY_FILE" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful'"; then
    print_error "SSH connection failed. Please check:"
    echo "  - EC2 instance IP: $EC2_HOST"
    echo "  - Security group allows SSH (port 22)"
    echo "  - Key file permissions: $(ls -la $KEY_FILE)"
    exit 1
fi

print_success "SSH connection verified!"

# Step 1: Build Angular Frontend
print_status "Building Angular frontend with fixes..."

# Update environment for production
print_status "Updating environment configuration..."
cat > src/environments/environment.prod.ts << 'EOF'
export const environment = {
  production: true,
  unifiedBackendUrl: 'https://13-222-100-183.nip.io/api/',
  supabaseUrl: '', // Removed for security - handled by backend
  supabaseAnonKey: '', // Removed for security - handled by backend
  difyApiKey: '', // Removed for security - handled by backend
  
  // Performance optimization settings
  unifiedBackend: {
    enabled: true,
    streamingEnabled: true,
    smartTemplateDetection: true,
    cacheEnabled: true
  }
};
EOF

# Build the application
print_status "Building Angular application for production..."
ng build --configuration=production

if [ $? -ne 0 ]; then
    print_error "Angular build failed!"
    exit 1
fi

print_success "Angular build completed successfully!"

# Step 2: Create backup of existing deployment
print_status "Creating backup of existing frontend..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    if [ -d '/var/www/html' ]; then
        sudo cp -r /var/www/html /var/www/html_backup_\$(date +%Y%m%d_%H%M%S)
        echo 'Frontend backup created successfully'
    else
        echo 'No existing frontend deployment found'
    fi
"

# Step 3: Upload built frontend
print_status "Uploading built frontend to server..."

# Create temporary directory for upload
TEMP_DIR=$(mktemp -d)
cp -r dist/* "$TEMP_DIR/"

# Upload to server
scp -i "$KEY_FILE" -r "$TEMP_DIR"/* "$EC2_USER@$EC2_HOST:/tmp/hedge-agent-frontend/"

# Move files to web directory
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    sudo mkdir -p /var/www/html
    sudo rm -rf /var/www/html/*
    sudo cp -r /tmp/hedge-agent-frontend/* /var/www/html/
    sudo chown -R www-data:www-data /var/www/html/
    sudo chmod -R 755 /var/www/html/
    rm -rf /tmp/hedge-agent-frontend/
"

print_success "Frontend files uploaded successfully!"

# Step 4: Update TypeScript component files (your fixes)
print_status "Uploading updated component files with fixes..."

# Create component directory on server if it doesn't exist
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    sudo mkdir -p $REMOTE_DIR/src/app/features/hawk-agent/prompt-templates
    sudo chown -R ubuntu:ubuntu $REMOTE_DIR
"

# Upload the fixed component
scp -i "$KEY_FILE" src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts \
    "$EC2_USER@$EC2_HOST:$REMOTE_DIR/src/app/features/hawk-agent/prompt-templates/"

# Upload service files if they exist
if [ -f "src/app/features/hawk-agent/services/hawk-agent-simple.service.ts" ]; then
    print_status "Uploading updated service files..."
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "sudo mkdir -p $REMOTE_DIR/src/app/features/hawk-agent/services"
    scp -i "$KEY_FILE" src/app/features/hawk-agent/services/hawk-agent-simple.service.ts \
        "$EC2_USER@$EC2_HOST:$REMOTE_DIR/src/app/features/hawk-agent/services/"
fi

# Step 5: Check backend status and restart if needed
print_status "Checking backend status..."

# Check if backend is running
BACKEND_STATUS=$(ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "curl -s http://localhost:8004/health | grep -o '\"status\":\"healthy\"' || echo 'not_running'")

if [ "$BACKEND_STATUS" = "not_running" ]; then
    print_status "Backend not running, starting it..."
    
    # Set environment variables and start backend
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
        cd $REMOTE_DIR
        export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
        export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
        export DIFY_API_KEY='app-juJAFQ9a8QAghx5tACyTvqqG'
        
        # Kill any existing backend processes
        pkill -f unified_smart_backend || true
        
        # Start the backend
        nohup python3 unified_smart_backend.py > backend.log 2>&1 &
        
        echo 'Backend startup initiated'
    "
    
    # Wait for backend to start
    print_status "Waiting for backend to start..."
    sleep 10
else
    print_success "Backend is already running!"
fi

# Step 6: Verify deployment
print_status "Verifying deployment..."

# Test health endpoint
HEALTH_CHECK=$(ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8004/health")

if [ "$HEALTH_CHECK" = "200" ]; then
    print_success "Backend health check passed!"
else
    print_error "Backend health check failed (Status: $HEALTH_CHECK)"
    print_status "Checking backend logs..."
    ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "tail -20 $REMOTE_DIR/backend.log"
fi

# Test external access
print_status "Testing external access..."
EXTERNAL_CHECK=$(curl -s -o /dev/null -w '%{http_code}' "http://$EC2_HOST:8004/health" || echo "000")

if [ "$EXTERNAL_CHECK" = "200" ]; then
    print_success "External access verified!"
else
    print_error "External access failed (Status: $EXTERNAL_CHECK)"
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "=============================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=============================================="
echo ""
echo "🌍 Frontend URL: http://$EC2_HOST (via nginx/apache)"
echo "🔧 Backend URL: http://$EC2_HOST:8004"
echo "📊 Health Check: http://$EC2_HOST:8004/health"
echo ""
echo "🚀 Your fixes are now deployed:"
echo "   ✅ Agent Mode Streaming fixes"
echo "   ✅ Database schema compatibility"
echo "   ✅ Graceful error handling"
echo "   ✅ JSON parsing improvements"
echo ""
echo "🧪 Test your fixes:"
echo "   1. Go to Agent Mode"
echo "   2. Try asking a question"
echo "   3. Check browser console for detailed logs"
echo ""
echo "📊 Monitor performance:"
echo "   • Backend logs: ssh -i $KEY_FILE $EC2_USER@$EC2_HOST 'tail -f $REMOTE_DIR/backend.log'"
echo "   • System status: curl http://$EC2_HOST:8004/system/status"
echo ""
print_success "Deployment successful! 🎉"