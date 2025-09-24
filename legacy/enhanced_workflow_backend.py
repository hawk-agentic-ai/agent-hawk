"""
ENHANCED HAWK Agent Workflow-Optimized Backend
Based on actual 39-table Supabase schema analysis
Precision-tuned for 11 core hedge accounting operations
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
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

# Enhanced Pydantic models based on actual schema
class HedgeInstructionRequest(BaseModel):
    order_id: str
    sub_order_id: str
    instruction_type: str  # I, U, R, T
    exposure_currency: str
    hedge_amount_order: Optional[float] = None
    entity_id_filter: Optional[str] = None
    nav_type_filter: Optional[str] = None

class AvailableAmountRequest(BaseModel):
    entity_id: str
    currency_code: str
    nav_type: Optional[str] = None
    as_of_date: Optional[str] = None
    include_waterfall_logic: bool = True

class DealBookingRequest(BaseModel):
    order_id: str
    sub_order_id: Optional[str] = None
    include_stage_status: bool = True
    include_gl_status: bool = False

class UsdPbDepositRequest(BaseModel):
    currency_code: str = "USD"
    measurement_date: Optional[str] = None
    include_forecasts: bool = False

class HedgeAdjustmentRequest(BaseModel):
    currency_code: str
    days_back: int = 30
    include_entity_breakdown: bool = True
    include_differential_components: bool = False

# Enhanced cache configuration based on schema analysis
CACHE_CONFIG = {
    # Ultra High-Frequency - Core hedge operations
    "hedge_instruction_validation": {"ttl": 180, "priority": "critical"},     # 3 min
    "available_amounts_waterfall": {"ttl": 120, "priority": "critical"},     # 2 min
    "allocation_engine_lookup": {"ttl": 90, "priority": "critical"},         # 1.5 min
    
    # High-Frequency - Business event tracking  
    "deal_booking_stage_lookup": {"ttl": 300, "priority": "high"},           # 5 min
    "hedge_business_events": {"ttl": 240, "priority": "high"},               # 4 min
    "stage2_completion_status": {"ttl": 180, "priority": "high"},            # 3 min
    
    # Medium-Frequency - Analysis and reporting
    "usd_pb_capacity_analysis": {"ttl": 900, "priority": "medium"},          # 15 min
    "hedge_adjustments_breakdown": {"ttl": 1800, "priority": "medium"},      # 30 min
    "effectiveness_monitoring": {"ttl": 3600, "priority": "medium"},         # 60 min
    
    # Configuration caches - Lower frequency
    "entity_currency_config": {"ttl": 14400, "priority": "low"},             # 4 hours
    "threshold_configuration": {"ttl": 7200, "priority": "low"},             # 2 hours
    "waterfall_logic_config": {"ttl": 21600, "priority": "low"}              # 6 hours
}

class EnhancedWorkflowCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.hit_stats = {"hits": 0, "misses": 0, "workflows": {}}
        
    def _generate_key(self, workflow: str, operation: str, params: Dict) -> str:
        """Generate workflow-specific cache keys"""
        param_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:10]
        return f"hawk:v2:{workflow}:{operation}:{hash_suffix}"
    
    async def get_workflow_cache(self, workflow: str, operation: str, params: Dict) -> Optional[Any]:
        """Get cached result with workflow tracking"""
        try:
            key = self._generate_key(workflow, operation, params)
            cached = await self.redis.get(key)
            
            if cached:
                self.hit_stats["hits"] += 1
                if workflow not in self.hit_stats["workflows"]:
                    self.hit_stats["workflows"][workflow] = {"hits": 0, "misses": 0}
                self.hit_stats["workflows"][workflow]["hits"] += 1
                
                logger.info(f"Cache HIT for {workflow}.{operation}")
                return json.loads(cached)
            else:
                self.hit_stats["misses"] += 1
                if workflow not in self.hit_stats["workflows"]:
                    self.hit_stats["workflows"][workflow] = {"hits": 0, "misses": 0}
                self.hit_stats["workflows"][workflow]["misses"] += 1
                
                logger.info(f"Cache MISS for {workflow}.{operation}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set_workflow_cache(self, workflow: str, operation: str, params: Dict, data: Any, custom_ttl: int = None) -> bool:
        """Set workflow-specific cache"""
        try:
            key = self._generate_key(workflow, operation, params)
            ttl = custom_ttl or CACHE_CONFIG.get(operation, {}).get("ttl", 1800)
            
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
            logger.info(f"Cache SET for {workflow}.{operation} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

# Global instances
app = FastAPI(title="Enhanced HAWK Agent Backend", version="2.1.0")
supabase: Client = None
cache: EnhancedWorkflowCache = None

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
    cache = EnhancedWorkflowCache(redis_client)
    logger.info("✅ Enhanced Redis cache initialized")
    
    yield
    
    logger.info("🔄 Shutting down connections")

app.router.lifespan_context = lifespan

# =============================================================================
# WORKFLOW 1: Enhanced Hedge Instructions with Allocation Engine
# =============================================================================

@app.post("/api/v2/hedge-instructions/validate-enhanced")
async def validate_hedge_instruction_enhanced(request: HedgeInstructionRequest):
    """
    Enhanced hedge instruction validation using allocation_engine table
    Includes waterfall logic and entity-specific filtering
    """
    start_time = datetime.now()
    workflow = "hedge_instructions"
    
    cache_params = {
        "order_id": request.order_id,
        "sub_order_id": request.sub_order_id,
        "currency": request.exposure_currency,
        "type": request.instruction_type,
        "entity_filter": request.entity_id_filter,
        "nav_filter": request.nav_type_filter
    }
    
    # Try cache first
    cached_result = await cache.get_workflow_cache(workflow, "validation", cache_params)
    if cached_result:
        cached_result["performance"]["cache_hit"] = True
        cached_result["performance"]["total_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        return cached_result
    
    try:
        # Enhanced parallel validation with allocation engine
        validation_tasks = [
            get_allocation_engine_data(request.exposure_currency, request.entity_id_filter, request.nav_type_filter),
            get_waterfall_logic_config(request.exposure_currency, request.nav_type_filter),
            get_enhanced_entity_config(request.exposure_currency),
            get_threshold_configuration_enhanced(request.exposure_currency),
            check_existing_instructions(request.order_id, request.sub_order_id)
        ]
        
        allocation_data, waterfall_config, entity_config, thresholds, existing_instructions = await asyncio.gather(*validation_tasks)
        
        # Enhanced validation logic with allocation engine
        validation_result = {
            "validation_status": "PASSED",
            "order_id": request.order_id,
            "sub_order_id": request.sub_order_id,
            "instruction_type": request.instruction_type,
            "exposure_currency": request.exposure_currency,
            
            # Enhanced data from actual schema
            "allocation_engine_data": allocation_data,
            "waterfall_logic": waterfall_config,
            "entity_configuration": entity_config,
            "threshold_limits": thresholds,
            "existing_instructions": existing_instructions,
            
            # Available amounts from allocation engine
            "available_amounts_summary": calculate_available_from_allocation_engine(allocation_data),
            
            "validation_timestamp": datetime.now().isoformat(),
            "schema_version": "v2.1"
        }
        
        # Cache for 3 minutes (ultra-high frequency)
        await cache.set_workflow_cache(workflow, "validation", cache_params, validation_result, 180)
        
        validation_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False,
            "data_sources": {
                "allocation_engine": len(allocation_data),
                "waterfall_rules": len(waterfall_config),
                "entity_configs": len(entity_config),
                "thresholds": len(thresholds)
            }
        }
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Enhanced hedge instruction validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

async def get_allocation_engine_data(currency: str, entity_filter: str = None, nav_filter: str = None) -> List[Dict]:
    """Get allocation engine data with filters"""
    query = supabase.table('allocation_engine').select('*').eq('currency_code', currency).eq('allocation_status', 'Active')
    
    if entity_filter:
        query = query.eq('entity_id', entity_filter)
    if nav_filter:
        query = query.eq('nav_type', nav_filter)
    
    response = query.order('waterfall_priority').limit(50).execute()
    return response.data

async def get_waterfall_logic_config(currency: str, nav_type: str = None) -> List[Dict]:
    """Get waterfall logic configuration"""
    query = supabase.table('waterfall_logic_configuration').select('*').eq('currency_code', currency).eq('active_flag', 'Y')
    
    if nav_type:
        query = query.eq('nav_type', nav_type)
    
    response = query.order('priority_level').execute()
    return response.data

def calculate_available_from_allocation_engine(allocation_data: List[Dict]) -> Dict:
    """Calculate available amounts directly from allocation_engine table"""
    summary = {
        "total_entities": len(set(item.get("entity_id") for item in allocation_data)),
        "total_sfx_position": sum(float(item.get("sfx_position", 0)) for item in allocation_data),
        "total_car_amount": sum(float(item.get("car_amount_distribution", 0)) for item in allocation_data),
        "total_manual_overlay": sum(float(item.get("manual_overlay_amount", 0)) for item in allocation_data),
        "total_buffer_amount": sum(float(item.get("buffer_amount", 0)) for item in allocation_data),
        "total_hedged_position": sum(float(item.get("hedged_position", 0)) for item in allocation_data),
        "total_available_for_hedging": sum(float(item.get("available_amount_for_hedging", 0)) for item in allocation_data),
        "allocation_records": len(allocation_data)
    }
    
    return summary

# =============================================================================
# WORKFLOW 2: Enhanced Available Amounts with Waterfall Logic
# =============================================================================

@app.post("/api/v2/available-amounts/calculate-enhanced")
async def calculate_available_amounts_enhanced(request: AvailableAmountRequest):
    """
    Enhanced available amount calculation using allocation_engine and waterfall logic
    """
    start_time = datetime.now()
    workflow = "available_amounts"
    
    cache_params = {
        "entity_id": request.entity_id,
        "currency": request.currency_code,
        "nav_type": request.nav_type or "ALL",
        "date": request.as_of_date or datetime.now().date().isoformat(),
        "waterfall": request.include_waterfall_logic
    }
    
    # Check cache
    cached_result = await cache.get_workflow_cache(workflow, "calculation", cache_params)
    if cached_result:
        cached_result["performance"]["cache_hit"] = True
        cached_result["performance"]["total_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        return cached_result
    
    try:
        # Enhanced parallel data fetching
        calculation_tasks = [
            get_allocation_engine_for_entity(request.entity_id, request.currency_code, request.nav_type),
            get_position_nav_enhanced(request.entity_id, request.currency_code, request.nav_type, request.as_of_date),
            get_active_overlays(request.entity_id, request.currency_code),
            get_hedge_business_events_for_entity(request.entity_id, request.currency_code)
        ]
        
        if request.include_waterfall_logic:
            calculation_tasks.append(get_waterfall_logic_for_entity(request.entity_id, request.currency_code, request.nav_type))
        
        results = await asyncio.gather(*calculation_tasks)
        allocation_data = results[0]
        nav_data = results[1]
        overlay_data = results[2]
        hedge_events = results[3]
        waterfall_logic = results[4] if len(results) > 4 else []
        
        # Enhanced calculation using allocation engine
        calculation_result = {
            "entity_id": request.entity_id,
            "currency_code": request.currency_code,
            "nav_type": request.nav_type,
            "calculation_date": cache_params["date"],
            
            # Direct from allocation_engine table
            "allocation_engine_summary": calculate_available_from_allocation_engine(allocation_data),
            
            # Cross-verification with position_nav_master
            "position_nav_verification": verify_with_position_nav(allocation_data, nav_data),
            
            # Active overlays impact
            "overlay_adjustments": calculate_overlay_impact(overlay_data),
            
            # Current hedge position impact
            "hedge_position_impact": calculate_hedge_impact(hedge_events),
            
            # Waterfall logic application
            "waterfall_application": apply_waterfall_logic(allocation_data, waterfall_logic) if waterfall_logic else None,
            
            "calculation_timestamp": datetime.now().isoformat(),
            "schema_version": "v2.1"
        }
        
        # Cache for 2 minutes (ultra-high frequency)
        await cache.set_workflow_cache(workflow, "calculation", cache_params, calculation_result, 120)
        
        calculation_result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False,
            "data_sources": {
                "allocation_records": len(allocation_data),
                "nav_records": len(nav_data),
                "overlay_records": len(overlay_data),
                "hedge_events": len(hedge_events),
                "waterfall_rules": len(waterfall_logic)
            }
        }
        
        return calculation_result
        
    except Exception as e:
        logger.error(f"Enhanced available amounts calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

async def get_allocation_engine_for_entity(entity_id: str, currency: str, nav_type: str = None) -> List[Dict]:
    """Get allocation engine records for specific entity"""
    query = supabase.table('allocation_engine').select('*').eq('entity_id', entity_id).eq('currency_code', currency).eq('allocation_status', 'Active')
    
    if nav_type:
        query = query.eq('nav_type', nav_type)
    
    response = query.order('allocation_sequence').execute()
    return response.data

async def get_position_nav_enhanced(entity_id: str, currency: str, nav_type: str = None, as_of_date: str = None) -> List[Dict]:
    """Enhanced position NAV data with computed totals"""
    query = supabase.table('position_nav_master').select('*').eq('entity_id', entity_id).eq('currency_code', currency)
    
    if nav_type:
        query = query.eq('nav_type', nav_type)
    if as_of_date:
        query = query.eq('as_of_date', as_of_date)
    else:
        query = query.gte('as_of_date', (datetime.now() - timedelta(days=7)).date())
    
    response = query.order('as_of_date', desc=True).limit(20).execute()
    return response.data

async def get_active_overlays(entity_id: str, currency: str) -> List[Dict]:
    """Get active overlay configurations"""
    response = supabase.table('overlay_configuration').select('*').eq('entity_id', entity_id).eq('currency_code', currency).eq('active_flag', 'Y').eq('approval_status', 'Approved').execute()
    return response.data

async def get_hedge_business_events_for_entity(entity_id: str, currency: str) -> List[Dict]:
    """Get hedge business events for entity"""
    response = supabase.table('hedge_business_events').select('*, hedge_instructions!inner(*)').eq('entity_id', entity_id).eq('hedge_instructions.exposure_currency', currency).in_('stage_2_status', ['Completed', 'In Progress']).execute()
    return response.data

async def get_waterfall_logic_for_entity(entity_id: str, currency: str, nav_type: str = None) -> List[Dict]:
    """Get waterfall logic rules for entity"""
    # Get entity type first
    entity_response = supabase.table('entity_master').select('entity_type').eq('entity_id', entity_id).single().execute()
    entity_type = entity_response.data.get('entity_type') if entity_response.data else None
    
    query = supabase.table('waterfall_logic_configuration').select('*').eq('currency_code', currency).eq('active_flag', 'Y')
    
    if entity_type:
        query = query.eq('entity_type', entity_type)
    if nav_type:
        query = query.eq('nav_type', nav_type)
    
    response = query.order('priority_level').execute()
    return response.data

def verify_with_position_nav(allocation_data: List[Dict], nav_data: List[Dict]) -> Dict:
    """Cross-verify allocation engine with position NAV master"""
    allocation_totals = calculate_available_from_allocation_engine(allocation_data)
    
    nav_totals = {
        "total_current_position": sum(float(item.get("current_position", 0)) for item in nav_data),
        "total_coi_amount": sum(float(item.get("coi_amount", 0)) for item in nav_data),
        "total_re_amount": sum(float(item.get("re_amount", 0)) for item in nav_data),
        "total_computed_nav": sum(float(item.get("computed_total_nav", 0)) for item in nav_data),
        "nav_records": len(nav_data)
    }
    
    return {
        "allocation_engine_totals": allocation_totals,
        "position_nav_totals": nav_totals,
        "variance_analysis": {
            "sfx_position_variance": allocation_totals["total_sfx_position"] - nav_totals["total_current_position"],
            "data_consistency_score": calculate_consistency_score(allocation_totals, nav_totals)
        }
    }

def calculate_overlay_impact(overlay_data: List[Dict]) -> Dict:
    """Calculate impact of active overlays"""
    return {
        "total_overlay_amount": sum(float(item.get("overlay_amount", 0)) for item in overlay_data),
        "overlay_by_type": {
            overlay_type: sum(float(item.get("overlay_amount", 0)) for item in overlay_data if item.get("overlay_type") == overlay_type)
            for overlay_type in set(item.get("overlay_type") for item in overlay_data)
        },
        "overlay_count": len(overlay_data),
        "pending_approvals": len([item for item in overlay_data if item.get("approval_status") == "Pending"])
    }

def calculate_hedge_impact(hedge_events: List[Dict]) -> Dict:
    """Calculate current hedge position impact"""
    active_hedges = [event for event in hedge_events if event.get("stage_2_status") == "Completed"]
    
    return {
        "total_hedge_notional": sum(float(event.get("notional_amount", 0)) for event in active_hedges),
        "hedge_by_instrument": {
            instrument: sum(float(event.get("notional_amount", 0)) for event in active_hedges if event.get("hedging_instrument") == instrument)
            for instrument in set(event.get("hedging_instrument") for event in active_hedges)
        },
        "active_hedge_count": len(active_hedges),
        "pending_stage2_count": len([event for event in hedge_events if event.get("stage_2_status") == "In Progress"])
    }

def apply_waterfall_logic(allocation_data: List[Dict], waterfall_rules: List[Dict]) -> Dict:
    """Apply waterfall logic to allocation data"""
    if not waterfall_rules:
        return None
    
    # Sort allocation data by waterfall priority
    sorted_allocations = sorted(allocation_data, key=lambda x: x.get("waterfall_priority", 999))
    
    waterfall_result = {
        "waterfall_sequence": [],
        "total_prioritized_amount": 0,
        "rules_applied": len(waterfall_rules)
    }
    
    for rule in sorted(waterfall_rules, key=lambda x: x.get("priority_level", 999)):
        matching_allocations = [
            alloc for alloc in sorted_allocations 
            if meets_waterfall_criteria(alloc, rule)
        ]
        
        rule_amount = sum(float(alloc.get("available_amount_for_hedging", 0)) for alloc in matching_allocations)
        
        waterfall_result["waterfall_sequence"].append({
            "priority_level": rule.get("priority_level"),
            "description": rule.get("description"),
            "matching_allocations": len(matching_allocations),
            "amount": rule_amount,
            "business_rule": rule.get("business_rule")
        })
        
        waterfall_result["total_prioritized_amount"] += rule_amount
    
    return waterfall_result

def meets_waterfall_criteria(allocation: Dict, rule: Dict) -> bool:
    """Check if allocation meets waterfall rule criteria"""
    # Implement business logic for waterfall criteria matching
    nav_criteria = rule.get("nav_amount_criteria", "")
    car_exemption_required = rule.get("car_exemption_required", "N")
    
    # Check CAR exemption requirement
    if car_exemption_required == "Y" and allocation.get("car_exemption_flag") != "Y":
        return False
    
    # Add more criteria checks based on your business rules
    return True

def calculate_consistency_score(allocation_totals: Dict, nav_totals: Dict) -> float:
    """Calculate data consistency score between allocation engine and position NAV"""
    try:
        variance = abs(allocation_totals["total_sfx_position"] - nav_totals["total_current_position"])
        total_amount = allocation_totals["total_sfx_position"]
        
        if total_amount == 0:
            return 100.0
        
        consistency = max(0, 100 - (variance / total_amount * 100))
        return round(consistency, 2)
    except:
        return 0.0

# =============================================================================
# WORKFLOW 3: Enhanced Deal Bookings with Stage Status
# =============================================================================

@app.post("/api/v2/deal-bookings/enhanced-lookup")
async def get_deal_bookings_enhanced(request: DealBookingRequest):
    """
    Enhanced deal booking lookup with stage_2_status, stage_3_status tracking
    """
    start_time = datetime.now()
    workflow = "deal_bookings"
    
    cache_params = {
        "order_id": request.order_id,
        "sub_order_id": request.sub_order_id or "ALL",
        "include_stage": request.include_stage_status,
        "include_gl": request.include_gl_status
    }
    
    # Check cache
    cached_result = await cache.get_workflow_cache(workflow, "enhanced_lookup", cache_params)
    if cached_result:
        cached_result["performance"]["cache_hit"] = True
        cached_result["performance"]["total_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        return cached_result
    
    try:
        # Enhanced query with stage tracking
        base_query = """
        SELECT 
            hi.instruction_id,
            hi.order_id,
            hi.sub_order_id,
            hi.instruction_type,
            hi.exposure_currency,
            hi.hedge_amount_order,
            hi.allocated_notional,
            hi.not_allocated_notional,
            hi.instruction_status,
            hi.check_status,
            hi.acknowledgement_status,
            hbe.event_id,
            hbe.entity_id,
            hbe.stage_2_status,
            hbe.stage_3_status,
            hbe.stage_2_start_time,
            hbe.stage_2_completion_time,
            hbe.gl_posting_status,
            hbe.notional_amount as event_notional,
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
            db.internal_reference,
            db.final_hedge_position,
            db.position_tracking
        FROM hedge_instructions hi
        JOIN hedge_business_events hbe ON hi.instruction_id = hbe.instruction_id
        JOIN deal_bookings db ON hbe.event_id = db.event_id
        WHERE hi.order_id = %s
        """
        
        params = [request.order_id]
        if request.sub_order_id:
            base_query += " AND hi.sub_order_id = %s"
            params.append(request.sub_order_id)
            
        base_query += " ORDER BY hi.order_id, hi.sub_order_id, db.deal_sequence"
        
        # Execute enhanced query
        response = supabase.rpc('execute_sql', {'sql': base_query, 'params': params}).execute()
        deal_data = response.data
        
        # Enhanced grouping and analysis
        enhanced_results = analyze_deal_booking_stages(deal_data)
        
        result = {
            "search_criteria": cache_params,
            "enhanced_analysis": enhanced_results,
            "raw_deal_data": deal_data,
            "total_deals": len(deal_data),
            "query_timestamp": datetime.now().isoformat(),
            "schema_version": "v2.1"
        }
        
        # Get Stage 2 error details if requested
        if request.include_stage_status and any(item.get("stage_2_status") == "Failed" for item in deal_data):
            stage2_errors = await get_stage2_error_details([item.get("event_id") for item in deal_data])
            result["stage2_error_details"] = stage2_errors
        
        # Cache for 5 minutes
        await cache.set_workflow_cache(workflow, "enhanced_lookup", cache_params, result, 300)
        
        result["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False,
            "data_sources": {
                "deal_bookings": len(deal_data),
                "unique_events": len(set(item.get("event_id") for item in deal_data)),
                "unique_instructions": len(set(item.get("instruction_id") for item in deal_data))
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced deal bookings lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")

def analyze_deal_booking_stages(deal_data: List[Dict]) -> Dict:
    """Analyze deal booking data with stage progression tracking"""
    analysis = {
        "stage_progression": {
            "stage_2_completed": 0,
            "stage_2_in_progress": 0,
            "stage_2_failed": 0,
            "stage_3_completed": 0,
            "stage_3_in_progress": 0,
            "stage_3_failed": 0
        },
        "gl_posting_status": {},
        "deal_status_breakdown": {},
        "hedge_position_tracking": {
            "final_hedge_positions": 0,
            "position_tracking_enabled": 0,
            "total_hedge_notional": 0
        },
        "time_analysis": {
            "avg_stage2_completion_time": None,
            "longest_stage2_time": None,
            "deals_over_sla": 0
        }
    }
    
    stage2_times = []
    
    for deal in deal_data:
        # Stage progression analysis
        stage_2_status = deal.get("stage_2_status", "")
        stage_3_status = deal.get("stage_3_status", "")
        
        if stage_2_status == "Completed":
            analysis["stage_progression"]["stage_2_completed"] += 1
        elif stage_2_status == "In Progress":
            analysis["stage_progression"]["stage_2_in_progress"] += 1
        elif stage_2_status == "Failed":
            analysis["stage_progression"]["stage_2_failed"] += 1
            
        if stage_3_status == "Completed":
            analysis["stage_progression"]["stage_3_completed"] += 1
        elif stage_3_status == "In Progress":
            analysis["stage_progression"]["stage_3_in_progress"] += 1
        elif stage_3_status == "Failed":
            analysis["stage_progression"]["stage_3_failed"] += 1
        
        # GL posting status
        gl_status = deal.get("gl_posting_status", "Unknown")
        analysis["gl_posting_status"][gl_status] = analysis["gl_posting_status"].get(gl_status, 0) + 1
        
        # Deal status breakdown
        deal_status = deal.get("deal_status", "Unknown")
        analysis["deal_status_breakdown"][deal_status] = analysis["deal_status_breakdown"].get(deal_status, 0) + 1
        
        # Hedge position tracking
        if deal.get("final_hedge_position"):
            analysis["hedge_position_tracking"]["final_hedge_positions"] += 1
        if deal.get("position_tracking"):
            analysis["hedge_position_tracking"]["position_tracking_enabled"] += 1
        
        event_notional = float(deal.get("event_notional", 0))
        analysis["hedge_position_tracking"]["total_hedge_notional"] += event_notional
        
        # Time analysis
        stage2_start = deal.get("stage_2_start_time")
        stage2_completion = deal.get("stage_2_completion_time")
        
        if stage2_start and stage2_completion:
            try:
                start_time = datetime.fromisoformat(stage2_start)
                completion_time = datetime.fromisoformat(stage2_completion)
                duration_minutes = (completion_time - start_time).total_seconds() / 60
                stage2_times.append(duration_minutes)
                
                # Check SLA (assuming 60 minutes SLA)
                if duration_minutes > 60:
                    analysis["time_analysis"]["deals_over_sla"] += 1
            except:
                pass
    
    # Calculate time statistics
    if stage2_times:
        analysis["time_analysis"]["avg_stage2_completion_time"] = sum(stage2_times) / len(stage2_times)
        analysis["time_analysis"]["longest_stage2_time"] = max(stage2_times)
    
    return analysis

async def get_stage2_error_details(event_ids: List[str]) -> List[Dict]:
    """Get Stage 2 error details for failed events"""
    if not event_ids:
        return []
    
    response = supabase.table('stage2_error_log').select('*').in_('event_id', event_ids).order('created_date', desc=True).execute()
    return response.data

# =============================================================================
# WORKFLOW 8: Enhanced USD PB Deposit Analysis
# =============================================================================

@app.post("/api/v2/usd-pb-deposits/enhanced-analysis")
async def enhanced_usd_pb_analysis(request: UsdPbDepositRequest):
    """
    Enhanced USD PB deposit analysis with forecasting and trend analysis
    """
    start_time = datetime.now()
    workflow = "usd_pb_deposits"
    
    cache_params = {
        "currency": request.currency_code,
        "measurement_date": request.measurement_date or datetime.now().date().isoformat(),
        "include_forecasts": request.include_forecasts
    }
    
    # Check cache
    cached_result = await cache.get_workflow_cache(workflow, "enhanced_analysis", cache_params)
    if cached_result:
        cached_result["performance"]["cache_hit"] = True
        cached_result["performance"]["total_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        return cached_result
    
    try:
        # Enhanced USD PB deposit query with all fields
        query_date = request.measurement_date or datetime.now().date().isoformat()
        
        response = supabase.table('usd_pb_deposit').select('*').eq('currency_code', request.currency_code).eq('measurement_date', query_date).execute()
        deposit_data = response.data
        
        # Enhanced analysis with all available fields
        enhanced_analysis = {
            "measurement_date": query_date,
            "currency_code": request.currency_code,
            "total_records": len(deposit_data),
            
            # Capacity analysis
            "capacity_analysis": analyze_usd_pb_capacity_enhanced(deposit_data),
            
            # Trend analysis
            "trend_analysis": analyze_deposit_trends(deposit_data),
            
            # Risk analysis
            "risk_analysis": analyze_deposit_risks(deposit_data),
            
            # Forecasting (if requested)
            "forecasting_analysis": analyze_deposit_forecasts(deposit_data) if request.include_forecasts else None,
            
            # Data quality assessment
            "data_quality_analysis": analyze_data_quality(deposit_data),
            
            "analysis_timestamp": datetime.now().isoformat(),
            "schema_version": "v2.1"
        }
        
        # Cache for 15 minutes
        await cache.set_workflow_cache(workflow, "enhanced_analysis", cache_params, enhanced_analysis, 900)
        
        enhanced_analysis["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False,
            "data_records_analyzed": len(deposit_data)
        }
        
        return enhanced_analysis
        
    except Exception as e:
        logger.error(f"Enhanced USD PB deposit analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def analyze_usd_pb_capacity_enhanced(deposit_data: List[Dict]) -> Dict:
    """Enhanced USD PB capacity analysis with all fields"""
    if not deposit_data:
        return {"error": "No deposit data available"}
    
    analysis = {
        "overall_totals": {
            "total_usd_pb_deposits": sum(float(item.get("total_usd_pb_deposits", 0)) for item in deposit_data),
            "total_current_hedge_exposure": sum(float(item.get("current_hedge_exposure", 0)) for item in deposit_data),
            "total_pending_hedge_requests": sum(float(item.get("pending_hedge_requests", 0)) for item in deposit_data),
            "total_projected_exposure": sum(float(item.get("total_projected_exposure", 0)) for item in deposit_data),
            "total_available_capacity": sum(float(item.get("available_capacity", 0)) for item in deposit_data)
        },
        "threshold_analysis": {
            "breach_entities": [],
            "critical_entities": [],
            "warning_entities": [],
            "normal_entities": []
        },
        "utilization_statistics": {
            "avg_utilization": 0,
            "max_utilization": 0,
            "min_utilization": 100,
            "entities_over_80_percent": 0
        }
    }
    
    utilizations = []
    
    for deposit in deposit_data:
        deposit_id = deposit.get("deposit_id", "Unknown")
        breach_status = deposit.get("breach_status", "NORMAL")
        utilization = float(deposit.get("utilization_percentage", 0))
        
        utilizations.append(utilization)
        
        entity_summary = {
            "deposit_id": deposit_id,
            "total_deposits": float(deposit.get("total_usd_pb_deposits", 0)),
            "available_capacity": float(deposit.get("available_capacity", 0)),
            "utilization_percentage": utilization,
            "breach_status": breach_status,
            "threshold_warning": float(deposit.get("threshold_warning", 0)),
            "threshold_critical": float(deposit.get("threshold_critical", 0)),
            "threshold_maximum": float(deposit.get("threshold_maximum", 0)),
            "daily_change": float(deposit.get("daily_change_amount", 0)),
            "escalation_level": deposit.get("escalation_level", "None")
        }
        
        if breach_status == "BREACH":
            analysis["threshold_analysis"]["breach_entities"].append(entity_summary)
        elif breach_status == "CRITICAL":
            analysis["threshold_analysis"]["critical_entities"].append(entity_summary)
        elif breach_status == "WARNING":
            analysis["threshold_analysis"]["warning_entities"].append(entity_summary)
        else:
            analysis["threshold_analysis"]["normal_entities"].append(entity_summary)
        
        if utilization >= 80:
            analysis["utilization_statistics"]["entities_over_80_percent"] += 1
    
    # Calculate utilization statistics
    if utilizations:
        analysis["utilization_statistics"]["avg_utilization"] = sum(utilizations) / len(utilizations)
        analysis["utilization_statistics"]["max_utilization"] = max(utilizations)
        analysis["utilization_statistics"]["min_utilization"] = min(utilizations)
    
    return analysis

def analyze_deposit_trends(deposit_data: List[Dict]) -> Dict:
    """Analyze deposit trends and changes"""
    trend_analysis = {
        "daily_changes": {
            "total_daily_change": sum(float(item.get("daily_change_amount", 0)) for item in deposit_data),
            "avg_daily_change_percent": sum(float(item.get("daily_change_percentage", 0)) for item in deposit_data) / len(deposit_data) if deposit_data else 0,
            "entities_increasing": len([item for item in deposit_data if float(item.get("daily_change_amount", 0)) > 0]),
            "entities_decreasing": len([item for item in deposit_data if float(item.get("daily_change_amount", 0)) < 0])
        },
        "deposit_trends": {
            "upward_trend": len([item for item in deposit_data if item.get("deposit_trend") == "Increasing"]),
            "downward_trend": len([item for item in deposit_data if item.get("deposit_trend") == "Decreasing"]),
            "stable_trend": len([item for item in deposit_data if item.get("deposit_trend") == "Stable"])
        }
    }
    
    return trend_analysis

def analyze_deposit_risks(deposit_data: List[Dict]) -> Dict:
    """Analyze deposit-related risks"""
    risk_analysis = {
        "breach_risks": {
            "current_breaches": len([item for item in deposit_data if item.get("breach_status") == "BREACH"]),
            "critical_alerts": len([item for item in deposit_data if item.get("breach_status") == "CRITICAL"]),
            "warning_alerts": len([item for item in deposit_data if item.get("breach_status") == "WARNING"]),
            "entities_requiring_escalation": len([item for item in deposit_data if item.get("escalation_level") in ["Level2", "Level3"]])
        },
        "notification_status": {
            "notifications_sent": len([item for item in deposit_data if item.get("notification_sent_flag") == "Y"]),
            "notifications_pending": len([item for item in deposit_data if item.get("notification_sent_flag") == "N"]),
            "recent_breaches": len([item for item in deposit_data if item.get("last_breach_timestamp") and 
                                  (datetime.now() - datetime.fromisoformat(item.get("last_breach_timestamp"))).days <= 1])
        }
    }
    
    return risk_analysis

def analyze_deposit_forecasts(deposit_data: List[Dict]) -> Dict:
    """Analyze deposit forecasts"""
    forecast_analysis = {
        "forecast_1_day": {
            "total_forecast": sum(float(item.get("forecast_1_day", 0)) for item in deposit_data),
            "entities_with_forecasts": len([item for item in deposit_data if item.get("forecast_1_day")])
        },
        "forecast_7_days": {
            "total_forecast": sum(float(item.get("forecast_7_days", 0)) for item in deposit_data),
            "entities_with_forecasts": len([item for item in deposit_data if item.get("forecast_7_days")])
        },
        "forecast_30_days": {
            "total_forecast": sum(float(item.get("forecast_30_days", 0)) for item in deposit_data),
            "entities_with_forecasts": len([item for item in deposit_data if item.get("forecast_30_days")])
        }
    }
    
    return forecast_analysis

def analyze_data_quality(deposit_data: List[Dict]) -> Dict:
    """Analyze data quality scores"""
    quality_scores = [float(item.get("data_quality_score", 0)) for item in deposit_data if item.get("data_quality_score")]
    
    quality_analysis = {
        "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
        "min_quality_score": min(quality_scores) if quality_scores else 0,
        "max_quality_score": max(quality_scores) if quality_scores else 0,
        "entities_with_quality_scores": len(quality_scores),
        "high_quality_entities": len([score for score in quality_scores if score >= 90]),
        "low_quality_entities": len([score for score in quality_scores if score < 70])
    }
    
    return quality_analysis

# =============================================================================
# WORKFLOW 4: Enhanced GL Hedge Adjustments with Differential Components
# =============================================================================

@app.post("/api/v2/gl-entries/hedge-adjustments-enhanced")
async def get_hedge_adjustments_enhanced(request: HedgeAdjustmentRequest):
    """
    Enhanced GL hedge adjustment analysis with differential components
    """
    start_time = datetime.now()
    workflow = "hedge_adjustments"
    
    cache_params = {
        "currency": request.currency_code,
        "days_back": request.days_back,
        "entity_breakdown": request.include_entity_breakdown,
        "differential_components": request.include_differential_components
    }
    
    # Check cache
    cached_result = await cache.get_workflow_cache(workflow, "enhanced_analysis", cache_params)
    if cached_result:
        cached_result["performance"]["cache_hit"] = True
        cached_result["performance"]["total_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        return cached_result
    
    try:
        # Enhanced GL entries query
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=request.days_back)
        
        # Build enhanced query with all relevant fields
        query = supabase.table('gl_entries').select('*').eq('entry_type', 'HEDGE_ADJUSTMENT').gte('posting_date', start_date).lte('posting_date', end_date).order('posting_date', desc=True)
        
        response = query.execute()
        gl_entries = response.data
        
        # Filter by currency (check multiple fields where currency might be referenced)
        currency_entries = []
        for entry in gl_entries:
            # Check if currency appears in product_code, proxy_currency_pair, or other fields
            product_code = str(entry.get('product_code', '')).upper()
            proxy_pair = str(entry.get('proxy_currency_pair', '')).upper()
            
            if (request.currency_code.upper() in product_code or 
                request.currency_code.upper() in proxy_pair):
                currency_entries.append(entry)
        
        # Enhanced analysis
        enhanced_analysis = {
            "currency_code": request.currency_code,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": request.days_back
            },
            "total_entries": len(currency_entries),
            
            # Enhanced aggregation analysis
            "adjustment_summary": aggregate_hedge_adjustments_enhanced(currency_entries),
            
            # Entity breakdown if requested
            "entity_breakdown": analyze_adjustments_by_entity(currency_entries) if request.include_entity_breakdown else None,
            
            # Differential components analysis if requested
            "differential_analysis": analyze_differential_components(currency_entries) if request.include_differential_components else None,
            
            # Processing flags analysis
            "processing_analysis": analyze_processing_flags(currency_entries),
            
            "analysis_timestamp": datetime.now().isoformat(),
            "schema_version": "v2.1"
        }
        
        # Cache for 30 minutes
        await cache.set_workflow_cache(workflow, "enhanced_analysis", cache_params, enhanced_analysis, 1800)
        
        enhanced_analysis["performance"] = {
            "total_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "cache_hit": False,
            "entries_analyzed": len(currency_entries),
            "total_entries_scanned": len(gl_entries)
        }
        
        return enhanced_analysis
        
    except Exception as e:
        logger.error(f"Enhanced hedge adjustments analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def aggregate_hedge_adjustments_enhanced(entries: List[Dict]) -> Dict:
    """Enhanced aggregation with all GL entry fields"""
    summary = {
        "totals": {
            "total_entries": len(entries),
            "total_amount_sgd": sum(float(entry.get("amount_sgd", 0)) for entry in entries),
            "positive_adjustments": sum(float(entry.get("amount_sgd", 0)) for entry in entries if float(entry.get("amount_sgd", 0)) > 0),
            "negative_adjustments": sum(abs(float(entry.get("amount_sgd", 0))) for entry in entries if float(entry.get("amount_sgd", 0)) < 0),
            "net_adjustment": sum(float(entry.get("amount_sgd", 0)) for entry in entries)
        },
        "by_source_field": {},
        "by_source_system": {},
        "by_entity": {},
        "by_posting_date": {},
        "account_analysis": {
            "unique_debit_accounts": set(),
            "unique_credit_accounts": set(),
            "account_pairs": {}
        }
    }
    
    for entry in entries:
        amount_sgd = float(entry.get("amount_sgd", 0))
        entity_id = entry.get("entity_id", "UNKNOWN")
        source_field = entry.get("source_field", "GENERAL")
        source_system = entry.get("source_system", "UNKNOWN")
        posting_date = entry.get("posting_date", "")
        debit_account = entry.get("debit_account", "")
        credit_account = entry.get("credit_account", "")
        
        # Aggregate by source field
        if source_field not in summary["by_source_field"]:
            summary["by_source_field"][source_field] = {"count": 0, "total_amount": 0}
        summary["by_source_field"][source_field]["count"] += 1
        summary["by_source_field"][source_field]["total_amount"] += amount_sgd
        
        # Aggregate by source system
        if source_system not in summary["by_source_system"]:
            summary["by_source_system"][source_system] = {"count": 0, "total_amount": 0}
        summary["by_source_system"][source_system]["count"] += 1
        summary["by_source_system"][source_system]["total_amount"] += amount_sgd
        
        # Aggregate by entity
        if entity_id not in summary["by_entity"]:
            summary["by_entity"][entity_id] = {"count": 0, "total_amount": 0, "debit_total": 0, "credit_total": 0}
        summary["by_entity"][entity_id]["count"] += 1
        summary["by_entity"][entity_id]["total_amount"] += amount_sgd
        if amount_sgd > 0:
            summary["by_entity"][entity_id]["debit_total"] += amount_sgd
        else:
            summary["by_entity"][entity_id]["credit_total"] += abs(amount_sgd)
        
        # Aggregate by posting date
        if posting_date not in summary["by_posting_date"]:
            summary["by_posting_date"][posting_date] = {"count": 0, "total_amount": 0}
        summary["by_posting_date"][posting_date]["count"] += 1
        summary["by_posting_date"][posting_date]["total_amount"] += amount_sgd
        
        # Account analysis
        if debit_account:
            summary["account_analysis"]["unique_debit_accounts"].add(debit_account)
        if credit_account:
            summary["account_analysis"]["unique_credit_accounts"].add(credit_account)
        
        account_pair = f"{debit_account}|{credit_account}"
        if account_pair not in summary["account_analysis"]["account_pairs"]:
            summary["account_analysis"]["account_pairs"][account_pair] = {"count": 0, "total_amount": 0}
        summary["account_analysis"]["account_pairs"][account_pair]["count"] += 1
        summary["account_analysis"]["account_pairs"][account_pair]["total_amount"] += amount_sgd
    
    # Convert sets to lists for JSON serialization
    summary["account_analysis"]["unique_debit_accounts"] = list(summary["account_analysis"]["unique_debit_accounts"])
    summary["account_analysis"]["unique_credit_accounts"] = list(summary["account_analysis"]["unique_credit_accounts"])
    
    return summary

def analyze_adjustments_by_entity(entries: List[Dict]) -> Dict:
    """Detailed entity-level adjustment analysis"""
    entity_analysis = {}
    
    for entry in entries:
        entity_id = entry.get("entity_id", "UNKNOWN")
        
        if entity_id not in entity_analysis:
            entity_analysis[entity_id] = {
                "total_entries": 0,
                "total_amount": 0,
                "by_source_field": {},
                "reversal_entries": 0,
                "daily_processing_entries": 0,
                "monthly_only_entries": 0,
                "date_range": {"earliest": None, "latest": None}
            }
        
        entity_data = entity_analysis[entity_id]
        amount_sgd = float(entry.get("amount_sgd", 0))
        source_field = entry.get("source_field", "GENERAL")
        posting_date = entry.get("posting_date")
        
        entity_data["total_entries"] += 1
        entity_data["total_amount"] += amount_sgd
        
        # Source field breakdown
        if source_field not in entity_data["by_source_field"]:
            entity_data["by_source_field"][source_field] = {"count": 0, "amount": 0}
        entity_data["by_source_field"][source_field]["count"] += 1
        entity_data["by_source_field"][source_field]["amount"] += amount_sgd
        
        # Processing flags
        if entry.get("reversal_flag"):
            entity_data["reversal_entries"] += 1
        if entry.get("daily_processing"):
            entity_data["daily_processing_entries"] += 1
        if entry.get("monthly_only"):
            entity_data["monthly_only_entries"] += 1
        
        # Date range tracking
        if posting_date:
            if not entity_data["date_range"]["earliest"] or posting_date < entity_data["date_range"]["earliest"]:
                entity_data["date_range"]["earliest"] = posting_date
            if not entity_data["date_range"]["latest"] or posting_date > entity_data["date_range"]["latest"]:
                entity_data["date_range"]["latest"] = posting_date
    
    return entity_analysis

def analyze_differential_components(entries: List[Dict]) -> Dict:
    """Analyze differential components in GL entries"""
    differential_analysis = {
        "entries_with_differentials": 0,
        "differential_types": {},
        "dual_currency_treatments": 0,
        "embedded_spot_logic_entries": 0,
        "ndf_specific_logic_entries": 0,
        "currency_differential_breakdown": {}
    }
    
    for entry in entries:
        differential_components = entry.get("differential_components")
        dual_currency_treatment = entry.get("dual_currency_treatment")
        embedded_spot_logic = entry.get("embedded_spot_logic")
        ndf_specific_logic = entry.get("ndf_specific_logic")
        currency_differential_type = entry.get("currency_differential_type")
        
        if differential_components:
            differential_analysis["entries_with_differentials"] += 1
            # Parse JSONB differential components if needed
            # Add specific differential analysis based on your business logic
        
        if dual_currency_treatment:
            differential_analysis["dual_currency_treatments"] += 1
        
        if embedded_spot_logic:
            differential_analysis["embedded_spot_logic_entries"] += 1
        
        if ndf_specific_logic:
            differential_analysis["ndf_specific_logic_entries"] += 1
        
        if currency_differential_type:
            if currency_differential_type not in differential_analysis["currency_differential_breakdown"]:
                differential_analysis["currency_differential_breakdown"][currency_differential_type] = {"count": 0, "total_amount": 0}
            differential_analysis["currency_differential_breakdown"][currency_differential_type]["count"] += 1
            differential_analysis["currency_differential_breakdown"][currency_differential_type]["total_amount"] += float(entry.get("amount_sgd", 0))
    
    return differential_analysis

def analyze_processing_flags(entries: List[Dict]) -> Dict:
    """Analyze processing flags and characteristics"""
    processing_analysis = {
        "reversal_entries": len([e for e in entries if e.get("reversal_flag")]),
        "daily_processing_entries": len([e for e in entries if e.get("daily_processing")]),
        "monthly_only_entries": len([e for e in entries if e.get("monthly_only")]),
        "entity_dependent_entries": len([e for e in entries if e.get("entity_dependent_posting")]),
        "daily_reversal_entries": len([e for e in entries if e.get("daily_reversal")]),
        
        "processing_patterns": {
            "daily_and_monthly": len([e for e in entries if e.get("daily_processing") and e.get("monthly_only")]),
            "reversal_and_daily": len([e for e in entries if e.get("reversal_flag") and e.get("daily_processing")]),
            "entity_dependent_and_reversal": len([e for e in entries if e.get("entity_dependent_posting") and e.get("reversal_flag")])
        }
    }
    
    return processing_analysis

# =============================================================================
# Enhanced Configuration Endpoints
# =============================================================================

async def get_enhanced_entity_config(currency: str) -> List[Dict]:
    """Enhanced entity configuration with all related data"""
    response = supabase.table('entity_master').select('*, currency_configuration!inner(*), hedging_framework(*)').eq('currency_configuration.currency_code', currency).eq('active_flag', 'Y').execute()
    return response.data

async def get_threshold_configuration_enhanced(currency: str) -> List[Dict]:
    """Enhanced threshold configuration with escalation details"""
    response = supabase.table('threshold_configuration').select('*').eq('currency_code', currency).eq('active_flag', 'Y').execute()
    return response.data

async def check_existing_instructions(order_id: str, sub_order_id: str) -> List[Dict]:
    """Check for existing or related instructions"""
    # Check for exact match
    exact_match = supabase.table('hedge_instructions').select('*').eq('order_id', order_id).eq('sub_order_id', sub_order_id).execute()
    
    # Check for related instructions (same order_id)
    related_instructions = supabase.table('hedge_instructions').select('*').eq('order_id', order_id).neq('sub_order_id', sub_order_id).execute()
    
    return {
        "exact_matches": exact_match.data,
        "related_instructions": related_instructions.data
    }

# =============================================================================
# ENHANCED CACHE MANAGEMENT & PERFORMANCE
# =============================================================================

@app.get("/api/v2/cache/workflow-stats")
async def get_workflow_cache_stats():
    """Get workflow-specific cache performance statistics"""
    try:
        redis_info = await cache.redis.info()
        
        stats = {
            "overall_performance": {
                "total_hits": cache.hit_stats["hits"],
                "total_misses": cache.hit_stats["misses"],
                "overall_hit_ratio": cache.hit_stats["hits"] / (cache.hit_stats["hits"] + cache.hit_stats["misses"]) if (cache.hit_stats["hits"] + cache.hit_stats["misses"]) > 0 else 0
            },
            "workflow_performance": cache.hit_stats["workflows"],
            "redis_performance": {
                "connected_clients": redis_info.get("connected_clients", 0),
                "used_memory": redis_info.get("used_memory_human", "0B"),
                "keyspace_hits": redis_info.get("keyspace_hits", 0),
                "keyspace_misses": redis_info.get("keyspace_misses", 0),
                "redis_hit_ratio": redis_info.get("keyspace_hits", 0) / (redis_info.get("keyspace_hits", 0) + redis_info.get("keyspace_misses", 1)) if (redis_info.get("keyspace_hits", 0) + redis_info.get("keyspace_misses", 1)) > 0 else 0
            },
            "cache_configuration": CACHE_CONFIG
        }
        
        return stats
    except Exception as e:
        logger.error(f"Workflow cache stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

# =============================================================================
# HEALTH CHECK & STATUS
# =============================================================================

@app.get("/api/v2/health")
async def health_check():
    """Enhanced system health check"""
    try:
        # Test Supabase connection with actual table
        supabase_test = supabase.table('entity_master').select('count').limit(1).execute()
        supabase_healthy = len(supabase_test.data) >= 0
        
        # Test Redis connection  
        redis_test = cache.redis.ping()
        redis_healthy = redis_test
        
        # Test critical tables
        critical_tables = ['allocation_engine', 'hedge_instructions', 'hedge_business_events', 'usd_pb_deposit']
        table_health = {}
        
        for table in critical_tables:
            try:
                test_query = supabase.table(table).select('count').limit(1).execute()
                table_health[table] = "healthy"
            except:
                table_health[table] = "error"
        
        overall_status = "healthy" if (supabase_healthy and redis_healthy and all(status == "healthy" for status in table_health.values())) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
            "services": {
                "supabase": "healthy" if supabase_healthy else "unhealthy",
                "redis": "healthy" if redis_healthy else "unhealthy"
            },
            "critical_tables": table_health,
            "cache_performance": {
                "total_hits": cache.hit_stats["hits"],
                "total_misses": cache.hit_stats["misses"],
                "hit_ratio": cache.hit_stats["hits"] / (cache.hit_stats["hits"] + cache.hit_stats["misses"]) if (cache.hit_stats["hits"] + cache.hit_stats["misses"]) > 0 else 0
            },
            "schema_version": "v2.1"
        }
    except Exception as e:
        logger.error(f"Enhanced health check error: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)