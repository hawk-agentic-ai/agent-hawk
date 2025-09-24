"""
Check valid values for constraint fields
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def check_valid_values():
    print("CHECKING VALID VALUES FOR CONSTRAINT FIELDS")
    print("=" * 55)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return

        # Check existing instruction_status values
        print("\n[hedge_instructions.instruction_status values]")
        print("-" * 40)
        try:
            result = hedge_processor.supabase_client.table("hedge_instructions").select("instruction_status").limit(20).execute()
            if result.data:
                unique_statuses = list(set([r["instruction_status"] for r in result.data if r["instruction_status"]]))
                print(f"Valid instruction_status values: {unique_statuses}")
            else:
                print("No existing records to check instruction_status values")
        except Exception as e:
            print(f"Error checking instruction_status: {e}")

        # Check existing instruction_type values
        print("\n[hedge_instructions.instruction_type values]")
        print("-" * 40)
        try:
            result = hedge_processor.supabase_client.table("hedge_instructions").select("instruction_type").limit(20).execute()
            if result.data:
                unique_types = list(set([r["instruction_type"] for r in result.data if r["instruction_type"]]))
                print(f"Valid instruction_type values: {unique_types}")
            else:
                print("No existing records to check instruction_type values")
        except Exception as e:
            print(f"Error checking instruction_type: {e}")

        # Check existing event_status values
        print("\n[hedge_business_events.event_status values]")
        print("-" * 40)
        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").select("event_status").limit(20).execute()
            if result.data:
                unique_statuses = list(set([r["event_status"] for r in result.data if r["event_status"]]))
                print(f"Valid event_status values: {unique_statuses}")
            else:
                print("No existing records to check event_status values")
        except Exception as e:
            print(f"Error checking event_status: {e}")

        # Check existing business_event_type values
        print("\n[hedge_business_events.business_event_type values]")
        print("-" * 40)
        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").select("business_event_type").limit(20).execute()
            if result.data:
                unique_types = list(set([r["business_event_type"] for r in result.data if r["business_event_type"]]))
                print(f"Valid business_event_type values: {unique_types}")
            else:
                print("No existing records to check business_event_type values")
        except Exception as e:
            print(f"Error checking business_event_type: {e}")

    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_valid_values())