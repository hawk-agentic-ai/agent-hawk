#!/bin/bash
echo "📦 Deploying MCP Phase 2 Implementation..."

# Upload all new components
echo "📤 Uploading Phase 2 components..."
scp -i agent_hawk.pem -o StrictHostKeyChecking=no requirements.txt ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no mcp_server.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no start_dual_servers.sh ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/
scp -i agent_hawk.pem -o StrictHostKeyChecking=no shared/hedge_processor.py ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/shared/
scp -r -i agent_hawk.pem -o StrictHostKeyChecking=no mcp_tools/ ubuntu@3.91.170.95:/home/ubuntu/hedge-agent/

echo "🔧 Installing MCP dependencies and testing..."
ssh -i agent_hawk.pem ubuntu@3.91.170.95 -o StrictHostKeyChecking=no << 'EOF'
    cd /home/ubuntu/hedge-agent
    
    echo "📦 Installing MCP dependencies..."
    pip3 install --user mcp anyio
    
    echo "🧪 Testing shared components..."
    python3 -c "from shared.hedge_processor import hedge_processor; print('✅ HedgeProcessor import successful')" || echo "❌ HedgeProcessor import failed"
    
    echo "🧪 Testing MCP imports..."
    python3 -c "from mcp.server import Server; from mcp.types import Tool; print('✅ MCP imports successful')" || echo "❌ MCP imports failed"
    
    echo "🧪 Testing MCP server module..."
    python3 -c "import mcp_server; print('✅ MCP server module import successful')" || echo "❌ MCP server import failed"
    
    echo "🧪 Testing MCP tools..."
    python3 -c "from mcp_tools.hedge_tools import HedgeFundTools; print('✅ MCP tools import successful')" || echo "❌ MCP tools import failed"
    
    echo "📋 Directory structure check..."
    ls -la shared/
    ls -la mcp_tools/
    
    echo "🚀 Ready for dual server startup!"
EOF

echo "✅ Phase 2 deployment complete!"
echo "🔗 Next step: Run ./start_dual_servers.sh on the server"