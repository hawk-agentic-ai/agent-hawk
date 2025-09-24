#!/usr/bin/env python3
"""
Simple MCP Client Test
Tests MCP server functionality via stdio protocol
"""

import asyncio
import json
import subprocess
import sys

async def test_mcp_server():
    """Test MCP server via subprocess stdio"""
    print("🧪 Testing MCP Server via stdio...")
    
    try:
        # Start MCP server process
        process = await asyncio.create_subprocess_exec(
            sys.executable, "mcp_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        request_json = json.dumps(init_request) + "\n"
        print(f"📤 Sending: {request_json.strip()}")
        
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        # Read response with timeout
        try:
            response = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            response_text = response.decode().strip()
            print(f"📥 Received: {response_text}")
            
            if response_text:
                response_data = json.loads(response_text)
                if "result" in response_data:
                    print("✅ MCP server responded successfully")
                    print(f"   Server capabilities: {response_data.get('result', {}).get('capabilities', {})}")
                    return True
                else:
                    print(f"❌ Unexpected response: {response_data}")
                    return False
            else:
                print("❌ No response from MCP server")
                return False
                
        except asyncio.TimeoutError:
            print("❌ MCP server response timeout")
            return False
            
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False
    finally:
        try:
            process.terminate()
            await process.wait()
        except:
            pass

async def main():
    """Run MCP client test"""
    print("🚀 Starting MCP Client Test...\n")
    
    success = await test_mcp_server()
    
    print(f"\n📋 Test Result: {'✅ Pass' if success else '❌ Fail'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())