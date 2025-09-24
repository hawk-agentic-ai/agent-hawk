#!/usr/bin/env python3
"""Test Simple MCP Server"""

import asyncio
import json
import sys

async def test_simple_mcp():
    """Test simple MCP server"""
    print("🧪 Testing Simple MCP Server...")
    
    try:
        # Start process
        process = await asyncio.create_subprocess_exec(
            sys.executable, "mcp_server_simple.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        
        # Initialize
        init_req = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
        }
        process.stdin.write((json.dumps(init_req) + "\n").encode())
        await process.stdin.drain()
        
        init_resp = await asyncio.wait_for(process.stdout.readline(), timeout=15.0)
        print("✅ Initialized")
        
        # List tools
        list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        process.stdin.write((json.dumps(list_req) + "\n").encode())
        await process.stdin.drain()
        
        list_resp = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        list_data = json.loads(list_resp.decode().strip())
        
        if "result" in list_data:
            tools = list_data["result"]["tools"]
            print(f"✅ Found {len(tools)} tools: {[t['name'] for t in tools]}")
        else:
            print(f"❌ Tool list failed: {list_data}")
            return False
            
        # Call health tool
        health_req = {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "get_system_health", "arguments": {}}
        }
        process.stdin.write((json.dumps(health_req) + "\n").encode())
        await process.stdin.drain()
        
        health_resp = await asyncio.wait_for(process.stdout.readline(), timeout=15.0)
        health_data = json.loads(health_resp.decode().strip())
        
        if "result" in health_data and "content" in health_data["result"]:
            content = health_data["result"]["content"][0]["text"]
            health_info = json.loads(content)
            print(f"✅ Health: {health_info['status']}")
            return True
        else:
            print(f"❌ Health failed: {health_data}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            process.terminate()
            await process.wait()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_simple_mcp())
    print(f"Result: {'✅ Pass' if success else '❌ Fail'}")