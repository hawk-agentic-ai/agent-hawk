"""
Debug Write Operations - Identify Silent Failure in process_hedge_prompt
"""

import os
import asyncio
import logging
from datetime import datetime

# Set environment with working keys
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"
# os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "sb_secret_X5tqrZ7xBcdFCgI41ciHFA_OKNlYi2D"  # Testing with anon key first

# Enhanced logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_write_operations():
    print("DEBUGGING WRITE OPERATIONS - process_hedge_prompt")
    print("=" * 60)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("CRITICAL: Supabase client not initialized")
            return False

        print(f"Database connection established with key type: {'SERVICE_ROLE' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'ANON'}")

        # Test 1: Direct table write test
        print("\n[TEST 1] Direct Table Write Test")
        print("-" * 40)

        # Test hedge_instructions write
        test_instruction = {
            "instruction_id": f"TEST_WRITE_{int(datetime.now().timestamp())}",
            "instruction_type": "I",
            "exposure_currency": "USD",
            "hedge_amount_order": 1000000,
            "hedge_method": "COH",
            "instruction_status": "Test",
            "created_by": "DEBUG_TEST",
            "created_date": datetime.now().isoformat(),
            "received_timestamp": datetime.now().isoformat(),
            "instruction_date": datetime.now().date().isoformat(),
            "trace_id": f"DEBUG-TEST_{int(datetime.now().timestamp())}",
            "notes": "Debug test write operation"
        }

        try:
            print("Attempting hedge_instructions insert...")
            result = hedge_processor.supabase_client.table("hedge_instructions").insert(test_instruction).execute()
            print(f"SUCCESS: hedge_instructions write - {len(result.data) if result.data else 0} records")
            print(f"Response data: {result.data}")
            instruction_id = result.data[0]["instruction_id"] if result.data else None
        except Exception as e:
            print(f"FAILED: hedge_instructions write error: {e}")
            print(f"Error type: {type(e)}")
            instruction_id = None

        # Test hedge_business_events write
        test_event = {
            "event_id": f"TEST_EVENT_{int(datetime.now().timestamp())}",
            "instruction_id": instruction_id or "TEST_INST_FALLBACK",
            "event_type": "Inception",
            "event_status": "Test",
            "stage_1a_status": "Testing",
            "created_by": "DEBUG_TEST",
            "created_date": datetime.now().isoformat(),
            "notes": "Debug test event write operation"
        }

        try:
            print("Attempting hedge_business_events insert...")
            result = hedge_processor.supabase_client.table("hedge_business_events").insert(test_event).execute()
            print(f"SUCCESS: hedge_business_events write - {len(result.data) if result.data else 0} records")
            print(f"Response data: {result.data}")
        except Exception as e:
            print(f"FAILED: hedge_business_events write error: {e}")
            print(f"Error type: {type(e)}")

        # Test 2: Full process_hedge_prompt workflow
        print("\n[TEST 2] Full process_hedge_prompt Workflow")
        print("-" * 40)

        try:
            print("Testing full prompt processing with write operations...")
            result = await hedge_processor.universal_prompt_processor(
                "Create USD 2M hedge inception instruction for testing",
                currency="USD",
                amount=2000000
            )

            print(f"Prompt processing result status: {result.get('status')}")
            print(f"Records affected: {result.get('records_affected', 0)}")
            print(f"Tables modified: {result.get('tables_modified', [])}")

            # Check for specific errors
            details = result.get("details", {})
            if "hedge_instructions_error" in details:
                print(f"HEDGE_INSTRUCTIONS ERROR: {details['hedge_instructions_error']}")
            if "hedge_business_events_error" in details:
                print(f"HEDGE_BUSINESS_EVENTS ERROR: {details['hedge_business_events_error']}")

            # Check if writes actually occurred
            if result.get("records_affected", 0) == 0:
                print("WARNING: No records were written despite no errors reported")

        except Exception as e:
            print(f"FAILED: Full workflow error: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()

        # Test 3: Permission validation
        print("\n[TEST 3] Database Permission Validation")
        print("-" * 40)

        try:
            # Test read access
            read_result = hedge_processor.supabase_client.table("hedge_instructions").select("instruction_id").limit(1).execute()
            print(f"READ permission: {'OK' if read_result.data is not None else 'FAILED'}")

            # Test write access with minimal data
            minimal_test = {
                "instruction_id": f"PERM_TEST_{int(datetime.now().timestamp())}",
                "instruction_type": "T",
                "created_by": "PERMISSION_TEST"
            }

            write_result = hedge_processor.supabase_client.table("hedge_instructions").insert(minimal_test).execute()
            print(f"WRITE permission: {'OK' if write_result.data else 'FAILED'}")

        except Exception as e:
            print(f"Permission test error: {e}")

        # Test 4: Check table constraints and requirements
        print("\n[TEST 4] Table Schema Requirements")
        print("-" * 40)

        try:
            # Attempt insert with missing required fields to see constraint errors
            incomplete_data = {"instruction_id": f"SCHEMA_TEST_{int(datetime.now().timestamp())}"}

            result = hedge_processor.supabase_client.table("hedge_instructions").insert(incomplete_data).execute()
            print("Unexpected success with incomplete data - check table constraints")

        except Exception as e:
            print(f"Schema constraint error (expected): {e}")
            # This helps identify required fields

        return True

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(debug_write_operations())