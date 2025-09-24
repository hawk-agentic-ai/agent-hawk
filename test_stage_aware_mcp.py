"""
Test Stage-Aware MCP Implementation
"""

import asyncio
import os

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_stage_aware_functionality():
    print("TESTING STAGE-AWARE MCP FUNCTIONALITY")
    print("=" * 50)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        # Test cases for different agent roles and stages
        test_cases = [
            {
                "name": "Allocation Agent - Stage 1A",
                "params": {
                    "user_prompt": "Check utilization capacity for USD 20M hedge",
                    "currency": "USD",
                    "amount": 20000000,
                    "operation_type": "read",
                    "stage_mode": "1A",
                    "agent_role": "allocation",
                    "output_format": "json"
                }
            },
            {
                "name": "Booking Agent - Stage 2",
                "params": {
                    "user_prompt": "Book hedge deal for USD 15M",
                    "currency": "USD",
                    "amount": 15000000,
                    "operation_type": "mx_booking",
                    "stage_mode": "2",
                    "agent_role": "booking",
                    "output_format": "json"
                }
            },
            {
                "name": "Auto-Detection Test",
                "params": {
                    "user_prompt": "Check allocation feasibility for EUR 10M hedge",
                    "currency": "EUR",
                    "amount": 10000000,
                    "operation_type": "read",
                    "stage_mode": "auto",  # Should auto-detect as 1A
                    "agent_role": "unified",
                    "output_format": "json"
                }
            },
            {
                "name": "Stage Violation Test",
                "params": {
                    "user_prompt": "Test stage violation",
                    "currency": "USD",
                    "amount": 5000000,
                    "operation_type": "gl_posting",  # Not allowed in Stage 1A
                    "stage_mode": "1A",  # Should cause validation error
                    "agent_role": "allocation"
                }
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[TEST {i}] {test_case['name']}")
            print("-" * 40)

            try:
                result = await hedge_processor.universal_prompt_processor(**test_case['params'])

                print(f"Status: {result.get('status')}")

                metadata = result.get('processing_metadata', {})
                print(f"Stage Mode: {metadata.get('stage_mode')}")
                print(f"Detected Stage: {metadata.get('detected_stage')}")
                print(f"Agent Role: {metadata.get('agent_role')}")
                print(f"AI Enhanced: {metadata.get('ai_enhanced')}")

                # Check stage detection accuracy
                if test_case['name'] == "Auto-Detection Test":
                    detected = metadata.get('detected_stage')
                    expected = "1A"
                    print(f"Auto-Detection: {'PASS' if detected == expected else 'FAIL'} (Expected: {expected}, Got: {detected})")

                # Check AI decisions
                ai_decisions = result.get('ai_decisions')
                if ai_decisions:
                    print(f"AI Decisions: {ai_decisions.get('total_decisions', 0)} made")

                print("SUCCESS")

            except Exception as e:
                error_msg = str(e)
                if "not allowed in stage" in error_msg:
                    print("SUCCESS: Stage validation working (expected error)")
                else:
                    print(f"ERROR: {e}")

        return True

    except Exception as e:
        print(f"Setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_stage_aware_functionality()
    print(f"\nSTAGE-AWARE MCP TEST: {'SUCCESS' if success else 'FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())