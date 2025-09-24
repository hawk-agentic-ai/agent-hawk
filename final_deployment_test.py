"""
Final MCP Production Server Deployment Test
"""

import os
import asyncio

# Set environment variables with working keys
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:4200,https://dify.ai"

async def comprehensive_test():
    print("FINAL MCP PRODUCTION SERVER TEST")
    print("=" * 50)

    tests_passed = 0
    total_tests = 6

    # Test 1: Server initialization
    print("\n[1/6] Server Initialization")
    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if hedge_processor.supabase_client:
            print("PASS: Database connected")
            tests_passed += 1
        else:
            print("FAIL: Database connection failed")
    except Exception as e:
        print(f"FAIL: Initialization error: {e}")

    # Test 2: JSON-RPC compliance
    print("\n[2/6] JSON-RPC 2.0 Compliance")
    try:
        from mcp_server_production import _jsonrpc_error, HawkErrorCodes
        error = _jsonrpc_error(1, HawkErrorCodes.STAGE_1A_VALIDATION_FAILED, "Test", stage="Stage 1A")
        assert error["jsonrpc"] == "2.0" and "hawk_stage" in error["error"]["data"]
        print("PASS: JSON-RPC 2.0 format validated")
        tests_passed += 1
    except Exception as e:
        print(f"FAIL: JSON-RPC test error: {e}")

    # Test 3: All MCP tools
    print("\n[3/6] MCP Tools Functionality")
    try:
        # Tool 1: System health
        health = hedge_processor.get_system_health()
        assert "status" in health

        # Tool 2: Cache management
        cache = hedge_processor.manage_cache_operations("stats")
        assert "operation" in cache

        # Tool 3: Database query
        db_result = await hedge_processor.query_supabase_direct("entity_master", limit=1)
        assert db_result["status"] == "success"

        # Tool 4: Prompt processing
        prompt_result = await hedge_processor.universal_prompt_processor(
            "Test USD 1M hedge utilization", currency="USD", amount=1000000
        )
        assert "status" in prompt_result

        print("PASS: All 4 MCP tools functional")
        tests_passed += 1
    except Exception as e:
        print(f"FAIL: MCP tools error: {e}")

    # Test 4: Table access validation
    print("\n[4/6] Table Access & CRUD")
    try:
        from mcp_server_production import _validate_tool_parameters

        # Valid table
        result = _validate_tool_parameters("query_supabase_data",
            {"table_name": "hedge_instructions", "operation": "select"})
        assert result is None

        # Invalid table
        result = _validate_tool_parameters("query_supabase_data",
            {"table_name": "invalid_table"})
        assert result is not None

        # View protection
        result = _validate_tool_parameters("query_supabase_data",
            {"table_name": "v_hedge_positions_fast", "operation": "insert"})
        assert result is not None

        print("PASS: Table validation and CRUD protection works")
        tests_passed += 1
    except Exception as e:
        print(f"FAIL: Table access error: {e}")

    # Test 5: Error handling
    print("\n[5/6] Error Handling")
    try:
        from mcp_server_production import _categorize_hedge_error

        # Test error categorization
        test_exception = Exception("Insufficient capacity test")
        code, msg, stage, op = _categorize_hedge_error(test_exception, "process_hedge_prompt",
            {"template_category": "utilization"})

        assert code == -32001  # STAGE_1A_VALIDATION_FAILED
        assert "Stage 1A" in stage

        print("PASS: Error categorization and handling works")
        tests_passed += 1
    except Exception as e:
        print(f"FAIL: Error handling test: {e}")

    # Test 6: Real database operation
    print("\n[6/6] Database CRUD Operations")
    try:
        # Test SELECT operation
        result = await hedge_processor.query_supabase_direct(
            table_name="entity_master",
            operation="select",
            limit=2
        )

        if result["status"] == "success":
            print(f"PASS: Database SELECT works ({result['records']} records)")
            tests_passed += 1
        else:
            print(f"FAIL: Database SELECT failed: {result.get('error')}")

    except Exception as e:
        print(f"FAIL: Database operation error: {e}")

    # Final results
    print("\n" + "=" * 50)
    print("DEPLOYMENT READINESS RESULTS")
    print("=" * 50)
    print(f"Tests Passed: {tests_passed}/{total_tests}")

    if tests_passed == total_tests:
        print("\nSTATUS: MCP SERVER PRODUCTION READY!")
        print("- All core functionality working")
        print("- Database connected and operational")
        print("- Error handling robust")
        print("- JSON-RPC 2.0 compliant")
        print("- Ready for Dify integration")
    elif tests_passed >= 4:
        print("\nSTATUS: MCP SERVER MOSTLY READY")
        print("- Core functionality working")
        print("- Minor issues to address")
    else:
        print("\nSTATUS: NEEDS MORE WORK")
        print("- Major issues to resolve")

    return tests_passed == total_tests

if __name__ == "__main__":
    asyncio.run(comprehensive_test())