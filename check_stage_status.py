"""
Check valid stage_status enum values
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def check_stage_status():
    print("CHECKING STAGE STATUS ENUM VALUES")
    print("=" * 40)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return

        # Check stage_1a_status values
        print("\n[stage_1a_status values]")
        print("-" * 25)
        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").select("stage_1a_status").limit(20).execute()
            if result.data:
                unique_statuses = list(set([r["stage_1a_status"] for r in result.data if r["stage_1a_status"]]))
                print(f"Valid stage_1a_status values: {unique_statuses}")
        except Exception as e:
            print(f"Error checking stage_1a_status: {e}")

        # Check stage_1b_status values
        print("\n[stage_1b_status values]")
        print("-" * 25)
        try:
            result = hedge_processor.supabase_client.table("hedge_business_events").select("stage_1b_status").limit(20).execute()
            if result.data:
                unique_statuses = list(set([r["stage_1b_status"] for r in result.data if r["stage_1b_status"]]))
                print(f"Valid stage_1b_status values: {unique_statuses}")
        except Exception as e:
            print(f"Error checking stage_1b_status: {e}")

    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(check_stage_status())