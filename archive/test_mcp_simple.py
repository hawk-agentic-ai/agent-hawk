#!/usr/bin/env python3
"""
Simple MCP Test - No Unicode issues
"""

import asyncio
import sys
import json

async def test_imports():
    """Test basic imports"""
    print("Testing imports...")
    try:
        from shared.hedge_processor import hedge_processor
        print("[OK] HedgeProcessor import")
        
        from mcp.server import Server
        print("[OK] MCP server import")
        
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False

async def test_mcp_server():
    """Test MCP server basic functionality"""
    print("Testing MCP server startup...")
    
    try:
        # Start MCP server
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
                "clientInfo": {"name": "simple-test", "version": "1.0"}
            }
        }
        
        request_str = json.dumps(init_request) + "\n"
        process.stdin.write(request_str.encode())
        await process.stdin.drain()
        
        # Wait for response
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            if response_line:
                response_str = response_line.decode().strip()
                response_data = json.loads(response_str)
                
                if "result" in response_data:
                    print("[OK] MCP server responded successfully")
                    server_info = response_data['result'].get('serverInfo', {})
                    print(f"Server: {server_info.get('name', 'unknown')}")
                    return True
                else:
                    print(f"[FAIL] Server error: {response_data}")
                    return False
            else:
                print("[FAIL] No response from server")
                return False
                
        except asyncio.TimeoutError:
            print("[FAIL] Server response timeout")
            return False
        except json.JSONDecodeError as e:
            print(f"[FAIL] Invalid JSON: {e}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        return False
    finally:
        try:
            if 'process' in locals():
                process.terminate()
                await process.wait()
        except:
            pass

async def main():
    print("SIMPLE MCP SERVER TEST")
    print("=" * 30)
    
    # Test imports
    if not await test_imports():
        return 1
    
    # Test MCP server
    if await test_mcp_server():
        print("\n[OK] MCP test PASSED")
        return 0
    else:
        print("\n[FAIL] MCP test FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)