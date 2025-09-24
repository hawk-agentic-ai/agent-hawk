#!/usr/bin/env python3

"""
Simple Test for Unified Smart Backend v5.0.0
Basic testing without Unicode characters
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8004"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Health OK - {data.get('status')}")
            print(f"      Components: {data.get('components', {})}")
            return True
        else:
            print(f"FAIL: Health check failed - {response.status_code}")
            return False
    except Exception as e:
        print(f"FAIL: Health check error - {e}")
        return False

def test_system_status():
    """Test system status"""
    print("Testing system status...")
    
    try:
        response = requests.get(f"{BASE_URL}/system/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: System status OK - v{data.get('version')}")
            
            components = data.get('components', {})
            for name, status in components.items():
                if isinstance(status, dict) and 'status' in status:
                    print(f"      {name}: {status['status']}")
            return True
        else:
            print(f"FAIL: System status failed - {response.status_code}")
            return False
    except Exception as e:
        print(f"FAIL: System status error - {e}")
        return False

def test_prompt_analysis():
    """Test prompt analysis"""
    print("Testing prompt analysis...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/prompt-analysis/test",
            params={"prompt": "Check CNY hedge capacity", "category": "hedge_accounting"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            analysis = data.get('analysis', {})
            print(f"PASS: Prompt analysis OK")
            print(f"      Intent: {analysis.get('intent')}")
            print(f"      Confidence: {analysis.get('confidence')}%")
            print(f"      Tables: {len(analysis.get('required_tables', []))}")
            return True
        else:
            print(f"FAIL: Prompt analysis failed - {response.status_code}")
            return False
    except Exception as e:
        print(f"FAIL: Prompt analysis error - {e}")
        return False

def test_main_endpoint():
    """Test main endpoint performance"""
    print("Testing main endpoint...")
    
    test_data = {
        "user_prompt": "Check CNY hedge capacity",
        "template_category": "hedge_accounting", 
        "currency": "CNY"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/hawk-agent/process-prompt",
            json=test_data,
            timeout=30,
            stream=True
        )
        
        if response.status_code == 200:
            # Read some of the streaming response
            content_size = 0
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    content_size += len(chunk)
                    # Stop after getting some data
                    if content_size > 1000:
                        break
            
            response_time = time.time() - start_time
            
            print(f"PASS: Main endpoint OK")
            print(f"      Response time: {response_time:.2f}s")
            print(f"      Content received: {content_size} bytes")
            
            if response_time < 2.0:
                print(f"      EXCELLENT: Sub-2s target achieved!")
            else:
                print(f"      NOTE: Response time above 2s target")
                
            return True
        else:
            print(f"FAIL: Main endpoint failed - {response.status_code}")
            return False
            
    except Exception as e:
        print(f"FAIL: Main endpoint error - {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("UNIFIED SMART BACKEND v5.0.0 - SIMPLE TEST SUITE")
    print("=" * 60)
    print("")
    
    tests = [
        test_health,
        test_system_status, 
        test_prompt_analysis,
        test_main_endpoint
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print("")
        except Exception as e:
            print(f"FAIL: Test {test_func.__name__} crashed - {e}")
            print("")
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("STATUS: ALL TESTS PASSED - Backend is ready!")
    else:
        print("STATUS: Some tests failed - check output above")
    
    print("")
    print("Unified Smart Backend v5.0.0 deployment test complete.")
    
    # Return exit code
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit(main())