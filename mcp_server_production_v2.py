#!/usr/bin/env python3
"""
Dify-Compatible MCP Server (HTTP JSON-RPC 2.0) — Prompt-Intelligent + Safe Caps

What’s in here:
- Intent inference for Stage 1A analytical reads (utilization, PB deposit summary, capacity)
- No hard-mandated filters; the server infers and then guards via caps + truncation
- Single Supabase client reuse; health probes use the same client path
- JSON content items for structured results (not giant text blobs)
- Unified CORS and strict init gating
- Table/view validation aligned with HAWK KB tables

Grounded on your current server and KB tables. 
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import inspect

import uvicorn
from fastapi import FastAPI, Request, Response, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from anyio import to_thread

# Shared business logic processor
from shared.hedge_processor import hedge_processor

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp")

# -----------------------------------------------------------------------------
# App & CORS (single source of truth; JSON-RPC = POST only)
# -----------------------------------------------------------------------------
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

ALLOWED_ORIGINS: List[str] = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:4200,https://dify.ai,https://cloud.dify.ai"
).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST"],     # JSON-RPC endpoint only
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"]
)

# -----------------------------------------------------------------------------
# State / Auth
# -----------------------------------------------------------------------------
initialized = False
AUTH_TOKEN = os.getenv("DIFY_TOOL_TOKEN", "").strip()
REQUIRE_AUTH_ON_HEALTH = os.getenv("REQUIRE_AUTH_ON_HEALTH", "false").lower() == "true"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _authz_or_403(auth_header: Optional[str]):
    if not AUTH_TOKEN:
        return  # auth disabled
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bearer token")

# -----------------------------------------------------------------------------
# Error codes (from your server)
# -----------------------------------------------------------------------------
class HawkErrorCodes:
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    STAGE_1A_VALIDATION_FAILED = -32001
    STAGE_1B_ALLOCATION_FAILED = -32002
    STAGE_2_BOOKING_FAILED = -32003
    STAGE_3_GL_POSTING_FAILED = -32004

    INSUFFICIENT_HEDGE_CAPACITY = -32101
    INVALID_CURRENCY = -32102
    ENTITY_NOT_FOUND = -32103
    MISSING_RATE_DATA = -32104
    DATABASE_CONNECTION_ERROR = -32105
    CACHE_ERROR = -32106

    AUTH_TOKEN_MISSING = -32200
    AUTH_TOKEN_INVALID = -32201
    INSUFFICIENT_PERMISSIONS = -32202

def _jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None,
                   stage: str = None, operation: str = None):
    err: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message}
    }
    error_data = {}
    if data is not None:
        error_data["details"] = str(data)
    if stage:
        error_data["hawk_stage"] = stage
    if operation:
        error_data["operation"] = operation
    error_data["timestamp"] = _now_iso()
    if error_data:
        err["error"]["data"] = error_data
    return err

def _categorize_hedge_error(exception: Exception, tool_name: str, arguments: dict):
    error_str = str(exception).lower()
    if "connection" in error_str or "supabase" in error_str:
        return (HawkErrorCodes.DATABASE_CONNECTION_ERROR, "Database connection failed", "Stage 1A", "Database Access")
    if "redis" in error_str or "cache" in error_str:
        return (HawkErrorCodes.CACHE_ERROR, "Cache operation failed", "System", "Cache Management")
    if tool_name == "process_hedge_prompt":
        template_category = (arguments.get("template_category") or "").lower()
        if "utilization" in template_category:
            return (HawkErrorCodes.STAGE_1A_VALIDATION_FAILED, f"Stage 1A utilization check failed: {exception}", "Stage 1A", "Utilization Check")
        if "inception" in template_category:
            return (HawkErrorCodes.STAGE_2_BOOKING_FAILED, f"Stage 2 hedge inception failed: {exception}", "Stage 2", "Hedge Booking")
        if "rollover" in template_category or "termination" in template_category:
            return (HawkErrorCodes.STAGE_1B_ALLOCATION_FAILED, f"Stage 1B business event processing failed: {exception}", "Stage 1B", "Event Processing")
    if "currency" in error_str and arguments.get("currency"):
        return (HawkErrorCodes.INVALID_CURRENCY, f"Invalid currency '{arguments.get('currency')}': {exception}", "Validation", "Currency Check")
    if "entity" in error_str and arguments.get("entity_id"):
        return (HawkErrorCodes.ENTITY_NOT_FOUND, f"Entity '{arguments.get('entity_id')}' not found: {exception}", "Validation", "Entity Check")
    if "capacity" in error_str or "insufficient" in error_str:
        return (HawkErrorCodes.INSUFFICIENT_HEDGE_CAPACITY, f"Insufficient hedge capacity: {exception}", "Stage 1A", "Capacity Check")
    return (HawkErrorCodes.INTERNAL_ERROR, f"Internal processing error in {tool_name}: {exception}", "System", tool_name)

# -----------------------------------------------------------------------------
# Stage aliasing (accept 'stage_1a' etc.)
# -----------------------------------------------------------------------------
def _stage_alias(stage_in: Optional[str]) -> str:
    alias = (stage_in or "auto").strip().lower()
    stage_map = {"1a": "1A", "stage_1a": "1A", "stage1a": "1A",
                 "pre_utilization": "1A", "auto": "auto", "2": "2", "3": "3"}
    return stage_map.get(alias, "auto")

# -----------------------------------------------------------------------------
# HAWK KB-aligned tables & views (cross-checked from your file)  :contentReference[oaicite:1]{index=1}
# -----------------------------------------------------------------------------
KNOWN_BASE_TABLES = [
    "allocation_engine", "hedge_instructions", "hedge_business_events",
    "entity_master", "currency_configuration", "position_nav_master",
    "deal_bookings", "gl_entries", "currency_rates",
    "audit_trail", "buffer_configuration", "capacity_overrides", "car_master",
    "car_parameters", "car_thresholds", "currency_rate_pairs", "system_configuration",
    "hawk_agent_attachments", "hawk_agent_conversations", "hawk_agent_errors",
    "hawk_agent_sessions", "prompt_templates",
    "hedge_be_config", "hedge_effectiveness", "hedge_instruments", "hedging_framework",
    "instruction_event_config", "murex_book_config", "h_stg_mrx_ext",
    "gl_be_narrative_templates", "gl_coa", "gl_entries_detail", "gl_journal_lines",
    "gl_periods", "gl_posting_queue", "gl_rules", "stage_bundles",
    "risk_metrics", "risk_monitoring", "stage2_error_log", "trade_history",
    "fx_proxy_parameters", "market_data", "mx_discounted_spot", "mx_proxy_hedge_report",
    "overlay_configuration", "portfolio_positions", "proxy_configuration",
    "threshold_configuration", "usd_pb_deposit", "hfm_template_entries",
    "deal_bookings_archive", "hedge_instructions_archive", "gl_entries_archive"
]
KNOWN_VIEWS = [
    "currency_rates_parsed", "hedge_instructions_legacy", "mv_car_latest",
    "position_nav_master_with_exposure", "v_allocation_waterfall_summary",
    "v_available_amounts_fast", "v_available_amounts_test", "v_ccy_to_usd",
    "v_entity_capacity_complete", "v_event_acked_deals", "v_event_acked_deals_new",
    "v_event_expected_deals", "v_gl_export_ready", "v_hedge_instructions_fast",
    "v_hedge_lifecycle_status", "v_hedge_positions_fast", "v_hi_actionable",
    "hawk_hbe_instruction_mismatch"
]
ALL_KNOWN = set(KNOWN_BASE_TABLES) | set(KNOWN_VIEWS)

# -----------------------------------------------------------------------------
# Validation helpers (no hard filter mandate for Stage 1A analytics)
# -----------------------------------------------------------------------------
def _validate_tool_parameters(tool_name: str, arguments: dict):
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
        t = arguments["table_name"]
        if t not in ALL_KNOWN:
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                f"Unknown table: {t}",
                f"Available tables: {len(ALL_KNOWN)} total (base + views)",
                "Validation", "Table Check"
            )
        op = arguments.get("operation", "select")
        if op in ["insert", "update", "delete"] and t in KNOWN_VIEWS:
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                f"Write operation '{op}' not allowed on view: {t}",
                "Views are read-only. Use base tables for write operations.",
                "Validation", "Operation Check"
            )
    elif tool_name == "manage_cache":
        op = arguments.get("operation")
        if op not in ["stats", "info", "clear_currency"]:
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                f"Invalid or missing cache operation: {op}",
                "Valid operations: stats, info, clear_currency",
                "Validation", "Parameter Check"
            )
        if op == "clear_currency" and not arguments.get("currency"):
            return lambda req_id: _jsonrpc_error(
                req_id, HawkErrorCodes.INVALID_PARAMS,
                "Missing currency parameter for clear_currency operation",
                "Currency code required when clearing currency-specific cache",
                "Validation", "Parameter Check"
            )
    return None

# -----------------------------------------------------------------------------
# Intent inference (Stage 1A analytics)
# -----------------------------------------------------------------------------
ISO_CCY = {
    "USD","EUR","GBP","AUD","NZD","CAD","SGD","CHF","JPY","CNY","HKD","INR","SEK","NOK","DKK","ZAR","AED","SAR"
}
ENTITY_RE = re.compile(r"\b([A-Z]{2}[A-Z]{1,}[A-Z]*\d{3,})\b")
CCY_RE = re.compile(r"\b([A-Z]{3})\b")

def _infer_stage1a_intent(user_prompt: str) -> dict:
    text = (user_prompt or "").strip()
    lo = text.lower()

    if any(k in lo for k in ["utilisation", "utilization", "can we hedge", "put on another hedge", "headroom"]):
        intent = "utilization_check"
    elif any(k in lo for k in ["pb deposit", "usd pb", "prime brokerage", "pb balance", "pb summary"]):
        intent = "pb_deposit_summary"
    elif any(k in lo for k in ["capacity", "max hedge", "available amount", "headroom summary"]):
        intent = "capacity_summary"
    else:
        intent = "stage1a_generic_read"

    currency = None
    for m in CCY_RE.findall(text):
        if m in ISO_CCY:
            currency = m
            break

    amount = None
    amt_match = re.search(r"\b(\d[\d,_.]*)(\s*[kKmM])?\b", text)
    if amt_match:
        raw = amt_match.group(1).replace(",", "").replace("_", "")
        suffix = (amt_match.group(2) or "").strip().lower()
        try:
            amt_val = float(raw)
            if suffix == "k": amt_val *= 1_000
            elif suffix == "m": amt_val *= 1_000_000
            amount = amt_val
        except Exception:
            pass

    entities = ENTITY_RE.findall(text)
    return {"intent": intent, "currency": currency, "amount": amount, "entities": entities}

# -----------------------------------------------------------------------------
# Result packing & caps
# -----------------------------------------------------------------------------
MAX_ROWS_CAP = int(os.getenv("MAX_ROWS_CAP", "200"))
MAX_BYTES_CAP = int(os.getenv("MAX_BYTES_CAP", str(128 * 1024)))  # 128 KB

def _as_content(result: Any) -> List[Dict[str, Any]]:
    # Dify MCP clients expect content items of type 'text'|'image'|'resource'.
    # Return text-only content to satisfy Pydantic validation.
    if isinstance(result, (dict, list)):
        try:
            text_content = json.dumps(result, default=str)
        except Exception:
            text_content = str(result)
        return [{"type": "text", "text": text_content}]
    return [{"type": "text", "text": str(result)}]

def _result_guard_pack(packed):
    encoded = json.dumps(packed, default=str).encode("utf-8")
    if len(encoded) <= MAX_BYTES_CAP:
        return packed, False
    sample = packed[:50] if isinstance(packed, list) else packed
    return {
        "truncated": True,
        "approx_bytes": len(encoded),
        "hint": "Refine filters (currency/entity/date_window) or narrow intent",
        "sample": sample
    }, True

# -----------------------------------------------------------------------------
# Safe call wrapper for processor
# -----------------------------------------------------------------------------
async def _call_universal_prompt_processor_safe(arguments: dict, operation_type: str):
    fn = hedge_processor.universal_prompt_processor
    sig = inspect.signature(fn)

    kwargs = {
        "user_prompt": arguments.get("user_prompt"),
        "template_category": arguments.get("template_category"),
        "currency": arguments.get("currency"),
        "entity_id": arguments.get("entity_id"),
        "nav_type": arguments.get("nav_type"),
        "amount": arguments.get("amount"),
        "use_cache": arguments.get("use_cache", True),
        "operation_type": operation_type,
        "write_data": arguments.get("write_data"),
        "instruction_id": arguments.get("instruction_id"),
        "execute_booking": arguments.get("execute_booking", False),
        "execute_posting": arguments.get("execute_posting", False),
        "stage_mode": arguments.get("stage_mode", "auto"),
        "agent_role": arguments.get("agent_role", "unified"),
        "output_format": arguments.get("output_format", "json"),
        # Optional caps – only pass if supported
        "max_rows": arguments.get("max_rows"),
        "max_kb": arguments.get("max_kb"),
    }

    filtered = {k: v for k, v in kwargs.items() if v is not None and k in sig.parameters}
    return await fn(**filtered)

# -----------------------------------------------------------------------------
# Startup (single client init)
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_init():
    try:
        await hedge_processor.initialize()
        logger.info("MCP server: HedgeFundProcessor initialized on startup")
    except Exception as e:
        logger.error(f"MCP server startup init failed: {e}")

# -----------------------------------------------------------------------------
# Tools list
# -----------------------------------------------------------------------------
def _tools_list_result(req_id: Any):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "process_hedge_prompt",
                    "description": "Stage 1A/2/3 processing with prompt-intent inference and safe caps",
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
                            "stage_mode": {"type": "string", "enum": ["auto", "1A", "2", "3"], "default": "auto"},
                            "agent_role": {"type": "string", "enum": ["allocation", "booking", "unified"], "default": "unified"},
                            "output_format": {"type": "string", "enum": ["json", "agent_report"], "default": "json"},
                            "write_data": {"type": "object"},
                            "instruction_id": {"type": "string"},
                            "execute_booking": {"type": "boolean", "default": False},
                            "execute_posting": {"type": "boolean", "default": False},
                            "max_rows": {"type": "integer", "default": 100},
                            "max_kb": {"type": "integer", "default": 128}
                        },
                        "required": ["user_prompt"]
                    }
                },
                {
                    "name": "query_supabase_data",
                    "description": "CRUD with known-table validation and default caps",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string"},
                            "operation": {"type": "string", "enum": ["select", "insert", "update", "delete"], "default": "select"},
                            "filters": {"type": "object", "default": {}},
                            "data": {"type": "object"},
                            "limit": {"type": "integer", "default": 50},
                            "order_by": {"type": "string", "default": None},
                            "use_cache": {"type": "boolean", "default": True}
                        },
                        "required": ["table_name"]
                    }
                },
                {
                    "name": "get_system_health",
                    "description": "Get system health and DB probe",
                    "inputSchema": {"type": "object", "properties": {}, "required": []}
                },
                {
                    "name": "manage_cache",
                    "description": "Cache ops: stats | info | clear_currency",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"operation": {"type": "string", "enum": ["stats", "info", "clear_currency"]},
                                       "currency": {"type": "string"}},
                        "required": ["operation"]
                    }
                },
                {
                    "name": "generate_agent_report",
                    "description": "Generate stage-specific agent reports",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_type": {"type": "string", "enum": ["allocation", "booking"]},
                            "processing_result": {"type": "object"},
                            "instruction_id": {"type": "string"},
                            "include_verification": {"type": "boolean", "default": True}
                        },
                        "required": ["agent_type", "processing_result"]
                    }
                }
            ]
        }
    }

# -----------------------------------------------------------------------------
# JSON-RPC endpoint
# -----------------------------------------------------------------------------
@app.post("/")
async def mcp_endpoint(request: Request, authorization: Optional[str] = Header(default=None)):
    global initialized
    _authz_or_403(authorization)

    body = await request.json()
    logger.info("Request: %s", json.dumps(body, ensure_ascii=False))

    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {}) or {}

    # Strict init gate
    if method in ("tools/list", "tools/call") and not initialized:
        return _jsonrpc_error(req_id, HawkErrorCodes.INVALID_REQUEST,
                              "Server not initialized; call 'initialize' then 'initialized'.")

    if method == "initialize":
        initialized = False
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "hedge-fund-mcp", "version": "1.2.0"}
            }
        }

    if method in ("initialized", "notifications/initialized"):
        initialized = True
        return Response(status_code=204)

    if method == "tools/list":
        return _tools_list_result(req_id)

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {}) or {}
        if not tool_name:
            return _jsonrpc_error(req_id, HawkErrorCodes.INVALID_PARAMS, "Missing tool name")

        # Ensure processor is ready
        try:
            if hedge_processor and getattr(hedge_processor, "data_extractor", None) is None:
                await hedge_processor.initialize()
        except Exception as e:
            return _jsonrpc_error(req_id, HawkErrorCodes.INTERNAL_ERROR, "Processor init failed", str(e))

        # Validate args
        validation_error = _validate_tool_parameters(tool_name, arguments)
        if validation_error:
            return validation_error(req_id)

        try:
            if tool_name == "process_hedge_prompt":
                stage_mode = _stage_alias(arguments.get("stage_mode"))
                operation_type = arguments.get("operation_type", "read")

                stage_permissions = {"1A": ["read", "write", "amend"],
                                     "2": ["read", "mx_booking"],
                                     "3": ["read", "gl_posting"]}
                if stage_mode != "auto" and operation_type not in stage_permissions.get(stage_mode, []):
                    return _jsonrpc_error(req_id, HawkErrorCodes.INVALID_PARAMS,
                                          f"Operation '{operation_type}' not allowed in stage '{stage_mode}'",
                                          f"Stage {stage_mode} only allows: {stage_permissions.get(stage_mode, [])}")

                # Prompt-intelligent inference for Stage 1A analytics (no hard mandates)
                inferred = _infer_stage1a_intent(arguments.get("user_prompt"))
                if stage_mode in ("1A", "auto") and operation_type == "read":
                    arguments.setdefault("currency", inferred.get("currency"))
                    if arguments.get("amount") is None and inferred.get("amount") is not None:
                        arguments["amount"] = inferred["amount"]
                    if not arguments.get("entity_id") and inferred["entities"]:
                        arguments["entity_id"] = ",".join(inferred["entities"])

                    intent = inferred["intent"]
                    if intent == "pb_deposit_summary":
                        arguments.setdefault("template_category", "usd_pb_deposit_summary")
                    elif intent == "capacity_summary":
                        arguments.setdefault("template_category", "capacity_summary")
                    elif intent == "utilization_check":
                        arguments.setdefault("template_category", "utilization_check")
                    else:
                        arguments.setdefault("template_category", "stage1a_generic_read")

                    # Soft caps passed to processor
                    arguments["max_rows"] = min(int(arguments.get("max_rows", 100)), MAX_ROWS_CAP)
                    arguments["max_kb"] = min(int(arguments.get("max_kb", 128)), MAX_BYTES_CAP // 1024)

                # Call shared logic with the SAME client (safe kwarg filter for compatibility)
                result = await _call_universal_prompt_processor_safe(arguments, operation_type)

            elif tool_name == "query_supabase_data":
                req_limit = arguments.get("limit", 50) or 50
                limit = min(int(req_limit), MAX_ROWS_CAP)
                result = await hedge_processor.query_supabase_direct(
                    table_name=arguments.get("table_name"),
                    operation=arguments.get("operation", "select"),
                    filters=arguments.get("filters") or {},
                    data=arguments.get("data"),
                    limit=limit,
                    order_by=arguments.get("order_by"),
                    use_cache=arguments.get("use_cache", True),
                )

            elif tool_name == "get_system_health":
                result = hedge_processor.get_system_health()

            elif tool_name == "manage_cache":
                result = hedge_processor.manage_cache_operations(
                    operation=arguments.get("operation"),
                    currency=arguments.get("currency")
                )

            elif tool_name == "generate_agent_report":
                from shared.agent_report_generator import agent_report_generator
                agent_report_generator.supabase_client = hedge_processor.supabase_client
                result = await agent_report_generator.generate_report(
                    agent_type=arguments.get("agent_type"),
                    processing_result=arguments.get("processing_result"),
                    instruction_id=arguments.get("instruction_id"),
                    include_verification=arguments.get("include_verification", True)
                )

            else:
                return _jsonrpc_error(req_id, HawkErrorCodes.METHOD_NOT_FOUND,
                                      f"Tool not found: {tool_name}",
                                      "Available: process_hedge_prompt, query_supabase_data, get_system_health, manage_cache, generate_agent_report")

            # Post-size guard (avoid 300KB blasts)
            packed, truncated = _result_guard_pack(result)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": _as_content(packed),
                    "metadata": {
                        "tool": tool_name,
                        "timestamp": _now_iso(),
                        "success": True,
                        "truncated": truncated
                    }
                }
            }

        except Exception as e:
            code, msg, stage, op = _categorize_hedge_error(e, tool_name, arguments)
            logger.error("HAWK %s error in %s: %s", stage, op, e, extra={
                "tool": tool_name, "stage": stage, "operation": op, "arguments": arguments
            })
            return _jsonrpc_error(req_id, code, msg, str(e), stage, op)

    return _jsonrpc_error(req_id, HawkErrorCodes.METHOD_NOT_FOUND, f"Method not found: {method}")

# -----------------------------------------------------------------------------
# Health endpoints (using the same Supabase client)
# -----------------------------------------------------------------------------
def _mask(s: str) -> str:
    if not s: return ""
    if len(s) <= 8: return "****"
    return f"{s[:4]}…{s[-4:]}"

async def _tiny_db_probe() -> Dict[str, Any]:
    if hedge_processor is None or hedge_processor.supabase_client is None:
        return {"status": "error", "error": "supabase_client not initialized"}
    try:
        res = hedge_processor.supabase_client.table("currency_rates").select("*").limit(1).execute()
        return {"status": "ok", "table": "currency_rates", "records": len(res.data or [])}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/")
async def root_get(authorization: Optional[str] = Header(default=None)):
    if REQUIRE_AUTH_ON_HEALTH:
        _authz_or_403(authorization)
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
    probe = await _tiny_db_probe()
    return {
        "status": "ok" if probe.get("status") == "ok" else "error",
        "name": "hedge-fund-mcp",
        "protocol": "jsonrpc-2.0",
        "version": "1.2.0",
        "timestamp": _now_iso(),
        "supabase": {"connected": probe.get("status") == "ok",
                     "url": url, "key_present": bool(key), "key_masked": _mask(key)},
        "db_probe": probe
    }

@app.get("/health")
async def health(authorization: Optional[str] = Header(default=None)):
    if REQUIRE_AUTH_ON_HEALTH:
        _authz_or_403(authorization)
    return await root_get(authorization)

@app.get("/health/db")
async def health_db(authorization: Optional[str] = Header(default=None)):
    if REQUIRE_AUTH_ON_HEALTH:
        _authz_or_403(authorization)
    return await _tiny_db_probe()

# -----------------------------------------------------------------------------
# Optional /mcp/* aliases
# -----------------------------------------------------------------------------
@app.post("/mcp/")
async def mcp_endpoint_alias(request: Request, authorization: Optional[str] = Header(default=None)):
    return await mcp_endpoint(request, authorization)

@app.get("/mcp/")
async def mcp_get_alias(authorization: Optional[str] = Header(default=None)):
    return await root_get(authorization)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8009")), log_level="info")
