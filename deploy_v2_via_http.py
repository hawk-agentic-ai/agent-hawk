#!/usr/bin/env python3
"""
Deploy V2 using HTTP requests to existing cloud services
"""
import requests
import base64
import os
import time

def deploy_v2():
    print("Deploying V2 MCP Server via HTTP...")

    # Read V2 server content
    v2_file = "mcp_server_production v2.py"
    if not os.path.exists(v2_file):
        print("ERROR: V2 server file not found")
        return False

    with open(v2_file, 'r', encoding='utf-8') as f:
        v2_content = f.read()

    # Create a simple deployment script that can be executed via curl
    deploy_cmd = f'''
cd /home/ubuntu/hedge-agent/hedge-agent
pkill -f "python.*mcp_server_production.py" || true
sleep 3
export SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTc5MDAzOSwiZXhwIjoyMDQxMzY2MDM5fQ.q9J3UvqYzfJx6CTN1lsLuYE5d6C-DYrfGNI4Y_NbY-vU
export CORS_ORIGINS="http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"
nohup python3 "mcp_server_production v2.py" > mcp_v2.log 2>&1 &
echo $! > mcp_v2.pid
sleep 8
curl -s http://localhost:8009/health
echo "V2 deployed at https://3-91-170-95.nip.io/mcp/"
'''

    # Save the deployment command
    with open('v2_deploy_cmd.sh', 'w') as f:
        f.write(deploy_cmd.strip())

    print("Deployment files created:")
    print("  - V2 server ready for manual deployment")
    print("  - Execute v2_deploy_cmd.sh on cloud server")
    print()
    print("Expected endpoints:")
    print("  - https://3-91-170-95.nip.io/mcp/")
    print("  - https://3-91-170-95.nip.io/mcp/health")
    print("  - https://3-91-170-95.nip.io/mcp/tools/list")

    return True

if __name__ == "__main__":
    deploy_v2()