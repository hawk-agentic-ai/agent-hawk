#!/usr/bin/env python3
"""
Dify-Compatible MCP Server (HTTP JSON-RPC 2.0)
- Goal: Provide a minimal MCP-over-HTTP surface compatible with Dify Cloud connectors
- Scope: Transport + tool routing only. Business logic remains in shared modules.
"""

import json
import logging
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, Response, Header, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

import os
from typing import Optional, Dict, Any

# Shared business logic processor
from shared.hedge_processor import hedge_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Secure CORS configuration
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:4200,https://dify.ai").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"]
)

# Server state
initialized = False
AUTH_TOKEN = os.getenv("DIFY_TOOL_TOKEN", "").strip()

@app.on_event("startup")
async def startup_init():
    try:
        await hedge_processor.initialize()
        logger.info("MCP server: HedgeFundProcessor initialized on startup")
    except Exception as e:
        logger.error(f"MCP server startup init failed: {e}")

def _authz_or_403(auth_header: Optional[str]):
    if not AUTH_TOKEN:
        return  # auth disabled
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bearer token")

# Enhanced Error Handling for HAWK Operations
class HawkErrorCodes:
    # JSON-RPC Standard Errors
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # HAWK-Specific Business Logic Errors (Range: -32000 to -32099)
    STAGE_1A_VALIDATION_FAILED = -32001
    STAGE_1B_ALLOCATION_FAILED = -32002
    STAGE_2_BOOKING_FAILED = -32003
    STAGE_3_GL_POSTING_FAILED = -32004

    # Data/Configuration Errors (Range: -32100 to -32199)
    INSUFFICIENT_HEDGE_CAPACITY = -32101
    INVALID_CURRENCY = -32102
    ENTITY_NOT_FOUND = -32103
    MISSING_RATE_DATA = -32104
    DATABASE_CONNECTION_ERROR = -32105
    CACHE_ERROR = -32106

    # Authentication/Authorization (Range: -32200 to -32299)
    AUTH_TOKEN_MISSING = -32200
    AUTH_TOKEN_INVALID = -32201
    INSUFFICIENT_PERMISSIONS = -32202

def _jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None, stage: str = None, operation: str = None):
    """Enhanced JSON-RPC error with HAWK-specific context"""
    err: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": code,
            "message": message
        }
    }

    # Add contextual data for debugging
    error_data = {}
    if data is not None:
        error_data["details"] = str(data)
    if stage:
        error_data["hawk_stage"] = stage
    if operation:
        error_data["operation"] = operation
    error_data["timestamp"] = datetime.now().isoformat()

    if error_data:
        err["error"]["data"] = error_data

    return err

def _categorize_hedge_error(exception: Exception, tool_name: str, arguments: dict) -> tuple[int, str, str, str]:
    """Categorize exceptions into HAWK-specific error codes"""
    error_str = str(exception).lower()

    # Database/Connection Errors
    if "connection" in error_str or "supabase" in error_str:
        return (HawkErrorCodes.DATABASE_CONNECTION_ERROR,
                "Database connection failed", "Stage 1A", "Database Access")

    # Cache Errors
    if "redis" in error_str or "cache" in error_str:
        return (HawkErrorCodes.CACHE_ERROR,
                "Cache operation failed", "System", "Cache Management")

    # Stage-Specific Errors Based on Tool and Arguments
    if tool_name == "process_hedge_prompt":
        template_category = arguments.get("template_category", "").lower()

        if "utilization" in template_category:
            return (HawkErrorCodes.STAGE_1A_VALIDATION_FAILED,
                    f"Stage 1A utilization check failed: {exception}", "Stage 1A", "Utilization Check")
        elif "inception" in template_category:
            return (HawkErrorCodes.STAGE_2_BOOKING_FAILED,
                    f"Stage 2 hedge inception failed: {exception}", "Stage 2", "Hedge Booking")
        elif "rollover" in template_category or "termination" in template_category:
            return (HawkErrorCodes.STAGE_1B_ALLOCATION_FAILED,
                    f"Stage 1B business event processing failed: {exception}", "Stage 1B", "Event Processing")

    # Currency/Entity Validation Errors
    if "currency" in error_str and arguments.get("currency"):
        return (HawkErrorCodes.INVALID_CURRENCY,
                f"Invalid currency '{arguments.get('currency')}': {exception}", "Validation", "Currency Check")

    if "entity" in error_str and arguments.get("entity_id"):
        return (HawkErrorCodes.ENTITY_NOT_FOUND,
                f"Entity '{arguments.get('entity_id')}' not found: {exception}", "Validation", "Entity Check")

    # Capacity/Amount Errors
    if "capacity" in error_str or "insufficient" in error_str:
        return (HawkErrorCodes.INSUFFICIENT_HEDGE_CAPACITY,
                f"Insufficient hedge capacity: {exception}", "Stage 1A", "Capacity Check")

    # Default to generic internal error
    return (HawkErrorCodes.INTERNAL_ERROR,
            f"Internal processing error in {tool_name}: {exception}", "System", tool_name)

def _validate_tool_parameters(tool_name: str, arguments: dict) -> callable:
    """Validate tool parameters and return error function if invalid"""

    if tool_name == "process_hedge_prompt":
        if not arguments.get("user_prompt"):
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                "Missing required parameter: user_prompt",
                "The user_prompt parameter is required for hedge operations",
                "Validation", "Parameter Check"
            )

    elif tool_name == "query_supabase_data":
        if not arguments.get("table_name"):
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                "Missing required parameter: table_name",
                "The table_name parameter is required for database queries",
                "Validation", "Parameter Check"
            )

        # Validate table name against known HAWK tables (from KB docs - All Tables Glossary.md)
        known_base_tables = [
            # Core operational tables
            "allocation_engine", "hedge_instructions", "hedge_business_events",
            "entity_master", "currency_configuration", "position_nav_master",
            "deal_bookings", "gl_entries", "currency_rates",

            # Configuration tables
            "audit_trail", "buffer_configuration", "capacity_overrides", "car_master",
            "car_parameters", "car_thresholds", "currency_rate_pairs", "system_configuration",

            # Agent operations tables
            "hawk_agent_attachments", "hawk_agent_conversations", "hawk_agent_errors",
            "hawk_agent_sessions", "prompt_templates",

            # Stage-specific tables
            "hedge_be_config", "hedge_effectiveness", "hedge_instruments", "hedging_framework",
            "instruction_event_config", "murex_book_config", "h_stg_mrx_ext",

            # GL and accounting tables
            "gl_be_narrative_templates", "gl_coa", "gl_entries_detail", "gl_journal_lines",
            "gl_periods", "gl_posting_queue", "gl_rules", "stage_bundles",

            # Risk and monitoring tables
            "risk_metrics", "risk_monitoring", "stage2_error_log", "trade_history",

            # Financial data tables
            "fx_proxy_parameters", "market_data", "mx_discounted_spot", "mx_proxy_hedge_report",
            "overlay_configuration", "portfolio_positions", "proxy_configuration",
            "threshold_configuration", "usd_pb_deposit", "hfm_template_entries",

            # Archive tables
            "deal_bookings_archive", "hedge_instructions_archive", "gl_entries_archive"
        ]

        # Add views (read-only access)
        known_views = [
            "currency_rates_parsed", "hedge_instructions_legacy", "mv_car_latest",
            "position_nav_master_with_exposure", "v_allocation_waterfall_summary",
            "v_available_amounts_fast", "v_available_amounts_test", "v_ccy_to_usd",
            "v_entity_capacity_complete", "v_event_acked_deals", "v_event_acked_deals_new",
            "v_event_expected_deals", "v_gl_export_ready", "v_hedge_instructions_fast",
            "v_hedge_lifecycle_status", "v_hedge_positions_fast", "v_hi_actionable",
            "hawk_hbe_instruction_mismatch"
        ]

        all_known_tables = known_base_tables + known_views
        table_name = arguments.get("table_name")
        if table_name not in all_known_tables:
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                f"Unknown table: {table_name}",
                f"Available tables: {len(all_known_tables)} total (base tables + views)",
                "Validation", "Table Check"
            )

        # Restrict write operations to base tables only (not views)
        operation = arguments.get("operation", "select")
        if operation in ["insert", "update", "delete"] and table_name in known_views:
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                f"Write operation '{operation}' not allowed on view: {table_name}",
                "Views are read-only. Use base tables for write operations.",
                "Validation", "Operation Check"
            )

    elif tool_name == "manage_cache":
        operation = arguments.get("operation")
        if not operation:
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                "Missing required parameter: operation",
                "Valid operations: stats, info, clear_currency",
                "Validation", "Parameter Check"
            )

        if operation not in ["stats", "info", "clear_currency"]:
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                f"Invalid cache operation: {operation}",
                "Valid operations: stats, info, clear_currency",
                "Validation", "Parameter Check"
            )

        if operation == "clear_currency" and not arguments.get("currency"):
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                "Missing currency parameter for clear_currency operation",
                "Currency code required when clearing currency-specific cache",
                "Validation", "Parameter Check"
            )

    # All validations passed
    return None

def _tools_list_result(req_id: Any):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "process_hedge_prompt",
                    "description": "Complete hedge fund operations workflow: Stage 1A (Allocation), Stage 2 (Booking), Stage 3 (GL Posting) with full CRUD on all core tables",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_prompt": {"type": "string"},
                            "template_category": {"type": "string"},
                            "currency": {"type": "string"},
                            "entity_id": {"type": "string"},
                            "nav_type": {"type": "string"},
                            "amount": {"type": "number"},
                            "use_cache": {"type": "boolean", "default": True},
                            "operation_type": {"type": "string", "enum": ["read", "write", "amend", "mx_booking", "gl_posting"], "default": "read"},
                            "stage_mode": {"type": "string", "enum": ["auto", "1A", "2", "3"], "default": "auto", "description": "Stage restriction for agent specialization"},
                            "agent_role": {"type": "string", "enum": ["allocation", "booking", "unified"], "default": "unified", "description": "Agent role for specialized processing"},
                            "output_format": {"type": "string", "enum": ["json", "agent_report"], "default": "json", "description": "Output format for agent compatibility"},
                            "write_data": {"type": "object", "description": "Data for any core table: allocation_engine, hedge_instructions, hedge_business_events, deal_bookings, h_stg_mrx_ext, hedge_gl_packages, hedge_gl_entries"},
                            "instruction_id": {"type": "string", "description": "Instruction ID for workflow operations"},
                            "execute_booking": {"type": "boolean", "default": False, "description": "Execute Stage 2 Murex booking"},
                            "execute_posting": {"type": "boolean", "default": False, "description": "Execute Stage 3 GL posting"}
                        },
                        "required": ["user_prompt"]
                    }
                },
                {
                    "name": "query_supabase_data",
                    "description": "Full CRUD Supabase operations: select, insert, update, delete on all hedge fund tables",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "Target table name"},
                            "operation": {"type": "string", "enum": ["select", "insert", "update", "delete"], "default": "select"},
                            "filters": {"type": "object", "default": {}, "description": "WHERE clause filters"},
                            "data": {"type": "object", "description": "Data for insert/update operations"},
                            "limit": {"type": "integer", "default": 100},
                            "order_by": {"type": "string", "default": None},
                            "use_cache": {"type": "boolean", "default": True}
                        },
                        "required": ["table_name"]
                    }
                },
                {
                    "name": "get_system_health",
                    "description": "Get system health and cache stats",
                    "inputSchema": {"type": "object", "properties": {}, "required": []}
                },
                {
                    "name": "manage_cache",
                    "description": "Cache operations: stats | info | clear_currency",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "operation": {"type": "string", "enum": ["stats", "info", "clear_currency"]},
                            "currency": {"type": "string"}
                        },
                        "required": ["operation"]
                    }
                },
                {
                    "name": "generate_agent_report",
                    "description": "Generate stage-specific agent reports with rich markdown tables and assessments",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_type": {"type": "string", "enum": ["allocation", "booking"], "description": "Agent specialization type"},
                            "processing_result": {"type": "object", "description": "Result from process_hedge_prompt"},
                            "instruction_id": {"type": "string", "description": "Optional instruction ID for verification"},
                            "include_verification": {"type": "boolean", "default": True, "description": "Include database verification tables"}
                        },
                        "required": ["agent_type", "processing_result"]
                    }
                },
                # =============================================================================
                # AGENT-SPECIFIC BRIDGE TOOLS
                # =============================================================================
                {
                    "name": "allocation_stage1a_processor",
                    "description": "Allocation Agent Stage 1A: Capacity assessment and utilization validation with buffer application",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_prompt": {"type": "string"},
                            "currency": {"type": "string"},
                            "entity_id": {"type": "string"},
                            "nav_type": {"type": "string"},
                            "amount": {"type": "number"},
                            "write_data": {"type": "object", "description": "Allocation engine write data"}
                        },
                        "required": ["user_prompt", "currency", "entity_id", "amount"]
                    }
                },
                {
                    "name": "allocation_utilization_checker",
                    "description": "Check available hedging capacity and utilization for allocation decisions",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "currency": {"type": "string"},
                            "entity_id": {"type": "string"},
                            "nav_type": {"type": "string"},
                            "amount": {"type": "number"}
                        },
                        "required": ["currency", "entity_id", "amount"]
                    }
                },
                {
                    "name": "hedge_booking_processor",
                    "description": "Booking Agent Stage 2: Execute hedge deal booking in Murex with validation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_prompt": {"type": "string"},
                            "instruction_id": {"type": "string"},
                            "currency": {"type": "string"},
                            "entity_id": {"type": "string"},
                            "amount": {"type": "number"},
                            "execute_booking": {"type": "boolean", "default": True},
                            "write_data": {"type": "object", "description": "Booking data"}
                        },
                        "required": ["instruction_id", "currency", "amount"]
                    }
                },
                {
                    "name": "gl_posting_processor",
                    "description": "Booking Agent Stage 3: Create and post balanced GL journal entries",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_prompt": {"type": "string"},
                            "instruction_id": {"type": "string"},
                            "currency": {"type": "string"},
                            "amount": {"type": "number"},
                            "execute_posting": {"type": "boolean", "default": True},
                            "write_data": {"type": "object", "description": "GL posting data"}
                        },
                        "required": ["instruction_id", "currency", "amount"]
                    }
                },
                {
                    "name": "analytics_processor",
                    "description": "Analytics Agent: Generate performance analysis, risk metrics, and hedge effectiveness reports",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_prompt": {"type": "string"},
                            "currency": {"type": "string"},
                            "entity_id": {"type": "string"},
                            "time_period": {"type": "string", "default": "current"}
                        },
                        "required": ["user_prompt"]
                    }
                },
                {
                    "name": "config_crud_processor",
                    "description": "Config Agent: CRUD operations on configuration tables (entity_master, thresholds, etc.)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string"},
                            "operation": {"type": "string", "enum": ["select", "insert", "update", "delete"], "default": "select"},
                            "data": {"type": "object", "description": "Data for insert/update operations"},
                            "filters": {"type": "object", "description": "WHERE clause filters"},
                            "limit": {"type": "integer", "default": 100}
                        },
                        "required": ["table_name"]
                    }
                }
            ]
        }
    }

