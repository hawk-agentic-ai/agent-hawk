"""
Check actual table schemas for hedge_instructions and hedge_business_events
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def check_table_schemas():
    print("CHECKING ACTUAL TABLE SCHEMAS")
    print("=" * 50)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return

        # Check hedge_instructions table structure
        print("\n[TABLE 1] hedge_instructions")
        print("-" * 30)
        try:
            # Get existing records to see actual column structure
            result = hedge_processor.supabase_client.table("hedge_instructions").select("*").limit(1).execute()
            if result.data and len(result.data) > 0:
                print("Existing columns:")
                for column in result.data[0].keys():
                    print(f"  - {column}")
            else:
                print("No existing records to examine column structure")

                # Try minimal insert to see what's required
                try:
                    test_insert = {"instruction_id": "SCHEMA_TEST_001"}
                    result = hedge_processor.supabase_client.table("hedge_instructions").insert(test_insert).execute()
                except Exception as e:
                    print(f"Required field error: {e}")
        except Exception as e:
            print(f"Error checking hedge_instructions: {e}")

        # Check hedge_business_events table structure
        print("\n[TABLE 2] hedge_business_events")
        print("-" * 30)
        try:
            # Get existing records to see actual column structure
            result = hedge_processor.supabase_client.table("hedge_business_events").select("*").limit(1).execute()
            if result.data and len(result.data) > 0:
                print("Existing columns:")
                for column in result.data[0].keys():
                    print(f"  - {column}")
            else:
                print("No existing records to examine column structure")

                # Try minimal insert to see what's required
                try:
                    test_insert = {"event_id": "SCHEMA_TEST_001"}
                    result = hedge_processor.supabase_client.table("hedge_business_events").insert(test_insert).execute()
                except Exception as e:
                    print(f"Required field error: {e}")
        except Exception as e:
            print(f"Error checking hedge_business_events: {e}")

        # Test other potential table names
        print("\n[ALTERNATIVE TABLES CHECK]")
        print("-" * 30)

        potential_tables = [
            "hedge_instruction",  # singular
            "instruction_master",
            "hedge_event",       # singular
            "business_events",   # different prefix
            "hedge_operations",
            "instruction_events"
        ]

        for table_name in potential_tables:
            try:
                result = hedge_processor.supabase_client.table(table_name).select("*").limit(1).execute()
                print(f"✓ Table '{table_name}' exists with {len(result.data)} records")
                if result.data:
                    print(f"  Columns: {list(result.data[0].keys())}")
            except Exception as e:
                if "schema cache" in str(e):
                    print(f"✗ Table '{table_name}' does not exist")
                else:
                    print(f"? Table '{table_name}' error: {e}")

    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_table_schemas())