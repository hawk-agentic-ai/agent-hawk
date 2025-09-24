#!/usr/bin/env python3
"""
Standalone HTTP MCP Server for Complete Supabase Database Operations
Port: 8006 | Protocol: HTTP | Purpose: Full CRUD operations for Dify Cloud
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

# MCP Tool Definitions
MCP_TOOLS = {
    "query_table": {
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
    "insert_record": {
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
    "update_record": {
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
    "delete_record": {
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
    "list_tables": {
        "name": "list_tables",
        "description": "Get list of all available tables in the database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_system": {"type": "boolean", "default": False, "description": "Include system tables"}
            }
        }
    },
    "get_table_schema": {
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
    "execute_sql": {
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
    "system_health": {
        "name": "system_health",
        "description": "Get MCP server health and database connection status",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
}

# Pydantic Models
class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

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
    title="Hedge Fund MCP Data Server",
    description="HTTP MCP Server for complete Supabase database operations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Tool Implementations
class MCPTools:
    """MCP tool implementations for database operations"""
    
    @staticmethod
    async def query_table(arguments: Dict[str, Any]) -> MCPResponse:
        """Query table with filters and options"""
        try:
            table_name = arguments["table_name"]
            filters = arguments.get("filters", {})
            columns = arguments.get("columns")
            limit = arguments.get("limit", 100)
            order_by = arguments.get("order_by")
            offset = arguments.get("offset", 0)
            
            # Build query
            query = supabase_client.table(table_name)
            
            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)
            
            # Apply column selection
            if columns:
                query = query.select(",".join(columns))
            
            # Apply ordering
            if order_by:
                if order_by.startswith("-"):
                    query = query.order(order_by[1:], desc=True)
                else:
                    query = query.order(order_by)
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            # Execute query
            result = query.execute()
            
            return MCPResponse(
                success=True,
                data=result.data,
                metadata={
                    "table": table_name,
                    "count": len(result.data),
                    "limit": limit,
                    "offset": offset
                }
            )
            
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    @staticmethod
    async def insert_record(arguments: Dict[str, Any]) -> MCPResponse:
        """Insert new record"""
        try:
            table_name = arguments["table_name"]
            data = arguments["data"]
            return_record = arguments.get("return_record", True)
            
            # Add audit fields
            data["created_at"] = datetime.utcnow().isoformat()
            data["updated_at"] = datetime.utcnow().isoformat()
            
            # Insert record
            if return_record:
                result = supabase_client.table(table_name).insert(data).execute()
                return MCPResponse(
                    success=True,
                    data=result.data[0] if result.data else None,
                    metadata={"table": table_name, "operation": "insert"}
                )
            else:
                supabase_client.table(table_name).insert(data).execute()
                return MCPResponse(
                    success=True,
                    data={"message": "Record inserted successfully"},
                    metadata={"table": table_name, "operation": "insert"}
                )
                
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    @staticmethod
    async def update_record(arguments: Dict[str, Any]) -> MCPResponse:
        """Update existing record"""
        try:
            table_name = arguments["table_name"]
            record_id = arguments["record_id"]
            data = arguments["data"]
            id_column = arguments.get("id_column", "id")
            
            # Add audit fields
            data["updated_at"] = datetime.utcnow().isoformat()
            
            # Update record
            result = supabase_client.table(table_name)\
                .update(data)\
                .eq(id_column, record_id)\
                .execute()
            
            return MCPResponse(
                success=True,
                data=result.data[0] if result.data else None,
                metadata={
                    "table": table_name,
                    "operation": "update",
                    "record_id": record_id
                }
            )
            
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    @staticmethod
    async def delete_record(arguments: Dict[str, Any]) -> MCPResponse:
        """Delete record"""
        try:
            table_name = arguments["table_name"]
            record_id = arguments["record_id"]
            id_column = arguments.get("id_column", "id")
            
            # Delete record
            result = supabase_client.table(table_name)\
                .delete()\
                .eq(id_column, record_id)\
                .execute()
            
            return MCPResponse(
                success=True,
                data={"message": f"Record {record_id} deleted successfully"},
                metadata={
                    "table": table_name,
                    "operation": "delete", 
                    "record_id": record_id
                }
            )
            
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    @staticmethod
    async def list_tables(arguments: Dict[str, Any]) -> MCPResponse:
        """List all tables"""
        try:
            # Get tables from information_schema
            result = supabase_client.rpc("get_table_list").execute()
            
            return MCPResponse(
                success=True,
                data=result.data,
                metadata={"operation": "list_tables"}
            )
            
        except Exception as e:
            # Fallback to common hedge fund tables
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
            return MCPResponse(
                success=True,
                data=tables,
                metadata={"operation": "list_tables", "source": "fallback"}
            )
    
    @staticmethod
    async def get_table_schema(arguments: Dict[str, Any]) -> MCPResponse:
        """Get table schema"""
        try:
            table_name = arguments["table_name"]
            
            # Query information_schema for column details
            result = supabase_client.rpc("get_table_schema", {"table_name": table_name}).execute()
            
            return MCPResponse(
                success=True,
                data=result.data,
                metadata={"table": table_name, "operation": "schema"}
            )
            
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    @staticmethod
    async def execute_sql(arguments: Dict[str, Any]) -> MCPResponse:
        """Execute custom SQL query"""
        try:
            sql_query = arguments["sql_query"]
            params = arguments.get("params", {})
            
            # Basic SQL validation
            sql_lower = sql_query.lower().strip()
            allowed_operations = ["select", "insert", "update", "delete"]
            
            if not any(sql_lower.startswith(op) for op in allowed_operations):
                return MCPResponse(
                    success=False, 
                    error="Only SELECT, INSERT, UPDATE, DELETE operations allowed"
                )
            
            # Execute query
            result = supabase_client.rpc("execute_sql", {
                "query": sql_query,
                "params": params
            }).execute()
            
            return MCPResponse(
                success=True,
                data=result.data,
                metadata={"operation": "custom_sql"}
            )
            
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    @staticmethod
    async def system_health(arguments: Dict[str, Any]) -> MCPResponse:
        """Get system health"""
        try:
            health_data = {
                "status": "healthy",
                "server": "mcp-data-server",
                "version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": {
                    "supabase": "connected" if supabase_client else "disconnected",
                    "redis": "connected" if redis_client else "disconnected"
                }
            }
            
            # Test database connection
            if supabase_client:
                try:
                    test_result = supabase_client.table("entity_master").select("count").limit(1).execute()
                    health_data["database_test"] = "success"
                except Exception as e:
                    health_data["database_test"] = f"failed: {str(e)}"
                    health_data["status"] = "degraded"
            
            return MCPResponse(
                success=True,
                data=health_data,
                metadata={"operation": "health_check"}
            )
            
        except Exception as e:
            return MCPResponse(success=False, error=str(e))

# MCP HTTP Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Hedge Fund MCP Data Server", 
        "version": "1.0.0",
        "protocol": "http",
        "tools_available": len(MCP_TOOLS)
    }

@app.get("/mcp/tools")
async def list_tools():
    """MCP tool discovery endpoint"""
    return {
        "tools": list(MCP_TOOLS.values())
    }

@app.post("/mcp/call/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """Call specific MCP tool"""
    try:
        body = await request.json()
        arguments = body.get("arguments", {})
        
        if tool_name not in MCP_TOOLS:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Get tool implementation
        tool_method = getattr(MCPTools, tool_name)
        result = await tool_method(arguments)
        
        return result.dict()
        
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        return MCPResponse(success=False, error=str(e)).dict()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    tool_impl = MCPTools()
    result = await tool_impl.system_health({})
    return result.dict()

# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", "8006"))
    uvicorn.run(
        "mcp_data_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )