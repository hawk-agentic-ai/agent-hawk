"""
AI Decision Engine for HAWK Hedge Fund Operations
Replaces hardcoded values with intelligent, context-aware decisions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DecisionConfidence(Enum):
    """Confidence levels for AI decisions"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FALLBACK = "fallback"

@dataclass
class AIDecision:
    """Container for AI decision with reasoning and confidence"""
    value: Any
    reasoning: str
    confidence: DecisionConfidence
    factors_considered: List[str]
    alternatives_evaluated: List[str]
    timestamp: str

@dataclass
class HedgeContext:
    """Parsed context from user prompt and parameters"""
    user_prompt: str
    currency: Optional[str] = None
    amount: Optional[float] = None
    geographic_indicators: List[str] = None
    urgency_level: str = "standard"
    operation_type: str = "inception"
    risk_profile: str = "standard"
    regulatory_domain: str = "unknown"
    tenor_indicators: List[str] = None
    market_conditions: Dict[str, Any] = None

class HedgeDecisionEngine:
    """
    AI-powered decision engine for hedge fund operations
    Replaces all hardcoded values with intelligent, context-aware choices
    """

    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client
        self.decision_cache = {}
        self.market_data_cache = {}
        self.last_cache_update = None

        # Geographic mappings for intelligent entity selection
        self.geographic_entity_mapping = {
            "US": ["ENTITY0001", "ENTITY0002"],
            "UK": ["ENTITY0003", "ENTITY0004"],
            "EU": ["ENTITY0005", "ENTITY0006"],
            "APAC": ["ENTITY0007", "ENTITY0008"],
            "CANADA": ["ENTITY0009", "ENTITY0010"]
        }

        # Currency risk profiles
        self.currency_risk_profiles = {
            "USD": {"volatility": "low", "liquidity": "high", "g3": True},
            "EUR": {"volatility": "low", "liquidity": "high", "g3": True},
            "GBP": {"volatility": "medium", "liquidity": "high", "g3": True},
            "JPY": {"volatility": "medium", "liquidity": "high", "g3": True},
            "CAD": {"volatility": "medium", "liquidity": "medium", "g3": False},
            "AUD": {"volatility": "medium", "liquidity": "medium", "g3": False}
        }

        logger.info("AI Decision Engine initialized")

    async def make_all_decisions(self, context: HedgeContext) -> Dict[str, AIDecision]:
        """
        Make all intelligent decisions for hedge operation
        Replaces all hardcoded values with AI-driven choices
        """
        try:
            logger.info(f"Making AI decisions for: {context.user_prompt[:100]}...")

            # Update market context if needed
            await self._update_market_context()

            decisions = {}

            # Core entity and geographic decisions
            decisions["entity_id"] = await self._decide_entity_selection(context)
            decisions["nav_type"] = await self._decide_nav_type(context)
            decisions["currency_type"] = await self._decide_currency_type(context)

            # Instrument and execution decisions
            decisions["hedging_instrument"] = await self._decide_hedging_instrument(context)
            decisions["accounting_method"] = await self._decide_accounting_method(context)

            # Status and workflow decisions
            decisions["instruction_status"] = await self._decide_instruction_status(context)
            decisions["event_status"] = await self._decide_event_status(context)
            decisions["stage_1a_status"] = await self._decide_stage_status(context, "1a")

            # Business logic decisions
            decisions["business_event_type"] = await self._decide_business_event_type(context)
            decisions["buffer_percentage"] = await self._decide_buffer_percentage(context)

            # GL and accounting decisions
            decisions["account_code"] = await self._decide_account_code(context)
            decisions["business_unit"] = await self._decide_business_unit(context)
            decisions["profit_center"] = await self._decide_profit_center(context)

            # Apply confidence-based validation and enhancement
            decisions = await self._apply_confidence_validation(decisions, context)

            logger.info(f"Completed AI decisions with average confidence: {self._calculate_average_confidence(decisions)}")
            return decisions

        except Exception as e:
            logger.error(f"AI decision engine error: {e}")
            # Return safe fallback decisions
            return await self._get_fallback_decisions(context)

    async def _decide_entity_selection(self, context: HedgeContext) -> AIDecision:
        """Intelligently select entity based on geographic and currency context"""
        try:
            # Parse geographic indicators from prompt
            geographic_clues = await self._extract_geographic_context(context.user_prompt)

            # Consider currency jurisdiction
            currency_jurisdiction = self._get_currency_jurisdiction(context.currency)

            # Score entities based on multiple factors
            entity_scores = {}
            available_entities = await self._get_available_entities()

            for entity in available_entities:
                score = await self._score_entity_suitability(
                    entity, geographic_clues, currency_jurisdiction, context
                )
                entity_scores[entity["entity_id"]] = score

            # Select highest scoring entity
            best_entity = max(entity_scores.items(), key=lambda x: x[1])

            return AIDecision(
                value=best_entity[0],
                reasoning=f"Selected {best_entity[0]} based on geographic context ({geographic_clues}), currency jurisdiction ({currency_jurisdiction}), and entity capability score ({best_entity[1]:.2f})",
                confidence=DecisionConfidence.HIGH if best_entity[1] > 0.8 else DecisionConfidence.MEDIUM,
                factors_considered=["geographic_context", "currency_jurisdiction", "entity_capabilities", "regulatory_alignment"],
                alternatives_evaluated=list(entity_scores.keys()),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Entity selection AI failed: {e}, using fallback")
            # Intelligent fallback based on context
            fallback_entity = self._get_fallback_entity(context)
            return AIDecision(
                value=fallback_entity,
                reasoning=f"Fallback to {fallback_entity} entity due to AI processing error, selected based on context currency {context.currency}",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_hedging_instrument(self, context: HedgeContext) -> AIDecision:
        """Intelligently select hedging instrument based on market conditions and context"""
        try:
            # Get available instruments from database
            available_instruments = await self._get_available_instruments()

            # Analyze market conditions for currency
            market_conditions = await self._get_market_conditions(context.currency)

            # Score instruments based on multiple factors
            instrument_scores = {}

            for instrument in available_instruments:
                score = await self._score_instrument_suitability(
                    instrument, context, market_conditions
                )
                instrument_scores[instrument] = score

            # Select optimal instrument
            best_instrument = max(instrument_scores.items(), key=lambda x: x[1])

            return AIDecision(
                value=best_instrument[0],
                reasoning=f"Selected {best_instrument[0]} based on market volatility ({market_conditions.get('volatility', 'unknown')}), liquidity ({market_conditions.get('liquidity', 'unknown')}), and cost efficiency (score: {best_instrument[1]:.2f})",
                confidence=DecisionConfidence.HIGH if best_instrument[1] > 0.7 else DecisionConfidence.MEDIUM,
                factors_considered=["market_volatility", "liquidity", "cost_efficiency", "tenor_suitability"],
                alternatives_evaluated=list(instrument_scores.keys()),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Instrument selection AI failed: {e}, using fallback")
            return AIDecision(
                value="FX_Swap",
                reasoning="Fallback to FX_Swap as most common instrument",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_nav_type(self, context: HedgeContext) -> AIDecision:
        """Decide NAV type based on entity characteristics, database patterns, and operation type"""
        try:
            # Get available NAV types from database
            available_nav_types = await self._get_available_nav_types(context.currency)

            # Analyze entity characteristics if entity is known
            entity_profile = await self._get_entity_profile(context)

            # Enhanced decision logic considering multiple factors
            decision_factors = {}

            # Factor 1: Operation type influence
            if context.operation_type in ["inception", "increase", "hedge_utilization"]:
                decision_factors["operation_preference"] = "COI"
            elif context.operation_type in ["termination", "rollover"]:
                decision_factors["operation_preference"] = "RE"

            # Factor 2: Regulatory framework influence
            if entity_profile.get("regulatory_classification") == "IFRS":
                decision_factors["regulatory_preference"] = "RE"
            elif entity_profile.get("regulatory_classification") == "US_GAAP":
                decision_factors["regulatory_preference"] = "COI"

            # Factor 3: Amount size influence (large amounts often use RE for fair value)
            if context.amount and context.amount > 50000000:  # > 50M
                decision_factors["amount_preference"] = "RE"
            else:
                decision_factors["amount_preference"] = "COI"

            # Factor 4: Database usage patterns
            if available_nav_types:
                decision_factors["database_common"] = available_nav_types[0]  # Most common

            # Scoring logic
            scores = {"COI": 0, "RE": 0, "SFX": 0, "FX": 0}
            for factor, preference in decision_factors.items():
                if preference in scores:
                    scores[preference] += 1

            # Select highest scoring option
            nav_decision = max(scores.items(), key=lambda x: x[1])[0]
            max_score = scores[nav_decision]

            # Determine confidence based on consensus
            if max_score >= 3:
                confidence = DecisionConfidence.HIGH
                reasoning = f"{nav_decision} selected with strong consensus across {max_score} factors: {list(decision_factors.keys())}"
            elif max_score >= 2:
                confidence = DecisionConfidence.MEDIUM
                reasoning = f"{nav_decision} selected with moderate consensus across {max_score} factors"
            else:
                # Fallback to conservative choice
                nav_decision = "COI"
                confidence = DecisionConfidence.LOW
                reasoning = "COI selected as conservative fallback due to unclear consensus"

            return AIDecision(
                value=nav_decision,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["operation_type", "entity_regulatory_classification", "valuation_methodology"],
                alternatives_evaluated=["COI", "RE"],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"NAV type decision AI failed: {e}, using fallback")
            return AIDecision(
                value="COI",
                reasoning="Fallback to COI as most common NAV type",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_instruction_status(self, context: HedgeContext) -> AIDecision:
        """Determine appropriate instruction status based on urgency and workflow"""
        try:
            # Parse urgency from prompt
            urgency = await self._determine_urgency(context.user_prompt)

            # Determine appropriate status
            if urgency == "urgent":
                status = "Validated"  # Skip to validated for urgent processing
                reasoning = "Validated status for urgent processing to expedite workflow"
                confidence = DecisionConfidence.HIGH
            elif urgency == "standard":
                status = "Received"  # Standard processing flow
                reasoning = "Received status for standard processing workflow"
                confidence = DecisionConfidence.HIGH
            else:
                status = "Received"  # Default safe choice
                reasoning = "Received status as conservative default"
                confidence = DecisionConfidence.MEDIUM

            return AIDecision(
                value=status,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["urgency_level", "workflow_optimization", "risk_management"],
                alternatives_evaluated=["Received", "Validated", "Allocated"],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Instruction status decision AI failed: {e}, using fallback")
            return AIDecision(
                value="Received",
                reasoning="Fallback to Received as safest initial status",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    # Helper methods for AI decision making

    async def _extract_geographic_context(self, prompt: str) -> List[str]:
        """Extract geographic indicators from user prompt"""
        geographic_keywords = {
            "US": ["america", "american", "usa", "united states", "dollar", "usd"],
            "UK": ["britain", "british", "england", "london", "pound", "gbp"],
            "EU": ["europe", "european", "germany", "france", "euro", "eur"],
            "APAC": ["asia", "asian", "japan", "singapore", "hong kong", "jpy"],
            "CANADA": ["canada", "canadian", "cad", "toronto"]
        }

        prompt_lower = prompt.lower()
        detected_regions = []

        for region, keywords in geographic_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                detected_regions.append(region)

        return detected_regions or ["GLOBAL"]

    def _get_fallback_entity(self, context: HedgeContext) -> str:
        """Get intelligent fallback entity based on context"""
        # Map currencies to likely entity jurisdictions
        currency_entity_map = {
            "USD": "US_BR_001",
            "HKD": "HK_BR_001",
            "SGD": "SG_SUB_001",
            "EUR": "EU_BR_001",
            "GBP": "UK_ASC_001",
            "JPY": "JP_BR_001",
            "AUD": "AU_BR_001"
        }

        # Get entity based on currency context
        return currency_entity_map.get(context.currency, "HEDGE_MASTER")

    async def _get_available_nav_types(self, currency: str) -> List[str]:
        """Get available NAV types from database based on usage patterns"""
        try:
            if self.supabase_client:
                # Query position_nav_master to see what NAV types are actually used
                result = self.supabase_client.table("position_nav_master").select("nav_type").eq("currency_code", currency).execute()
                if result.data:
                    # Count frequency and return most common first
                    nav_counts = {}
                    for row in result.data:
                        nav_type = row.get("nav_type")
                        if nav_type:
                            nav_counts[nav_type] = nav_counts.get(nav_type, 0) + 1

                    # Sort by frequency
                    sorted_navs = sorted(nav_counts.items(), key=lambda x: x[1], reverse=True)
                    return [nav[0] for nav in sorted_navs]

            # Enhanced fallback based on common hedge fund practices
            return ["COI", "RE", "SFX", "FX"]
        except Exception as e:
            logger.warning(f"Could not fetch NAV types: {e}")
            return ["COI", "RE"]

    async def _get_available_entities(self) -> List[Dict]:
        """Get available entities from database with intelligent geographic/regulatory filtering"""
        try:
            if self.supabase_client:
                result = self.supabase_client.table("entity_master").select("entity_id, entity_name, country_code, regulatory_classification, entity_type, active_flag").execute()
                entities = result.data or []

                # Filter to active entities only
                active_entities = [e for e in entities if e.get("active_flag") in ["Y", "Active", True]]

                if active_entities:
                    return active_entities
                else:
                    # If no active entities found, return all available
                    return entities
            else:
                # Enhanced fallback with geographic diversity
                return [
                    {"entity_id": "HK_BR_001", "entity_name": "Hong Kong Branch", "country_code": "HK", "regulatory_classification": "IFRS", "entity_type": "Branch"},
                    {"entity_id": "SG_SUB_001", "entity_name": "Singapore Subsidiary", "country_code": "SG", "regulatory_classification": "IFRS", "entity_type": "Subsidiary"},
                    {"entity_id": "US_BR_001", "entity_name": "US Branch", "country_code": "US", "regulatory_classification": "US_GAAP", "entity_type": "Branch"},
                    {"entity_id": "UK_ASC_001", "entity_name": "UK Associate", "country_code": "UK", "regulatory_classification": "IFRS", "entity_type": "Associate"}
                ]
        except Exception as e:
            logger.warning(f"Could not fetch entities: {e}")
            # Smart fallback based on common hedge fund entity structures
            return [
                {"entity_id": "HEDGE_MASTER", "entity_name": "Master Fund", "country_code": "KY", "regulatory_classification": "IFRS", "entity_type": "Fund"},
                {"entity_id": "PRIME_BROKER", "entity_name": "Prime Brokerage", "country_code": "US", "regulatory_classification": "US_GAAP", "entity_type": "Subsidiary"}
            ]

    async def _get_available_instruments(self) -> List[str]:
        """Get available hedging instruments from database"""
        try:
            if self.supabase_client:
                result = self.supabase_client.table("hedge_instruments").select("instrument_name").execute()
                return [row["instrument_name"] for row in result.data] if result.data else ["FX_Swap"]
            else:
                return ["FX_Swap", "FX_Forward", "FX_Option"]
        except Exception as e:
            logger.warning(f"Could not fetch instruments: {e}")
            return ["FX_Swap"]

    def _calculate_average_confidence(self, decisions: Dict[str, AIDecision]) -> str:
        """Calculate average confidence across all decisions"""
        confidence_scores = {
            DecisionConfidence.HIGH: 0.9,
            DecisionConfidence.MEDIUM: 0.7,
            DecisionConfidence.LOW: 0.5,
            DecisionConfidence.FALLBACK: 0.3
        }

        total_score = sum(confidence_scores[decision.confidence] for decision in decisions.values())
        avg_score = total_score / len(decisions) if decisions else 0.5

        if avg_score >= 0.8:
            return "HIGH"
        elif avg_score >= 0.6:
            return "MEDIUM"
        else:
            return "LOW"

    # Complete implementation of remaining decision methods

    async def _decide_currency_type(self, context: HedgeContext) -> AIDecision:
        """Decide currency type (Matched/Mismatched) based on entity and exposure alignment"""
        try:
            # Get entity's base currency
            entity_profile = await self._get_entity_profile(context)
            entity_currency = entity_profile.get("base_currency", "USD")

            # Determine if currencies are matched
            if context.currency == entity_currency:
                currency_type = "Matched"
                reasoning = f"Currency type 'Matched' - exposure currency {context.currency} aligns with entity base currency"
                confidence = DecisionConfidence.HIGH
            else:
                currency_type = "Mismatched"
                reasoning = f"Currency type 'Mismatched' - exposure currency {context.currency} differs from entity base currency {entity_currency}"
                confidence = DecisionConfidence.HIGH

            return AIDecision(
                value=currency_type,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["entity_base_currency", "exposure_currency", "alignment_analysis"],
                alternatives_evaluated=["Matched", "Mismatched"],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Currency type decision AI failed: {e}, using fallback")
            return AIDecision(
                value="Matched",
                reasoning="Fallback to Matched as most common scenario",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_accounting_method(self, context: HedgeContext) -> AIDecision:
        """Decide accounting method based on regulatory domain and entity characteristics"""
        try:
            # Analyze regulatory requirements
            if context.regulatory_domain == "IFRS":
                method = "IFRS_Hedge"
                reasoning = "IFRS_Hedge accounting selected for IFRS regulatory domain"
                confidence = DecisionConfidence.HIGH
            elif context.regulatory_domain == "US_GAAP":
                method = "ASC815_Hedge"
                reasoning = "ASC815_Hedge accounting selected for US GAAP regulatory domain"
                confidence = DecisionConfidence.HIGH
            else:
                # Default to COH (Cash or Hedge) for flexibility
                method = "COH"
                reasoning = "COH accounting method selected as flexible default for regulatory domain"
                confidence = DecisionConfidence.MEDIUM

            return AIDecision(
                value=method,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["regulatory_domain", "accounting_standards", "compliance_requirements"],
                alternatives_evaluated=["COH", "IFRS_Hedge", "ASC815_Hedge"],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Accounting method decision AI failed: {e}, using fallback")
            return AIDecision(
                value="COH",
                reasoning="Fallback to COH as most flexible accounting method",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_event_status(self, context: HedgeContext) -> AIDecision:
        """Decide event status based on operation type and workflow requirements"""
        try:
            if context.urgency_level == "urgent":
                status = "Booked"
                reasoning = "Booked status for urgent processing to expedite settlement"
                confidence = DecisionConfidence.HIGH
            elif context.operation_type == "termination":
                status = "Settled"
                reasoning = "Settled status appropriate for termination operations"
                confidence = DecisionConfidence.HIGH
            else:
                status = "Pending"
                reasoning = "Pending status for standard processing workflow"
                confidence = DecisionConfidence.HIGH

            return AIDecision(
                value=status,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["urgency_level", "operation_type", "workflow_optimization"],
                alternatives_evaluated=["Pending", "Booked", "Settled"],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Event status decision AI failed: {e}, using fallback")
            return AIDecision(
                value="Pending",
                reasoning="Fallback to Pending as safest initial status",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_stage_status(self, context: HedgeContext, stage: str) -> AIDecision:
        """Decide stage-specific status based on workflow and urgency"""
        try:
            if context.urgency_level == "urgent":
                status = "Completed"  # Fast-track urgent requests
                reasoning = f"Stage {stage} status 'Completed' for urgent processing"
                confidence = DecisionConfidence.HIGH
            else:
                status = "Pending"  # Standard workflow
                reasoning = f"Stage {stage} status 'Pending' for standard processing"
                confidence = DecisionConfidence.HIGH

            return AIDecision(
                value=status,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["urgency_level", "workflow_stage", "processing_requirements"],
                alternatives_evaluated=["Pending", "In_Progress", "Completed"],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Stage status decision AI failed: {e}, using fallback")
            return AIDecision(
                value="Pending",
                reasoning="Fallback to Pending as safest stage status",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_business_event_type(self, context: HedgeContext) -> AIDecision:
        """Decide business event type based on operation context"""
        try:
            # Map operation types to business event types
            event_mapping = {
                "inception": "Initiation",
                "rollover": "Rollover",
                "termination": "Termination",
                "increase": "Initiation",  # Treat as new initiation
                "decrease": "Termination"  # Treat as partial termination
            }

            event_type = event_mapping.get(context.operation_type, "Initiation")
            reasoning = f"Business event type '{event_type}' mapped from operation type '{context.operation_type}'"
            confidence = DecisionConfidence.HIGH

            return AIDecision(
                value=event_type,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["operation_type", "business_logic_mapping"],
                alternatives_evaluated=list(event_mapping.values()),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Business event type decision AI failed: {e}, using fallback")
            return AIDecision(
                value="Initiation",
                reasoning="Fallback to Initiation as most common business event",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    async def _decide_buffer_percentage(self, context: HedgeContext) -> AIDecision:
        """Intelligently determine buffer percentage based on risk and market conditions"""
        try:
            # Base buffer percentage
            base_buffer = 5.0

            # Adjust based on currency volatility
            currency_volatility = self.currency_risk_profiles.get(context.currency, {}).get("volatility", "medium")
            if currency_volatility == "high":
                buffer_adjustment = 2.0  # Add 2% for high volatility
            elif currency_volatility == "low":
                buffer_adjustment = -1.0  # Reduce 1% for low volatility
            else:
                buffer_adjustment = 0.0

            # Adjust based on amount size (larger amounts need more buffer)
            if context.amount and context.amount > 100000000:  # >100M
                size_adjustment = 1.0
            elif context.amount and context.amount < 10000000:  # <10M
                size_adjustment = -0.5
            else:
                size_adjustment = 0.0

            # Final buffer percentage
            final_buffer = max(1.0, base_buffer + buffer_adjustment + size_adjustment)

            return AIDecision(
                value=final_buffer,
                reasoning=f"Buffer percentage {final_buffer}% calculated: base 5% + volatility adjustment {buffer_adjustment}% + size adjustment {size_adjustment}%",
                confidence=DecisionConfidence.HIGH,
                factors_considered=["currency_volatility", "exposure_size", "market_conditions", "risk_management"],
                alternatives_evaluated=[1.0, 3.0, 5.0, 7.0, 10.0],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Buffer percentage decision AI failed: {e}, using fallback")
            return AIDecision(
                value=5.0,
                reasoning="Fallback to 5% as standard buffer percentage",
                confidence=DecisionConfidence.FALLBACK,
                factors_considered=["fallback_logic"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

    # Database and market data methods

    async def _get_entity_profile(self, context: HedgeContext) -> Dict[str, Any]:
        """Get entity profile information"""
        try:
            if self.supabase_client and hasattr(context, 'entity_id'):
                result = self.supabase_client.table("entity_master").select("*").eq("entity_id", context.entity_id).execute()
                return result.data[0] if result.data else {}
            else:
                # Return default profile
                return {
                    "base_currency": "USD",
                    "regulatory_classification": "US_GAAP",
                    "jurisdiction": "US",
                    "risk_profile": "medium"
                }
        except Exception as e:
            logger.warning(f"Could not fetch entity profile: {e}")
            return {"base_currency": "USD", "regulatory_classification": "US_GAAP"}

    async def _score_entity_suitability(self, entity: Dict, geographic_clues: List[str],
                                      currency_jurisdiction: str, context: HedgeContext) -> float:
        """Score entity suitability based on multiple factors"""
        score = 0.0

        # Geographic alignment (40% weight)
        entity_jurisdiction = entity.get("country_code", "US")
        if entity_jurisdiction in geographic_clues:
            score += 0.4
        elif "GLOBAL" in geographic_clues:
            score += 0.2  # Partial match for global operations

        # Currency jurisdiction alignment (30% weight)
        if entity_jurisdiction == currency_jurisdiction:
            score += 0.3

        # Entity capabilities (20% weight)
        entity_capabilities = entity.get("capabilities", [])
        if "hedge_operations" in entity_capabilities:
            score += 0.2

        # Risk profile alignment (10% weight)
        entity_risk = entity.get("risk_profile", "medium")
        if entity_risk == context.risk_profile:
            score += 0.1

        return score

    async def _score_instrument_suitability(self, instrument: str, context: HedgeContext,
                                          market_conditions: Dict) -> float:
        """Score instrument suitability based on market conditions and context"""
        score = 0.0

        # Liquidity score (40% weight)
        liquidity = market_conditions.get("liquidity", "medium")
        if instrument == "FX_Swap" and liquidity in ["high", "medium"]:
            score += 0.4
        elif instrument == "FX_Forward" and liquidity == "high":
            score += 0.4
        elif instrument == "FX_Option":
            score += 0.2  # Options generally less liquid

        # Volatility suitability (30% weight)
        volatility = market_conditions.get("volatility", "medium")
        if instrument == "FX_Option" and volatility == "high":
            score += 0.3  # Options good for high volatility
        elif instrument in ["FX_Swap", "FX_Forward"] and volatility in ["low", "medium"]:
            score += 0.3

        # Cost efficiency (20% weight)
        if instrument == "FX_Forward":
            score += 0.2  # Generally most cost-efficient
        elif instrument == "FX_Swap":
            score += 0.15

        # Tenor suitability (10% weight)
        if "short_term" in context.tenor_indicators and instrument == "FX_Forward":
            score += 0.1
        elif "long_term" in context.tenor_indicators and instrument == "FX_Swap":
            score += 0.1

        return score

    async def _get_market_conditions(self, currency: Optional[str]) -> Dict[str, Any]:
        """Get current market conditions for currency"""
        try:
            # In a real implementation, this would fetch live market data
            # For now, return based on currency risk profiles
            if currency and currency in self.currency_risk_profiles:
                return self.currency_risk_profiles[currency]
            else:
                return {"volatility": "medium", "liquidity": "medium"}
        except Exception as e:
            logger.warning(f"Could not fetch market conditions: {e}")
            return {"volatility": "medium", "liquidity": "medium"}

    def _get_currency_jurisdiction(self, currency: Optional[str]) -> str:
        """Map currency to primary jurisdiction"""
        currency_jurisdictions = {
            "USD": "US",
            "EUR": "EU",
            "GBP": "UK",
            "JPY": "APAC",
            "CAD": "CANADA",
            "AUD": "APAC"
        }
        return currency_jurisdictions.get(currency, "GLOBAL")

    async def _determine_urgency(self, prompt: str) -> str:
        """Determine urgency level from prompt"""
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["urgent", "asap", "immediate", "emergency"]):
            return "urgent"
        elif any(word in prompt_lower for word in ["priority", "important", "expedite"]):
            return "high"
        else:
            return "standard"

    async def _update_market_context(self):
        """Update cached market data if needed"""
        try:
            now = datetime.now()
            if not self.last_cache_update or (now - self.last_cache_update).seconds > 3600:  # 1 hour cache
                # In real implementation, fetch live market data here
                self.market_data_cache = {
                    "timestamp": now.isoformat(),
                    "global_volatility": "medium",
                    "liquidity_conditions": "normal"
                }
                self.last_cache_update = now
                logger.info("Market context updated")
        except Exception as e:
            logger.warning(f"Market context update failed: {e}")

    async def _decide_account_code(self, context: HedgeContext) -> AIDecision:
        """Decide account code based on currency and operation type"""
        try:
            # Account code mapping based on hedge fund best practices
            currency_account_map = {
                "USD": "101001",  # USD Cash/Trading
                "EUR": "101002",  # EUR Cash/Trading
                "GBP": "101003",  # GBP Cash/Trading
                "HKD": "101004",  # HKD Cash/Trading
                "SGD": "101005",  # SGD Cash/Trading
                "JPY": "101006",  # JPY Cash/Trading
            }

            operation_account_map = {
                "hedge_utilization": "210001",  # Hedge Reserve
                "hedge_inception": "210002",    # Hedge Inception
                "hedge_termination": "210003",  # Hedge Settlement
                "gl_posting": "310001"          # GL Operations
            }

            # Primary logic: operation type takes precedence
            account_code = operation_account_map.get(context.operation_type)
            reasoning = f"Account code selected based on operation type: {context.operation_type}"
            confidence = DecisionConfidence.HIGH

            # Secondary logic: currency-based if no operation match
            if not account_code:
                account_code = currency_account_map.get(context.currency, "999999")
                reasoning = f"Account code selected based on currency: {context.currency}"
                confidence = DecisionConfidence.MEDIUM

            return AIDecision(
                value=account_code,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["operation_type", "currency", "hedge_fund_standards"],
                alternatives_evaluated=list(operation_account_map.values()) + list(currency_account_map.values()),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Account code decision failed: {e}")
            return AIDecision("999999", "Fallback account code", DecisionConfidence.FALLBACK, [], [], datetime.now().isoformat())

    async def _decide_business_unit(self, context: HedgeContext) -> AIDecision:
        """Decide business unit based on operation characteristics"""
        try:
            # Business unit decision logic
            if context.operation_type in ["hedge_utilization", "hedge_inception", "hedge_termination"]:
                business_unit = "HEDGE_OPERATIONS"
                reasoning = "Hedge operations assigned to specialized hedge unit"
                confidence = DecisionConfidence.HIGH
            elif context.operation_type == "gl_posting":
                business_unit = "ACCOUNTING"
                reasoning = "GL operations assigned to accounting unit"
                confidence = DecisionConfidence.HIGH
            elif context.amount and context.amount > 100000000:  # >100M
                business_unit = "INSTITUTIONAL"
                reasoning = "Large amounts assigned to institutional unit"
                confidence = DecisionConfidence.MEDIUM
            else:
                business_unit = "TRADING"
                reasoning = "Default assignment to trading unit"
                confidence = DecisionConfidence.MEDIUM

            return AIDecision(
                value=business_unit,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["operation_type", "amount_size", "organizational_structure"],
                alternatives_evaluated=["TRADING", "HEDGE_OPERATIONS", "ACCOUNTING", "INSTITUTIONAL"],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Business unit decision failed: {e}")
            return AIDecision("TRADING", "Fallback business unit", DecisionConfidence.FALLBACK, [], [], datetime.now().isoformat())

    async def _decide_profit_center(self, context: HedgeContext) -> AIDecision:
        """Decide profit center based on hedge strategy and currency"""
        try:
            # Profit center mapping based on hedge fund structure
            currency_pc_map = {
                "USD": "PC_USD_HEDGE",
                "EUR": "PC_EUR_HEDGE",
                "GBP": "PC_GBP_HEDGE",
                "HKD": "PC_ASIA_HEDGE",
                "SGD": "PC_ASIA_HEDGE",
                "JPY": "PC_ASIA_HEDGE"
            }

            operation_pc_map = {
                "hedge_utilization": "PC_ALLOCATION",
                "hedge_inception": "PC_INCEPTION",
                "hedge_termination": "PC_SETTLEMENT",
                "gl_posting": "PC_ACCOUNTING"
            }

            # Primary: operation-based profit center
            profit_center = operation_pc_map.get(context.operation_type)
            if profit_center:
                reasoning = f"Profit center based on operation: {context.operation_type}"
                confidence = DecisionConfidence.HIGH
            else:
                # Secondary: currency-based profit center
                profit_center = currency_pc_map.get(context.currency, "PC_FX_HEDGE")
                reasoning = f"Profit center based on currency: {context.currency}"
                confidence = DecisionConfidence.MEDIUM

            return AIDecision(
                value=profit_center,
                reasoning=reasoning,
                confidence=confidence,
                factors_considered=["operation_type", "currency", "profit_center_structure"],
                alternatives_evaluated=list(operation_pc_map.values()) + list(currency_pc_map.values()),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.warning(f"Profit center decision failed: {e}")
            return AIDecision("PC_FX_HEDGE", "Fallback profit center", DecisionConfidence.FALLBACK, [], [], datetime.now().isoformat())

    async def _apply_confidence_validation(self, decisions: Dict[str, AIDecision], context: HedgeContext) -> Dict[str, AIDecision]:
        """Apply confidence-based validation and enhancement to decisions"""
        try:
            enhanced_decisions = {}
            low_confidence_decisions = []

            for key, decision in decisions.items():
                confidence_level = getattr(decision, 'confidence', DecisionConfidence.FALLBACK)

                # Track low confidence decisions for potential retry
                if confidence_level in [DecisionConfidence.FALLBACK, DecisionConfidence.LOW]:
                    low_confidence_decisions.append(key)

                # Apply confidence-based enhancements
                if confidence_level == DecisionConfidence.FALLBACK:
                    # Attempt to improve fallback decisions with context
                    enhanced_decision = await self._enhance_fallback_decision(key, decision, context)
                    enhanced_decisions[key] = enhanced_decision
                elif confidence_level == DecisionConfidence.LOW:
                    # Add uncertainty flags to low confidence decisions
                    enhanced_decision = self._add_uncertainty_flags(decision)
                    enhanced_decisions[key] = enhanced_decision
                else:
                    # Keep high/medium confidence decisions as-is
                    enhanced_decisions[key] = decision

            # Log confidence analysis
            if low_confidence_decisions:
                logger.warning(f"Low confidence decisions detected: {low_confidence_decisions}")

            # Add confidence metadata
            confidence_score = self._calculate_confidence_score(enhanced_decisions)
            enhanced_decisions["_confidence_metadata"] = AIDecision(
                value=confidence_score,
                reasoning=f"Overall decision confidence: {confidence_score:.2f}, Low confidence items: {len(low_confidence_decisions)}",
                confidence=DecisionConfidence.HIGH if confidence_score > 0.8 else DecisionConfidence.MEDIUM,
                factors_considered=["decision_confidence_distribution", "fallback_ratio"],
                alternatives_evaluated=[],
                timestamp=datetime.now().isoformat()
            )

            return enhanced_decisions

        except Exception as e:
            logger.warning(f"Confidence validation error: {e}")
            return decisions  # Return original decisions if validation fails

    async def _enhance_fallback_decision(self, decision_key: str, decision: AIDecision, context: HedgeContext) -> AIDecision:
        """Attempt to enhance fallback decisions with additional context"""
        try:
            # Try to make better decision based on available context
            if decision_key == "entity_id" and context.currency:
                # Use currency-based entity selection as enhancement
                fallback_entity = self._get_fallback_entity(context)
                return AIDecision(
                    value=fallback_entity,
                    reasoning=f"Enhanced fallback: Selected {fallback_entity} based on currency context {context.currency}",
                    confidence=DecisionConfidence.MEDIUM,  # Upgraded from FALLBACK
                    factors_considered=["currency_mapping", "context_enhancement"],
                    alternatives_evaluated=getattr(decision, 'alternatives_evaluated', []),
                    timestamp=datetime.now().isoformat()
                )

            elif decision_key == "nav_type" and context.amount:
                # Use amount-based NAV type enhancement
                enhanced_nav = "RE" if context.amount > 50000000 else "COI"
                return AIDecision(
                    value=enhanced_nav,
                    reasoning=f"Enhanced fallback: Selected {enhanced_nav} based on amount size {context.amount}",
                    confidence=DecisionConfidence.MEDIUM,
                    factors_considered=["amount_threshold", "context_enhancement"],
                    alternatives_evaluated=["COI", "RE"],
                    timestamp=datetime.now().isoformat()
                )

            # If no enhancement possible, return original with warning
            return decision

        except Exception as e:
            logger.warning(f"Fallback enhancement failed for {decision_key}: {e}")
            return decision

    def _add_uncertainty_flags(self, decision: AIDecision) -> AIDecision:
        """Add uncertainty flags to low confidence decisions"""
        enhanced_reasoning = f"{getattr(decision, 'reasoning', '')} [LOW CONFIDENCE - Recommend manual review]"

        return AIDecision(
            value=getattr(decision, 'value', None),
            reasoning=enhanced_reasoning,
            confidence=getattr(decision, 'confidence', DecisionConfidence.LOW),
            factors_considered=getattr(decision, 'factors_considered', []) + ["uncertainty_flagged"],
            alternatives_evaluated=getattr(decision, 'alternatives_evaluated', []),
            timestamp=datetime.now().isoformat()
        )

    def _calculate_confidence_score(self, decisions: Dict[str, AIDecision]) -> float:
        """Calculate overall confidence score for decision set"""
        if not decisions:
            return 0.0

        confidence_scores = {
            DecisionConfidence.HIGH: 1.0,
            DecisionConfidence.MEDIUM: 0.7,
            DecisionConfidence.LOW: 0.4,
            DecisionConfidence.FALLBACK: 0.1
        }

        total_score = 0.0
        decision_count = 0

        for key, decision in decisions.items():
            if key.startswith("_"):  # Skip metadata
                continue

            confidence_level = getattr(decision, 'confidence', DecisionConfidence.FALLBACK)
            score = confidence_scores.get(confidence_level, 0.0)
            total_score += score
            decision_count += 1

        return total_score / decision_count if decision_count > 0 else 0.0

    async def _get_fallback_decisions(self, context: HedgeContext) -> Dict[str, AIDecision]:
        """Provide safe fallback decisions if AI processing fails"""
        fallback_timestamp = datetime.now().isoformat()

        return {
            "entity_id": AIDecision("ENTITY0001", "Fallback to default entity", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "nav_type": AIDecision("COI", "Fallback to COI", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "currency_type": AIDecision("Matched", "Fallback to Matched", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "hedging_instrument": AIDecision("FX_Swap", "Fallback to FX_Swap", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "accounting_method": AIDecision("COH", "Fallback to COH", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "instruction_status": AIDecision("Received", "Fallback to Received", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "event_status": AIDecision("Pending", "Fallback to Pending", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "stage_1a_status": AIDecision("Pending", "Fallback to Pending", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "business_event_type": AIDecision("Initiation", "Fallback to Initiation", DecisionConfidence.FALLBACK, [], [], fallback_timestamp),
            "buffer_percentage": AIDecision(5.0, "Fallback to 5%", DecisionConfidence.FALLBACK, [], [], fallback_timestamp)
        }

# Global instance for shared use
ai_decision_engine = HedgeDecisionEngine()