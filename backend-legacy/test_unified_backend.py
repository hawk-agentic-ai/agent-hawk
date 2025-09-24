#!/usr/bin/env python3

"""
Test Script for Unified Smart Backend v5.0.0
Comprehensive testing of all components and endpoints
"""

import asyncio
import json
import requests
import time
from datetime import datetime
from typing import Dict, Any, List

# Test configuration
BASE_URL = "http://localhost:8004"
TEST_PROMPTS = [
    {
        "name": "CNY Hedge Capacity Check",
        "request": {
            "user_prompt": "Check if I can hedge 150K CNY today",
            "template_category": "hedge_accounting",
            "currency": "CNY",
            "amount": 150000
        },
        "expected_intent": "utilization"
    },
    {
        "name": "USD Inception Request",
        "request": {
            "user_prompt": "Start USD 25M COI hedge",
            "template_category": "hedge_accounting",
            "currency": "USD",
            "nav_type": "COI",
            "amount": 25000000,
            "instruction_type": "I"
        },
        "expected_intent": "inception"
    },
    {
        "name": "General Risk Analysis",
        "request": {
            "user_prompt": "Analyze VAR for portfolio performance",
            "template_category": "risk_management"
        },
        "expected_intent": "analysis"
    },
    {
        "name": "Compliance Report",
        "request": {
            "user_prompt": "Generate compliance report for Q1 2024",
            "template_category": "compliance",
            "time_period": "Q1-2024"
        },
        "expected_intent": "reporting"
    },
    {
        "name": "Status Inquiry",
        "request": {
            "user_prompt": "Status of all EUR instructions",
            "template_category": "hedge_accounting",
            "currency": "EUR",
            "instruction_type": "Q"
        },
        "expected_intent": "inquiry"
    }
]

