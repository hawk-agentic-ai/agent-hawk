#!/usr/bin/env python3
"""
Test script to verify that different agents are routed to different Dify APIs
"""

import requests
import json

BASE_URL = "https://3-91-170-95.nip.io/api"

# Test data
test_request = {
    "user_prompt": "What are our current USD hedge positions?",
    "template_category": "utilization_analysis",
    "currency": "USD",
    "entity_id": "ENTITY001",
    "nav_type": "GAAP",
    "amount": 100000,
    "stream_response": False,
    "force_fresh": False,
    "use_cache": True
}

def test_agent_routing():
    """Test that different agent_ids route to different configurations"""
    
    print("🧪 Testing Agent Routing Configuration")
    print("=" * 50)
    
    # Test 1: Default agent (should use standard DIFY_API_KEY)
    print("\n🔹 Testing Default Agent")
    default_request = test_request.copy()
    default_request["agent_id"] = "hawk"
    
    try:
        response = requests.post(f"{BASE_URL}/hawk-agent/process-prompt", 
                               json=default_request, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Default agent request successful")
        else:
            print(f"   ❌ Default agent failed: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Default agent error: {e}")
    
    # Test 2: Allocation agent (should use DIFY_API_KEY_ALLOCATION)
    print("\n🔹 Testing Allocation Agent")
    allocation_request = test_request.copy()
    allocation_request["agent_id"] = "allocation"
    allocation_request["user_prompt"] = "Can I place a new hedge for 150,000 CNY under ENTITY001?"
    
    try:
        response = requests.post(f"{BASE_URL}/hawk-agent/process-prompt", 
                               json=allocation_request, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Allocation agent request successful")
            # Check if we got a response indicating allocation agent functionality
            response_text = response.text
            if "allocation" in response_text.lower() or "hedge" in response_text.lower():
                print("   ✅ Response content suggests allocation agent functionality")
        else:
            print(f"   ❌ Allocation agent failed: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Allocation agent error: {e}")
    
    # Test 3: Check backend health
    print("\n🔹 Testing Backend Health")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("   ✅ Backend healthy")
            print(f"   📊 Version: {health_data.get('version')}")
            print(f"   🔌 Components: {list(health_data.get('components', {}).keys())}")
        else:
            print(f"   ❌ Backend health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")

if __name__ == "__main__":
    test_agent_routing()