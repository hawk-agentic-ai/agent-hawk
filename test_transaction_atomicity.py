#!/usr/bin/env python3
"""
Test Transaction Atomicity - Verify that multi-table writes are atomic
Tests rollback scenarios and ensures data consistency
"""

import asyncio
import logging
import sys
from pathlib import Path

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

async def test_transaction_atomicity():
    """Test atomic transaction system with rollback scenarios"""

    logger.info("Starting Transaction Atomicity Tests...")

    from shared.supabase_client import DatabaseManager
    from shared.transaction_manager import DatabaseTransactionManager, WriteOperation, TransactionStatus
    from shared.write_validator import StrictWriteValidator
    from shared.atomic_write_operations import (
        execute_atomic_hedge_inception,
        execute_atomic_booking_and_gl,
        execute_atomic_single_table_write
    )

    # Initialize components
    db_manager = DatabaseManager()
    supabase_client, _ = await db_manager.initialize_connections()

    if not supabase_client:
        logger.error("Failed to initialize Supabase client")
        return False

    write_validator = StrictWriteValidator(supabase_client)
    transaction_manager = DatabaseTransactionManager(supabase_client, write_validator)

    test_results = []

    # Test 1: Simple atomic transaction (should succeed)
    logger.info("\nTest 1: Simple atomic transaction with valid data")

    valid_operations = [
        WriteOperation("hedge_instructions", "INSERT", {
            "instruction_id": "INST_ATOMIC_TEST_001",
            "instruction_type": "I",
            "exposure_currency": "USD",
            "hedge_amount_order": 1000000.00,
            "instruction_status": "Received",
            "entity_id": "TEST_ENTITY_001",
            "nav_type": "COI",
            "created_by": "TEST_USER",
            "created_date": "2025-01-15T10:30:00Z",
            "received_timestamp": "2025-01-15T10:30:00Z",
            "instruction_date": "2025-01-15",
            "trace_id": "TEST_TRACE_001"
        })
    ]

    result = await transaction_manager.execute_transaction(valid_operations, "test_simple_success")
    test_results.append(("Simple Transaction Success", result.status == TransactionStatus.COMMITTED))

    logger.info(f"Test 1 Result: Status={result.status.value}, Operations={result.operations_succeeded}/{result.operations_attempted}")
    if result.errors:
        logger.warning(f"Test 1 Errors: {result.errors}")

    # Test 2: Transaction with invalid data (should rollback)
    logger.info("\nTest 2: Transaction with invalid data (should rollback)")

    invalid_operations = [
        WriteOperation("hedge_instructions", "INSERT", {
            "instruction_id": "INST_ATOMIC_TEST_002",
            "instruction_type": "I",
            "exposure_currency": "USD",
            "hedge_amount_order": 2000000.00,
            "instruction_status": "Received",
            "created_by": "TEST_USER",
            "created_date": "2025-01-15T10:30:00Z"
            # Missing required fields to trigger validation failure
        }),
        WriteOperation("allocation_engine", "INSERT", {
            "allocation_id": "ALLOC_ATOMIC_TEST_002",
            "entity_id": "NONEXISTENT_ENTITY",  # This should fail FK validation
            "currency_code": "USD",
            "allocation_status": "Calculated",
            "created_by": "TEST_USER",
            "created_date": "2025-01-15T10:30:00Z"
        })
    ]

    result = await transaction_manager.execute_transaction(invalid_operations, "test_rollback")
    test_results.append(("Transaction Rollback", result.status in [TransactionStatus.ROLLED_BACK, TransactionStatus.FAILED]))

    logger.info(f"Test 2 Result: Status={result.status.value}, Rollback={result.rollback_performed}")
    if result.errors:
        logger.info(f"Test 2 Expected Errors: {result.errors}")

    # Test 3: Mixed valid/invalid operations (should rollback all)
    logger.info("\nTest 3: Mixed valid/invalid operations (should rollback all)")

    mixed_operations = [
        WriteOperation("hedge_instructions", "INSERT", {
            "instruction_id": "INST_ATOMIC_TEST_003",
            "instruction_type": "I",
            "exposure_currency": "USD",
            "hedge_amount_order": 3000000.00,
            "instruction_status": "Received",
            "entity_id": "TEST_ENTITY_003",
            "nav_type": "COI",
            "created_by": "TEST_USER",
            "created_date": "2025-01-15T10:30:00Z",
            "received_timestamp": "2025-01-15T10:30:00Z",
            "instruction_date": "2025-01-15",
            "trace_id": "TEST_TRACE_003"
        }),
        WriteOperation("allocation_engine", "INSERT", {
            "allocation_id": "ALLOC_ATOMIC_TEST_003",
            "entity_id": "NONEXISTENT_ENTITY_2",  # This will fail
            "currency_code": "USD",
            "allocation_status": "Calculated",
            "created_by": "TEST_USER",
            "created_date": "2025-01-15T10:30:00Z"
        })
    ]

    result = await transaction_manager.execute_transaction(mixed_operations, "test_mixed_rollback")
    test_results.append(("Mixed Transaction Rollback", result.status in [TransactionStatus.ROLLED_BACK, TransactionStatus.FAILED]))

    logger.info(f"Test 3 Result: Status={result.status.value}, Operations succeeded before rollback: {result.operations_succeeded}")

    # Verify rollback: Check that INST_ATOMIC_TEST_003 was NOT created
    try:
        check_result = supabase_client.table("hedge_instructions").select("instruction_id").eq("instruction_id", "INST_ATOMIC_TEST_003").execute()
        rollback_verified = len(check_result.data or []) == 0
        test_results.append(("Rollback Verification", rollback_verified))
        logger.info(f"Rollback Verification: {'PASSED' if rollback_verified else 'FAILED'} - Records found: {len(check_result.data or [])}")
    except Exception as e:
        logger.error(f"Rollback verification failed: {e}")
        test_results.append(("Rollback Verification", False))

    # Test 4: High-level atomic hedge inception
    logger.info("\nTest 4: High-level atomic hedge inception")

    class MockAnalysisResult:
        intent = type('Intent', (), {'value': 'hedge_inception'})()
        extracted_params = {"currency": "EUR", "amount": 500000}

    try:
        result = await execute_atomic_hedge_inception(
            transaction_manager=transaction_manager,
            user_prompt="Test atomic hedge inception for 500k EUR",
            analysis_result=MockAnalysisResult(),
            write_data={"target_table": "hedge_instructions"},
            currency="EUR",
            entity_id="TEST_ENTITY_004",
            nav_type="COI",
            amount=500000.00
        )

        hedge_inception_success = result.get("status") == "success"
        test_results.append(("Atomic Hedge Inception", hedge_inception_success))

        if hedge_inception_success:
            logger.info(f"Test 4 Success: {result['records_affected']} records created across {len(result['tables_modified'])} tables")
            logger.info(f"Tables modified: {result['tables_modified']}")
        else:
            logger.error(f"Test 4 Failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Test 4 Exception: {e}")
        test_results.append(("Atomic Hedge Inception", False))

    # Test 5: Transaction manager statistics
    logger.info("\nTest 5: Transaction manager statistics")

    stats = transaction_manager.get_transaction_stats()
    stats_valid = isinstance(stats, dict) and "active_transactions" in stats
    test_results.append(("Transaction Statistics", stats_valid))

    logger.info(f"Transaction Stats: {stats}")

    # Cleanup test data
    logger.info("\nCleaning up test data...")

    cleanup_instructions = ["INST_ATOMIC_TEST_001", "INST_ATOMIC_TEST_003", "INST_ATOMIC_TEST_004"]

    for instruction_id in cleanup_instructions:
        try:
            # Delete from hedge_instructions (cascading should handle related records)
            delete_result = supabase_client.table("hedge_instructions").delete().eq("instruction_id", instruction_id).execute()
            if delete_result.data:
                logger.info(f"Cleaned up instruction: {instruction_id}")
        except Exception as e:
            logger.warning(f"Cleanup failed for {instruction_id}: {e}")

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TRANSACTION ATOMICITY TEST SUMMARY")
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
        logger.info("\n🎉 SUCCESS: ALL TRANSACTION TESTS PASSED!")
        logger.info("✅ Multi-table writes are atomic")
        logger.info("✅ Rollback mechanism works correctly")
        logger.info("✅ Data consistency is maintained")
        return True
    else:
        logger.error(f"\n❌ ERROR: {failed} TRANSACTION TESTS FAILED!")
        logger.error("Database write operations may not be fully atomic")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_transaction_atomicity())
    sys.exit(0 if success else 1)