class BackendTester:
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results: List[Dict[str, Any]] = []
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_health_endpoint(self) -> bool:
        """Test basic health endpoint"""
        self.log("Testing health endpoint...")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                self.log(f"Health OK - Status: {health_data.get('status')}")
                self.log(f"   Components: {health_data.get('components', {})}")
                return True
            else:
                self.log(f"Health check failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Health check error: {e}", "ERROR")
            return False
    
    def test_system_status(self) -> bool:
        """Test system status endpoint"""
        self.log("Testing system status...")
        
        try:
            response = self.session.get(f"{self.base_url}/system/status", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                self.log(f"✅ System Status OK - Version: {status_data.get('version')}")
                
                components = status_data.get('components', {})
                for component, details in components.items():
                    if isinstance(details, dict) and 'status' in details:
                        self.log(f"   {component}: {details['status']}")
                    
                return True
            else:
                self.log(f"❌ System status failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ System status error: {e}", "ERROR")
            return False
    
    def test_cache_stats(self) -> bool:
        """Test cache statistics endpoint"""
        self.log("Testing cache stats...")
        
        try:
            response = self.session.get(f"{self.base_url}/cache/stats", timeout=10)
            
            if response.status_code == 200:
                cache_data = response.json()
                hit_rate = cache_data.get('cache_hit_rate', '0%')
                total_requests = cache_data.get('total_requests', 0)
                
                self.log(f"✅ Cache Stats OK - Hit Rate: {hit_rate}, Requests: {total_requests}")
                
                if 'redis_keys_count' in cache_data:
                    self.log(f"   Redis Keys: {cache_data['redis_keys_count']}")
                    
                return True
            else:
                self.log(f"❌ Cache stats failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Cache stats error: {e}", "ERROR")
            return False
    
    def test_prompt_analysis(self) -> bool:
        """Test prompt analysis functionality"""
        self.log("Testing prompt analysis...")
        
        test_prompt = "Check CNY hedge capacity"
        
        try:
            response = self.session.get(
                f"{self.base_url}/prompt-analysis/test",
                params={"prompt": test_prompt, "category": "hedge_accounting"},
                timeout=10
            )
            
            if response.status_code == 200:
                analysis_data = response.json()
                analysis = analysis_data.get('analysis', {})
                
                intent = analysis.get('intent')
                confidence = analysis.get('confidence', 0)
                
                self.log(f"✅ Prompt Analysis OK - Intent: {intent}, Confidence: {confidence}%")
                self.log(f"   Required Tables: {len(analysis.get('required_tables', []))}")
                self.log(f"   Extracted Params: {analysis.get('extracted_params', {})}")
                
                return True
            else:
                self.log(f"❌ Prompt analysis failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Prompt analysis error: {e}", "ERROR")
            return False
    
    def test_main_endpoint_performance(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test main endpoint with performance measurement"""
        self.log(f"Testing: {test_case['name']}")
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.base_url}/hawk-agent/process-prompt",
                json=test_case['request'],
                timeout=30,  # Allow up to 30 seconds for processing
                stream=True  # Handle streaming response
            )
            
            if response.status_code == 200:
                # For streaming responses, we'll just check if we get data
                content_received = ""
                bytes_received = 0
                
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        content_received += chunk.decode('utf-8', errors='ignore')
                        bytes_received += len(chunk)
                        # Stop after receiving some data to avoid waiting too long
                        if bytes_received > 1000:
                            break
                
                response_time = time.time() - start_time
                
                result = {
                    "name": test_case['name'],
                    "status": "success",
                    "response_time_ms": round(response_time * 1000, 2),
                    "bytes_received": bytes_received,
                    "has_content": len(content_received) > 0,
                    "performance_target_met": response_time < 2.0  # Sub-2 second target
                }
                
                self.log(f"✅ {test_case['name']} - {response_time:.2f}s, {bytes_received} bytes")
                
                if response_time >= 2.0:
                    self.log(f"⚠️  Performance target not met (>2s)", "WARNING")
                
                return result
                
            else:
                response_time = time.time() - start_time
                error_content = response.text[:200] if hasattr(response, 'text') else 'Unknown error'
                
                result = {
                    "name": test_case['name'],
                    "status": "error",
                    "response_time_ms": round(response_time * 1000, 2),
                    "status_code": response.status_code,
                    "error": error_content
                }
                
                self.log(f"❌ {test_case['name']} failed - {response.status_code}", "ERROR")
                return result
                
        except Exception as e:
            response_time = time.time() - start_time
            
            result = {
                "name": test_case['name'],
                "status": "exception",
                "response_time_ms": round(response_time * 1000, 2),
                "error": str(e)
            }
            
            self.log(f"❌ {test_case['name']} exception: {e}", "ERROR")
            return result
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate comprehensive report"""
        self.log("=" * 60)
        self.log("UNIFIED SMART BACKEND COMPREHENSIVE TEST")
        self.log("=" * 60)
        
        test_start_time = time.time()
        results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "backend_version": "5.0.0",
            "component_tests": {},
            "performance_tests": [],
            "summary": {}
        }
        
        # Component Tests
        self.log("\n🔍 COMPONENT TESTS")
        self.log("-" * 30)
        
        results["component_tests"]["health"] = self.test_health_endpoint()
        results["component_tests"]["system_status"] = self.test_system_status()
        results["component_tests"]["cache_stats"] = self.test_cache_stats()
        results["component_tests"]["prompt_analysis"] = self.test_prompt_analysis()
        
        # Performance Tests
        self.log("\n⚡ PERFORMANCE TESTS")
        self.log("-" * 30)
        
        for test_case in TEST_PROMPTS:
            result = self.test_main_endpoint_performance(test_case)
            results["performance_tests"].append(result)
            time.sleep(1)  # Brief pause between tests
        
        # Generate Summary
        total_time = time.time() - test_start_time
        component_pass_count = sum(1 for passed in results["component_tests"].values() if passed)
        performance_pass_count = sum(1 for test in results["performance_tests"] if test["status"] == "success")
        fast_response_count = sum(1 for test in results["performance_tests"] if test.get("performance_target_met", False))
        
        results["summary"] = {
            "total_test_time_s": round(total_time, 2),
            "component_tests_passed": f"{component_pass_count}/{len(results['component_tests'])}",
            "performance_tests_passed": f"{performance_pass_count}/{len(results['performance_tests'])}",
            "sub_2s_responses": f"{fast_response_count}/{len(results['performance_tests'])}",
            "overall_health": "PASS" if component_pass_count == len(results['component_tests']) else "FAIL",
            "performance_grade": "A" if fast_response_count >= len(results['performance_tests']) * 0.8 else "B" if fast_response_count >= len(results['performance_tests']) * 0.5 else "C"
        }
        
        # Display Summary
        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"📊 Total Test Time: {results['summary']['total_test_time_s']}s")
        self.log(f"🔧 Component Tests: {results['summary']['component_tests_passed']}")
        self.log(f"⚡ Performance Tests: {results['summary']['performance_tests_passed']}")
        self.log(f"🎯 Sub-2s Responses: {results['summary']['sub_2s_responses']}")
        self.log(f"🏆 Overall Health: {results['summary']['overall_health']}")
        self.log(f"📈 Performance Grade: {results['summary']['performance_grade']}")
        
        if results['summary']['overall_health'] == 'PASS':
            self.log("✅ Unified Smart Backend is ready for production!", "SUCCESS")
        else:
            self.log("⚠️  Some issues detected - check logs above", "WARNING")
        
        return results

def main():
    """Main test execution"""
    print("Unified Smart Backend Test Suite v5.0.0")
    print("=" * 60)
    
    tester = BackendTester()
    results = tester.run_comprehensive_test()
    
    # Save results to file
    results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Return appropriate exit code
    if results['summary']['overall_health'] == 'PASS':
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()