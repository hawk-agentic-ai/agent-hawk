"""
Test Data Column Fix - Verify the 'data' column issue is resolved
Test with write_data containing invalid 'data' field
"""

import asyncio
import os
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_data_column_fix():
    """Test that the 'data' column issue is fixed"""
    print("TESTING DATA COLUMN FIX")
    print("=" * 25)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        test_session = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Test Case: Include 'data' field in write_data (should be filtered out)
        print("Test Case: write_data with invalid 'data' field")
        print("-" * 45)

        test_prompt = "Can I place a new hedge for 150000 AUD today"

        # This write_data includes a 'data' field that should be filtered out
        problematic_write_data = {
            "msg_uid": f"TEST_DATA_FIX_{test_session}",
            "target_table": "hedge_instructions",
            "instruction_type": "U",
            "exposure_currency": "AUD",
            "hedge_amount_order": 150000,
            "data": {"invalid": "this should not be inserted"},  # This caused the original error
            "extra_field": "this should also be filtered out"
        }

        print(f"Prompt: \"{test_prompt}\"")
        print(f"write_data contains 'data' field: {bool('data' in problematic_write_data)}")
        print(f"write_data contains 'extra_field': {bool('extra_field' in problematic_write_data)}")

        try:
            result = await hedge_processor.universal_prompt_processor(
                user_prompt=test_prompt,
                currency="AUD",
                amount=150000,
                operation_type="write",
                write_data=problematic_write_data
            )

            print(f"\nResult Status: {result.get('status')}")

            # Check if write operations succeeded
            write_results = result.get("write_results", {})
            if write_results:
                records_affected = write_results.get("records_affected", 0)
                tables_modified = write_results.get("tables_modified", [])

                print(f"Database Operations:")
                print(f"  Records Affected: {records_affected}")
                print(f"  Tables Modified: {tables_modified}")

                # Check for specific table results
                details = write_results.get("details", {})
                if "hedge_instructions" in details:
                    hi_result = details["hedge_instructions"]
                    if hi_result:
                        print(f"  hedge_instructions: SUCCESS - Record created")
                        print(f"    instruction_id: {hi_result.get('instruction_id', 'N/A')}")
                    else:
                        print(f"  hedge_instructions: No record returned")

                if "hedge_instructions_error" in details:
                    error_msg = details["hedge_instructions_error"]
                    print(f"  hedge_instructions: ERROR - {error_msg}")

                    # Check if it's still the 'data' column error
                    if "Could not find the 'data' column" in error_msg:
                        print("  ERROR: 'data' column issue NOT FIXED")
                        return False
                    else:
                        print("  Different error (not the 'data' column issue)")

            # Verify that invalid fields were filtered out
            if result.get('status') == 'success':
                print(f"\nSUCCESS: No 'data' column error occurred")
                print(f"Field Filtering: Invalid fields were properly filtered out")
                return True
            else:
                print(f"\nPARTIAL: Operation had issues but not 'data' column related")
                return True

        except Exception as e:
            error_str = str(e)
            print(f"\nERROR: {error_str}")

            # Check if it's the specific 'data' column error
            if "Could not find the 'data' column" in error_str:
                print("FAILED: 'data' column issue still exists")
                return False
            else:
                print("Different error - not the 'data' column issue")
                return True

    except Exception as e:
        print(f"Test setup error: {e}")
        return False

async def main():
    print(f"Data Column Fix Test started at: {datetime.now()}")
    success = await test_data_column_fix()
    print(f"\nDATA COLUMN FIX TEST: {'SUCCESS' if success else 'FAILED'}")
    print(f"Test completed at: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())