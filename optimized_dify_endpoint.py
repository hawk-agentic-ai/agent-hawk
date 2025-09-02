from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import asyncio
import json
import hashlib
import httpx
import os
from datetime import datetime
import logging

from optimized_hedge_data_service import OptimizedHedgeDataService, PromptAnalyzer
from redis_cache_service import CachedHedgeDataService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DifyOptimizedRequest(BaseModel):
    """Request model for optimized Dify integration"""
    query: str = Field(..., description="User's prompt/query")
    msgUid: str = Field(..., description="Message unique identifier")
    instructionId: str = Field(..., description="Instruction identifier")
    
    # Context parameters
    exposure_currency: str = Field(..., description="Primary currency for context")
    hedge_method: Optional[str] = Field(None, description="Hedge accounting method (COH, MTM)")
    nav_type: Optional[str] = Field(None, description="NAV type (COI, RE)")
    currency_type: Optional[str] = Field(None, description="Currency classification")
    
    # Optimization flags
    use_cache: bool = Field(True, description="Whether to use cached data")
    max_context_size: int = Field(50000, description="Maximum context size in characters")
    include_historical: bool = Field(False, description="Include historical data beyond recent")

class DifyOptimizedResponse(BaseModel):
    """Response model for optimized Dify integration"""
    success: bool
    dify_response: Optional[Dict[str, Any]] = None
    context_metadata: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    error: Optional[str] = None

