import redis
import json
import hashlib
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import pickle
import asyncio
from concurrent.futures import ThreadPoolExecutor

from supabase_client import get_supabase

class RedisCacheService:
    """Redis-based caching service for hedge data optimization"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis connection with connection pooling"""
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=False,  # We'll handle encoding/decoding manually
            max_connections=20,
            retry_on_timeout=True
        )
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache TTL configurations (in seconds)
        self.cache_ttl = {
            "static_config": 3600 * 4,      # 4 hours - rarely changes
            "currency_rates": 3600 * 24,     # 24 hours - daily updates
            "entity_positions": 3600 * 2,    # 2 hours - position updates
            "allocations": 1800,              # 30 minutes - frequent updates
            "hedge_events": 3600,             # 1 hour - moderate updates
            "framework_rules": 3600 * 8,     # 8 hours - infrequent changes
            "prompt_context": 900             # 15 minutes - context data
        }
    
    def generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate consistent cache keys"""
        sorted_params = sorted(kwargs.items())
        param_string = "_".join([f"{k}:{v}" for k, v in sorted_params])
        if len(param_string) > 100:
            param_hash = hashlib.md5(param_string.encode()).hexdigest()[:12]
            return f"hedge:{prefix}:{param_hash}"
        return f"hedge:{prefix}:{param_string}"
    
    def serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        try:
            if isinstance(data, (dict, list)) and self._is_json_serializable(data):
                return json.dumps(data, default=str).encode('utf-8')
            else:
                return pickle.dumps(data)
        except Exception as e:
            print(f"Serialization error: {e}")
            return pickle.dumps(data)
    
    def deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis storage"""
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                return pickle.loads(data)
            except Exception as e:
                print(f"Deserialization error: {e}")
                return None
    
    def _is_json_serializable(self, obj: Any) -> bool:
        try:
            json.dumps(obj, default=str)
            return True
        except (TypeError, ValueError):
            return False
    
    async def get_cached(self, cache_key: str) -> Optional[Any]:
        try:
            loop = asyncio.get_event_loop()
            cached_data = await loop.run_in_executor(
                self.executor, 
                self.redis_client.get, 
                cache_key
            )
            if cached_data:
                return self.deserialize_data(cached_data)
            return None
        except Exception as e:
            print(f"Cache get error for key {cache_key}: {e}")
            return None
    
    async def set_cached(self, cache_key: str, data: Any, ttl: int) -> bool:
        try:
            serialized_data = self.serialize_data(data)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.redis_client.setex(cache_key, ttl, serialized_data)
            )
            return result
        except Exception as e:
            print(f"Cache set error for key {cache_key}: {e}")
            return False
    
    async def delete_cached(self, pattern: str) -> int:
        try:
            loop = asyncio.get_event_loop()
            keys = await loop.run_in_executor(
                self.executor,
                self.redis_client.keys,
                pattern
            )
            if keys:
                deleted_count = 0
                batch_size = 100
                for i in range(0, len(keys), batch_size):
                    batch = keys[i:i + batch_size]
                    deleted = await loop.run_in_executor(
                        self.executor,
                        self.redis_client.delete,
                        *batch
                    )
                    deleted_count += deleted
                return deleted_count
            return 0
        except Exception as e:
            print(f"Cache delete error for pattern {pattern}: {e}")
            return 0
    
    # Specific cache methods for hedge data
    
    async def get_currency_rates_cached(self, currency_pairs: List[str], date_str: str = None) -> Optional[List[Dict]]:
        if not date_str:
            date_str = date.today().isoformat()
        cache_key = self.generate_cache_key(
            "currency_rates",
            pairs="_".join(sorted(currency_pairs)),
            date=date_str
        )
        return await self.get_cached(cache_key)
    
    async def set_currency_rates_cached(self, currency_pairs: List[str], rates_data: List[Dict], date_str: str = None) -> bool:
        if not date_str:
            date_str = date.today().isoformat()
        cache_key = self.generate_cache_key(
            "currency_rates",
            pairs="_".join(sorted(currency_pairs)),
            date=date_str
        )
        return await self.set_cached(cache_key, rates_data, self.cache_ttl["currency_rates"])
    
    async def get_static_config_cached(self, config_type: str, currency: str = None) -> Optional[Dict]:
        cache_key = self.generate_cache_key(
            "static_config",
            type=config_type,
            currency=currency or "global"
        )
        return await self.get_cached(cache_key)
    
    async def set_static_config_cached(self, config_type: str, config_data: Dict, currency: str = None) -> bool:
        cache_key = self.generate_cache_key(
            "static_config",
            type=config_type,
            currency=currency or "global"
        )
        return await self.set_cached(cache_key, config_data, self.cache_ttl["static_config"])
    
    async def get_entity_positions_cached(self, entity_ids: List[str], currency: str, nav_type: str = None) -> Optional[List[Dict]]:
        cache_key = self.generate_cache_key(
            "entity_positions",
            entities="_".join(sorted(entity_ids[:20])),
            currency=currency,
            nav_type=nav_type or "all"
        )
        return await self.get_cached(cache_key)
    
    async def set_entity_positions_cached(self, entity_ids: List[str], currency: str, positions_data: List[Dict], nav_type: str = None) -> bool:
        cache_key = self.generate_cache_key(
            "entity_positions",
            entities="_".join(sorted(entity_ids[:20])),
            currency=currency,
            nav_type=nav_type or "all"
        )
        return await self.set_cached(cache_key, positions_data, self.cache_ttl["entity_positions"])
    
    async def get_prompt_context_cached(self, prompt_hash: str, currency: str) -> Optional[Dict]:
        cache_key = self.generate_cache_key(
            "prompt_context",
            hash=prompt_hash,
            currency=currency
        )
        return await self.get_cached(cache_key)
    
    async def set_prompt_context_cached(self, prompt_hash: str, currency: str, context_data: Dict) -> bool:
        cache_key = self.generate_cache_key(
            "prompt_context",
            hash=prompt_hash,
            currency=currency
        )
        return await self.set_cached(cache_key, context_data, self.cache_ttl["prompt_context"])
    
    async def invalidate_currency_cache(self, currency: str) -> int:
        patterns = [
            f"hedge:*:*currency:{currency}*",
            f"hedge:*:*{currency}*",
            f"hedge:entity_positions:*{currency}*",
            f"hedge:currency_rates:*{currency}*"
        ]
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.delete_cached(pattern)
            total_deleted += deleted
        return total_deleted
    
    async def invalidate_entity_cache(self, entity_id: str) -> int:
        patterns = [
            f"hedge:entity_positions:*{entity_id}*",
            f"hedge:allocations:*{entity_id}*",
            f"hedge:hedge_events:*{entity_id}*"
        ]
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.delete_cached(pattern)
            total_deleted += deleted
        return total_deleted
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                self.executor,
                self.redis_client.info,
                "memory"
            )
            all_keys = await loop.run_in_executor(
                self.executor,
                self.redis_client.keys,
                "hedge:*"
            )
            key_stats = {}
            for key in all_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                prefix = key.split(':')[1] if ':' in key else 'unknown'
                key_stats[prefix] = key_stats.get(prefix, 0) + 1
            return {
                "total_keys": len(all_keys),
                "memory_used_human": info.get("used_memory_human", "N/A"),
                "memory_used_bytes": info.get("used_memory", 0),
                "key_distribution": key_stats,
                "cache_hit_ratio": "N/A"
            }
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    def cache_decorator(self, cache_type: str, ttl_override: int = None):
        """Decorator for automatic caching of function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                cache_key = self.generate_cache_key(
                    f"func_{cache_type}",
                    func_name=func.__name__,
                    args=str(hash(str(args))),
                    kwargs=str(hash(str(sorted(kwargs.items()))))
                )
                cached_result = await self.get_cached(cache_key)
                if cached_result is not None:
                    return cached_result
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                ttl = ttl_override or self.cache_ttl.get(cache_type, 1800)
                await self.set_cached(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

class CachedHedgeDataService:
    """Hedge data service with integrated Redis caching"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.cache = RedisCacheService(redis_url)
        self.supabase = get_supabase()
    
    async def get_currency_rates_with_cache(self, currency_pairs: List[str]) -> List[Dict]:
        today = date.today().isoformat()
        cached_rates = await self.cache.get_currency_rates_cached(currency_pairs, today)
        if cached_rates:
            return cached_rates
        rates_data = []
        for pair in currency_pairs:
            result = (self.supabase.table("currency_rates")
                     .select("*")
                     .eq("currency_pair", pair)
                     .order("effective_date", desc=True)
                     .limit(1)
                     .execute())
            if hasattr(result, 'data') and result.data:
                rates_data.extend(result.data)
        await self.cache.set_currency_rates_cached(currency_pairs, rates_data, today)
        return rates_data
    
    async def get_waterfall_config_cached(self) -> List[Dict]:
        """Get waterfall configuration with caching"""
        cache_wrap = self.cache.cache_decorator("static_config", ttl_override=3600 * 4)
        @cache_wrap
        async def inner():
            result = (self.supabase.table("waterfall_logic_configuration")
                     .select("*")
                     .eq("active_flag", "Y")
                     .order("waterfall_type")
                     .order("priority_level")
                     .execute())
            return getattr(result, "data", []) or []
        return await inner()
    
    async def get_system_config_cached(self) -> List[Dict]:
        """Get system configuration with caching"""
        cache_wrap = self.cache.cache_decorator("static_config", ttl_override=3600 * 4)
        @cache_wrap
        async def inner():
            result = (self.supabase.table("system_configuration")
                     .select("*")
                     .eq("active_flag", "Y")
                     .execute())
            return getattr(result, "data", []) or []
        return await inner()
    
    async def invalidate_entity_related_cache(self, entity_id: str, currency: str):
        await self.cache.invalidate_entity_cache(entity_id)
        await self.cache.invalidate_currency_cache(currency)
    
    async def get_cache_health(self) -> Dict[str, Any]:
        return await self.cache.get_cache_stats()

# Usage example
async def demo_cache_usage():
    cache_service = CachedHedgeDataService()
    currency_pairs = ["USDSGD", "EURSGD", "GBPSGD"]
    rates = await cache_service.get_currency_rates_with_cache(currency_pairs)
    print(f"Currency rates (cached): {len(rates)} records")
    waterfall_config = await cache_service.get_waterfall_config_cached()
    print(f"Waterfall config (cached): {len(waterfall_config)} records")
    stats = await cache_service.get_cache_health()
    print(f"Cache stats: {stats}")

if __name__ == "__main__":
    asyncio.run(demo_cache_usage())
