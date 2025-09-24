"""
Check required fields and get sample values
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def check_required_fields():
    print("CHECKING REQUIRED FIELDS")
    print("=" * 30)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return

        # Check entity_id values from hedge_business_events
        print("\n[entity_id values from hedge_business_events]")
        print("-" * 40)
        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").select("entity_id").limit(10).execute()
            if result.data:
                unique_entities = list(set([r["entity_id"] for r in result.data if r["entity_id"]]))
                print(f"Sample entity_id values: {unique_entities[:5]}")
        except Exception as e:
            print(f"Error checking entity_id: {e}")

        # Check entity_master table for valid entity_ids
        print("\n[entity_master table]")
        print("-" * 20)
        try:
            result = hedge_processor.supabase_client.table("entity_master").select("entity_id").limit(5).execute()
            if result.data:
                entities = [r["entity_id"] for r in result.data if r["entity_id"]]
                print(f"Available entity_ids: {entities}")
        except Exception as e:
            print(f"Error checking entity_master: {e}")

        # Check instruction_fingerprint field - what makes it unique
        print("\n[instruction_fingerprint patterns]")
        print("-" * 35)
        try:
            result = hedge_processor.supabase_client.table("hedge_instructions").select("instruction_fingerprint").limit(5).execute()
            if result.data:
                fingerprints = [r["instruction_fingerprint"] for r in result.data if r["instruction_fingerprint"]]
                print(f"Sample fingerprints: {fingerprints}")
        except Exception as e:
            print(f"Error checking instruction_fingerprint: {e}")

    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(check_required_fields())