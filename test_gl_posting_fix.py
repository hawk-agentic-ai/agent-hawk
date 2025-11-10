#!/usr/bin/env python3
"""Test GL Posting Bridge Fix"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

async def test_gl_posting_fix():
    from shared.hedge_processor import HedgeFundProcessor
    from shared.mcp_tool_bridges import get_mcp_bridge

    # Initialize
    processor = HedgeFundProcessor()
    await processor.initialize()
    bridge = get_mcp_bridge()

    print("Testing GL Posting Bridge Fix...")

    gl_args = {
        'user_prompt': 'Create GL postings for hedge instruction INST_TEST_001',
        'instruction_id': 'INST_TEST_001',
        'currency': 'USD',
        'amount': 1000000.00,
        'execute_posting': False  # Don't actually execute for test
    }

    try:
        result = await bridge.execute_tool('gl_posting_processor', gl_args)

        success = (
            isinstance(result, dict) and
            'status' in result and
            result.get('status') != 'error' and
            'stage_info' in result and
            result['stage_info'].get('stage') == '3'
        )

        print(f'GL Posting Test: {"PASS" if success else "FAIL"}')

        if success:
            print(f'✅ Agent: {result["stage_info"].get("agent")}')
            print(f'✅ Purpose: {result["stage_info"].get("purpose")}')
            print(f'✅ Status: {result.get("status")}')
        else:
            print(f'❌ Error: {result.get("error", "Unknown error")}')
            print(f'❌ Full result: {result}')

        return success

    except Exception as e:
        print(f'❌ Exception: {e}')
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gl_posting_fix())
    sys.exit(0 if success else 1)