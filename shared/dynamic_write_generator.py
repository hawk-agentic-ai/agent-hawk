"""
Dynamic Write Data Generator - Intelligent Backend for All Hedge Fund Scenarios
Automatically generates valid write data based on context, intent, and business rules
"""

import logging
import uuid
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum

logger = logging.getLogger(__name__)

class StageType(Enum):
    STAGE_1A = "1A"  # Allocation/Utilization
    STAGE_2 = "2"    # Booking/Murex
    STAGE_3 = "3"    # GL Posting

class IntentType(Enum):
    HEDGE_UTILIZATION = "hedge_utilization"
    HEDGE_BOOKING = "hedge_booking"
    GL_POSTING = "gl_posting"
    REPORTING = "reporting"
    CONFIGURATION = "configuration"

class OperationType(Enum):
    READ = "read"
    WRITE = "write"
    AMEND = "amend"
    MX_BOOKING = "mx_booking"
    GL_POSTING = "gl_posting"

class DynamicWriteGenerator:
    """
    Intelligent write data generator that adapts to different scenarios:
    - Stage 1A: hedge_instructions, hedge_business_events (feasibility only)
    - Stage 1B: allocation_engine (actual allocation)
    - Stage 2: deal_bookings, h_stg_mrx_ext
    - Stage 3: hedge_gl_packages, hedge_gl_entries
    - Config: entity_master, threshold_configuration
    """

    def __init__(self):
        # Valid enum values extracted from schema
        self.valid_values = {
            "instruction_type": ["I", "U", "R", "T", "A", "Q"],
            "instruction_status": ["Received", "Validated", "Processing", "Completed", "Failed", "Cancelled", "Executed"],
            "exposure_currency": ["USD", "EUR", "GBP", "JPY", "HKD", "SGD", "CAD", "AUD", "CNY", "KRW"],
            "check_status": ["Pass", "Fail", "Pending", "Warning"],
            "event_status": ["Pending", "Active", "Completed", "Failed", "Cancelled"],
            "booking_status": ["Pending", "Booked", "Failed", "Cancelled", "Settled"],
            "gl_status": ["Draft", "Posted", "Failed", "Cancelled", "Adjusted"],
            "hedge_type": ["FX_Forward", "FX_Swap", "FX_Option", "Interest_Rate_Swap", "Cross_Currency_Swap"],
            "accounting_method": ["COH", "FV_Hedge", "Net_Investment", "Economic"]
        }

        # Table-specific field mappings
        self.table_schemas = {
            "hedge_instructions": {
                "required": ["msg_uid", "instruction_type", "exposure_currency", "hedge_amount_order", "instruction_status"],
                "optional": ["check_status", "failure_reason", "nav_type", "hedge_type", "target_date", "created_by"],
                "auto_generate": ["msg_uid", "created_date", "created_by"],
                "excluded": ["entity_id"]  # This column doesn't exist in hedge_instructions table
            },
            "hedge_business_events": {
                "required": ["event_id", "instruction_id", "business_event_type", "event_status"],
                "optional": ["nav_type", "currency_type", "notional_amount", "stage_1a_status", "stage_2_status", "stage_3_status"],
                "auto_generate": ["event_id", "created_date", "created_by"]
            },
            "allocation_engine": {
                "required": ["allocation_id", "currency_code", "entity_id", "allocated_amount", "allocation_status"],
                "optional": ["allocation_type", "target_ratio", "current_utilization", "available_capacity"],
                "auto_generate": ["allocation_id", "created_date", "created_by"]
            },
            "deal_bookings": {
                "required": ["booking_id", "instruction_id", "currency_pair", "notional_amount", "booking_status"],
                "optional": ["murex_deal_id", "trade_date", "settlement_date", "fx_rate", "booking_system"],
                "auto_generate": ["booking_id", "created_date", "created_by"]
            },
            "hedge_gl_packages": {
                "required": ["package_id", "instruction_id", "package_status", "total_amount"],
                "optional": ["package_type", "accounting_method", "gl_date", "posting_reference"],
                "auto_generate": ["package_id", "created_date", "created_by"]
            },
            "hedge_gl_entries": {
                "required": ["entry_id", "package_id", "account_code", "debit_amount", "credit_amount"],
                "optional": ["entry_type", "description", "cost_center", "business_unit"],
                "auto_generate": ["entry_id", "created_date", "created_by"]
            }
        }

    def detect_write_intent(self, user_prompt: str) -> tuple[bool, str]:
        """
        Enhanced write intent detection for immediate vs read-first operations
        Returns: (should_write_immediately, intent_type)
        """
        prompt_lower = user_prompt.lower()

        # High-priority command verbs (immediate write)
        command_verbs = [
            "process", "run", "execute", "initiate", "book", "place", "submit",
            "create", "generate", "perform", "conduct", "start", "begin"
        ]

        # Command phrases (immediate write)
        command_phrases = [
            "place a hedge", "run feasibility", "process utilization", "execute hedge",
            "book a feasibility", "initiate hedge", "perform check", "conduct analysis",
            "run stage", "process stage", "execute stage"
        ]

        # Question indicators (read-first)
        question_indicators = [
            "would like to check", "can i", "could i", "is it possible", "what if",
            "how much", "tell me", "show me", "what would", "do i have"
        ]

        # Check for immediate write commands
        for verb in command_verbs:
            if prompt_lower.startswith(verb + " ") or f" {verb} " in prompt_lower:
                return True, "immediate_command"

        for phrase in command_phrases:
            if phrase in prompt_lower:
                return True, "immediate_command"

        # Check for question patterns (read-first)
        for indicator in question_indicators:
            if indicator in prompt_lower:
                return False, "inquiry"

        # Default: if contains write keywords but not questions, assume command
        write_keywords = ["save", "persist", "record", "write", "insert"]
        if any(keyword in prompt_lower for keyword in write_keywords):
            return True, "write_command"

        return False, "read_only"

    def generate_write_data(self,
                          user_prompt: str,
                          intent: str,
                          stage_mode: str = "auto",
                          operation_type: str = "write",
                          currency: Optional[str] = None,
                          entity_id: Optional[str] = None,
                          amount: Optional[float] = None,
                          instruction_id: Optional[str] = None,
                          context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Dynamically generate write data based on context and business rules
        """
        logger.info(f"Generating write data - Intent: {intent}, Stage: {stage_mode}, Operation: {operation_type}")

        # Determine target table and scenario
        target_scenario = self._determine_scenario(intent, stage_mode, operation_type, user_prompt)

        # Generate base write data
        write_data = self._generate_base_data(target_scenario, currency, entity_id, amount, instruction_id, context_data)

        # Apply business rules and validations
        write_data = self._apply_business_rules(write_data, target_scenario, user_prompt, context_data)

        # Auto-generate required fields
        write_data = self._auto_generate_fields(write_data, target_scenario)

        logger.info(f"Generated write data for {target_scenario['table']} with {len(write_data)} fields")
        return write_data

    def _determine_scenario(self, intent: str, stage_mode: str, operation_type: str, user_prompt: str) -> Dict[str, Any]:
        """Determine the target table and scenario based on context"""

        prompt_lower = user_prompt.lower()

        # Stage 1A scenarios (Feasibility/Utilization Checks Only)
        if (stage_mode == "1A" or
            any(keyword in prompt_lower for keyword in ["utilization", "capacity", "feasibility"])):

            # Stage 1A ONLY writes to hedge_instructions (feasibility check)
            # hedge_business_events will be handled separately if feasibility passes
            return {
                "table": "hedge_instructions",
                "scenario": "stage_1a_feasibility",
                "status_field": "instruction_status",
                "default_status": "Received"  # Start with Received, update to Executed after processing
            }

        # Stage 1B scenarios (Actual Allocation)
        elif (stage_mode == "1B" or
              any(keyword in prompt_lower for keyword in ["allocate", "allocation_execution"])):
            return {
                "table": "allocation_engine",
                "scenario": "allocation_execution",
                "status_field": "allocation_status",
                "default_status": "Active"
            }

        # Stage 2 scenarios (Booking/Murex)
        elif (stage_mode == "2" or operation_type == "mx_booking" or
              any(keyword in prompt_lower for keyword in ["booking", "deal", "murex", "trade"])):
            return {
                "table": "deal_bookings",
                "scenario": "stage_2_booking",
                "status_field": "booking_status",
                "default_status": "Booked"
            }

        # Stage 3 scenarios (GL Posting)
        elif (stage_mode == "3" or operation_type == "gl_posting" or
              any(keyword in prompt_lower for keyword in ["gl", "posting", "journal", "accounting"])):

            if "package" in prompt_lower:
                return {
                    "table": "hedge_gl_packages",
                    "scenario": "stage_3_package",
                    "status_field": "package_status",
                    "default_status": "Posted"
                }
            else:
                return {
                    "table": "hedge_gl_entries",
                    "scenario": "stage_3_entry",
                    "status_field": "entry_status",
                    "default_status": "Posted"
                }

        # Configuration scenarios
        elif any(keyword in prompt_lower for keyword in ["config", "setup", "entity", "threshold"]):
            if "entity" in prompt_lower:
                return {
                    "table": "entity_master",
                    "scenario": "entity_config",
                    "status_field": "entity_status",
                    "default_status": "Active"
                }
            else:
                return {
                    "table": "threshold_configuration",
                    "scenario": "threshold_config",
                    "status_field": "config_status",
                    "default_status": "Active"
                }

        # Default: Stage 1A hedge instruction
        return {
            "table": "hedge_instructions",
            "scenario": "default_hedge_instruction",
            "status_field": "instruction_status",
            "default_status": "Received"
        }

    def _generate_base_data(self, scenario: Dict[str, Any], currency: Optional[str],
                          entity_id: Optional[str], amount: Optional[float],
                          instruction_id: Optional[str], context_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate base data structure for the scenario"""

        table = scenario["table"]
        base_data = {"target_table": table}

        # Common fields across most tables
        if currency:
            if table == "hedge_instructions":
                base_data["exposure_currency"] = currency
            elif table in ["allocation_engine", "deal_bookings"]:
                base_data["currency_code"] = currency
            elif table == "hedge_business_events":
                base_data["currency_type"] = currency

        if entity_id and table not in ["hedge_instructions"]:  # hedge_instructions doesn't have entity_id column
            base_data["entity_id"] = entity_id

        if amount:
            amount_field = {
                "hedge_instructions": "hedge_amount_order",
                "allocation_engine": "allocated_amount",
                "deal_bookings": "notional_amount",
                "hedge_gl_packages": "total_amount",
                "hedge_business_events": "notional_amount"
            }.get(table, "amount")
            base_data[amount_field] = amount

        if instruction_id:
            base_data["instruction_id"] = instruction_id

        # Table-specific base fields
        if table == "hedge_instructions":
            base_data.update({
                "instruction_type": self._determine_instruction_type(scenario, context_data),
                "instruction_status": scenario["default_status"],
                "check_status": "Pass"  # Default to Pass for successful operations
            })

        elif table == "hedge_business_events":
            base_data.update({
                "business_event_type": "Utilization",  # Stage 1A creates Utilization events
                "event_status": scenario.get("default_status", "Pending"),
                "stage_1a_status": "Approved" if "feasibility" in scenario.get("scenario", "") else "Pending"
            })

        elif table == "allocation_engine":
            base_data.update({
                "allocation_status": scenario["default_status"],
                "allocation_type": "Auto"
            })

        elif table == "deal_bookings":
            base_data.update({
                "booking_status": scenario["default_status"],
                "booking_system": "MUREX"
            })

        elif table == "hedge_gl_packages":
            base_data.update({
                "package_status": scenario["default_status"],
                "accounting_method": "COH"
            })

        elif table == "hedge_gl_entries":
            base_data.update({
                "entry_type": "Hedge_Adjustment"
            })

        return base_data

    def _determine_instruction_type(self, scenario: Dict[str, Any], context_data: Optional[Dict[str, Any]]) -> str:
        """Determine instruction type based on scenario"""
        scenario_name = scenario.get("scenario", "")

        if "feasibility" in scenario_name or "utilization" in scenario_name:
            return "U"  # Utilization check
        elif "booking" in scenario_name:
            return "I"  # Instruction
        elif "reporting" in scenario_name:
            return "R"  # Report
        else:
            return "U"  # Default to Utilization

    def _apply_business_rules(self, write_data: Dict[str, Any], scenario: Dict[str, Any],
                            user_prompt: str, context_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply business rules and intelligent defaults"""

        table = scenario["table"]
        prompt_lower = user_prompt.lower()

        # Business rule: If prompt indicates failure/breach, set appropriate status and reason
        if any(keyword in prompt_lower for keyword in ["breach", "fail", "limit", "exceeded", "insufficient"]):
            if table == "hedge_instructions":
                write_data["check_status"] = "Fail"
                write_data["instruction_status"] = "Failed"

                # Extract failure reason from prompt
                if "limit" in prompt_lower and "breach" in prompt_lower:
                    write_data["failure_reason"] = "Limit breach detected"
                elif "insufficient" in prompt_lower:
                    write_data["failure_reason"] = "Insufficient capacity available"
                else:
                    write_data["failure_reason"] = "Validation failed"

        # Business rule: If prompt indicates success/completion, use positive status
        elif any(keyword in prompt_lower for keyword in ["success", "complete", "execute", "process"]):
            if table == "hedge_instructions":
                write_data["instruction_status"] = "Executed"
                write_data["check_status"] = "Pass"

        # Business rule: Set hedge type based on currency pattern
        if table in ["hedge_instructions", "deal_bookings"] and "exposure_currency" in write_data:
            currency = write_data.get("exposure_currency", write_data.get("currency_code", ""))
            if currency in ["USD", "EUR", "GBP", "JPY"]:
                write_data["hedge_type"] = "FX_Forward"
            else:
                write_data["hedge_type"] = "FX_Swap"

        # Business rule: Set target date for instructions
        if table == "hedge_instructions":
            target_date = datetime.now().strftime("%Y-%m-%d")
            write_data["target_date"] = target_date

        return write_data

    def _auto_generate_fields(self, write_data: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-generate required fields like IDs, timestamps"""

        table = scenario["table"]
        current_time = datetime.now()

        # Generate unique identifiers
        if table == "hedge_instructions" and "msg_uid" not in write_data:
            # Format: HAWK_1A_DDMMYY_EXEC_XXX
            date_str = current_time.strftime("%d%m%y")
            random_num = random.randint(1, 999)
            write_data["msg_uid"] = f"HAWK_1A_{date_str}_EXEC_{random_num:03d}"

        if table == "hedge_business_events" and "event_id" not in write_data:
            # Format: EVT_1A_DDMMYY_XXX
            date_str = current_time.strftime("%d%m%y")
            random_num = random.randint(1, 999)
            write_data["event_id"] = f"EVT_1A_{date_str}_{random_num:03d}"

        if table == "allocation_engine" and "allocation_id" not in write_data:
            write_data["allocation_id"] = str(uuid.uuid4())

        if table == "deal_bookings" and "booking_id" not in write_data:
            write_data["booking_id"] = str(uuid.uuid4())

        if table == "hedge_gl_packages" and "package_id" not in write_data:
            write_data["package_id"] = str(uuid.uuid4())

        if table == "hedge_gl_entries" and "entry_id" not in write_data:
            write_data["entry_id"] = str(uuid.uuid4())

        # Add metadata fields
        write_data["created_by"] = "HAWK_AGENT"
        write_data["created_date"] = current_time.isoformat()

        return write_data

    def validate_write_data(self, write_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate generated write data against schema constraints"""

        table = write_data.get("target_table")
        if not table:
            return False, ["Missing target_table"]

        errors = []
        schema = self.table_schemas.get(table, {})

        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in write_data:
                errors.append(f"Missing required field: {field}")

        # Validate enum values
        for field, value in write_data.items():
            if field in self.valid_values:
                valid_options = self.valid_values[field]
                if value not in valid_options:
                    errors.append(f"Invalid {field}: {value}. Valid options: {valid_options}")

        return len(errors) == 0, errors

    def generate_business_event_data(self,
                                   instruction_id: str,
                                   feasibility_result: str,
                                   currency: Optional[str] = None,
                                   entity_id: Optional[str] = None,
                                   nav_type: Optional[str] = None,
                                   amount: Optional[float] = None,
                                   context_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Generate hedge_business_events data when Stage 1A feasibility passes
        Only creates business events for Pass or Partial results, not Fail
        """
        logger.info(f"Generating business event data - Result: {feasibility_result}, Instruction: {instruction_id}")

        # Only create business events for successful feasibility checks
        if feasibility_result not in ["Pass", "Partial"]:
            logger.info(f"No business event created for feasibility result: {feasibility_result}")
            return None

        current_time = datetime.now()
        date_str = current_time.strftime("%d%m%y")
        random_num = random.randint(1, 999)

        # Generate business event data
        event_data = {
            "target_table": "hedge_business_events",
            "event_id": f"EVT_1A_{date_str}_{random_num:03d}",
            "instruction_id": instruction_id,
            "entity_id": entity_id or "SYSTEM",  # Required field, default to SYSTEM if not provided
            "business_event_type": "Utilization",
            "event_status": "Booked" if feasibility_result == "Pass" else "Pending",
            "stage_1a_status": "Completed" if feasibility_result == "Pass" else "Pending",
            "stage_2_status": "Pending",
            "stage_3_status": "Pending",
            "created_by": "HAWK_AGENT",
            "created_date": current_time.isoformat()
        }

        # Add optional fields if provided
        if currency:
            event_data["currency_type"] = currency
        if nav_type:
            event_data["nav_type"] = nav_type
        if amount:
            event_data["notional_amount"] = amount

        logger.info(f"Generated business event data: {event_data}")
        return event_data

# Global instance
dynamic_write_generator = DynamicWriteGenerator()