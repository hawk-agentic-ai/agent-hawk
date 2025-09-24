#!/bin/bash
# Test script for nip.io MCP server

echo "🧪 Testing HAWK Allocation MCP Server via nip.io..."
echo "🌐 URL: http://3-91-170-95.nip.io:8010"
echo ""

echo "1️⃣ Testing basic health..."
curl -s http://3-91-170-95.nip.io:8010/ || echo "❌ Port 8010 blocked in AWS Security Group"

echo ""
echo "2️⃣ Testing MCP initialize..."
curl -s -X POST http://3-91-170-95.nip.io:8010/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' || echo "❌ Port blocked"

echo ""
echo "3️⃣ Testing tools list..."
curl -s -X POST http://3-91-170-95.nip.io:8010/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialized", "id": 2}' > /dev/null

curl -s -X POST http://3-91-170-95.nip.io:8010/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 3}' | head -5 || echo "❌ Port blocked"

echo ""
echo "✅ Add port 8010 to AWS Security Group to enable access!"
echo "📋 Use this URL in Dify: http://3-91-170-95.nip.io:8010"