"""
Test Hedge Processor AI Integration
"""

import os
import asyncio

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_processor_integration():
    print("TESTING HEDGE PROCESSOR AI INTEGRATION")
    print("=" * 50)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        if not hedge_processor.supabase_client:
            print("ERROR: Database connection failed")
            return False

        print("Database connected successfully")

        # Test with one simple prompt
        prompt = "Create USD 6M hedge inception instruction"
        print(f"Testing prompt: '{prompt}'")

        try:
            # Force write operation mode
            result = await hedge_processor.universal_prompt_processor(
                prompt,
                currency="USD",
                amount=6000000,
                operation_type="write"  # Explicitly set to write
            )

            print(f"Operation completed")
            print(f"Status: {result.get('status')}")
            print(f"AI Enhanced: {result.get('processing_metadata', {}).get('ai_enhanced', False)}")

            # Check AI decisions
            ai_decisions = result.get('ai_decisions')
            if ai_decisions:
                print(f"AI Decisions: {ai_decisions.get('total_decisions', 0)} decisions made")
                decision_details = ai_decisions.get('decision_details', {})
                for key in list(decision_details.keys())[:3]:  # Show first 3
                    decision = decision_details[key]
                    print(f"  - {key}: {decision.get('value')} (confidence: {decision.get('confidence')})")
            else:
                print("AI Decisions: None")

            # Check write results
            write_results = result.get('write_results')
            if write_results:
                print(f"Write Results: {write_results.get('records_affected', 0)} records affected")
                print(f"Tables modified: {write_results.get('tables_modified', [])}")
                if write_results.get('details'):
                    print(f"Details keys: {list(write_results['details'].keys())}")
            else:
                print("Write Results: None")

            return result.get('status') == 'success'

        except Exception as e:
            print(f"Processor error: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"Setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_processor_integration())
    print(f"\nPROCESSOR INTEGRATION TEST: {'SUCCESS' if success else 'FAILED'}")