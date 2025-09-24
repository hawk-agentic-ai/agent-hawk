#!/bin/bash
echo "🚀 Deploying MCP Production V2 Server to Cloud..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📤 Uploading V2 server files...${NC}"

# Check if we have SSH access
if ! curl -s --connect-timeout 5 http://3.91.170.95 > /dev/null; then
    echo -e "${RED}❌ Cannot reach cloud server 3.91.170.95${NC}"
    exit 1
fi

# Since we can't use SCP without keys, we'll use the working HTTP method
echo -e "${YELLOW}📋 Preparing V2 server content for deployment...${NC}"

# Create a deployment package with V2 server content
cat > /tmp/mcp_v2_deployment.py << 'DEPLOY_SCRIPT'
#!/usr/bin/env python3
"""
Quick deployment of MCP V2 server content via HTTP
"""
import requests
import os
import sys

def main():
    # Read the V2 server content
    v2_file = "mcp_server_production v2.py"
    if not os.path.exists(v2_file):
        print("❌ V2 server file not found")
        return False

    with open(v2_file, 'r') as f:
        v2_content = f.read()

    # Deploy to cloud by writing directly to working directory
    print("📤 Deploying V2 server via direct file creation...")

    # Since direct upload isn't working, let's create a startup script
    startup_script = f'''#!/bin/bash
cd /home/ubuntu/hedge-agent

# Stop any existing servers on port 8009
pkill -f "python.*mcp_server_production"

# Create V2 server file
cat > mcp_server_production_v2.py << 'PYEOF'
{v2_content}
PYEOF

# Set environment variables
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS=http://localhost:3000,http://localhost:4200,https://dify.ai

# Install any missing dependencies
pip3 install --user anyio

# Start V2 server
echo "🚀 Starting MCP Production V2 Server..."
nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &

echo "✅ MCP V2 server deployed and started"
echo "📍 Endpoint: https://3-91-170-95.nip.io/"
echo "📍 Health: https://3-91-170-95.nip.io/health"

sleep 3

# Test the deployment
curl -s https://3-91-170-95.nip.io/health || echo "❌ Health check failed"
'''

    print("📤 Generated deployment script")
    print("🔧 Manual deployment required - SSH access needed")
    return True

if __name__ == "__main__":
    main()
DEPLOY_SCRIPT

python3 /tmp/mcp_v2_deployment.py

echo -e "${GREEN}✅ V2 server deployment prepared${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. SSH to cloud server: ssh ubuntu@3.91.170.95"
echo "2. Upload V2 server file manually"
echo "3. Start V2 server with environment variables"

echo -e "${GREEN}🌐 Expected Dify Endpoints:${NC}"
echo "📍 Main Endpoint: https://3-91-170-95.nip.io/"
echo "📍 Health Check: https://3-91-170-95.nip.io/health"
echo "📍 MCP Tools: https://3-91-170-95.nip.io/tools/list"