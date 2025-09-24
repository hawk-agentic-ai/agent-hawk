#!/usr/bin/env python3
"""
Simple Working Backend for Deployment Test
Minimal FastAPI backend without complex dependencies
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from datetime import datetime

app = FastAPI(
    title="Hedge Fund Agent - Simple Backend",
    description="Working backend for frontend integration",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hedge Fund Agent API - Simple Backend", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "backend_type": "simple",
        "components": {
            "api": "running",
            "cors": "enabled"
        }
    }

@app.get("/api/templates")
async def get_templates():
    """Return mock template data for frontend"""
    return {
        "templates": [
            {
                "id": 1,
                "name": "CNY Hedge Inception",
                "category": "hedge_inception",
                "description": "Create new CNY hedge instruction"
            },
            {
                "id": 2,
                "name": "USD Hedge Utilization",
                "category": "hedge_utilization",
                "description": "Check USD hedge capacity utilization"
            },
            {
                "id": 3,
                "name": "EUR Hedge Termination",
                "category": "hedge_termination",
                "description": "Terminate EUR hedge instruction"
            }
        ],
        "count": 3,
        "status": "success"
    }

@app.post("/api/hawk-agent/process-prompt")
async def process_prompt(request: dict):
    """Mock prompt processing for frontend testing"""
    return {
        "success": True,
        "message": "Prompt processed successfully",
        "response": f"Mock response for: {request.get('user_prompt', 'No prompt provided')}",
        "timestamp": datetime.now().isoformat(),
        "backend": "simple"
    }

@app.get("/api/system/status")
async def system_status():
    return {
        "status": "online",
        "backend": "simple",
        "environment": "production",
        "server": "AWS EC2",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)