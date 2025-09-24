"""
Test MCP Workflow with unique identifiers to avoid constraint violations
"""

import os
import asyncio
import time
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_unique_workflow():
    print("TESTING UNIQUE MCP WORKFLOW")
    print("=" * 40)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("Database connection failed")
            return False

        # Test with unique amounts to avoid constraint violations
        timestamp = int(time.time())
        test_prompts = [
            (f"Create USD hedge inception instruction for {5000000 + timestamp} amount", "USD", 5000000 + timestamp),
            (f"Generate new hedge initiation for USD {7500000 + timestamp} exposure", "USD", 7500000 + timestamp),
            (f"Process hedge inception USD {9000000 + timestamp} notional", "USD", 9000000 + timestamp)
        ]

        total_success = 0
        for i, (prompt, currency, amount) in enumerate(test_prompts, 1):
            print(f"\n[TEST {i}] Prompt: '{prompt[:50]}...'")
            print("-" * 50)

            try:
                result = await hedge_processor.universal_prompt_processor(
                    prompt, currency=currency, amount=amount, operation_type="write"
                )

                print(f"Status: {result.get('status')}")
                print(f"AI Enhanced: {result.get('processing_metadata', {}).get('ai_enhanced', False)}")

                ai_decisions = result.get('ai_decisions')
                if ai_decisions:
                    print(f"AI Decisions: {ai_decisions.get('total_decisions', 0)} decisions")
                    # Show key decisions
                    decision_details = ai_decisions.get('decision_details', {})
                    key_decisions = ['entity_id', 'hedging_instrument', 'instruction_status']
                    for key in key_decisions:
                        if key in decision_details:
                            decision = decision_details[key]
                            print(f"  {key}: {decision.get('value')} (confidence: {decision.get('confidence')})")

                write_results = result.get('write_results')
                if write_results:
                    records_affected = write_results.get('records_affected', 0)
                    print(f"Records Created: {records_affected}")
                    print(f"Tables Modified: {write_results.get('tables_modified', [])}")

                    if records_affected > 0:
                        total_success += 1
                        print("SUCCESS: Record created with AI-driven parameters!")
                    else:
                        print("No records created")
                        details = write_results.get('details', {})
                        if any('error' in key for key in details.keys()):
                            print("Errors found:")
                            for key in details:
                                if 'error' in key:
                                    print(f"  {key}: {details[key]}")
                else:
                    print("No write results")

            except Exception as e:
                print(f"Error in test {i}: {e}")

        print(f"\n" + "=" * 50)
        print(f"FINAL RESULTS: {total_success}/{len(test_prompts)} tests successful")
        print(f"AI-driven MCP tool: {'WORKING' if total_success > 0 else 'NEEDS DEBUGGING'}")

        return total_success > 0

    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_unique_workflow())
    print(f"\nUNIQUE WORKFLOW RESULT: {'SUCCESS' if success else 'FAILED'}")