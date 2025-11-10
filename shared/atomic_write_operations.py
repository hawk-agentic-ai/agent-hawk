"""
Atomic Write Operations - Transaction-based database operations
Replaces individual table writes with atomic multi-table transactions
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .transaction_manager import WriteOperation, TransactionResult

logger = logging.getLogger(__name__)

async def execute_atomic_hedge_inception(transaction_manager,
                                       user_prompt: str,
                                       analysis_result,
                                       write_data: Dict[str, Any],
                                       currency: str,
                                       entity_id: str,
                                       nav_type: str,
                                       amount: float,
                                       ai_decisions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Atomic hedge inception - Creates instruction + allocation + business event atomically
    All operations succeed or all are rolled back
    """

    logger.info("Starting atomic hedge inception transaction")

    # Helper function to get AI decision values
    def get_ai_value(decision_key: str, fallback_value: Any) -> Any:
        try:
            if ai_decisions and decision_key in ai_decisions:
                decision = ai_decisions[decision_key]
                return getattr(decision, 'value', decision)
            return fallback_value
        except Exception:
            return fallback_value

    # Prepare transaction operations
    operations = []

    # Operation 1: Create hedge instruction
    effective_currency = currency or (write_data and write_data.get("exposure_currency")) or get_ai_value("currency", "USD")
    effective_amount = amount or (write_data and write_data.get("hedge_amount_order")) or get_ai_value("amount", 1000000)

    instruction_data = {
        "instruction_id": (write_data and write_data.get("instruction_id")) or f"INST_{analysis_result.intent.value.upper()}_{int(time.time())}",
        "instruction_type": (write_data and write_data.get("instruction_type")) or analysis_result.intent.value[6:7].upper(),
        "exposure_currency": effective_currency,
        "hedge_amount_order": effective_amount,
        "hedge_method": (write_data and write_data.get("hedge_method")) or get_ai_value("hedge_method", "COH"),
        "instruction_status": (write_data and write_data.get("instruction_status")) or get_ai_value("instruction_status", "Received"),
        "entity_id": entity_id or get_ai_value("entity_id", "ENTITY001"),
        "nav_type": nav_type or get_ai_value("nav_type", "COI"),
        "created_by": "HAWK_AGENT",
        "created_date": datetime.now().isoformat(),
        "received_timestamp": datetime.now().isoformat(),
        "instruction_date": datetime.now().date().isoformat(),
        "trace_id": f"HI-ATOMIC_{int(time.time())}"
    }

    operations.append(WriteOperation("hedge_instructions", "INSERT", instruction_data))

    # Operation 2: Create allocation record
    allocation_data = {
        "allocation_id": f"ALLOC_ATOMIC_{int(time.time())}",
        "request_id": f"REQ_ATOMIC_{int(time.time())}",
        "entity_id": entity_id or get_ai_value("entity_id", "ENTITY001"),
        "currency_code": effective_currency,
        "nav_type": nav_type or get_ai_value("nav_type", "COI"),
        "hedge_amount_allocation": effective_amount,
        "sfx_position": 0,
        "calculation_date": datetime.now().date().isoformat(),
        "executed_date": datetime.now().date().isoformat(),
        "allocation_status": get_ai_value("allocation_status", "Calculated"),
        "created_by": "HAWK_AGENT",
        "created_date": datetime.now().isoformat(),
        "instruction_id": instruction_data["instruction_id"]  # Link to instruction
    }

    operations.append(WriteOperation("allocation_engine", "INSERT", allocation_data))

    # Operation 3: Create business event record
    event_data = {
        "event_id": f"EVENT_ATOMIC_{int(time.time())}",
        "instruction_id": instruction_data["instruction_id"],
        "entity_id": entity_id or get_ai_value("entity_id", "ENTITY001"),
        "nav_type": nav_type or get_ai_value("nav_type", "COI"),
        "currency_type": get_ai_value("currency_type", "Matched"),
        "hedging_instrument": get_ai_value("hedging_instrument", "FX_Swap"),
        "accounting_method": get_ai_value("accounting_method", "COH"),
        "notional_amount": effective_amount,
        "trade_date": datetime.now().date().isoformat(),
        "business_event_type": get_ai_value("business_event_type", "Initiation"),
        "event_status": get_ai_value("event_status", "Pending"),
        "stage_1a_status": get_ai_value("stage_1a_status", "Pending"),
        "created_by": "HAWK_AGENT",
        "created_date": datetime.now().isoformat(),
        "notes": f"Atomic transaction from: {user_prompt[:100]}"
    }

    operations.append(WriteOperation("hedge_business_events", "INSERT", event_data))

    # Execute atomic transaction
    try:
        transaction_result = await transaction_manager.execute_transaction(
            operations,
            transaction_name="hedge_inception",
            validate_before_commit=True
        )

        # Convert transaction result to expected format
        if transaction_result.status.value == "committed":
            return {
                "status": "success",
                "records_affected": transaction_result.operations_succeeded,
                "details": {
                    "hedge_instructions": transaction_result.results[0] if len(transaction_result.results) > 0 else None,
                    "allocation_engine": transaction_result.results[1] if len(transaction_result.results) > 1 else None,
                    "hedge_business_events": transaction_result.results[2] if len(transaction_result.results) > 2 else None
                },
                "tables_modified": ["hedge_instructions", "allocation_engine", "hedge_business_events"],
                "transaction_id": transaction_result.transaction_id,
                "execution_time_ms": transaction_result.execution_time_ms
            }
        else:
            return {
                "status": "error",
                "error": f"Transaction {transaction_result.status.value}: {', '.join(transaction_result.errors)}",
                "records_affected": 0,
                "transaction_id": transaction_result.transaction_id,
                "rollback_performed": transaction_result.rollback_performed
            }

    except Exception as e:
        logger.error(f"Atomic hedge inception failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "records_affected": 0
        }

