"""
Check currency_type values and understand fingerprint issue
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def check_fields():
    print("CHECKING REMAINING FIELD ISSUES")
    print("=" * 40)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return

        # Check currency_type values
        print("\n[currency_type values]")
        print("-" * 25)
        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").select("currency_type").limit(10).execute()
            if result.data:
                unique_currency_types = list(set([r["currency_type"] for r in result.data if r["currency_type"]]))
                print(f"Valid currency_type values: {unique_currency_types}")
        except Exception as e:
            print(f"Error checking currency_type: {e}")

        # Check if we can insert without certain fields - minimal insert test
        print("\n[Minimal Insert Test - hedge_instructions]")
        print("-" * 45)
        minimal_instruction = {
            "instruction_id": f"MINIMAL_TEST_{int(asyncio.get_event_loop().time() * 1000)}",
            "instruction_type": "I",
            "exposure_currency": "USD",
            "created_by": "MINIMAL_TEST"
        }

        try:
            result = hedge_processor.supabase_client.table("hedge_instructions").insert(minimal_instruction).execute()
            print(f"SUCCESS: Minimal instruction insert - {len(result.data) if result.data else 0} records")
            if result.data:
                print(f"Generated fingerprint: {result.data[0].get('instruction_fingerprint')}")
        except Exception as e:
            print(f"FAILED: Minimal instruction insert: {e}")

    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(check_fields())