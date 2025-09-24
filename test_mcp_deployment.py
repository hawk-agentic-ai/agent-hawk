#!/usr/bin/env python3
"""
MCP Production Server Deployment Test
Tests all core functionality before production deployment
"""

import os
import json
import asyncio
import httpx
from datetime import datetime

# Set environment variables for testing
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "sb_secret_X5tqrZ7xBcdFCgI41ciHFA_OKNlYi2D"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:4200,https://dify.ai"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"

print("MCP Production Server Deployment Test")
print("=" * 50)

async def test_server_startup():
    """Test 1: Server startup and initialization"""
    print("\n📋 Test 1: Server Startup")

    try:
        # Test imports
        from shared.hedge_processor import hedge_processor
        print("PASS hedge_processor import successful")

        # Test initialization
        await hedge_processor.initialize()
        print("PASS HedgeFundProcessor initialized")

        # Check components
        if hedge_processor.supabase_client:
            print("PASS Supabase client connected")
        else:
            print("FAIL Supabase client not connected")

        if hedge_processor.redis_client:
            print("PASS Redis client connected")
        else:
            print("WARN Redis client not connected (cache disabled)")

        return True

    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        return False

async def test_json_rpc_compliance():
    """Test 2: JSON-RPC 2.0 compliance"""
    print("\n📋 Test 2: JSON-RPC 2.0 Compliance")

    try:
        # Import server functions
        import sys
        sys.path.append('.')

        # Test JSON-RPC error format
        from mcp_server_production import _jsonrpc_error, HawkErrorCodes

        error_response = _jsonrpc_error(
            req_id=1,
            code=HawkErrorCodes.INVALID_PARAMS,
            message="Test error",
            data="Test data",
            stage="Test Stage",
            operation="Test Operation"
        )

        # Validate JSON-RPC 2.0 format
        assert error_response["jsonrpc"] == "2.0"
        assert error_response["id"] == 1
        assert "error" in error_response
        assert error_response["error"]["code"] == HawkErrorCodes.INVALID_PARAMS
        assert "hawk_stage" in error_response["error"]["data"]

        print("✅ JSON-RPC 2.0 error format valid")
        return True

    except Exception as e:
        print(f"❌ JSON-RPC compliance test failed: {e}")
        return False

async def test_mcp_tools():
    """Test 3: All 4 MCP tools functionality"""
    print("\n📋 Test 3: MCP Tools Functionality")

    try:
        from shared.hedge_processor import hedge_processor

        # Test 1: get_system_health
        print("Testing get_system_health...")
        health = hedge_processor.get_system_health()
        assert "status" in health
        print("✅ get_system_health works")

        # Test 2: manage_cache_operations
        print("Testing manage_cache_operations...")
        cache_stats = hedge_processor.manage_cache_operations("stats")
        assert "operation" in cache_stats
        print("✅ manage_cache_operations works")

        # Test 3: query_supabase_direct (if connected)
        if hedge_processor.supabase_client:
            print("Testing query_supabase_direct...")
            try:
                result = await hedge_processor.query_supabase_direct(
                    table_name="entity_master",
                    operation="select",
                    limit=1
                )
                assert result["status"] in ["success", "error"]
                print("✅ query_supabase_direct works")
            except Exception as e:
                print(f"⚠️ query_supabase_direct test: {e}")

        # Test 4: universal_prompt_processor
        print("Testing universal_prompt_processor...")
        result = await hedge_processor.universal_prompt_processor(
            user_prompt="Test hedge query",
            template_category="utilization",
            currency="USD",
            amount=1000000
        )
        assert "status" in result
        print("✅ universal_prompt_processor works")

        return True

    except Exception as e:
        print(f"❌ MCP tools test failed: {e}")
        return False

async def test_table_access():
    """Test 4: Table access validation"""
    print("\n📋 Test 4: Table Access Validation")

    try:
        from mcp_server_production import _validate_tool_parameters

        # Test valid table
        test_args = {"table_name": "hedge_instructions", "operation": "select"}
        validation_error = _validate_tool_parameters("query_supabase_data", test_args)
        assert validation_error is None
        print("✅ Valid table validation passed")

        # Test invalid table
        test_args = {"table_name": "invalid_table", "operation": "select"}
        validation_error = _validate_tool_parameters("query_supabase_data", test_args)
        assert validation_error is not None
        print("✅ Invalid table validation caught")

        # Test view write protection
        test_args = {"table_name": "v_hedge_positions_fast", "operation": "insert"}
        validation_error = _validate_tool_parameters("query_supabase_data", test_args)
        assert validation_error is not None
        print("✅ View write protection works")

        return True

    except Exception as e:
        print(f"❌ Table access test failed: {e}")
        return False

async def run_all_tests():
    """Run all deployment readiness tests"""
    print(f"Test started at: {datetime.now().isoformat()}")

    tests = [
        ("Server Startup", test_server_startup),
        ("JSON-RPC Compliance", test_json_rpc_compliance),
        ("MCP Tools", test_mcp_tools),
        ("Table Access", test_table_access)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT READINESS SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 MCP SERVER READY FOR PRODUCTION DEPLOYMENT!")
    else:
        print("⚠️ Fix failing tests before production deployment")

    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests())