"""
Smart Data Extraction Engine - Extracted for shared use
Intelligent data fetching with Redis cache integration
Supports parallel queries and targeted extraction
"""

import asyncio
import json
try:
    import redis
except ModuleNotFoundError:
    redis = None  # type: ignore
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from collections import defaultdict

# Import shared cache management and business logic
from .cache_manager import (
    get_hedge_cache_key, 
    get_cache_duration,
    HEDGE_QUERY_PATTERNS,
    OPTIMIZATION_STATS
)
from .business_logic import PromptAnalysisResult, PromptIntent


class SmartDataExtractor:
    """Intelligent data extraction with Redis caching and parallel queries"""
    
    def __init__(self, supabase_client, redis_client=None):
        self.supabase = supabase_client
        
        # Initialize Redis client or fallback to in-memory cache
        if redis_client:
            self.redis_client = redis_client
            self.redis_available = True
            self.memory_cache = None
        else:
            if redis is not None:
                try:
                    self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                    self.redis_client.ping()
                    self.redis_available = True
                    self.memory_cache = None
                except Exception:
                    self.redis_client = None
                    self.redis_available = False
                    # Use in-memory dict cache as fallback
                    self.memory_cache = {}
            else:
                # Redis library missing — fall back to in-memory cache
                self.redis_client = None
                self.redis_available = False
                self.memory_cache = {}
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_extraction_time = 0
        
    async def extract_data_for_prompt(self, 
                                    analysis_result: PromptAnalysisResult,
                                    use_cache: bool = True) -> Dict[str, Any]:
        """
        Main data extraction method - intelligently fetches data based on prompt analysis
        """
        start_time = time.time()
        
        # Build extraction parameters
        extraction_params = self._build_extraction_params(analysis_result)
        
        # Determine extraction strategy
        if analysis_result.data_scope == "minimal":
            extracted_data = await self._extract_minimal_data(extraction_params, use_cache)
        elif analysis_result.data_scope == "comprehensive":
            extracted_data = await self._extract_comprehensive_data(extraction_params, use_cache)
        else:  # targeted
            extracted_data = await self._extract_targeted_data(extraction_params, use_cache)
        
        # Add extraction metadata
        extraction_time = time.time() - start_time
        self.total_extraction_time += extraction_time
        
        extracted_data["_extraction_metadata"] = {
            "intent": analysis_result.intent.value,
            "confidence": analysis_result.confidence,
            "data_scope": analysis_result.data_scope,
            "tables_requested": len(analysis_result.required_tables),
            "tables_fetched": len([k for k in extracted_data.keys() if not k.startswith("_")]),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{(self.cache_hits/(max(self.cache_hits + self.cache_misses, 1))*100):.1f}%",
            "extraction_time_ms": round(extraction_time * 1000, 2),
            "redis_available": self.redis_available,
            "total_records": sum(len(v) if isinstance(v, list) else 0 for k, v in extracted_data.items() if not k.startswith("_")),
            "timestamp": datetime.now().isoformat()
        }
        
        return extracted_data
    
    def _build_extraction_params(self, analysis_result: PromptAnalysisResult) -> Dict[str, Any]:
        """Build extraction parameters from analysis result"""
        params = analysis_result.extracted_params.copy()
        
        # Add analysis metadata
        params.update({
            "intent": analysis_result.intent.value,
            "required_tables": analysis_result.required_tables,
            "instruction_type": analysis_result.instruction_type,
            "data_scope": analysis_result.data_scope
        })
        
        return params
    
    async def _extract_minimal_data(self, params: Dict[str, Any], use_cache: bool) -> Dict[str, Any]:
        """Extract minimal data for simple queries"""
        required_tables = params.get("required_tables", [])[:3]  # Limit to 3 tables max
        
        extraction_tasks = []
        for table in required_tables:
            task = self._fetch_table_with_cache(table, params, use_cache, limit=10)
            extraction_tasks.append(task)
        
        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        
        extracted_data = {}
        for i, table in enumerate(required_tables):
            if isinstance(results[i], Exception):
                extracted_data[table] = []
            else:
                extracted_data[table] = results[i]["data"]
                if results[i]["cache_hit"]:
                    self.cache_hits += 1
                else:
                    self.cache_misses += 1
        
        return extracted_data
    
    async def _extract_targeted_data(self, params: Dict[str, Any], use_cache: bool) -> Dict[str, Any]:
        """Extract targeted data based on specific parameters (currency, entity, etc.)"""
        required_tables = params.get("required_tables", [])
        
        # Build parallel extraction tasks with smart filtering
        extraction_tasks = []
        for table in required_tables:
            task = self._fetch_table_with_smart_filtering(table, params, use_cache)
            extraction_tasks.append(task)
        
        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        
        # Process results
        extracted_data = {}
        for i, table in enumerate(required_tables):
            if isinstance(results[i], Exception):
                extracted_data[table] = []
            else:
                extracted_data[table] = results[i]["data"]
                if results[i]["cache_hit"]:
                    self.cache_hits += 1
                else:
                    self.cache_misses += 1
        
        # Apply post-processing for hedge instructions
        if params.get("instruction_type") in ["I", "U", "R", "T"]:
            extracted_data = self._apply_hedge_instruction_processing(extracted_data, params)
        
        return extracted_data
    
    async def _extract_comprehensive_data(self, params: Dict[str, Any], use_cache: bool) -> Dict[str, Any]:
        """Extract comprehensive data for complex analysis"""
        required_tables = params.get("required_tables", [])
        
        # Add additional context tables for comprehensive analysis
        comprehensive_tables = list(set(required_tables + [
            "entity_master", "currency_configuration", "system_configuration"
        ]))
        
        extraction_tasks = []
        for table in comprehensive_tables:
            # No limits for comprehensive extraction
            task = self._fetch_table_with_smart_filtering(table, params, use_cache, comprehensive=True)
            extraction_tasks.append(task)
        
        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        
        extracted_data = {}
        for i, table in enumerate(comprehensive_tables):
            if isinstance(results[i], Exception):
                extracted_data[table] = []
            else:
                extracted_data[table] = results[i]["data"]
                if results[i]["cache_hit"]:
                    self.cache_hits += 1
                else:
                    self.cache_misses += 1
        
        return extracted_data
    
    async def _fetch_table_with_smart_filtering(self, 
                                              table: str, 
                                              params: Dict[str, Any], 
                                              use_cache: bool,
                                              comprehensive: bool = False,
                                              limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch table with intelligent filtering based on parameters"""
        
        # Build cache key
        cache_params = {k: v for k, v in params.items() if k in ["currency", "entity_id", "nav_type", "instruction_type"]}
        cache_key = get_hedge_cache_key(table, "system", cache_params)
        
        # Check cache first (Redis or memory)
        if use_cache:
            try:
                cached_data = None
                if self.redis_available:
                    cached_data = self.redis_client.get(cache_key)
                elif self.memory_cache is not None:
                    cached_data = self.memory_cache.get(cache_key)
                
                if cached_data:
                    # For memory cache, data is already a dict; for Redis it's JSON string
                    if self.redis_available:
                        data = json.loads(cached_data)
                    else:
                        data = cached_data
                    
                    self.cache_hits += 1
                    return {
                        "data": data,
                        "cache_hit": True,
                        "table": table
                    }
            except Exception as e:
                print(f"Cache read error for {table}: {e}")
        
        # Cache miss - build smart query
        query = self._build_smart_query(table, params, comprehensive, limit)
        
        try:
            result = query.execute()
            data = result.data or []
            
            # Cache the result (Redis or memory)
            if use_cache:
                try:
                    if self.redis_available:
                        cache_duration = get_cache_duration(table, 1)  # Use 30-user optimization
                        if cache_duration == 0:  # Permanent cache
                            self.redis_client.set(cache_key, json.dumps(data))
                        else:
                            self.redis_client.setex(cache_key, cache_duration, json.dumps(data))
                    elif self.memory_cache is not None:
                        # Store directly in memory cache (no expiration for simplicity)
                        self.memory_cache[cache_key] = data
                except Exception as e:
                    print(f"Cache write error for {table}: {e}")
            
            self.cache_misses += 1
            
            return {
                "data": data,
                "cache_hit": False,
                "table": table
            }
            
        except Exception as e:
            print(f"Database query error for {table}: {e}")
            return {
                "data": [],
                "cache_hit": False,
                "table": table
            }
    
    async def _fetch_table_with_cache(self, table: str, params: Dict[str, Any], use_cache: bool, limit: int = None):
        """Simple table fetch with cache - for backward compatibility"""
        return await self._fetch_table_with_smart_filtering(table, params, use_cache, limit=limit)
    
    def _build_smart_query(self, table: str, params: Dict[str, Any], comprehensive: bool = False, limit: Optional[int] = None):
        """Build intelligent Supabase query based on table and parameters"""
        query = self.supabase.table(table).select("*")

        # Apply smart filtering based on table type and available parameters
        currency = params.get("currency")
        entity_id = params.get("entity_id")
        nav_type = params.get("nav_type")
        instruction_type = params.get("instruction_type")
        order_id = params.get("order_id")

        # DEBUG: Log filtering parameters
        print(f"DEBUG: _build_smart_query table={table}, currency={currency}, params={params}")
        
        # Currency-based filtering
        if currency and table in [
            "entity_master", "position_nav_master", "hedge_instructions",
            "currency_configuration", "buffer_configuration", "allocation_engine",
            "threshold_configuration", "currency_rates"
        ]:
            if table == "entity_master":
                query = query.eq("currency_code", currency)
            elif table == "position_nav_master":
                query = query.eq("currency_code", currency)
            elif table == "hedge_instructions":
                query = query.eq("exposure_currency", currency)
            elif table == "currency_configuration":
                query = query.or_(f"currency_code.eq.{currency},proxy_currency.eq.{currency}")
            elif table in ["buffer_configuration", "allocation_engine"]:
                query = query.eq("currency_code", currency)
            elif table == "threshold_configuration":
                # Filter thresholds relevant to the currency (common schema uses currency_code)
                query = query.eq("currency_code", currency)
            elif table == "currency_rates":
                # Narrow to pairs involving the currency (supports both directions)
                # If your schema uses currency_pair (e.g., 'HKDUSD'), adjust to eq on that value.
                query = query.or_(f"from_ccy.eq.{currency},to_ccy.eq.{currency}")
        
        # Entity-based filtering
        if entity_id and table in ["position_nav_master", "allocation_engine", "hedge_business_events"]:
            query = query.eq("entity_id", entity_id)
        
        # NAV type filtering
        if nav_type and table in ["position_nav_master", "instruction_event_config"]:
            if table == "position_nav_master":
                query = query.eq("nav_type", nav_type)
            elif table == "instruction_event_config":
                query = query.in_("nav_type_applicable", ["Both", nav_type])
        
        # Order-specific filtering
        if order_id and table in ["hedge_instructions", "hedge_business_events", "gl_entries"]:
            query = query.eq("order_id", order_id)
        
        # Active record filtering
        if table in ["system_configuration", "buffer_configuration", "hedging_framework", 
                    "waterfall_logic_configuration", "hedge_instruments"]:
            query = query.eq("active_flag", "Y" if table != "hedge_instruments" else "Y")
        
        # Ordering and limits
        if not comprehensive:
            if table in ["hedge_instructions", "hedge_business_events"]:
                query = query.order("created_date", desc=True)
            elif table in ["currency_rates"]:
                query = query.order("rate_date", desc=True)
            elif table in ["allocation_engine"]:
                query = query.order("created_date", desc=True)
        
        # Apply limits
        if limit:
            query = query.limit(limit)
        elif not comprehensive:
            # Default limits for non-comprehensive queries
            default_limits = {
                "hedge_instructions": 50,
                "hedge_business_events": 50, 
                "allocation_engine": 100,
                "currency_rates": 20,
                "car_master": 10,
                "audit_trail": 20
            }
            if table in default_limits:
                query = query.limit(default_limits[table])
        
        return query
    
    def _apply_hedge_instruction_processing(self, extracted_data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply hedge instruction specific data processing similar to hedge_data.py"""
        
        # Get core data
        entities_rows = extracted_data.get("entity_master", [])
        positions_rows = extracted_data.get("position_nav_master", [])
        allocations_rows = extracted_data.get("allocation_engine", [])
        
        # Build entity lookup
        entity_info_lookup = {e.get("entity_id"): e for e in entities_rows if e.get("entity_id")}
        
        # Build allocation lookup
        allocation_lookup = defaultdict(list)
        for alloc in allocations_rows:
            eid = alloc.get("entity_id")
            if eid:
                allocation_lookup[eid].append(alloc)
        
        # Build hedge relationships lookup
        hedge_relationships = defaultdict(list)
        hedge_events = extracted_data.get("hedge_business_events", [])
        for event in hedge_events:
            eid = event.get("entity_id")
            if eid:
                hedge_relationships[eid].append(event)
        
        # Group positions by entity
        grouped_entities = defaultdict(list)
        for pos in positions_rows:
            eid = pos.get("entity_id")
            if not eid:
                continue
            
            # Get latest allocation
            latest_allocation = allocation_lookup.get(eid, [])[0] if allocation_lookup.get(eid) else {}
            
            # Calculate hedging state (simplified version of hedge_data.py logic)
            hedging_state = self._calculate_hedging_state(
                pos, latest_allocation, hedge_relationships.get(eid, [])
            )
            
            grouped_entities[eid].append({
                "nav_type": pos.get("nav_type", ""),
                "current_position": pos.get("current_position", 0),
                "hedging_state": hedging_state,
                "allocation_data": allocation_lookup.get(eid, []),
                "hedge_relationships": hedge_relationships.get(eid, [])
            })
        
        # Build entity groups
        entity_groups = []
        for eid, positions in grouped_entities.items():
            entity = entity_info_lookup.get(eid, {})
            entity_groups.append({
                "entity_id": eid,
                "entity_name": entity.get("entity_name", ""),
                "entity_type": entity.get("entity_type", ""),
                "exposure_currency": entity.get("currency_code", ""),
                "positions": positions
            })
        
        # Add structured data to extraction result
        extracted_data["_processed_entity_groups"] = entity_groups
        extracted_data["_processing_applied"] = "hedge_instruction_processing"
        
        return extracted_data
    
    def _calculate_hedging_state(self, position: Dict, allocation: Dict, hedge_relationships: List[Dict]) -> Dict:
        """Calculate hedging state for a position (simplified version)"""
        current_position = float(position.get("current_position", 0) or 0)
        hedged_position = float(allocation.get("hedged_position", 0) or 0)
        
        if current_position > 0:
            hedge_utilization_pct = (hedged_position / current_position) * 100.0
        else:
            hedge_utilization_pct = 0.0
        
        if hedged_position >= current_position:
            hedging_status = "Fully_Hedged"
        elif hedged_position > 0:
            hedging_status = "Partially_Hedged"
        else:
            hedging_status = "Available"
        
        return {
            "already_hedged_amount": hedged_position,
            "hedge_utilization_pct": round(hedge_utilization_pct, 2),
            "hedging_status": hedging_status,
            "active_hedge_count": len(hedge_relationships),
            "total_hedge_notional": sum(float(h.get("notional_amount", 0) or 0) for h in hedge_relationships)
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        
        cache_type = "redis" if self.redis_available else ("memory" if self.memory_cache is not None else "none")
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{(self.cache_hits/max(total_requests, 1)*100):.1f}%",
            "redis_available": self.redis_available,
            "cache_type": cache_type,
            "memory_cache_size": len(self.memory_cache) if self.memory_cache is not None else 0,
            "total_requests": total_requests,
            "avg_extraction_time_ms": round(self.total_extraction_time / max(total_requests, 1) * 1000, 2) if total_requests > 0 else 0,
            "optimization_target": OPTIMIZATION_STATS.get("cache_hit_rate_target", "98%")
        }
    
    def clear_cache_for_currency(self, currency: str):
        """Clear cache for specific currency"""
        if not self.redis_available:
            return
        
        try:
            # Find all cache keys related to this currency
            pattern = f"*{currency}*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
