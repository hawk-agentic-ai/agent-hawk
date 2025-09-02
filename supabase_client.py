import os
from supabase import create_client, Client

# Example function for loading credentials (mirroring your getSupabaseEnv())
def get_supabase_env():
    # Replace this logic as needed to get from config/env file
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variable!")
    return url, key

client: Client = None

def get_supabase() -> Client:
    global client
    if client is None:
        url, key = get_supabase_env()
        try:
            # No session persistence settings in Python client, but connection params go here
            client = create_client(url, key)
        except Exception as error:
            print('Failed to initialize Supabase client:', error)
            raise RuntimeError('Supabase connection unavailable') from error
    return client
