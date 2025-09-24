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
import httpx
import redis
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
from prompt_intelligence_engine import PromptIntelligenceEngine, PromptAnalysisResult, PromptIntent
from smart_data_extractor import SmartDataExtractor
from hedge_management_cache_config import (
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
supabase_client: Optional[Client] = None
redis_client: Optional[redis.Redis] = None
prompt_engine: Optional[PromptIntelligenceEngine] = None
data_extractor: Optional[SmartDataExtractor] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management"""
    global supabase_client, redis_client, prompt_engine, data_extractor
    
    try:
        # Initialize Supabase client
        SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ladviaautlfvpxuadqrb.supabase.co")
        SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes")
        
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized")
        
        # Initialize Redis client
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_client.ping()
            logger.info("Redis client connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
            redis_client = None
        
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
        # Cleanup
        if redis_client:
            redis_client.close()
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

def get_dify_headers():
    """Get Dify API headers"""
    DIFY_API_KEY = os.getenv("DIFY_API_KEY", "app-juJAFQ9a8QAghx5tACyTvqqG")
    return {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

async def stream_from_dify(dify_payload: Dict[str, Any]) -> StreamingResponse:
    """Stream response from Dify API"""
    DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
    
    async def generate_stream():
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    DIFY_API_URL,
                    json=dify_payload,
                    headers=get_dify_headers()
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"data: {{\"error\": \"Dify API error: {error_text.decode()}\"}}\n\n"
                        return
                    
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            yield f"data: {chunk}\n\n"
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
        # Step 1: Intelligent Prompt Analysis
        prompt_analysis_start = time.time()
        # DEBUG: Log incoming prompt
        logger.info(f"DEBUG - User prompt: {request.user_prompt}")
        
        # Collect user input fields from request for hybrid analysis
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
        
        # Use HYBRID analysis method (user fields + regex + instruction type)
        analysis_result = prompt_engine.analyze_prompt_hybrid(
            request.user_prompt, 
            request.template_category,
            user_input_fields
        )
        
        # DEBUG: Log hybrid extracted parameters
        logger.info(f"DEBUG - Hybrid extracted params: {analysis_result.extracted_params}")
        
        # Legacy overrides for backward compatibility
        if request.order_id:
            analysis_result.extracted_params["order_id"] = request.order_id
        if request.instruction_type:
            analysis_result.instruction_type = request.instruction_type
        
        prompt_analysis_time = (time.time() - prompt_analysis_start) * 1000
        
        # Step 2: Smart Data Extraction with Advanced Freshness Controls
        data_extraction_start = time.time()
        
        # Apply data freshness logic
        if request.force_fresh:
            logger.info(f"🔄 Force fresh data requested for {analysis_result.extracted_params.get('currency', 'query')}")
        
        # Cache disabled - Dify handles caching internally
        # Application-level cache is disabled as Dify manages its own caching
        use_cache_strategy = False  # Always disabled - Dify handles caching
        logger.info(f"📊 Cache strategy: DISABLED (Dify manages caching) - use_cache={use_cache_strategy}")
        
        extracted_data = await data_extractor.extract_data_for_prompt(
            analysis_result,
            use_cache=use_cache_strategy
        )
        data_extraction_time = (time.time() - data_extraction_start) * 1000
        
        # Step 3: Build Optimized Context for Dify
        optimized_context = build_optimized_context(extracted_data, analysis_result)
        
        # Step 4: Prepare Dify Payload
        # Align with optimized prompt v2: pass optimized_context in inputs, keep query as user's prompt
        dify_payload = {
            "inputs": {
                "user_prompt": request.user_prompt,
                "template_category": request.template_category or "general",
                "optimized_context": optimized_context,
                "extracted_params": json.dumps(analysis_result.extracted_params),
            },
            # Keep query minimal so the LLM sees the actual user instruction as the message
            "query": request.user_prompt,
            "response_mode": "streaming",
            "user": f"unified_backend_{int(time.time())}"
        }
        
        # Step 5: Stream Response from Dify
        dify_start = time.time()
        
        # Add metadata header for performance tracking
        processing_metadata = {
            "prompt_analysis_time_ms": round(prompt_analysis_time, 2),
            "data_extraction_time_ms": round(data_extraction_time, 2),
            "cache_stats": data_extractor.get_cache_stats(),
            "intent": analysis_result.intent.value,
            "confidence": analysis_result.confidence,
            "tables_fetched": extracted_data.get("_extraction_metadata", {}).get("tables_fetched", 0),
            "total_records": extracted_data.get("_extraction_metadata", {}).get("total_records", 0)
        }
        
        # Store metadata for potential logging
        if redis_client:
            try:
                metadata_key = f"processing_metadata:{int(time.time())}"
                redis_client.setex(metadata_key, 3600, json.dumps(processing_metadata))  # 1 hour
            except Exception:
                pass  # Non-critical
        
        # Return streaming response from Dify
        return await stream_from_dify(dify_payload)
        
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
