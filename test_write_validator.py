#!/usr/bin/env python3
"""
Test script for the Strict Write Validator
Tests all validation rules and edge cases
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

async def test_write_validator():
    """Test the strict write validation system"""

    logger.info("Starting Write Validator Tests...")

    from shared.write_validator import StrictWriteValidator
    from shared.supabase_client import DatabaseManager

    # Initialize with database connection
    db_manager = DatabaseManager()
    supabase_client, _ = await db_manager.initialize_connections()

    validator = StrictWriteValidator(supabase_client)

    test_results = []

    # Test 1: Valid hedge instruction
    logger.info("\nTest 1: Valid hedge instruction")
    valid_instruction = {
        "instruction_id": "INST_TEST_001",
        "instruction_type": "I",
        "exposure_currency": "USD",
        "hedge_amount_order": 1000000.00,
        "instruction_status": "Received",
        "created_by": "TEST_USER",
        "created_date": "2025-01-15T10:30:00Z"
    }

    result = await validator.validate_write_operation(
        "hedge_instructions", "INSERT", valid_instruction
    )

    test_results.append(("Valid Instruction", result.is_valid))
    print(validator.format_validation_report(result))

    # Test 2: Missing required fields
    logger.info("\nTest 2: Missing required fields")
    invalid_instruction = {
        "instruction_type": "I",
        "exposure_currency": "USD"
        # Missing: instruction_id, hedge_amount_order, instruction_status, created_by, created_date
    }

    result = await validator.validate_write_operation(
        "hedge_instructions", "INSERT", invalid_instruction
    )

    test_results.append(("Missing Required Fields", not result.is_valid))  # Should be invalid
    print(validator.format_validation_report(result))

    # Test 3: Invalid enum values
    logger.info("\nTest 3: Invalid enum values")
    invalid_enum = {
        "instruction_id": "INST_TEST_003",
        "instruction_type": "INVALID_TYPE",  # Should be I, U, R, T, A, Q
        "exposure_currency": "INVALID_CURRENCY",  # Should be USD, EUR, etc.
        "hedge_amount_order": 1000000.00,
        "instruction_status": "INVALID_STATUS",  # Should be Received, etc.
        "created_by": "TEST_USER",
        "created_date": "2025-01-15T10:30:00Z"
    }

    result = await validator.validate_write_operation(
        "hedge_instructions", "INSERT", invalid_enum
    )

    test_results.append(("Invalid Enum Values", not result.is_valid))
    print(validator.format_validation_report(result))

    # Test 4: Type validation
    logger.info("\nTest 4: Type validation")
    wrong_types = {
        "instruction_id": 12345,  # Should be string
        "instruction_type": "I",
        "exposure_currency": "USD",
        "hedge_amount_order": "not_a_number",  # Should be numeric
        "instruction_status": "Received",
        "created_by": "TEST_USER",
        "created_date": "2025-01-15T10:30:00Z"
    }

    result = await validator.validate_write_operation(
        "hedge_instructions", "INSERT", wrong_types
    )

    test_results.append(("Wrong Types", not result.is_valid))
    print(validator.format_validation_report(result))

    # Test 5: Field constraints
    logger.info("\nTest 5: Field constraints")
    constraint_violations = {
        "instruction_id": "INVALID_FORMAT_NO_PREFIX",  # Should match pattern
        "instruction_type": "I",
        "exposure_currency": "USD",
        "hedge_amount_order": -1000.00,  # Should be positive
        "instruction_status": "Received",
        "created_by": "TEST_USER",
        "created_date": "2025-01-15T10:30:00Z"
    }

    result = await validator.validate_write_operation(
        "hedge_instructions", "INSERT", constraint_violations
    )

    test_results.append(("Constraint Violations", not result.is_valid))
    print(validator.format_validation_report(result))

    # Test 6: UPDATE without filters
    logger.info("\nTest 6: UPDATE without filters (should fail)")
    update_data = {
        "instruction_status": "Completed",
        "modified_by": "TEST_USER",
        "modified_date": "2025-01-15T10:35:00Z"
    }

    result = await validator.validate_write_operation(
        "hedge_instructions", "UPDATE", update_data  # No filters provided
    )

    test_results.append(("UPDATE without filters", not result.is_valid))
    print(validator.format_validation_report(result))

    # Test 7: Valid allocation engine record
    logger.info("\nTest 7: Valid allocation engine record")
    valid_allocation = {
        "allocation_id": "ALLOC_TEST_001",
        "entity_id": "ENTITY001",
        "currency_code": "USD",
        "hedge_amount_allocation": 500000.00,
        "allocation_status": "Calculated",
        "created_by": "TEST_USER",
        "created_date": "2025-01-15T10:30:00Z"
    }

    result = await validator.validate_write_operation(
        "allocation_engine", "INSERT", valid_allocation
    )

    test_results.append(("Valid Allocation", result.is_valid))
    print(validator.format_validation_report(result))

    # Test 8: Non-existent table
    logger.info("\nTest 8: Non-existent table")
    result = await validator.validate_write_operation(
        "non_existent_table", "INSERT", {"test": "data"}
    )

    test_results.append(("Non-existent table", not result.is_valid))
    print(validator.format_validation_report(result))

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)

    passed = 0
    failed = 0

    for test_name, expected_result in test_results:
        status = "PASS" if expected_result else "FAIL"
        logger.info(f"{status}: {test_name}")
        if expected_result:
            passed += 1
        else:
            failed += 1

    logger.info(f"\nTotal Tests: {len(test_results)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")

    if failed == 0:
        logger.info("\nSUCCESS: ALL TESTS PASSED! Write validator is working correctly.")
        return True
    else:
        logger.error(f"\nERROR: {failed} TESTS FAILED! Write validator needs fixes.")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_write_validator())
    sys.exit(0 if success else 1)