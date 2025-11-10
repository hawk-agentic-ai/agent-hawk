#!/usr/bin/env python3
"""
Test MCP Tool Bridges - Verify agent tools route correctly to backend
Tests the bridge layer that maps agent-expected tools to existing backend
"""

import asyncio
import logging
import sys
from pathlib import Path
import json

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env file from: {env_path}")
except ImportError:
    logger.warning("python-dotenv not available")

async def test_mcp_bridges():
    """Test MCP bridge tools route correctly to backend functions"""

    logger.info("Starting MCP Bridge Tests...")

    from shared.hedge_processor import HedgeFundProcessor
    from shared.mcp_tool_bridges import get_mcp_bridge

    # Initialize hedge processor (this initializes the bridge)
    processor = HedgeFundProcessor()
    await processor.initialize()

    bridge = get_mcp_bridge()
    if not bridge:
        logger.error("MCP bridge not initialized")
        return False

    logger.info("MCP bridge initialized successfully")

    test_results = []

    # Test 1: Allocation Stage 1A Processor
    logger.info("\nTest 1: Allocation Stage 1A Processor Bridge")

    allocation_args = {
        "user_prompt": "Check allocation capacity for 1M USD hedge",
        "currency": "USD",
        "entity_id": "ENTITY001",
        "nav_type": "COI",
        "amount": 1000000.00
    }

    try:
        result = await bridge.execute_tool("allocation_stage1a_processor", allocation_args)

        success = (
            isinstance(result, dict) and
            "status" in result and
            result.get("status") != "error" and
            "stage_info" in result and
            result["stage_info"].get("stage") == "1A"
        )

        test_results.append(("Allocation Stage 1A Bridge", success))

        if success:
            logger.info("✅ Allocation Stage 1A bridge working")
            logger.info(f"   Agent: {result['stage_info'].get('agent')}")
            logger.info(f"   Purpose: {result['stage_info'].get('purpose')}")
        else:
            logger.error(f"❌ Allocation Stage 1A bridge failed: {result}")

    except Exception as e:
        logger.error(f"❌ Allocation Stage 1A bridge exception: {e}")
        test_results.append(("Allocation Stage 1A Bridge", False))

    # Test 2: Utilization Checker
    logger.info("\nTest 2: Allocation Utilization Checker Bridge")

    utilization_args = {
        "currency": "EUR",
        "entity_id": "ENTITY002",
        "nav_type": "RE",
        "amount": 500000.00
    }

    try:
        result = await bridge.execute_tool("allocation_utilization_checker", utilization_args)

        success = (
            isinstance(result, dict) and
            "status" in result and
            result.get("status") != "error"
        )

        test_results.append(("Utilization Checker Bridge", success))

        if success:
            logger.info("✅ Utilization checker bridge working")
            if "utilization_analysis" in result:
                logger.info(f"   Utilization data keys: {list(result['utilization_analysis'].keys())}")
        else:
            logger.error(f"❌ Utilization checker bridge failed: {result}")

    except Exception as e:
        logger.error(f"❌ Utilization checker bridge exception: {e}")
        test_results.append(("Utilization Checker Bridge", False))

    # Test 3: Hedge Booking Processor
    logger.info("\nTest 3: Hedge Booking Processor Bridge")

    booking_args = {
        "user_prompt": "Execute booking for hedge instruction INST_TEST_001",
        "instruction_id": "INST_TEST_001",
        "currency": "GBP",
        "entity_id": "ENTITY003",
        "amount": 750000.00,
        "execute_booking": False  # Don't actually execute for test
    }

    try:
        result = await bridge.execute_tool("hedge_booking_processor", booking_args)

        success = (
            isinstance(result, dict) and
            "status" in result and
            result.get("status") != "error" and
            "stage_info" in result and
            result["stage_info"].get("stage") == "2"
        )

        test_results.append(("Booking Processor Bridge", success))

        if success:
            logger.info("✅ Booking processor bridge working")
            logger.info(f"   Agent: {result['stage_info'].get('agent')}")
            logger.info(f"   Purpose: {result['stage_info'].get('purpose')}")
        else:
            logger.error(f"❌ Booking processor bridge failed: {result}")

    except Exception as e:
        logger.error(f"❌ Booking processor bridge exception: {e}")
        test_results.append(("Booking Processor Bridge", False))

    # Test 4: GL Posting Processor
    logger.info("\nTest 4: GL Posting Processor Bridge")

    gl_args = {
        "user_prompt": "Create GL postings for hedge instruction INST_TEST_001",
        "instruction_id": "INST_TEST_001",
        "currency": "USD",
        "amount": 1000000.00,
        "execute_posting": False  # Don't actually execute for test
    }

    try:
        result = await bridge.execute_tool("gl_posting_processor", gl_args)

        success = (
            isinstance(result, dict) and
            "status" in result and
            result.get("status") != "error" and
            "stage_info" in result and
            result["stage_info"].get("stage") == "3"
        )

        test_results.append(("GL Posting Bridge", success))

        if success:
            logger.info("✅ GL posting bridge working")
            logger.info(f"   Agent: {result['stage_info'].get('agent')}")
            logger.info(f"   Purpose: {result['stage_info'].get('purpose')}")
        else:
            logger.error(f"❌ GL posting bridge failed: {result}")

    except Exception as e:
        logger.error(f"❌ GL posting bridge exception: {e}")
        test_results.append(("GL Posting Bridge", False))

    # Test 5: Analytics Processor
    logger.info("\nTest 5: Analytics Processor Bridge")

    analytics_args = {
        "user_prompt": "Analyze hedge effectiveness for EUR exposures",
        "currency": "EUR",
        "entity_id": "ENTITY001",
        "time_period": "Q1_2025"
    }

    try:
        result = await bridge.execute_tool("analytics_processor", analytics_args)

        success = (
            isinstance(result, dict) and
            "status" in result and
            result.get("status") != "error" and
            "agent_info" in result and
            result["agent_info"].get("agent") == "analytics"
        )

        test_results.append(("Analytics Processor Bridge", success))

        if success:
            logger.info("✅ Analytics processor bridge working")
            logger.info(f"   Agent: {result['agent_info'].get('agent')}")
            logger.info(f"   Purpose: {result['agent_info'].get('purpose')}")
        else:
            logger.error(f"❌ Analytics processor bridge failed: {result}")

    except Exception as e:
        logger.error(f"❌ Analytics processor bridge exception: {e}")
        test_results.append(("Analytics Processor Bridge", False))

    # Test 6: Config CRUD Processor
    logger.info("\nTest 6: Config CRUD Processor Bridge")

    config_args = {
        "table_name": "entity_master",
        "operation": "select",
        "filters": {"active_flag": "Y"},
        "limit": 5
    }

    try:
        result = await bridge.execute_tool("config_crud_processor", config_args)

        success = (
            isinstance(result, dict) and
            "status" in result and
            result.get("status") != "error" and
            "agent_info" in result and
            result["agent_info"].get("agent") == "config"
        )

        test_results.append(("Config CRUD Bridge", success))

        if success:
            logger.info("✅ Config CRUD bridge working")
            logger.info(f"   Agent: {result['agent_info'].get('agent')}")
            logger.info(f"   Table: {result['agent_info'].get('table')}")
            logger.info(f"   Operation: {result['agent_info'].get('operation')}")
        else:
            logger.error(f"❌ Config CRUD bridge failed: {result}")

    except Exception as e:
        logger.error(f"❌ Config CRUD bridge exception: {e}")
        test_results.append(("Config CRUD Bridge", False))

    # Test 7: Unknown Tool Error Handling
    logger.info("\nTest 7: Unknown Tool Error Handling")

    try:
        result = await bridge.execute_tool("nonexistent_tool", {})

        success = (
            isinstance(result, dict) and
            result.get("status") == "error" and
            "Unknown tool" in result.get("error", "")
        )

        test_results.append(("Unknown Tool Handling", success))

        if success:
            logger.info("✅ Unknown tool error handling working")
        else:
            logger.error(f"❌ Unknown tool error handling failed: {result}")

    except Exception as e:
        logger.error(f"❌ Unknown tool error handling exception: {e}")
        test_results.append(("Unknown Tool Handling", False))

    # Test 8: Tool Information
    logger.info("\nTest 8: Tool Information Retrieval")

    try:
        available_tools = bridge.get_available_tools()
        tool_info = bridge.get_tool_info("allocation_stage1a_processor")

        success = (
            isinstance(available_tools, list) and
            len(available_tools) > 0 and
            "allocation_stage1a_processor" in available_tools and
            isinstance(tool_info, dict) and
            tool_info.get("agent") == "allocation"
        )

        test_results.append(("Tool Information", success))

        if success:
            logger.info("✅ Tool information retrieval working")
            logger.info(f"   Available tools: {len(available_tools)}")
            logger.info(f"   Tool info sample: {tool_info.get('purpose', 'N/A')}")
        else:
            logger.error(f"❌ Tool information retrieval failed")

    except Exception as e:
        logger.error(f"❌ Tool information retrieval exception: {e}")
        test_results.append(("Tool Information", False))

    # Summary
    logger.info("\n" + "="*60)
    logger.info("MCP BRIDGE TEST SUMMARY")
    logger.info("="*60)

    passed = 0
    failed = 0

    for test_name, success in test_results:
        status = "PASS" if success else "FAIL"
        logger.info(f"{status}: {test_name}")
        if success:
            passed += 1
        else:
            failed += 1

    logger.info(f"\nTotal Tests: {len(test_results)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")

    if failed == 0:
        logger.info("\n🎉 SUCCESS: ALL MCP BRIDGE TESTS PASSED!")
        logger.info("✅ Agent tools successfully route to backend")
        logger.info("✅ Allocation Agent → Stage 1A processing")
        logger.info("✅ Booking Agent → Stage 2&3 processing")
        logger.info("✅ Analytics Agent → Performance analysis")
        logger.info("✅ Config Agent → CRUD operations")
        logger.info("✅ Error handling and tool info working")
        return True
    else:
        logger.error(f"\n❌ ERROR: {failed} MCP BRIDGE TESTS FAILED!")
        logger.error("Some agent tools may not route correctly to backend")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_bridges())
    sys.exit(0 if success else 1)