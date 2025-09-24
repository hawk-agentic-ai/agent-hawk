"""
Check accounting_method values
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def check_accounting_method():
    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        result = hedge_processor.supabase_client.table("hedge_business_events").select("accounting_method").limit(10).execute()
        if result.data:
            methods = list(set([r["accounting_method"] for r in result.data if r["accounting_method"]]))
            print(f"Valid accounting_method values: {methods}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_accounting_method())