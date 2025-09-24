"""
Test MCP Workflow specifically
"""

import os
import asyncio
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_mcp_workflow():
    print("TESTING MCP WORKFLOW SPECIFICALLY")
    print("=" * 40)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return False

        # Test different prompt variations to trigger writes
        test_prompts = [
            ("Create USD 6M hedge inception instruction", "USD", 6000000),
            ("Generate new hedge initiation for USD 7M", "USD", 7000000),
            ("Process hedge inception USD 8M exposure", "USD", 8000000)
        ]

        for i, (prompt, currency, amount) in enumerate(test_prompts, 1):
            print(f"\n[TEST {i}] Prompt: '{prompt}'")
            print("-" * 50)

            try:
                result = await hedge_processor.universal_prompt_processor(
                    prompt, currency=currency, amount=amount
                )

                print(f"Status: {result.get('status')}")
                print(f"Records affected: {result.get('records_affected', 0)}")
                print(f"Tables modified: {result.get('tables_modified', [])}")
                print(f"Details keys: {list(result.get('details', {}).keys())}")

                # Check for write errors
                details = result.get("details", {})
                if "hedge_instructions_error" in details:
                    print(f"hedge_instructions error: {details['hedge_instructions_error']}")
                if "hedge_business_events_error" in details:
                    print(f"hedge_business_events error: {details['hedge_business_events_error']}")

                if result.get("records_affected", 0) > 0:
                    print(f"SUCCESS: {result.get('records_affected')} records created!")
                    return True
                else:
                    print("No records created")

            except Exception as e:
                print(f"Error in test {i}: {e}")

        # Test explicit write operation
        print(f"\n[TEST EXPLICIT WRITE] Force hedge_instructions write")
        print("-" * 50)

        try:
            # Force a write by providing write_data
            write_data = {"target_table": "hedge_instructions"}
            result = await hedge_processor.universal_prompt_processor(
                "Create USD 9M hedge inception for explicit test",
                currency="USD",
                amount=9000000,
                write_data=write_data
            )

            print(f"Explicit write result: {result.get('records_affected', 0)} records")
            print(f"Tables modified: {result.get('tables_modified', [])}")

            if result.get("records_affected", 0) > 0:
                return True

        except Exception as e:
            print(f"Explicit write error: {e}")

        return False

    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_workflow())
    print(f"\nMCP WORKFLOW RESULT: {'SUCCESS' if success else 'NEEDS INVESTIGATION'}")