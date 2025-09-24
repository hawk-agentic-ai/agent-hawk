"""
Debug the intermittent test failure in MCP Tools
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def debug_mcp_tools():
    print("DEBUG: MCP Tools Individual Tests")
    print("=" * 40)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()
        print("PASS: Initialization complete")

        # Test each tool individually with detailed error catching

        # Tool 1: System Health
        print("\nTesting Tool 1: get_system_health")
        try:
            health = hedge_processor.get_system_health()
            print(f"Result: {health}")
            if "status" not in health:
                print("ERROR: 'status' key missing from health result")
                return False
            print("PASS: System health works")
        except Exception as e:
            print(f"ERROR: System health failed: {e}")
            print(f"Error type: {type(e)}")
            return False

        # Tool 2: Cache Management
        print("\nTesting Tool 2: manage_cache_operations")
        try:
            cache = hedge_processor.manage_cache_operations("stats")
            print(f"Result: {cache}")
            if "operation" not in cache:
                print("ERROR: 'operation' key missing from cache result")
                return False
            print("PASS: Cache operations work")
        except Exception as e:
            print(f"ERROR: Cache operations failed: {e}")
            print(f"Error type: {type(e)}")
            return False

        # Tool 3: Database Query
        print("\nTesting Tool 3: query_supabase_direct")
        try:
            db_result = await hedge_processor.query_supabase_direct("entity_master", limit=1)
            print(f"Result: {db_result}")
            if db_result.get("status") != "success":
                print(f"ERROR: Database query failed: {db_result.get('error')}")
                return False
            print("PASS: Database query works")
        except Exception as e:
            print(f"ERROR: Database query failed: {e}")
            print(f"Error type: {type(e)}")
            return False

        # Tool 4: Prompt Processing
        print("\nTesting Tool 4: universal_prompt_processor")
        try:
            prompt_result = await hedge_processor.universal_prompt_processor(
                "Test USD 1M hedge utilization",
                currency="USD",
                amount=1000000
            )
            print(f"Result keys: {list(prompt_result.keys()) if prompt_result else 'None'}")
            if not prompt_result or "status" not in prompt_result:
                print("ERROR: 'status' key missing from prompt result")
                return False
            print("PASS: Prompt processing works")
        except Exception as e:
            print(f"ERROR: Prompt processing failed: {e}")
            print(f"Error type: {type(e)}")
            return False

        print("\nALL MCP TOOLS WORKING CORRECTLY")
        return True

    except Exception as e:
        print(f"CRITICAL ERROR during MCP tools test: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(debug_mcp_tools())