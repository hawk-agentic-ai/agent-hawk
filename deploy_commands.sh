#!/bin/bash
set -e

cd /home/ec2-user

# Download the deployment package
aws s3 cp s3://hedge-agent-deployment-1757056539/unified_backend_fixed.tar.gz .

# Extract files
tar -xzf unified_backend_fixed.tar.gz

# Stop existing backend
echo "🛑 Stopping existing backend..."
sudo pkill -f "python.*unified_smart_backend.py" || true
sudo pkill -f "uvicorn.*8004" || true
sleep 3

# Install/update dependencies
echo "📦 Installing Python dependencies..."
pip3 install --user -r requirements_fixed_new.txt --quiet

# Set environment variables and start backend
echo "🚀 Starting Fixed Unified Smart Backend v5.0.0..."
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
export DIFY_API_KEY='app-sF86KavXxF9u2HwQx5JpM4TK'

nohup python3 unified_smart_backend.py > unified_backend.log 2>&1 &

echo "✅ Backend started"
sleep 5

# Test health endpoint
if curl -s http://localhost:8004/health > /dev/null; then
    echo "✅ Health endpoint responding"
else
    echo "❌ Health endpoint not responding"
    tail -5 unified_backend.log
fi

# Clean up
rm -f unified_backend_fixed.tar.gz

echo "🎉 Deployment completed successfully!"
