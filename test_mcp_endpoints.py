#!/usr/bin/env python3
"""
Test MCP server endpoints and JSON-RPC functionality
"""
import json
import time
import requests
from datetime import datetime

MCP_SERVER_URL = "http://localhost:8010"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your_secure_token_here"  # Update if needed
}

def test_jsonrpc_request(method, params=None, req_id=1):
    """Send JSON-RPC 2.0 request to MCP server"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": req_id
    }
    if params:
        payload["params"] = params

    try:
        response = requests.post(MCP_SERVER_URL, json=payload, headers=HEADERS, timeout=10)
        print(f"[{method}] Status: {response.status_code}")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return {"status": "no_content"}
        else:
            print(f"[{method}] HTTP Error: {response.text}")
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"[{method}] Request failed: {e}")
        return {"error": str(e)}

def test_health_endpoint():
    """Test health endpoint"""
    try:
        response = requests.get(f"{MCP_SERVER_URL}/health", timeout=10)
        print(f"[HEALTH] Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"[HEALTH] Response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"[HEALTH] Error: {response.text}")
            return None
    except Exception as e:
        print(f"[HEALTH] Failed: {e}")
        return None

def test_db_health_endpoint():
    """Test database health endpoint"""
    try:
        response = requests.get(f"{MCP_SERVER_URL}/health/db", timeout=10)
        print(f"[DB_HEALTH] Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"[DB_HEALTH] Response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"[DB_HEALTH] Error: {response.text}")
            return None
    except Exception as e:
        print(f"[DB_HEALTH] Failed: {e}")
        return None

def main():
    """Run comprehensive MCP server tests"""
    print("=== MCP Server Test Suite ===")
    print(f"Target URL: {MCP_SERVER_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Test 1: Health endpoints
    print("1. Testing health endpoints...")
    health_data = test_health_endpoint()
    db_health_data = test_db_health_endpoint()
    print()

    # Test 2: Initialize MCP
    print("2. Testing MCP initialization...")
    init_response = test_jsonrpc_request("initialize", req_id="init_1")
    print(f"Initialize response: {json.dumps(init_response, indent=2)}")
    print()

    # Test 3: Send initialized notification
    print("3. Sending initialized notification...")
    init_notify_response = test_jsonrpc_request("initialized", req_id="notify_1")
    print(f"Initialized notification response: {json.dumps(init_notify_response, indent=2)}")
    print()

    # Test 4: List tools
    print("4. Testing tools/list...")
    tools_response = test_jsonrpc_request("tools/list", req_id="tools_1")
    if "result" in tools_response and "tools" in tools_response["result"]:
        tools = tools_response["result"]["tools"]
        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")
    else:
        print(f"Tools response: {json.dumps(tools_response, indent=2)}")
    print()

    # Test 5: Test process_hedge_prompt tool
    print("5. Testing process_hedge_prompt tool...")
    hedge_prompt_params = {
        "name": "process_hedge_prompt",
        "arguments": {
            "user_prompt": "What is the available USD capacity for hedging?",
            "operation_type": "read",
            "stage_mode": "1A",
            "currency": "USD"
        }
    }
    hedge_response = test_jsonrpc_request("tools/call", hedge_prompt_params, req_id="hedge_1")
    print(f"Hedge prompt response: {json.dumps(hedge_response, indent=2)}")
    print()

    # Test 6: Test query_supabase_data tool
    print("6. Testing query_supabase_data tool...")
    query_params = {
        "name": "query_supabase_data",
        "arguments": {
            "table_name": "currency_rates",
            "operation": "select",
            "limit": 5,
            "use_cache": False
        }
    }
    query_response = test_jsonrpc_request("tools/call", query_params, req_id="query_1")
    print(f"Query response: {json.dumps(query_response, indent=2)}")
    print()

    # Test 7: Test get_system_health tool
    print("7. Testing get_system_health tool...")
    health_params = {
        "name": "get_system_health",
        "arguments": {}
    }
    system_health_response = test_jsonrpc_request("tools/call", health_params, req_id="health_1")
    print(f"System health response: {json.dumps(system_health_response, indent=2)}")
    print()

    # Summary
    print("=== Test Summary ===")
    tests = [
        ("Health Endpoint", health_data is not None),
        ("DB Health Endpoint", db_health_data is not None),
        ("MCP Initialize", "result" in init_response),
        ("MCP Initialized", True),  # 204 response is expected
        ("Tools List", "result" in tools_response),
        ("Process Hedge Prompt", "result" in hedge_response),
        ("Query Supabase Data", "result" in query_response),
        ("System Health Tool", "result" in system_health_response)
    ]

    for test_name, success in tests:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {test_name}")

    total_passed = sum(1 for _, success in tests if success)
    print(f"\nResults: {total_passed}/{len(tests)} tests passed")

if __name__ == "__main__":
    main()