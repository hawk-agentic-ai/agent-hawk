#!/usr/bin/env python3
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

# These are the publicly accessible JSON-RPC endpoints for your servers
# as routed by Nginx.
PRODUCTION_MCP_ENDPOINT = "https://3-91-170-95.nip.io/mcp/"
HAWK_ALLOCATION_ENDPOINT = "https://3-91-170-95.nip.io/dify"  # Note: No trailing slash

async def event_stream():
    """
    This stream advertises BOTH of your servers to Dify.
    Dify will register each one as a separate tool source.
    """
    yield f"event: endpoint\ndata: {PRODUCTION_MCP_ENDPOINT}\n\n"
    await asyncio.sleep(0.1)  # Brief pause to ensure delivery
    yield f"event: endpoint\ndata: {HAWK_ALLOCATION_ENDPOINT}\n\n"

    # Keep the connection alive
    while True:
        yield "event: ping\ndata: keepalive\n\n"
        await asyncio.sleep(25)

@app.get("/master-discovery/sse")
async def master_sse_endpoint(request: Request):
    """The single discovery endpoint for Dify."""
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "master-discovery-server",
        "endpoints_advertised": [
            PRODUCTION_MCP_ENDPOINT,
            HAWK_ALLOCATION_ENDPOINT
        ]
    }

if __name__ == "__main__":
    print("🔍 Running Master Discovery Server on port 8008...")
    print(f"📡 Advertising endpoints:")
    print(f"   Production MCP: {PRODUCTION_MCP_ENDPOINT}")
    print(f"   HAWK Allocation: {HAWK_ALLOCATION_ENDPOINT}")
    print(f"🌐 Dify URL: https://3-91-170-95.nip.io/master-discovery/sse")
    uvicorn.run(app, host="0.0.0.0", port=8008)