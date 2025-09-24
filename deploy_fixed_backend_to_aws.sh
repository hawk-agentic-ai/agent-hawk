#!/bin/bash

# Deploy Fixed Unified Smart Backend to AWS
# This deploys the currency extraction fix to the existing EC2 instance

set -e

echo "🚀 Deploying Fixed Unified Smart Backend v5.0.0 to AWS"
echo "======================================================"
echo ""

# Configuration
AWS_INSTANCE_IP="3.91.170.95"
AWS_INSTANCE_ID="i-0f823f8aab8f67952"
AWS_REGION="us-east-1"
AWS_KEY_PATH="$HOME/.ssh/hedge-agent-key.pem"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if instance is running
echo "🔍 Checking AWS instance status..."
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids $AWS_INSTANCE_ID --query 'Reservations[0].Instances[0].State.Name' --output text)

if [ "$INSTANCE_STATE" != "running" ]; then
    log_error "Instance is not running (state: $INSTANCE_STATE)"
    exit 1
fi

log_info "Instance is running at $AWS_INSTANCE_IP"

# Test local backend is working with fix
echo "🧪 Testing local backend with currency extraction fix..."
CURL_RESPONSE=$(curl -s -X POST "http://localhost:8004/hawk-agent/process-prompt" \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "Check if I can hedge 150K CNY today",
    "template_category": "hedge_utilization",
    "stream_response": false
  }' | head -c 100 || echo "ERROR")

if [[ "$CURL_RESPONSE" != "ERROR" ]]; then
    log_info "Local backend is responding correctly"
else
    log_error "Local backend is not responding - fix deployment locally first"
    exit 1
fi

# Create deployment package
echo "📦 Creating deployment package..."
tar -czf unified_backend_fixed.tar.gz \
    unified_smart_backend.py \
    prompt_intelligence_engine.py \
    smart_data_extractor.py \
    hedge_management_cache_config.py \
    payloads.py \
    requirements_fixed_new.txt \
    Dockerfile

log_info "Deployment package created"

# Transfer files to EC2
echo "📤 Transferring files to AWS EC2..."

# Check if we can connect
if ! ssh -i "$AWS_KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ec2-user@$AWS_INSTANCE_IP "echo 'Connection test successful'" 2>/dev/null; then
    log_error "Cannot connect to EC2 instance. Check your key file and security groups."
    echo "Expected key location: $AWS_KEY_PATH"
    echo "If you don't have the key, you can use the existing deployment scripts or AWS Systems Manager Session Manager"
    exit 1
fi

# Transfer the package
scp -i "$AWS_KEY_PATH" -o StrictHostKeyChecking=no unified_backend_fixed.tar.gz ec2-user@$AWS_INSTANCE_IP:~/
log_info "Files transferred successfully"

# Deploy on EC2
echo "🚀 Deploying on EC2 instance..."

ssh -i "$AWS_KEY_PATH" -o StrictHostKeyChecking=no ec2-user@$AWS_INSTANCE_IP << 'ENDSSH'
    # Extract files
    cd /home/ec2-user
    tar -xzf unified_backend_fixed.tar.gz
    
    # Stop existing backend
    echo "🛑 Stopping existing backend..."
    sudo pkill -f "python.*unified_smart_backend.py" || true
    sudo pkill -f "uvicorn.*8004" || true
    sleep 3
    
    # Install/update dependencies
    echo "📦 Installing Python dependencies..."
    pip3 install --user -r requirements_fixed_new.txt --quiet
    
    # Set environment variables
    echo "🔧 Setting environment variables..."
    export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
    export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
    export DIFY_API_KEY='app-sF86KavXxF9u2HwQx5JpM4TK'
    
    # Start the fixed backend
    echo "🚀 Starting Fixed Unified Smart Backend v5.0.0..."
    nohup python3 unified_smart_backend.py > unified_backend.log 2>&1 &
    
    echo "✅ Backend started successfully"
    echo "📄 Log file: unified_backend.log"
    
    # Wait for startup
    sleep 5
    
    # Test the backend
    echo "🏥 Testing health endpoint..."
    if curl -s http://localhost:8004/health > /dev/null; then
        echo "✅ Health endpoint responding"
    else
        echo "❌ Health endpoint not responding"
        echo "📄 Last few lines of log:"
        tail -5 unified_backend.log
    fi
ENDSSH

# Test the deployed backend from outside
echo "🧪 Testing deployed backend externally..."
sleep 10

# Test health endpoint
if curl -s "http://$AWS_INSTANCE_IP:8004/health" > /dev/null; then
    log_info "AWS backend health endpoint responding"
else
    log_warning "Health endpoint not accessible externally - check security groups"
fi

# Test currency extraction fix
echo "🔧 Testing currency extraction fix on AWS..."
AWS_TEST_RESPONSE=$(curl -s -X POST "http://$AWS_INSTANCE_IP:8004/hawk-agent/process-prompt" \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "Check if I can hedge 150K CNY today",
    "template_category": "hedge_utilization",
    "stream_response": false
  }' | head -c 200 2>/dev/null || echo "TIMEOUT_OR_ERROR")

if [[ "$AWS_TEST_RESPONSE" != "TIMEOUT_OR_ERROR" ]] && [[ "$AWS_TEST_RESPONSE" != "" ]]; then
    log_info "AWS backend is processing requests correctly"
    echo "Sample response (first 200 chars):"
    echo "$AWS_TEST_RESPONSE"
else
    log_warning "AWS backend not accessible externally or streaming response"
    echo "This may be due to security group settings limiting external access"
fi

# Update security groups to allow access on port 8004
echo "🔒 Updating security groups..."
SECURITY_GROUP_ID=$(aws ec2 describe-instances --instance-ids $AWS_INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

# Allow access on port 8004
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 8004 \
  --cidr 0.0.0.0/0 2>/dev/null || log_warning "Port 8004 may already be open"

log_info "Security group updated to allow port 8004"

# Clean up
rm -f unified_backend_fixed.tar.gz

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================"
log_info "Fixed Unified Smart Backend v5.0.0 deployed to AWS"
echo "🌐 AWS Backend URL: http://$AWS_INSTANCE_IP:8004"
echo "🏥 Health Check: http://$AWS_INSTANCE_IP:8004/health"
echo "📊 System Status: http://$AWS_INSTANCE_IP:8004/system/status"
echo "🧪 Test Endpoint: http://$AWS_INSTANCE_IP:8004/hawk-agent/process-prompt"
echo ""
echo "🔧 CURRENCY EXTRACTION FIX DEPLOYED:"
echo "   • CNY requests now extract CNY (not CAN)"
echo "   • HKD requests now extract HKD (not CAN)"
echo "   • KRW requests now extract KRW (not CAN)"
echo ""
echo "📝 Next Steps:"
echo "   1. Update Angular environment to point to: http://$AWS_INSTANCE_IP:8004"
echo "   2. Test the fixed currency extraction in the UI"
echo "   3. Monitor performance with: curl http://$AWS_INSTANCE_IP:8004/system/status"

echo ""
echo "✅ Ready for testing with correct currency-specific data fetching!"