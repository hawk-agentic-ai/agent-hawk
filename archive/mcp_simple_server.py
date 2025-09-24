#!/usr/bin/env python3
"""
Simple HTTP MCP Server for Dify Cloud - Minimal Implementation
Compatible with Dify's MCP expectations
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client
supabase_client: Optional[Client] = None

# Pydantic models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

# Initialize connections
async def init_supabase():
    global supabase_client
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables must be set")

        supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_supabase()
    yield

# FastAPI app
app = FastAPI(
    title="Simple MCP Server",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Tools
TOOLS = [
    {
        "name": "query_table",
        "description": "Query database table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "list_tables",
        "description": "List all available tables",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "system_health",
        "description": "Get system health status",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool implementations
async def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if name == "system_health":
            return {
                "status": "healthy",
                "server": "hedge-fund-mcp-server",
                "version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected" if supabase_client else "disconnected"
            }
        
        elif name == "list_tables":
            return {
                "tables": [
                    "entity_master",
                    "position_nav_master", 
                    "hedge_instructions",
                    "hedge_business_events"
                ]
            }
        
        elif name == "query_table":
            table_name = arguments.get("table_name")
            limit = arguments.get("limit", 10)
            
            if not supabase_client:
                return {"error": "Database not connected"}
            
            result = supabase_client.table(table_name).select("*").limit(limit).execute()
            return {
                "table": table_name,
                "data": result.data,
                "count": len(result.data)
            }
        
        else:
            return {"error": f"Unknown tool: {name}"}
            
    except Exception as e:
        return {"error": str(e)}

# Routes
@app.get("/")
async def root():
    # Return JSON-RPC 2.0 format even for GET requests
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "hedge-fund-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"listChanged": False}
            }
        }
    }

@app.post("/")
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
        
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        # Handle notifications (no response expected)
        if request_id is None:
            # This is a notification, not a request
            if method == "notifications/initialized":
                # Just log and don't respond
                logger.info("Received initialization complete notification")
                return {"status": "ok"}  # Simple acknowledgment
            elif method == "initialized":
                logger.info("Received initialized notification")
                return {"status": "ok"}
            else:
                logger.info(f"Received notification: {method}")
                return {"status": "ok"}
        
        # Handle requests (response required)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "hedge-fund-mcp-server",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "initialized":
            # This shouldn't have an ID, but handle it just in case
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": TOOLS
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})
            
            result = await execute_tool(tool_name, tool_arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Request failed: {e}")
        logger.error(f"Request body: {body if 'body' in locals() else 'Unknown'}")
        
        # Try to get request ID if available
        req_id = None
        try:
            if 'body' in locals() and isinstance(body, dict):
                req_id = body.get("id")
        except:
            pass
            
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        }

@app.get("/health")
async def health():
    health_data = await execute_tool("system_health", {})
    # Return in JSON-RPC 2.0 format
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(health_data)
                }
            ]
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "mcp_simple_server:app",
        host="0.0.0.0", 
        port=8007,
        log_level="info"
    )