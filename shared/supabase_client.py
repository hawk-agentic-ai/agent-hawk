"""
Supabase and Redis client management for shared use between FastAPI and MCP server.
Extracted from unified_smart_backend.py to enable connection reuse.
"""

import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    import os.path
    # Get the absolute path to the .env file in the project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
except ImportError:
    pass

try:
    import redis
    import redis.asyncio as aioredis
except ModuleNotFoundError:
    redis = None  # type: ignore
    aioredis = None  # type: ignore
import logging
import asyncio
from typing import Optional, Tuple
from supabase import create_client, Client
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages Supabase and Redis connections with connection pooling for shared use"""

    def __init__(self):
        self.supabase_client: Optional[Client] = None
        self.redis_client: Optional[redis.Redis] = None
        self.redis_pool: Optional[aioredis.ConnectionPool] = None
        self._connection_pool_size = 10
        self._max_connections = 20
    
    async def initialize_connections(self) -> Tuple[Optional[Client], Optional[redis.Redis]]:
        """Initialize both Supabase and Redis connections"""
        try:
            # Initialize Supabase client - Properly read from environment variables
            SUPABASE_URL = os.getenv("SUPABASE_URL")
            SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

            # Use service role key if available, otherwise use anon key
            SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY

            logger.info(f"Reading from environment variables:")
            logger.info(f"SUPABASE_URL: {SUPABASE_URL}")
            logger.info(f"Service role key available: {bool(SUPABASE_SERVICE_ROLE_KEY)}")
            logger.info(f"Anon key available: {bool(SUPABASE_ANON_KEY)}")

            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY environment variables must be set")

            using = "service_role" if SUPABASE_SERVICE_ROLE_KEY else "anon"
            logger.info(f"Initializing Supabase client using {using} key")
            logger.info(f"SUPABASE_KEY length: {len(SUPABASE_KEY) if SUPABASE_KEY else 0}")

            # Validate URL format
            if not SUPABASE_URL.startswith('https://') or '.supabase.co' not in SUPABASE_URL:
                raise ValueError(f"Invalid Supabase URL format: {SUPABASE_URL}")

            # Strip any whitespace that might cause issues
            SUPABASE_URL = SUPABASE_URL.strip()
            SUPABASE_KEY = SUPABASE_KEY.strip()

            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")

            # Test the connection with a simple query
            await self._test_supabase_connection()
            
            # Initialize Redis with connection pooling
            if redis is None or aioredis is None:
                logger.warning("Redis library not available. Continuing without cache.")
                self.redis_client = None
                self.redis_pool = None
            else:
                try:
                    # Create connection pool
                    redis_host = os.getenv("REDIS_HOST", "localhost")
                    redis_port = int(os.getenv("REDIS_PORT", "6379"))
                    redis_db = int(os.getenv("REDIS_DB", "0"))

                    self.redis_pool = aioredis.ConnectionPool.from_url(
                        f"redis://{redis_host}:{redis_port}/{redis_db}",
                        max_connections=self._max_connections,
                        decode_responses=True
                    )

                    # Test connection
                    async with aioredis.Redis(connection_pool=self.redis_pool) as redis_conn:
                        await redis_conn.ping()

                    # Also maintain sync client for backward compatibility
                    self.redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        decode_responses=True,
                        max_connections=self._connection_pool_size
                    )
                    self.redis_client.ping()

                    logger.info(f"Redis connection pool initialized: {self._max_connections} max connections")
                except Exception as e:
                    logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
                    self.redis_client = None
                    self.redis_pool = None
            
            return self.supabase_client, self.redis_client
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return None, None
    
    def get_supabase_client(self) -> Optional[Client]:
        """Get the current Supabase client instance"""
        return self.supabase_client
    
    def get_redis_client(self) -> Optional[redis.Redis]:
        """Get the current Redis client instance"""
        return self.redis_client

    @asynccontextmanager
    async def get_redis_connection(self):
        """Get async Redis connection from pool"""
        if self.redis_pool and aioredis is not None:
            async with aioredis.Redis(connection_pool=self.redis_pool) as redis_conn:
                yield redis_conn
        else:
            yield None
    
    async def cleanup_connections(self) -> None:
        """Clean up database connections and pools"""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis sync connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis sync connection: {e}")

        if self.redis_pool and aioredis is not None:
            try:
                await self.redis_pool.disconnect()
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {e}")

        logger.info("Database connections cleanup complete")

    async def _test_supabase_connection(self) -> None:
        """Test Supabase connection with a simple query"""
        try:
            if not self.supabase_client:
                raise ValueError("Supabase client not initialized")

            # Try a simple query to test the connection
            # Using a system table that should always exist
            result = self.supabase_client.table("entity_master").select("count").limit(1).execute()

            logger.info("✅ Supabase connection test successful")
            logger.info(f"Connection validated - Response received")

        except Exception as e:
            logger.error(f"❌ Supabase connection test failed: {e}")
            # Try alternative test with different table
            try:
                # Try with a potentially different table structure
                result = self.supabase_client.from_("information_schema.tables").select("table_name").limit(1).execute()
                logger.info("✅ Supabase connection test successful (alternative method)")
            except Exception as e2:
                logger.error(f"❌ Alternative connection test also failed: {e2}")
                raise ConnectionError(f"Cannot establish connection to Supabase: {e}")

    def test_connection_sync(self) -> bool:
        """Synchronous connection test for debugging"""
        try:
            if not self.supabase_client:
                return False

            result = self.supabase_client.table("entity_master").select("count").limit(1).execute()
            logger.info("✅ Synchronous Supabase connection test successful")
            return True

        except Exception as e:
            logger.error(f"❌ Synchronous connection test failed: {e}")
            return False

# Global instance for shared use
db_manager = DatabaseManager()
