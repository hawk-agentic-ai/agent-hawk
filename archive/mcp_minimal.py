#!/usr/bin/env python3
"""
Minimal MCP Server for Dify - Bare bones implementation
Only JSON-RPC 2.0 over HTTP POST
"""

import os
import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client
supabase_client = None

async def init_supabase():
    global supabase_client
    try:
        supabase_url = "https://ladviaautlfvpxuadqrb.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"
        supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase initialized")
    except Exception as e:
        logger.error(f"Supabase failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_supabase()
    yield

app = FastAPI(title="Minimal MCP Server", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/")
async def mcp_handler(request: Request):
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")
        
        logger.info(f"MCP Request: {method}")
        
        # Handle notifications (no response)
        if req_id is None:
            logger.info(f"Notification: {method}")
            return {"ok": True}
        
        # Handle requests
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2023-05-20",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "hedge-fund-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", 
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "health_check",
                            "description": "Get server health",
                            "inputSchema": {"type": "object", "properties": {}}
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            if tool_name == "health_check":
                health_data = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "database": "connected" if supabase_client else "disconnected"
                }
                
                return {
                    "jsonrpc": "2.0",
                    "id": req_id, 
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(health_data)
                            }
                        ]
                    }
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": "Tool not found"}
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found"}
            }
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "jsonrpc": "2.0", 
            "id": body.get("id", None) if 'body' in locals() else None,
            "error": {"code": -32603, "message": str(e)}
        }

if __name__ == "__main__":
    uvicorn.run("mcp_minimal:app", host="0.0.0.0", port=8008, log_level="info")