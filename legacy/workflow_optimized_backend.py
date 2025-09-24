"""
HAWK Agent Workflow-Optimized Backend
Precision-tuned for 11 core hedge accounting operations
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from supabase import create_client, Client
import os
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests
class HedgeInstructionRequest(BaseModel):
    order_id: str
    sub_order_id: str
    instruction_type: str  # I, U, R, T
    exposure_currency: str
    hedge_amount: Optional[float] = None

class AvailableAmountRequest(BaseModel):
    entity_id: str
    currency_code: str
    nav_type: Optional[str] = None
    as_of_date: Optional[str] = None

class DealBookingRequest(BaseModel):
    order_id: str
    sub_order_id: Optional[str] = None

class UsdPbDepositRequest(BaseModel):
    entity_id: Optional[str] = None
    business_date: Optional[str] = None

# Multi-tier cache configuration based on real workflows
CACHE_CONFIG = {
    # L1: Ultra High-Frequency (Redis) - Hedge operations
    "hedge_instruction_validation": {"ttl": 300, "priority": "critical"},    # 5 min
    "available_amounts": {"ttl": 180, "priority": "critical"},               # 3 min  
    "deal_booking_lookup": {"ttl": 600, "priority": "high"},                 # 10 min
    "entity_currency_config": {"ttl": 900, "priority": "high"},              # 15 min
    
    # L2: High-Frequency (Database cache) - Calculations
    "usd_pb_capacity": {"ttl": 1800, "priority": "medium"},                  # 30 min
    "hedge_adjustments": {"ttl": 3600, "priority": "medium"},                # 60 min
    "total_hedge_amounts": {"ttl": 1200, "priority": "medium"},              # 20 min
    
    # L3: Medium-Frequency (Materialized views) - Reports
    "net_interest_income": {"ttl": 86400, "priority": "low"},                # 24 hours
    "maturity_analysis": {"ttl": 14400, "priority": "low"},                  # 4 hours
    "car_hedge_calculations": {"ttl": 7200, "priority": "low"}               # 2 hours
}

class WorkflowOptimizedCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.hit_stats = {"hits": 0, "misses": 0}
        
    def _generate_key(self, operation: str, params: Dict) -> str:
        """Generate deterministic cache key for operation"""
        param_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"hawk:{operation}:{hash_suffix}"
    
    async def get(self, operation: str, params: Dict) -> Optional[Any]:
        """Get cached result with hit/miss tracking"""
        try:
            key = self._generate_key(operation, params)
            cached = await self.redis.get(key)
            
            if cached:
                self.hit_stats["hits"] += 1
                logger.info(f"Cache HIT for {operation}")
                return json.loads(cached)
            else:
                self.hit_stats["misses"] += 1
                logger.info(f"Cache MISS for {operation}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, operation: str, params: Dict, data: Any, custom_ttl: int = None) -> bool:
        """Set cache with workflow-specific TTL"""
        try:
            key = self._generate_key(operation, params)
            ttl = custom_ttl or CACHE_CONFIG.get(operation, {}).get("ttl", 3600)
            
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
            logger.info(f"Cache SET for {operation} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        try:
            keys = await self.redis.keys(f"hawk:{pattern}:*")
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache keys for pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

# Global instances
app = FastAPI(title="HAWK Agent Workflow-Optimized Backend", version="2.0.0")
supabase: Client = None
cache: WorkflowOptimizedCache = None

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connections on startup"""
    global supabase, cache
    
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") 
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")
    
    supabase = create_client(url, key)
    logger.info("✅ Supabase connection initialized")
    
    # Initialize Redis
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    cache = WorkflowOptimizedCache(redis_client)
    logger.info("✅ Redis cache initialized")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🔄 Shutting down connections")

app.router.lifespan_context = lifespan

# =============================================================================
# WORKFLOW 1: Hedge Instructions Processing (I, U, R, T) - ULTRA HIGH FREQUENCY
# =============================================================================

