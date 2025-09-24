#!/bin/bash
# Hedge Fund MCP Data Server Startup Script (cloud)
# Port: 8009 | Protocol: HTTP JSON-RPC 2.0 | Purpose: Dify integration

set -euo pipefail

# Always run from this script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Hedge Fund MCP Data Server... (cwd: $SCRIPT_DIR)"

# Load production env if available (service role, token, etc.)
if [ -f ./.env.production ]; then
  echo "🔧 Loading .env.production"
  set -a
  # shellcheck disable=SC1091
  . ./.env.production
  set +a
fi

# Configuration
export MCP_SERVER_PORT=8009
export SUPABASE_URL="${SUPABASE_URL:-https://ladviaautlfvpxuadqrb.supabase.co}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes}"
# Preserve pre-set service role key if provided by env/.env.production
export SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-}"
export DIFY_TOOL_TOKEN="${DIFY_TOOL_TOKEN:-}"  # Set authentication token for production
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000,http://localhost:4200,https://dify.ai}"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

# Choose python: prefer project venv if available
PYTHON_BIN="python3"
if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
  PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
elif [ -x "$SCRIPT_DIR/../venv/bin/python" ]; then
  PYTHON_BIN="$SCRIPT_DIR/../venv/bin/python"
fi

# Stop existing server if bound to 8009
if command -v lsof >/dev/null 2>&1 && lsof -Pi :8009 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8009 in use. Stopping existing process..."
    pkill -f "mcp_server_production" || true
    sleep 2 || true
fi

# Start server
if [ -n "$SUPABASE_SERVICE_ROLE_KEY" ]; then
  echo "🔐 Using Supabase SERVICE ROLE key for DB access (writes enabled)"
else
  echo "⚠️  SUPABASE_SERVICE_ROLE_KEY is not set. Using anon key — writes may fail due to RLS."
fi

echo "📊 Starting MCP Production Server on port 8009 with $PYTHON_BIN..."
"$PYTHON_BIN" mcp_server_production.py &
MCP_PID=$!

echo "✅ MCP Production Server started with PID: $MCP_PID"
echo "🌐 Server URL: http://localhost:8009"
echo "🔗 JSON-RPC Endpoint: http://localhost:8009/"

# Wait for server to start
sleep 3

# Test server
echo "🧪 Testing server availability..."
if curl -s -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"initialize","id":1}' http://localhost:8009/ >/dev/null; then
    echo "✅ Server is responding to JSON-RPC requests"
else
    echo "❌ Server JSON-RPC test failed"
    exit 1
fi

# Keep script running
wait $MCP_PID
