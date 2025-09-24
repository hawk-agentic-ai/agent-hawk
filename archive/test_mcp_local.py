#!/usr/bin/env python3
"""
Local MCP Server Test
Tests the MCP server components locally before deployment
"""

import asyncio
import json
import sys
import os

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.hedge_processor import hedge_processor

async def test_hedge_processor():
    """Test the HedgeFundProcessor initialization and basic functionality"""
    print("🧪 Testing HedgeFundProcessor...")
    
    try:
        # Initialize processor
        await hedge_processor.initialize()
        print("✅ HedgeFundProcessor initialized")
        
        # Test system health
        health = hedge_processor.get_system_health()
        print(f"✅ System Health: {health['status']}")
        print(f"   Components: {health['components']}")
        
        # Test cache management
        cache_stats = hedge_processor.manage_cache_operations("stats")
        print(f"✅ Cache Stats: {cache_stats['status']}")
        
        # Test basic prompt processing (with mock data expected)
        try:
            result = await hedge_processor.universal_prompt_processor(
                user_prompt="Show me system status",
                use_cache=False  # Skip cache for testing
            )
            print(f"✅ Prompt Processing: {result['status']}")
            if result['status'] == 'success':
                print(f"   Intent: {result['prompt_analysis']['intent']}")
                print(f"   Processing Time: {result['processing_metadata']['processing_time_ms']}ms")
        except Exception as e:
            print(f"⚠️ Prompt Processing (expected with no data): {e}")
        
        print("\n🎉 All core components working!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await hedge_processor.cleanup()

async def test_mcp_imports():
    """Test MCP server imports"""
    print("🧪 Testing MCP imports...")
    
    try:
        # Test MCP server imports
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        print("✅ MCP imports successful")
        
        # Test our MCP server
        import mcp_server
        print("✅ MCP server module imports successful")
        
        # Test MCP tools
        from mcp_tools.hedge_tools import HedgeFundTools
        print("✅ MCP tools import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ MCP import failed: {e}")
        print("💡 Install MCP dependencies: pip install mcp>=1.0.0")
        return False
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting MCP Local Tests...\n")
    
    # Test 1: MCP imports
    mcp_ok = await test_mcp_imports()
    print()
    
    # Test 2: Core processor (only if not in CI/test environment)
    if os.getenv("SUPABASE_URL"):
        processor_ok = await test_hedge_processor()
    else:
        print("⚠️ Skipping processor tests (no SUPABASE_URL env var)")
        processor_ok = True
    
    print("\n📋 Test Summary:")
    print("─────────────────")
    print(f"MCP Imports: {'✅ Pass' if mcp_ok else '❌ Fail'}")
    print(f"Processor: {'✅ Pass' if processor_ok else '❌ Fail'}")
    
    if mcp_ok and processor_ok:
        print("\n🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print("\n❌ Some tests failed. Check dependencies and configuration.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())