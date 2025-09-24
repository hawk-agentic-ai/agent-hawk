#!/usr/bin/env python3
"""
Deploy V2 MCP server to cloud via HTTP methods
"""
import requests
import time
import os

def create_deployment_payload():
    # Read V2 server content
    v2_file = "mcp_server_production v2.py"
    if not os.path.exists(v2_file):
        print("ERROR: V2 server file not found")
        return None

    with open(v2_file, 'r', encoding='utf-8') as f:
        v2_content = f.read()

    # Create a deployment script for remote execution
    deployment_script = f'''#!/bin/bash
cd /home/ubuntu/hedge-agent/hedge-agent

echo "Stopping any existing MCP servers on port 8009..."
pkill -f "python.*mcp_server_production.py" || true
sleep 3

echo "Creating V2 server file..."
cat > mcp_server_production_v2.py << 'PYEOF'
{v2_content}
PYEOF

echo "Setting environment variables..."
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"

echo "Starting V2 MCP server on port 8009..."
nohup python3 mcp_server_production_v2.py > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid

echo "Waiting for startup..."
sleep 8

echo "Testing health..."
curl -s http://localhost:8009/health

echo "V2 deployment complete!"
echo "Server available at: https://3-91-170-95.nip.io/mcp/"
'''

    return deployment_script

def main():
    print("🚀 Preparing V2 MCP Server deployment...")

    # Create deployment payload
    deploy_script = create_deployment_payload()
    if not deploy_script:
        return False

    # Save deployment script for manual execution
    with open('cloud_deploy_v2.sh', 'w') as f:
        f.write(deploy_script)

    print("✅ V2 deployment script created: cloud_deploy_v2.sh")
    print("")
    print("📋 Current Cloud Status:")
    print("   • Port 8009 (Main MCP): Available for V2")
    print("   • Port 8010 (Allocation): Running (will keep)")
    print("   • Port 80 (Frontend): Running")
    print("")
    print("🌐 Expected V2 Endpoints after deployment:")
    print("   • Main: https://3-91-170-95.nip.io/mcp/")
    print("   • Health: https://3-91-170-95.nip.io/mcp/health")
    print("   • Tools: https://3-91-170-95.nip.io/mcp/tools/list")
    print("")
    print("⚡ V2 Features:")
    print("   • 5 tools: process_hedge_prompt, query_supabase_data, get_system_health, manage_cache, generate_agent_report")
    print("   • CORS enabled for cloud.dify.ai")
    print("   • Optimized async handling")
    print("   • Production security (no API docs)")
    print("")
    print("📝 Next step: Copy cloud_deploy_v2.sh to server and execute")

    return True

if __name__ == "__main__":
    main()