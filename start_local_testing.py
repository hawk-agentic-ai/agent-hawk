#!/usr/bin/env python3
"""
Start Local Testing - Quick setup for local MCP server testing
"""

import asyncio
import sys
import json
from pathlib import Path
import subprocess
import time
import requests

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_server_health():
    """Test if the MCP server is responding"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "health-check",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "local-test", "version": "1.0.0"}
            }
        }

        response = requests.post(
            "http://localhost:8000",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Server health check PASSED")
            return True
        else:
            print(f"❌ Server health check FAILED: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Server health check FAILED: {e}")
        return False

def test_tools_list():
    """Test that all bridge tools are available"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "tools-list",
            "method": "tools/list",
            "params": {}
        }

        response = requests.post(
            "http://localhost:8000",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            tools = result.get("result", {}).get("tools", [])
            tool_names = [tool["name"] for tool in tools]

            expected_tools = [
                "allocation_stage1a_processor",
                "hedge_booking_processor",
                "gl_posting_processor",
                "analytics_processor",
                "config_crud_processor"
            ]

            missing_tools = [tool for tool in expected_tools if tool not in tool_names]

            if not missing_tools:
                print(f"✅ All {len(expected_tools)} bridge tools available")
                return True
            else:
                print(f"❌ Missing bridge tools: {missing_tools}")
                return False

        else:
            print(f"❌ Tools list failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Tools list failed: {e}")
        return False

def test_allocation_agent():
    """Test allocation agent bridge"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "test-allocation",
            "method": "tools/call",
            "params": {
                "name": "allocation_stage1a_processor",
                "arguments": {
                    "user_prompt": "Check allocation capacity for 1M USD hedge",
                    "currency": "USD",
                    "entity_id": "ENTITY001",
                    "nav_type": "COI",
                    "amount": 1000000
                }
            }
        }

        response = requests.post(
            "http://localhost:8000",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if "error" not in result:
                print("✅ Allocation Agent test PASSED")
                return True
            else:
                print(f"❌ Allocation Agent test FAILED: {result['error']}")
                return False
        else:
            print(f"❌ Allocation Agent test FAILED: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Allocation Agent test FAILED: {e}")
        return False

def main():
    """Main local testing routine"""
    print("🚀 Starting Local Testing Setup...")
    print("=" * 50)

    # Check if server is running
    print("\n1. Testing Server Health...")
    if not test_server_health():
        print("\n❌ MCP Server is not running or not responding")
        print("\nTo start the server, run in another terminal:")
        print("   cd hedge-agent")
        print("   python mcp_server_production.py")
        print("\nThen run this script again.")
        return False

    # Test tools list
    print("\n2. Testing Available Tools...")
    if not test_tools_list():
        print("❌ Bridge tools are not properly configured")
        return False

    # Test allocation agent
    print("\n3. Testing Allocation Agent Integration...")
    if not test_allocation_agent():
        print("❌ Agent integration is not working")
        return False

    print("\n" + "=" * 50)
    print("🎉 LOCAL TESTING SUCCESSFUL!")
    print("✅ MCP Server running and responding")
    print("✅ All bridge tools available")
    print("✅ Agent integration working")
    print("\n🚀 Ready for full local testing!")
    print("\nNext steps:")
    print("1. Test other agents (booking, analytics, config)")
    print("2. Run: python test_mcp_bridges.py")
    print("3. Test with your Dify agents pointing to localhost:8000")
    print("4. Ready for production when all tests pass!")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)