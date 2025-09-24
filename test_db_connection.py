"""
Test database connection with correct keys
"""

import os
import asyncio

# Set correct environment variables
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"

# Try service role key first (if you have it)
# For now, test with anon key to verify connection
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_supabase_connection():
    print("Testing Supabase Connection")
    print("=" * 40)

    try:
        from shared.hedge_processor import hedge_processor

        print("Testing with ANON key (limited access)...")
        await hedge_processor.initialize()

        if hedge_processor.supabase_client:
            print("PASS: Supabase client created")

            # Test basic connection
            try:
                result = await hedge_processor.query_supabase_direct(
                    table_name="entity_master",
                    operation="select",
                    limit=1
                )
                print(f"Database query result: {result.get('status', 'unknown')}")
                if result.get('status') == 'success':
                    print(f"Records found: {result.get('records', 0)}")
                else:
                    print(f"Query error: {result.get('error', 'unknown')}")

            except Exception as e:
                print(f"Query test error: {e}")
        else:
            print("FAIL: Supabase client not created")

    except Exception as e:
        print(f"Connection test error: {e}")

    print("\nNOTE: If you have the actual SERVICE ROLE key (not anon key),")
    print("replace SUPABASE_SERVICE_ROLE_KEY in the environment for full access.")
    print("Anon keys have limited permissions - service role keys have full access.")

if __name__ == "__main__":
    asyncio.run(test_supabase_connection())