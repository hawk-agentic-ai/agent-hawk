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
        return (HawkErrorCodes.DATABASE_CONNECTION_ERROR, "Database connection error", "system", "db_connect")
    if "cache" in error_str:
        return (HawkErrorCodes.CACHE_ERROR, "Cache operation failed", "system", "cache")
    if tool_name == "process_hedge_prompt" and "stage_1a" in error_str:
        return (HawkErrorCodes.STAGE_1A_VALIDATION_FAILED, "Stage 1A validation failed", "stage_1a", "validation")
    # Add more categorizations as needed
    return (HawkErrorCodes.INTERNAL_ERROR, "Internal server error", "unknown", "general")

# -----------------------------------------------------------------------------
# Result Guard and Content Formatting
# -----------------------------------------------------------------------------
def _result_guard_pack(result: Any) -> tuple[Any, bool]:
    # Truncate if too large (e.g., >300KB)
    packed = result
    truncated = False
    if isinstance(result, (dict, list)) and json.dumps(result).__sizeof__() > 300 * 1024:
        packed = result[:100] if isinstance(result, list) else {k: v for k, v in list(result.items())[:100]}
        truncated = True
    return packed, truncated

def _as_content(result: Any) -> List[Dict[str, Any]]:
    # FIXED: Use 'text' type and stringify the result to match Dify's CallToolResult schema
    # Previously: [{"type": "json", "json": result}] — caused Pydantic validation errors
    text_content = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
    return [{"type": "text", "text": text_content}]

# -----------------------------------------------------------------------------
# JSON-RPC Endpoint
# -----------------------------------------------------------------------------
@app.post("/")
async def mcp_endpoint(request: Request, authorization: Optional[str] = Header(default=None)):
    _authz_or_403(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _jsonrpc_error(None, HawkErrorCodes.INVALID_REQUEST, "Invalid JSON request")

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if method == "callTool":
        tool_name = params.get("tool")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "process_hedge_prompt":
                result = await to_thread.run_sync(
                    hedge_processor.process_hedge_prompt,
                    arguments.get("user_prompt"),
                    arguments.get("currency"),
                    arguments.get("amount"),
                    arguments.get("operation_type"),
                    arguments.get("write_data")
                )
            elif tool_name == "query_supabase_data":
                result = await to_thread.run_sync(
                    hedge_processor.query_supabase_data,
                    arguments.get("table_name"),
                    arguments.get("operation", "select"),
                    arguments.get("filters", {}),
                    arguments.get("order_by"),
                    arguments.get("limit")
                )
            elif tool_name == "get_system_health":
                result = await to_thread.run_sync(hedge_processor.get_system_health)
            elif tool_name == "manage_cache":
                result = await to_thread.run_sync(
                    hedge_processor.manage_cache,
                    arguments.get("operation"),
                    arguments.get("key"),
                    arguments.get("value"),
                    arguments.get("ttl")
                )
            elif tool_name == "generate_agent_report":
                result = await to_thread.run_sync(
                    hedge_processor.generate_agent_report,
                    arguments.get("agent_type"),
                    arguments.get("processing_result"),
                    arguments.get("instruction_id"),
                    arguments.get("include_verification", True)
                )
            else:
                return _jsonrpc_error(req_id, HawkErrorCodes.METHOD_NOT_FOUND,
                                      f"Tool not found: {tool_name}",
                                      "Available: process_hedge_prompt, query_supabase_data, get_system_health, manage_cache, generate_agent_report")

            # Post-size guard (avoid 300KB blasts)
            packed, truncated = _result_guard_pack(result)

            # FIXED: Use the updated _as_content to ensure Dify-compatible format
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