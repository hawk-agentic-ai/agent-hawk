import asyncio
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor
import re
import hashlib

from supabase_client import get_supabase

class PromptAnalyzer:
    """Analyzes user prompts to determine data requirements"""
    
    @staticmethod
    def analyze_prompt_requirements(prompt_text: str) -> Dict[str, Any]:
        """Extract data requirements from prompt text"""
        prompt_lower = prompt_text.lower()
        
        # Extract entities mentioned
        entities = PromptAnalyzer._extract_entities(prompt_text)
        
        # Extract currencies
        currencies = PromptAnalyzer._extract_currencies(prompt_text)
        
        # Extract date ranges
        date_range = PromptAnalyzer._extract_date_range(prompt_text)
        
        # Extract hedge types/methods
        hedge_types = PromptAnalyzer._extract_hedge_methods(prompt_text)
        
        # Extract NAV types
        nav_types = PromptAnalyzer._extract_nav_types(prompt_text)
        
        # Estimate data scope needed
        data_scope = PromptAnalyzer._estimate_data_scope(prompt_text)
        
        return {
            "entities": entities,
            "currencies": currencies,
            "date_range": date_range,
            "hedge_types": hedge_types,
            "nav_types": nav_types,
            "data_scope": data_scope,
            "requires_recent_data": "recent" in prompt_lower or "latest" in prompt_lower,
            "requires_historical": "history" in prompt_lower or "past" in prompt_lower,
            "requires_config": "configuration" in prompt_lower or "setup" in prompt_lower,
            "requires_analysis": "analyze" in prompt_lower or "calculate" in prompt_lower
        }
    
    @staticmethod
    def _extract_entities(text: str) -> List[str]:
        """Extract entity names/IDs from text"""
        # Look for entity patterns
        entity_patterns = [
            r'\b[A-Z]{2,6}\d{2,4}\b',  # Entity codes like ABC123
            r'\bentity[_\s]*(?:id|name)[_\s]*:?\s*([A-Za-z0-9]+)',
            r'\b(?:fund|entity|portfolio)\s+([A-Z][A-Za-z\s]+)',
        ]
        
        entities = []
        for pattern in entity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)
        
        return list(set(entities))
    
    @staticmethod
    def _extract_currencies(text: str) -> List[str]:
        """Extract currency codes from text"""
        # Common currency patterns
        currency_pattern = r'\b(USD|EUR|GBP|JPY|SGD|AUD|CHF|CAD|HKD|CNY|INR|KRW|THB|MYR|PHP|TWD|NZD)\b'
        currencies = re.findall(currency_pattern, text, re.IGNORECASE)
        
        # Also look for currency code patterns
        currency_code_pattern = r'\b[A-Z]{3}\b'
        potential_currencies = re.findall(currency_code_pattern, text)
        
        # Filter to common currencies
        known_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'SGD', 'AUD', 'CHF', 'CAD', 'HKD', 'CNY'}
        currencies.extend([c for c in potential_currencies if c in known_currencies])
        
        return list(set([c.upper() for c in currencies]))
    
    @staticmethod
    def _extract_date_range(text: str) -> Dict[str, Any]:
        """Extract date range from text"""
        date_info = {"days_back": 30, "specific_dates": []}
        
        # Look for relative dates
        if re.search(r'\b(?:last|past)\s+(\d+)\s+days?\b', text, re.IGNORECASE):
            match = re.search(r'\b(?:last|past)\s+(\d+)\s+days?\b', text, re.IGNORECASE)
            date_info["days_back"] = int(match.group(1))
        elif re.search(r'\b(?:last|past)\s+week\b', text, re.IGNORECASE):
            date_info["days_back"] = 7
        elif re.search(r'\b(?:last|past)\s+month\b', text, re.IGNORECASE):
            date_info["days_back"] = 30
        elif re.search(r'\b(?:last|past)\s+quarter\b', text, re.IGNORECASE):
            date_info["days_back"] = 90
        elif re.search(r'\b(?:last|past)\s+year\b', text, re.IGNORECASE):
            date_info["days_back"] = 365
        
        # Look for specific dates
        date_patterns = [
            r'\b(\d{4}-\d{2}-\d{2})\b',
            r'\b(\d{2}/\d{2}/\d{4})\b',
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            date_info["specific_dates"].extend(matches)
        
        return date_info
    
    @staticmethod
    def _extract_hedge_methods(text: str) -> List[str]:
        """Extract hedge methods/types from text"""
        hedge_patterns = [
            r'\b(cash flow hedge|fair value hedge|net investment hedge)\b',
            r'\b(COH|MTM|NIH)\b',
            r'\b(forward|swap|option|future)\b',
        ]
        
        hedge_types = []
        for pattern in hedge_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            hedge_types.extend(matches)
        
        return list(set([h.upper() for h in hedge_types]))
    
    @staticmethod
    def _extract_nav_types(text: str) -> List[str]:
        """Extract NAV types from text"""
        nav_pattern = r'\b(COI|RE|REIT|Both)\b'
        nav_types = re.findall(nav_pattern, text, re.IGNORECASE)
        return list(set([n.upper() for n in nav_types]))
    
    @staticmethod
    def _estimate_data_scope(text: str) -> str:
        """Estimate how much data is needed based on prompt complexity"""
        text_lower = text.lower()
        
        # High complexity indicators
        high_complexity = [
            'comprehensive', 'detailed', 'full', 'complete', 'all',
            'analysis', 'report', 'dashboard', 'summary'
        ]
        
        # Medium complexity
        medium_complexity = [
            'current', 'latest', 'recent', 'status', 'position'
        ]
        
        if any(word in text_lower for word in high_complexity):
            return "comprehensive"
        elif any(word in text_lower for word in medium_complexity):
            return "focused"
        else:
            return "minimal"


class OptimizedHedgeDataService:
    """Optimized hedge data fetching with parallel queries and smart filtering"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.executor = ThreadPoolExecutor(max_workers=8)
    
    async def fetch_complete_hedge_data_optimized(
        self,
        exposure_currency: str,
        hedge_method: str,
        hedge_amount_order: float,
        order_id: str,
        prompt_text: str = "",
        nav_type: str = None,
        currency_type: str = None
    ) -> Dict[str, Any]:
        """Optimized data fetching with parallel execution and smart filtering"""
        
        try:
            # Step 1: Analyze prompt to understand requirements
            requirements = PromptAnalyzer.analyze_prompt_requirements(prompt_text)
            
            # Step 2: Execute core queries in parallel
            core_data = await self._fetch_core_data_parallel(
                exposure_currency, nav_type, currency_type, requirements
            )
            
            # Step 3: Extract entity IDs from core data
            entity_ids = self._extract_entity_ids(core_data)
            
            # Step 4: Fetch detailed data in parallel (filtered by requirements)
            detail_data = await self._fetch_detail_data_parallel(
                entity_ids, exposure_currency, requirements
            )
            
            # Step 5: Fetch configuration data (cached where possible)
            config_data = await self._fetch_config_data_parallel(
                exposure_currency, hedge_method, nav_type, currency_type, requirements
            )
            
            # Step 6: Structure optimized response
            return self._structure_optimized_response(
                core_data, detail_data, config_data, requirements
            )
            
        except Exception as e:
            print(f"Optimized Data Fetch Error: {str(e)}")
            return {"error": str(e), "entity_groups": [], "optimization_applied": True}
    
    async def _fetch_core_data_parallel(
        self, 
        exposure_currency: str, 
        nav_type: str, 
        currency_type: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch core data (entities, positions, currency config) in parallel"""
        
        async def fetch_entities():
            query = self.supabase.table("entity_master").select("*, currency_configuration(currency_type)")
            
            if currency_type:
                query = query.eq("currency_code", exposure_currency).eq("currency_configuration.currency_type", currency_type)
            else:
                query = query.eq("currency_code", exposure_currency)
            
            # Filter by specific entities if mentioned in prompt
            if requirements["entities"]:
                # Try to match entity names or IDs
                entity_filter = " or ".join([f"entity_name.ilike.%{entity}%" for entity in requirements["entities"]])
                query = query.or_(entity_filter)
            
            return query.execute()
        
        async def fetch_positions():
            query = self.supabase.table("position_nav_master").select("*").eq("currency_code", exposure_currency)
            
            if nav_type:
                query = query.eq("nav_type", nav_type)
            elif requirements["nav_types"]:
                query = query.in_("nav_type", requirements["nav_types"])
            
            return query.execute()
        
        async def fetch_currency_config():
            return self.supabase.table("currency_configuration").select("*").or_(
                f"currency_code.eq.{exposure_currency},proxy_currency.eq.{exposure_currency}"
            ).execute()
        
        # Execute in parallel
        results = await asyncio.gather(
            asyncio.get_event_loop().run_in_executor(self.executor, lambda: fetch_entities()),
            asyncio.get_event_loop().run_in_executor(self.executor, lambda: fetch_positions()),
            asyncio.get_event_loop().run_in_executor(self.executor, lambda: fetch_currency_config())
        )
        
        return {
            "entities": getattr(results[0], "data", []) or [],
            "positions": getattr(results[1], "data", []) or [],
            "currency_config": getattr(results[2], "data", []) or []
        }
    
    async def _fetch_detail_data_parallel(
        self,
        entity_ids: List[str],
        exposure_currency: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch detailed data in parallel with smart limits based on requirements"""
        
        # Adjust limits based on data scope requirements
        limit_config = {
            "comprehensive": {"allocations": 50, "instructions": 30, "events": 30},
            "focused": {"allocations": 20, "instructions": 15, "events": 15},
            "minimal": {"allocations": 10, "instructions": 5, "events": 10}
        }
        
        limits = limit_config.get(requirements["data_scope"], limit_config["focused"])
        
        # Calculate date cutoff
        days_back = requirements["date_range"]["days_back"]
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        async def fetch_allocations():
            query = (self.supabase.table("allocation_engine")
                    .select("*")
                    .eq("currency_code", exposure_currency)
                    .order("created_date", desc=True)
                    .limit(limits["allocations"]))
            
            if requirements["requires_recent_data"]:
                query = query.gte("created_date", cutoff_date)
            
            return query.execute()
        
        async def fetch_hedge_instructions():
            query = (self.supabase.table("hedge_instructions")
                    .select("*")
                    .eq("exposure_currency", exposure_currency)
                    .order("instruction_date", desc=True)
                    .limit(limits["instructions"]))
            
            if requirements["requires_recent_data"]:
                query = query.gte("instruction_date", cutoff_date)
            
            return query.execute()
        
        async def fetch_hedge_events():
            query = self.supabase.table("hedge_business_events").select("*")
            
            if entity_ids:
                query = query.in_("entity_id", entity_ids[:20])  # Limit entity scope
            
            query = query.order("trade_date", desc=True).limit(limits["events"])
            
            if requirements["requires_recent_data"]:
                query = query.gte("trade_date", cutoff_date)
            
            return query.execute()
        
        async def fetch_car_master():
            query = (self.supabase.table("car_master")
                    .select("*")
                    .eq("currency_code", exposure_currency)
                    .order("reporting_date", desc=True)
                    .limit(20))
            
            if requirements["requires_recent_data"]:
                query = query.gte("reporting_date", cutoff_date)
            
            return query.execute()
        
        # Execute in parallel
        results = await asyncio.gather(
            asyncio.get_event_loop().run_in_executor(self.executor, lambda: fetch_allocations()),
            asyncio.get_event_loop().run_in_executor(self.executor, lambda: fetch_hedge_instructions()),
            asyncio.get_event_loop().run_in_executor(self.executor, lambda: fetch_hedge_events()),
            asyncio.get_event_loop().run_in_executor(self.executor, lambda: fetch_car_master())
        )
        
        return {
            "allocations": getattr(results[0], "data", []) or [],
            "hedge_instructions": getattr(results[1], "data", []) or [],
            "hedge_events": getattr(results[2], "data", []) or [],
            "car_master": getattr(results[3], "data", []) or []
        }
    
 # ... previous code ...

    async def _fetch_core_data_parallel(
        self, 
        exposure_currency: str, 
        nav_type: str, 
        currency_type: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch core data (entities, positions, currency config) in parallel"""

        async def fetch_entities():
            query = self.supabase.table("entity_master").select("*, currency_configuration(currency_type)")
            if currency_type:
                query = query.eq("currency_code", exposure_currency).eq("currency_configuration.currency_type", currency_type)
            else:
                query = query.eq("currency_code", exposure_currency)
            if requirements["entities"]:
                entity_filter = " or ".join([f"entity_name.ilike.%{entity}%" for entity in requirements["entities"]])
                query = query.or_(entity_filter)
            return query.execute()

        async def fetch_positions():
            query = self.supabase.table("position_nav_master").select("*").eq("currency_code", exposure_currency)
            if nav_type:
                query = query.eq("nav_type", nav_type)
            elif requirements["nav_types"]:
                query = query.in_("nav_type", requirements["nav_types"])
            return query.execute()

        async def fetch_currency_config():
            return self.supabase.table("currency_configuration").select("*").or_(
                f"currency_code.eq.{exposure_currency},proxy_currency.eq.{exposure_currency}"
            ).execute()

        results = await asyncio.gather(
            fetch_entities(),
            fetch_positions(),
            fetch_currency_config()
        )

        return {
            "entities": getattr(results[0], "data", []) or [],
            "positions": getattr(results[1], "data", []) or [],
            "currency_config": getattr(results[2], "data", []) or []
        }

    async def _fetch_detail_data_parallel(
        self,
        entity_ids: List[str],
        exposure_currency: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch detailed data in parallel with smart limits based on requirements"""

        # ... (define fetch_allocations, fetch_hedge_instructions, etc., as async)

        async def fetch_allocations():
            query = (self.supabase.table("allocation_engine")
                    .select("*")
                    .eq("currency_code", exposure_currency)
                    .order("created_date", desc=True)
                    .limit(limits["allocations"]))
            if requirements["requires_recent_data"]:
                query = query.gte("created_date", cutoff_date)
            return query.execute()

        async def fetch_hedge_instructions():
            query = (self.supabase.table("hedge_instructions")
                    .select("*")
                    .eq("exposure_currency", exposure_currency)
                    .order("instruction_date", desc=True)
                    .limit(limits["instructions"]))
            if requirements["requires_recent_data"]:
                query = query.gte("instruction_date", cutoff_date)
            return query.execute()

        async def fetch_hedge_events():
            query = self.supabase.table("hedge_business_events").select("*")
            if entity_ids:
                query = query.in_("entity_id", entity_ids[:20])
            query = query.order("trade_date", desc=True).limit(limits["events"])
            if requirements["requires_recent_data"]:
                query = query.gte("trade_date", cutoff_date)
            return query.execute()

        async def fetch_car_master():
            query = (self.supabase.table("car_master")
                    .select("*")
                    .eq("currency_code", exposure_currency)
                    .order("reporting_date", desc=True)
                    .limit(20))
            if requirements["requires_recent_data"]:
                query = query.gte("reporting_date", cutoff_date)
            return query.execute()

        results = await asyncio.gather(
            fetch_allocations(),
            fetch_hedge_instructions(),
            fetch_hedge_events(),
            fetch_car_master()
        )

        return {
            "allocations": getattr(results[0], "data", []) or [],
            "hedge_instructions": getattr(results[1], "data", []) or [],
            "hedge_events": getattr(results[2], "data", []) or [],
            "car_master": getattr(results[3], "data", []) or []
        }

    async def _fetch_config_data_parallel(
        self,
        exposure_currency: str,
        hedge_method: str,
        nav_type: str,
        currency_type: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch configuration data in parallel (with caching for static data)"""

        async def fetch_buffer_config():
            return (self.supabase.table("buffer_configuration")
                   .select("*")
                   .eq("currency_code", exposure_currency)
                   .eq("active_flag", "Y")
                   .execute())

        async def fetch_waterfall_config():
            return (self.supabase.table("waterfall_logic_configuration")
                   .select("*")
                   .eq("active_flag", "Y")
                   .order("waterfall_type")
                   .order("priority_level")
                   .execute())

        async def fetch_overlay_config():
            return (self.supabase.table("overlay_configuration")
                   .select("*")
                   .eq("currency_code", exposure_currency)
                   .eq("active_flag", "Y")
                   .execute())

        async def fetch_hedging_framework():
            return (self.supabase.table("hedging_framework")
                   .select("*")
                   .eq("currency_code", exposure_currency)
                   .eq("active_flag", "Y")
                   .execute())

        async def fetch_hedge_instruments():
            today = date.today().isoformat()
            pair1 = f"{exposure_currency}SGD"
            pair2 = f"SGD{exposure_currency}"

            query = (self.supabase.table("hedge_instruments")
                    .select("*")
                    .eq("active_flag", "Y")
                    .lte("effective_date", today))

            or_clause = (f"base_currency.eq.{exposure_currency},"
                        f"quote_currency.eq.{exposure_currency},"
                        f"currency_pair.in.({pair1},{pair2})")
            query = query.or_(or_clause)

            if currency_type:
                query = query.eq("currency_classification", currency_type)

            if nav_type:
                query = query.in_("nav_type_applicable", ["Both", nav_type])

            if hedge_method:
                query = query.in_("accounting_method_supported", ["Both", hedge_method])

            return query.order("effective_date", desc=True).execute()

        config_queries = []

        if requirements["requires_config"] or requirements["data_scope"] == "comprehensive":
            config_queries = [
                fetch_buffer_config(),
                fetch_waterfall_config(),
                fetch_overlay_config(),
                fetch_hedging_framework(),
                fetch_hedge_instruments()
            ]
        else:
            config_queries = [
                fetch_hedging_framework(),
                fetch_hedge_instruments()
            ]

        results = await asyncio.gather(*config_queries)

        if len(results) == 5:
            return {
                "buffer_config": getattr(results[0], "data", []) or [],
                "waterfall_config": getattr(results[1], "data", []) or [],
                "overlay_config": getattr(results[2], "data", []) or [],
                "hedging_framework": getattr(results[3], "data", []) or [],
                "hedge_instruments": getattr(results[4], "data", []) or []
            }
        else:
            return {
                "buffer_config": [],
                "waterfall_config": [],
                "overlay_config": [],
                "hedging_framework": getattr(results[0], "data", []) or [],
                "hedge_instruments": getattr(results[1], "data", []) or []
            }
    
    def _extract_entity_ids(self, core_data: Dict[str, Any]) -> List[str]:
        """Extract entity IDs from core data"""
        entity_ids = set()
        
        # From entities
        for entity in core_data["entities"]:
            if entity.get("entity_id"):
                entity_ids.add(entity["entity_id"])
        
        # From positions
        for position in core_data["positions"]:
            if position.get("entity_id"):
                entity_ids.add(position["entity_id"])
        
        return list(entity_ids)
    
    def _structure_optimized_response(
        self,
        core_data: Dict[str, Any],
        detail_data: Dict[str, Any],
        config_data: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Structure the response with optimization metadata"""
        
        # Process entity groups (similar to original but with optimized data)
        entity_groups = self._process_entity_groups(core_data, detail_data, config_data)
        
        # Structure response based on requirements
        response = {
            "entity_groups": entity_groups,
            "optimization_applied": True,
            "optimization_metadata": {
                "prompt_analysis": requirements,
                "data_scope": requirements["data_scope"],
                "entities_processed": len(core_data["entities"]),
                "positions_processed": len(core_data["positions"]),
                "allocations_included": len(detail_data["allocations"]),
                "instructions_included": len(detail_data["hedge_instructions"]),
                "events_included": len(detail_data["hedge_events"]),
                "execution_mode": "parallel_optimized"
            }
        }
        
        # Add configuration data based on requirements
        if requirements["requires_config"] or requirements["data_scope"] == "comprehensive":
            response["stage_1a_config"] = {
                "buffer_configuration": config_data["buffer_config"],
                "waterfall_logic": self._split_waterfall_config(config_data["waterfall_config"]),
                "overlay_configuration": config_data["overlay_config"],
                "hedging_framework": config_data["hedging_framework"]
            }
        
        # Add detailed data
        response["stage_1b_data"] = {
            "current_allocations": detail_data["allocations"],
            "hedge_instructions_history": detail_data["hedge_instructions"],
            "active_hedge_events": detail_data["hedge_events"],
            "car_master_data": detail_data["car_master"]
        }
        
        # Add instruments
        response["stage_2_config"] = {
            "hedge_instruments": config_data["hedge_instruments"]
        }
        
        return response
    
    def _process_entity_groups(
        self,
        core_data: Dict[str, Any],
        detail_data: Dict[str, Any],
        config_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process entity groups with optimized data structure"""
        
        # Create lookups for efficient processing
        entity_lookup = {e["entity_id"]: e for e in core_data["entities"] if e.get("entity_id")}
        
        # Group positions by entity
        entity_positions = defaultdict(list)
        for pos in core_data["positions"]:
            entity_id = pos.get("entity_id")
            if entity_id:
                entity_positions[entity_id].append(pos)
        
        # Create allocation lookup
        allocation_lookup = defaultdict(list)
        for alloc in detail_data["allocations"]:
            entity_id = alloc.get("entity_id")
            if entity_id:
                allocation_lookup[entity_id].append(alloc)
        
        # Create hedge events lookup
        hedge_events_lookup = defaultdict(list)
        for event in detail_data["hedge_events"]:
            entity_id = event.get("entity_id")
            if entity_id:
                hedge_events_lookup[entity_id].append(event)
        
        # Process entity groups
        entity_groups = []
        for entity_id, positions in entity_positions.items():
            entity = entity_lookup.get(entity_id, {})
            entity_allocations = allocation_lookup.get(entity_id, [])
            entity_hedge_events = hedge_events_lookup.get(entity_id, [])
            
            processed_positions = []
            for pos in positions:
                latest_allocation = entity_allocations[0] if entity_allocations else {}
                hedging_state = self._calculate_hedging_state(pos, latest_allocation, entity_hedge_events)
                
                processed_positions.append({
                    "nav_type": pos.get("nav_type", ""),
                    "current_position": pos.get("current_position", 0),
                    "computed_total_nav": pos.get("computed_total_nav", 0),
                    "hedging_state": hedging_state,
                    "allocation_data": entity_allocations[:5],  # Limit to recent 5
                    "hedge_relationships": entity_hedge_events[:10]  # Limit to recent 10
                })
            
            entity_groups.append({
                "entity_id": entity_id,
                "entity_name": entity.get("entity_name", ""),
                "entity_type": entity.get("entity_type", ""),
                "exposure_currency": entity.get("currency_code", ""),
                "positions": processed_positions
            })
        
        return entity_groups
    
    def _calculate_hedging_state(self, position: Dict, allocation: Dict, hedge_events: List[Dict]) -> Dict:
        """Calculate hedging state with optimized logic"""
        current_position = float(position.get("current_position", 0) or 0)
        hedged_position = float(allocation.get("hedged_position", 0) or 0)
        
        hedge_utilization_pct = 0.0
        if current_position > 0:
            hedge_utilization_pct = (hedged_position / current_position) * 100.0
        
        return {
            "already_hedged_amount": hedged_position,
            "hedge_utilization_pct": round(hedge_utilization_pct, 2),
            "hedging_status": "Fully_Hedged" if hedged_position >= current_position else "Available",
            "active_hedge_count": len(hedge_events),
            "optimization_note": "Calculated with optimized algorithm"
        }
    
    def _split_waterfall_config(self, waterfall_config: List[Dict]) -> Dict[str, List[Dict]]:
        """Split waterfall config by type"""
        return {
            "opening": [w for w in waterfall_config if w.get("waterfall_type") == "Opening"],
            "closing": [w for w in waterfall_config if w.get("waterfall_type") == "Closing"]
        }


# Usage example
async def main():
    service = OptimizedHedgeDataService()
    
    result = await service.fetch_complete_hedge_data_optimized(
        exposure_currency="USD",
        hedge_method="COH",
        hedge_amount_order=1000000,
        order_id="TEST123",
        prompt_text="Analyze current hedging position for USD exposure with recent allocation data",
        nav_type="COI"
    )
    
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())