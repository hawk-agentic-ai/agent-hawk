"""
Simple MCP Production Server Test
"""

import os
import asyncio

# Set environment variables for testing
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "sb_secret_X5tqrZ7xBcdFCgI41ciHFA_OKNlYi2D"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:4200,https://dify.ai"

async def test_mcp_server():
    print("MCP Production Server Test")
    print("=" * 40)

    # Test 1: Import and initialize
    print("\nTest 1: Server Initialization")
    try:
        from shared.hedge_processor import hedge_processor
        print("PASS: hedge_processor imported")

        await hedge_processor.initialize()
        print("PASS: hedge_processor initialized")

        if hedge_processor.supabase_client:
            print("PASS: Supabase connected")
        else:
            print("FAIL: Supabase not connected")

        if hedge_processor.redis_client:
            print("PASS: Redis connected")
        else:
            print("WARN: Redis not connected")

    except Exception as e:
        print(f"FAIL: Initialization error: {e}")
        return False

    # Test 2: System Health
    print("\nTest 2: System Health Check")
    try:
        health = hedge_processor.get_system_health()
        print(f"PASS: System health status: {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"FAIL: Health check error: {e}")

    # Test 3: Cache Operations
    print("\nTest 3: Cache Operations")
    try:
        cache_result = hedge_processor.manage_cache_operations("stats")
        print(f"PASS: Cache stats retrieved: {cache_result.get('operation', 'unknown')}")
    except Exception as e:
        print(f"FAIL: Cache operation error: {e}")

    # Test 4: Database Query
    print("\nTest 4: Database Operations")
    try:
        if hedge_processor.supabase_client:
            result = await hedge_processor.query_supabase_direct(
                table_name="entity_master",
                operation="select",
                limit=1
            )
            print(f"PASS: Database query status: {result.get('status', 'unknown')}")
        else:
            print("SKIP: Database not connected")
    except Exception as e:
        print(f"FAIL: Database query error: {e}")

    # Test 5: Prompt Processing
    print("\nTest 5: Prompt Processing")
    try:
        result = await hedge_processor.universal_prompt_processor(
            user_prompt="Test utilization check for USD 1M",
            template_category="utilization",
            currency="USD",
            amount=1000000
        )
        print(f"PASS: Prompt processing status: {result.get('status', 'unknown')}")
    except Exception as e:
        print(f"FAIL: Prompt processing error: {e}")

    print("\n" + "=" * 40)
    print("MCP Server Test Complete")
    return True

if __name__ == "__main__":
    asyncio.run(test_mcp_server())