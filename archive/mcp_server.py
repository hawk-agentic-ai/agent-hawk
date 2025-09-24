"""
MCP Server for Hedge Fund Operations
Model Context Protocol server that exposes hedge fund functionality to Dify and other MCP clients
Uses shared business logic from HedgeFundProcessor
"""

import asyncio
import logging
import json
from typing import Any, Dict, Optional

# MCP Server imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import our shared components
from shared.hedge_processor import hedge_processor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("hedge-fund-mcp-server")

# Global processor instance
processor = None

@server.list_tools()
async def list_tools() -> list[Tool]:
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
                        "description": "Optional template category hint (e.g., 'inception', 'utilization', 'risk_analysis')",
                        "default": None
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code for filtering (e.g., 'USD', 'EUR', 'GBP')",
                        "default": None
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID for entity-specific operations",
                        "default": None
                    },
                    "nav_type": {
                        "type": "string", 
                        "description": "NAV type for position filtering (e.g., 'Official', 'Unofficial')",
                        "default": None
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount for financial calculations",
                        "default": None
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Whether to use Redis caching for data retrieval",
                        "default": True
                    }
                },
                "required": ["user_prompt"]
            }
        ),
        Tool(
            name="query_supabase_data", 
            description="Direct access to Supabase database tables with filtering and ordering",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the Supabase table to query"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Key-value pairs for filtering records",
                        "default": {}
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "Maximum number of records to return",
                        "default": 100
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Column to order by (prefix with '-' for descending)",
                        "default": None
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Whether to use caching for the query",
                        "default": True
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
            description="Manage Redis cache operations including stats, clearing, and information",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Cache operation to perform",
                        "enum": ["stats", "clear_currency", "info"]
                    },
                    "currency": {
                        "type": "string", 
                        "description": "Currency code for clear_currency operation",
                        "default": None
                    }
                },
                "required": ["operation"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls from MCP clients"""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        
        if not processor:
            error_response = {
                "status": "error",
                "error": "HedgeFundProcessor not initialized",
                "timestamp": "N/A"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
        
        if name == "process_hedge_prompt":
            result = await processor.universal_prompt_processor(
                user_prompt=arguments.get("user_prompt"),
                template_category=arguments.get("template_category"),
                currency=arguments.get("currency"),
                entity_id=arguments.get("entity_id"),
                nav_type=arguments.get("nav_type"),
                amount=arguments.get("amount"),
                use_cache=arguments.get("use_cache", True)
            )
            
        elif name == "query_supabase_data":
            result = await processor.query_supabase_direct(
                table_name=arguments.get("table_name"),
                filters=arguments.get("filters"),
                limit=arguments.get("limit"),
                order_by=arguments.get("order_by"),
                use_cache=arguments.get("use_cache", True)
            )
            
        elif name == "get_system_health":
            result = processor.get_system_health()
            
        elif name == "manage_cache":
            result = processor.manage_cache_operations(
                operation=arguments.get("operation"),
                currency=arguments.get("currency")
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
        logger.info("Starting Hedge Fund MCP Server...")
        
        # Initialize the hedge fund processor
        processor = hedge_processor
        await processor.initialize()
        
        logger.info("HedgeFundProcessor initialized successfully")
        logger.info("MCP Server ready for connections...")
        
        # Start the MCP server with stdio transport
        async with stdio_server() as streams:
            await server.run(
                streams[0], 
                streams[1],
                server.create_initialization_options()
            )
            
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