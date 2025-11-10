"""
Cache Invalidation Manager - Maintains Cache Consistency After Write Operations
Ensures that cached data is invalidated when underlying database tables are modified
"""

import logging
from typing import Dict, List, Set, Optional, Any
import redis

logger = logging.getLogger(__name__)

# Cache Dependency Mapping
# Maps database tables to cache keys/patterns that need invalidation
CACHE_DEPENDENCIES = {
    # Core transaction tables
    "hedge_instructions": [
        "*hedge_positions*",
        "*v_available_amounts_fast*",
        "*v_entity_capacity_complete*",
        "*exposure_analysis*",
        "*hedge_effectiveness*",
        "*allocation_drift*",
        "*inception_template*",
        "*utilisation_template*",
    ],

    "position_nav_master": [
        "*v_available_amounts_fast*",
        "*v_entity_capacity_complete*",
        "*nav_calculations*",
        "*portfolio_valuation*",
        "*position_nav_master*",
    ],

    "deal_bookings": [
        "*hedge_positions*",
        "*portfolio_structure*",
        "*deal_bookings*",
        "*real_time_pnl*",
    ],

    "gl_entries": [
        "*portfolio_valuation*",
        "*real_time_pnl*",
        "*gl_entries*",
    ],

    "currency_rates": [
        "*market_data*",
        "*currency_rates*",
        "*portfolio_valuation*",
    ],

    # Configuration tables
    "entity_master": [
        "*entity_master*",
        "*v_entity_capacity_complete*",
    ],

    "currency_configuration": [
        "*currency_configuration*",
        "*v_available_amounts_fast*",
    ],

    "buffer_configuration": [
        "*buffer_configuration*",
        "*v_available_amounts_fast*",
    ],

    "threshold_configuration": [
        "*threshold_configuration*",
        "*v_available_amounts_fast*",
    ],
}

# View dependencies - when these views are queried, they depend on these tables
VIEW_SOURCE_TABLES = {
    "v_available_amounts_fast": ["hedge_instructions", "position_nav_master", "currency_configuration", "buffer_configuration", "threshold_configuration"],
    "v_entity_capacity_complete": ["hedge_instructions", "position_nav_master", "entity_master"],
}


class CacheInvalidationManager:
    """
    Manages cache invalidation after database write operations
    Ensures data consistency between cache and database
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize cache invalidation manager

        Args:
            redis_client: Redis client for cache operations (optional)
        """
        self.redis_client = redis_client
        self.invalidation_stats = {
            "total_invalidations": 0,
            "keys_invalidated": 0,
            "tables_processed": 0,
        }

    @property
    def redis_available(self) -> bool:
        """Check if Redis is available"""
        return self.redis_client is not None

    async def invalidate_after_write(self,
                                     table: str,
                                     operation: str,
                                     data: Optional[Dict[str, Any]] = None) -> int:
        """
        Invalidate cache keys affected by a write operation

        Args:
            table: Table that was modified
            operation: Type of operation (INSERT, UPDATE, DELETE)
            data: Data that was written (optional, for targeted invalidation)

        Returns:
            Number of cache keys invalidated
        """
        if not self.redis_available:
            logger.debug(f"Redis not available, skipping cache invalidation for {table}")
            return 0

        keys_invalidated = 0

        try:
            # Get cache patterns to invalidate for this table
            patterns = CACHE_DEPENDENCIES.get(table, [])

            if not patterns:
                logger.debug(f"No cache dependencies defined for table: {table}")
                return 0

            logger.info(f"Invalidating cache for {table} ({operation}): {len(patterns)} patterns")

            # Invalidate each pattern
            for pattern in patterns:
                count = await self._invalidate_pattern(pattern)
                keys_invalidated += count

            # Update stats
            self.invalidation_stats["total_invalidations"] += 1
            self.invalidation_stats["keys_invalidated"] += keys_invalidated
            self.invalidation_stats["tables_processed"] += 1

            logger.info(f"✅ Invalidated {keys_invalidated} cache keys for {table}")

            return keys_invalidated

        except Exception as e:
            logger.error(f"Cache invalidation error for {table}: {e}")
            return 0

    async def _invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern

        Args:
            pattern: Redis key pattern (supports wildcards)

        Returns:
            Number of keys deleted
        """
        try:
            # Find all keys matching pattern
            keys = self.redis_client.keys(pattern)

            if keys:
                # Delete all matching keys
                self.redis_client.delete(*keys)
                logger.debug(f"Deleted {len(keys)} keys matching pattern: {pattern}")
                return len(keys)

            return 0

        except Exception as e:
            logger.warning(f"Error invalidating pattern {pattern}: {e}")
            return 0

    async def invalidate_after_transaction(self,
                                          tables_modified: List[str]) -> int:
        """
        Invalidate cache after a multi-table transaction

        Args:
            tables_modified: List of tables that were modified in the transaction

        Returns:
            Total number of cache keys invalidated
        """
        if not self.redis_available:
            return 0

        total_invalidated = 0
        unique_tables = set(tables_modified)

        logger.info(f"Invalidating cache for transaction affecting {len(unique_tables)} tables")

        for table in unique_tables:
            count = await self.invalidate_after_write(table, "TRANSACTION", None)
            total_invalidated += count

        return total_invalidated

    async def invalidate_by_currency(self, currency: str) -> int:
        """
        Invalidate all cache keys related to a specific currency
        Useful for targeted invalidation when currency-specific data changes

        Args:
            currency: Currency code (e.g., "USD", "EUR")

        Returns:
            Number of cache keys invalidated
        """
        if not self.redis_available:
            return 0

        try:
            pattern = f"*{currency}*"
            return await self._invalidate_pattern(pattern)
        except Exception as e:
            logger.error(f"Currency-specific cache invalidation error: {e}")
            return 0

    async def invalidate_by_entity(self, entity_id: str) -> int:
        """
        Invalidate all cache keys related to a specific entity

        Args:
            entity_id: Entity identifier

        Returns:
            Number of cache keys invalidated
        """
        if not self.redis_available:
            return 0

        try:
            pattern = f"*{entity_id}*"
            return await self._invalidate_pattern(pattern)
        except Exception as e:
            logger.error(f"Entity-specific cache invalidation error: {e}")
            return 0

    async def clear_all_cache(self) -> int:
        """
        Clear all cache keys (use with caution!)

        Returns:
            Number of cache keys cleared
        """
        if not self.redis_available:
            return 0

        try:
            # Get all hedge-related keys
            pattern = "hedge_*"
            keys = self.redis_client.keys(pattern)

            if keys:
                self.redis_client.delete(*keys)
                logger.warning(f"🗑️ Cleared ALL cache: {len(keys)} keys deleted")
                return len(keys)

            return 0

        except Exception as e:
            logger.error(f"Clear all cache error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache invalidation statistics"""
        return {
            **self.invalidation_stats,
            "redis_available": self.redis_available
        }

    def reset_stats(self):
        """Reset invalidation statistics"""
        self.invalidation_stats = {
            "total_invalidations": 0,
            "keys_invalidated": 0,
            "tables_processed": 0,
        }


# Singleton instance for shared use
_cache_invalidation_manager: Optional[CacheInvalidationManager] = None


def initialize_cache_invalidation(redis_client: Optional[redis.Redis] = None):
    """Initialize the global cache invalidation manager"""
    global _cache_invalidation_manager
    _cache_invalidation_manager = CacheInvalidationManager(redis_client)
    logger.info("Cache invalidation manager initialized")


def get_cache_invalidation_manager() -> Optional[CacheInvalidationManager]:
    """Get the global cache invalidation manager"""
    return _cache_invalidation_manager