class OptimizedDifyService:
    """Service for optimized Dify integration with context pre-loading"""
    
    def __init__(self):
        self.hedge_service = OptimizedHedgeDataService()
        self.cache_service = CachedHedgeDataService()
        self.dify_api_key = os.getenv("DIFY_API_KEY", "your-dify-api-key")
        print(f"DIFY_API_KEY loaded: {self.dify_api_key}")  # Debug print to confirm key loading
        self.dify_base_url = "https://api.dify.ai/v1"
        
        # Performance tracking
        self.performance_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "avg_context_prep_time": 0,
            "avg_dify_response_time": 0
        }
    
    def generate_prompt_hash(self, query: str, context_params: Dict) -> str:
        """Generate hash for prompt caching"""
        prompt_data = {
            "query": query,
            "exposure_currency": context_params.get("exposure_currency"),
            "hedge_method": context_params.get("hedge_method"),
            "nav_type": context_params.get("nav_type")
        }
        
        prompt_string = json.dumps(prompt_data, sort_keys=True)
        return hashlib.md5(prompt_string.encode()).hexdigest()[:16]
    
    async def prepare_optimized_context(self, request: DifyOptimizedRequest) -> Dict[str, Any]:
        """Prepare optimized context for Dify based on prompt analysis"""
        
        start_time = datetime.now()
        
        try:
            # Step 1: Check for cached context
            prompt_hash = self.generate_prompt_hash(request.query, request.dict())
            
            if request.use_cache:
                cached_context = await self.cache_service.cache.get_prompt_context_cached(
                    prompt_hash, request.exposure_currency
                )
                if cached_context:
                    self.performance_stats["cache_hits"] += 1
                    return {
                        "context": cached_context,
                        "source": "cache",
                        "preparation_time_ms": (datetime.now() - start_time).total_seconds() * 1000
                    }
            
            # Step 2: Analyze prompt requirements
            requirements = PromptAnalyzer.analyze_prompt_requirements(request.query)
            logger.info(f"Prompt requirements: {requirements}")
            
            # Step 3: Fetch optimized data
            hedge_data = await self.hedge_service.fetch_complete_hedge_data_optimized(
                exposure_currency=request.exposure_currency,
                hedge_method=request.hedge_method or "COH",
                hedge_amount_order=0,  # Not used in this context
                order_id=request.instructionId,
                prompt_text=request.query,
                nav_type=request.nav_type,
                currency_type=request.currency_type
            )
            
            # Step 4: Structure context for Dify
            dify_context = self._structure_context_for_dify(
                hedge_data, 
                requirements, 
                request.max_context_size
            )
            
            # Step 5: Cache the context
            if request.use_cache:
                await self.cache_service.cache.set_prompt_context_cached(
                    prompt_hash, request.exposure_currency, dify_context
                )
            
            preparation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "context": dify_context,
                "source": "fresh",
                "preparation_time_ms": preparation_time,
                "requirements": requirements
            }
            
        except Exception as e:
            logger.error(f"Context preparation error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Context preparation failed: {str(e)}")
    
    def _structure_context_for_dify(
        self, 
        hedge_data: Dict[str, Any], 
        requirements: Dict[str, Any],
        max_size: int
    ) -> Dict[str, Any]:
        """Structure hedge data into optimized context for Dify"""
        
        context = {
            "prompt_analysis": requirements,
            "data_summary": {
                "entities_count": len(hedge_data.get("entity_groups", [])),
                "data_scope": requirements.get("data_scope", "focused"),
                "optimization_applied": hedge_data.get("optimization_applied", False)
            }
        }
        
        # Add entity data based on requirements
        if requirements.get("data_scope") == "minimal":
            context["entities"] = self._get_minimal_entity_context(hedge_data)
        elif requirements.get("data_scope") == "focused":
            context["entities"] = self._get_focused_entity_context(hedge_data, requirements)
        else:
            context["entities"] = hedge_data.get("entity_groups", [])
        
        # Add configuration data if needed
        if requirements.get("requires_config") or requirements.get("data_scope") == "comprehensive":
            context["configuration"] = {
                "hedging_framework": hedge_data.get("stage_1a_config", {}).get("hedging_framework", []),
                "hedge_instruments": hedge_data.get("stage_2_config", {}).get("hedge_instruments", [])
            }
        
        # Add recent activities if requested
        if requirements.get("requires_recent_data"):
            context["recent_activities"] = {
                "allocations": hedge_data.get("stage_1b_data", {}).get("current_allocations", [])[:10],
                "instructions": hedge_data.get("stage_1b_data", {}).get("hedge_instructions_history", [])[:5],
                "hedge_events": hedge_data.get("stage_1b_data", {}).get("active_hedge_events", [])[:10]
            }
        
        # Ensure context size doesn't exceed limit
        context_str = json.dumps(context, default=str)
        if len(context_str) > max_size:
            logger.warning(f"Context size ({len(context_str)}) exceeds limit ({max_size}). Truncating...")
            context = self._truncate_context(context, max_size)
        
        return context
    
    def _get_minimal_entity_context(self, hedge_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get minimal entity context for simple queries"""
        entities = hedge_data.get("entity_groups", [])[:5]  # Limit to 5 entities
        
        minimal_entities = []
        for entity in entities:
            minimal_entity = {
                "entity_id": entity.get("entity_id"),
                "entity_name": entity.get("entity_name"),
                "exposure_currency": entity.get("exposure_currency"),
                "positions_summary": {
                    "count": len(entity.get("positions", [])),
                    "total_position": sum(p.get("current_position", 0) for p in entity.get("positions", [])),
                    "hedging_status": entity.get("positions", [{}])[0].get("hedging_state", {}).get("hedging_status", "Unknown")
                }
            }
            minimal_entities.append(minimal_entity)
        
        return minimal_entities
    
    def _get_focused_entity_context(self, hedge_data: Dict[str, Any], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get focused entity context based on requirements"""
        entities = hedge_data.get("entity_groups", [])
        
        if requirements.get("entities"):
            mentioned_entities = [e.lower() for e in requirements["entities"]]
            entities = [e for e in entities if 
                        any(mentioned in e.get("entity_name", "").lower() or 
                            mentioned in e.get("entity_id", "").lower() 
                            for mentioned in mentioned_entities)]
        
        entities = entities[:10]
        
        focused_entities = []
        for entity in entities:
            focused_entity = {
                "entity_id": entity.get("entity_id"),
                "entity_name": entity.get("entity_name"),
                "entity_type": entity.get("entity_type"),
                "exposure_currency": entity.get("exposure_currency"),
                "positions": []
            }
            
            for position in entity.get("positions", []):
                if requirements.get("nav_types") and position.get("nav_type") not in requirements["nav_types"]:
                    continue
                
                focused_position = {
                    "nav_type": position.get("nav_type"),
                    "current_position": position.get("current_position"),
                    "hedging_state": position.get("hedging_state", {})
                }
                
                if requirements.get("requires_recent_data"):
                    focused_position["recent_allocations"] = position.get("allocation_data", [])[:3]
                
                focused_entity["positions"].append(focused_position)
            
            focused_entities.append(focused_entity)
        
        return focused_entities
    
    def _truncate_context(self, context: Dict[str, Any], max_size: int) -> Dict[str, Any]:
        """Truncate context to fit size limit while preserving important data"""
        priority_keys = ["data_summary", "entities", "recent_activities", "configuration"]
        
        truncated_context = {"data_summary": context.get("data_summary", {})}
        current_size = len(json.dumps(truncated_context, default=str))
        
        for key in priority_keys:
            if key == "data_summary":
                continue
                
            if key in context:
                key_data = context[key]
                key_size = len(json.dumps(key_data, default=str))
                
                if current_size + key_size <= max_size:
                    truncated_context[key] = key_data
                    current_size += key_size
                else:
                    if isinstance(key_data, list) and key_data:
                        partial_data = []
                        for item in key_data:
                            item_size = len(json.dumps(item, default=str))
                            if current_size + item_size <= max_size:
                                partial_data.append(item)
                                current_size += item_size
                            else:
                                break
                        if partial_data:
                            truncated_context[key] = partial_data
                    break
        
        truncated_context["truncation_applied"] = True
        return truncated_context
    
    async def send_to_dify_optimized(
        self, 
        request: DifyOptimizedRequest,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send optimized request to Dify with pre-loaded context"""
        
        start_time = datetime.now()
        
        try:
            dify_payload = {
                "inputs": {
                    "hedge_context": json.dumps(context_data["context"], default=str),
                    "msg_uid": request.msgUid,
                    "instruction_id": request.instructionId,
                    "optimization_metadata": json.dumps({
                        "context_source": context_data["source"],
                        "context_preparation_time_ms": context_data.get("preparation_time_ms", 0),
                        "prompt_requirements": context_data.get("requirements", {})
                    }, default=str)
                },
                "query": request.query,
                "response_mode": "blocking",
                "conversation_id": "",
                "user": f"hedge_user_{request.msgUid}",
                "files": []
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.dify_base_url}/chat-messages",
                    headers={
                        "Authorization": f"Bearer {self.dify_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=dify_payload
                )
                
                response.raise_for_status()
                dify_response = response.json()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.performance_stats["total_requests"] += 1
            self.performance_stats["avg_dify_response_time"] = (
                (self.performance_stats["avg_dify_response_time"] * (self.performance_stats["total_requests"] - 1) + response_time) /
                self.performance_stats["total_requests"]
            )
            
            return {
                "dify_response": dify_response,
                "response_time_ms": response_time,
                "context_metadata": {
                    "context_source": context_data["source"],
                    "context_size_chars": len(json.dumps(context_data["context"], default=str)),
                    "context_preparation_time_ms": context_data.get("preparation_time_ms", 0)
                }
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Dify API error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Dify API error: {str(e)}")
        except Exception as e:
            logger.error(f"Dify integration error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Dify integration error: {str(e)}")
    
    async def send_to_dify_streaming(
        self, 
        request: DifyOptimizedRequest,
        context_data: Dict[str, Any]
    ):
        """Send optimized request to Dify with streaming response"""
        
        try:
            dify_payload = {
                "inputs": {
                    "hedge_context": json.dumps(context_data["context"], default=str),
                    "msg_uid": request.msgUid,
                    "instruction_id": request.instructionId
                },
                "query": request.query,
                "response_mode": "streaming",
                "conversation_id": "",
                "user": f"hedge_user_{request.msgUid}",
                "files": []
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.dify_base_url}/chat-messages",
                    headers={
                        "Authorization": f"Bearer {self.dify_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=dify_payload
                ) as response:
                    response.raise_for_status()
                    
                    async for chunk in response.aiter_lines():
                        if chunk:
                            yield f"data: {chunk}\n\n"
            
        except Exception as e:
            error_response = {
                "error": str(e),
                "context_metadata": context_data.get("source", "unknown")
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        cache_hit_rate = (
            (self.performance_stats["cache_hits"] / self.performance_stats["total_requests"] * 100)
            if self.performance_stats["total_requests"] > 0 else 0
        )
        
        return {
            **self.performance_stats,
            "cache_hit_rate_percent": round(cache_hit_rate, 2)
        }

# FastAPI app with optimized endpoints
app = FastAPI(title="Optimized Dify Hedge Agent API", version="1.0.0")
dify_service = OptimizedDifyService()

@app.post("/dify/chat-optimized", response_model=DifyOptimizedResponse)
async def dify_chat_optimized(request: DifyOptimizedRequest) -> DifyOptimizedResponse:
    """Optimized Dify chat endpoint with context pre-loading"""
    
    try:
        # Prepare optimized context
        context_data = await dify_service.prepare_optimized_context(request)
        
        # Send to Dify with context
        dify_result = await dify_service.send_to_dify_optimized(request, context_data)
        
        return DifyOptimizedResponse(
            success=True,
            dify_response=dify_result["dify_response"],
            context_metadata=dify_result["context_metadata"],
            performance_metrics={
                "total_time_ms": (
                    dify_result["response_time_ms"] + 
                    context_data.get("preparation_time_ms", 0)
                ),
                "context_prep_time_ms": context_data.get("preparation_time_ms", 0),
                "dify_response_time_ms": dify_result["response_time_ms"],
                "context_source": context_data["source"]
            }
        )
        
    except Exception as e:
        logger.error(f"Optimized chat error: {str(e)}")
        return DifyOptimizedResponse(
            success=False,
            context_metadata={"error": "context_preparation_failed"},
            performance_metrics={"error": True},
            error=str(e)
        )

@app.post("/dify/stream-optimized")
async def dify_stream_optimized(request: DifyOptimizedRequest):
    """Optimized Dify streaming endpoint with context pre-loading"""
    
    try:
        # Prepare optimized context
        context_data = await dify_service.prepare_optimized_context(request)
        
        # Stream response from Dify
        return StreamingResponse(
            dify_service.send_to_dify_streaming(request, context_data),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Context-Source": context_data["source"],
                "X-Context-Prep-Time": str(context_data.get("preparation_time_ms", 0))
            }
        )
        
    except Exception as e:
        logger.error(f"Optimized streaming error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dify/performance-stats")
async def get_performance_stats():
    """Get performance statistics for the optimized service"""
    
    service_stats = dify_service.get_performance_stats()
    cache_stats = await dify_service.cache_service.get_cache_health()
    
    return {
        "service_performance": service_stats,
        "cache_health": cache_stats,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/cache/invalidate/{currency}")
async def invalidate_currency_cache(currency: str):
    """Invalidate cache for a specific currency"""
    
    deleted_count = await dify_service.cache_service.cache.invalidate_currency_cache(currency)
    
    return {
        "success": True,
        "currency": currency,
        "cache_entries_deleted": deleted_count,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
