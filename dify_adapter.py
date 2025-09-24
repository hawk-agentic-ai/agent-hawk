#!/usr/bin/env python3
"""
Dify Adapter for MCP Server
Translates Dify's direct tool calls to JSON-RPC 2.0 format for our MCP server
"""

import json
import httpx
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dify MCP Adapter", version="1.0.0")

# CORS for Dify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

MCP_SERVER_URL = "http://localhost:8009"

async def call_mcp_tool(tool_name: str, arguments: dict):
    """Call the real MCP server with proper JSON-RPC format"""
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 1,
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(MCP_SERVER_URL, json=payload, timeout=60.0)
            response.raise_for_status()
            result = response.json()

            # Extract the actual result from JSON-RPC wrapper
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"][0]["text"]
                return json.loads(content)
            else:
                return result

    except Exception as e:
        logger.error(f"Error calling MCP server: {e}")
        return {"error": str(e), "tool": tool_name}

@app.post("/")
async def dify_endpoint(request: Request):
    """Handle Dify's direct tool call format and translate to MCP"""
    try:
        body = await request.json()
        logger.info(f"Dify request: {json.dumps(body)}")

        # Check if this is a direct tool call from Dify
        tool_name = None
        arguments = {}

        # Dify sends: {"tool_name": {"param1": "value1", ...}}
        for key, value in body.items():
            if isinstance(value, dict):
                tool_name = key
                arguments = value
                break

        if not tool_name:
            return {"error": "No tool call found in request"}

        # Check if tool exists
        valid_tools = [
            "process_hedge_prompt",
            "query_supabase_data",
            "get_system_health",
            "manage_cache",
            "generate_agent_report"
        ]

        if tool_name not in valid_tools:
            return {tool_name: f"there is not a tool named {tool_name}"}

        # Call the real MCP server
        result = await call_mcp_tool(tool_name, arguments)

        # Return in Dify's expected format
        return {tool_name: result}

    except Exception as e:
        logger.error(f"Error processing Dify request: {e}")
        return {"error": str(e)}

@app.options("/")
async def options_root():
    """Handle OPTIONS for CORS preflight"""
    return {"status": "ok"}

@app.get("/")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "dify-mcp-adapter",
        "timestamp": datetime.now().isoformat(),
        "mcp_server": MCP_SERVER_URL,
        "endpoint_validation": "ready",
        "cors_enabled": True
    }

@app.get("/tools")
async def list_tools():
    """List available tools for Dify"""
    return {
        "tools": [
            "process_hedge_prompt",
            "query_supabase_data",
            "get_system_health",
            "manage_cache",
            "generate_agent_report"
        ]
    }

@app.get("/schema")
async def get_schema():
    """OpenAPI-like schema for Dify validation"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Hedge Fund MCP Adapter",
            "version": "1.0.0",
            "description": "Dify adapter for hedge fund operations"
        },
        "servers": [{"url": "https://3-91-170-95.nip.io/dify/"}],
        "paths": {
            "/": {
                "post": {
                    "summary": "Execute hedge fund tools",
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info")