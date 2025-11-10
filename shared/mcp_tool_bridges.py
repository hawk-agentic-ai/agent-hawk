"""
MCP Tool Bridges - Maps agent-expected tools to backend functions
Enables Dify agents to work with existing backend architecture
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from .dynamic_write_generator import dynamic_write_generator

logger = logging.getLogger(__name__)

class MCPToolBridge:
    """
    Bridges agent-expected MCP tools to actual backend implementations
    """

    def __init__(self, hedge_processor=None):
        self.hedge_processor = hedge_processor
        self.tool_mappings = {
            # Allocation Agent Tools
            "allocation_stage1a_processor": self._allocation_stage1a_processor,
            "allocation_utilization_checker": self._allocation_utilization_checker,

            # Booking Agent Tools
            "hedge_booking_processor": self._hedge_booking_processor,
            "gl_posting_processor": self._gl_posting_processor,
            "murex_integration_processor": self._murex_integration_processor,

            # Analytics Agent Tools
            "analytics_processor": self._analytics_processor,
            "performance_analyzer": self._performance_analyzer,
            "risk_calculator": self._risk_calculator,

            # Config Agent Tools
            "config_crud_processor": self._config_crud_processor,
            "entity_manager": self._entity_manager,
            "threshold_manager": self._threshold_manager
        }

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by routing to the appropriate backend function"""

        if tool_name not in self.tool_mappings:
            return {
                "status": "error",
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self.tool_mappings.keys())
            }

        try:
            logger.info(f"Executing bridge tool: {tool_name}")
            return await self.tool_mappings[tool_name](arguments)

        except Exception as e:
            logger.error(f"Tool bridge error for {tool_name}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "tool": tool_name
            }

    # =============================================================================
    # ALLOCATION AGENT BRIDGES
    # =============================================================================

    async def _allocation_stage1a_processor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Allocation Agent -> Stage 1A Processing
        Maps to universal_prompt_processor with stage_mode="1A"
        """
        logger.info("Bridge: allocation_stage1a_processor -> universal_prompt_processor")

        # Extract allocation-specific arguments
        user_prompt = arguments.get("user_prompt", arguments.get("prompt", ""))
        currency = arguments.get("currency")
        entity_id = arguments.get("entity_id")
        nav_type = arguments.get("nav_type")
        amount = arguments.get("amount")
        write_data = arguments.get("write_data")

        # Enhanced write intent detection - check for immediate commands vs questions
        original_prompt = arguments.get("user_prompt", arguments.get("prompt", ""))
        should_write_immediately, intent_type = dynamic_write_generator.detect_write_intent(original_prompt)

        logger.info(f"Write intent detection: {intent_type} -> should_write_immediately={should_write_immediately}")

        # For command language, force immediate write operation
        if should_write_immediately:
            logger.info("Detected command language - proceeding with immediate write operation")
            operation_type = "write"
        else:
            logger.info("Detected inquiry language - performing read-first analysis")
            operation_type = "read"

        # Ensure we're in allocation/utilization context (preserve original write keywords)
        if not user_prompt or ("allocation" not in user_prompt.lower() and "utilization" not in user_prompt.lower()):
            if should_write_immediately:
                user_prompt = f"Process and record allocation and utilization for {amount} {currency} entity {entity_id}"
            else:
                user_prompt = f"Check allocation and utilization for {amount} {currency} entity {entity_id}"
        elif should_write_immediately and "process" not in user_prompt.lower():
            # Preserve original prompt but ensure it has write language
            user_prompt = f"Process {user_prompt}"

        # Force currency filtering by enhancing prompt
        if currency and currency not in user_prompt:
            user_prompt = f"{user_prompt} for {currency} currency only"

        # Auto-create write_data using dynamic generator when write intent detected
        if should_write_immediately and not write_data:
            write_data = dynamic_write_generator.generate_write_data(
                user_prompt=user_prompt,
                intent="hedge_utilization",
                stage_mode="1A",
                operation_type="write",
                currency=currency,
                entity_id=entity_id,
                amount=amount,
                context_data={"bridge": "allocation_stage1a_processor"}
            )
            logger.info(f"Dynamic generator created write_data for Stage 1A: {write_data}")

            # Validate the generated data
            is_valid, errors = dynamic_write_generator.validate_write_data(write_data)
            if not is_valid:
                logger.warning(f"Generated write_data validation errors: {errors}")
                # Fall back to basic structure if validation fails
                from datetime import datetime
                import random
                current_time = datetime.now()
                date_str = current_time.strftime("%d%m%y")
                random_num = random.randint(1, 999)
                fallback_msg_uid = f"HAWK_1A_{date_str}_EXEC_{random_num:03d}"

                write_data = {
                    "target_table": "hedge_instructions",
                    "instruction_type": "U",
                    "exposure_currency": currency or "USD",
                    "hedge_amount_order": amount or 0,
                    "instruction_status": "Received",
                    "msg_uid": fallback_msg_uid
                }

        # Call universal processor with Stage 1A focus
        result = await self.hedge_processor.universal_prompt_processor(
            user_prompt=user_prompt,
            template_category="hedge_accounting",
            currency=currency,
            entity_id=entity_id,
            nav_type=nav_type,
            amount=float(amount) if amount else None,
            use_cache=True,
            operation_type=operation_type,  # Use the dynamically determined operation type
            write_data=write_data,
            stage_mode="1A",  # Force Stage 1A processing
            agent_role="allocation",
            output_format="json"
        )

        # Add allocation-specific metadata
        result["stage_info"] = {
            "stage": "1A",
            "purpose": "Capacity Assessment & Utilization Validation",
            "agent": "allocation"
        }

        return result

    async def _allocation_utilization_checker(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Allocation utilization checker -> Data extraction focused on utilization
        """
        logger.info("Bridge: allocation_utilization_checker -> data extraction")

        user_prompt = f"Check utilization capacity for {arguments.get('amount', '')} {arguments.get('currency', '')} entity {arguments.get('entity_id', '')}"

        result = await self.hedge_processor.universal_prompt_processor(
            user_prompt=user_prompt,
            template_category="hedge_accounting",
            currency=arguments.get("currency"),
            entity_id=arguments.get("entity_id"),
            nav_type=arguments.get("nav_type"),
            amount=float(arguments.get("amount")) if arguments.get("amount") else None,
            use_cache=True,
            operation_type="read",
            stage_mode="1A",
            agent_role="allocation",
            output_format="json"
        )

        # Focus response on utilization data
        if "extracted_data" in result:
            utilization_data = {}
            for table in ["allocation_engine", "position_nav_master", "buffer_configuration"]:
                if table in result["extracted_data"]:
                    utilization_data[table] = result["extracted_data"][table]

            result["utilization_analysis"] = utilization_data

        return result

    # =============================================================================
    # BOOKING AGENT BRIDGES
    # =============================================================================

    async def _hedge_booking_processor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Booking Agent -> Stage 2 Processing (Deal Booking)
        Maps to universal_prompt_processor with stage_mode="2"
        """
        logger.info("Bridge: hedge_booking_processor -> universal_prompt_processor")

        user_prompt = arguments.get("user_prompt", arguments.get("prompt", ""))
        instruction_id = arguments.get("instruction_id")

        # Ensure we're in booking context
        if not user_prompt or "booking" not in user_prompt.lower():
            user_prompt = f"Execute booking for hedge instruction {instruction_id}"

        # Auto-generate booking write_data if needed
        write_data = arguments.get("write_data")
        if not write_data and arguments.get("execute_booking", True):
            write_data = dynamic_write_generator.generate_write_data(
                user_prompt=user_prompt,
                intent="hedge_booking",
                stage_mode="2",
                operation_type="mx_booking",
                currency=arguments.get("currency"),
                entity_id=arguments.get("entity_id"),
                amount=arguments.get("amount"),
                instruction_id=instruction_id,
                context_data={"bridge": "hedge_booking_processor"}
            )
            logger.info(f"Dynamic generator created booking write_data: {write_data}")

        result = await self.hedge_processor.universal_prompt_processor(
            user_prompt=user_prompt,
            template_category="hedge_accounting",
            currency=arguments.get("currency"),
            entity_id=arguments.get("entity_id"),
            nav_type=arguments.get("nav_type"),
            amount=float(arguments.get("amount")) if arguments.get("amount") else None,
            use_cache=True,
            operation_type="mx_booking",  # Trigger MX booking operations
            write_data=write_data,
            instruction_id=instruction_id,
            execute_booking=arguments.get("execute_booking", True),
            stage_mode="2",  # Force Stage 2 processing
            agent_role="booking",
            output_format="json"
        )

        # Add booking-specific metadata
        result["stage_info"] = {
            "stage": "2",
            "purpose": "Deal Booking & Murex Integration",
            "agent": "booking"
        }

        return result

    async def _gl_posting_processor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: GL Posting -> Stage 3 Processing (GL Journal Creation)
        Maps to universal_prompt_processor with stage_mode="3"
        """
        logger.info("Bridge: gl_posting_processor -> universal_prompt_processor")

        user_prompt = arguments.get("user_prompt", arguments.get("prompt", ""))
        instruction_id = arguments.get("instruction_id")

        # Ensure we're in GL posting context
        if not user_prompt or "gl" not in user_prompt.lower():
            user_prompt = f"Create GL postings for hedge instruction {instruction_id}"

        # Auto-generate GL posting write_data if needed
        write_data = arguments.get("write_data")
        if not write_data and arguments.get("execute_posting", True):
            write_data = dynamic_write_generator.generate_write_data(
                user_prompt=user_prompt,
                intent="gl_posting",
                stage_mode="3",
                operation_type="gl_posting",
                currency=arguments.get("currency"),
                entity_id=arguments.get("entity_id"),
                amount=arguments.get("amount"),
                instruction_id=instruction_id,
                context_data={"bridge": "gl_posting_processor"}
            )
            logger.info(f"Dynamic generator created GL posting write_data: {write_data}")

        result = await self.hedge_processor.universal_prompt_processor(
            user_prompt=user_prompt,
            template_category="hedge_accounting",
            currency=arguments.get("currency"),
            entity_id=arguments.get("entity_id"),
            nav_type=arguments.get("nav_type"),
            amount=float(arguments.get("amount")) if arguments.get("amount") else None,
            use_cache=True,
            operation_type="gl_posting",  # Trigger GL posting operations
            write_data=write_data,
            instruction_id=instruction_id,
            execute_posting=arguments.get("execute_posting", True),
            stage_mode="3",  # Force Stage 3 processing
            agent_role="booking",
            output_format="json"
        )

        # Add GL posting-specific metadata
        result["stage_info"] = {
            "stage": "3",
            "purpose": "GL Journal Creation & Posting",
            "agent": "booking"
        }

        return result

    async def _murex_integration_processor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Murex integration -> External system integration
        """
        logger.info("Bridge: murex_integration_processor -> external system integration")

        # This would integrate with actual Murex systems
        # For now, simulate Murex integration

        instruction_id = arguments.get("instruction_id")
        deal_data = arguments.get("deal_data", {})

        result = {
            "status": "success",
            "murex_integration": {
                "instruction_id": instruction_id,
                "murex_deal_id": f"MRX_BRIDGE_{int(datetime.now().timestamp())}",
                "integration_status": "completed",
                "deal_reference": deal_data.get("deal_reference"),
                "booking_timestamp": datetime.now().isoformat()
            },
            "stage_info": {
                "stage": "2",
                "purpose": "Murex System Integration",
                "agent": "booking"
            }
        }

        return result

    # =============================================================================
    # ANALYTICS AGENT BRIDGES
    # =============================================================================

    async def _analytics_processor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Analytics Agent -> Analytics-focused processing
        Maps to universal_prompt_processor with analytics context
        """
        logger.info("Bridge: analytics_processor -> universal_prompt_processor")

        user_prompt = arguments.get("user_prompt", arguments.get("prompt", ""))

        # Ensure analytics context
        if not any(word in user_prompt.lower() for word in ["analyze", "report", "performance", "risk"]):
            user_prompt = f"Analyze hedge fund performance and risk metrics: {user_prompt}"

        result = await self.hedge_processor.universal_prompt_processor(
            user_prompt=user_prompt,
            template_category="performance",
            currency=arguments.get("currency"),
            entity_id=arguments.get("entity_id"),
            nav_type=arguments.get("nav_type"),
            use_cache=True,
            operation_type="read",
            stage_mode="auto",
            agent_role="analytics",
            output_format="json"
        )

        # Add analytics-specific processing
        if "extracted_data" in result:
            analytics_data = {}
            for table in ["hedge_effectiveness", "performance_data", "risk_monitoring", "currency_rates"]:
                if table in result["extracted_data"]:
                    analytics_data[table] = result["extracted_data"][table]

            result["analytics_data"] = analytics_data

        result["agent_info"] = {
            "agent": "analytics",
            "purpose": "Performance Analysis & Risk Reporting"
        }

        return result

    async def _performance_analyzer(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Performance analysis -> Performance metrics calculation
        """
        logger.info("Bridge: performance_analyzer -> performance calculation")

        # Extract performance analysis parameters
        time_period = arguments.get("time_period", "current")
        entity_id = arguments.get("entity_id")

        user_prompt = f"Analyze hedge effectiveness and performance for {entity_id} over {time_period}"

        result = await self.hedge_processor.universal_prompt_processor(
            user_prompt=user_prompt,
            template_category="performance",
            entity_id=entity_id,
            use_cache=True,
            operation_type="read",
            stage_mode="auto",
            agent_role="analytics",
            output_format="json"
        )

        # Add performance calculations (simplified)
        if "extracted_data" in result:
            performance_metrics = {
                "hedge_effectiveness_ratio": "80-125%",
                "period": time_period,
                "entity": entity_id,
                "status": "compliant"
            }
            result["performance_metrics"] = performance_metrics

        return result

    async def _risk_calculator(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Risk calculation -> Risk metrics and VaR calculation
        """
        logger.info("Bridge: risk_calculator -> risk metrics")

        confidence_level = arguments.get("confidence_level", "95%")
        currency = arguments.get("currency", "USD")

        user_prompt = f"Calculate VaR and risk metrics at {confidence_level} confidence level for {currency}"

        result = await self.hedge_processor.universal_prompt_processor(
            user_prompt=user_prompt,
            template_category="risk_management",
            currency=currency,
            use_cache=True,
            operation_type="read",
            stage_mode="auto",
            agent_role="analytics",
            output_format="json"
        )

        # Add risk calculations (simplified)
        risk_metrics = {
            "var_95": "1.2M USD",
            "confidence_level": confidence_level,
            "currency": currency,
            "calculation_date": datetime.now().isoformat()
        }
        result["risk_metrics"] = risk_metrics

        return result

    # =============================================================================
    # CONFIG AGENT BRIDGES
    # =============================================================================

    async def _config_crud_processor(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Config Agent -> Direct database CRUD operations
        Maps to query_supabase_direct for configuration management
        """
        logger.info("Bridge: config_crud_processor -> query_supabase_direct")

        table_name = arguments.get("table_name")
        operation = arguments.get("operation", "select").lower()
        data = arguments.get("data")
        filters = arguments.get("filters")

        if not table_name:
            return {
                "status": "error",
                "error": "table_name is required for config operations"
            }

        # Use direct database access for config operations
        result = await self.hedge_processor.query_supabase_direct(
            table_name=table_name,
            filters=filters,
            limit=arguments.get("limit"),
            order_by=arguments.get("order_by"),
            use_cache=arguments.get("use_cache", True),
            operation=operation,
            data=data
        )

        # Add config-specific metadata
        result["agent_info"] = {
            "agent": "config",
            "purpose": "Configuration Management & CRUD Operations",
            "table": table_name,
            "operation": operation
        }

        return result

    async def _entity_manager(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Entity management -> entity_master table operations
        """
        logger.info("Bridge: entity_manager -> entity_master operations")

        operation = arguments.get("operation", "select").lower()
        entity_data = arguments.get("entity_data", arguments.get("data"))
        entity_id = arguments.get("entity_id")

        filters = {"entity_id": entity_id} if entity_id else arguments.get("filters")

        result = await self.hedge_processor.query_supabase_direct(
            table_name="entity_master",
            filters=filters,
            operation=operation,
            data=entity_data,
            use_cache=True
        )

        result["entity_management"] = {
            "operation": operation,
            "entity_id": entity_id,
            "agent": "config"
        }

        return result

    async def _threshold_manager(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge: Threshold management -> threshold_configuration table operations
        """
        logger.info("Bridge: threshold_manager -> threshold_configuration operations")

        operation = arguments.get("operation", "select").lower()
        threshold_data = arguments.get("threshold_data", arguments.get("data"))
        entity_id = arguments.get("entity_id")

        filters = {"entity_id": entity_id} if entity_id else arguments.get("filters")

        result = await self.hedge_processor.query_supabase_direct(
            table_name="threshold_configuration",
            filters=filters,
            operation=operation,
            data=threshold_data,
            use_cache=True
        )

        result["threshold_management"] = {
            "operation": operation,
            "entity_id": entity_id,
            "agent": "config"
        }

        return result

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def get_available_tools(self) -> List[str]:
        """Get list of all available bridged tools"""
        return list(self.tool_mappings.keys())

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool"""

        tool_info = {
            # Allocation Agent Tools
            "allocation_stage1a_processor": {
                "agent": "allocation",
                "stage": "1A",
                "purpose": "Capacity assessment and utilization validation",
                "parameters": ["user_prompt", "currency", "entity_id", "nav_type", "amount", "write_data"]
            },
            "allocation_utilization_checker": {
                "agent": "allocation",
                "stage": "1A",
                "purpose": "Check available hedging capacity",
                "parameters": ["currency", "entity_id", "nav_type", "amount"]
            },

            # Booking Agent Tools
            "hedge_booking_processor": {
                "agent": "booking",
                "stage": "2",
                "purpose": "Execute deal booking in Murex",
                "parameters": ["user_prompt", "instruction_id", "currency", "amount", "execute_booking", "write_data"]
            },
            "gl_posting_processor": {
                "agent": "booking",
                "stage": "3",
                "purpose": "Create and post GL journal entries",
                "parameters": ["user_prompt", "instruction_id", "currency", "amount", "execute_posting", "write_data"]
            },

            # Analytics Agent Tools
            "analytics_processor": {
                "agent": "analytics",
                "stage": "reporting",
                "purpose": "Generate performance and risk analytics",
                "parameters": ["user_prompt", "currency", "entity_id", "time_period"]
            },

            # Config Agent Tools
            "config_crud_processor": {
                "agent": "config",
                "stage": "management",
                "purpose": "CRUD operations on configuration tables",
                "parameters": ["table_name", "operation", "data", "filters", "limit"]
            }
        }

        return tool_info.get(tool_name, {"error": "Tool not found"})

# Global bridge instance
mcp_bridge: Optional[MCPToolBridge] = None

def initialize_mcp_bridge(hedge_processor):
    """Initialize global MCP tool bridge"""
    global mcp_bridge
    mcp_bridge = MCPToolBridge(hedge_processor)
    logger.info("MCP Tool Bridge initialized")

def get_mcp_bridge() -> Optional[MCPToolBridge]:
    """Get global MCP tool bridge instance"""
    return mcp_bridge