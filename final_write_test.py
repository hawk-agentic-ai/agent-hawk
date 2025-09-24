"""
Final write test with complete fields
"""

import os
import asyncio
import time
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def final_write_test():
    print("FINAL WRITE TEST WITH ALL FIELDS")
    print("=" * 40)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return False

        # Check hedging_instrument values first
        print("\n[Checking hedging_instrument values]")
        result = hedge_processor.supabase_client.table("hedge_business_events").select("hedging_instrument").limit(10).execute()
        if result.data:
            instruments = list(set([r["hedging_instrument"] for r in result.data if r["hedging_instrument"]]))
            print(f"Valid hedging_instrument values: {instruments}")

        # Generate very unique timestamp to avoid fingerprint collision
        import random
        unique_timestamp = int(time.time() * 1000000) + random.randint(1000, 9999)  # add randomness

        # Test 1: hedge_instructions with minimal but sufficient fields
        print(f"\n[TEST 1] hedge_instructions (timestamp: {unique_timestamp})")
        print("-" * 50)

        test_instruction = {
            "instruction_id": f"FINAL_TEST_{unique_timestamp}",
            "instruction_type": "I",
            "exposure_currency": "USD",
            "hedge_amount_order": 5000000 + random.randint(1000, 99999),  # Vary amount to avoid fingerprint collision
            "hedge_method": "COH",
            "instruction_status": "Received",
            "created_by": "FINAL_TEST",
            "created_date": datetime.now().isoformat(),
            "received_timestamp": datetime.now().isoformat(),
            "instruction_date": datetime.now().date().isoformat(),
            "trace_id": f"FINAL-TEST_{unique_timestamp}"
        }

        try:
            result = hedge_processor.supabase_client.table("hedge_instructions").insert(test_instruction).execute()
            print(f"SUCCESS: hedge_instructions - {len(result.data) if result.data else 0} records")
            instruction_id = result.data[0]["instruction_id"] if result.data else None
            print(f"  Instruction ID: {instruction_id}")
        except Exception as e:
            print(f"FAILED: hedge_instructions error: {e}")
            instruction_id = None

        # Test 2: hedge_business_events with all required fields
        print(f"\n[TEST 2] hedge_business_events")
        print("-" * 30)

        test_event = {
            "event_id": f"FINAL_EVENT_{unique_timestamp}",
            "instruction_id": instruction_id or "FALLBACK_INST_ID",
            "entity_id": "ENTITY0001",
            "nav_type": "COI",
            "currency_type": "Matched",
            "hedging_instrument": instruments[0] if instruments else "FX_Swap",  # Use actual value or fallback
            "accounting_method": "COH",  # Required field
            "notional_amount": 5000000,  # Required field
            "trade_date": datetime.now().date().isoformat(),  # Required field
            "business_event_type": "Initiation",
            "event_status": "Pending",
            "stage_1a_status": "Pending",
            "created_by": "FINAL_TEST",
            "created_date": datetime.now().isoformat(),
            "notes": "Final complete test write operation"
        }

        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").insert(test_event).execute()
            print(f"SUCCESS: hedge_business_events - {len(result.data) if result.data else 0} records")
            event_id = result.data[0]["event_id"] if result.data else None
            print(f"  Event ID: {event_id}")
        except Exception as e:
            print(f"FAILED: hedge_business_events error: {e}")

        # Test 3: MCP workflow
        print(f"\n[TEST 3] Full MCP Workflow")
        print("-" * 25)

        try:
            result = await hedge_processor.universal_prompt_processor(
                f"Create USD 4M hedge inception for final test {unique_timestamp}",
                currency="USD",
                amount=4000000
            )

            print(f"Status: {result.get('status')}")
            print(f"Records affected: {result.get('records_affected', 0)}")
            print(f"Tables modified: {result.get('tables_modified', [])}")

            if result.get("records_affected", 0) > 0:
                print("SUCCESS: MCP workflow created records!")
                return True
            else:
                print("PARTIAL: MCP workflow ran but no records created")
                return False

        except Exception as e:
            print(f"FAILED: MCP workflow error: {e}")
            return False

    except Exception as e:
        print(f"Critical error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(final_write_test())
    print(f"\nFINAL RESULT: {'WRITE OPERATIONS WORKING' if success else 'STILL NEEDS FIXES'}")