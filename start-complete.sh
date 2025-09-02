#!/bin/bash
source /home/ubuntu/hedge-agent/venv/bin/activate
export DIFY_API_KEY="app-KKtaMynVyn8tKbdV9VbbaeyR"
export SUPABASE_URL="https://ladviaautlfvpxuadqrb.supabase.co"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"
export ENVIRONMENT="production"
uvicorn complete_optimized_backend:app --host 0.0.0.0 --port 8000