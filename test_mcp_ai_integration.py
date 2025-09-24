"""
Test AI Integration through MCP Server Interface
"""

import asyncio
import json
import httpx
import os

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_mcp_ai_flow():
    print("TESTING AI INTEGRATION THROUGH MCP SERVER")
    print("=" * 50)

    # Test direct processor (bypassing HTTP)
    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        prompt = "Create USD 15M hedge inception instruction"
        print(f"Testing prompt: {prompt}")

        result = await hedge_processor.universal_prompt_processor(
            user_prompt=prompt,
            currency="USD",
            amount=15000000,
            operation_type="write"
        )

        print(f"\nSTATUS: {result.get('status')}")
        print(f"AI ENHANCED: {result.get('processing_metadata', {}).get('ai_enhanced', False)}")

        # Extract AI decision information
        ai_decisions = result.get('ai_decisions')
        if ai_decisions:
            print(f"\nAI DECISIONS MADE: {ai_decisions.get('total_decisions', 0)}")
            decision_details = ai_decisions.get('decision_details', {})

            print("Key AI Decisions:")
            key_decisions = ['entity_id', 'hedging_instrument', 'accounting_method', 'instruction_status']
            for key in key_decisions:
                if key in decision_details:
                    decision = decision_details[key]
                    print(f"  {key}: {decision.get('value')} (confidence: {decision.get('confidence')})")
                    if decision.get('reasoning'):
                        print(f"    Reasoning: {decision.get('reasoning')[:80]}...")

            print(f"\nContext Analysis:")
            context = ai_decisions.get('context_analysis', {})
            print(f"  Geographic: {context.get('geographic_indicators', [])}")
            print(f"  Urgency: {context.get('urgency_level', 'standard')}")
            print(f"  Operation Type: {context.get('operation_type', 'inception')}")
            print(f"  Risk Profile: {context.get('risk_profile', 'medium')}")
        else:
            print("NO AI DECISIONS FOUND")

        # Check write results
        write_results = result.get('write_results')
        if write_results:
            print(f"\nWRITE OPERATIONS:")
            print(f"  Records Created: {write_results.get('records_affected', 0)}")
            print(f"  Tables Modified: {write_results.get('tables_modified', [])}")

            # Show what got written
            details = write_results.get('details', {})
            if 'hedge_instructions' in details:
                hedge_data = details['hedge_instructions']
                print(f"  Instruction ID: {hedge_data.get('instruction_id')}")
                print(f"  Instruction Status: {hedge_data.get('instruction_status')}")
                print(f"  Hedge Method: {hedge_data.get('hedge_method')}")
        else:
            print("NO WRITE RESULTS")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_mcp_ai_flow()
    print(f"\nMCP AI INTEGRATION TEST: {'SUCCESS' if success else 'FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())