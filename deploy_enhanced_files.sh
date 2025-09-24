#!/bin/bash
# Enhanced Files Deployment Script
# Deploys the optimized hedge backend with proper dependencies

set -e

# Configuration - UPDATE THESE VALUES
EC2_HOST="3.91.170.95"
EC2_USER="ubuntu"
KEY_FILE="agent_hawk.pem"
REMOTE_DIR="/home/ubuntu/hedge_backend"

echo "🚀 Deploying Enhanced Hedge Backend Files..."
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if we have the required files
required_files=(
    "hedge_management_cache_config.py"
    "enhanced_hedge_backend.py"
    "workflow_optimized_backend.py"
    "materialized_views.sql"
    "requirements_complete.txt"
    "table_schemas.txt"
)

print_status "Checking required files..."
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Missing required file: $file"
        exit 1
    fi
    echo "  ✓ $file"
done

# Test SSH connection first
print_status "Testing SSH connection..."
if ! ssh -i "$KEY_FILE" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful'"; then
    print_error "SSH connection failed. Please check:"
    echo "  - EC2 instance IP: $EC2_HOST"
    echo "  - Security group allows SSH (port 22)"
    echo "  - Key file permissions: $(ls -la $KEY_FILE)"
    exit 1
fi

# Create backup of existing deployment
print_status "Creating backup of existing deployment..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    if [ -d '$REMOTE_DIR' ]; then
        sudo cp -r '$REMOTE_DIR' '${REMOTE_DIR}_backup_$(date +%Y%m%d_%H%M%S)'
        echo 'Backup created successfully'
    else
        echo 'No existing deployment found'
    fi
"

# Create remote directory
print_status "Preparing remote directory..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    sudo mkdir -p '$REMOTE_DIR'
    sudo chown ubuntu:ubuntu '$REMOTE_DIR'
"

# Upload files in dependency order
print_status "Uploading files in correct dependency order..."

# 1. First, upload the configuration dependency
print_status "1/6 Uploading cache configuration..."
scp -i "$KEY_FILE" hedge_management_cache_config.py "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"

# 2. Upload table schemas (for reference)
print_status "2/6 Uploading table schemas..."
scp -i "$KEY_FILE" table_schemas.txt "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"

# 3. Upload requirements
print_status "3/6 Uploading requirements..."
scp -i "$KEY_FILE" requirements_complete.txt "$EC2_USER@$EC2_HOST:$REMOTE_DIR/requirements.txt"

# 4. Upload database optimizations
print_status "4/6 Uploading materialized views..."
scp -i "$KEY_FILE" materialized_views.sql "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"

# 5. Upload the enhanced backend (depends on cache config)
print_status "5/6 Uploading enhanced hedge backend..."
scp -i "$KEY_FILE" enhanced_hedge_backend.py "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"

# 6. Upload the workflow optimized backend
print_status "6/6 Uploading workflow optimized backend..."
scp -i "$KEY_FILE" workflow_optimized_backend.py "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"

# Verify uploads
print_status "Verifying uploaded files..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    cd '$REMOTE_DIR'
    echo 'Files in remote directory:'
    ls -la
    echo ''
    echo 'Checking Python imports...'
    python3 -c 'import hedge_management_cache_config; print(\"✓ Cache config imports successfully\")'
"

# Install/update dependencies
print_status "Installing Python dependencies..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    cd '$REMOTE_DIR'
    
    # Create virtual environment if it doesn't exist
    if [ ! -d 'venv' ]; then
        python3 -m venv venv
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo 'Dependencies installed successfully'
"

# Test the enhanced backend
print_status "Testing enhanced backend imports..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" "
    cd '$REMOTE_DIR'
    source venv/bin/activate
    
    python3 -c '
import sys
sys.path.append(\".\")
try:
    from enhanced_hedge_backend import app
    print(\"✓ Enhanced hedge backend imports successfully\")
except Exception as e:
    print(f\"✗ Import error: {e}\")
    exit(1)
'
"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Enhanced Files Deployed Successfully!${NC}"
echo "=========================================="
echo ""
echo "📁 Remote directory: $REMOTE_DIR"
echo "🔧 Next steps:"
echo "   1. Configure environment variables"
echo "   2. Run materialized_views.sql in Supabase"
echo "   3. Start the enhanced backend"
echo ""
echo "🚀 To start the service:"
echo "   ssh -i $KEY_FILE $EC2_USER@$EC2_HOST"
echo "   cd $REMOTE_DIR"
echo "   source venv/bin/activate" 
echo "   python3 enhanced_hedge_backend.py"
echo ""