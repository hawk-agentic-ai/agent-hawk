"""
Trace MCP Server Operations for Specific Prompt
Test: "Can I place a new hedge for 150000 AUD today"
Track all tables fetched and tools used
"""

import asyncio
import os
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def trace_mcp_operations():
    """Trace MCP server operations for the specific prompt"""
    print("TRACING MCP SERVER OPERATIONS")
    print("=" * 40)

    test_prompt = "Can I place a new hedge for 150000 AUD today"
    print(f"TEST PROMPT: \"{test_prompt}\"")
    print("-" * 50)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        print("Step 1: Initializing MCP processor...")
        print("Step 2: Processing prompt with full tracing...")

        # Execute the prompt with detailed tracking
        result = await hedge_processor.universal_prompt_processor(
            user_prompt=test_prompt,
            operation_type="read",  # Safe read operation for tracing
            output_format="json"
        )

        print(f"\nRESULT STATUS: {result.get('status')}")

        # Analyze extracted data (tables fetched)
        print(f"\n[TABLES FETCHED BY MCP SERVER]")
        print("-" * 35)

        extracted_data = result.get("extracted_data", {})
        if extracted_data:
            print(f"Total tables accessed: {len(extracted_data)}")

            for table_name, table_data in extracted_data.items():
                if isinstance(table_data, list):
                    record_count = len(table_data)
                    print(f"  {table_name}: {record_count} records")

                    # Show sample of first record structure
                    if record_count > 0 and isinstance(table_data[0], dict):
                        sample_fields = list(table_data[0].keys())[:5]  # First 5 fields
                        print(f"    Sample fields: {sample_fields}")
                else:
                    print(f"  {table_name}: {type(table_data).__name__} data")
        else:
            print("  No table data extracted")

        # Analyze AI decisions (tools/intelligence used)
        print(f"\n[AI TOOLS & INTELLIGENCE USED]")
        print("-" * 33)

        ai_decisions = result.get("ai_decisions", {})
        if ai_decisions:
            print(f"AI decision engine activated: {len(ai_decisions)} decisions")

            for decision_key, decision in ai_decisions.items():
                if not decision_key.startswith("_"):
                    value = getattr(decision, 'value', 'N/A')
                    confidence = getattr(decision, 'confidence', 'N/A')
                    reasoning = getattr(decision, 'reasoning', 'N/A')[:60] + "..."

                    print(f"  {decision_key}:")
                    print(f"    Value: {value}")
                    print(f"    Confidence: {confidence}")
                    print(f"    Reasoning: {reasoning}")
        else:
            print("  No AI decisions made")

        # Analyze processing metadata (system tools used)
        print(f"\n[SYSTEM TOOLS & COMPONENTS USED]")
        print("-" * 35)

        processing_meta = result.get("processing_metadata", {})
        if processing_meta:
            ai_enhanced = processing_meta.get("ai_enhanced", False)
            processing_time = processing_meta.get("processing_time_ms", 0)
            cache_stats = processing_meta.get("cache_stats", {})

            print(f"  AI Enhancement: {'ACTIVE' if ai_enhanced else 'INACTIVE'}")
            print(f"  Processing Time: {processing_time}ms")
            print(f"  Cache System: {cache_stats}")

            # Show detected parameters
            stage_mode = processing_meta.get("stage_mode", "unknown")
            agent_role = processing_meta.get("agent_role", "unknown")
            output_format = processing_meta.get("output_format", "unknown")

            print(f"  Stage Detection: {stage_mode}")
            print(f"  Agent Role: {agent_role}")
            print(f"  Output Format: {output_format}")

        # Analyze context analysis results
        print(f"\n[CONTEXT ANALYSIS RESULTS]")
        print("-" * 28)

        analysis = result.get("analysis", {})
        if analysis:
            intent = analysis.get("intent", {})
            confidence = analysis.get("confidence", 0)
            data_scope = analysis.get("data_scope", [])
            parameters = analysis.get("parameters", {})

            print(f"  Intent Detected: {intent}")
            print(f"  Confidence Level: {confidence}%")
            print(f"  Data Scope: {data_scope}")
            print(f"  Extracted Parameters:")

            for param_key, param_value in parameters.items():
                print(f"    {param_key}: {param_value}")

        # Currency and amount detection
        print(f"\n[PROMPT INTELLIGENCE ANALYSIS]")
        print("-" * 32)

        # Check for currency detection
        currency_detected = None
        amount_detected = None

        if "AUD" in str(result):
            currency_detected = "AUD"
        if "150000" in str(result):
            amount_detected = "150,000"

        print(f"  Currency Detection: {currency_detected or 'Not detected'}")
        print(f"  Amount Detection: {amount_detected or 'Not detected'}")
        print(f"  Geographic Context: {'Australia' if currency_detected == 'AUD' else 'Not determined'}")
        print(f"  Operation Type: {'New hedge placement' if 'place' in test_prompt else 'Unknown'}")

        # Check for Stage 1A specific processing
        print(f"\n[ALLOCATION AGENT (STAGE 1A) ANALYSIS]")
        print("-" * 38)

        # Based on the HAWK Allocation Agent prompt, this should be Stage 1A
        print(f"  Stage 1A Scope: Utilization Check ('U') or New Hedge Feasibility ('I')")
        print(f"  Expected Behavior: Pre-utilization feasibility assessment")
        print(f"  Should NOT do: Actual booking, GL posting, or trade execution")

        # Check if this triggered allocation logic
        allocation_relevant = any(table in extracted_data for table in [
            'allocation_engine', 'buffer_configuration', 'threshold_configuration',
            'entity_master', 'position_nav_master'
        ])

        print(f"  Allocation Tables Accessed: {'YES' if allocation_relevant else 'NO'}")

        if allocation_relevant:
            print(f"  Stage 1A Process: CORRECTLY TRIGGERED")
            print(f"  Expected Output: Feasibility assessment with capacity analysis")
        else:
            print(f"  Stage 1A Process: May need review")

        # Tool chain summary
        print(f"\n[MCP TOOL CHAIN SUMMARY]")
        print("-" * 27)

        tools_used = []

        if extracted_data:
            tools_used.append("Data Extraction Tool")
        if ai_decisions:
            tools_used.append("AI Decision Engine")
        if processing_meta.get("ai_enhanced"):
            tools_used.append("AI Enhancement System")
        if result.get("optimized_context"):
            tools_used.append("Context Optimization")

        print(f"  Tools Activated: {len(tools_used)}")
        for i, tool in enumerate(tools_used, 1):
            print(f"    {i}. {tool}")

        print(f"\n[FINAL ASSESSMENT]")
        print("-" * 18)

        success_indicators = {
            "Prompt Processing": result.get('status') == 'success',
            "Data Extraction": bool(extracted_data),
            "AI Intelligence": bool(ai_decisions),
            "Currency Detection": currency_detected == "AUD",
            "Amount Detection": amount_detected == "150,000",
            "Stage 1A Scope": allocation_relevant
        }

        for indicator, status in success_indicators.items():
            status_text = "SUCCESS" if status else "MISSING"
            print(f"  {indicator}: {status_text}")

        success_rate = sum(success_indicators.values()) / len(success_indicators) * 100
        print(f"\nOVERALL MCP PERFORMANCE: {success_rate:.1f}% ({sum(success_indicators.values())}/{len(success_indicators)})")

        return True

    except Exception as e:
        print(f"Trace error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print(f"MCP Operation Trace started at: {datetime.now()}")
    success = await trace_mcp_operations()
    print(f"\nMCP TRACE: {'SUCCESS' if success else 'FAILED'}")
    print(f"Trace completed at: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())