#!/usr/bin/env python3
"""
Complete MCP Server Startup Script
Sets up environment and starts the production MCP server
"""
import os
import sys
import asyncio
from pathlib import Path

# Set environment variables for the server
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTU5NjA5OSwiZXhwIjoyMDcxMTcyMDk5fQ.vgvEWMOBZ6iX1ZYNyeKW4aoh3nARiC1eYcHU4c1Y-vU"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:4200,https://dify.ai"
os.environ["DIFY_TOOL_TOKEN"] = "your_secure_token_here"

# Import the MCP server after setting environment
try:
    from mcp_server_production import app
    import uvicorn

    print("Starting MCP Server with complete configuration...")
    print(f"Supabase URL: {os.environ.get('SUPABASE_URL')}")
    print(f"CORS Origins: {os.environ.get('CORS_ORIGINS')}")
    print("Server starting on port 8010...")

    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info")

except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Server error: {e}")
    sys.exit(1)