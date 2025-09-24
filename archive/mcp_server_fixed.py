#!/usr/bin/env python3
"""
Fixed MCP Server for Hedge Fund Operations
Compatible with MCP 2024-11-05 protocol specification
"""

import asyncio
import logging
import json
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from shared.hedge_processor import hedge_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server
server = Server("hedge-fund-mcp-server")
processor = None

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available MCP tools for hedge fund operations"""
    return [
        Tool(
            name="process_hedge_prompt",
            description="Process hedge fund operations from natural language prompts using AI analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "Natural language prompt describing the hedge fund operation"
                    },
                    "template_category": {
                        "type": "string", 
                        "description": "Optional template category hint",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code for filtering",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Whether to use Redis caching",
                        "default": True
                    }
                },
                "required": ["user_prompt"]
            }
        ),
        Tool(
            name="query_supabase_data", 
            description="Direct access to Supabase database tables with filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the Supabase table to query"
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "Maximum number of records to return",
                        "default": 10
                    }
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="get_system_health",
            description="Get comprehensive system health and performance metrics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="manage_cache",
            description="Manage Redis cache operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Cache operation to perform",
                        "enum": ["stats", "info"]
                    }
                },
                "required": ["operation"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from MCP clients"""
    global processor
    
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        if not processor:
            error_response = {
                "status": "error",
                "error": "HedgeFundProcessor not initialized"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
        
        if name == "process_hedge_prompt":
            result = await processor.universal_prompt_processor(
                user_prompt=arguments.get("user_prompt", "system status"),
                template_category=arguments.get("template_category"),
                currency=arguments.get("currency"),
                use_cache=arguments.get("use_cache", True)
            )
            
        elif name == "query_supabase_data":
            result = await processor.query_supabase_direct(
                table_name=arguments.get("table_name"),
                limit=arguments.get("limit", 10),
                use_cache=True
            )
            
        elif name == "get_system_health":
            result = processor.get_system_health()
            
        elif name == "manage_cache":
            result = processor.manage_cache_operations(
                operation=arguments.get("operation", "stats")
            )
            
        else:
            result = {
                "status": "error",
                "error": f"Unknown tool: {name}",
                "available_tools": ["process_hedge_prompt", "query_supabase_data", "get_system_health", "manage_cache"]
            }
        
        # Return structured JSON response
        response_text = json.dumps(result, indent=2, default=str)
        return [TextContent(type="text", text=response_text)]
        
    except Exception as e:
        logger.error(f"Tool execution error for {name}: {e}")
        error_response = {
            "status": "error", 
            "tool": name,
            "error": str(e),
            "arguments": arguments
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

async def main():
    """Main MCP server entry point"""
    global processor
    
    try:
        logger.info("Starting Fixed Hedge Fund MCP Server...")
        
        # Initialize the hedge fund processor
        processor = hedge_processor
        await processor.initialize()
        
        logger.info("HedgeFundProcessor initialized successfully")
        logger.info("Fixed MCP Server ready for connections...")
        
        # Start the MCP server with stdio transport
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1])
            
    except KeyboardInterrupt:
        logger.info("MCP Server shutdown requested")
    except Exception as e:
        logger.error(f"MCP Server error: {e}")
        raise
    finally:
        # Cleanup
        if processor:
            await processor.cleanup()
        logger.info("MCP Server shutdown complete")

if __name__ == "__main__":
    # Run the MCP server
    asyncio.run(main())