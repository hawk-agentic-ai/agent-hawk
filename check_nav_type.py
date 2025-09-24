"""
Check valid nav_type values
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def check_nav_type():
    print("CHECKING nav_type VALUES")
    print("=" * 30)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return

        # Check nav_type values
        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").select("nav_type").limit(20).execute()
            if result.data:
                unique_nav_types = list(set([r["nav_type"] for r in result.data if r["nav_type"]]))
                print(f"Valid nav_type values: {unique_nav_types}")
        except Exception as e:
            print(f"Error checking nav_type: {e}")

    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(check_nav_type())