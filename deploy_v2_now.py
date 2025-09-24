#!/usr/bin/env python3
"""
Direct V2 deployment using HTTP approach
"""
import requests
import json
import os

def main():
    print("🚀 Deploying V2 MCP Server to Cloud...")

    # Read V2 server content
    v2_file = "mcp_server_production v2.py"
    if not os.path.exists(v2_file):
        print("❌ V2 server file not found")
        return False

    with open(v2_file, 'r') as f:
        v2_content = f.read()

    # Create deployment payload
    deployment_script = f'''#!/bin/bash
cd /home/ubuntu/hedge-agent/hedge-agent

# Stop any existing MCP servers
pkill -f "python.*mcp_server_production" || true
sleep 3

# Create V2 server file
cat > "mcp_server_production_v2.py" << 'PYEOF'
{v2_content}
PYEOF

# Set environment variables
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS=http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai

# Install dependencies
pip3 install --user anyio || true

# Start V2 server on port 8009
echo "✅ Starting MCP V2 Server..."
nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid

# Wait and verify
sleep 5
curl -s http://localhost:8009/health || echo "❌ Health check failed"
echo "🌐 V2 Server deployed at: https://3-91-170-95.nip.io/mcp/"
'''

    # Save deployment script locally for manual execution
    with open('v2_deploy_remote.sh', 'w') as f:
        f.write(deployment_script)

    print("📤 V2 deployment script created: v2_deploy_remote.sh")
    print("📋 Deployment Summary:")
    print("   • V2 server will run on port 8009 (replacing V1)")
    print("   • Same nginx routing: /mcp/* -> localhost:8009")
    print("   • CORS includes cloud.dify.ai")
    print("   • Database credentials are set")
    print("")
    print("🌐 Expected V2 Endpoints:")
    print("   • Main: https://3-91-170-95.nip.io/mcp/")
    print("   • Health: https://3-91-170-95.nip.io/mcp/health")
    print("   • Tools: https://3-91-170-95.nip.io/mcp/tools/list")
    print("")
    print("📝 Manual deployment needed - copy and run script on cloud server")

    return True

if __name__ == "__main__":
    main()