"""
Unified Hedge Fund Processor - Core business logic for both FastAPI and MCP server
Combines PromptIntelligenceEngine and SmartDataExtractor with universal processing logic
Extracted from unified_smart_backend.py for shared use
"""

import asyncio
import json
import os
import logging
import time
import hashlib
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

from .business_logic import PromptIntelligenceEngine, PromptAnalysisResult, PromptIntent, analyze_prompt
from .data_extractor import SmartDataExtractor
from .supabase_client import DatabaseManager
from .cache_manager import get_cache_duration, OPTIMIZATION_STATS
from .transaction_manager import DatabaseTransactionManager, WriteOperation, atomic_hedge_inception, atomic_booking_and_gl
from .mcp_tool_bridges import initialize_mcp_bridge, get_mcp_bridge
from .cache_invalidation import initialize_cache_invalidation

logger = logging.getLogger(__name__)


class HedgeFundProcessor:
    """Unified processor for hedge fund operations - shared between FastAPI and MCP"""
    
    def __init__(self):
        self.db_manager = None
        self.supabase_client = None
        self.redis_client = None
        self.prompt_engine = None
        self.data_extractor = None
        self.table_hints = None
        self.transaction_manager = None
        self.write_validator = None

        # Performance tracking
        self.total_requests = 0
        self.total_processing_time = 0
    
    async def initialize(self):
        """Initialize all components for shared use"""
        try:
            # Initialize database connections
            self.db_manager = DatabaseManager()
            self.supabase_client, self.redis_client = await self.db_manager.initialize_connections()
            
            # Initialize intelligent modules
            self.prompt_engine = PromptIntelligenceEngine()
            self.data_extractor = SmartDataExtractor(self.supabase_client, self.redis_client)

            # Initialize write validator and transaction manager
            try:
                from .write_validator import StrictWriteValidator
                self.write_validator = StrictWriteValidator(self.supabase_client)
                logger.info("Write validator initialized")
            except ImportError as e:
                logger.warning(f"Write validator not available: {e}")
                self.write_validator = None

            self.transaction_manager = DatabaseTransactionManager(
                self.supabase_client,
                self.write_validator
            )
            logger.info("Transaction manager initialized")

            # Initialize cache invalidation manager
            initialize_cache_invalidation(self.redis_client)
            logger.info("Cache invalidation manager initialized")

            # Initialize MCP tool bridge
            initialize_mcp_bridge(self)
            logger.info("MCP tool bridge initialized")

            # Load optional table hints (non-blocking guardrails)
            try:
                hints_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'table_hints.json')
                if os.path.exists(hints_path):
                    with open(hints_path, 'r', encoding='utf-8') as f:
                        self.table_hints = json.load(f)
                    logger.info("Table hints loaded for guardrails")
                else:
                    self.table_hints = None
            except Exception as e:
                logger.warning(f"Failed to load table hints: {e}")
                self.table_hints = None
            
            logger.info("HedgeFundProcessor initialized successfully")
            logger.info(f"Components: Supabase={'connected' if self.supabase_client else 'disconnected'}, Redis={'connected' if self.redis_client else 'disconnected'}")
            
        except Exception as e:
            logger.error(f"HedgeFundProcessor initialization error: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup database connections"""
        if self.db_manager:
            await self.db_manager.cleanup_connections()
            logger.info("HedgeFundProcessor cleanup complete")
    
    async def universal_prompt_processor(self,
                                       user_prompt: str,
                                       template_category: Optional[str] = None,
                                       currency: Optional[str] = None,
                                       entity_id: Optional[str] = None,
                                       nav_type: Optional[str] = None,
                                       amount: Optional[float] = None,
                                       use_cache: bool = True,
                                       operation_type: str = "read",
                                       write_data: Optional[Dict[str, Any]] = None,
                                       instruction_id: Optional[str] = None,
                                       execute_booking: bool = False,
                                       execute_posting: bool = False,
                                       stage_mode: str = "auto",
                                       agent_role: str = "unified",
                                       output_format: str = "json") -> Dict[str, Any]:
        """
        Universal prompt processor - core business logic shared between FastAPI and MCP
        Returns structured data instead of streaming responses for MCP compatibility
        """
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Step 0: Parse and normalize write_data (Dify often sends JSON strings or nested {data:{...}})
            if write_data and isinstance(write_data, str):
                try:
                    write_data = json.loads(write_data)
                    logger.info(f"Parsed write_data from JSON string: {type(write_data)}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse write_data JSON: {e}")
                    write_data = None
            # Flatten nested payloads
            if write_data and isinstance(write_data, dict) and isinstance(write_data.get("data"), dict):
                try:
                    inner = write_data.get("data")
                    wd = inner.copy()
                    for k, v in write_data.items():
                        if k != "data":
                            wd[k] = v
                    write_data = wd
                    logger.info("Normalized nested write_data.data into flat write_data")
                except Exception as e:
                    logger.warning(f"Failed to normalize nested write_data: {e}")

            # Step 1: Analyze the user prompt
            logger.info(f"Processing prompt: {user_prompt[:100]}...")
            logger.info(f"Operation type: {operation_type}, Stage mode: {stage_mode}, Agent role: {agent_role}")

            analysis_result = analyze_prompt(user_prompt, template_category)

            # Auto-detect stage if not specified
            if stage_mode == "auto":
                if any(word in user_prompt.lower() for word in ["utilization", "capacity", "feasibility", "allocation"]):
                    detected_stage = "1A"
                elif any(word in user_prompt.lower() for word in ["booking", "deal", "murex"]):
                    detected_stage = "2"
                elif any(word in user_prompt.lower() for word in ["gl", "posting", "journal"]):
                    detected_stage = "3"
                else:
                    detected_stage = "auto"
                logger.info(f"Auto-detected stage: {detected_stage}")
            else:
                detected_stage = stage_mode
            
            # Step 2: Extract required data
            logger.info(f"Intent: {analysis_result.intent.value}, Confidence: {analysis_result.confidence}")

            # Pass currency parameters to data extraction for filtering
            extracted_data = await self.data_extractor.extract_data_for_prompt(
                analysis_result,
                use_cache=use_cache,
                currency=currency,
                entity_id=entity_id,
                nav_type=nav_type,
                amount=amount
            )

            # Step 2.5: Do NOT auto-promote reads to writes. Only write when explicitly requested

            # Step 2.6: AI-driven parameter decisions for write operations
            ai_decisions = {}
            if operation_type == "write":
                from .context_analyzer import context_analyzer
                from .ai_decision_engine import ai_decision_engine

                # Create context from prompt analysis
                hedge_context = await context_analyzer.create_hedge_context(
                    user_prompt, currency, amount
                )

                # Initialize AI engine with database connection
                ai_decision_engine.supabase_client = self.supabase_client

                # Get all AI decisions
                ai_decisions = await ai_decision_engine.make_all_decisions(hedge_context)
                logger.info(f"AI decisions completed with {len(ai_decisions)} intelligent parameters")

            # Step 3: Execute write operations if requested
            write_results = {}
            if operation_type != "read":
                write_results = await self.execute_write_operations(
                    operation_type, user_prompt, analysis_result, extracted_data,
                    currency=currency, entity_id=entity_id, nav_type=nav_type, amount=amount,
                    write_data=write_data, instruction_id=instruction_id,
                    execute_booking=execute_booking, execute_posting=execute_posting,
                    ai_decisions=ai_decisions,  # Pass AI decisions to write operations
                    detected_stage=detected_stage,  # Pass detected stage to write operations
                    agent_role=agent_role  # Pass agent role for RBAC
                )
            
            # Step 4: Build optimized context
            optimized_context = self.build_optimized_context(
                analysis_result, extracted_data, user_prompt,
                currency=currency, entity_id=entity_id, nav_type=nav_type, amount=amount,
                write_results=write_results, ai_decisions=ai_decisions
            )
            
            # Step 5: Prepare structured response
            processing_time = time.time() - start_time
            self.total_processing_time += processing_time
            
            # Prepare AI decision transparency for response
            ai_decision_summary = {}
            if ai_decisions:
                ai_decision_summary = {
                    "total_decisions": len(ai_decisions),
                    "decision_details": {
                        key: {
                            "value": decision.value,
                            "confidence": decision.confidence,
                            "reasoning": decision.reasoning[:200] + "..." if len(decision.reasoning) > 200 else decision.reasoning,
                            "category": getattr(decision, 'category', 'parameter_selection')
                        }
                        for key, decision in ai_decisions.items()
                    },
                    "context_analysis": {
                        "geographic_indicators": getattr(hedge_context, 'geographic_indicators', []) if 'hedge_context' in locals() else [],
                        "urgency_level": getattr(hedge_context, 'urgency_level', 'standard') if 'hedge_context' in locals() else 'standard',
                        "operation_type": getattr(hedge_context, 'operation_type', 'inception') if 'hedge_context' in locals() else 'inception',
                        "risk_profile": getattr(hedge_context, 'risk_profile', 'medium') if 'hedge_context' in locals() else 'medium'
                    }
                }

            # Determine top-level status (bubble write status for clarity)
            top_status = "success"
            if operation_type != "read" and isinstance(write_results, dict):
                top_status = write_results.get("status", "success")

            response = {
                "status": top_status,
                "prompt_analysis": {
                    "intent": analysis_result.intent.value,
                    "confidence": analysis_result.confidence,
                    "instruction_type": analysis_result.instruction_type,
                    "data_scope": analysis_result.data_scope,
                    "parameters": analysis_result.extracted_params
                },
                "extracted_data": extracted_data,
                "write_results": write_results if operation_type != "read" else None,
                "ai_decisions": ai_decision_summary if ai_decisions else None,  # AI Decision Transparency
                "optimized_context": optimized_context,
                "processing_metadata": {
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                    "cache_stats": self.data_extractor.get_cache_stats() if self.data_extractor else {},
                    "request_id": f"req_{self.total_requests}_{int(time.time())}",
                    "ai_enhanced": bool(ai_decisions),  # Flag indicating AI-driven processing
                    "stage_mode": stage_mode,
                    "detected_stage": detected_stage,
                    "agent_role": agent_role,
                    "output_format": output_format
                }
            }

            # Generate agent report if requested
            if output_format == "agent_report" and agent_role in ["allocation", "booking"]:
                try:
                    from shared.agent_report_generator import agent_report_generator
                    agent_report_generator.supabase_client = self.supabase_client

                    # Get instruction_id from write results if available
                    instruction_id = None
                    if write_results and "details" in write_results:
                        hedge_instructions = write_results["details"].get("hedge_instructions")
                        if hedge_instructions:
                            instruction_id = hedge_instructions.get("instruction_id")

                    # Generate agent-specific report
                    agent_result = await agent_report_generator.generate_report(
                        agent_type=agent_role,
                        processing_result=response,
                        instruction_id=instruction_id,
                        include_verification=True
                    )

                    # Add agent report to response
                    response["agent_report"] = agent_result.get("report", agent_result.get("formatted_report", ""))
                    response["agent_report_status"] = agent_result.get("status", "unknown")

                except Exception as e:
                    logger.error(f"Agent report generation error: {e}")
                    response["agent_report_error"] = str(e)

            # Apply intelligent response formatting
            response = self._apply_intelligent_formatting(response, user_prompt, template_category)

            logger.info(f"Processing completed in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Universal processor error: {e}")
            
            return {
                "status": "error",
                "error": str(e),
                "processing_metadata": {
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_{self.total_requests}_{int(time.time())}"
                }
            }
    
    def build_optimized_context(self,
                              analysis_result: PromptAnalysisResult,
                              extracted_data: Dict[str, Any],
                              user_prompt: str,
                              currency: Optional[str] = None,
                              entity_id: Optional[str] = None,
                              nav_type: Optional[str] = None,
                              amount: Optional[float] = None,
                              write_results: Optional[Dict[str, Any]] = None,
                              ai_decisions: Optional[Dict[str, Any]] = None) -> str:
        """
        Build optimized context for AI analysis - preserving exact logic from unified_smart_backend.py
        """
        try:
            # Build context sections
            context_sections = []
            
            # 1. User Intent Section
            context_sections.append(f"""
# USER REQUEST ANALYSIS
Intent: {analysis_result.intent.value}
Confidence: {analysis_result.confidence}%
Instruction Type: {analysis_result.instruction_type or 'General'}
Parameters: {json.dumps(analysis_result.extracted_params, indent=2)}
""")
            
            # 2. Data Summary Section
            total_records = sum(len(v) if isinstance(v, list) else 0 for k, v in extracted_data.items() if not k.startswith("_"))
            tables_included = [k for k in extracted_data.keys() if not k.startswith("_") and isinstance(extracted_data[k], list)]
            
            context_sections.append(f"""
# DATA SUMMARY
Tables Included: {', '.join(tables_included)}
Total Records: {total_records}
Cache Performance: {extracted_data.get('_extraction_metadata', {}).get('cache_hit_rate', 'N/A')}
""")
            
            # 3. Key Data Sections
            for table_name in tables_included[:5]:  # Limit to top 5 tables
                table_data = extracted_data.get(table_name, [])
                if table_data and len(table_data) > 0:
                    context_sections.append(f"""
# {table_name.upper().replace('_', ' ')} DATA
Records: {len(table_data)}
Sample: {json.dumps(table_data[:2], indent=2, default=str)}
""")
            
            # 4. Special Processing Results
            if "_processed_entity_groups" in extracted_data:
                entity_groups = extracted_data["_processed_entity_groups"]
                context_sections.append(f"""
# HEDGE INSTRUCTION ANALYSIS
Entity Groups Processed: {len(entity_groups)}
Processing Applied: {extracted_data.get('_processing_applied', 'N/A')}
""")
            
            # 5. AI Decision Results (if any)
            if ai_decisions:
                decision_summary = []
                for key, decision in ai_decisions.items():
                    decision_summary.append(f"- {key}: {decision.value} (confidence: {decision.confidence}%)")
                    if hasattr(decision, 'reasoning') and decision.reasoning:
                        decision_summary.append(f"  Reasoning: {decision.reasoning[:150]}...")

                context_sections.append(f"""
# AI DECISION ENGINE RESULTS
Total AI Decisions: {len(ai_decisions)}
Parameter Selections:
{chr(10).join(decision_summary)}
AI-Enhanced Processing: Enabled
""")

            # 6. Write Results (if any)
            if write_results:
                context_sections.append(f"""
# WRITE OPERATION RESULTS
Operation Type: {write_results.get('operation_type', 'N/A')}
Status: {write_results.get('status', 'N/A')}
Records Affected: {write_results.get('records_affected', 0)}
Details: {json.dumps(write_results.get('details', {}), indent=2, default=str)}
""")
            
            # 7. Context Footer
            context_sections.append(f"""
# PROCESSING CONTEXT
Original Prompt: "{user_prompt}"
Processing Timestamp: {datetime.now().isoformat()}
System: Hedge Agent v5.0.0 - MCP Compatible
""")
            
            return "\n".join(context_sections)
            
        except Exception as e:
            logger.error(f"Context building error: {e}")
            return f"""
# ERROR IN CONTEXT BUILDING
Error: {str(e)}
Original Prompt: "{user_prompt}"
Available Data Tables: {list(extracted_data.keys()) if extracted_data else 'None'}
"""
    
    async def query_supabase_direct(self,
                                  table_name: str,
                                  filters: Optional[Dict[str, Any]] = None,
                                  limit: Optional[int] = None,
                                  order_by: Optional[str] = None,
                                  use_cache: bool = True,
                                  operation: str = "select",
                                  data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Direct Supabase CRUD operations for MCP tools with full table access"""
        try:
            if not self.supabase_client:
                return {"status": "error", "error": "Supabase not connected"}

            # Validate table access for all critical hedge fund tables
            critical_tables = [
                # Stage 1A - Allocation Agent (Full CRUD)
                "hedge_instructions", "allocation_engine", "hedge_business_events",
                "entity_master", "position_nav_master", "buffer_configuration",
                "threshold_configuration", "currency_rates", "hedging_framework",

                # Stage 2 & Stage 3 - Booking Agent (Full CRUD)
                "deal_bookings", "h_stg_mrx_ext", "hedge_gl_packages",
                "hedge_gl_entries", "murex_book_config", "hedge_be_config",

                # Additional Configuration Tables (Usually Read-Only)
                "currency_configuration", "v_event_expected_deals", "v_event_acked_deals"
            ]

            logger.info(f"Executing {operation} on {table_name} with filters: {filters}")

            # Guardrails (non-blocking): produce validation warnings from table hints
            validation_warnings = []
            try:
                if self.table_hints and isinstance(self.table_hints, dict):
                    hints = self.table_hints.get(table_name)
                    if hints:
                        # Required fields for insert
                        if operation == "insert" and isinstance(data, dict):
                            req = hints.get("required_fields", [])
                            missing = [k for k in req if k not in data]
                            if missing:
                                validation_warnings.append(
                                    f"Insert on {table_name} missing required fields: {', '.join(missing)}"
                                )
                            # Status allowed check
                            status_field = hints.get("status_field")
                            allowed = hints.get("allowed_status") or []
                            if status_field and status_field in data and allowed:
                                if data[status_field] not in allowed:
                                    validation_warnings.append(
                                        f"{status_field}='{data[status_field]}' not in allowed values {allowed}"
                                    )
                        # Update should have filters and respect allowed status if provided
                        if operation == "update":
                            if not filters:
                                validation_warnings.append(
                                    f"Update on {table_name} without filters may affect multiple rows"
                                )
                            status_field = hints.get("status_field")
                            allowed = hints.get("allowed_status") or []
                            if isinstance(data, dict) and status_field and status_field in data and allowed:
                                if data[status_field] not in allowed:
                                    validation_warnings.append(
                                        f"{status_field}='{data[status_field]}' not in allowed values {allowed}"
                                    )
            except Exception as e:
                logger.debug(f"Hints validation skipped due to error: {e}")

            # Utility: normalize filters coming from Dify (may be JSON strings with PostgREST-like operators)
            def _normalize_filters(raw_filters: Any) -> Optional[Dict[str, Any]]:
                if raw_filters is None:
                    return None
                f = raw_filters
                # If filters is a JSON string, try to parse
                if isinstance(f, str):
                    try:
                        f = json.loads(f)
                    except Exception:
                        # Keep as string if not JSON; caller likely mis-specified
                        return None
                if not isinstance(f, dict):
                    return None
                return f

            def _coerce_value(v: str) -> Any:
                # Convert basic strings to bool/number where appropriate
                if isinstance(v, str):
                    low = v.lower()
                    if low == 'true':
                        return True
                    if low == 'false':
                        return False
                    # Try number
                    try:
                        if '.' in v:
                            return float(v)
                        return int(v)
                    except Exception:
                        pass
                return v

            def _apply_filters(query, flt: Dict[str, Any]):
                for key, value in flt.items():
                    # Support PostgREST style like "eq.value", "gte.value", "in.(a,b)"
                    if isinstance(value, str):
                        val = value
                        op = 'eq'
                        if val.startswith('in.(') and val.endswith(')'):
                            items = [x.strip() for x in val[4:-1].split(',') if x.strip()]
                            query = query.in_(key, [ _coerce_value(x) for x in items ])
                            continue
                        if '.' in val:
                            op, rhs = val.split('.', 1)
                        else:
                            rhs = val
                        rhsv = _coerce_value(rhs)
                        if op == 'eq':
                            query = query.eq(key, rhsv)
                        elif op in ('neq', 'ne'):
                            query = query.neq(key, rhsv)
                        elif op == 'gt':
                            query = query.gt(key, rhsv)
                        elif op == 'gte':
                            query = query.gte(key, rhsv)
                        elif op == 'lt':
                            query = query.lt(key, rhsv)
                        elif op == 'lte':
                            query = query.lte(key, rhsv)
                        elif op == 'like':
                            query = query.like(key, rhs)
                        elif op == 'ilike':
                            query = query.ilike(key, rhs)
                        else:
                            # Fallback to eq
                            query = query.eq(key, rhs)
                    elif isinstance(value, list):
                        query = query.in_(key, value)
                    else:
                        query = query.eq(key, value)
                return query

            # SELECT operation
            if operation == "select":
                query = self.supabase_client.table(table_name).select("*")

                # Apply filters
                nf = _normalize_filters(filters)
                if nf:
                    query = _apply_filters(query, nf)

                # Apply ordering
                if order_by:
                    desc = order_by.startswith('-')
                    column = order_by.lstrip('-')
                    query = query.order(column, desc=desc)

                # Apply limit
                if limit:
                    query = query.limit(limit)

                result = query.execute()
                data = result.data or []

                return {
                    "status": "success",
                    "operation": "select",
                    "table": table_name,
                    "records": len(data),
                    "data": data,
                    "hints": validation_warnings or None,
                    "timestamp": datetime.now().isoformat()
                }

            # INSERT operation
            elif operation == "insert":
                if not data:
                    return {"status": "error", "error": "Data required for insert operation"}

                # Add audit fields for critical tables
                if table_name in critical_tables:
                    data.setdefault("created_by", "HAWK_AGENT")
                    data.setdefault("created_date", datetime.now().isoformat())

                result = self.supabase_client.table(table_name).insert(data).execute()

                return {
                    "status": "success",
                    "operation": "insert",
                    "table": table_name,
                    "records": len(result.data) if result.data else 0,
                    "data": result.data,
                    "hints": validation_warnings or None,
                    "timestamp": datetime.now().isoformat()
                }

            # UPDATE operation
            elif operation == "update":
                if not data:
                    return {"status": "error", "error": "Data required for update operation"}
                if not filters:
                    return {"status": "error", "error": "Filters required for update operation"}

                # Add audit fields for critical tables
                if table_name in critical_tables:
                    data.setdefault("modified_by", "HAWK_AGENT")
                    data.setdefault("modified_date", datetime.now().isoformat())

                query = self.supabase_client.table(table_name).update(data)

                # Apply filters (with normalization)
                nf = _normalize_filters(filters)
                if nf:
                    query = _apply_filters(query, nf)

                result = query.execute()

                return {
                    "status": "success",
                    "operation": "update",
                    "table": table_name,
                    "records": len(result.data) if result.data else 0,
                    "data": result.data,
                    "hints": validation_warnings or None,
                    "timestamp": datetime.now().isoformat()
                }

            # DELETE operation
            elif operation == "delete":
                if not filters:
                    return {"status": "error", "error": "Filters required for delete operation"}

                query = self.supabase_client.table(table_name).delete()

                # Apply filters (with normalization)
                nf = _normalize_filters(filters)
                if nf:
                    query = _apply_filters(query, nf)

                result = query.execute()

                return {
                    "status": "success",
                    "operation": "delete",
                    "table": table_name,
                    "records": len(result.data) if result.data else 0,
                    "hints": validation_warnings or None,
                    "timestamp": datetime.now().isoformat()
                }

            else:
                return {"status": "error", "error": f"Unsupported operation: {operation}"}

        except Exception as e:
            logger.error(f"Database {operation} error for {table_name}: {e}")
            return {
                "status": "error",
                "operation": operation,
                "table": table_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            # Get cache stats
            cache_stats = self.data_extractor.get_cache_stats() if self.data_extractor else {}
            
            # Calculate average processing time
            avg_processing_time = (self.total_processing_time / max(self.total_requests, 1)) * 1000
            
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "5.0.0-mcp",
                "components": {
                    "supabase": "connected" if self.supabase_client else "disconnected",
                    "redis": "connected" if self.redis_client else "disconnected", 
                    "prompt_engine": "initialized" if self.prompt_engine else "not_initialized",
                    "data_extractor": "initialized" if self.data_extractor else "not_initialized"
                },
                "performance": {
                    "total_requests": self.total_requests,
                    "avg_processing_time_ms": round(avg_processing_time, 2),
                    "total_processing_time_s": round(self.total_processing_time, 2)
                },
                "cache_stats": cache_stats,
                "optimization_target": OPTIMIZATION_STATS.get("cache_hit_rate_target", "98%")
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def manage_cache_operations(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Manage cache operations"""
        try:
            if not self.data_extractor or not self.data_extractor.redis_available:
                return {
                    "status": "error",
                    "operation": operation,
                    "error": "Redis cache not available - using memory cache fallback",
                    "fallback_stats": {
                        "cache_type": "memory",
                        "redis_available": False,
                        "memory_cache_operational": True
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            if operation == "stats":
                return {
                    "status": "success",
                    "operation": "stats",
                    "cache_stats": self.data_extractor.get_cache_stats(),
                    "timestamp": datetime.now().isoformat()
                }
                
            elif operation == "clear_currency":
                currency = kwargs.get("currency")
                if not currency:
                    return {"status": "error", "error": "Currency parameter required"}
                
                cleared_keys = self.data_extractor.clear_cache_for_currency(currency)
                return {
                    "status": "success",
                    "operation": "clear_currency",
                    "currency": currency,
                    "keys_cleared": cleared_keys,
                    "timestamp": datetime.now().isoformat()
                }
                
            elif operation == "info":
                redis_info = {}
                try:
                    if self.redis_client:
                        redis_info = self.redis_client.info("memory")
                except:
                    pass
                    
                return {
                    "status": "success", 
                    "operation": "info",
                    "redis_info": redis_info,
                    "cache_stats": self.data_extractor.get_cache_stats(),
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Unknown cache operation: {operation}",
                    "available_operations": ["stats", "clear_currency", "info"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Cache management error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def execute_write_operations(self,
                                     operation_type: str,
                                     user_prompt: str,
                                     analysis_result: PromptAnalysisResult,
                                     extracted_data: Dict[str, Any],
                                     currency: Optional[str] = None,
                                     entity_id: Optional[str] = None,
                                     nav_type: Optional[str] = None,
                                     amount: Optional[float] = None,
                                     write_data: Optional[Dict[str, Any]] = None,
                                     instruction_id: Optional[str] = None,
                                     execute_booking: bool = False,
                                     execute_posting: bool = False,
                                     ai_decisions: Optional[Dict[str, Any]] = None,
                                     detected_stage: str = "auto",
                                     agent_role: str = "unified") -> Dict[str, Any]:
        """
        Execute database write operations based on operation type
        """
        try:
            # --- RBAC GUARDRAILS ---
            # Defense-in-depth: Even if frontend routing fails, backend must deny invalid access
            
            # 1. Booking Agent should NOT perform Utilization/Feasibility (Stage 1A)
            if agent_role == "booking" and detected_stage == "1A":
                logger.warning(f"RBAC DENIED: Booking Agent attempted Stage 1A operation. Prompt: {user_prompt[:50]}")
                return {
                    "status": "error",
                    "error": "Access Denied: Booking Agent cannot perform Utilization/Feasibility checks. Please ask the Allocation Agent.",
                    "code": "RBAC_VIOLATION_BOOKING_1A"
                }

            # 2. Allocation Agent should NOT perform Booking/GL (Stage 2/3)
            # Note: Allocation agent often needs to "check" booking status, so we only block explicit write intents if strictly needed.
            # For now, we'll block explicit booking/posting operations.
            if agent_role == "allocation" and (operation_type in ["mx_booking", "gl_posting"] or detected_stage in ["2", "3"]):
                # Allow strictly read-only access? The universal processor usually handles reads before this point.
                # execute_write_operations is only called for NON-READ operations.
                logger.warning(f"RBAC DENIED: Allocation Agent attempted Stage 2/3 write operation. Prompt: {user_prompt[:50]}")
                return {
                    "status": "error",
                    "error": "Access Denied: Allocation Agent cannot perform Booking or GL Posting. Please ask the Booking Agent.",
                    "code": "RBAC_VIOLATION_ALLOCATION_23"
                }
            # -----------------------

            results = {
                "operation_type": operation_type,
                "status": "success",
                "records_affected": 0,
                "details": {},
                "timestamp": datetime.now().isoformat()
            }
            
            if operation_type == "write":
                results.update(await self._execute_write(
                    user_prompt, analysis_result, write_data, currency, entity_id, nav_type, amount, ai_decisions, detected_stage
                ))
            
            elif operation_type == "amend":
                results.update(await self._execute_amend(
                    instruction_id, write_data, user_prompt, analysis_result
                ))
            
            elif operation_type == "mx_booking":
                results.update(await self._execute_mx_booking(
                    instruction_id, execute_booking, user_prompt
                ))
            
            elif operation_type == "gl_posting":
                results.update(await self._execute_gl_posting(
                    instruction_id, execute_posting, user_prompt
                ))
            
            # Harden status: mark as error if any table-specific error present
            details = results.get("details") or {}
            if any(k.endswith("_error") for k in details.keys()):
                results["status"] = "error"
            # If write but no rows and no tables modified, treat as error
            if operation_type == "write":
                if results.get("records_affected", 0) == 0 and not results.get("tables_modified"):
                    results["status"] = "error"
                    results["error"] = results.get("error") or "no_write_target_or_noop"

            return results
            
        except Exception as e:
            logger.error(f"Write operation error ({operation_type}): {e}")
            return {
                "operation_type": operation_type,
                "status": "error",
                "error": str(e),
                "records_affected": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_write(self, user_prompt: str, analysis_result: PromptAnalysisResult,
                           write_data: Dict[str, Any], currency: str, entity_id: str,
                           nav_type: str, amount: float, ai_decisions: Optional[Dict[str, Any]] = None,
                           detected_stage: str = "auto") -> Dict[str, Any]:
        """Execute hedge instruction write operations with ATOMIC TRANSACTIONS"""
        try:
            # Validate write_data is a dictionary
            if write_data is not None and not isinstance(write_data, dict):
                raise TypeError(f"write_data must be a dictionary, got {type(write_data)}")

            results = {"records_affected": 0, "details": {}, "tables_modified": [], "verification": {}}

            # Helper function to get AI decision values
            def get_ai_value(decision_key: str, fallback_value: Any) -> Any:
                """Extract value from AI decision or use fallback"""
                try:
                    if ai_decisions and decision_key in ai_decisions:
                        decision = ai_decisions[decision_key]
                        if hasattr(decision, 'value'):
                            return decision.value
                        else:
                            logger.warning(f"AI decision {decision_key} has no 'value' attribute, using fallback")
                            return fallback_value
                    else:
                        logger.debug(f"No AI decision for {decision_key}, using fallback: {fallback_value}")
                        return fallback_value
                except Exception as e:
                    logger.error(f"Error accessing AI decision {decision_key}: {e}")
                    return fallback_value

            logger.info(f"Executing write operations with {'AI-driven' if ai_decisions else 'fallback'} parameter selection")

            # Allocation Engine Operations - ONLY FOR STAGE 1B/2 (ACTUAL ALLOCATION)
            # Stage 1A utilization checks should NOT write to allocation_engine
            if (write_data and write_data.get("target_table") == "allocation_engine") or (detected_stage in ["1B", "2"] and analysis_result.intent.value == "hedge_utilization"):
                allocation_data = {
                    "allocation_id": (write_data and write_data.get("allocation_id")) or f"ALLOC_{int(time.time())}",
                    "request_id": (write_data and write_data.get("request_id")) or f"REQ_{int(time.time())}",
                    "entity_id": entity_id or (write_data and write_data.get("entity_id")) or get_ai_value("entity_id", "SYSTEM"),  # AI-driven entity selection
                    "currency_code": currency or (write_data and write_data.get("currency_code")) or (write_data and write_data.get("exposure_currency")) or "AUD",
                    "nav_type": nav_type or (write_data and write_data.get("nav_type")) or get_ai_value("nav_type", "COI"),  # AI-driven NAV type
                    "hedge_amount_allocation": amount or (write_data and write_data.get("hedge_amount_allocation")),
                    # Provide sensible defaults for common NOT NULL columns
                    "sfx_position": (write_data and write_data.get("sfx_position")) or 0,
                    "calculation_date": (write_data and write_data.get("calculation_date")) or datetime.now().date().isoformat(),
                    "executed_date": (write_data and write_data.get("executed_date")) or datetime.now().date().isoformat(),
                    "allocation_status": (write_data and write_data.get("allocation_status")) or get_ai_value("allocation_status", "Calculated"),  # AI-driven allocation status
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat(),
                    # Remove allocation_notes as it doesn't exist in the schema
                }

                if write_data:
                    # Only update with fields that belong to allocation_engine table
                    allowed_fields = {
                        "allocation_id", "request_id", "entity_id", "currency_code", "nav_type",
                        "sfx_position", "car_exemption_flag", "car_amount_distribution", "manual_overlay_amount",
                        "buffer_percentage", "buffer_amount", "hedged_position", "unhedged_position",
                        "hedge_amount_allocation", "available_amount_for_hedging", "waterfall_priority",
                        "allocation_sequence", "allocation_status", "execution_date", "created_by",
                        "calculation_date", "executed_date", "created_date", "event_id", "instruction_id"
                    }
                    allocation_data.update({k: v for k, v in write_data.items() if k in allowed_fields})

                try:
                    result = self.supabase_client.table("allocation_engine").insert(allocation_data).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["allocation_engine"] = result.data[0] if result.data else None
                    results["tables_modified"].append("allocation_engine")
                    logger.info(f"Successfully inserted into allocation_engine: {len(result.data) if result.data else 0} records")
                except Exception as e:
                    logger.error(f"Allocation engine insert error: {e}")
                    results["details"]["allocation_engine_error"] = str(e)

            # Hedge Instructions Operations - AI-DRIVEN PARAMETER SELECTION
            if analysis_result.intent.value in ["hedge_inception", "hedge_rollover", "hedge_termination"] or (write_data and (write_data and write_data.get("target_table")) == "hedge_instructions"):
                # Derive robust currency/amount defaults if not provided
                effective_currency = currency or (write_data and write_data.get("exposure_currency"))
                effective_amount = amount or (write_data and write_data.get("hedge_amount_order"))
                try:
                    if not effective_currency:
                        effective_currency = (analysis_result.extracted_params or {}).get("currency")
                    if not effective_amount:
                        effective_amount = (analysis_result.extracted_params or {}).get("amount")
                    if ai_decisions:
                        if not effective_currency and ai_decisions.get("currency"):
                            cdec = ai_decisions.get("currency")
                            effective_currency = getattr(cdec, 'value', cdec)
                        if not effective_amount and ai_decisions.get("amount"):
                            adec = ai_decisions.get("amount")
                            effective_amount = getattr(adec, 'value', adec)
                except Exception as _e:
                    logger.debug(f"Instruction fallback param derive failed: {_e}")

                # Generate msg_uid if not provided in write_data
                current_time = datetime.now()
                date_str = current_time.strftime("%d%m%y")
                random_num = random.randint(1, 999)
                fallback_msg_uid = f"HAWK_1A_{date_str}_EXEC_{random_num:03d}"

                instruction_data = {
                    "instruction_id": (write_data and write_data.get("instruction_id")) or f"INST_{analysis_result.intent.value.upper()}_{int(time.time())}",
                    "instruction_type": (write_data and write_data.get("instruction_type")) or analysis_result.intent.value[6:7].upper(),  # Extract I/R/T
                    "exposure_currency": effective_currency,
                    "hedge_amount_order": effective_amount,
                    "hedge_method": (write_data and write_data.get("hedge_method")) or get_ai_value("hedge_method", "COH"),  # AI-driven hedge method
                    "instruction_status": (write_data and write_data.get("instruction_status")) or get_ai_value("instruction_status", "Received"),  # AI-driven status
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat(),
                    "received_timestamp": datetime.now().isoformat(),
                    "instruction_date": (write_data and write_data.get("instruction_date")) or datetime.now().date().isoformat(),
                    "trace_id": (write_data and write_data.get("trace_id")) or f"HI-INST_{int(time.time())}",
                    "msg_uid": (write_data and write_data.get("msg_uid")) or fallback_msg_uid  # Ensure msg_uid is always present
                }

                if write_data:
                    # Only update with fields that belong to hedge_instructions table
                    allowed_fields = {
                        "instruction_type", "instruction_date", "exposure_currency", "hedge_amount_order",
                        "hedge_method", "order_id", "sub_order_id", "entity_id", "nav_type", "currency_type",
                        "accounting_method", "instruction_status", "received_timestamp", "trace_id",
                        "created_by", "created_date", "msg_uid", "deal_id", "package_id"
                    }
                    instruction_data.update({k: v for k, v in write_data.items() if k in allowed_fields})

                try:
                    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
                        logger.warning("Attempting hedge_instructions insert without SUPABASE_SERVICE_ROLE_KEY; RLS may block writes.")
                    result = self.supabase_client.table("hedge_instructions").insert(instruction_data).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["hedge_instructions"] = result.data[0] if result.data else None
                    results["tables_modified"].append("hedge_instructions")
                    logger.info(f"Successfully inserted into hedge_instructions: {len(result.data) if result.data else 0} records")

                    # AUTO-GENERATE BUSINESS EVENT FOR STAGE 1A FEASIBILITY SUCCESS
                    # Only create business events for feasible operations (Pass/Partial)
                    instruction_result = result.data[0] if result.data else None
                    if instruction_result and detected_stage == "1A":
                        from .dynamic_write_generator import dynamic_write_generator

                        # Determine feasibility result from instruction status/check_status
                        instruction_status = instruction_result.get("instruction_status", "")
                        check_status = instruction_result.get("check_status", "")

                        # Map instruction status to feasibility result
                        feasibility_result = "Pass"  # Default
                        if check_status == "Fail" or instruction_status == "Failed":
                            feasibility_result = "Fail"
                        elif "Partial" in instruction_status or check_status == "Warning":
                            feasibility_result = "Partial"

                        # Generate business event for Pass/Partial only
                        if feasibility_result in ["Pass", "Partial"]:
                            business_event_data = dynamic_write_generator.generate_business_event_data(
                                instruction_id=instruction_result.get("instruction_id"),
                                feasibility_result=feasibility_result,
                                currency=currency,
                                entity_id=entity_id,
                                nav_type=nav_type,
                                amount=amount
                            )

                            if business_event_data:
                                try:
                                    # Remove target_table before insert
                                    event_insert_data = {k: v for k, v in business_event_data.items() if k != "target_table"}
                                    event_result = self.supabase_client.table("hedge_business_events").insert(event_insert_data).execute()
                                    results["records_affected"] += len(event_result.data) if event_result.data else 0
                                    results["details"]["hedge_business_events"] = event_result.data[0] if event_result.data else None
                                    results["tables_modified"].append("hedge_business_events")
                                    logger.info(f"Auto-generated business event for instruction {instruction_result.get('instruction_id')}")
                                except Exception as e:
                                    logger.error(f"Failed to auto-generate business event: {e}")
                                    results["details"]["hedge_business_events_error"] = str(e)
                except Exception as e:
                    # Idempotent handling for duplicate (23505): fetch by msg_uid if provided
                    err_txt = str(e)
                    logger.error(f"Hedge instructions insert error: {err_txt}")
                    results["details"]["hedge_instructions_error"] = err_txt
                    try:
                        msg_uid = (write_data and write_data.get("msg_uid")) or instruction_data.get("msg_uid")
                        if msg_uid and ("23505" in err_txt or "duplicate key value" in err_txt):
                            existing = self.supabase_client.table("hedge_instructions").select("*").eq("msg_uid", msg_uid).order("created_date", desc=True).limit(1).execute()
                            if existing.data:
                                results["details"]["hedge_instructions"] = existing.data[0]
                                results["status"] = "exists"
                                logger.info("Idempotent match found for msg_uid; returning existing instruction")
                    except Exception as _:
                        pass

            # Hedge Business Events Operations - AI-DRIVEN PARAMETER SELECTION
            if write_data and (write_data and write_data.get("target_table")) == "hedge_business_events":
                event_data = {
                    "event_id": (write_data and write_data.get("event_id")) or f"EVENT_{int(time.time())}",
                    "instruction_id": (write_data and write_data.get("instruction_id")) or (results["details"].get("hedge_instructions") or {}).get("instruction_id"),
                    "entity_id": (write_data and write_data.get("entity_id")) or get_ai_value("entity_id", "ENTITY0001"),  # AI-driven entity selection
                    "nav_type": (write_data and write_data.get("nav_type")) or get_ai_value("nav_type", "COI"),  # AI-driven NAV type
                    "currency_type": (write_data and write_data.get("currency_type")) or get_ai_value("currency_type", "Matched"),  # AI-driven currency alignment
                    "hedging_instrument": (write_data and write_data.get("hedging_instrument")) or get_ai_value("hedging_instrument", "FX_Swap"),  # AI-driven instrument selection
                    "accounting_method": (write_data and write_data.get("accounting_method")) or get_ai_value("accounting_method", "COH"),  # AI-driven accounting method
                    "notional_amount": (write_data and write_data.get("notional_amount")) or amount or 1000000,  # Use provided amount
                    "trade_date": (write_data and write_data.get("trade_date")) or datetime.now().date().isoformat(),  # Current date default
                    "business_event_type": ((write_data and write_data.get("business_event_type")) if write_data else None) or ((write_data and write_data.get("event_type")) if write_data else None) or get_ai_value("business_event_type", "Initiation"),  # AI-driven event type
                    "event_status": (write_data and write_data.get("event_status")) or get_ai_value("event_status", "Pending"),  # AI-driven event status
                    "stage_1a_status": (write_data and write_data.get("stage_1a_status")) or get_ai_value("stage_1a_status", "Pending"),  # AI-driven stage status
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat(),
                    "notes": (write_data and write_data.get("notes")) or f"Auto-created from: {user_prompt[:100]}"
                }

                if write_data:
                    # Only update with fields that belong to hedge_business_events table
                    allowed_fields = {
                        "event_id", "instruction_id", "entity_id", "nav_type", "currency_type",
                        "business_event_type", "event_status", "stage_1a_status", "stage_2_status", "stage_3_status",
                        "notional_amount", "allocated_amount", "booking_reference", "gl_reference",
                        "created_by", "created_date", "notes"
                    }
                    event_data.update({k: v for k, v in write_data.items() if k in allowed_fields})

                try:
                    result = self.supabase_client.table("hedge_business_events").insert(event_data).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["hedge_business_events"] = result.data[0] if result.data else None
                    results["tables_modified"].append("hedge_business_events")
                    logger.info(f"Successfully inserted into hedge_business_events: {len(result.data) if result.data else 0} records")
                except Exception as e:
                    logger.error(f"Hedge business events insert error: {e}")
                    results["details"]["hedge_business_events_error"] = str(e)

            # Stage 2 Booking Operations - AI-DRIVEN PARAMETER SELECTION
            if write_data and (write_data and write_data.get("target_table")) == "deal_bookings":
                # Column alias handling (KB vs internal):
                # - deal_id ↔ booking_id (normalize to booking_id for insert)
                # - product_code ↔ portfolio_code (normalize to portfolio_code)
                # - trade_ref ↔ murex_deal_id (normalize to murex_deal_id)
                normalized_booking_id = (write_data and (write_data.get("booking_id") or write_data.get("deal_id"))) or f"BOOKING_{int(time.time())}"
                normalized_portfolio = (write_data and (write_data.get("portfolio_code") or write_data.get("product_code"))) or get_ai_value("portfolio_code", "CO_FX")
                normalized_mx_ref = (write_data and (write_data.get("murex_deal_id") or write_data.get("trade_ref")))

                booking_data = {
                    "booking_id": normalized_booking_id,
                    "instruction_id": (write_data and write_data.get("instruction_id")) or (results["details"].get("hedge_instructions") or {}).get("instruction_id"),
                    "event_id": (write_data and write_data.get("event_id")) or (results["details"].get("hedge_business_events") or {}).get("event_id"),
                    "murex_deal_id": normalized_mx_ref,
                    "portfolio_code": normalized_portfolio,
                    "notional_amount": (write_data and write_data.get("notional_amount")) or amount,
                    "currency": (write_data and write_data.get("currency")) or currency,
                    "value_date": (write_data and write_data.get("value_date")) or get_ai_value("value_date", None),
                    "maturity_date": (write_data and write_data.get("maturity_date")) or get_ai_value("maturity_date", None),
                    "booking_status": (write_data and write_data.get("booking_status")) or get_ai_value("booking_status", "Pending"),
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat(),
                    "notes": (write_data and write_data.get("notes")) or f"Auto-created from: {user_prompt[:100]}"
                }

                # Do not pass through KB-only fields that may not exist on this table
                # Keep payload minimal and schema-safe

                try:
                    result = self.supabase_client.table("deal_bookings").insert(booking_data).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["deal_bookings"] = result.data[0] if result.data else None
                    results["tables_modified"].append("deal_bookings")
                    logger.info(f"Successfully inserted into deal_bookings: {len(result.data) if result.data else 0} records")
                except Exception as e:
                    logger.error(f"Deal bookings insert error: {e}")
                    results["details"]["deal_bookings_error"] = str(e)

            # Stage 2 External System Integration - AI-DRIVEN PARAMETER SELECTION
            if write_data and (write_data and write_data.get("target_table")) == "h_stg_mrx_ext":
                mrx_data = {
                    "message_id": (write_data and write_data.get("message_id")) or f"MRX_{int(time.time())}",
                    "instruction_id": (write_data and write_data.get("instruction_id")) or (results["details"].get("hedge_instructions") or {}).get("instruction_id"),
                    "booking_id": (write_data and write_data.get("booking_id")) or (results["details"].get("deal_bookings") or {}).get("booking_id"),
                    "message_type": (write_data and write_data.get("message_type")) or get_ai_value("message_type", "BOOKING_REQUEST"),  # AI-driven message type
                    "message_status": (write_data and write_data.get("message_status")) or get_ai_value("message_status", "QUEUED"),  # AI-driven message status
                    "message_payload": (write_data and write_data.get("message_payload")) or f"{{\"instruction_id\": \"{results['details'].get('hedge_instructions', {}).get('instruction_id')}\", \"generated_by\": \"HAWK_AGENT\"}}",
                    "processing_attempt": (write_data and write_data.get("processing_attempt")) or 1,
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat()
                }

                if write_data:
                    mrx_data.update({k: v for k, v in write_data.items() if k != "target_table"})

                try:
                    result = self.supabase_client.table("h_stg_mrx_ext").insert(mrx_data).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["h_stg_mrx_ext"] = result.data[0] if result.data else None
                    results["tables_modified"].append("h_stg_mrx_ext")
                    logger.info(f"Successfully inserted into h_stg_mrx_ext: {len(result.data) if result.data else 0} records")
                except Exception as e:
                    logger.error(f"Murex external integration insert error: {e}")
                    results["details"]["h_stg_mrx_ext_error"] = str(e)

            # Stage 3 GL Package Header - AI-DRIVEN PARAMETER SELECTION (Hybrid with Compliance Rules)
            if write_data and (write_data and write_data.get("target_table")) == "hedge_gl_packages":
                gl_package_data = {
                    "package_id": (write_data and write_data.get("package_id")) or f"GL_PKG_{int(time.time())}",
                    "instruction_id": (write_data and write_data.get("instruction_id")) or (results["details"].get("hedge_instructions") or {}).get("instruction_id"),
                    "event_id": (write_data and write_data.get("event_id")) or (results["details"].get("hedge_business_events") or {}).get("event_id"),
                    "booking_id": (write_data and write_data.get("booking_id")) or (results["details"].get("deal_bookings") or {}).get("booking_id"),
                    "package_status": (write_data and write_data.get("package_status")) or get_ai_value("package_status", "DRAFT"),  # AI-driven package status
                    "gl_date": (write_data and write_data.get("gl_date")) or get_ai_value("gl_date", datetime.now().date().isoformat()),  # AI-driven GL date selection
                    "total_debit_amount": (write_data and write_data.get("total_debit_amount")) or 0,  # Compliance rule: Zero until calculated
                    "total_credit_amount": (write_data and write_data.get("total_credit_amount")) or 0,  # Compliance rule: Zero until calculated
                    "currency": (write_data and write_data.get("currency")) or currency,
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat(),
                    "notes": (write_data and write_data.get("notes")) or f"Auto-created from: {user_prompt[:100]}"
                }

                if write_data:
                    gl_package_data.update({k: v for k, v in write_data.items() if k != "target_table"})

                try:
                    result = self.supabase_client.table("hedge_gl_packages").insert(gl_package_data).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["hedge_gl_packages"] = result.data[0] if result.data else None
                    results["tables_modified"].append("hedge_gl_packages")
                    logger.info(f"Successfully inserted into hedge_gl_packages: {len(result.data) if result.data else 0} records")
                except Exception as e:
                    logger.error(f"GL packages insert error: {e}")
                    results["details"]["hedge_gl_packages_error"] = str(e)

            # Stage 3 GL Entries (DR/CR Lines) - AI-DRIVEN PARAMETER SELECTION (Hybrid with Compliance Rules)
            if write_data and (write_data and write_data.get("target_table")) == "hedge_gl_entries":
                gl_entry_data = {
                    "entry_id": (write_data and write_data.get("entry_id")) or f"GL_ENTRY_{int(time.time())}",
                    "package_id": (write_data and write_data.get("package_id")) or (results["details"].get("hedge_gl_packages") or {}).get("package_id"),
                    "instruction_id": (write_data and write_data.get("instruction_id")) or (results["details"].get("hedge_instructions") or {}).get("instruction_id"),
                    "account_code": (write_data and write_data.get("account_code")) or get_ai_value("account_code", "999999"),  # AI-driven account selection
                    "debit_amount": ((write_data and write_data.get("debit_amount")) if write_data else None) or (amount if write_data and (write_data and write_data.get("entry_type")) == "DEBIT" else 0),
                    "credit_amount": ((write_data and write_data.get("credit_amount")) if write_data else None) or (amount if write_data and (write_data and write_data.get("entry_type")) == "CREDIT" else 0),
                    "entry_type": (write_data and write_data.get("entry_type")) or get_ai_value("entry_type", "DEBIT"),  # AI-driven entry type
                    "currency": (write_data and write_data.get("currency")) or currency,
                    "narrative": (write_data and write_data.get("narrative")) or get_ai_value("narrative", f"Hedge operation - {analysis_result.intent.value}"),  # AI-driven narrative
                    "business_unit": (write_data and write_data.get("business_unit")) or get_ai_value("business_unit", "TRADING"),  # AI-driven business unit
                    "profit_center": (write_data and write_data.get("profit_center")) or get_ai_value("profit_center", "FX_HEDGE"),  # AI-driven profit center
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat()
                }

                if write_data:
                    gl_entry_data.update({k: v for k, v in write_data.items() if k != "target_table"})

                try:
                    result = self.supabase_client.table("hedge_gl_entries").insert(gl_entry_data).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["hedge_gl_entries"] = result.data[0] if result.data else None
                    results["tables_modified"].append("hedge_gl_entries")
                    logger.info(f"Successfully inserted into hedge_gl_entries: {len(result.data) if result.data else 0} records")
                except Exception as e:
                    logger.error(f"GL entries insert error: {e}")
                    results["details"]["hedge_gl_entries_error"] = str(e)

            # KB-aligned GL entries direct insert support (gl_entries)
            if write_data and (write_data and write_data.get("target_table")) == "gl_entries":
                kb_gl = {
                    "entry_id": (write_data and write_data.get("entry_id")) or f"GLENT_{int(time.time())}",
                    "package_id": (write_data and write_data.get("package_id")),
                    "be_code": (write_data and write_data.get("be_code")) or get_ai_value("be_code", "BE_FX_RE"),
                    "dr_account": (write_data and write_data.get("dr_account")),
                    "cr_account": (write_data and write_data.get("cr_account")),
                    "dr_amount_sgd": (write_data and write_data.get("dr_amount_sgd")) or 0,
                    "cr_amount_sgd": (write_data and write_data.get("cr_amount_sgd")) or 0,
                    "currency": (write_data and write_data.get("currency")) or currency,
                    "created_by": "HAWK_AGENT",
                    "created_date": datetime.now().isoformat()
                }
                try:
                    result = self.supabase_client.table("gl_entries").insert(kb_gl).execute()
                    results["records_affected"] += len(result.data) if result.data else 0
                    results["details"]["gl_entries"] = result.data[0] if result.data else None
                    results["tables_modified"].append("gl_entries")
                    logger.info(f"Successfully inserted into gl_entries: {len(result.data) if result.data else 0} records")
                except Exception as e:
                    logger.error(f"KB gl_entries insert error: {e}")
                    results["details"]["gl_entries_error"] = str(e)

            # Step: Verification via msg_uid if available
            if results["records_affected"] > 0:
                await self._verify_write_operations(results, write_data)

            return results

        except Exception as e:
            logger.error(f"Write execution error: {e}")
            raise

    async def _verify_write_operations(self, results: Dict[str, Any], write_data: Optional[Dict[str, Any]]) -> None:
        """Verify write operations via msg_uid lookup"""
        try:
            verification_results = {}

            # Check if hedge_instructions were created and verify via msg_uid
            if "hedge_instructions" in results["details"] and results["details"]["hedge_instructions"]:
                instruction_data = results["details"]["hedge_instructions"]
                instruction_id = instruction_data.get("instruction_id")

                if instruction_id:
                    # Query to verify the record exists
                    verify_query = await self.query_supabase_direct(
                        table_name="hedge_instructions",
                        filters={"instruction_id": instruction_id},
                        limit=1
                    )

                    if verify_query["status"] == "success" and verify_query["records"] > 0:
                        verification_results["hedge_instructions"] = {
                            "status": "verified",
                            "instruction_id": instruction_id,
                            "msg_uid": verify_query["data"][0].get("msg_uid"),
                            "trace_id": verify_query["data"][0].get("trace_id")
                        }
                    else:
                        verification_results["hedge_instructions"] = {
                            "status": "verification_failed",
                            "instruction_id": instruction_id,
                            "error": "Record not found after insert"
                        }

            # Check allocation_engine verification
            if "allocation_engine" in results["details"] and results["details"]["allocation_engine"]:
                allocation_data = results["details"]["allocation_engine"]
                allocation_id = allocation_data.get("allocation_id")

                if allocation_id:
                    verify_query = await self.query_supabase_direct(
                        table_name="allocation_engine",
                        filters={"allocation_id": allocation_id},
                        limit=1
                    )

                    if verify_query["status"] == "success" and verify_query["records"] > 0:
                        verification_results["allocation_engine"] = {
                            "status": "verified",
                            "allocation_id": allocation_id,
                            "allocation_run_id": verify_query["data"][0].get("allocation_run_id")
                        }
                    else:
                        verification_results["allocation_engine"] = {
                            "status": "verification_failed",
                            "allocation_id": allocation_id,
                            "error": "Record not found after insert"
                        }

            results["verification"] = verification_results
            logger.info(f"Write operation verification completed: {len(verification_results)} tables verified")

        except Exception as e:
            logger.error(f"Verification error: {e}")
            results["verification"] = {"status": "verification_error", "error": str(e)}
    
    async def _execute_amend(self, instruction_id: str, write_data: Dict[str, Any], 
                           user_prompt: str, analysis_result: PromptAnalysisResult) -> Dict[str, Any]:
        """Execute amendment operations on existing records"""
        try:
            if not write_data or not isinstance(write_data, dict):
                raise ValueError("write_data must be a dictionary for amend operations")

            target_table = write_data.get("target_table")

            # Decide whether this is an allocation_engine amend or hedge_instructions amend
            is_allocation_amend = (
                target_table == "allocation_engine"
                or ("allocation_id" in write_data)
                or ("amount" in write_data or "status" in write_data)
            )

            if is_allocation_amend:
                allocation_id = write_data.get("allocation_id")
                if not allocation_id:
                    # Fallback: if caller passed only instruction_id but intended allocation amend, require explicit allocation_id
                    raise ValueError("allocation_id required for allocation_engine amend")

                update_data = {
                    "modified_by": "HAWK_AGENT",
                    "modified_date": datetime.now().isoformat(),
                    # Do not include free-form 'notes' unless schema supports it
                }

                # Map common shorthands
                if "amount" in write_data:
                    update_data["hedge_amount_allocation"] = write_data["amount"]
                if "status" in write_data:
                    update_data["allocation_status"] = write_data["status"]

                # Merge provided fields, excluding routing and shorthand keys already mapped
                exclude_keys = {"target_table", "allocation_id", "amount", "status"}
                update_data.update({k: v for k, v in write_data.items() if k not in exclude_keys})

                # Try update with allocation_status; if column mismatch, retry with status
                try:
                    result = self.supabase_client.table("allocation_engine")\
                        .update(update_data)\
                        .eq("allocation_id", allocation_id)\
                        .execute()
                except Exception as e:
                    err = str(e).lower()
                    # Retry by swapping allocation_status <-> status if column unknown
                    try:
                        swapped = update_data.copy()
                        if "allocation_status" in swapped and "column" in err and "allocation_status" in err:
                            val = swapped.pop("allocation_status")
                            swapped["status"] = val
                        elif "status" in swapped and "column" in err and "status" in err:
                            val = swapped.pop("status")
                            swapped["allocation_status"] = val
                        result = self.supabase_client.table("allocation_engine")\
                            .update(swapped)\
                            .eq("allocation_id", allocation_id)\
                            .execute()
                    except Exception as e2:
                        logger.error(f"Allocation amend failed with both variants: {e2}")
                        raise

                return {"records_affected": len(result.data), "details": {"updated_allocation": allocation_id}}

            # Otherwise, amend hedge_instructions
            if not instruction_id:
                raise ValueError("instruction_id required for hedge_instructions amend")

            update_data = {
                "modified_by": "HAWK_AGENT",
                "modified_date": datetime.now().isoformat(),
            }
            # Exclude routing and primary-key shorthands from payload
            exclude_keys = {"target_table", "instruction_id"}
            update_data.update({k: v for k, v in write_data.items() if k not in exclude_keys})

            result = self.supabase_client.table("hedge_instructions")\
                .update(update_data)\
                .eq("instruction_id", instruction_id)\
                .execute()

            return {"records_affected": len(result.data), "details": {"updated_instruction": instruction_id}}

        except Exception as e:
            logger.error(f"Amend execution error: {e}")
            raise
    
    async def _execute_mx_booking(self, instruction_id: str, execute_booking: bool, user_prompt: str) -> Dict[str, Any]:
        """Execute Murex booking operations"""
        try:
            if not instruction_id:
                raise ValueError("instruction_id required for mx_booking operations")
            
            # Update hedge_business_events with booking status
            booking_data = {
                "stage_2_status": "In_Progress" if execute_booking else "Pending",
                "stage_2_start_time": datetime.now().isoformat() if execute_booking else None,
                "assigned_booking_model": "HAWK_AUTO_BOOKING" if execute_booking else None,
                "notes": f"Booking initiated via: {user_prompt[:100]}"
            }
            
            result = self.supabase_client.table("hedge_business_events")\
                .update(booking_data)\
                .eq("instruction_id", instruction_id)\
                .execute()
            
            # If execute_booking is True, simulate booking completion
            if execute_booking and result.data:
                completion_data = {
                    "stage_2_status": "Completed",
                    "stage_2_completion_time": datetime.now().isoformat(),
                    "murex_deal_id": f"MRX_AUTO_{int(time.time())}",
                    "booking_reference": f"BK_AUTO_{int(time.time())}",
                    "event_status": "Booked"
                }
                
                self.supabase_client.table("hedge_business_events")\
                    .update(completion_data)\
                    .eq("instruction_id", instruction_id)\
                    .execute()
            
            return {
                "records_affected": len(result.data),
                "details": {
                    "instruction_id": instruction_id,
                    "booking_status": "Executed" if execute_booking else "Queued",
                    "murex_deal_id": f"MRX_AUTO_{int(time.time())}" if execute_booking else None
                }
            }
            
        except Exception as e:
            logger.error(f"MX Booking execution error: {e}")
            raise
    
    async def _execute_gl_posting(self, instruction_id: str, execute_posting: bool, user_prompt: str) -> Dict[str, Any]:
        """Execute GL posting operations"""
        try:
            if not instruction_id:
                raise ValueError("instruction_id required for gl_posting operations")
            
            # Update hedge_business_events with GL posting status
            posting_data = {
                "stage_3_status": "In_Progress" if execute_posting else "Pending",
                "gl_posting_status": "In_Progress" if execute_posting else "Pending",
                "modified_date": datetime.now().isoformat(),  # Use standard modified_date instead
                "modified_by": "HAWK_AGENT",
                "notes": f"GL posting initiated via: {user_prompt[:100]}"
            }
            
            result = self.supabase_client.table("hedge_business_events")\
                .update(posting_data)\
                .eq("instruction_id", instruction_id)\
                .execute()
            
            # If execute_posting is True, simulate posting completion
            if execute_posting and result.data:
                completion_data = {
                    "stage_3_status": "Completed",
                    "gl_posting_status": "Posted", 
                    "gl_package_id": f"GL_AUTO_{int(time.time())}",
                    "stage_3_attempts": 1
                }
                
                self.supabase_client.table("hedge_business_events")\
                    .update(completion_data)\
                    .eq("instruction_id", instruction_id)\
                    .execute()
            
            return {
                "records_affected": len(result.data),
                "details": {
                    "instruction_id": instruction_id,
                    "gl_status": "Posted" if execute_posting else "Queued",
                    "gl_package_id": f"GL_AUTO_{int(time.time())}" if execute_posting else None
                }
            }
            
        except Exception as e:
            logger.error(f"GL Posting execution error: {e}")
            raise

    def _apply_intelligent_formatting(self, response: Dict[str, Any], user_prompt: str, template_category: Optional[str] = None) -> Dict[str, Any]:
        """Apply intelligent response formatting based on user context and verbosity"""
        try:
            # Detect user context for formatting
            prompt_lower = user_prompt.lower()

            # Determine response style based on clues
            if any(term in prompt_lower for term in ["executive", "summary", "overview", "high-level"]):
                response_style = "executive"
            elif any(term in prompt_lower for term in ["detailed", "comprehensive", "full", "complete"]):
                response_style = "detailed"
            elif any(term in prompt_lower for term in ["technical", "debug", "trace", "error"]):
                response_style = "technical"
            elif template_category:
                response_style = template_category.lower()
            else:
                response_style = "operational"  # Default

            # Apply formatting based on style
            if response_style == "executive":
                response = self._format_executive_response(response)
            elif response_style == "detailed":
                response = self._format_detailed_response(response)
            elif response_style == "technical":
                response = self._format_technical_response(response)
            else:
                response = self._format_operational_response(response)

            # Add response metadata
            response["formatting_metadata"] = {
                "detected_style": response_style,
                "template_category": template_category,
                "verbosity_level": self._calculate_verbosity_level(response)
            }

            return response

        except Exception as e:
            logger.warning(f"Response formatting error: {e}")
            return response  # Return unmodified if formatting fails

    def _format_executive_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format response for executive audience - high-level summary"""
        try:
            # Create executive summary
            exec_summary = {
                "status": response.get("status"),
                "key_findings": self._extract_key_findings(response),
                "recommendations": self._extract_recommendations(response),
                "risk_highlights": self._extract_risk_highlights(response)
            }

            # Add executive summary to response
            response["executive_summary"] = exec_summary
            return response

        except Exception as e:
            logger.warning(f"Executive formatting error: {e}")
            return response

    def _format_detailed_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format response for detailed analysis"""
        try:
            # Add comprehensive analysis
            response["detailed_analysis"] = {
                "ai_decision_count": len(response.get("ai_decisions", {})),
                "data_sources_consulted": len(response.get("extracted_data", {})),
                "processing_efficiency": f"{response.get('processing_metadata', {}).get('processing_time_ms', 0)}ms"
            }
            return response

        except Exception as e:
            logger.warning(f"Detailed formatting error: {e}")
            return response

    def _format_technical_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format response for technical debugging"""
        try:
            # Add technical details
            response["technical_details"] = {
                "ai_decisions_made": len(response.get("ai_decisions", {})),
                "database_operations": response.get("write_results", {}).get("records_affected", 0),
                "processing_time": response.get("processing_metadata", {}).get("processing_time_ms", 0)
            }
            return response

        except Exception as e:
            logger.warning(f"Technical formatting error: {e}")
            return response

    def _format_operational_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format response for operational use - balanced detail"""
        try:
            # Add operational summary
            response["operational_summary"] = {
                "status": response.get("status"),
                "ai_enhanced": bool(response.get("ai_decisions")),
                "records_processed": response.get("write_results", {}).get("records_affected", 0)
            }
            return response

        except Exception as e:
            logger.warning(f"Operational formatting error: {e}")
            return response

    def _extract_key_findings(self, response: Dict[str, Any]) -> List[str]:
        """Extract key findings for executive summary"""
        findings = []
        if response.get("status") == "success":
            findings.append("Operation completed successfully")
        if "ai_decisions" in response:
            findings.append(f"AI-driven decisions: {len(response['ai_decisions'])}")
        return findings or ["No significant findings"]

    def _extract_recommendations(self, response: Dict[str, Any]) -> List[str]:
        """Extract recommendations for executive summary"""
        recommendations = []
        if response.get("status") == "success":
            recommendations.append("Proceed with planned operations")
        return recommendations or ["Continue with standard procedures"]

    def _extract_risk_highlights(self, response: Dict[str, Any]) -> List[str]:
        """Extract risk highlights for executive summary"""
        risks = []
        if response.get("status") == "error":
            risks.append("Operational failure detected")
        return risks or ["No significant risks identified"]

    def _calculate_verbosity_level(self, response: Dict[str, Any]) -> str:
        """Calculate response verbosity level"""
        total_keys = len(response)
        if total_keys <= 5:
            return "minimal"
        elif total_keys <= 10:
            return "standard"
        else:
            return "detailed"


# Global instance for shared use
hedge_processor = HedgeFundProcessor()
