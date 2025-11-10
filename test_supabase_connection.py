#!/usr/bin/env python3
"""
Test script for Supabase connection debugging
Run this to verify the connection works before implementing strict write validations
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Explicitly load .env file for testing
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env file from: {env_path}")
    else:
        logger.warning(f"No .env file found at: {env_path}")
except ImportError:
    logger.warning("python-dotenv not available - environment variables may not load")

async def test_supabase_connection():
    """Test the Supabase connection with detailed debugging"""

    logger.info("Starting Supabase connection test...")

    # Check environment variables
    logger.info("Checking environment variables:")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

    logger.info(f"   SUPABASE_URL: {supabase_url}")
    logger.info(f"   Service key: {'OK' if supabase_service_key else 'MISSING'} ({len(supabase_service_key) if supabase_service_key else 0} chars)")
    logger.info(f"   Anon key: {'OK' if supabase_anon_key else 'MISSING'} ({len(supabase_anon_key) if supabase_anon_key else 0} chars)")

    if not supabase_url:
        logger.error("ERROR: SUPABASE_URL not found in environment variables")
        return False

    if not (supabase_service_key or supabase_anon_key):
        logger.error("ERROR: Neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_ANON_KEY found")
        return False

    # Test the database manager
    try:
        logger.info("Testing DatabaseManager initialization...")
        from shared.supabase_client import DatabaseManager

        db_manager = DatabaseManager()
        supabase_client, redis_client = await db_manager.initialize_connections()

        if not supabase_client:
            logger.error("ERROR: Supabase client initialization failed")
            return False

        logger.info("SUCCESS: DatabaseManager initialized successfully")

        # Test a simple query
        logger.info("Testing simple database query...")
        try:
            # Try querying a basic table
            result = supabase_client.table("entity_master").select("*").limit(1).execute()
            logger.info(f"SUCCESS: Query successful - Found {len(result.data) if result.data else 0} records")

        except Exception as e:
            logger.warning(f"WARNING: entity_master query failed: {e}")

            # Try alternative query
            try:
                result = supabase_client.rpc('version').execute()
                logger.info("SUCCESS: Alternative query successful (database version check)")
            except Exception as e2:
                logger.error(f"ERROR: All queries failed: {e2}")
                return False

        # Test write permissions (if using service role key)
        if supabase_service_key:
            logger.info("Testing write permissions (service role)...")
            try:
                # Try to insert and immediately delete a test record
                test_data = {
                    "entity_id": "TEST_CONN_001",
                    "entity_name": "Connection Test Entity",
                    "currency_code": "USD",
                    "nav_type": "COI",
                    "active_flag": "Y"
                }

                # Insert test record
                insert_result = supabase_client.table("entity_master").insert(test_data).execute()

                if insert_result.data:
                    logger.info("SUCCESS: Write test successful - test record inserted")

                    # Clean up - delete test record
                    delete_result = supabase_client.table("entity_master")\
                        .delete().eq("entity_id", "TEST_CONN_001").execute()
                    logger.info("CLEANUP: Test record cleaned up")
                else:
                    logger.warning("WARNING: Write test unclear - no data returned")

            except Exception as e:
                logger.warning(f"WARNING: Write test failed (this may be normal): {e}")

        logger.info("SUCCESS: Connection test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"ERROR: Connection test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connection_sync():
    """Synchronous wrapper for the connection test"""
    return asyncio.run(test_supabase_connection())

if __name__ == "__main__":
    print("=" * 60)
    print("SUPABASE CONNECTION TEST")
    print("=" * 60)

    success = test_connection_sync()

    if success:
        print("\nSUCCESS: CONNECTION TEST PASSED")
        print("   Ready to implement strict write validations!")
        sys.exit(0)
    else:
        print("\nERROR: CONNECTION TEST FAILED")
        print("   Please fix connection issues before proceeding.")
        sys.exit(1)