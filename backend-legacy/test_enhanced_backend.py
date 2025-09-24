#!/usr/bin/env python3
"""
Complete Test Suite for Enhanced Hedge Management API
Optimized for 30 users with template-based AI integration
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://3.91.170.95:8001"
TEST_ENTITY = "ENTITY0015"
TEST_FUND = "TEST_HEDGE_FUND"

def test_endpoint(name: str, method: str, url: str, data: Dict = None) -> Dict[str, Any]:
    """Test an API endpoint and return results"""
    print(f"\n🧪 Testing {name}...")
    start_time = time.time()
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        elapsed_time = round((time.time() - start_time) * 1000, 2)
        
        if response.status_code == 200:
            result_data = response.json()
            print(f"✅ {name}: SUCCESS ({elapsed_time}ms)")
            return {"success": True, "data": result_data, "time_ms": elapsed_time}
        else:
            print(f"❌ {name}: FAILED - Status {response.status_code}")
            return {"success": False, "error": response.text, "time_ms": elapsed_time}
            
    except Exception as e:
        elapsed_time = round((time.time() - start_time) * 1000, 2)
        print(f"🚨 {name}: ERROR - {str(e)}")
        return {"success": False, "error": str(e), "time_ms": elapsed_time}

def main():
    """Run complete test suite"""
    print("🚀 Enhanced Hedge Management API - Complete Test Suite")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: Health Check
    test_results["health"] = test_endpoint(
        "Health Check",
        "GET", 
        f"{BASE_URL}/health"
    )
    
    # Test 2: System Status
    test_results["system_status"] = test_endpoint(
        "Enhanced System Status",
        "GET",
        f"{BASE_URL}/system/status"
    )
    
    # Test 3: Hedge Positions
    test_results["hedge_positions"] = test_endpoint(
        "Hedge Positions Query",
        "GET",
        f"{BASE_URL}/hedge/positions/{TEST_ENTITY}"
    )
    
    # Test 4: Cache Performance Metrics
    test_results["cache_metrics"] = test_endpoint(
        "Cache Performance Metrics",
        "GET",
        f"{BASE_URL}/system/hedge-metrics"
    )
    
    # Test 5: Hedge Effectiveness Analytics
    test_results["hedge_effectiveness"] = test_endpoint(
        "Hedge Effectiveness Analytics",
        "GET",
        f"{BASE_URL}/hedge/effectiveness/{TEST_ENTITY}"
    )
    
    # Test 6: Template-Based AI - Inception
    test_results["dify_inception"] = test_endpoint(
        "Dify AI - Inception Template",
        "POST",
        f"{BASE_URL}/dify/hedge-chat",
        {
            "query": "Help me initiate a new USD hedge position for ENTITY0015",
            "query_type": "inception",
            "entity_id": TEST_ENTITY,
            "fund_id": TEST_FUND,
            "user_id": "test_user"
        }
    )
    
    # Test 7: Template-Based AI - Utilisation (should be cached)
    test_results["dify_utilisation"] = test_endpoint(
        "Dify AI - Utilisation Template",
        "POST",
        f"{BASE_URL}/dify/hedge-chat",
        {
            "query": "How should I modify my current hedge utilisation?",
            "query_type": "utilisation",
            "entity_id": TEST_ENTITY,
            "fund_id": TEST_FUND,
            "user_id": "test_user"
        }
    )
    
    # Test 8: Cache Test - Repeat Inception (should be cached)
    print(f"\n⏱️  Testing Cache Performance...")
    test_results["cache_test"] = test_endpoint(
        "Cache Test - Repeat Inception",
        "POST",
        f"{BASE_URL}/dify/hedge-chat",
        {
            "query": "Help me initiate a new USD hedge position for ENTITY0015",
            "query_type": "inception", 
            "entity_id": TEST_ENTITY,
            "fund_id": TEST_FUND,
            "user_id": "test_user"
        }
    )
    
    # Results Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for result in test_results.values() if result["success"])
    total_tests = len(test_results)
    
    print(f"✅ Successful Tests: {success_count}/{total_tests}")
    print(f"⏱️  Average Response Time: {sum(r['time_ms'] for r in test_results.values()) / total_tests:.0f}ms")
    
    # Performance Analysis
    if test_results["cache_test"]["success"] and test_results["dify_inception"]["success"]:
        first_call = test_results["dify_inception"]["time_ms"]
        cached_call = test_results["cache_test"]["time_ms"]
        
        if cached_call < first_call:
            speedup = round(first_call / cached_call, 1)
            print(f"🚀 Cache Performance: {speedup}x faster on repeat calls")
        
        # Check if cache was actually used
        try:
            cache_used = test_results["cache_test"]["data"].get("performance", {}).get("cache_used", False)
            if cache_used:
                print("✅ Cache System: WORKING - Permanent cache for 30 users")
            else:
                print("⚠️  Cache System: Not used (may be expected for fresh data)")
        except:
            pass
    
    # Service Status
    print(f"\n🔧 SERVICE STATUS:")
    try:
        health_data = test_results["health"]["data"]
        services = health_data.get("services", {})
        for service, status in services.items():
            emoji = "✅" if status == "connected" or status == "online" or status == "enabled" else "❌"
            print(f"   {emoji} {service}: {status}")
    except:
        print("   ⚠️  Could not retrieve service status")
    
    # Advanced Features Status
    print(f"\n🎯 ADVANCED FEATURES:")
    try:
        status_data = test_results["system_status"]["data"]
        capabilities = status_data.get("capabilities", {})
        for feature, enabled in capabilities.items():
            emoji = "✅" if enabled else "❌"
            print(f"   {emoji} {feature.replace('_', ' ').title()}: {'Enabled' if enabled else 'Disabled'}")
    except:
        print("   ⚠️  Could not retrieve capabilities status")
    
    print(f"\n🌐 Access your API at: {BASE_URL}/docs")
    print(f"📊 Monitor performance: {BASE_URL}/system/hedge-metrics")
    
    return test_results

if __name__ == "__main__":
    results = main()
    
    # Save detailed results
    with open("hedge_api_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: hedge_api_test_results.json")