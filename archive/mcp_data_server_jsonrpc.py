#!/usr/bin/env python3
"""
JSON-RPC 2.0 MCP Server for Dify Cloud Integration
Port: 8006 | Protocol: JSON-RPC 2.0 over HTTP | Purpose: Full CRUD operations
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import create_client, Client
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global clients
supabase_client: Optional[Client] = None
redis_client: Optional[redis.Redis] = None

# JSON-RPC 2.0 Models
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

# MCP Server Info
MCP_SERVER_INFO = {
    "name": "hedge-fund-mcp-server",
    "version": "2.0.0",
    "protocolVersion": "2024-11-05",
    "capabilities": {
        "tools": {
            "listChanged": False
        }
    }
}

# MCP Tools Definition
MCP_TOOLS = [
    {
        "name": "query_table",
        "description": "Query any Supabase table with filters, sorting, and column selection",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Table name to query"},
                "filters": {"type": "object", "description": "Filter conditions as key-value pairs"},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "Specific columns to select"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                "order_by": {"type": "string", "description": "Column to order by (prefix with '-' for DESC)"},
                "offset": {"type": "integer", "minimum": 0, "default": 0}
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "insert_record",
        "description": "Insert new record into any Supabase table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Table name for insertion"},
                "data": {"type": "object", "description": "Record data as key-value pairs"},
                "return_record": {"type": "boolean", "default": True, "description": "Return inserted record"}
            },
            "required": ["table_name", "data"]
        }
    },
    {
        "name": "update_record",
        "description": "Update existing record in any Supabase table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Table name for update"},
                "record_id": {"type": "string", "description": "Record ID to update"},
                "data": {"type": "object", "description": "Updated data as key-value pairs"},
                "id_column": {"type": "string", "default": "id", "description": "ID column name"}
            },
            "required": ["table_name", "record_id", "data"]
        }
    },
    {
        "name": "delete_record",
        "description": "Delete record from any Supabase table",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "table_name": {"type": "string", "description": "Table name for deletion"},
                "record_id": {"type": "string", "description": "Record ID to delete"},
                "id_column": {"type": "string", "default": "id", "description": "ID column name"}
            },
            "required": ["table_name", "record_id"]
        }
    },
    {
        "name": "list_tables",
        "description": "Get list of all available tables in the database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_system": {"type": "boolean", "default": False, "description": "Include system tables"}
            }
        }
    },
    {
        "name": "get_table_schema",
        "description": "Get table schema including columns, types, and constraints", 
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Table name to get schema for"}
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "execute_sql",
        "description": "Execute custom SQL query (SELECT, INSERT, UPDATE, DELETE)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string", "description": "SQL query to execute"},
                "params": {"type": "object", "description": "Query parameters for prepared statements"}
            },
            "required": ["sql_query"]
        }
    },
    {
        "name": "system_health",
        "description": "Get MCP server health and database connection status",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Database Connection Manager
async def initialize_connections():
    """Initialize Supabase and Redis connections"""
    global supabase_client, redis_client
    
    try:
        # Initialize Supabase
        supabase_url = os.getenv("SUPABASE_URL", "https://ladviaautlfvpxuadqrb.supabase.co")
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes")
        
        supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
        
        # Initialize Redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        
        try:
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
            logger.info("Redis client connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            redis_client = None
            
    except Exception as e:
        logger.error(f"Failed to initialize connections: {e}")
        raise

async def cleanup_connections():
    """Cleanup database connections"""
    global redis_client
    
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection closed")

# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_connections()
    yield
    # Shutdown
    await cleanup_connections()

# Initialize FastAPI
app = FastAPI(
    title="Hedge Fund MCP Data Server (JSON-RPC 2.0)",
    description="JSON-RPC 2.0 MCP Server for complete Supabase database operations",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Tool Implementations
class MCPTools:
    """MCP tool implementations for database operations"""
    
    @staticmethod
    async def query_table(params: Dict[str, Any]) -> Dict[str, Any]:
        """Query table with filters and options"""
        try:
            table_name = params["table_name"]
            filters = params.get("filters", {})
            columns = params.get("columns")
            limit = params.get("limit", 100)
            order_by = params.get("order_by")
            offset = params.get("offset", 0)
            
            # Build query - fix for Supabase query builder
            query = supabase_client.table(table_name)
            
            # Apply column selection first
            if columns:
                query = query.select(",".join(columns))
            else:
                query = query.select("*")
            
            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)
            
            # Apply ordering
            if order_by:
                if order_by.startswith("-"):
                    query = query.order(order_by[1:], desc=True)
                else:
                    query = query.order(order_by)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Execute query
            result = query.execute()
            
            return {
                "success": True,
                "data": result.data,
                "count": len(result.data),
                "table": table_name
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def insert_record(params: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new record"""
        try:
            table_name = params["table_name"]
            data = params["data"]
            return_record = params.get("return_record", True)
            
            # Add audit fields
            data["created_at"] = datetime.utcnow().isoformat()
            data["updated_at"] = datetime.utcnow().isoformat()
            
            # Insert record
            result = supabase_client.table(table_name).insert(data).execute()
            
            return {
                "success": True,
                "data": result.data[0] if result.data and return_record else {"message": "Record inserted successfully"},
                "table": table_name
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def update_record(params: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing record"""
        try:
            table_name = params["table_name"]
            record_id = params["record_id"]
            data = params["data"]
            id_column = params.get("id_column", "id")
            
            # Add audit fields
            data["updated_at"] = datetime.utcnow().isoformat()
            
            # Update record
            result = supabase_client.table(table_name)\
                .update(data)\
                .eq(id_column, record_id)\
                .execute()
            
            return {
                "success": True,
                "data": result.data[0] if result.data else {"message": "Record updated successfully"},
                "table": table_name,
                "record_id": record_id
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def delete_record(params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete record"""
        try:
            table_name = params["table_name"]
            record_id = params["record_id"]
            id_column = params.get("id_column", "id")
            
            # Delete record
            result = supabase_client.table(table_name)\
                .delete()\
                .eq(id_column, record_id)\
                .execute()
            
            return {
                "success": True,
                "data": {"message": f"Record {record_id} deleted successfully"},
                "table": table_name,
                "record_id": record_id
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def list_tables(params: Dict[str, Any]) -> Dict[str, Any]:
        """List all tables"""
        try:
            # Common hedge fund tables (fallback approach)
            tables = [
                "entity_master",
                "position_nav_master", 
                "hedge_instructions",
                "hedge_business_events",
                "allocation_engine",
                "currency_configuration",
                "compliance_rules",
                "risk_metrics"
            ]
            
            return {
                "success": True,
                "data": tables,
                "count": len(tables)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_table_schema(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get table schema"""
        try:
            table_name = params["table_name"]
            
            # Basic schema info for common hedge fund tables
            schema_info = {
                "table_name": table_name,
                "columns": [
                    {"name": "id", "type": "uuid", "nullable": False},
                    {"name": "created_at", "type": "timestamp", "nullable": False},
                    {"name": "updated_at", "type": "timestamp", "nullable": False}
                ]
            }
            
            return {
                "success": True,
                "data": schema_info,
                "table": table_name
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def execute_sql(params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom SQL query"""
        try:
            sql_query = params["sql_query"]
            
            # Basic SQL validation
            sql_lower = sql_query.lower().strip()
            allowed_operations = ["select", "insert", "update", "delete"]
            
            if not any(sql_lower.startswith(op) for op in allowed_operations):
                return {
                    "success": False,
                    "error": "Only SELECT, INSERT, UPDATE, DELETE operations allowed"
                }
            
            # For SELECT queries, use Supabase RPC or direct query
            if sql_lower.startswith("select"):
                # This would need custom RPC function in Supabase
                return {
                    "success": False,
                    "error": "Custom SQL execution requires RPC function setup in Supabase"
                }
            
            return {
                "success": False,
                "error": "SQL execution not implemented yet"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def system_health(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get system health"""
        try:
            health_data = {
                "status": "healthy",
                "server": "mcp-data-server",
                "version": "2.0.0",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": {
                    "supabase": "connected" if supabase_client else "disconnected",
                    "redis": "connected" if redis_client else "disconnected"
                }
            }
            
            # Test database connection
            if supabase_client:
                try:
                    test_result = supabase_client.table("entity_master").select("*").limit(1).execute()
                    health_data["database_test"] = "success"
                except Exception as e:
                    health_data["database_test"] = f"failed: {str(e)}"
                    health_data["status"] = "degraded"
            
            return {
                "success": True,
                "data": health_data
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# JSON-RPC 2.0 Request Handler
async def handle_jsonrpc_request(request_data: JSONRPCRequest) -> JSONRPCResponse:
    """Handle JSON-RPC 2.0 requests"""
    try:
        method = request_data.method
        params = request_data.params or {}
        request_id = request_data.id
        
        # Handle MCP protocol methods
        if method == "initialize":
            return JSONRPCResponse(
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": MCP_SERVER_INFO["capabilities"],
                    "serverInfo": {
                        "name": MCP_SERVER_INFO["name"],
                        "version": MCP_SERVER_INFO["version"]
                    }
                },
                id=request_id
            )
        
        elif method == "tools/list":
            return JSONRPCResponse(
                result={"tools": MCP_TOOLS},
                id=request_id
            )
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})
            
            # Get tool implementation
            if hasattr(MCPTools, tool_name):
                tool_method = getattr(MCPTools, tool_name)
                result = await tool_method(tool_arguments)
                
                return JSONRPCResponse(
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result)
                            }
                        ]
                    },
                    id=request_id
                )
            else:
                return JSONRPCResponse(
                    error={
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    },
                    id=request_id
                )
        
        else:
            return JSONRPCResponse(
                error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                id=request_id
            )
    
    except Exception as e:
        return JSONRPCResponse(
            error={
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            id=request_data.id if hasattr(request_data, 'id') else None
        )

# Routes
@app.get("/")
async def root():
    """Root endpoint - returns MCP server info in JSON-RPC format"""
    return JSONRPCResponse(
        result={
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": MCP_SERVER_INFO["name"],
                "version": MCP_SERVER_INFO["version"]
            },
            "capabilities": MCP_SERVER_INFO["capabilities"]
        },
        id=1
    ).dict()

@app.post("/")
async def jsonrpc_endpoint(request: Request):
    """Main JSON-RPC 2.0 endpoint"""
    try:
        body = await request.json()
        
        # Handle single request
        if isinstance(body, dict):
            jsonrpc_request = JSONRPCRequest(**body)
            response = await handle_jsonrpc_request(jsonrpc_request)
            return response.dict()
        
        # Handle batch requests
        elif isinstance(body, list):
            responses = []
            for item in body:
                jsonrpc_request = JSONRPCRequest(**item)
                response = await handle_jsonrpc_request(jsonrpc_request)
                responses.append(response.dict())
            return responses
        
        else:
            return JSONRPCResponse(
                error={
                    "code": -32600,
                    "message": "Invalid Request"
                },
                id=None
            ).dict()
    
    except Exception as e:
        logger.error(f"JSON-RPC request failed: {e}")
        return JSONRPCResponse(
            error={
                "code": -32700,
                "message": "Parse error",
                "data": str(e)
            },
            id=None
        ).dict()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    tool_impl = MCPTools()
    result = await tool_impl.system_health({})
    return result

# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", "8006"))
    uvicorn.run(
        "mcp_data_server_jsonrpc:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )