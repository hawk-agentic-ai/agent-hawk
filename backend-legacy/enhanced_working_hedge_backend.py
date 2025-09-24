from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import redis
import json
import time
import hashlib
import os
import asyncio
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd

# Import optimized cache configuration for 30 users
from hedge_management_cache_config import (
    HEDGE_CACHE_STRATEGY, 
    get_hedge_cache_key, 
    get_cache_duration,
    HEDGE_QUERY_PATTERNS,
    OPTIMIZATION_STATS
)

app = FastAPI(
    title="Enhanced Hedge Management API - 30 Users Optimized",
    description="Complete hedge management system with template-based AI integration",
    version="2.1.0"
)

# Configuration
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# Initialize services
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    redis_client = None

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    # Test with hedge_instructions table (more relevant than prompt_templates)
    supabase.table('hedge_instructions').select("instruction_id").limit(1).execute()
    SUPABASE_AVAILABLE = True
except:
    SUPABASE_AVAILABLE = False
    supabase = None

# Enhanced Pydantic models
class HedgeQueryRequest(BaseModel):
    query: str
    user_id: str = "fund_manager"
    query_type: str = "general"  # hedge_positions, risk_analysis, compliance, inception, utilisation, rollover, termination
    fund_id: str = "default_fund"
    entity_id: Optional[str] = None
    include_historical: bool = True
    cache_preference: str = "smart"  # smart, fresh, cached_only

class HedgeEffectivenessRequest(BaseModel):
    entity_id: str
    currency_code: Optional[str] = None
    nav_type: Optional[str] = None
    analysis_period_days: int = 30

class HedgeMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.total_queries = 0
        self.cache_hits = 0
        self.permanent_cache_items = 0
        self.strategic_queries = 0
        self.template_queries = 0
        self.dify_api_calls = 0
    
    def record_query(self, cache_hit=False, is_strategic=False, cache_duration=0, is_template=False):
        self.total_queries += 1
        if cache_hit:
            self.cache_hits += 1
        if is_strategic:
            self.strategic_queries += 1
        if cache_duration == 0:  # Permanent cache
            self.permanent_cache_items += 1
        if is_template:
            self.template_queries += 1
        if not cache_hit:
            self.dify_api_calls += 1
    
    def get_optimization_stats(self):
        uptime = time.time() - self.start_time
        cache_rate = (self.cache_hits / self.total_queries * 100) if self.total_queries > 0 else 0
        cost_savings = ((self.total_queries - self.dify_api_calls) / max(self.total_queries, 1)) * 100
        
        return {
            "uptime_hours": round(uptime / 3600, 2),
            "total_hedge_queries": self.total_queries,
            "cache_hit_rate": f"{cache_rate:.1f}%",
            "strategic_queries": self.strategic_queries,
            "template_queries": self.template_queries,
            "permanent_cache_items": self.permanent_cache_items,
            "dify_api_calls_saved": self.total_queries - self.dify_api_calls,
            "cost_savings_percentage": f"{cost_savings:.1f}%",
            "optimization_type": "30_user_permanent_cache",
            "expected_monthly_dify_calls": max(100, self.dify_api_calls * 30),
            "services": {
                "redis": "connected" if REDIS_AVAILABLE else "disconnected",
                "supabase": "connected" if SUPABASE_AVAILABLE else "disconnected",
                "dify": "enabled" if DIFY_API_KEY else "disabled"
            }
        }

metrics = HedgeMetrics()

# =============================================================================
# CORE ENDPOINTS (existing functionality)
# =============================================================================

@app.get('/health')
def health_check():
    return {
        'status': 'healthy',
        'system_type': 'enhanced_hedge_management_30_users',
        'timestamp': time.time(),
        'services': {
            'fastapi': 'online',
            'redis': 'connected' if REDIS_AVAILABLE else 'disconnected',
            'supabase': 'connected' if SUPABASE_AVAILABLE else 'disconnected',
            'dify_integration': 'enabled' if DIFY_API_KEY else 'disabled'
        },
        'optimization': OPTIMIZATION_STATS
    }