async def execute_atomic_booking_and_gl(transaction_manager,
                                      user_prompt: str,
                                      instruction_id: str,
                                      write_data: Dict[str, Any],
                                      currency: str,
                                      amount: float,
                                      ai_decisions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Atomic booking and GL posting - Creates booking + GL package + GL entries atomically
    """

    logger.info(f"Starting atomic booking and GL transaction for instruction: {instruction_id}")

    def get_ai_value(decision_key: str, fallback_value: Any) -> Any:
        try:
            if ai_decisions and decision_key in ai_decisions:
                decision = ai_decisions[decision_key]
                return getattr(decision, 'value', decision)
            return fallback_value
        except Exception:
            return fallback_value

    operations = []

    # Operation 1: Create booking record
    booking_data = {
        "booking_id": f"BOOKING_ATOMIC_{int(time.time())}",
        "instruction_id": instruction_id,
        "event_id": (write_data and write_data.get("event_id")),
        "murex_deal_id": (write_data and write_data.get("murex_deal_id")) or f"MRX_ATOMIC_{int(time.time())}",
        "portfolio_code": get_ai_value("portfolio_code", "CO_FX"),
        "notional_amount": amount,
        "currency": currency,
        "value_date": get_ai_value("value_date", None),
        "maturity_date": get_ai_value("maturity_date", None),
        "booking_status": get_ai_value("booking_status", "Pending"),
        "created_by": "HAWK_AGENT",
        "created_date": datetime.now().isoformat(),
        "notes": f"Atomic booking from: {user_prompt[:100]}"
    }

    operations.append(WriteOperation("deal_bookings", "INSERT", booking_data))

    # Operation 2: Create GL package
    gl_package_data = {
        "package_id": f"GL_PKG_ATOMIC_{int(time.time())}",
        "instruction_id": instruction_id,
        "event_id": (write_data and write_data.get("event_id")),
        "booking_id": booking_data["booking_id"],
        "package_status": get_ai_value("package_status", "DRAFT"),
        "gl_date": get_ai_value("gl_date", datetime.now().date().isoformat()),
        "total_debit_amount": 0,  # Will be updated after entries
        "total_credit_amount": 0,  # Will be updated after entries
        "currency": currency,
        "created_by": "HAWK_AGENT",
        "created_date": datetime.now().isoformat(),
        "notes": f"Atomic GL package from: {user_prompt[:100]}"
    }

    operations.append(WriteOperation("hedge_gl_packages", "INSERT", gl_package_data))

    # Operation 3 & 4: Create balanced GL entries (DR + CR)
    debit_entry = {
        "entry_id": f"GL_DR_ATOMIC_{int(time.time())}",
        "package_id": gl_package_data["package_id"],
        "instruction_id": instruction_id,
        "account_code": get_ai_value("debit_account_code", "999999"),
        "debit_amount": amount,
        "credit_amount": 0,
        "entry_type": "DEBIT",
        "currency": currency,
        "narrative": get_ai_value("narrative", f"Hedge operation - {instruction_id}"),
        "business_unit": get_ai_value("business_unit", "TRADING"),
        "profit_center": get_ai_value("profit_center", "FX_HEDGE"),
        "created_by": "HAWK_AGENT",
        "created_date": datetime.now().isoformat()
    }

    credit_entry = {
        "entry_id": f"GL_CR_ATOMIC_{int(time.time())}",
        "package_id": gl_package_data["package_id"],
        "instruction_id": instruction_id,
        "account_code": get_ai_value("credit_account_code", "888888"),
        "debit_amount": 0,
        "credit_amount": amount,
        "entry_type": "CREDIT",
        "currency": currency,
        "narrative": get_ai_value("narrative", f"Hedge operation - {instruction_id}"),
        "business_unit": get_ai_value("business_unit", "TRADING"),
        "profit_center": get_ai_value("profit_center", "FX_HEDGE"),
        "created_by": "HAWK_AGENT",
        "created_date": datetime.now().isoformat()
    }

    operations.append(WriteOperation("hedge_gl_entries", "INSERT", debit_entry))
    operations.append(WriteOperation("hedge_gl_entries", "INSERT", credit_entry))

    # Operation 5: Update GL package totals
    gl_package_update = {
        "total_debit_amount": amount,
        "total_credit_amount": amount,
        "package_status": "BALANCED",
        "modified_by": "HAWK_AGENT",
        "modified_date": datetime.now().isoformat()
    }

    operations.append(WriteOperation(
        "hedge_gl_packages",
        "UPDATE",
        gl_package_update,
        filters={"package_id": gl_package_data["package_id"]}
    ))

    # Execute atomic transaction
    try:
        transaction_result = await transaction_manager.execute_transaction(
            operations,
            transaction_name="booking_and_gl",
            validate_before_commit=True
        )

        if transaction_result.status.value == "committed":
            return {
                "status": "success",
                "records_affected": transaction_result.operations_succeeded,
                "details": {
                    "deal_bookings": transaction_result.results[0] if len(transaction_result.results) > 0 else None,
                    "hedge_gl_packages": transaction_result.results[1] if len(transaction_result.results) > 1 else None,
                    "gl_entries_count": 2,
                    "balanced_amounts": {"debit": amount, "credit": amount}
                },
                "tables_modified": ["deal_bookings", "hedge_gl_packages", "hedge_gl_entries"],
                "transaction_id": transaction_result.transaction_id,
                "execution_time_ms": transaction_result.execution_time_ms
            }
        else:
            return {
                "status": "error",
                "error": f"Transaction {transaction_result.status.value}: {', '.join(transaction_result.errors)}",
                "records_affected": 0,
                "transaction_id": transaction_result.transaction_id,
                "rollback_performed": transaction_result.rollback_performed
            }

    except Exception as e:
        logger.error(f"Atomic booking and GL failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "records_affected": 0
        }

async def execute_atomic_single_table_write(transaction_manager,
                                          table_name: str,
                                          operation: str,
                                          data: Dict[str, Any],
                                          filters: Optional[Dict[str, Any]] = None,
                                          validate: bool = True) -> Dict[str, Any]:
    """
    Atomic single table write - Even single operations use transactions for consistency
    """

    logger.info(f"Starting atomic single table write: {operation} on {table_name}")

    operations = [WriteOperation(table_name, operation, data, filters)]

    try:
        transaction_result = await transaction_manager.execute_transaction(
            operations,
            transaction_name=f"single_{operation.lower()}",
            validate_before_commit=validate
        )

        if transaction_result.status.value == "committed":
            return {
                "status": "success",
                "records_affected": transaction_result.operations_succeeded,
                "details": {
                    table_name: transaction_result.results[0] if transaction_result.results else None
                },
                "tables_modified": [table_name],
                "transaction_id": transaction_result.transaction_id,
                "execution_time_ms": transaction_result.execution_time_ms
            }
        else:
            return {
                "status": "error",
                "error": f"Transaction {transaction_result.status.value}: {', '.join(transaction_result.errors)}",
                "records_affected": 0,
                "transaction_id": transaction_result.transaction_id,
                "rollback_performed": transaction_result.rollback_performed
            }

    except Exception as e:
        logger.error(f"Atomic single table write failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "records_affected": 0
        }