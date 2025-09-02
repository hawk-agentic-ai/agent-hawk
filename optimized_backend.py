from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import redis
import json
import time
import hashlib
import os
from typing import Optional

app = FastAPI(title="Hedge Agent Optimized Dify API")

# Redis connection for caching
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    redis_client = None

class QueryRequest(BaseModel):
    query: str
    user_id: str = "default"

class PerformanceMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.cache_hits = 0
    
    def record_request(self, cache_hit=False):
        self.request_count += 1
        if cache_hit:
            self.cache_hits += 1
    
    def get_stats(self):
        uptime = time.time() - self.start_time
        cache_rate = (self.cache_hits / self.request_count * 100) if self.request_count > 0 else 0
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.request_count,
            "cache_hit_rate": f"{cache_rate:.1f}%",
            "cache_hits": self.cache_hits,
            "server_optimization": "enabled",
            "redis_status": "connected" if REDIS_AVAILABLE else "disconnected"
        }

metrics = PerformanceMetrics()

def get_cache_key(query: str, user_id: str) -> str:
    """Generate cache key for query"""
    content = f"{query}:{user_id}"
    return f"dify_cache:{hashlib.md5(content.encode()).hexdigest()}"

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "fastapi": "online",
            "redis": "connected" if REDIS_AVAILABLE else "disconnected",
            "dify_integration": "enabled"
        }
    }

@app.get("/dify/performance-stats")
def get_performance_stats():
    """Get detailed performance statistics"""
    stats = metrics.get_stats()
    
    # Add Redis memory info if available
    if REDIS_AVAILABLE and redis_client:
        try:
            redis_info = redis_client.info('memory')
            stats["redis_memory_mb"] = round(redis_info.get('used_memory', 0) / 1024 / 1024, 2)
            stats["redis_keys"] = redis_client.dbsize()
        except:
            stats["redis_memory_mb"] = 0
            stats["redis_keys"] = 0
    else:
        stats["redis_memory_mb"] = 0
        stats["redis_keys"] = 0
    
    return stats

@app.post("/dify/chat")
async def optimized_dify_chat(request: QueryRequest):
    """Optimized Dify chat with Redis caching and performance monitoring"""
    start_time = time.time()
    
    # Check cache first (if Redis is available)
    cached_response = None
    if REDIS_AVAILABLE and redis_client:
        cache_key = get_cache_key(request.query, request.user_id)
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                cached_response = json.loads(cached_data)
                metrics.record_request(cache_hit=True)
                
                return {
                    "response": cached_response,
                    "performance": {
                        "response_time_ms": round((time.time() - start_time) * 1000, 2),
                        "cache_used": True,
                        "optimization": "cache_hit",
                        "data_source": "redis_cache"
                    },
                    "metadata": {
                        "cached_at": cached_response.get("cached_at"),
                        "user_id": request.user_id
                    }
                }
        except Exception as e:
            print(f"Cache check error: {e}")
    
    # No cache hit - call Dify API
    dify_api_key = os.environ.get("DIFY_API_KEY", "")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            dify_response = await client.post(
                "https://api.dify.ai/v1/chat-messages",
                headers={
                    "Authorization": f"Bearer {dify_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "inputs": {},
                    "query": request.query,
                    "user": request.user_id,
                    "response_mode": "blocking"
                }
            )
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            if dify_response.status_code == 200:
                dify_data = dify_response.json()
                
                # Cache the response (if Redis is available)
                if REDIS_AVAILABLE and redis_client:
                    cache_data = {
                        **dify_data,
                        "cached_at": time.time(),
                        "query": request.query
                    }
                    
                    try:
                        cache_key = get_cache_key(request.query, request.user_id)
                        redis_client.setex(cache_key, 1800, json.dumps(cache_data))  # Cache for 30 minutes
                    except Exception as e:
                        print(f"Cache save error: {e}")
                
                metrics.record_request(cache_hit=False)
                
                return {
                    "response": dify_data,
                    "performance": {
                        "response_time_ms": response_time,
                        "cache_used": False,
                        "optimization": "live_api_call",
                        "data_source": "dify_api"
                    },
                    "metadata": {
                        "user_id": request.user_id,
                        "cached_for_future": REDIS_AVAILABLE
                    }
                }
            else:
                raise HTTPException(
                    status_code=dify_response.status_code,
                    detail=f"Dify API error: {dify_response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Dify API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API call failed: {str(e)}")

@app.get("/dify/cache-info")
def get_cache_info():
    """Get information about cached queries"""
    if not REDIS_AVAILABLE or not redis_client:
        return {"error": "Redis not available", "total_cached_queries": 0}
    
    try:
        keys = redis_client.keys("dify_cache:*")
        cache_items = []
        
        for key in keys[:10]:  # Show last 10 cached items
            data = redis_client.get(key)
            if data:
                cache_data = json.loads(data)
                cache_items.append({
                    "query_preview": cache_data.get("query", "")[:50] + "...",
                    "cached_at": cache_data.get("cached_at"),
                    "ttl": redis_client.ttl(key)
                })
        
        return {
            "total_cached_queries": len(keys),
            "recent_cache_items": cache_items,
            "cache_hit_rate": metrics.get_stats()["cache_hit_rate"]
        }
    except Exception as e:
        return {"error": f"Cache info unavailable: {str(e)}"}

@app.delete("/dify/cache")
def clear_cache():
    """Clear all cached Dify responses"""
    if not REDIS_AVAILABLE or not redis_client:
        return {"error": "Redis not available"}
    
    try:
        keys = redis_client.keys("dify_cache:*")
        if keys:
            redis_client.delete(*keys)
        return {"message": f"Cleared {len(keys)} cached items"}
    except Exception as e:
        return {"error": f"Cache clear failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)