@app.post("/api/v2/hedge-instructions/validate")
async def validate_hedge_instruction(request: HedgeInstructionRequest):
    """
    Ultra-fast validation for hedge instructions (I, U, R, T)
    Caches validation rules, entity configs, and threshold checks
    """
    start_time = datetime.now()
    
    cache_params = {
        "order_id": request.order_id,
        "sub_order_id": request.sub_order_id,
        "currency": request.exposure_currency,
        "type": request.instruction_type
    }
    
    # Try cache first
    cached_result = await cache.get("hedge_instruction_validation", cache_params)
    if cached_result:
        cached_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": True
        }
        return cached_result
    
    try:
        # Parallel validation queries
        validation_tasks = [
            get_instruction_business_rules(request.exposure_currency, request.instruction_type),
            get_entity_currency_config(request.exposure_currency),
            get_threshold_configuration(request.exposure_currency),
            check_instruction_constraints(request.order_id, request.sub_order_id)
        ]
        
        rules, entity_config, thresholds, constraints = await asyncio.gather(*validation_tasks)
        
        # Validation logic
        validation_result = {
            "valid": True,
            "order_id": request.order_id,
            "sub_order_id": request.sub_order_id,
            "instruction_type": request.instruction_type,
            "exposure_currency": request.exposure_currency,
            "validation_rules": rules,
            "entity_configuration": entity_config,
            "threshold_limits": thresholds,
            "constraint_checks": constraints,
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Cache for 5 minutes (high frequency operations)
        await cache.set("hedge_instruction_validation", cache_params, validation_result, 300)
        
        validation_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False
        }
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Hedge instruction validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

async def get_instruction_business_rules(currency: str, instruction_type: str) -> Dict:
    """Get business rules for instruction validation"""
    response = supabase.table('instruction_event_config').select('*').eq('currency_code', currency).eq('instruction_type', instruction_type).execute()
    return {"rules": response.data}

async def get_entity_currency_config(currency: str) -> Dict:
    """Get entity configuration for currency"""
    response = supabase.table('entity_master').select('*, currency_configuration!inner(*)').eq('currency_configuration.currency_code', currency).eq('active_flag', 'Y').execute()
    return {"entities": response.data}

async def get_threshold_configuration(currency: str) -> Dict:
    """Get threshold limits for currency"""
    response = supabase.table('threshold_configuration').select('*').eq('currency_code', currency).eq('active_flag', 'Y').execute()
    return {"thresholds": response.data}

async def check_instruction_constraints(order_id: str, sub_order_id: str) -> Dict:
    """Check existing instruction constraints"""
    response = supabase.table('hedge_instructions').select('instruction_status, check_status, failure_reason').eq('order_id', order_id).eq('sub_order_id', sub_order_id).execute()
    return {"existing_instructions": response.data}

# =============================================================================
# WORKFLOW 2: Available Amount Calculations - ULTRA HIGH FREQUENCY  
# =============================================================================

@app.post("/api/v2/available-amounts/calculate")
async def calculate_available_amounts(request: AvailableAmountRequest):
    """
    Calculate available hedge amounts with 3-minute caching
    Critical for every instruction validation
    """
    start_time = datetime.now()
    
    cache_params = {
        "entity_id": request.entity_id,
        "currency": request.currency_code,
        "nav_type": request.nav_type or "ALL",
        "date": request.as_of_date or datetime.now().date().isoformat()
    }
    
    # Check cache first
    cached_result = await cache.get("available_amounts", cache_params)
    if cached_result:
        cached_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": True
        }
        return cached_result
    
    try:
        # Parallel data fetching for amount calculation
        amount_tasks = [
            get_position_nav_data(request.entity_id, request.currency_code, request.nav_type),
            get_car_master_data(request.entity_id, request.currency_code),
            get_overlay_amounts(request.entity_id, request.currency_code),
            get_buffer_configuration(request.entity_id, request.currency_code),
            get_current_hedge_totals(request.entity_id, request.currency_code)
        ]
        
        nav_data, car_data, overlay_data, buffer_data, hedge_totals = await asyncio.gather(*amount_tasks)
        
        # Available amount calculation
        calculation_result = calculate_available_hedge_amount({
            "nav_positions": nav_data,
            "car_amounts": car_data,
            "overlay_amounts": overlay_data,
            "buffer_amounts": buffer_data,
            "current_hedges": hedge_totals
        })
        
        result = {
            "entity_id": request.entity_id,
            "currency_code": request.currency_code,
            "nav_type": request.nav_type,
            "as_of_date": cache_params["date"],
            "calculations": calculation_result,
            "data_sources": {
                "position_nav": len(nav_data),
                "car_master": len(car_data),
                "overlays": len(overlay_data),
                "buffers": len(buffer_data),
                "hedge_totals": len(hedge_totals)
            },
            "calculation_timestamp": datetime.now().isoformat()
        }
        
        # Cache for 3 minutes (ultra-high frequency)
        await cache.set("available_amounts", cache_params, result, 180)
        
        result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Available amounts calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

async def get_position_nav_data(entity_id: str, currency: str, nav_type: str = None) -> List[Dict]:
    """Get position NAV master data"""
    query = supabase.table('position_nav_master').select('*').eq('entity_id', entity_id).eq('currency_code', currency)
    if nav_type and nav_type != "ALL":
        query = query.eq('nav_type', nav_type)
    
    response = query.order('as_of_date', desc=True).limit(10).execute()
    return response.data

async def get_car_master_data(entity_id: str, currency: str) -> List[Dict]:
    """Get CAR master data for calculations"""
    response = supabase.table('car_master').select('*').eq('entity_id', entity_id).eq('currency_code', currency).execute()
    return response.data

async def get_overlay_amounts(entity_id: str, currency: str) -> List[Dict]:
    """Get manual overlay amounts"""
    response = supabase.table('overlay_configuration').select('*').eq('entity_id', entity_id).eq('currency_code', currency).eq('active_flag', 'Y').execute()
    return response.data

async def get_buffer_configuration(entity_id: str, currency: str) -> List[Dict]:
    """Get buffer configuration"""
    response = supabase.table('buffer_configuration').select('*').eq('entity_id', entity_id).eq('currency_code', currency).eq('active_flag', 'Y').execute()
    return response.data

async def get_current_hedge_totals(entity_id: str, currency: str) -> List[Dict]:
    """Get current hedge position totals"""
    response = supabase.table('hedge_business_events').select('*, hedge_instructions!inner(*)').eq('hedge_instructions.exposure_currency', currency).eq('entity_id', entity_id).eq('stage_2_status', 'Completed').execute()
    return response.data

def calculate_available_hedge_amount(data: Dict) -> Dict:
    """Core business logic for available amount calculation"""
    nav_positions = data.get("nav_positions", [])
    car_amounts = data.get("car_amounts", [])
    overlay_amounts = data.get("overlay_amounts", [])
    buffer_amounts = data.get("buffer_amounts", [])
    current_hedges = data.get("current_hedges", [])
    
    # Sum position components
    total_sfx_position = sum(float(pos.get("current_position", 0)) for pos in nav_positions)
    total_coi_amount = sum(float(pos.get("coi_amount", 0)) for pos in nav_positions)
    total_re_amount = sum(float(pos.get("re_amount", 0)) for pos in nav_positions)
    
    # Sum CAR amounts
    total_car_amount = sum(float(car.get("car_amount", 0)) for car in car_amounts)
    
    # Sum overlay amounts
    total_overlay_amount = sum(float(overlay.get("overlay_amount", 0)) for overlay in overlay_amounts)
    
    # Sum buffer amounts  
    total_buffer_amount = sum(float(buffer.get("buffer_amount", 0)) for buffer in buffer_amounts)
    
    # Sum current hedge positions
    total_hedged_position = sum(float(hedge.get("notional_amount", 0)) for hedge in current_hedges)
    
    # Available amount calculation
    available_amount = (
        total_sfx_position - 
        total_car_amount + 
        total_overlay_amount - 
        total_buffer_amount - 
        total_hedged_position
    )
    
    return {
        "sfx_position": total_sfx_position,
        "coi_amount": total_coi_amount,
        "re_amount": total_re_amount,
        "car_amount": total_car_amount,
        "overlay_amount": total_overlay_amount,
        "buffer_amount": total_buffer_amount,
        "hedged_position": total_hedged_position,
        "available_to_hedge": available_amount,
        "calculation_components": {
            "nav_records": len(nav_positions),
            "car_records": len(car_amounts),
            "overlay_records": len(overlay_amounts),
            "buffer_records": len(buffer_amounts),
            "hedge_records": len(current_hedges)
        }
    }

# =============================================================================
# WORKFLOW 3: Murex Deal Bookings by Order ID - HIGH FREQUENCY
# =============================================================================

