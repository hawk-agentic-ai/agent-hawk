from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime, date

# =============================================================================
# FLEXIBLE REQUEST MODELS - NO MANDATORY CONSTRAINTS
# =============================================================================

class FlexiblePromptRequest(BaseModel):
    """
    Universal prompt request model for ALL template types:
    - Hedge Instructions (I-U-R-T-A-Q)
    - Risk Analysis queries
    - Compliance reporting
    - Performance analytics
    - Monitoring & status
    - General hedge fund analysis
    """
    user_prompt: str = Field(..., description="Natural language prompt from user")
    template_category: Optional[str] = Field(None, description="Template family type (hedge_accounting, risk_management, compliance, etc.)")
    template_id: Optional[str] = Field(None, description="Specific template ID from database")
    
    # Optional context fields - extracted from prompt or template dynamically
    currency: Optional[str] = Field(None, description="Currency code if applicable")
    entity_id: Optional[str] = Field(None, description="Entity ID if applicable") 
    nav_type: Optional[str] = Field(None, description="NAV type (COI/RE/RE_Reserve) if applicable")
    time_period: Optional[str] = Field(None, description="Time period for analysis if applicable")
    portfolio: Optional[str] = Field(None, description="Portfolio identifier if applicable")
    amount: Optional[float] = Field(None, description="Amount/notional if applicable")
    
    # Instruction-specific fields (only when needed)
    instruction_type: Optional[str] = Field(None, description="Instruction type (I/U/R/T/A/Q) - inferred from prompt")
    order_id: Optional[str] = Field(None, description="Order ID - only for amendments/rollover/termination")
    previous_order_id: Optional[str] = Field(None, description="Previous order ID - only for amendments")
    reference_hedge_id: Optional[str] = Field(None, description="Reference hedge - only for rollover/termination")
    hedge_method: Optional[str] = Field(None, description="Hedge method (COH/MTM/etc) if applicable")
    
    # Client message correlation (used by some Dify apps)
    msg_uid: Optional[str] = Field(None, description="Client-side message UID for correlation/trace")
    
    # Template-specific dynamic fields
    extracted_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Fields extracted dynamically from template")
    
    # Processing options
    use_cache: Optional[bool] = Field(True, description="Whether to use Redis cache for data fetching")
    include_metadata: Optional[bool] = Field(True, description="Include extraction metadata in response")
    
    # NEW: Data freshness controls
    force_fresh: Optional[bool] = Field(False, description="Force fresh data fetch, bypass all caches")
    data_freshness_minutes: Optional[int] = Field(15, description="Cache TTL in minutes (2-60), default 15min")

    # Agent routing (for multi-agent selection in Agent Mode)
    agent_id: Optional[str] = Field(None, description="Optional agent identifier for routing (e.g., 'allocation', 'hawk')")
    # Optional direct Dify API key override (frontend-provided per app)
    agent_api_key: Optional[str] = Field(None, description="Override Dify API key for selected agent/app")
    
    @field_validator('currency')
    @classmethod
    def validate_currency_optional(cls, v):
        """Ensure currency is uppercase if provided."""
        return v.upper() if v else None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "user_prompt": "Check if I can hedge 150K CNY today",
                    "template_category": "hedge_accounting", 
                    "currency": "CNY",
                    "amount": 150000
                },
                {
                    "user_prompt": "Generate compliance report for Q1 2024",
                    "template_category": "compliance",
                    "time_period": "Q1-2024"
                },
                {
                    "user_prompt": "Analyze VAR for FUND001 portfolio",
                    "template_category": "risk_management",
                    "entity_id": "FUND001"
                }
            ]
        }

# =============================================================================
# LEGACY INSTRUCTION MODEL - FOR BACKWARD COMPATIBILITY ONLY
# =============================================================================

class HedgeInstructionPayload(BaseModel):
    """
    DEPRECATED: Legacy instruction model - use FlexiblePromptRequest instead
    Kept for backward compatibility with existing instruction-only endpoints
    """
    instruction_type: Optional[str] = Field(None, description="Instruction type: I, U, R, T, A, Q - now optional")
    
    order_id: Optional[str] = Field(None, description="Order ID - only required for specific instruction types")
    sub_order_id: Optional[str] = Field(None, description="Sub-order ID - optional")
    exposure_currency: Optional[str] = Field(None, description="Exposure currency - optional, can be inferred from prompt")
    hedge_amount_order: Optional[float] = Field(None, description="Amount to be hedged - optional")
    hedge_method: Optional[str] = Field(None, description="Hedge method - optional")

    nav_type: Optional[str] = Field(None, description="NAV type filter (COI/RE/RE_Reserve)")
    currency_type: Optional[str] = Field(None, description="Currency type filter")
    hedging_instrument_hint: Optional[str] = Field(None, description="Hint for the hedging instrument")
    
    reference_hedge_id: Optional[str] = Field(None, description="Hedge ID for rollover/termination")
    new_maturity_date: Optional[date] = Field(None, description="New maturity date for rollover")
    termination_date: Optional[date] = Field(None, description="Termination date")

    @field_validator('exposure_currency')
    @classmethod
    def validate_exposure_currency_optional(cls, v):
        """Ensure exposure currency is uppercase if provided."""
        return v.upper() if v else None

    @field_validator('hedge_amount_order')
    @classmethod
    def validate_hedge_amount_optional(cls, v):
        """Validate hedge amount if provided - no longer mandatory."""
        if v is not None:
            if v <= 0:
                raise ValueError('Hedge amount must be positive if provided')
            if v > 100000000000:
                raise ValueError('Hedge amount exceeds maximum limit')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "instruction_type": "I",
                "order_id": "ORD_001",
                "sub_order_id": "SUB_001",
                "exposure_currency": "HKD",
                "hedge_amount_order": 5000000.0,
                "hedge_method": "COH",
                "nav_type": "COI",
                "currency_type": "Matched",
                "hedging_instrument_hint": "FX Swap"
            }
        }

