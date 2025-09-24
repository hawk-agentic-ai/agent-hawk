#!/usr/bin/env python3
"""
Basic MCP Server Test - Minimal validation
"""

import asyncio
import json
import sys
import subprocess

async def test_basic_mcp():
    """Basic MCP server functionality test"""
    print("Testing MCP Server Basic Functionality...")
    
    try:
        # Start MCP server
        print("1. Starting MCP server...")
        process = await asyncio.create_subprocess_exec(
            sys.executable, "mcp_server_fixed.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print("2. Sending initialization request...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "basic-test", "version": "1.0"}
            }
        }
        
        # Send request
        request_str = json.dumps(init_request) + "\n"
        process.stdin.write(request_str.encode())
        await process.stdin.drain()
        
        print("3. Waiting for response...")
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=15.0)
            if response_line:
                response_str = response_line.decode().strip()
                print(f"4. Received: {response_str}")
                
                if response_str:
                    response_data = json.loads(response_str)
                    if "result" in response_data:
                        print("✅ MCP server responded successfully!")
                        print(f"   Protocol Version: {response_data['result'].get('protocolVersion')}")
                        print(f"   Server Name: {response_data['result'].get('serverInfo', {}).get('name')}")
                        return True
                    elif "error" in response_data:
                        print(f"❌ MCP server error: {response_data['error']}")
                        return False
                    else:
                        print(f"⚠️ Unexpected response format: {response_data}")
                        return False
                else:
                    print("❌ Empty response from server")
                    return False
            else:
                print("❌ No response from server")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Server response timeout")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            if process:
                process.terminate()
                await process.wait()
        except:
            pass

async def test_import():
    """Test basic imports"""
    print("Testing imports...")
    try:
        from shared.hedge_processor import hedge_processor
        print("✅ HedgeProcessor import OK")
        
        from mcp.server import Server
        print("✅ MCP server import OK")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

async def main():
    print("🧪 BASIC MCP SERVER TEST")
    print("=" * 30)
    
    # Test imports first
    if not await test_import():
        return 1
    
    # Test basic MCP functionality
    if await test_basic_mcp():
        print("\n✅ Basic MCP test PASSED")
        return 0
    else:
        print("\n❌ Basic MCP test FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())