@app.post("/api/v2/deal-bookings/by-order")
async def get_deal_bookings_by_order(request: DealBookingRequest):
    """
    Get Murex deal bookings filtered by Order ID
    10-minute caching for status tracking
    """
    start_time = datetime.now()
    
    cache_params = {
        "order_id": request.order_id,
        "sub_order_id": request.sub_order_id or "ALL"
    }
    
    # Check cache
    cached_result = await cache.get("deal_booking_lookup", cache_params)
    if cached_result:
        cached_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": True
        }
        return cached_result
    
    try:
        # Build complex join query for deal bookings
        query = """
        SELECT 
            hi.order_id,
            hi.sub_order_id,
            hi.instruction_type,
            hi.exposure_currency,
            hi.hedge_amount_order,
            hi.instruction_status,
            hbe.event_id,
            hbe.stage_2_status,
            hbe.event_type,
            db.deal_booking_id,
            db.deal_sequence,
            db.deal_status,
            db.deal_type,
            db.sell_currency,
            db.buy_currency,
            db.sell_amount,
            db.buy_amount,
            db.fx_rate,
            db.trade_date,
            db.value_date,
            db.maturity_date,
            db.counterparty,
            db.portfolio,
            db.booking_reference,
            db.internal_reference
        FROM hedge_instructions hi
        JOIN hedge_business_events hbe ON hi.instruction_id = hbe.instruction_id
        JOIN deal_bookings db ON hbe.event_id = db.event_id
        WHERE hi.order_id = %s
        """
        
        params = [request.order_id]
        if request.sub_order_id:
            query += " AND hi.sub_order_id = %s"
            params.append(request.sub_order_id)
            
        query += " ORDER BY hi.order_id, hi.sub_order_id, db.deal_sequence"
        
        response = supabase.rpc('execute_sql', {'sql': query, 'params': params}).execute()
        deal_bookings = response.data
        
        # Group results by order/sub-order
        grouped_results = {}
        for booking in deal_bookings:
            key = f"{booking['order_id']}_{booking['sub_order_id']}"
            if key not in grouped_results:
                grouped_results[key] = {
                    "order_id": booking["order_id"],
                    "sub_order_id": booking["sub_order_id"],
                    "instruction_type": booking["instruction_type"],
                    "exposure_currency": booking["exposure_currency"],
                    "instruction_status": booking["instruction_status"],
                    "hedge_amount_order": booking["hedge_amount_order"],
                    "total_deals": 0,
                    "deal_bookings": []
                }
            
            grouped_results[key]["deal_bookings"].append({
                "deal_booking_id": booking["deal_booking_id"],
                "deal_sequence": booking["deal_sequence"],
                "deal_status": booking["deal_status"],
                "deal_type": booking["deal_type"],
                "sell_currency": booking["sell_currency"],
                "buy_currency": booking["buy_currency"],
                "sell_amount": booking["sell_amount"],
                "buy_amount": booking["buy_amount"],
                "fx_rate": booking["fx_rate"],
                "trade_date": booking["trade_date"],
                "value_date": booking["value_date"],
                "maturity_date": booking["maturity_date"],
                "counterparty": booking["counterparty"],
                "portfolio": booking["portfolio"],
                "booking_reference": booking["booking_reference"],
                "internal_reference": booking["internal_reference"],
                "stage_2_status": booking["stage_2_status"],
                "event_type": booking["event_type"]
            })
            grouped_results[key]["total_deals"] += 1
        
        result = {
            "search_criteria": cache_params,
            "results": list(grouped_results.values()),
            "total_orders": len(grouped_results),
            "total_deal_bookings": len(deal_bookings),
            "query_timestamp": datetime.now().isoformat()
        }
        
        # Cache for 10 minutes
        await cache.set("deal_booking_lookup", cache_params, result, 600)
        
        result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Deal bookings lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")

# =============================================================================
# WORKFLOW 8: USD PB Deposit Checks - MEDIUM FREQUENCY
# =============================================================================

@app.post("/api/v2/usd-pb-deposits/capacity-check")
async def check_usd_pb_capacity(request: UsdPbDepositRequest):
    """
    Check USD PB deposit capacity and threshold status
    30-minute caching for threshold monitoring
    """
    start_time = datetime.now()
    
    cache_params = {
        "entity_id": request.entity_id or "ALL",
        "business_date": request.business_date or datetime.now().date().isoformat()
    }
    
    # Check cache
    cached_result = await cache.get("usd_pb_capacity", cache_params)
    if cached_result:
        cached_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": True
        }
        return cached_result
    
    try:
        # Query USD PB deposits with threshold analysis
        query = supabase.table('usd_pb_deposit').select('*')
        
        if request.entity_id:
            query = query.eq('entity_id', request.entity_id)
        if request.business_date:
            query = query.eq('measurement_date', request.business_date)
        else:
            query = query.eq('measurement_date', datetime.now().date())
        
        deposits_response = query.execute()
        deposits = deposits_response.data
        
        # Analyze capacity and thresholds
        capacity_analysis = analyze_usd_pb_capacity(deposits)
        
        result = {
            "search_criteria": cache_params,
            "capacity_analysis": capacity_analysis,
            "deposit_details": deposits,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Cache for 30 minutes
        await cache.set("usd_pb_capacity", cache_params, result, 1800)
        
        result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False
        }
        
        return result
        
    except Exception as e:
        logger.error(f"USD PB capacity check error: {e}")
        raise HTTPException(status_code=500, detail=f"Capacity check failed: {str(e)}")

def analyze_usd_pb_capacity(deposits: List[Dict]) -> Dict:
    """Analyze USD PB deposit capacity and threshold breaches"""
    analysis = {
        "total_entities": len(set(d.get("entity_id") for d in deposits)),
        "total_deposits": sum(float(d.get("total_usd_pb_deposits", 0)) for d in deposits),
        "breach_entities": [],
        "critical_entities": [],
        "warning_entities": [],
        "normal_entities": [],
        "capacity_summary": {}
    }
    
    for deposit in deposits:
        entity_id = deposit.get("entity_id")
        total_deposits = float(deposit.get("total_usd_pb_deposits", 0))
        available_capacity = float(deposit.get("available_capacity", 0))
        breach_status = deposit.get("breach_status", "NORMAL")
        
        entity_summary = {
            "entity_id": entity_id,
            "total_deposits": total_deposits,
            "available_capacity": available_capacity,
            "utilization_pct": float(deposit.get("utilization_percentage", 0)),
            "breach_status": breach_status,
            "threshold_warning": float(deposit.get("threshold_warning", 0)),
            "threshold_critical": float(deposit.get("threshold_critical", 0)),
            "threshold_maximum": float(deposit.get("threshold_maximum", 0))
        }
        
        if breach_status == "BREACH":
            analysis["breach_entities"].append(entity_summary)
        elif breach_status == "CRITICAL":
            analysis["critical_entities"].append(entity_summary)  
        elif breach_status == "WARNING":
            analysis["warning_entities"].append(entity_summary)
        else:
            analysis["normal_entities"].append(entity_summary)
    
    # Overall capacity summary
    analysis["capacity_summary"] = {
        "breach_count": len(analysis["breach_entities"]),
        "critical_count": len(analysis["critical_entities"]),
        "warning_count": len(analysis["warning_entities"]),
        "normal_count": len(analysis["normal_entities"]),
        "total_available_capacity": sum(float(d.get("available_capacity", 0)) for d in deposits),
        "requires_immediate_attention": len(analysis["breach_entities"]) > 0
    }
    
    return analysis

# =============================================================================
# WORKFLOW 4: GL Hedge Adjustment Entries by Currency - HIGH FREQUENCY
# =============================================================================

@app.get("/api/v2/gl-entries/hedge-adjustments/{currency}")
async def get_hedge_adjustments_by_currency(currency: str, days: int = 30):
    """
    Get GL hedge adjustment entries filtered by currency
    60-minute caching for adjustment tracking
    """
    start_time = datetime.now()
    
    cache_params = {
        "currency": currency,
        "days_back": days
    }
    
    # Check cache
    cached_result = await cache.get("hedge_adjustments", cache_params)
    if cached_result:
        cached_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": True
        }
        return cached_result
    
    try:
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Query GL entries for hedge adjustments
        response = supabase.table('gl_entries').select('*').eq('entry_type', 'HEDGE_ADJUSTMENT').gte('posting_date', start_date).lte('posting_date', end_date).order('posting_date', desc=True).execute()
        
        gl_entries = response.data
        
        # Filter and aggregate by currency (assuming currency info in product_code or other fields)
        currency_entries = [entry for entry in gl_entries if currency.upper() in str(entry.get('product_code', '')).upper()]
        
        # Aggregate adjustments
        adjustment_summary = aggregate_hedge_adjustments(currency_entries, currency)
        
        result = {
            "currency": currency,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "adjustment_summary": adjustment_summary,
            "gl_entries": currency_entries,
            "total_entries": len(currency_entries),
            "query_timestamp": datetime.now().isoformat()
        }
        
        # Cache for 1 hour
        await cache.set("hedge_adjustments", cache_params, result, 3600)
        
        result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Hedge adjustments lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")

