"""
Test Fixed Write Operations
"""

import os
import asyncio
import hashlib
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_fixed_writes():
    print("TESTING FIXED WRITE OPERATIONS")
    print("=" * 50)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return False

        # Test 1: Fixed hedge_instructions write
        print("\n[TEST 1] Fixed hedge_instructions Write")
        print("-" * 40)

        # Generate unique fingerprint
        timestamp = int(datetime.now().timestamp())
        fingerprint_data = f"USD_1500000_test_{timestamp}"
        instruction_fingerprint = hashlib.md5(fingerprint_data.encode()).hexdigest()

        test_instruction = {
            "instruction_id": f"FIXED_TEST_{timestamp}",
            "instruction_type": "I",
            "exposure_currency": "USD",
            "hedge_amount_order": 1500000,
            "hedge_method": "COH",
            "instruction_status": "Received",
            "created_by": "FIXED_TEST",
            "created_date": datetime.now().isoformat(),
            "received_timestamp": datetime.now().isoformat(),
            "instruction_date": datetime.now().date().isoformat(),
            "trace_id": f"FIXED-TEST_{timestamp}"
        }

        try:
            result = hedge_processor.supabase_client.table("hedge_instructions").insert(test_instruction).execute()
            print(f"SUCCESS: hedge_instructions write - {len(result.data) if result.data else 0} records")
            instruction_id = result.data[0]["instruction_id"] if result.data else None
            print(f"  Instruction ID: {instruction_id}")
        except Exception as e:
            print(f"FAILED: hedge_instructions write error: {e}")
            instruction_id = None

        # Test 2: Fixed hedge_business_events write
        print("\n[TEST 2] Fixed hedge_business_events Write")
        print("-" * 40)

        test_event = {
            "event_id": f"FIXED_EVENT_{int(datetime.now().timestamp())}",
            "instruction_id": instruction_id or "FALLBACK_INST_ID",
            "entity_id": "ENTITY0001",  # Required field
            "nav_type": "COI",  # Required field
            "currency_type": "Matched",  # Required field
            "business_event_type": "Initiation",  # Fixed column name
            "event_status": "Pending",
            "stage_1a_status": "Pending",
            "created_by": "FIXED_TEST",
            "created_date": datetime.now().isoformat(),
            "notes": "Fixed test event write operation"
        }

        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").insert(test_event).execute()
            print(f"SUCCESS: hedge_business_events write - {len(result.data) if result.data else 0} records")
            print(f"  Event ID: {result.data[0]['event_id'] if result.data else 'None'}")
        except Exception as e:
            print(f"FAILED: hedge_business_events write error: {e}")

        # Test 3: Full process_hedge_prompt workflow with fixed schema
        print("\n[TEST 3] Full process_hedge_prompt Workflow (Fixed)")
        print("-" * 40)

        try:
            result = await hedge_processor.universal_prompt_processor(
                "Create USD 3M hedge inception instruction for schema test",
                currency="USD",
                amount=3000000
            )

            print(f"Status: {result.get('status')}")
            print(f"Records affected: {result.get('records_affected', 0)}")
            print(f"Tables modified: {result.get('tables_modified', [])}")

            details = result.get("details", {})
            if "hedge_instructions_error" in details:
                print(f"HEDGE_INSTRUCTIONS ERROR: {details['hedge_instructions_error']}")
            elif "hedge_instructions" in details:
                print(f"hedge_instructions created: {details['hedge_instructions'].get('instruction_id')}")

            if "hedge_business_events_error" in details:
                print(f"HEDGE_BUSINESS_EVENTS ERROR: {details['hedge_business_events_error']}")
            elif "hedge_business_events" in details:
                print(f"hedge_business_events created: {details['hedge_business_events'].get('event_id')}")

            return result.get("records_affected", 0) > 0

        except Exception as e:
            print(f"FAILED: Full workflow error: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fixed_writes())
    print(f"\n{'SUCCESS' if success else 'NEEDS MORE WORK'}: Write operations test")