#!/usr/bin/env python3
"""
HAWK Stage 1A Allocation Agent - Dedicated MCP Server
Port 8010 | Optimized for allocation operations with intelligent intent detection
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

import uvicorn
from fastapi import FastAPI, Request, Response, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Database imports
from supabase import create_client, Client
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hawk_allocation_mcp")

# -----------------------------------------------------------------------------
# Global State & Configuration
# -----------------------------------------------------------------------------
initialized = False
supabase_client: Optional[Client] = None
redis_client: Optional[redis.Redis] = None

def _load_env_from_files():
    """Best-effort load of env variables from common .env files if missing.
    Avoids startup failures when process manager didn’t inject env.
    """
    candidates = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), ".env.production"),
    ]
    for path in candidates:
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        # Support both KEY=VAL and export KEY=VAL
                        if line.startswith("export "):
                            line = line[len("export "):]
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip()
                            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                v = v[1:-1]
                            if k and v and k not in os.environ:
                                os.environ[k] = v
        except Exception:
            continue

# Prime env from files if critical vars are missing
if not os.getenv("SUPABASE_URL") or not (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")):
    _load_env_from_files()

# Environment variables (after attempted load)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AUTH_TOKEN = os.getenv("DIFY_TOOL_TOKEN", "").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()

# Performance settings
MAX_RESPONSE_SIZE_KB = int(os.getenv("MAX_RESPONSE_SIZE_KB", "64"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes

# -----------------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------------
async def initialize_connections():
    """Initialize Supabase and Redis connections"""
    global supabase_client, redis_client

    try:
        # Always initialize for SSE discovery, even without DB
        if SUPABASE_URL and SUPABASE_KEY:
            supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized")
        else:
            logger.warning("Missing Supabase credentials - SSE will work for discovery")
            # Set a placeholder so SSE endpoint works
            supabase_client = True

        # Initialize Redis (optional, non-blocking)
        try:
            redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

            # Test connection with ping
            redis_client.ping()
            logger.info("✅ Redis client connected and healthy")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
            redis_client = None
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Caching will be disabled.")
            redis_client = None

        return True

    except Exception as e:
        logger.warning(f"Database initialization issue: {e}")
        # Still return True to allow SSE discovery
        supabase_client = True
        return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    success = await initialize_connections()
    if not success:
        logger.error("Startup failed - database connections not available")
    yield
    # Shutdown
    pass

# -----------------------------------------------------------------------------
# FastAPI App Configuration
# -----------------------------------------------------------------------------
app = FastAPI(
    title="HAWK Allocation MCP Server",
    description="Stage 1A Dedicated MCP Server with Intent Detection",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration - Match production v2 pattern
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:4200,https://dify.ai"
).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["Content-Type", "Authorization"]
)

# -----------------------------------------------------------------------------
# Intent Detection Engine
# -----------------------------------------------------------------------------
class IntentDetector:
    """Intelligent intent detection for Stage 1A operations"""

    # Currency patterns
    CURRENCIES = {
        "USD", "EUR", "GBP", "AUD", "NZD", "CAD", "SGD", "CHF", "JPY",
        "CNY", "HKD", "INR", "SEK", "NOK", "DKK", "ZAR", "AED", "SAR",
        "TWD", "KRW", "THB", "MYR"
    }

    # Regex patterns
    CURRENCY_RE = re.compile(r'\b([A-Z]{3})\b')
    AMOUNT_RE = re.compile(r'\b(\d+(?:[.,]\d+)*)\s*([KMB]?)\b', re.IGNORECASE)
    ENTITY_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9_]+)\b')

    # Intent classification patterns
    QUERY_INDICATORS = [
        "show", "what's", "what is", "available", "status", "breakdown",
        "summary", "how much", "display", "list", "get", "view"
    ]

    INSTRUCTION_INDICATORS = [
        "can i", "can we", "check if", "process", "hedge", "place",
        "put on", "create", "would like", "want to", "utilization", "utilisation"
    ]

    @classmethod
    def detect_intent(cls, user_prompt: str) -> Dict[str, Any]:
        """Detect intent and extract parameters from natural language prompt"""
        text = user_prompt.lower().strip()

        # Extract currency
        currency = None
        for match in cls.CURRENCY_RE.findall(user_prompt.upper()):
            if match in cls.CURRENCIES:
                currency = match
                break

        # Extract amount
        amount = None
        amount_match = cls.AMOUNT_RE.search(text)
        if amount_match:
            try:
                value = float(amount_match.group(1).replace(',', ''))
                suffix = amount_match.group(2).upper()
                if suffix == 'K':
                    value *= 1_000
                elif suffix == 'M':
                    value *= 1_000_000
                elif suffix == 'B':
                    value *= 1_000_000_000
                amount = value
            except (ValueError, AttributeError):
                pass

        # Extract entities
        entities = cls.ENTITY_RE.findall(user_prompt.upper())

        # Classify intent type
        intent_type = "query"  # default
        confidence = 0.5

        # Check for instruction indicators
        instruction_score = sum(1 for indicator in cls.INSTRUCTION_INDICATORS
                               if indicator in text)
        query_score = sum(1 for indicator in cls.QUERY_INDICATORS
                         if indicator in text)

        # Intent scoring logic
        if instruction_score > query_score or amount is not None:
            intent_type = "instruction"
            confidence = 0.8 if instruction_score > 0 else 0.7
        elif query_score > 0:
            intent_type = "query"
            confidence = 0.8

        # Determine intent subtype
        intent_subtype = cls._classify_subtype(text, intent_type, currency, amount)

        return {
            "intent_type": intent_type,
            "intent_subtype": intent_subtype,
            "currency": currency,
            "amount": amount,
            "entities": entities,
            "confidence": confidence,
            "extracted_text": {
                "original": user_prompt,
                "normalized": text
            }
        }

    @classmethod
    def _classify_subtype(cls, text: str, intent_type: str, currency: str, amount: float) -> str:
        """Classify the specific subtype of intent"""

        if intent_type == "query":
            if "capacity" in text or "available" in text or "headroom" in text:
                return "capacity_query"
            elif "threshold" in text or "pb" in text or "usd" in text:
                return "threshold_query"
            elif "breakdown" in text or "entity" in text or "summary" in text:
                return "entity_analysis"
            else:
                return "general_query"

        else:  # instruction
            if amount and currency:
                return "utilization_instruction"
            elif "utilization" in text or "utilisation" in text:
                return "utilization_check"
            elif "hedge" in text and ("can" in text or "check" in text):
                return "hedge_feasibility"
            else:
                return "general_instruction"

# -----------------------------------------------------------------------------
# View-First Query Engine
# -----------------------------------------------------------------------------
class ViewOptimizedQuery:
    """Optimized query engine with view-first approach"""

    AVAILABLE_VIEWS = {
        "v_entity_capacity_complete": "Complete entity capacity analysis",
        "v_available_amounts_fast": "Rapid available capacity calculations",
        "v_usd_pb_capacity_check": "USD threshold monitoring",
        "v_allocation_waterfall_summary": "Allocation priority sequencing"
    }

    def __init__(self, supabase_client: Client, redis_client: Optional[redis.Redis] = None):
        self.supabase = supabase_client
        self.redis = redis_client

    async def query_by_intent(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route query based on detected intent"""

        intent_subtype = intent_data["intent_subtype"]
        currency = intent_data["currency"]
        entities = intent_data["entities"]

        # Route to appropriate view
        if intent_subtype == "capacity_query":
            return await self._query_capacity(currency, entities)
        elif intent_subtype == "threshold_query":
            return await self._query_thresholds(currency)
        elif intent_subtype == "entity_analysis":
            return await self._query_entity_breakdown(currency)
        else:
            return await self._query_general_capacity(currency)

    async def _query_capacity(self, currency: str, entities: List[str]) -> Dict[str, Any]:
        """Query entity capacity using optimized view"""

        try:
            query = self.supabase.table("v_entity_capacity_complete").select("*")

            if currency:
                query = query.eq("currency_code", currency)
            if entities:
                query = query.in_("entity_id", entities)

            query = query.limit(50)  # Reasonable limit
            result = query.execute()

            return {
                "data": result.data,
                "source": "v_entity_capacity_complete",
                "cache_hit": False,
                "record_count": len(result.data) if result.data else 0
            }

        except Exception as e:
            logger.error(f"View query failed: {e}")
            return {"data": [], "error": str(e)}

    async def _query_thresholds(self, currency: str) -> Dict[str, Any]:
        """Query USD PB thresholds"""

        try:
            query = self.supabase.table("v_usd_pb_capacity_check").select("*")
            if currency:
                query = query.eq("currency_code", currency)
            result = query.execute()

            return {
                "data": result.data,
                "source": "v_usd_pb_capacity_check",
                "cache_hit": False
            }

        except Exception as e:
            logger.error(f"Threshold query failed: {e}")
            return {"data": [], "error": str(e)}

    async def _query_entity_breakdown(self, currency: str) -> Dict[str, Any]:
        """Query entity breakdown and analysis"""

        try:
            query = self.supabase.table("v_allocation_waterfall_summary").select("*")
            if currency:
                query = query.eq("currency_code", currency)
            result = query.execute()

            return {
                "data": result.data,
                "source": "v_allocation_waterfall_summary",
                "cache_hit": False
            }

        except Exception as e:
            logger.error(f"Entity breakdown query failed: {e}")
            return {"data": [], "error": str(e)}

    async def _query_general_capacity(self, currency: str) -> Dict[str, Any]:
        """General capacity query using fast amounts view"""

        try:
            query = self.supabase.table("v_available_amounts_fast").select("*")
            if currency:
                query = query.eq("currency_code", currency)
            result = query.execute()

            return {
                "data": result.data,
                "source": "v_available_amounts_fast",
                "cache_hit": False
            }

        except Exception as e:
            logger.error(f"General capacity query failed: {e}")
            return {"data": [], "error": str(e)}

