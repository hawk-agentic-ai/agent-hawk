"""
Payloads Module - Request/Response Models for Hawk Agent API
Defines Pydantic models for API communication
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class InstructionType(str, Enum):
    """Hedge fund operation types (I-U-R-T-A-Q)"""
    INCEPTION = "inception"
    UTILIZATION = "utilization"
    ROLLOVER = "rollover"
    TERMINATION = "termination"
    AMENDMENT = "amendment"
    QUERY = "query"


class ProcessingStage(str, Enum):
    """Processing stages for hedge fund operations"""
    STAGE_1A = "stage_1a"
    STAGE_1B = "stage_1b"
    STAGE_2 = "stage_2"


class FlexiblePromptRequest(BaseModel):
    """Flexible request model for HAWK agent operations"""
    instruction_type: Optional[InstructionType] = Field(
        default=None,
        description="Type of hedge fund operation to perform"
    )
    user_prompt: str = Field(
        ...,
        description="User's natural language prompt"
    )
    stage: ProcessingStage = Field(
        default=ProcessingStage.STAGE_1A,
        description="Processing stage for the operation"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context information"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier for tracking"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for tracking"
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response"
    )

    # Frontend compatibility fields
    template_category: Optional[str] = Field(
        default=None,
        description="Template category from frontend"
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="HAWK agent identifier"
    )
    agent_api_key: Optional[str] = Field(
        default=None,
        description="Dify agent API key"
    )
    instruction_id: Optional[str] = Field(
        default=None,
        description="Instruction ID for tracking"
    )
    use_cache: Optional[bool] = Field(
        default=True,
        description="Whether to use caching"
    )
    force_fresh: Optional[bool] = Field(
        default=False,
        description="Force fresh data fetch"
    )

    # Additional dynamic fields for data extraction
    currency: Optional[str] = None
    entity_id: Optional[str] = None
    nav_type: Optional[str] = None
    amount: Optional[float] = None
    time_period: Optional[str] = None
    portfolio: Optional[str] = None


class HedgeInstructionPayload(BaseModel):
    """Legacy hedge instruction payload for backward compatibility"""
    instruction_type: str = Field(..., description="Instruction type")
    user_prompt: str = Field(..., description="User prompt")
    stage: str = Field(default="stage_1a", description="Processing stage")

    # Optional fields for enhanced processing
    fund_id: Optional[str] = None
    position_id: Optional[str] = None
    amount: Optional[float] = None
    symbol: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessingResponse(BaseModel):
    """Standard response model for processing operations"""
    success: bool = Field(..., description="Operation success status")
    operation_id: Optional[str] = Field(None, description="Unique operation identifier")
    result: Optional[Dict[str, Any]] = Field(None, description="Operation result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    cached: bool = Field(default=False, description="Whether result was cached")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="Service version")
    services: Dict[str, str] = Field(..., description="Dependent services status")
    uptime: Optional[int] = Field(None, description="Service uptime in seconds")
    timestamp: str = Field(..., description="Response timestamp")


class StreamingChunk(BaseModel):
    """Individual chunk in a streaming response"""
    type: str = Field(..., description="Chunk type (data, metadata, error, complete)")
    content: str = Field(..., description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    timestamp: str = Field(..., description="Error timestamp")


# MCP (Model Context Protocol) specific payloads
class MCPRequest(BaseModel):
    """MCP JSON-RPC 2.0 request format"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: str = Field(..., description="Request identifier")
    method: str = Field(..., description="Method to call")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")


class MCPResponse(BaseModel):
    """MCP JSON-RPC 2.0 response format"""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: str = Field(..., description="Request identifier")
    result: Optional[Dict[str, Any]] = Field(None, description="Success result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error object")


class MCPToolCall(BaseModel):
    """MCP tool call request"""
    name: str = Field(..., description="Tool name to call")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")


class MCPToolResponse(BaseModel):
    """MCP tool call response"""
    content: List[Dict[str, Any]] = Field(..., description="Response content")
    isError: bool = Field(default=False, description="Whether response is an error")


# Allocation-specific payloads
class AllocationRequest(BaseModel):
    """Fund allocation request"""
    fund_id: str = Field(..., description="Fund identifier")
    allocation_type: str = Field(..., description="Type of allocation")
    amount: float = Field(..., description="Allocation amount")
    symbol: Optional[str] = Field(None, description="Symbol for position allocation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional allocation data")


class CapacityCheckRequest(BaseModel):
    """Fund capacity check request"""
    fund_id: Optional[str] = Field(None, description="Specific fund ID to check")
    required_capacity: Optional[float] = Field(None, description="Required capacity amount")


class CapacityCheckResponse(BaseModel):
    """Fund capacity check response"""
    total_capacity: float = Field(..., description="Total fund capacity")
    utilized_capacity: float = Field(..., description="Currently utilized capacity")
    available_capacity: float = Field(..., description="Available capacity")
    utilization_rate: float = Field(..., description="Utilization rate (0-1)")
    can_allocate: bool = Field(..., description="Whether requested allocation is possible")


# Analytics and reporting payloads
class AnalyticsRequest(BaseModel):
    """Analytics data request"""
    fund_id: Optional[str] = Field(None, description="Fund ID for analytics")
    date_from: Optional[str] = Field(None, description="Start date for analytics")
    date_to: Optional[str] = Field(None, description="End date for analytics")
    metrics: Optional[List[str]] = Field(None, description="Specific metrics to retrieve")


class PerformanceMetrics(BaseModel):
    """Performance metrics response"""
    total_return: float = Field(..., description="Total return percentage")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    volatility: Optional[float] = Field(None, description="Volatility percentage")
    alpha: Optional[float] = Field(None, description="Alpha value")
    beta: Optional[float] = Field(None, description="Beta value")


# Configuration and system payloads
class SystemConfig(BaseModel):
    """System configuration settings"""
    cache_enabled: bool = Field(default=True, description="Whether caching is enabled")
    max_cache_size: int = Field(default=1000, description="Maximum cache entries")
    default_timeout: int = Field(default=30, description="Default request timeout")
    streaming_enabled: bool = Field(default=True, description="Whether streaming is enabled")


class ValidationError(BaseModel):
    """Input validation error details"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value")


class BatchRequest(BaseModel):
    """Batch processing request"""
    operations: List[FlexiblePromptRequest] = Field(..., description="List of operations to process")
    parallel: bool = Field(default=False, description="Whether to process in parallel")
    stop_on_error: bool = Field(default=True, description="Whether to stop batch on first error")


class BatchResponse(BaseModel):
    """Batch processing response"""
    success: bool = Field(..., description="Overall batch success")
    results: List[ProcessingResponse] = Field(..., description="Individual operation results")
    total_operations: int = Field(..., description="Total number of operations")
    successful_operations: int = Field(..., description="Number of successful operations")
    failed_operations: int = Field(..., description="Number of failed operations")
    execution_time: float = Field(..., description="Total batch execution time")