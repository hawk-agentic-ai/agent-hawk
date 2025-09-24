#!/usr/bin/env python3
"""
Test Supabase connection and credentials
"""
import os
import sys
from supabase import create_client, Client

def test_supabase_connection():
    """Test Supabase authentication and basic query"""

    # Load environment variables
    SUPABASE_URL = "https://ladviaautlfvpxuadqrb.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTU5NjA5OSwiZXhwIjoyMDcxMTcyMDk5fQ.vgvEWMOBZ6iX1ZYNyeKW4aoh3nARiC1eYcHU4c1Y-vU"

    print(f"Testing Supabase connection...")
    print(f"URL: {SUPABASE_URL}")
    print(f"Key: {SUPABASE_KEY[:20]}...")

    try:
        # Create client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[OK] Supabase client created successfully")

        # Test basic query
        print("Testing basic query...")
        result = supabase.table("currency_rates").select("*").limit(1).execute()

        if result.data:
            print(f"[OK] Query successful! Found {len(result.data)} records")
            print(f"Sample record: {result.data[0] if result.data else 'None'}")
        else:
            print("[WARN] Query returned no data")

        return True

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)