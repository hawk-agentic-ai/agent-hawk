#!/bin/bash
source /home/ubuntu/hedge-agent/venv/bin/activate
export DIFY_API_KEY="app-KKtaMynVyn8tKbdV9VbbaeyR"
export ENVIRONMENT="production"
uvicorn optimized_backend:app --host 0.0.0.0 --port 8000