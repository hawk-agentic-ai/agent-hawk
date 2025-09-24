#!/bin/bash
# Simple Frontend Deployment Script
# Deploy the built frontend to existing AWS server

set -e

EC2_HOST="3.91.170.95"
EC2_USER="ubuntu"
KEY_FILE="agent_hawk.pem"

echo "🚀 Simple Frontend Deployment..."
echo "==============================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# The build is already done from the previous script, just deploy it

print_status "Creating frontend directory on server..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    sudo mkdir -p /tmp/frontend-upload
    sudo chown ubuntu:ubuntu /tmp/frontend-upload
"

print_status "Uploading built frontend files..."
scp -i "$KEY_FILE" -r dist/* "$EC2_USER@$EC2_HOST:/tmp/frontend-upload/"

print_status "Moving files to web directory..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    sudo mkdir -p /var/www/html
    sudo rm -rf /var/www/html/*
    sudo cp -r /tmp/frontend-upload/* /var/www/html/
    sudo chown -R www-data:www-data /var/www/html/ || sudo chown -R nginx:nginx /var/www/html/ || true
    sudo chmod -R 755 /var/www/html/
    rm -rf /tmp/frontend-upload
"

print_status "Uploading component source files for reference..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    mkdir -p /home/ubuntu/hedge-agent-source/src/app/features/hawk-agent/prompt-templates
    mkdir -p /home/ubuntu/hedge-agent-source/src/app/features/hawk-agent/services
"

scp -i "$KEY_FILE" src/app/features/hawk-agent/prompt-templates/enhanced-prompt-templates-v2.component.ts \
    "$EC2_USER@$EC2_HOST:/home/ubuntu/hedge-agent-source/src/app/features/hawk-agent/prompt-templates/"

if [ -f "src/app/features/hawk-agent/services/hawk-agent-simple.service.ts" ]; then
    scp -i "$KEY_FILE" src/app/features/hawk-agent/services/hawk-agent-simple.service.ts \
        "$EC2_USER@$EC2_HOST:/home/ubuntu/hedge-agent-source/src/app/features/hawk-agent/services/"
fi

print_status "Checking backend status..."
HEALTH_CHECK=$(ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8004/health")

if [ "$HEALTH_CHECK" = "200" ]; then
    print_success "Backend is healthy!"
else
    print_status "Backend status code: $HEALTH_CHECK - may need restart"
fi

print_success "Frontend deployment complete!"
print_status "Your fixes are now deployed to: http://$EC2_HOST"
print_status "Backend API: http://$EC2_HOST:8004"