# -----------------------------------------------------------------------------
# Stage 1A Instruction Pipeline
# -----------------------------------------------------------------------------
class Stage1AInstructionProcessor:
    """Complete Stage 1A instruction processing with database writes"""

    def __init__(self, supabase_client: Client, query_engine: ViewOptimizedQuery):
        self.supabase = supabase_client
        self.query_engine = query_engine

    async def process_instruction(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process complete Stage 1A instruction with feasibility and persistence"""

        start_time = time.time()

        # Generate unique identifiers
        msg_uid = f"HAWK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        instruction_id = f"INS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Extract parameters
        currency = intent_data["currency"]
        amount = intent_data["amount"]
        user_prompt = intent_data["extracted_text"]["original"]

        # Step 1: Perform feasibility analysis
        feasibility_result = await self._analyze_feasibility(currency, amount)

        # Step 2: Record instruction
        db_result = await self._record_instruction(
            msg_uid, instruction_id, currency, amount, user_prompt, feasibility_result
        )

        processing_time = round((time.time() - start_time) * 1000, 2)

        return {
            "intent": intent_data["intent_subtype"],
            "instruction_id": instruction_id,
            "msg_uid": msg_uid,
            "feasibility": feasibility_result,
            "database_writes": {
                "hedge_instructions": db_result
            },
            "processing_time_ms": processing_time,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _analyze_feasibility(self, currency: str, amount: float) -> Dict[str, Any]:
        """Analyze hedge feasibility using Stage 1A logic"""

        if not currency or not amount:
            return {
                "status": "Fail",
                "reason": "Missing required parameters (currency or amount)",
                "allocated_amount": 0
            }

        try:
            # Get capacity data
            capacity_data = await self.query_engine._query_capacity(currency, [])

            if not capacity_data["data"]:
                return {
                    "status": "Fail",
                    "reason": f"No capacity data available for {currency}",
                    "allocated_amount": 0
                }

            # Calculate total available capacity
            total_capacity = sum(
                float(row.get("available_capacity", 0) or 0)
                for row in capacity_data["data"]
            )

            # Feasibility logic
            if amount <= total_capacity:
                status = "Pass"
                allocated_amount = amount
                reason = f"Sufficient capacity available ({total_capacity:,.0f} {currency})"
            elif total_capacity > 0:
                status = "Partial"
                allocated_amount = total_capacity
                reason = f"Partial allocation available ({total_capacity:,.0f} {currency})"
            else:
                status = "Fail"
                allocated_amount = 0
                reason = f"No available capacity for {currency}"

            return {
                "status": status,
                "reason": reason,
                "allocated_amount": allocated_amount,
                "requested_amount": amount,
                "total_capacity": total_capacity,
                "currency": currency
            }

        except Exception as e:
            logger.error(f"Feasibility analysis failed: {e}")
            return {
                "status": "Fail",
                "reason": f"Analysis error: {str(e)}",
                "allocated_amount": 0
            }

    async def _record_instruction(self, msg_uid: str, instruction_id: str,
                                currency: str, amount: float, user_prompt: str,
                                feasibility: Dict[str, Any]) -> Dict[str, Any]:
        """Record instruction in hedge_instructions table"""

        try:
            instruction_data = {
                "instruction_id": instruction_id,
                "msg_uid": msg_uid,
                "instruction_type": "U",  # Utilization check
                "instruction_date": datetime.now().date().isoformat(),
                "exposure_currency": currency,
                "hedge_amount_order": amount,
                "instruction_status": "Processed",
                "check_status": feasibility["status"],
                "available_amount": feasibility["allocated_amount"],
                "reason": feasibility["reason"],
                "user_prompt": user_prompt,
                "created_date": datetime.now(timezone.utc).isoformat(),
                "created_by": "HAWK_Allocation_Agent"
            }

            result = self.supabase.table("hedge_instructions").insert(instruction_data).execute()

            return {
                "status": "SUCCESS",
                "table": "hedge_instructions",
                "instruction_id": instruction_id,
                "records_inserted": len(result.data) if result.data else 0
            }

        except Exception as e:
            logger.error(f"Instruction recording failed: {e}")
            return {
                "status": "FAILED",
                "table": "hedge_instructions",
                "error": str(e)
            }

# Initialize global processors
query_engine = None
instruction_processor = None

def get_processors():
    """Get or initialize processors"""
    global query_engine, instruction_processor

    if not query_engine and supabase_client:
        query_engine = ViewOptimizedQuery(supabase_client, redis_client)

    if not instruction_processor and supabase_client and query_engine:
        instruction_processor = Stage1AInstructionProcessor(supabase_client, query_engine)

    return query_engine, instruction_processor

# -----------------------------------------------------------------------------
# Error Handling
# -----------------------------------------------------------------------------
class AllocationErrorCodes:
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

def _jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    """Generate JSON-RPC 2.0 error response"""
    error_response = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

    if data is not None:
        error_response["error"]["data"] = data

    return error_response

def _jsonrpc_success(req_id: Any, result: Any) -> Dict[str, Any]:
    """Generate JSON-RPC 2.0 success response"""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result
    }

# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------
def _check_auth(auth_header: Optional[str]):
    """Check authorization if token is configured"""
    if not AUTH_TOKEN:
        return  # Auth disabled

    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = auth_header.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bearer token")

# -----------------------------------------------------------------------------
# MCP Tools Implementation
# -----------------------------------------------------------------------------
def _get_tools_list(req_id: Any) -> Dict[str, Any]:
    """Return available MCP tools"""
    return _jsonrpc_success(req_id, {
        "tools": [
            {
                "name": "allocation_stage1a_processor",
                "description": "Intelligent Stage 1A processing with automatic intent detection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_prompt": {
                            "type": "string",
                            "description": "Natural language request for Stage 1A operations"
                        },
                        "force_write": {
                            "type": "boolean",
                            "default": False,
                            "description": "Force instruction recording even for query-type prompts"
                        }
                    },
                    "required": ["user_prompt"]
                }
            },
            {
                "name": "query_allocation_view",
                "description": "Direct access to optimized views for fast analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "view_name": {
                            "type": "string",
                            "enum": [
                                "v_entity_capacity_complete",
                                "v_available_amounts_fast",
                                "v_usd_pb_capacity_check",
                                "v_allocation_waterfall_summary"
                            ]
                        },
                        "filters": {
                            "type": "object",
                            "description": "Dynamic filters applied to the view"
                        }
                    },
                    "required": ["view_name"]
                }
            },
            {
                "name": "get_allocation_health",
                "description": "Stage 1A system health and performance metrics",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
    })

async def _handle_allocation_processor(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle allocation_stage1a_processor tool calls"""

    user_prompt = arguments.get("user_prompt", "").strip()
    force_write = arguments.get("force_write", False)

    if not user_prompt:
        raise ValueError("user_prompt is required")

    # Get processors
    q_engine, inst_processor = get_processors()
    if not q_engine:
        raise ValueError("Query engine not available")

    # Detect intent
    intent_data = IntentDetector.detect_intent(user_prompt)

    # Force instruction mode if requested
    if force_write:
        intent_data["intent_type"] = "instruction"
        intent_data["intent_subtype"] = "utilization_instruction"

    # Route based on intent
    if intent_data["intent_type"] == "instruction" and inst_processor:
        # Full instruction processing with database writes
        result = await inst_processor.process_instruction(intent_data)
        result["tool_mode"] = "instruction_pipeline"
    else:
        # Fast query processing using views
        result = await q_engine.query_by_intent(intent_data)
        result["tool_mode"] = "view_query"

    # Add intent metadata
    result["detected_intent"] = intent_data
    result["tool_name"] = "allocation_stage1a_processor"

    return result

async def _handle_view_query(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle query_allocation_view tool calls"""

    view_name = arguments.get("view_name")
    filters = arguments.get("filters", {})

    if not view_name:
        raise ValueError("view_name is required")

    # Get query engine
    q_engine, _ = get_processors()
    if not q_engine:
        raise ValueError("Query engine not available")

    # Direct view query
    try:
        query = q_engine.supabase.table(view_name).select("*")

        # Apply filters
        for key, value in filters.items():
            query = query.eq(key, value)

        query = query.limit(100)  # Safety limit
        result = query.execute()

        return {
            "view_name": view_name,
            "filters_applied": filters,
            "data": result.data,
            "record_count": len(result.data) if result.data else 0,
            "tool_name": "query_allocation_view"
        }

    except Exception as e:
        logger.error(f"View query failed: {e}")
        return {
            "view_name": view_name,
            "error": str(e),
            "data": [],
            "tool_name": "query_allocation_view"
        }

async def _handle_health_check() -> Dict[str, Any]:
    """Handle get_allocation_health tool calls"""

    # Database health
    db_health = {"connected": False, "response_time_ms": None}
    if supabase_client:
        try:
            start_time = time.time()
            result = supabase_client.table("currency_rates").select("*").limit(1).execute()
            db_health = {
                "connected": True,
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "last_query": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            db_health["error"] = str(e)

    # View availability
    view_health = {}
    if supabase_client:
        for view_name in ViewOptimizedQuery.AVAILABLE_VIEWS:
            try:
                supabase_client.table(view_name).select("*").limit(1).execute()
                view_health[view_name] = "available"
            except Exception:
                view_health[view_name] = "error"

    return {
        "status": "healthy" if db_health["connected"] else "degraded",
        "server": {
            "name": "hawk-allocation-mcp-server",
            "version": "1.0.0",
            "port": 8010,
            "specialization": "Stage 1A Allocation Operations"
        },
        "database": db_health,
        "views": view_health,
        "tool_name": "get_allocation_health",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# -----------------------------------------------------------------------------
# Dify Agent Integration - Tool Manifest
# -----------------------------------------------------------------------------
@app.get("/dify-agent-tools.json", include_in_schema=False)
async def get_dify_agent_tools():
    """
    Provides the tool manifest for Dify Agent integration.
    This endpoint describes the capabilities of the HAWK Stage 1A server.
    """
    # Get base URL from environment or construct from request
    base_url = PUBLIC_BASE_URL or "https://3-91-170-95.nip.io/dify"
    if not base_url:
        # Fallback to default if not configured
        base_url = "https://3-91-170-95.nip.io/dify"
        logger.warning(f"PUBLIC_BASE_URL not set, using default: {base_url}")

    tools = {
        "tools": [
            {
                "name": "hawk_stage1a_allocation",
                "description": (
                    "Processes a natural language instruction for a Stage 1A hedge allocation check. "
                    "Determines hedge capacity, validates against NAV positions and thresholds, "
                    "and returns a definitive status (e.g., 'Approved', 'Rejected'). "
                    "Use this tool for all pre-trade utilization checks for new hedges."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {
                            "type": "string",
                            "description": "The user's natural language instruction (e.g., 'check capacity for hedging 150M HKD in entity 1100')."
                        },
                        "trace_id": {
                            "type": "string",
                            "description": "A unique identifier for tracing the request through the HAWK lifecycle."
                        }
                    },
                    "required": ["instruction"]
                },
                "endpoint": {
                    "url": base_url,
                    "method": "POST",
                    "payload": {
                        "jsonrpc": "2.0",
                        "id": "{trace_id}",
                        "method": "tools/call",
                        "params": {
                            "name": "allocation_stage1a_processor",
                            "arguments": {
                                "user_prompt": "{instruction}",
                                "force_write": False
                            }
                        }
                    }
                }
            },
            {
                "name": "hawk_allocation_health",
                "description": (
                    "Checks the health and status of the HAWK allocation system. "
                    "Returns server status, database connectivity, and system performance metrics."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "endpoint": {
                    "url": base_url,
                    "method": "POST",
                    "payload": {
                        "jsonrpc": "2.0",
                        "id": "health_check",
                        "method": "tools/call",
                        "params": {
                            "name": "get_allocation_health",
                            "arguments": {}
                        }
                    }
                }
            },
            {
                "name": "hawk_capacity_query",
                "description": (
                    "Queries allocation capacity views for specific entities, currencies, or thresholds. "
                    "Provides direct access to optimized database views for capacity analysis."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "view_name": {
                            "type": "string",
                            "description": "The view to query (e.g., 'v_entity_capacity_complete', 'v_available_amounts_fast')."
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional filters to apply to the query (e.g., {'currency': 'USD', 'entity': '1100'})."
                        }
                    },
                    "required": ["view_name"]
                },
                "endpoint": {
                    "url": base_url,
                    "method": "POST",
                    "payload": {
                        "jsonrpc": "2.0",
                        "id": "capacity_query",
                        "method": "tools/call",
                        "params": {
                            "name": "query_allocation_view",
                            "arguments": {
                                "view_name": "{view_name}",
                                "filters": "{filters}"
                            }
                        }
                    }
                }
            }
        ]
    }
    return Response(content=json.dumps(tools, indent=2), media_type="application/json")

# -----------------------------------------------------------------------------
# MCP Protocol Endpoints
# -----------------------------------------------------------------------------
@app.options("/")
async def options_root():
    """Handle CORS preflight for MCP endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS, GET, HEAD",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400"
        }
    )

@app.get("/.well-known/mcp")
async def mcp_discovery(request: Request):
    """MCP server discovery endpoint"""
    # Get public base URL from environment
    def get_public_base_url() -> str:
        if PUBLIC_BASE_URL:
            return PUBLIC_BASE_URL
        # Fallback to default for backward compatibility
        logger.warning("PUBLIC_BASE_URL not set, using default URL")
        return "https://3-91-170-95.nip.io/dify"

    return {
        "mcp_version": "2024-11-05",
        "server_info": {
            "name": "hawk-allocation-mcp-server",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {"listChanged": True}
        },
        "transport": {
            "type": "http",
            "endpoint": get_public_base_url()
        }
    }

@app.post("/")
async def mcp_endpoint(request: Request, authorization: Optional[str] = Header(default=None)):
    """Main MCP JSON-RPC 2.0 endpoint"""
    global initialized

    # Only block if truly not initialized (supabase_client is None)
    if supabase_client is None:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Server not ready - database connections initializing",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    try:
        _check_auth(authorization)
        body = await request.json()

        method = body.get("method")
        req_id = body.get("id")
        params = body.get("params", {})

        logger.info(f"MCP Request: {method}")

        # MCP Protocol Methods
        if method == "initialize":
            initialized = False
            return _jsonrpc_success(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {
                    "name": "hawk-allocation-mcp-server",
                    "version": "1.0.0"
                }
            })

        elif method in ("initialized", "notifications/initialized"):
            initialized = True
            logger.info("MCP Server initialized")
            return Response(status_code=204)

        elif method == "tools/list":
            if not initialized:
                return _jsonrpc_error(req_id, AllocationErrorCodes.INVALID_REQUEST,
                                    "Server not initialized")
            return _get_tools_list(req_id)

        elif method == "tools/call":
            if not initialized:
                return _jsonrpc_error(req_id, AllocationErrorCodes.INVALID_REQUEST,
                                    "Server not initialized")

            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return _jsonrpc_error(req_id, AllocationErrorCodes.INVALID_PARAMS,
                                    "Missing tool name")

            # Route to appropriate tool handler
            try:
                if tool_name == "allocation_stage1a_processor":
                    result = await _handle_allocation_processor(arguments)
                elif tool_name == "query_allocation_view":
                    result = await _handle_view_query(arguments)
                elif tool_name == "get_allocation_health":
                    result = await _handle_health_check()
                else:
                    return _jsonrpc_error(req_id, AllocationErrorCodes.METHOD_NOT_FOUND,
                                        f"Unknown tool: {tool_name}")

                # Format response with content array
                return _jsonrpc_success(req_id, {
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                    ],
                    "metadata": {
                        "tool": tool_name,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "success": True
                    }
                })

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return _jsonrpc_error(req_id, AllocationErrorCodes.INTERNAL_ERROR,
                                    f"Tool execution error: {str(e)}")
        else:
            return _jsonrpc_error(req_id, AllocationErrorCodes.METHOD_NOT_FOUND,
                                f"Unknown method: {method}")

    except Exception as e:
        logger.error(f"Request processing failed: {e}")
        return _jsonrpc_error(None, AllocationErrorCodes.INTERNAL_ERROR,
                            f"Request processing error: {str(e)}")