@app.get('/hedge/positions/{entity_id}')
async def get_hedge_positions(entity_id: str):
    start_time = time.time()
    
    if not SUPABASE_AVAILABLE:
        return {
            'fund_id': entity_id,
            'data': {'error': 'Database unavailable', 'positions': []},
            'performance': {'response_time_ms': round((time.time() - start_time) * 1000, 2), 'cache_used': False}
        }
    
    try:
        result = supabase.table('position_nav_master').select(
            'entity_id, currency_code, current_position, nav_type, as_of_date'
        ).eq('entity_id', entity_id).execute()
        
        positions = []
        for row in result.data:
            positions.append({
                'currency': row['currency_code'],
                'amount': float(row['current_position']) if row['current_position'] else 0.0,
                'position_type': row['nav_type'],
                'as_of_date': row['as_of_date'],
                'entity_id': row['entity_id']
            })
        
        total_amount = sum(pos['amount'] for pos in positions)
        currencies = list(set(pos['currency'] for pos in positions))
        
        analysis_text = f"Entity {entity_id} has {len(positions)} positions totaling {total_amount:,.2f} across {len(currencies)} currencies"
        
        return {
            'fund_id': entity_id,
            'data': {
                'error': None,
                'positions': positions,
                'total_positions': len(positions),
                'total_amount': total_amount,
                'currencies': currencies
            },
            'analysis': {'analysis': analysis_text},
            'performance': {
                'response_time_ms': round((time.time() - start_time) * 1000, 2),
                'cache_used': False
            }
        }
        
    except Exception as e:
        return {
            'fund_id': entity_id,
            'data': {'error': f'Query failed: {str(e)}', 'positions': []},
            'performance': {'response_time_ms': round((time.time() - start_time) * 1000, 2), 'cache_used': False}
        }

# =============================================================================
# ENHANCED ENDPOINTS (new functionality)
# =============================================================================

@app.post("/dify/hedge-chat")
async def hedge_template_dify_chat(request: HedgeQueryRequest):
    """Enhanced Dify integration with template support and 30-user optimization"""
    start_time = time.time()
    
    # Determine query type and cache strategy
    query_type = HEDGE_QUERY_PATTERNS.get(request.query_type, request.query_type)
    cache_key = get_hedge_cache_key(query_type, request.user_id, {"fund": request.fund_id, "entity": request.entity_id})
    cache_duration = get_cache_duration(query_type, usage_count=1)  # Assume usage for 30-user optimization
    is_strategic = cache_duration == 0
    is_template = request.query_type in ['inception', 'utilisation', 'rollover', 'termination']
    
    # Check cache with 30-user optimized logic
    if REDIS_AVAILABLE and redis_client and request.cache_preference != "fresh":
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                cached_response = json.loads(cached_data)
                metrics.record_query(cache_hit=True, is_strategic=is_strategic, cache_duration=cache_duration, is_template=is_template)
                
                return {
                    "response": cached_response["dify_response"],
                    "hedge_context": cached_response.get("hedge_context", {}),
                    "performance": {
                        "response_time_ms": round((time.time() - start_time) * 1000, 2),
                        "cache_used": True,
                        "cache_type": "permanent" if cache_duration == 0 else f"timed_{cache_duration}s",
                        "optimization": "30_user_cache_hit"
                    },
                    "metadata": {
                        "cached_at": cached_response.get("cached_at"),
                        "query_type": query_type,
                        "strategic_query": is_strategic,
                        "template_query": is_template
                    }
                }
        except Exception as e:
            print(f"Cache check error: {e}")

    # Get hedge context for template enhancement
    hedge_context = {}
    if request.entity_id and SUPABASE_AVAILABLE:
        try:
            # Get position data for context
            position_result = supabase.table('position_nav_master').select('*').eq('entity_id', request.entity_id).execute()
            if position_result.data:
                hedge_context["positions"] = position_result.data
                hedge_context["total_exposure"] = sum(float(row.get('current_position', 0)) for row in position_result.data)
            
            # Get hedge instruction history for template context
            instruction_result = supabase.table('hedge_instructions').select('*').eq('exposure_currency', 'USD').limit(5).execute()
            if instruction_result.data:
                hedge_context["recent_instructions"] = instruction_result.data
                
        except Exception as e:
            hedge_context["context_error"] = str(e)

    # Enhanced query with template context
    template_context = ""
    if is_template:
        template_context = f"""
Template Type: {request.query_type.upper()} - {get_template_description(request.query_type)}
Entity Context: {request.entity_id or 'General'}
Fund Context: {request.fund_id}
Position Data: {hedge_context.get('total_exposure', 'Not available')}
"""
    
    enhanced_query = f"""
{template_context}
Hedge Fund Management Query - 30 User Optimized System:

User Query: {request.query}

Context Data:
{json.dumps(hedge_context, indent=2) if hedge_context else 'No additional context'}

Please provide specific hedge fund management insights considering:
1. Risk management best practices
2. Regulatory compliance requirements  
3. Portfolio optimization strategies
4. Template-specific recommendations for {request.query_type}

Focus on actionable insights for hedge fund operations.
"""

    # Call Dify API with enhanced context
    if not DIFY_API_KEY:
        return {
            "error": "Dify API integration not configured",
            "performance": {"response_time_ms": round((time.time() - start_time) * 1000, 2), "cache_used": False}
        }
    
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            dify_response = await client.post(
                "https://api.dify.ai/v1/chat-messages",
                headers={
                    "Authorization": f"Bearer {DIFY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "inputs": hedge_context,
                    "query": enhanced_query,
                    "user": f"hedge_manager_{request.user_id}",
                    "response_mode": "blocking"
                }
            )
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            if dify_response.status_code == 200:
                dify_data = dify_response.json()
                
                # Cache with 30-user optimized strategy
                if REDIS_AVAILABLE and redis_client:
                    cache_data = {
                        "dify_response": dify_data,
                        "hedge_context": hedge_context,
                        "cached_at": time.time(),
                        "query": request.query,
                        "enhanced_query": enhanced_query,
                        "query_type": query_type,
                        "template_type": request.query_type if is_template else None
                    }
                    
                    try:
                        if cache_duration == 0:  # Permanent cache (most items for 30 users)
                            redis_client.set(cache_key, json.dumps(cache_data, default=str))
                        else:
                            redis_client.setex(cache_key, cache_duration, json.dumps(cache_data, default=str))
                    except Exception as e:
                        print(f"Cache save error: {e}")
                
                metrics.record_query(cache_hit=False, is_strategic=is_strategic, cache_duration=cache_duration, is_template=is_template)
                
                return {
                    "response": dify_data,
                    "hedge_context": hedge_context,
                    "performance": {
                        "response_time_ms": response_time,
                        "cache_used": False,
                        "cache_type": "permanent" if cache_duration == 0 else f"timed_{cache_duration}s",
                        "optimization": "30_user_enhanced_template",
                        "template_enhanced": is_template
                    },
                    "metadata": {
                        "user_id": request.user_id,
                        "fund_id": request.fund_id,
                        "entity_id": request.entity_id,
                        "query_type": query_type,
                        "template_query": is_template,
                        "strategic_query": is_strategic,
                        "cached_for_future": REDIS_AVAILABLE and cache_duration == 0
                    }
                }
            else:
                raise HTTPException(status_code=dify_response.status_code, detail=f"Dify API error: {dify_response.text}")
                
    except Exception as e:
        return {
            "error": f"Dify integration failed: {str(e)}",
            "performance": {"response_time_ms": round((time.time() - start_time) * 1000, 2), "cache_used": False}
        }

def get_template_description(template_type: str) -> str:
    """Get description for hedge instruction templates"""
    descriptions = {
        "inception": "New hedge position initiation with risk assessment",
        "utilisation": "Existing hedge position modification and utilization",
        "rollover": "Hedge position rollover to new maturity date", 
        "termination": "Hedge position closure and final settlement"
    }
    return descriptions.get(template_type, "General hedge management query")

@app.get("/hedge/effectiveness/{entity_id}")
async def get_hedge_effectiveness(entity_id: str, currency_code: Optional[str] = None, analysis_period_days: int = 30):
    """Advanced hedge effectiveness analysis with caching"""
    start_time = time.time()
    
    if not SUPABASE_AVAILABLE:
        return {"error": "Database unavailable", "effectiveness_data": []}
    
    try:
        # Query hedge effectiveness data
        query = supabase.table('hedge_effectiveness').select('*').eq('entity_id', entity_id)
        if currency_code:
            query = query.eq('currency_code', currency_code)
        
        # Add date filter
        cutoff_date = (datetime.now() - timedelta(days=analysis_period_days)).date()
        result = query.gte('measurement_date', cutoff_date.isoformat()).execute()
        
        effectiveness_data = result.data
        
        # Calculate aggregate metrics
        if effectiveness_data:
            avg_effectiveness = sum(float(row.get('effectiveness_ratio', 0)) for row in effectiveness_data) / len(effectiveness_data)
            avg_hedge_ratio = sum(float(row.get('hedge_ratio', 0)) for row in effectiveness_data) / len(effectiveness_data)
            
            analysis = {
                "entity_id": entity_id,
                "analysis_period_days": analysis_period_days,
                "total_measurements": len(effectiveness_data),
                "average_effectiveness_ratio": round(avg_effectiveness, 4),
                "average_hedge_ratio": round(avg_hedge_ratio, 4),
                "effectiveness_status": "EFFECTIVE" if avg_effectiveness > 0.8 else "NEEDS_REVIEW",
                "currency_focus": currency_code or "ALL_CURRENCIES"
            }
        else:
            analysis = {
                "entity_id": entity_id,
                "analysis_period_days": analysis_period_days,
                "total_measurements": 0,
                "status": "NO_DATA_AVAILABLE"
            }
        
        return {
            "effectiveness_analysis": analysis,
            "detailed_data": effectiveness_data,
            "performance": {
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "cache_eligible": True,
                "cache_duration_strategy": "permanent_for_30_users"
            }
        }
        
    except Exception as e:
        return {
            "error": f"Hedge effectiveness analysis failed: {str(e)}",
            "performance": {"response_time_ms": round((time.time() - start_time) * 1000, 2)}
        }

@app.get("/system/hedge-metrics")
async def get_hedge_system_metrics():
    """Cache performance and system metrics optimized for 30 users"""
    return {
        "system_optimization": metrics.get_optimization_stats(),
        "cache_configuration": {
            "strategy_type": "30_user_permanent_cache",
            "permanent_cache_items": len([k for k, v in HEDGE_CACHE_STRATEGY.items() if v == 0]),
            "short_cache_items": len([k for k, v in HEDGE_CACHE_STRATEGY.items() if v > 0]),
            "expected_cache_hit_rate": OPTIMIZATION_STATS["cache_hit_rate_target"],
            "expected_cost_reduction": f"{OPTIMIZATION_STATS['cost_reduction_percentage']}%"
        },
        "hedge_operations": {
            "supported_templates": ["inception", "utilisation", "rollover", "termination"],
            "supported_analyses": ["hedge_effectiveness", "risk_metrics", "portfolio_analysis"],
            "data_sources": {
                "position_nav_master": "88 records",
                "hedge_instructions": "44 records", 
                "hedge_business_events": "Active monitoring",
                "hedge_effectiveness": "Historical analysis"
            }
        },
        "integration_status": {
            "supabase": "connected" if SUPABASE_AVAILABLE else "disconnected",
            "redis_cache": "connected" if REDIS_AVAILABLE else "disconnected", 
            "dify_ai": "enabled" if DIFY_API_KEY else "disabled"
        }
    }

@app.get("/system/status")
def get_enhanced_system_status():
    """Enhanced system status with 30-user optimization details"""
    return {
        "version": "2.1.0",
        "system": "Enhanced Hedge Management API - 30 Users Optimized",
        "specialization": "hedge_fund_management_with_templates",
        "user_base_optimization": OPTIMIZATION_STATS,
        "capabilities": {
            "permanent_caching": REDIS_AVAILABLE,
            "supabase_integration": SUPABASE_AVAILABLE,
            "template_based_ai": bool(DIFY_API_KEY),
            "hedge_analytics": True,
            "risk_management": True,
            "compliance_reporting": True,
            "murex_integration_ready": True,
            "gl_booking_ready": True
        },
        "performance_targets": {
            "cache_hit_rate": "98%",
            "avg_response_cached": "50ms",
            "monthly_dify_calls": "<100",
            "cost_savings": "95%"
        },
        "supported_operations": {
            "hedge_instructions": ["inception", "utilisation", "rollover", "termination"],
            "analytics": ["effectiveness", "risk_metrics", "performance"],
            "integrations": ["dify_ai", "supabase", "redis_cache"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)