# --- Response Models (Updated for clarity and completeness) ---

class HedgingState(BaseModel):
    already_hedged_amount: float
    available_for_hedging: float
    calculated_available_amount: float
    hedge_utilization_pct: float
    hedging_status: Literal["Available", "Fully_Hedged", "Partially_Hedged", "Not_Available"]
    car_amount_distribution: float
    manual_overlay_amount: float
    buffer_amount: float
    buffer_percentage: float
    framework_type: str
    car_exemption_flag: str
    framework_compliance: str
    last_allocation_date: Optional[str]
    waterfall_priority: Optional[int]
    allocation_sequence: Optional[int]
    allocation_status: str
    active_hedge_count: int
    total_hedge_notional: float

class PositionInfo(BaseModel):
    nav_type: str
    current_position: float
    computed_total_nav: float
    optimal_car_amount: float
    buffer_percentage: float
    buffer_amount: float
    manual_overlay: float
    allocation_status: str
    hedging_state: HedgingState
    allocation_data: List[Dict[str, Any]]
    hedge_relationships: List[Dict[str, Any]]
    framework_rule: Dict[str, Any]
    buffer_rule: Dict[str, Any]
    car_data: Dict[str, Any]

class EntityGroup(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str
    exposure_currency: str
    currency_type: Optional[str]
    car_exemption: str
    parent_child_nav_link: bool
    positions: List[PositionInfo]

class Stage1AConfig(BaseModel):
    buffer_configuration: List[Dict[str, Any]]
    waterfall_logic: Dict[str, List[Dict[str, Any]]]
    overlay_configuration: List[Dict[str, Any]]
    hedging_framework: List[Dict[str, Any]]
    system_configuration: List[Dict[str, Any]]
    threshold_configuration: Dict[str, Any]

class Stage1BData(BaseModel):
    current_allocations: List[Dict[str, Any]]
    hedge_instructions_history: List[Dict[str, Any]]
    active_hedge_events: List[Dict[str, Any]]
    car_master_data: List[Dict[str, Any]]

class Stage2Config(BaseModel):
    booking_model_config: List[Dict[str, Any]]
    murex_books: List[Dict[str, Any]]
    hedge_instruments: List[Dict[str, Any]]
    hedge_effectiveness: List[Dict[str, Any]]

class StageValidation(BaseModel):
    entity_check: Optional[bool] = None
    buffer_config_check: Optional[bool] = None
    waterfall_config_check: Optional[bool] = None
    hedging_framework_check: Optional[bool] = None
    usd_pb_check: Optional[bool] = None
    system_config_check: Optional[bool] = None
    allocation_data_check: Optional[bool] = None
    hedge_history_check: Optional[bool] = None
    car_data_check: Optional[bool] = None
    active_events_check: Optional[bool] = None
    booking_model_check: Optional[bool] = None
    murex_books_check: Optional[bool] = None
    hedge_instruments_check: Optional[bool] = None
    hedge_effectiveness_check: Optional[bool] = None

class ComprehensiveValidationResults(BaseModel):
    stage_1a: StageValidation
    stage_1b: StageValidation
    stage_2: StageValidation
    warnings: List[str]
    errors: List[str]

class DataCompleteness(BaseModel):
    stage_1a_completeness: float
    stage_1b_completeness: float
    stage_2_completeness: float
    overall_completeness: float
    total_entities: int
    currency_data_complete: bool
    rates_data_complete: bool

class CompleteHedgeData(BaseModel):
    entity_groups: List[EntityGroup]
    stage_1a_config: Stage1AConfig
    stage_1b_data: Stage1BData
    stage_2_config: Stage2Config
    risk_monitoring: List[Dict[str, Any]]
    currency_configuration: List[Dict[str, Any]]
    currency_rates: List[Dict[str, Any]]
    proxy_configuration: List[Dict[str, Any]]
    additional_rates: List[Dict[str, Any]]

class ComprehensiveHedgeInceptionResponse(BaseModel):
    status: Literal["success", "error"]
    complete_data: CompleteHedgeData
    payload: Dict[str, Any]
    validation_results: ComprehensiveValidationResults
    data_completeness: DataCompleteness
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

# Legacy models for backward compatibility
class EntityPositionInfo(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str
    exposure_currency: str
    currency_type: Optional[str]
    car_exemption: str
    parent_child_nav_link: bool
    positions: list

class USDPBCheck(BaseModel):
    total_usd_equivalent: float
    threshold: float
    status: Literal["PASS", "FAIL"]
    excess_amount: float

class ValidationResults(BaseModel):
    entity_check: bool
    currency_config_check: bool
    usd_pb_check: bool
    booking_model_check: bool
    murex_books_check: bool
    warnings: List[str]
    errors: List[str]

class HedgeInceptionResponse(BaseModel):
    status: Literal["success", "error"]
    hedgeinfo: dict
    payload: dict
    validation_results: Optional[ValidationResults] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
