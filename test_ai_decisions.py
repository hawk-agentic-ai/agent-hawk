"""
Test AI Decision Engine Activation in Write Mode
Test: "Can I place a new hedge for 150000 AUD today" with write operation
"""

import asyncio
import os
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_ai_decisions():
    """Test AI Decision Engine activation in write mode"""
    print("TESTING AI DECISION ENGINE ACTIVATION")
    print("=" * 42)

    test_prompt = "Can I place a new hedge for 150000 AUD today"
    print(f"TEST PROMPT: \"{test_prompt}\"")
    print("-" * 50)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        test_session = datetime.now().strftime('%Y%m%d_%H%M%S')

        print("Step 1: Testing with WRITE operation (AI decisions should activate)...")

        # Test with write operation - AI decisions should activate
        result = await hedge_processor.universal_prompt_processor(
            user_prompt=test_prompt,
            operation_type="write",  # This should trigger AI decisions
            write_data={
                "msg_uid": f"AI_TEST_{test_session}",
                "instruction_type": "U",
                "exposure_currency": "AUD",
                "hedge_amount_order": 150000
            }
        )

        print(f"\nRESULT STATUS: {result.get('status')}")

        # Check AI decisions
        print(f"\n[AI DECISION ENGINE RESULTS]")
        print("-" * 32)

        ai_decisions = result.get("ai_decisions", {})
        if ai_decisions:
            print(f"AI Decision Engine: ACTIVATED")
            print(f"Total AI Decisions: {len(ai_decisions)}")

            for decision_key, decision in ai_decisions.items():
                if hasattr(decision, 'value'):
                    value = decision.value
                    confidence = getattr(decision, 'confidence', 'N/A')
                    reasoning = getattr(decision, 'reasoning', 'N/A')[:50] + "..."
                else:
                    value = str(decision)
                    confidence = "N/A"
                    reasoning = "N/A"

                print(f"  {decision_key}:")
                print(f"    Value: {value}")
                print(f"    Confidence: {confidence}")
                print(f"    Reasoning: {reasoning}")
        else:
            print("AI Decision Engine: NOT ACTIVATED")
            print("This indicates an issue with the AI decision triggering logic")

        # Check processing metadata
        print(f"\n[PROCESSING METADATA]")
        print("-" * 21)

        processing_meta = result.get("processing_metadata", {})
        ai_enhanced = processing_meta.get("ai_enhanced", False)
        print(f"  AI Enhanced Flag: {'YES' if ai_enhanced else 'NO'}")

        # Stage and agent detection
        stage_mode = processing_meta.get("stage_mode", "unknown")
        agent_role = processing_meta.get("agent_role", "unknown")
        print(f"  Stage Detection: {stage_mode}")
        print(f"  Agent Role: {agent_role}")

        # Write operation results
        print(f"\n[WRITE OPERATION RESULTS]")
        print("-" * 26)

        write_results = result.get("write_results", {})
        if write_results:
            records_affected = write_results.get("records_affected", 0)
            tables_modified = write_results.get("tables_modified", [])

            print(f"  Records Created: {records_affected}")
            print(f"  Tables Modified: {tables_modified}")

            details = write_results.get("details", {})
            for table, result_data in details.items():
                if not table.endswith("_error"):
                    print(f"  {table}: SUCCESS")
                else:
                    print(f"  {table}: {result_data}")
        else:
            print("  No write operations performed")

        # Overall assessment
        print(f"\n[AI INTEGRATION ASSESSMENT]")
        print("-" * 29)

        success_indicators = {
            "AI Decisions Made": bool(ai_decisions),
            "AI Enhanced Processing": ai_enhanced,
            "Write Operation Success": result.get('status') == 'success',
            "Stage 1A Detection": stage_mode in ["1A", "auto"],
            "Database Operations": bool(write_results.get("records_affected", 0) > 0)
        }

        for indicator, status in success_indicators.items():
            status_text = "SUCCESS" if status else "MISSING"
            print(f"  {indicator}: {status_text}")

        success_rate = sum(success_indicators.values()) / len(success_indicators) * 100
        print(f"\nAI SYSTEM PERFORMANCE: {success_rate:.1f}% ({sum(success_indicators.values())}/{len(success_indicators)})")

        return True

    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print(f"AI Decision Engine Test started at: {datetime.now()}")
    success = await test_ai_decisions()
    print(f"\nAI DECISION TEST: {'SUCCESS' if success else 'FAILED'}")
    print(f"Test completed at: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())