# -----------------------------------------------------------------------------
# Health Endpoints
# -----------------------------------------------------------------------------
@app.get("/")
async def root():
    """Simple health endpoint matching production v2 pattern"""
    return {
        "status": "ok",
        "name": "hawk-allocation-mcp-server",
        "protocol": "jsonrpc-2.0",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "specialization": "Stage 1A Allocation Operations"
    }


@app.options("/sse")
async def options_sse():
    """Handle CORS preflight for SSE endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400"
        }
    )

@app.get("/sse")
@app.head("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for Dify MCP discovery.

    Dify expects a Server-Sent Events stream with event name 'endpoint' and the
    publicly reachable JSON-RPC URL in the data line. We construct this using
    host + an optional X-Forwarded-Prefix (set by the reverse proxy) so that
    deployments under a path like '/dify/' work correctly.
    """

    def build_public_base_url() -> str:
        # Get public base URL from environment
        # This is the URL that Dify needs to be able to connect to
        if PUBLIC_BASE_URL:
            return PUBLIC_BASE_URL
        # Fallback to default for backward compatibility
        logger.warning("PUBLIC_BASE_URL not set for SSE endpoint, using default URL")
        return "https://3-91-170-95.nip.io/dify"

    # Handle HEAD requests
    if request.method == "HEAD":
        origin = request.headers.get("origin")
        cors_origin = origin if origin else "*"
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Vary": "Origin",
            "Content-Type": "text/event-stream; charset=utf-8"
        }
        return Response(status_code=200, headers=headers)

    async def event_stream():
        public_base = build_public_base_url()

        logger.info(f"SSE endpoint streaming public base URL: {public_base}")

        # Dify expects SSE event named "endpoint" with the MCP JSON-RPC URL
        yield f"event: endpoint\n"
        yield f"data: {public_base}\n\n"

        # Yield immediately to ensure Dify gets the endpoint event
        await asyncio.sleep(0.1)

        # Keep the connection alive with periodic pings
        try:
            for _ in range(240):  # 240 * 25s = 100 minutes max
                yield f"event: ping\n"
                yield f"data: keepalive\n\n"
                await asyncio.sleep(25)
        except asyncio.CancelledError:
            # Client disconnected, exit gracefully
            pass

    origin = request.headers.get("origin")
    cors_origin = origin if origin else "*"
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Vary": "Origin",
    }

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers=headers,
    )


@app.get("/health")
async def health():
    """Detailed health check"""
    try:
        health_result = await _handle_health_check()
        return health_result
    except Exception as e:
        # Return basic health info even if database checks fail
        return {
            "status": "ok",
            "name": "hawk-allocation-mcp-server",
            "protocol": "jsonrpc-2.0",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "specialization": "Stage 1A Allocation Operations",
            "note": "Basic health check - database connectivity may be limited"
        }

@app.get("/ping")
async def ping():
    """Simple ping endpoint for connectivity testing"""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server": "hawk-allocation-mcp-server"
    }

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8010"))

    print(f"""
HAWK Stage 1A Allocation MCP Server
Port: {port}
Specialization: Stage 1A Operations Only
Features: Intent Detection | View Optimization | Database Writes
Ready for Dify integration
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