@app.post("/")
async def mcp_endpoint(request: Request, authorization: Optional[str] = Header(default=None)):
    global initialized
    
    try:
        _authz_or_403(authorization)
        body = await request.json()
        logger.info(f"Request: {json.dumps(body)}")
        
        method = body.get("method")
        req_id = body.get("id")
        params = body.get("params", {})
        
        if method == "initialize":
            initialized = False  # Reset state
            
            # Return minimal initialization response
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "hedge-fund-mcp",
                        "version": "1.0.1"
                    }
                }
            }
            logger.info(f"Initialize response: {json.dumps(response)}")
            return response
        
        elif method == "initialized":
            # Notification: no id expected; do not respond content
            initialized = True
            logger.info("Server marked as initialized (notification)")
            return Response(status_code=204)
        
        elif method == "notifications/initialized":
            # Alternative notification format
            initialized = True
            logger.info("Server marked as initialized (notification)")
            return Response(status_code=204)
        
        elif method == "tools/list":
            if not initialized:
                logger.warning("Tools/list called before initialization complete")
            return _tools_list_result(req_id)
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {}) or {}
            if not tool_name:
                return _jsonrpc_error(req_id, -32602, "Missing tool name")

            # Ensure processor is ready (in case startup hook failed)
            try:
                if hedge_processor and hedge_processor.data_extractor is None:
                    await hedge_processor.initialize()
            except Exception as e:
                return _jsonrpc_error(req_id, -32603, "Processor init failed", str(e))

            try:
                # Validate required parameters based on tool
                validation_error = _validate_tool_parameters(tool_name, arguments)
                if validation_error:
                    return validation_error(req_id)

                # Execute tool with enhanced error context
                if tool_name == "process_hedge_prompt":
                    # Stage validation for agent specialization
                    stage_mode = arguments.get("stage_mode", "auto")
                    operation_type = arguments.get("operation_type", "read")

                    # Validate stage-operation compatibility
                    stage_permissions = {
                        "1A": ["read", "write", "amend"],
                        "2": ["read", "mx_booking"],
                        "3": ["read", "gl_posting"]
                    }

                    if stage_mode != "auto" and operation_type not in stage_permissions.get(stage_mode, []):
                        return _jsonrpc_error(req_id, HawkErrorCodes.INVALID_PARAMS,
                                            f"Operation '{operation_type}' not allowed in stage '{stage_mode}'",
                                            f"Stage {stage_mode} only allows: {stage_permissions.get(stage_mode, [])}")

                    result = await hedge_processor.universal_prompt_processor(
                        user_prompt=arguments.get("user_prompt"),
                        template_category=arguments.get("template_category"),
                        currency=arguments.get("currency"),
                        entity_id=arguments.get("entity_id"),
                        nav_type=arguments.get("nav_type"),
                        amount=arguments.get("amount"),
                        use_cache=arguments.get("use_cache", True),
                        operation_type=operation_type,
                        write_data=arguments.get("write_data"),
                        instruction_id=arguments.get("instruction_id"),
                        execute_booking=arguments.get("execute_booking", False),
                        execute_posting=arguments.get("execute_posting", False),
                        # New stage-aware parameters
                        stage_mode=stage_mode,
                        agent_role=arguments.get("agent_role", "unified"),
                        output_format=arguments.get("output_format", "json")
                    )
                elif tool_name == "query_supabase_data":
                    result = await hedge_processor.query_supabase_direct(
                        table_name=arguments.get("table_name"),
                        operation=arguments.get("operation", "select"),
                        filters=arguments.get("filters"),
                        data=arguments.get("data"),
                        limit=arguments.get("limit"),
                        order_by=arguments.get("order_by"),
                        use_cache=arguments.get("use_cache", True)
                    )
                elif tool_name == "get_system_health":
                    result = hedge_processor.get_system_health()
                elif tool_name == "manage_cache":
                    result = hedge_processor.manage_cache_operations(
                        operation=arguments.get("operation"),
                        currency=arguments.get("currency")
                    )
                elif tool_name == "generate_agent_report":
                    # Import agent report generator
                    from shared.agent_report_generator import agent_report_generator

                    # Set supabase client for verification queries
                    agent_report_generator.supabase_client = hedge_processor.supabase_client

                    result = await agent_report_generator.generate_report(
                        agent_type=arguments.get("agent_type"),
                        processing_result=arguments.get("processing_result"),
                        instruction_id=arguments.get("instruction_id"),
                        include_verification=arguments.get("include_verification", True)
                    )

                # =============================================================================
                # AGENT-SPECIFIC BRIDGE TOOLS
                # =============================================================================
                elif tool_name in ["allocation_stage1a_processor", "allocation_utilization_checker",
                                 "hedge_booking_processor", "gl_posting_processor", "murex_integration_processor",
                                 "analytics_processor", "performance_analyzer", "risk_calculator",
                                 "config_crud_processor", "entity_manager", "threshold_manager"]:

                    # Route to MCP bridge
                    from shared.mcp_tool_bridges import get_mcp_bridge

                    mcp_bridge = get_mcp_bridge()
                    if not mcp_bridge:
                        return _jsonrpc_error(req_id, HawkErrorCodes.INTERNAL_ERROR,
                                            "MCP bridge not initialized",
                                            "Bridge tools require MCP bridge to be initialized")

                    result = await mcp_bridge.execute_tool(tool_name, arguments)

                    # Add bridge metadata
                    if isinstance(result, dict):
                        result["bridge_metadata"] = {
                            "bridge_tool": tool_name,
                            "routed_to_backend": True,
                            "timestamp": datetime.now().isoformat()
                        }

                else:
                    # Enhanced available tools list including bridges
                    available_tools = [
                        "process_hedge_prompt", "query_supabase_data", "get_system_health", "manage_cache", "generate_agent_report",
                        # Allocation Agent Tools
                        "allocation_stage1a_processor", "allocation_utilization_checker",
                        # Booking Agent Tools
                        "hedge_booking_processor", "gl_posting_processor", "murex_integration_processor",
                        # Analytics Agent Tools
                        "analytics_processor", "performance_analyzer", "risk_calculator",
                        # Config Agent Tools
                        "config_crud_processor", "entity_manager", "threshold_manager"
                    ]

                    return _jsonrpc_error(req_id, HawkErrorCodes.METHOD_NOT_FOUND,
                                        f"Tool not found: {tool_name}",
                                        f"Available tools: {', '.join(available_tools)}")

                # Enhanced success response with metadata
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                        ],
                        "metadata": {
                            "tool": tool_name,
                            "timestamp": datetime.now().isoformat(),
                            "success": True
                        }
                    }
                }

            except Exception as e:
                # Use intelligent error categorization
                error_code, error_msg, stage, operation = _categorize_hedge_error(e, tool_name, arguments)
                logger.error(f"HAWK {stage} error in {operation}: {e}", extra={
                    "tool": tool_name,
                    "stage": stage,
                    "operation": operation,
                    "arguments": arguments
                })
                return _jsonrpc_error(req_id, error_code, error_msg, str(e), stage, operation)
        
        else:
            return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")
    
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        req_id = None
        try:
            # try get id from body if available
            if 'body' in locals() and isinstance(body, dict):
                req_id = body.get("id")
        except Exception:
            pass
        return _jsonrpc_error(req_id, -32603, "Internal error", str(e))

@app.get("/")
async def root_get():
    """Return no content on GET to avoid JSON-RPC parsers misinterpreting health payloads."""
    return Response(status_code=204, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    })

@app.head("/")
async def root_head():
    """Return no content on HEAD as well."""
    return Response(status_code=204, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    })

@app.options("/")
async def root_options():
    """Return no content on OPTIONS to satisfy any preflight checks."""
    return Response(status_code=204, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    })

# Add /mcp endpoint for Dify compatibility
@app.post("/mcp")
async def mcp_dify_endpoint(request: Request, authorization: Optional[str] = Header(default=None)):
    return await mcp_endpoint(request, authorization)

if __name__ == "__main__":
    # Run using the current module's app to avoid import name mismatches
    uvicorn.run(app, host="0.0.0.0", port=8009, log_level="info")
