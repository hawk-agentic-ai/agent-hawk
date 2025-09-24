"""
Unified Smart Backend - AI-First Hedge Fund Operations v5.0.0
Comprehensive FastAPI backend that handles ALL prompt types with intelligent data pre-fetching
Solves the 6-10 minute delay problem by separating data operations from AI analysis

Architecture:
User → Angular HAWK Agent → Smart Backend Intelligence Layer → Dify Analysis → Stream Response

Features:
- Universal prompt processing for all template categories
- Intelligent data pre-fetching with Redis caching
- Parallel Supabase query execution
- Dify AI integration with optimized context
- Sub-2 second data preparation target
"""

import asyncio
import json
try:
    import httpx  # Preferred async HTTP client for streaming
    HTTPX_AVAILABLE = True
except ModuleNotFoundError:  # Gracefully fall back when dependency is missing
    httpx = None
    HTTPX_AVAILABLE = False
    import requests  # requests ships with most environments and supports streaming
try:
    import redis  # Optional; backend still runs without local Redis
except ModuleNotFoundError:
    redis = None  # type: ignore
import time
import traceback
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Supabase integration
from supabase import create_client, Client

# Import our intelligent components
from payloads import FlexiblePromptRequest, HedgeInstructionPayload
from shared.business_logic import PromptIntelligenceEngine, PromptAnalysisResult, PromptIntent
from shared.data_extractor import SmartDataExtractor
from shared.supabase_client import DatabaseManager
from shared.cache_manager import (
    HEDGE_CACHE_STRATEGY, 
    get_hedge_cache_key, 
    get_cache_duration,
    OPTIMIZATION_STATS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# APPLICATION LIFECYCLE MANAGEMENT
# =============================================================================

# Global variables for dependency injection
db_manager: Optional[DatabaseManager] = None
supabase_client: Optional[Client] = None
redis_client: Optional[redis.Redis] = None
prompt_engine: Optional[PromptIntelligenceEngine] = None
data_extractor: Optional[SmartDataExtractor] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management"""
    global db_manager, supabase_client, redis_client, prompt_engine, data_extractor
    
    try:
        # Initialize shared database manager
        db_manager = DatabaseManager()
        supabase_client, redis_client = await db_manager.initialize_connections()
        
        # Initialize our intelligent modules
        prompt_engine = PromptIntelligenceEngine()
        data_extractor = SmartDataExtractor(supabase_client, redis_client)
        
        logger.info("Unified Smart Backend v5.0.0 initialized successfully")
        logger.info("Components: Prompt Intelligence + Smart Data Extractor + Redis Cache + Dify Integration")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        traceback.print_exc()
        yield
    finally:
        # Cleanup using shared database manager
        if db_manager:
            await db_manager.cleanup_connections()
        logger.info("Unified Smart Backend shutdown complete")

# Initialize FastAPI app with lifecycle management
app = FastAPI(
    title="Unified Smart Backend - AI-First Hedge Operations",
    description="Intelligent data pre-fetching for ALL prompt types with Redis cache integration",
    version="5.0.0",
    lifespan=lifespan
)

# CORS configuration supporting both HTTP/HTTPS and production domains
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [
    "http://localhost:4200",
    "http://127.0.0.1:4200", 
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost",
    "http://127.0.0.1",
    # HTTPS production origins will be added via environment variable
]

# Add wildcard as fallback for development
if not any("https://" in origin for origin in ALLOWED_ORIGINS):
    ALLOWED_ORIGINS.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # avoid '*' + credentials incompatibility  
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# =============================================================================
# CORE MODELS
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    components: Dict[str, Any]
    cache_stats: Optional[Dict[str, Any]] = None

class ProcessingMetadata(BaseModel):
    prompt_analysis_time_ms: float
    data_extraction_time_ms: float
    dify_processing_time_ms: float
    total_processing_time_ms: float
    cache_utilization: Dict[str, Any]
    tables_queried: List[str]
    records_fetched: int

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_dify_headers(agent_id: Optional[str] = None):
    """Select Dify API key based on agent_id and build headers"""
    selected_key_env = None
    if agent_id:
        # Map known agent IDs to specific env vars
        if agent_id == "allocation":
            selected_key_env = "DIFY_API_KEY_ALLOCATION"
        # Future agents can be added here

    api_key = None
    if selected_key_env:
        api_key = os.getenv(selected_key_env)
        if not api_key:
            logger.warning(f"Env {selected_key_env} not set; falling back to default DIFY_API_KEY")

    if not api_key:
        api_key = os.getenv("DIFY_API_KEY")
    if not api_key:
        api_key = "app-juJAFQ9a8QAghx5tACyTvqqG"
        logger.warning("DIFY_API_KEY not set; using legacy fallback key (please set env variable)")

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

def get_dify_api_url(agent_id: Optional[str] = None) -> str:
    """Resolve Dify API base URL per agent (supports per-agent overrides)."""
    base = None
    if agent_id == "allocation":
        base = os.getenv("DIFY_API_URL_ALLOCATION")
    if not base:
        base = os.getenv("DIFY_API_URL", "https://api.dify.ai/v1")
    if base.endswith('/'):
        base = base[:-1]
    return f"{base}/chat-messages"

async def stream_from_dify(dify_payload: Dict[str, Any], agent_id: Optional[str] = None) -> StreamingResponse:
    """Stream response from Dify API with graceful httpx fallback."""
    DIFY_API_URL = get_dify_api_url(agent_id)

    async def generate_stream():
        try:
            if HTTPX_AVAILABLE:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    async with client.stream(
                        "POST",
                        DIFY_API_URL,
                        json=dify_payload,
                        headers=get_dify_headers(agent_id)
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            yield f"data: {{\"error\": \"Dify API error: {error_text.decode()}\"}}\n\n"
                            return

                        async for chunk in response.aiter_text():
                            if chunk.strip():
                                yield f"data: {chunk}\n\n"
            else:
                def request_stream():
                    try:
                        with requests.post(
                            DIFY_API_URL,
                            json=dify_payload,
                            headers=get_dify_headers(agent_id),
                            stream=True,
                            timeout=300
                        ) as response:
                            if response.status_code != 200:
                                error_text = response.text
                                yield f"data: {{\"error\": \"Dify API error: {error_text}\"}}\n\n"
                                return

                            for line in response.iter_lines(decode_unicode=True):
                                if not line:
                                    continue
                                if not line.startswith("data:"):
                                    line = f"data: {line}"
                                yield f"{line}\n\n"
                    except Exception as exc:
                        yield f"data: {{\"error\": \"Streaming error: {str(exc)}\"}}\n\n"

                stream_iter = request_stream()

                def next_chunk(iterator):
                    try:
                        return next(iterator)
                    except StopIteration:
                        return None

                while True:
                    chunk = await asyncio.to_thread(next_chunk, stream_iter)
                    if chunk is None:
                        break
                    yield chunk

        except Exception as e:
            yield f"data: {{\"error\": \"Streaming error: {str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

def build_optimized_context(extracted_data: Dict[str, Any], analysis_result: PromptAnalysisResult) -> str:
    """Build comprehensive context for Dify with detailed data - up to 100,000 characters"""
    
    # Get extraction metadata
    metadata = extracted_data.get("_extraction_metadata", {})
    
    context_parts = []
    
    # Detailed analysis summary
    context_parts.append("=" * 60)
    context_parts.append("SMART BACKEND ANALYSIS REPORT")
    context_parts.append("=" * 60)
    context_parts.append(f"Intent: {analysis_result.intent.value}")
    context_parts.append(f"Confidence: {analysis_result.confidence:.1f}%")
    context_parts.append(f"Data Scope: {analysis_result.data_scope}")
    context_parts.append(f"Instruction Type: {analysis_result.instruction_type or 'General'}")
    context_parts.append("")
    
    # Data extraction performance
    context_parts.append("DATA EXTRACTION PERFORMANCE:")
    context_parts.append(f"- Tables Fetched: {metadata.get('tables_fetched', 0)}")
    context_parts.append(f"- Total Records: {metadata.get('total_records', 0)}")
    context_parts.append(f"- Cache Hit Rate: {metadata.get('cache_hit_rate', '0%')}")
    context_parts.append(f"- Extraction Time: {metadata.get('extraction_time_ms', 0)}ms")
    context_parts.append(f"- Redis Available: {metadata.get('redis_available', False)}")
    context_parts.append("")
    
    # Extracted parameters
    if analysis_result.extracted_params:
        context_parts.append("EXTRACTED PARAMETERS:")
        for key, value in analysis_result.extracted_params.items():
            if value:
                context_parts.append(f"- {key}: {value}")
        context_parts.append("")
    
    # Detailed data from each table
    context_parts.append("COMPLETE DATA CONTEXT:")
    context_parts.append("-" * 40)
    
    for table, data in extracted_data.items():
        if table.startswith("_"):
            continue  # Skip metadata
            
        if isinstance(data, list):
            context_parts.append(f"\n{table.upper()} TABLE ({len(data)} records):")
            context_parts.append("-" * 30)
            
            if len(data) == 0:
                context_parts.append("No records found")
            else:
                # Show detailed records for key tables
                if table in ["entity_master", "position_nav_master", "allocation_engine", "hedge_business_events"]:
                    for i, record in enumerate(data[:10]):  # Show first 10 records in detail
                        context_parts.append(f"Record {i+1}:")
                        for key, value in record.items():
                            if value is not None and value != "":
                                context_parts.append(f"  {key}: {value}")
                        context_parts.append("")
                    
                    if len(data) > 10:
                        context_parts.append(f"... and {len(data)-10} more records")
                        context_parts.append("")
                
                else:
                    # For other tables, show first 5 records
                    for i, record in enumerate(data[:5]):
                        context_parts.append(f"Record {i+1}: {dict(list(record.items())[:5])}")  # Show first 5 fields
                    
                    if len(data) > 5:
                        context_parts.append(f"... and {len(data)-5} more records")
                    context_parts.append("")
    
    # Add processed entity groups if available
    if "_processed_entity_groups" in extracted_data:
        entity_groups = extracted_data["_processed_entity_groups"]
        context_parts.append(f"\nPROCESSED ENTITY ANALYSIS ({len(entity_groups)} entities):")
        context_parts.append("-" * 30)
        
        for group in entity_groups:
            context_parts.append(f"\nEntity ID: {group['entity_id']}")
            context_parts.append(f"Entity Name: {group['entity_name']}")
            context_parts.append(f"Entity Type: {group['entity_type']}")
            context_parts.append(f"Exposure Currency: {group['exposure_currency']}")
            
            context_parts.append("Positions:")
            for pos in group.get("positions", []):
                context_parts.append(f"  NAV Type: {pos.get('nav_type', 'N/A')}")
                context_parts.append(f"  Current Position: {pos.get('current_position', 'N/A')}")
                
                hedging_state = pos.get("hedging_state", {})
                context_parts.append(f"  Hedging Status: {hedging_state.get('hedging_status', 'N/A')}")
                context_parts.append(f"  Already Hedged: {hedging_state.get('already_hedged_amount', 'N/A')}")
                context_parts.append(f"  Hedge Utilization: {hedging_state.get('hedge_utilization_pct', 'N/A')}%")
                context_parts.append("")
    
    # Business logic instructions
    context_parts.append("=" * 60)
    context_parts.append("DIFY PROCESSING INSTRUCTIONS")
    context_parts.append("=" * 60)
    context_parts.append("🎯 FOCUS: Apply hedge fund business logic to the complete data above")
    context_parts.append("📊 DATA: All required data has been pre-fetched and provided above")
    context_parts.append("⚡ SPEED: No additional data queries needed - analyze immediately")
    context_parts.append("🔍 SCOPE: Use ALL provided data for comprehensive analysis")
    context_parts.append("")
    context_parts.append("KEY FORMULAS TO APPLY:")
    context_parts.append("- Unhedged Position = SFX Position - CAR Amount + Manual Overlay - (SFX Position × Buffer%) - Hedged Position")
    context_parts.append("- Hedge Effectiveness = (Change in Hedge Value / Change in Hedged Item Value) × 100")
    context_parts.append("- Target Effectiveness Range: 80% - 125%")
    context_parts.append("")
    context_parts.append("PROVIDE SPECIFIC, ACTIONABLE RECOMMENDATIONS WITH ACTUAL VALUES FROM THE DATA ABOVE.")
    
    # Join all parts
    context = "\n".join(context_parts)
    
    # Ensure we don't exceed 100,000 character limit
    if len(context) > 99000:  # Leave some margin
        context = context[:99000] + "\n\n[CONTEXT TRUNCATED TO FIT LIMIT - ANALYSIS BASED ON AVAILABLE DATA]"
    
    return context

# =============================================================================
# MAIN ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check with component status"""
    
    components = {
        "supabase": "connected" if supabase_client else "disconnected",
        "redis": "connected" if redis_client else "disconnected", 
        "prompt_engine": "initialized" if prompt_engine else "not_initialized",
        "data_extractor": "initialized" if data_extractor else "not_initialized"
    }
    
    cache_stats = None
    if data_extractor:
        cache_stats = data_extractor.get_cache_stats()
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="5.0.0",
        components=components,
        cache_stats=cache_stats
    )

# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.get("/cache/stats")
async def get_cache_stats():
    """Get detailed cache performance statistics"""
    if not data_extractor:
        raise HTTPException(status_code=503, detail="Data extractor not initialized")
    
    stats = data_extractor.get_cache_stats()
    
    # Add Redis info if available
    if redis_client:
        try:
            redis_info = redis_client.info()
            stats["redis_memory_usage"] = redis_info.get("used_memory_human", "N/A")
            stats["redis_keys_count"] = redis_client.dbsize()
            stats["redis_hit_rate"] = redis_info.get("keyspace_hit_rate", "N/A")
        except Exception as e:
            stats["redis_error"] = str(e)
    
    return stats

@app.post("/cache/clear/{currency}")
async def clear_cache_for_currency(currency: str):
    """Clear cache for specific currency"""
    if not data_extractor:
        raise HTTPException(status_code=503, detail="Data extractor not initialized")
    
    cleared_count = data_extractor.clear_cache_for_currency(currency.upper())
    
    return {
        "message": f"Cache cleared for currency {currency.upper()}",
        "keys_cleared": cleared_count,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/prompt-analysis/test")
async def test_prompt_analysis(prompt: str, category: Optional[str] = None):
    """Test prompt analysis capabilities"""
    if not prompt_engine:
        raise HTTPException(status_code=503, detail="Prompt engine not initialized")
    
    analysis_result = prompt_engine.analyze_prompt(prompt, category)
    
    return {
        "prompt": prompt,
        "category": category,
        "analysis": {
            "intent": analysis_result.intent.value,
            "confidence": analysis_result.confidence,
            "data_scope": analysis_result.data_scope,
            "instruction_type": analysis_result.instruction_type,
            "required_tables": analysis_result.required_tables,
            "extracted_params": analysis_result.extracted_params
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/system/status")
async def system_status():
    """Detailed system status for monitoring"""
    
    status = {
        "application": "Unified Smart Backend",
        "version": "5.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time(),  # Approximate since startup
        "components": {}
    }
    
    # Test Supabase connection
    try:
        if supabase_client:
            result = supabase_client.table("entity_master").select("count", count="exact").limit(1).execute()
            status["components"]["supabase"] = {
                "status": "healthy",
                "total_entities": result.count if hasattr(result, 'count') else "unknown"
            }
        else:
            status["components"]["supabase"] = {"status": "not_initialized"}
    except Exception as e:
        status["components"]["supabase"] = {"status": "error", "message": str(e)}
    
    # Test Redis connection
    try:
        if redis_client:
            redis_client.ping()
            status["components"]["redis"] = {
                "status": "healthy",
                "keys_count": redis_client.dbsize(),
                "memory_usage": redis_client.info().get("used_memory_human", "N/A")
            }
        else:
            status["components"]["redis"] = {"status": "not_initialized"}
    except Exception as e:
        status["components"]["redis"] = {"status": "error", "message": str(e)}
    
    # Component status
    status["components"]["prompt_engine"] = {
        "status": "initialized" if prompt_engine else "not_initialized"
    }
    
    status["components"]["data_extractor"] = {
        "status": "initialized" if data_extractor else "not_initialized"
    }
    
    if data_extractor:
        status["components"]["data_extractor"]["cache_stats"] = data_extractor.get_cache_stats()
    
    return status

@app.post("/cache/clear")
async def clear_cache():
    """Clear all cache data"""
    try:
        if redis_client:
            redis_client.flushdb()
            return {"message": "Redis cache cleared successfully"}
        elif data_extractor and hasattr(data_extractor, 'memory_cache') and data_extractor.memory_cache:
            data_extractor.memory_cache.clear()
            return {"message": "Memory cache cleared successfully"}
        else:
            return {"message": "No cache to clear"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")

# =============================================================================
# MAIN UNIVERSAL ENDPOINT
# =============================================================================

@app.post("/hawk-agent/process-prompt")
async def universal_prompt_processor(request: FlexiblePromptRequest):
    """
    Universal endpoint for ALL prompt types - the core of our Smart Backend
    
    Flow: Prompt Analysis → Smart Data Extraction → Optimized Dify Context → Stream Response
    """
    start_time = time.time()
    
    if not all([supabase_client, prompt_engine, data_extractor]):
        raise HTTPException(status_code=503, detail="Backend components not initialized")
    
    try:
        # Mode selection: default to MCP-first (Dify orchestrates MCP tools)
        mcp_mode = os.getenv("MCP_ORCHESTRATION_MODE", "true").lower() in ("1", "true", "yes")
        logger.info(f"/process-prompt mode: {'MCP' if mcp_mode else 'SMART_BACKEND'}")

        # Always log the incoming prompt; do not alter UI strings
        logger.info(f"DEBUG - User prompt: {request.user_prompt}")

        if mcp_mode:
            # Dify will call MCP tools to build context. We simply forward the prompt.
            dify_payload = {
                "inputs": {
                    "user_prompt": request.user_prompt,
                    "template_category": request.template_category or "general",
                    # Do NOT send optimized_context or extracted data here; MCP will handle it.
                },
                "query": request.user_prompt,
                "response_mode": "streaming",
                "user": f"unified_backend_{int(time.time())}"
            }
            agent = getattr(request, "agent_id", None)
            logger.info(f"Routing to Dify (MCP-first) agent_id={agent} url={get_dify_api_url(agent)}")
            return await stream_from_dify(dify_payload, agent)

        # Legacy SMART_BACKEND path (fallback/testing)
        # Step 1: Intelligent Prompt Analysis
        prompt_analysis_start = time.time()
        user_input_fields = {}
        if request.currency:
            user_input_fields["currency"] = request.currency
        if request.entity_id:
            user_input_fields["entity_id"] = request.entity_id
        if request.nav_type:
            user_input_fields["nav_type"] = request.nav_type
        if request.amount:
            user_input_fields["amount"] = request.amount
        if request.time_period:
            user_input_fields["time_period"] = request.time_period
        if request.portfolio:
            user_input_fields["portfolio"] = request.portfolio

        analysis_result = prompt_engine.analyze_prompt_hybrid(
            request.user_prompt,
            request.template_category,
            user_input_fields
        )
        prompt_analysis_time = (time.time() - prompt_analysis_start) * 1000

        # Step 2: Smart Data Extraction (cache can be enabled if desired)
        data_extraction_start = time.time()
        use_cache_strategy = True
        extracted_data = await data_extractor.extract_data_for_prompt(
            analysis_result,
            use_cache=use_cache_strategy
        )
        data_extraction_time = (time.time() - data_extraction_start) * 1000

        # Step 3: Build Optimized Context for Dify
        optimized_context = build_optimized_context(extracted_data, analysis_result)

        # Step 4: Prepare Dify Payload (legacy)
        dify_payload = {
            "inputs": {
                "user_prompt": request.user_prompt,
                "template_category": request.template_category or "general",
                "optimized_context": optimized_context,
                "extracted_params": json.dumps(analysis_result.extracted_params),
            },
            "query": request.user_prompt,
            "response_mode": "streaming",
            "user": f"unified_backend_{int(time.time())}"
        }

        # Optional: store processing metadata in Redis
        if redis_client:
            try:
                processing_metadata = {
                    "prompt_analysis_time_ms": round(prompt_analysis_time, 2),
                    "data_extraction_time_ms": round(data_extraction_time, 2),
                    "cache_stats": data_extractor.get_cache_stats(),
                    "intent": analysis_result.intent.value,
                    "confidence": analysis_result.confidence,
                    "tables_fetched": extracted_data.get("_extraction_metadata", {}).get("tables_fetched", 0),
                    "total_records": extracted_data.get("_extraction_metadata", {}).get("total_records", 0)
                }
                metadata_key = f"processing_metadata:{int(time.time())}"
                redis_client.setex(metadata_key, 3600, json.dumps(processing_metadata))
            except Exception:
                pass

        agent = getattr(request, "agent_id", None)
        logger.info(f"Routing to Dify (legacy path) agent_id={agent} url={get_dify_api_url(agent)}")
        return await stream_from_dify(dify_payload, agent)
        
    except Exception as e:
        logger.error(f"Universal processor error: {e}")
        traceback.print_exc()
        
        error_response = {
            "error": "Processing failed",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": round((time.time() - start_time) * 1000, 2)
        }
        
        return JSONResponse(content=error_response, status_code=500)

# =============================================================================
# LEGACY INSTRUCTION ENDPOINTS (BACKWARD COMPATIBILITY)
# =============================================================================

# =============================================================================
# LEGACY COMPATIBILITY ENDPOINTS
# =============================================================================

@app.post("/comprehensive-hedge-data")
async def legacy_comprehensive_data(request: FlexiblePromptRequest):
    """Legacy endpoint for backward compatibility - redirects to universal processor"""
    return await universal_prompt_processor(request)

@app.post("/dify/process")  
async def legacy_dify_process(request: FlexiblePromptRequest):
    """Legacy Dify processing endpoint - redirects to universal processor"""
    return await universal_prompt_processor(request)

@app.post("/hedge-ai/instruction")
async def process_hedge_instruction(request: HedgeInstructionPayload):
    """
    Legacy instruction endpoint for backward compatibility
    Converts to FlexiblePromptRequest and processes via universal endpoint
    """
    
    # Convert legacy request to flexible format
    flexible_request = FlexiblePromptRequest(
        user_prompt=f"Process {request.instruction_type or 'hedge'} instruction for {request.exposure_currency or 'currency'} {request.hedge_amount_order or 'amount'}",
        template_category="hedge_accounting",
        currency=request.exposure_currency,
        amount=request.hedge_amount_order,
        instruction_type=request.instruction_type,
        order_id=request.order_id,
        nav_type=request.nav_type,
        hedge_method=request.hedge_method,
        reference_hedge_id=request.reference_hedge_id
    )
    
    # Process via universal endpoint
    return await universal_prompt_processor(flexible_request)

# =============================================================================
# SYSTEM STATUS AND MANAGEMENT ENDPOINTS  
# =============================================================================

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Unified Smart Backend v5.0.0")
    print("Features: Universal Prompt Processing + Smart Data Extraction + Redis Cache + Dify Integration")
    print("Goal: Sub-2 second data preparation for ALL prompt types")
    print("Endpoints: /hawk-agent/process-prompt (main), /health, /cache/stats, /system/status")
    
    uvicorn.run(
        "unified_smart_backend:app",
        host="0.0.0.0",
        port=8004,  # New port for unified backend
        reload=False,
        log_level="info"
    )
