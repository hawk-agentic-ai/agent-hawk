#!/usr/bin/env python3
"""
Test MCP Tools Discovery and Execution
"""

import asyncio
import json
import sys

async def test_mcp_tools():
    """Test MCP server tool discovery and execution"""
    print("🧪 Testing MCP Tools...")
    
    try:
        # Start MCP server process  
        process = await asyncio.create_subprocess_exec(
            sys.executable, "mcp_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Initialize server
        init_request = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
        }
        
        process.stdin.write((json.dumps(init_request) + "\n").encode())
        await process.stdin.drain()
        init_response = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        print("✅ Server initialized")
        
        # Test tools/list
        list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        process.stdin.write((json.dumps(list_request) + "\n").encode()) 
        await process.stdin.drain()
        
        list_response = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        list_data = json.loads(list_response.decode().strip())
        
        if "result" in list_data and "tools" in list_data["result"]:
            tools = list_data["result"]["tools"]
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description'][:60]}...")
        else:
            print(f"❌ Tool list failed: {list_data}")
            return False
            
        # Test get_system_health tool
        health_request = {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "get_system_health", "arguments": {}}
        }
        
        process.stdin.write((json.dumps(health_request) + "\n").encode())
        await process.stdin.drain()
        
        health_response = await asyncio.wait_for(process.stdout.readline(), timeout=15.0)
        health_data = json.loads(health_response.decode().strip())
        
        if "result" in health_data:
            content = health_data["result"]["content"][0]["text"]
            health_info = json.loads(content)
            if health_info["status"] == "healthy":
                print(f"✅ Health check passed: {health_info['components']}")
                return True
            else:
                print(f"❌ Health check failed: {health_info}")
                return False
        else:
            print(f"❌ Health check call failed: {health_data}")
            return False
            
    except Exception as e:
        print(f"❌ MCP tools test failed: {e}")
        return False
    finally:
        try:
            process.terminate()
            await process.wait()
        except:
            pass

async def main():
    success = await test_mcp_tools()
    print(f"\n📋 Tools Test: {'✅ Pass' if success else '❌ Fail'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())