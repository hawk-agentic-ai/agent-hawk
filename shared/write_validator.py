"""
STRICT Write Validation System - Phase 1
Ensures data integrity and prevents database corruption by validating all write operations
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    ERROR = "error"      # Blocks write operation
    WARNING = "warning"  # Logs but allows write
    INFO = "info"        # Informational only

@dataclass
class ValidationResult:
    """Result of a validation check"""
    field: str
    severity: ValidationSeverity
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    suggestion: Optional[str] = None

@dataclass
class WriteValidationReport:
    """Complete validation report for a write operation"""
    table_name: str
    operation: str  # INSERT, UPDATE, DELETE
    is_valid: bool
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    info: List[ValidationResult]
    validation_time_ms: float

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

class StrictWriteValidator:
    """
    Validates all database write operations to prevent data corruption
    Implements safe/slow approach for hedge fund data integrity
    """

    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client
        self.validation_rules = self._load_validation_rules()
        self.schema_cache = {}

    def _load_validation_rules(self) -> Dict[str, Dict]:
        """Load table-specific validation rules"""
        return {
            "hedge_instructions": {
                "required_fields": [
                    "instruction_id", "instruction_type", "exposure_currency",
                    "hedge_amount_order", "instruction_status", "created_by", "created_date"
                ],
                "field_types": {
                    "instruction_id": str,
                    "instruction_type": str,
                    "exposure_currency": str,
                    "hedge_amount_order": (int, float),
                    "instruction_status": str,
                    "created_by": str,
                    "created_date": str
                },
                "enum_values": {
                    "instruction_type": ["I", "U", "R", "T", "A", "Q"],
                    "instruction_status": ["Received", "Validated", "Processing", "Completed", "Failed", "Cancelled", "Executed"],
                    "exposure_currency": ["USD", "EUR", "GBP", "JPY", "HKD", "SGD", "CAD", "AUD", "CNY", "KRW"]
                },
                "field_constraints": {
                    "instruction_id": {"max_length": 50, "pattern": r"^INST_[A-Z0-9_]+$"},
                    "hedge_amount_order": {"min_value": 0.01, "max_value": 1000000000}
                }
            },
            "allocation_engine": {
                "required_fields": [
                    "allocation_id", "entity_id", "currency_code",
                    "allocation_status", "created_by", "created_date"
                ],
                "field_types": {
                    "allocation_id": str,
                    "entity_id": str,
                    "currency_code": str,
                    "hedge_amount_allocation": (int, float, type(None)),
                    "allocation_status": str,
                    "created_by": str,
                    "created_date": str
                },
                "enum_values": {
                    "allocation_status": ["Calculated", "Pending", "Allocated", "Confirmed", "Failed"],
                    "currency_code": ["USD", "EUR", "GBP", "JPY", "HKD", "SGD", "CAD", "AUD", "CNY", "KRW"]
                },
                "field_constraints": {
                    "allocation_id": {"max_length": 50, "pattern": r"^ALLOC_[A-Z0-9_]+$"},
                    "hedge_amount_allocation": {"min_value": 0, "max_value": 1000000000}
                }
            },
            "hedge_business_events": {
                "required_fields": [
                    "event_id", "instruction_id", "entity_id", "business_event_type",
                    "event_status", "created_by", "created_date"
                ],
                "field_types": {
                    "event_id": str,
                    "instruction_id": str,
                    "entity_id": str,
                    "business_event_type": str,
                    "event_status": str,
                    "notional_amount": (int, float, type(None)),
                    "created_by": str,
                    "created_date": str
                },
                "enum_values": {
                    "business_event_type": ["Initiation", "Rollover", "Termination", "Amendment"],
                    "event_status": ["Pending", "Processing", "Completed", "Failed", "Cancelled"]
                },
                "field_constraints": {
                    "event_id": {"max_length": 50, "pattern": r"^EVENT_[A-Z0-9_]+$"}
                }
            },
            "deal_bookings": {
                "required_fields": [
                    "booking_id", "instruction_id", "currency",
                    "booking_status", "created_by", "created_date"
                ],
                "field_types": {
                    "booking_id": str,
                    "instruction_id": str,
                    "currency": str,
                    "notional_amount": (int, float, type(None)),
                    "booking_status": str,
                    "created_by": str,
                    "created_date": str
                },
                "enum_values": {
                    "booking_status": ["Pending", "Booked", "Settled", "Failed", "Cancelled"],
                    "currency": ["USD", "EUR", "GBP", "JPY", "HKD", "SGD", "CAD", "AUD", "CNY", "KRW"]
                },
                "field_constraints": {
                    "booking_id": {"max_length": 50, "pattern": r"^BOOKING_[A-Z0-9_]+$"}
                }
            },
            "hedge_gl_packages": {
                "required_fields": [
                    "package_id", "instruction_id", "package_status",
                    "created_by", "created_date"
                ],
                "field_types": {
                    "package_id": str,
                    "instruction_id": str,
                    "package_status": str,
                    "gl_date": str,
                    "total_debit_amount": (int, float, type(None)),
                    "total_credit_amount": (int, float, type(None)),
                    "created_by": str,
                    "created_date": str
                },
                "enum_values": {
                    "package_status": ["DRAFT", "PENDING", "POSTED", "CANCELLED"]
                },
                "field_constraints": {
                    "package_id": {"max_length": 50, "pattern": r"^PKG_[A-Z0-9_]+$"}
                },
                "gl_period_check": True  # Requires GL period validation
            },
            "hedge_gl_entries": {
                "required_fields": [
                    "entry_id", "package_id", "account_code",
                    "created_by", "created_date"
                ],
                "field_types": {
                    "entry_id": str,
                    "package_id": str,
                    "account_code": str,
                    "debit_amount": (int, float, type(None)),
                    "credit_amount": (int, float, type(None)),
                    "gl_date": str,
                    "created_by": str,
                    "created_date": str
                },
                "field_constraints": {
                    "entry_id": {"max_length": 50, "pattern": r"^ENTRY_[A-Z0-9_]+$"},
                    "account_code": {"max_length": 20}
                },
                "gl_period_check": True  # Requires GL period validation
            },
            "gl_entries": {
                "required_fields": [
                    "entry_id", "account_code", "gl_date",
                    "created_by", "created_date"
                ],
                "field_types": {
                    "entry_id": str,
                    "account_code": str,
                    "gl_date": str,
                    "debit_amount": (int, float, type(None)),
                    "credit_amount": (int, float, type(None)),
                    "created_by": str,
                    "created_date": str
                },
                "field_constraints": {
                    "account_code": {"max_length": 20}
                },
                "gl_period_check": True  # Requires GL period validation
            }
        }

    async def validate_write_operation(self,
                                     table_name: str,
                                     operation: str,
                                     data: Dict[str, Any],
                                     filters: Optional[Dict[str, Any]] = None) -> WriteValidationReport:
        """
        Main validation method - validates a complete write operation
        """
        start_time = datetime.now()

        errors = []
        warnings = []
        info = []

        logger.info(f"Validating {operation} operation on {table_name}")

        try:
            # Phase 1 Validations
            errors.extend(await self._validate_table_exists(table_name))
            errors.extend(await self._validate_required_fields(table_name, data))
            errors.extend(await self._validate_field_types(table_name, data))
            errors.extend(await self._validate_enum_values(table_name, data))
            errors.extend(await self._validate_field_constraints(table_name, data))

            # Operation-specific validations
            if operation == "UPDATE" and not filters:
                errors.append(ValidationResult(
                    field="filters",
                    severity=ValidationSeverity.ERROR,
                    message="UPDATE operations require WHERE filters to prevent accidental bulk updates",
                    suggestion="Add specific filters to target only intended records"
                ))

            if operation == "DELETE" and not filters:
                errors.append(ValidationResult(
                    field="filters",
                    severity=ValidationSeverity.ERROR,
                    message="DELETE operations require WHERE filters to prevent accidental bulk deletes",
                    suggestion="Add specific filters to target only intended records"
                ))

            # Foreign key validations (if Supabase client available)
            if self.supabase_client:
                fk_errors = await self._validate_foreign_keys(table_name, data)
                errors.extend(fk_errors)
            else:
                warnings.append(ValidationResult(
                    field="foreign_keys",
                    severity=ValidationSeverity.WARNING,
                    message="Foreign key validation skipped - Supabase client not available"
                ))

            # Audit trail validation
            audit_warnings = self._validate_audit_fields(data)
            warnings.extend(audit_warnings)

            # GL Period validation (if required for this table)
            if self.supabase_client:
                gl_period_errors = await self._validate_gl_period(table_name, data)
                errors.extend(gl_period_errors)
            else:
                # If no client but GL period check required, add warning
                rules = self.validation_rules.get(table_name, {})
                if rules.get("gl_period_check", False):
                    warnings.append(ValidationResult(
                        field="gl_period",
                        severity=ValidationSeverity.WARNING,
                        message="GL period validation skipped - Supabase client not available"
                    ))

        except Exception as e:
            logger.error(f"Validation error: {e}")
            errors.append(ValidationResult(
                field="validation_system",
                severity=ValidationSeverity.ERROR,
                message=f"Validation system error: {str(e)}",
                suggestion="Check validation system configuration"
            ))

        # Calculate validation time
        end_time = datetime.now()
        validation_time_ms = (end_time - start_time).total_seconds() * 1000

        # Create report
        is_valid = len(errors) == 0

        report = WriteValidationReport(
            table_name=table_name,
            operation=operation,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info,
            validation_time_ms=validation_time_ms
        )

        # Log results
        if is_valid:
            logger.info(f"SUCCESS: Validation PASSED for {operation} on {table_name} ({validation_time_ms:.1f}ms)")
        else:
            logger.error(f"ERROR: Validation FAILED for {operation} on {table_name} - {len(errors)} errors")

        return report

    async def _validate_table_exists(self, table_name: str) -> List[ValidationResult]:
        """Validate that the target table exists in the database"""
        errors = []

        if not self.supabase_client:
            return errors  # Skip if no client available

        try:
            # Try a simple query to check if table exists
            result = self.supabase_client.table(table_name).select("*").limit(0).execute()
            logger.debug(f"Table {table_name} exists")
        except Exception as e:
            error_msg = str(e).lower()
            if "does not exist" in error_msg or "relation" in error_msg:
                errors.append(ValidationResult(
                    field="table_name",
                    severity=ValidationSeverity.ERROR,
                    message=f"Table '{table_name}' does not exist in database",
                    actual_value=table_name,
                    suggestion="Verify table name spelling or check database schema"
                ))
            else:
                logger.warning(f"Table existence check failed with unexpected error: {e}")

        return errors

    async def _validate_required_fields(self, table_name: str, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate that all required fields are present"""
        errors = []

        rules = self.validation_rules.get(table_name, {})
        required_fields = rules.get("required_fields", [])

        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                errors.append(ValidationResult(
                    field=field,
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field '{field}' is missing or empty",
                    expected_value="non-empty value",
                    actual_value=data.get(field),
                    suggestion=f"Provide a valid value for {field}"
                ))

        return errors

    async def _validate_field_types(self, table_name: str, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate field data types"""
        errors = []

        rules = self.validation_rules.get(table_name, {})
        field_types = rules.get("field_types", {})

        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                value = data[field]

                # Handle union types (e.g., (int, float))
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        errors.append(ValidationResult(
                            field=field,
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{field}' has invalid type",
                            expected_value=f"one of {[t.__name__ for t in expected_type]}",
                            actual_value=f"{type(value).__name__}: {value}",
                            suggestion=f"Convert {field} to one of the expected types"
                        ))
                else:
                    if not isinstance(value, expected_type):
                        errors.append(ValidationResult(
                            field=field,
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{field}' has invalid type",
                            expected_value=expected_type.__name__,
                            actual_value=f"{type(value).__name__}: {value}",
                            suggestion=f"Convert {field} to {expected_type.__name__}"
                        ))

        return errors

    async def _validate_enum_values(self, table_name: str, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate enum/choice field values"""
        errors = []

        rules = self.validation_rules.get(table_name, {})
        enum_values = rules.get("enum_values", {})

        for field, allowed_values in enum_values.items():
            if field in data and data[field] is not None:
                value = data[field]
                if value not in allowed_values:
                    errors.append(ValidationResult(
                        field=field,
                        severity=ValidationSeverity.ERROR,
                        message=f"Field '{field}' has invalid value",
                        expected_value=f"one of {allowed_values}",
                        actual_value=value,
                        suggestion=f"Use one of the allowed values: {', '.join(allowed_values)}"
                    ))

        return errors

    async def _validate_field_constraints(self, table_name: str, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate field-specific constraints (length, range, pattern)"""
        errors = []

        rules = self.validation_rules.get(table_name, {})
        constraints = rules.get("field_constraints", {})

        for field, field_constraints in constraints.items():
            if field in data and data[field] is not None:
                value = data[field]

                # String length validation
                if "max_length" in field_constraints and isinstance(value, str):
                    if len(value) > field_constraints["max_length"]:
                        errors.append(ValidationResult(
                            field=field,
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{field}' exceeds maximum length",
                            expected_value=f"<= {field_constraints['max_length']} characters",
                            actual_value=f"{len(value)} characters",
                            suggestion=f"Shorten {field} to {field_constraints['max_length']} characters or less"
                        ))

                # Numeric range validation
                if "min_value" in field_constraints and isinstance(value, (int, float)):
                    if value < field_constraints["min_value"]:
                        errors.append(ValidationResult(
                            field=field,
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{field}' below minimum value",
                            expected_value=f">= {field_constraints['min_value']}",
                            actual_value=value,
                            suggestion=f"Set {field} to {field_constraints['min_value']} or higher"
                        ))

                if "max_value" in field_constraints and isinstance(value, (int, float)):
                    if value > field_constraints["max_value"]:
                        errors.append(ValidationResult(
                            field=field,
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{field}' exceeds maximum value",
                            expected_value=f"<= {field_constraints['max_value']}",
                            actual_value=value,
                            suggestion=f"Set {field} to {field_constraints['max_value']} or lower"
                        ))

                # Pattern validation
                if "pattern" in field_constraints and isinstance(value, str):
                    import re
                    pattern = field_constraints["pattern"]
                    if not re.match(pattern, value):
                        errors.append(ValidationResult(
                            field=field,
                            severity=ValidationSeverity.ERROR,
                            message=f"Field '{field}' does not match required pattern",
                            expected_value=f"pattern: {pattern}",
                            actual_value=value,
                            suggestion=f"Format {field} according to the pattern requirements"
                        ))

        return errors

    async def _validate_foreign_keys(self, table_name: str, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate foreign key references exist"""
        errors = []

        # Define foreign key relationships
        fk_relationships = {
            "hedge_instructions": {},  # No FK validations for now
            "allocation_engine": {
                "entity_id": ("entity_master", "entity_id")
            },
            "hedge_business_events": {
                "instruction_id": ("hedge_instructions", "instruction_id"),
                "entity_id": ("entity_master", "entity_id")
            },
            "deal_bookings": {
                "instruction_id": ("hedge_instructions", "instruction_id")
            }
        }

        table_fks = fk_relationships.get(table_name, {})

        for fk_field, (ref_table, ref_field) in table_fks.items():
            if fk_field in data and data[fk_field] is not None:
                fk_value = data[fk_field]

                try:
                    # Check if referenced record exists
                    result = self.supabase_client.table(ref_table)\
                        .select(ref_field)\
                        .eq(ref_field, fk_value)\
                        .limit(1)\
                        .execute()

                    if not result.data or len(result.data) == 0:
                        errors.append(ValidationResult(
                            field=fk_field,
                            severity=ValidationSeverity.ERROR,
                            message=f"Foreign key violation: {fk_field}='{fk_value}' does not exist in {ref_table}",
                            actual_value=fk_value,
                            suggestion=f"Ensure {fk_value} exists in {ref_table}.{ref_field} before referencing it"
                        ))

                except Exception as e:
                    logger.warning(f"FK validation failed for {fk_field}: {e}")
                    # Don't add error - might be schema issue

        return errors

    def _validate_audit_fields(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate audit trail fields are properly populated"""
        warnings = []

        # Check for audit fields
        audit_fields = ["created_by", "created_date", "modified_by", "modified_date"]

        if "created_by" not in data:
            warnings.append(ValidationResult(
                field="created_by",
                severity=ValidationSeverity.WARNING,
                message="Audit field 'created_by' is missing",
                suggestion="Add created_by field for audit trail compliance"
            ))

        if "created_date" not in data:
            warnings.append(ValidationResult(
                field="created_date",
                severity=ValidationSeverity.WARNING,
                message="Audit field 'created_date' is missing",
                suggestion="Add created_date field for audit trail compliance"
            ))

        return warnings

    async def _validate_gl_period(self, table_name: str, data: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate GL period is open for posting
        Critical for regulatory compliance - prevents posting to closed periods
        """
        errors = []

        # Check if this table requires GL period validation
        rules = self.validation_rules.get(table_name, {})
        if not rules.get("gl_period_check", False):
            return errors  # No GL period check required for this table

        # Get gl_date from data
        gl_date = data.get("gl_date")
        if not gl_date:
            errors.append(ValidationResult(
                field="gl_date",
                severity=ValidationSeverity.ERROR,
                message="GL date is required for GL posting operations",
                suggestion="Provide a valid gl_date field"
            ))
            return errors

        try:
            # Parse gl_date
            from datetime import datetime
            if isinstance(gl_date, str):
                try:
                    gl_date_parsed = datetime.fromisoformat(gl_date.replace('Z', '+00:00')).date()
                except ValueError:
                    # Try simple date format
                    gl_date_parsed = datetime.strptime(gl_date, '%Y-%m-%d').date()
            else:
                gl_date_parsed = gl_date

            # Query gl_periods table to check if period is open
            result = self.supabase_client.table("gl_periods")\
                .select("period_id, period_name, period_start, period_end, is_open, period_status")\
                .lte("period_start", gl_date_parsed.isoformat())\
                .gte("period_end", gl_date_parsed.isoformat())\
                .limit(1)\
                .execute()

            if not result.data or len(result.data) == 0:
                errors.append(ValidationResult(
                    field="gl_date",
                    severity=ValidationSeverity.ERROR,
                    message=f"No GL period found for date {gl_date_parsed}",
                    actual_value=gl_date,
                    suggestion="Ensure GL periods are configured and gl_date falls within a valid period"
                ))
                return errors

            period = result.data[0]

            # Check if period is open
            if not period.get("is_open", False):
                errors.append(ValidationResult(
                    field="gl_date",
                    severity=ValidationSeverity.ERROR,
                    message=f"GL period '{period.get('period_name')}' is CLOSED for posting",
                    actual_value=f"Period status: {period.get('period_status', 'CLOSED')}",
                    expected_value="is_open = TRUE",
                    suggestion=f"Use a gl_date that falls within an open period, or contact finance to reopen period {period.get('period_name')}"
                ))
                logger.warning(f"❌ GL period validation failed: Period {period.get('period_name')} is closed for {gl_date_parsed}")

            # Check period status
            period_status = period.get("period_status", "").upper()
            if period_status not in ["OPEN", "CURRENT"]:
                errors.append(ValidationResult(
                    field="gl_date",
                    severity=ValidationSeverity.ERROR,
                    message=f"GL period status is '{period_status}' - posting not allowed",
                    actual_value=period_status,
                    expected_value="OPEN or CURRENT",
                    suggestion=f"Period {period.get('period_name')} must be in OPEN or CURRENT status for posting"
                ))

            # Success - log for audit
            if not errors:
                logger.info(f"✅ GL period validation passed: {period.get('period_name')} is open for {gl_date_parsed}")

        except Exception as e:
            logger.warning(f"GL period validation check failed: {e}")
            # If gl_periods table doesn't exist, treat as warning not error
            if "does not exist" in str(e).lower() or "relation" in str(e).lower():
                errors.append(ValidationResult(
                    field="gl_period",
                    severity=ValidationSeverity.ERROR,
                    message="GL periods table not found - period control not configured",
                    suggestion="Create gl_periods table and configure period controls for compliance"
                ))
            else:
                # Other errors - log but don't block
                logger.error(f"Unexpected error during GL period validation: {e}")

        return errors

    def format_validation_report(self, report: WriteValidationReport) -> str:
        """Format validation report for logging/display"""
        lines = [
            f"VALIDATION REPORT: {report.operation} on {report.table_name}",
            f"Status: {'VALID' if report.is_valid else 'INVALID'}",
            f"Validation Time: {report.validation_time_ms:.1f}ms",
            f"Errors: {report.error_count}, Warnings: {report.warning_count}",
            ""
        ]

        if report.errors:
            lines.append("ERRORS (Write Blocked):")
            for error in report.errors:
                lines.append(f"  - {error.field}: {error.message}")
                if error.suggestion:
                    lines.append(f"    Suggestion: {error.suggestion}")
            lines.append("")

        if report.warnings:
            lines.append("WARNINGS:")
            for warning in report.warnings:
                lines.append(f"  - {warning.field}: {warning.message}")
            lines.append("")

        return "\n".join(lines)

# Global instance
write_validator = StrictWriteValidator()

async def validate_write(table_name: str, operation: str, data: Dict[str, Any],
                        supabase_client=None, filters: Optional[Dict[str, Any]] = None) -> WriteValidationReport:
    """Global function to validate write operations"""
    if supabase_client:
        write_validator.supabase_client = supabase_client

    return await write_validator.validate_write_operation(table_name, operation, data, filters)