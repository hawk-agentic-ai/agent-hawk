#!/usr/bin/env python3
"""
Simple MCP Server for Testing
Minimal implementation to verify MCP integration works
"""

import asyncio
import logging
import json
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from shared.hedge_processor import hedge_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server
server = Server("hedge-fund-simple")
processor = None

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_system_health",
            description="Get system health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="process_hedge_prompt", 
            description="Process hedge fund prompts",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_prompt": {"type": "string", "description": "User prompt"}
                },
                "required": ["user_prompt"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    global processor
    
    try:
        if name == "get_system_health":
            if processor:
                result = processor.get_system_health()
            else:
                result = {"status": "error", "error": "Processor not initialized"}
                
        elif name == "process_hedge_prompt":
            if processor:
                result = await processor.universal_prompt_processor(
                    user_prompt=arguments.get("user_prompt", "system status"),
                    use_cache=False
                )
            else:
                result = {"status": "error", "error": "Processor not initialized"}
        else:
            result = {"status": "error", "error": f"Unknown tool: {name}"}
            
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
    except Exception as e:
        logger.error(f"Tool error: {e}")
        error_result = {"status": "error", "error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

async def main():
    """Main entry point"""
    global processor
    
    try:
        logger.info("Starting Simple MCP Server...")
        
        # Initialize processor
        processor = hedge_processor
        await processor.initialize()
        
        logger.info("Processor initialized, starting MCP server...")
        
        # Run server
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1])
            
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        if processor:
            await processor.cleanup()
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())