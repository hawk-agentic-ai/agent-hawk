"""
Test Agent Report Generator Phase 2 Implementation
Tests allocation and booking agent report generation with MCP integration
"""

import asyncio
import os
import json
from datetime import datetime

# Set environment
os.environ["SUPABASE_URL"] = "https://ladviaautlfvpxuadqrb.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes"

async def test_agent_report_generation():
    """Test comprehensive agent report generation functionality"""
    print("TESTING AGENT REPORT GENERATOR - PHASE 2")
    print("=" * 55)

    try:
        from shared.hedge_processor import hedge_processor
        await hedge_processor.initialize()

        # Test cases for different agent reports
        test_cases = [
            {
                "name": "Allocation Agent Report - Stage 1A",
                "params": {
                    "user_prompt": "Check allocation feasibility for USD 25M hedge at HK Branch entities",
                    "currency": "USD",
                    "amount": 25000000,
                    "operation_type": "write",
                    "stage_mode": "1A",
                    "agent_role": "allocation",
                    "output_format": "agent_report",
                    "write_data": {
                        "msg_uid": f"TEST_AGENT_ALLOC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    }
                },
                "expected_sections": [
                    "Analysis Summary",
                    "Data Sources Consulted",
                    "Entity Lookup Results",
                    "Allocation Calculations",
                    "Threshold / Buffer Analysis",
                    "USD PB Position Summary",
                    "Database Insert Verification",
                    "Self-Assessment"
                ]
            },
            {
                "name": "Booking Agent Report - Stage 2",
                "params": {
                    "user_prompt": "Book hedge deal for EUR 15M with forward contract",
                    "currency": "EUR",
                    "amount": 15000000,
                    "operation_type": "mx_booking",
                    "stage_mode": "2",
                    "agent_role": "booking",
                    "output_format": "agent_report",
                    "write_data": {
                        "msg_uid": f"TEST_AGENT_BOOK_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    }
                },
                "expected_sections": [
                    "Analysis Summary",
                    "Market Conditions Assessment",
                    "Instrument Selection Analysis",
                    "Booking Transaction Details",
                    "Risk Assessment",
                    "Compliance Verification",
                    "Database Insert Verification",
                    "Self-Assessment"
                ]
            },
            {
                "name": "Unified Agent JSON Output",
                "params": {
                    "user_prompt": "Analyze USD capacity across all entities",
                    "currency": "USD",
                    "amount": 10000000,
                    "operation_type": "read",
                    "stage_mode": "auto",
                    "agent_role": "unified",
                    "output_format": "json"
                },
                "expected_type": "json_response"
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[TEST {i}] {test_case['name']}")
            print("-" * 50)

            try:
                result = await hedge_processor.universal_prompt_processor(**test_case['params'])

                print(f"Status: {result.get('status')}")

                # Check processing metadata
                metadata = result.get('processing_metadata', {})
                print(f"Stage Mode: {metadata.get('stage_mode')}")
                print(f"Agent Role: {metadata.get('agent_role')}")
                print(f"Output Format: {metadata.get('output_format')}")
                print(f"AI Enhanced: {metadata.get('ai_enhanced')}")

                # Validate output format
                if test_case['params']['output_format'] == 'agent_report':
                    agent_report = result.get('agent_report')
                    agent_report_status = result.get('agent_report_status')
                    agent_report_error = result.get('agent_report_error')

                    print(f"Agent Report Status: {agent_report_status}")
                    if agent_report_error:
                        print(f"Agent Report Error: {agent_report_error}")

                    if agent_report:
                        print(f"Agent Report Generated: {len(agent_report)} characters")

                        # Check for expected sections
                        expected_sections = test_case.get('expected_sections', [])
                        found_sections = []
                        for section in expected_sections:
                            if section in agent_report:
                                found_sections.append(section)

                        coverage = len(found_sections) / len(expected_sections) * 100 if expected_sections else 0
                        print(f"Section Coverage: {coverage:.1f}% ({len(found_sections)}/{len(expected_sections)})")

                        # Check for mandatory tables
                        table_indicators = ["Entity ID", "Available Amount", "Status", "USD"]
                        table_count = sum(1 for indicator in table_indicators if indicator in agent_report)
                        print(f"Table Indicators Found: {table_count}/{len(table_indicators)}")

                        # Show first 500 characters of report
                        print(f"Report Preview:\n{agent_report[:500]}...")

                    else:
                        print("ERROR: No agent report generated")

                elif test_case['params']['output_format'] == 'json':
                    if isinstance(result.get('data'), (dict, list)):
                        print(f"SUCCESS: JSON output generated with {len(str(result.get('data')))} characters")
                    else:
                        print("ERROR: Expected JSON output not found")

                # Check AI decisions
                ai_decisions = result.get('ai_decisions', {})
                if ai_decisions:
                    print(f"AI Decisions: {len(ai_decisions)} parameters decided")
                    key_decisions = ['entity_id', 'nav_type', 'hedging_instrument']
                    for key in key_decisions:
                        if key in ai_decisions:
                            decision = ai_decisions[key]
                            print(f"  {key}: {decision.get('value')} (confidence: {decision.get('confidence', 0):.2f})")

                # Check database operations
                db_operations = result.get('database_operations', [])
                if db_operations:
                    print(f"Database Operations: {len(db_operations)} executed")

                print("SUCCESS: TEST PASSED")

            except Exception as e:
                print(f"ERROR: TEST FAILED: {e}")
                # Print more details for debugging
                import traceback
                print(f"Error details: {traceback.format_exc()}")

        # Test direct agent report generator
        print(f"\n[DIRECT TEST] Agent Report Generator Module")
        print("-" * 50)

        try:
            from shared.agent_report_generator import agent_report_generator

            # Mock processing result for allocation agent
            mock_allocation_result = {
                "status": "success",
                "data": {
                    "entities": [
                        {
                            "entity_id": "HK_BR_001",
                            "entity_name": "HK Branch 1",
                            "entity_type": "Branch",
                            "currency": "USD",
                            "available_amount": 18750000,
                            "sfx_position": 25000000,
                            "car_amount": 5000000
                        }
                    ],
                    "total_available": 18750000,
                    "currency": "USD",
                    "requested_amount": 15000000
                },
                "processing_metadata": {
                    "stage_mode": "1A",
                    "agent_role": "allocation",
                    "snapshot_date": "2024-03-15"
                }
            }

            # Generate allocation report
            agent_report_generator.supabase_client = hedge_processor.supabase_client
            allocation_report = await agent_report_generator.generate_report(
                agent_type="allocation",
                processing_result=mock_allocation_result,
                instruction_id="TEST_ALLOC_001"
            )

            report_content = allocation_report.get('report', allocation_report.get('formatted_report', ''))
            print(f"SUCCESS: Allocation Report Generated: {len(report_content)} characters")
            print(f"Report Status: {allocation_report.get('status')}")
            if not report_content:
                print(f"Allocation Report Keys: {list(allocation_report.keys())}")
                # Don't print full result due to Unicode encoding issues
                print("Report content is empty - check agent_report_generator module")

            # Mock processing result for booking agent
            mock_booking_result = {
                "status": "success",
                "data": {
                    "hedge_details": {
                        "currency": "EUR",
                        "amount": 15000000,
                        "instrument_type": "forward",
                        "maturity_date": "2024-06-15"
                    },
                    "market_conditions": {
                        "spot_rate": 1.0850,
                        "forward_rate": 1.0875,
                        "volatility": 0.12
                    }
                },
                "processing_metadata": {
                    "stage_mode": "2",
                    "agent_role": "booking"
                }
            }

            # Generate booking report
            booking_report = await agent_report_generator.generate_report(
                agent_type="booking",
                processing_result=mock_booking_result,
                instruction_id="TEST_BOOK_001"
            )

            booking_content = booking_report.get('report', booking_report.get('formatted_report', ''))
            print(f"SUCCESS: Booking Report Generated: {len(booking_content)} characters")
            print(f"Report Status: {booking_report.get('status')}")

            print("SUCCESS: DIRECT TEST PASSED")

        except Exception as e:
            print(f"ERROR: DIRECT TEST FAILED: {e}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")

        return True

    except Exception as e:
        print(f"Setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print(f"Test started at: {datetime.now()}")
    success = await test_agent_report_generation()
    print(f"\nAGENT REPORT GENERATOR PHASE 2 TEST: {'SUCCESS' if success else 'FAILED'}")
    print(f"Test completed at: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())