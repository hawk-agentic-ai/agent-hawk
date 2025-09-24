"""
MCP Tools for Hedge Fund Operations
Individual tool implementations that can be registered with MCP servers
Contains all the hedge fund specific tools for Dify integration
"""

import json
import logging
from typing import Any, Dict, List
from mcp.types import Tool, TextContent

from shared.hedge_processor import HedgeFundProcessor

logger = logging.getLogger(__name__)

class HedgeFundTools:
    """Collection of hedge fund MCP tools"""
    
    def __init__(self, processor: HedgeFundProcessor):
        self.processor = processor
    
    def get_tool_definitions(self) -> List[Tool]:
        """Get all tool definitions for registration"""
        return [
            self.get_process_hedge_prompt_tool(),
            self.get_query_supabase_data_tool(), 
            self.get_system_health_tool(),
            self.get_manage_cache_tool()
        ]
    
    def get_process_hedge_prompt_tool(self) -> Tool:
        """Main hedge fund prompt processing tool"""
        return Tool(
            name="process_hedge_prompt",
            description="""Process hedge fund operations from natural language prompts.
            
This is the primary tool for hedge fund operations. It analyzes user prompts to determine intent
(inception, utilization, rollover, termination, risk analysis, compliance, etc.), extracts relevant
data from Supabase, and returns structured analysis results.

Examples:
- "Create inception hedge instruction for USD 1M position"
- "Show hedge effectiveness for EUR positions"  
- "Generate risk analysis for entity ABC123"
- "What's the hedge utilization for GBP positions?"
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "Natural language prompt describing the hedge fund operation"
                    },
                    "template_category": {
                        "type": "string", 
                        "description": "Template category hint (inception, utilization, rollover, termination, risk_analysis, compliance, performance, monitoring)",
                        "enum": ["inception", "utilization", "rollover", "termination", "risk_analysis", "compliance", "performance", "monitoring", "general"],
                        "default": None
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code for filtering (USD, EUR, GBP, JPY, CAD, AUD, etc.)",
                        "pattern": "^[A-Z]{3}$",
                        "default": None
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Specific entity ID for entity-targeted operations",
                        "default": None
                    },
                    "nav_type": {
                        "type": "string",
                        "description": "NAV type for position filtering",
                        "enum": ["Official", "Unofficial", "Both"],
                        "default": None
                    },
                    "amount": {
                        "type": "number",
                        "description": "Financial amount for calculations (in base currency units)",
                        "minimum": 0,
                        "default": None
                    },
                    "use_cache": {
                        "type": "boolean", 
                        "description": "Enable Redis caching for faster responses",
                        "default": True
                    }
                },
                "required": ["user_prompt"]
            }
        )
    
    def get_query_supabase_data_tool(self) -> Tool:
        """Direct database query tool"""
        return Tool(
            name="query_supabase_data",
            description="""Direct access to Supabase database tables with filtering and ordering.
            
Use this tool for specific data queries when you need raw database access without AI analysis.
Available tables include: entity_master, position_nav_master, hedge_instructions, 
hedge_business_events, allocation_engine, currency_configuration, buffer_configuration, etc.

Examples:
- Query entity_master for USD entities
- Get recent hedge_instructions with limit 50
- Fetch position_nav_master for specific entity_id
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Supabase table name to query",
                        "enum": [
                            "entity_master", "position_nav_master", "hedge_instructions", 
                            "hedge_business_events", "allocation_engine", "currency_configuration",
                            "buffer_configuration", "hedging_framework", "system_configuration",
                            "waterfall_logic_configuration", "hedge_instruments", "currency_rates",
                            "car_master", "gl_entries", "audit_trail"
                        ]
                    },
                    "filters": {
                        "type": "object", 
                        "description": "Key-value pairs for exact match filtering",
                        "additionalProperties": True,
                        "default": {}
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum records to return",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 100
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Column to sort by (prefix with '-' for descending order)",
                        "default": None
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Use caching for query results",
                        "default": True
                    }
                },
                "required": ["table_name"]
            }
        )
    
    def get_system_health_tool(self) -> Tool:
        """System health monitoring tool"""
        return Tool(
            name="get_system_health",
            description="""Get comprehensive system health and performance metrics.
            
Returns status of all system components including:
- Database connectivity (Supabase)
- Cache system (Redis) 
- Processing performance metrics
- Cache hit rates and optimization stats
- Component initialization status

Use for monitoring system health and troubleshooting issues.
            """,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    
    def get_manage_cache_tool(self) -> Tool:
        """Cache management tool"""  
        return Tool(
            name="manage_cache",
            description="""Manage Redis cache operations for performance optimization.
            
Available operations:
- stats: Get current cache statistics and hit rates
- clear_currency: Clear all cached data for a specific currency
- info: Get Redis server information and memory usage

The system uses aggressive caching optimized for small hedge funds (30 users max).
            """,
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
                        "description": "Currency code for clear_currency operation (e.g., USD, EUR)",
                        "pattern": "^[A-Z]{3}$",
                        "default": None
                    }
                },
                "required": ["operation"]
            }
        )
    
    async def execute_process_hedge_prompt(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute the main hedge prompt processing tool"""
        try:
            result = await self.processor.universal_prompt_processor(
                user_prompt=arguments.get("user_prompt"),
                template_category=arguments.get("template_category"),
                currency=arguments.get("currency"),
                entity_id=arguments.get("entity_id"),
                nav_type=arguments.get("nav_type"), 
                amount=arguments.get("amount"),
                use_cache=arguments.get("use_cache", True)
            )
            
            response_text = json.dumps(result, indent=2, default=str)
            return [TextContent(type="text", text=response_text)]
            
        except Exception as e:
            logger.error(f"process_hedge_prompt execution error: {e}")
            error_response = {
                "status": "error",
                "tool": "process_hedge_prompt",
                "error": str(e),
                "arguments": arguments
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def execute_query_supabase_data(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute direct Supabase query tool"""
        try:
            result = await self.processor.query_supabase_direct(
                table_name=arguments.get("table_name"),
                filters=arguments.get("filters"),
                limit=arguments.get("limit"), 
                order_by=arguments.get("order_by"),
                use_cache=arguments.get("use_cache", True)
            )
            
            response_text = json.dumps(result, indent=2, default=str)
            return [TextContent(type="text", text=response_text)]
            
        except Exception as e:
            logger.error(f"query_supabase_data execution error: {e}")
            error_response = {
                "status": "error",
                "tool": "query_supabase_data", 
                "error": str(e),
                "arguments": arguments
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def execute_get_system_health(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute system health check tool"""
        try:
            result = self.processor.get_system_health()
            
            response_text = json.dumps(result, indent=2, default=str)
            return [TextContent(type="text", text=response_text)]
            
        except Exception as e:
            logger.error(f"get_system_health execution error: {e}")
            error_response = {
                "status": "error",
                "tool": "get_system_health",
                "error": str(e),
                "arguments": arguments
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def execute_manage_cache(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute cache management tool"""
        try:
            result = self.processor.manage_cache_operations(
                operation=arguments.get("operation"),
                currency=arguments.get("currency")
            )
            
            response_text = json.dumps(result, indent=2, default=str)
            return [TextContent(type="text", text=response_text)]
            
        except Exception as e:
            logger.error(f"manage_cache execution error: {e}")
            error_response = {
                "status": "error",
                "tool": "manage_cache",
                "error": str(e),
                "arguments": arguments
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Route tool execution to appropriate handler"""
        tool_handlers = {
            "process_hedge_prompt": self.execute_process_hedge_prompt,
            "query_supabase_data": self.execute_query_supabase_data,
            "get_system_health": self.execute_get_system_health,
            "manage_cache": self.execute_manage_cache
        }
        
        handler = tool_handlers.get(name)
        if handler:
            return await handler(arguments)
        else:
            error_response = {
                "status": "error",
                "error": f"Unknown tool: {name}",
                "available_tools": list(tool_handlers.keys())
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


def register_hedge_tools(server, processor: HedgeFundProcessor) -> HedgeFundTools:
    """Register all hedge fund tools with an MCP server"""
    hedge_tools = HedgeFundTools(processor)
    
    # Register tool definitions
    @server.list_tools()
    async def list_tools():
        return hedge_tools.get_tool_definitions()
    
    # Register tool execution handler
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        return await hedge_tools.execute_tool(name, arguments)
    
    return hedge_tools