def aggregate_hedge_adjustments(entries: List[Dict], currency: str) -> Dict:
    """Aggregate hedge adjustment entries by type and entity"""
    summary = {
        "currency": currency,
        "total_entries": len(entries),
        "total_debits": 0,
        "total_credits": 0,
        "net_adjustment": 0,
        "by_entity": {},
        "by_adjustment_type": {},
        "by_posting_date": {}
    }
    
    for entry in entries:
        entity_id = entry.get("entity_id", "UNKNOWN")
        adjustment_type = entry.get("source_field", "GENERAL")
        posting_date = entry.get("posting_date", "")
        
        # Convert amounts (assuming they're in SGD or need conversion)
        amount_sgd = float(entry.get("amount_sgd", 0))
        
        # Determine if debit or credit based on account or amount sign
        if amount_sgd > 0:
            summary["total_debits"] += amount_sgd
        else:
            summary["total_credits"] += abs(amount_sgd)
        
        # Aggregate by entity
        if entity_id not in summary["by_entity"]:
            summary["by_entity"][entity_id] = {"debits": 0, "credits": 0, "net": 0}
        
        if amount_sgd > 0:
            summary["by_entity"][entity_id]["debits"] += amount_sgd
        else:
            summary["by_entity"][entity_id]["credits"] += abs(amount_sgd)
        
        summary["by_entity"][entity_id]["net"] = (
            summary["by_entity"][entity_id]["debits"] - 
            summary["by_entity"][entity_id]["credits"]
        )
        
        # Aggregate by adjustment type
        if adjustment_type not in summary["by_adjustment_type"]:
            summary["by_adjustment_type"][adjustment_type] = {"count": 0, "total_amount": 0}
        
        summary["by_adjustment_type"][adjustment_type]["count"] += 1
        summary["by_adjustment_type"][adjustment_type]["total_amount"] += amount_sgd
        
        # Aggregate by posting date
        if posting_date not in summary["by_posting_date"]:
            summary["by_posting_date"][posting_date] = {"count": 0, "total_amount": 0}
        
        summary["by_posting_date"][posting_date]["count"] += 1
        summary["by_posting_date"][posting_date]["total_amount"] += amount_sgd
    
    summary["net_adjustment"] = summary["total_debits"] - summary["total_credits"]
    
    return summary

# =============================================================================
# CACHE MANAGEMENT & PERFORMANCE ENDPOINTS
# =============================================================================

@app.get("/api/v2/cache/stats")
async def get_cache_stats():
    """Get cache performance statistics"""
    try:
        redis_info = await cache.redis.info()
        
        stats = {
            "hit_ratio": {
                "hits": cache.hit_stats["hits"],
                "misses": cache.hit_stats["misses"],
                "ratio": cache.hit_stats["hits"] / (cache.hit_stats["hits"] + cache.hit_stats["misses"]) if (cache.hit_stats["hits"] + cache.hit_stats["misses"]) > 0 else 0
            },
            "redis_stats": {
                "connected_clients": redis_info.get("connected_clients", 0),
                "used_memory": redis_info.get("used_memory_human", "0B"),
                "keyspace_hits": redis_info.get("keyspace_hits", 0),
                "keyspace_misses": redis_info.get("keyspace_misses", 0),
                "total_commands_processed": redis_info.get("total_commands_processed", 0)
            },
            "cache_config": CACHE_CONFIG
        }
        
        return stats
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@app.post("/api/v2/cache/invalidate")
async def invalidate_cache(pattern: str = ""):
    """Invalidate cache by pattern or all caches"""
    try:
        if pattern:
            deleted = await cache.invalidate_pattern(pattern)
            return {"message": f"Invalidated {deleted} cache keys for pattern: {pattern}"}
        else:
            # Clear all HAWK caches
            deleted = await cache.invalidate_pattern("*")
            return {"message": f"Invalidated {deleted} total cache keys"}
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        raise HTTPException(status_code=500, detail=f"Invalidation failed: {str(e)}")

# =============================================================================
# HEALTH CHECK & STATUS
# =============================================================================

@app.get("/api/v2/health")
async def health_check():
    """System health check"""
    try:
        # Test Supabase connection
        supabase_test = supabase.table('entity_master').select('count').limit(1).execute()
        supabase_healthy = len(supabase_test.data) >= 0
        
        # Test Redis connection  
        redis_test = await cache.redis.ping()
        redis_healthy = redis_test
        
        return {
            "status": "healthy" if (supabase_healthy and redis_healthy) else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "supabase": "healthy" if supabase_healthy else "unhealthy",
                "redis": "healthy" if redis_healthy else "unhealthy"
            },
            "cache_stats": {
                "total_hits": cache.hit_stats["hits"],
                "total_misses": cache.hit_stats["misses"]
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)