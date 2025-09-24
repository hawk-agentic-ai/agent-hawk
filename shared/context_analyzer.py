"""
Context Analyzer for HAWK Hedge Operations
Extracts business context from natural language prompts for AI decision making
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ExtractedContext:
    """Extracted business context from user prompt"""
    currencies: List[str]
    amounts: List[float]
    geographic_indicators: List[str]
    urgency_signals: List[str]
    operation_types: List[str]
    temporal_indicators: List[str]
    risk_signals: List[str]
    entity_hints: List[str]
    confidence_score: float

class ContextAnalyzer:
    """
    Analyzes natural language prompts to extract business context
    for intelligent hedge operation decision making
    """

    def __init__(self):
        # Currency patterns and aliases
        self.currency_patterns = {
            "USD": ["usd", "dollar", "dollars", "\\$", "us dollar", "american dollar"],
            "EUR": ["eur", "euro", "euros", "€", "european"],
            "GBP": ["gbp", "pound", "pounds", "£", "sterling", "british pound"],
            "JPY": ["jpy", "yen", "¥", "japanese yen"],
            "CAD": ["cad", "canadian dollar", "canadian"],
            "AUD": ["aud", "australian dollar", "aussie"],
            "CHF": ["chf", "swiss franc", "swiss"],
            "SEK": ["sek", "swedish krona", "swedish"],
            "NOK": ["nok", "norwegian krone", "norwegian"]
        }

        # Geographic indicators
        self.geographic_patterns = {
            "US": ["america", "american", "usa", "united states", "new york", "chicago"],
            "UK": ["britain", "british", "england", "london", "uk"],
            "EU": ["europe", "european", "germany", "german", "france", "french", "italy", "spain"],
            "APAC": ["asia", "asian", "japan", "japanese", "singapore", "hong kong", "australia"],
            "CANADA": ["canada", "canadian", "toronto"],
            "NORDIC": ["sweden", "norway", "denmark", "finland", "nordic"]
        }

        # Operation type indicators
        self.operation_patterns = {
            "inception": ["create", "new", "initiate", "start", "begin", "inception", "establish"],
            "rollover": ["rollover", "roll", "extend", "renew", "continue"],
            "termination": ["terminate", "close", "end", "cancel", "stop", "unwind"],
            "increase": ["increase", "add", "expand", "boost", "enhance"],
            "decrease": ["reduce", "decrease", "lower", "cut", "trim"]
        }

        # Urgency indicators
        self.urgency_patterns = {
            "urgent": ["urgent", "asap", "immediate", "emergency", "critical", "rush"],
            "high": ["priority", "important", "expedite", "fast", "quick"],
            "standard": ["normal", "regular", "standard", "routine"],
            "low": ["when convenient", "no rush", "flexible", "low priority"]
        }

        # Risk level indicators
        self.risk_patterns = {
            "high": ["high risk", "volatile", "risky", "aggressive", "maximum"],
            "medium": ["moderate", "balanced", "standard risk", "medium"],
            "low": ["conservative", "safe", "low risk", "minimal", "cautious"]
        }

        # Temporal indicators
        self.temporal_patterns = {
            "immediate": ["today", "now", "immediate", "asap"],
            "short_term": ["this week", "weekly", "short term", "days"],
            "monthly": ["monthly", "month", "quarterly", "quarter"],
            "long_term": ["annual", "yearly", "long term", "permanent"]
        }

        # Amount extraction patterns
        self.amount_patterns = [
            r'(\d+(?:\.\d+)?)\s*([mk]?)\s*(?:million|mil|m)\b',  # 5M, 10.5 million
            r'(\d+(?:\.\d+)?)\s*([bk]?)\s*(?:billion|bil|b)\b',  # 1B, 2.5 billion
            r'(\d+(?:\.\d+)?)\s*k\b',  # 500k
            r'(\d+(?:,\d{3})*(?:\.\d+)?)',  # 1,000,000 or 1000000
        ]

        logger.info("Context Analyzer initialized")

    async def analyze_prompt(self, user_prompt: str, currency: Optional[str] = None,
                           amount: Optional[float] = None) -> ExtractedContext:
        """
        Analyze user prompt to extract all relevant business context
        """
        try:
            logger.info(f"Analyzing prompt: {user_prompt[:100]}...")

            prompt_lower = user_prompt.lower()

            # Extract different types of context
            currencies = self._extract_currencies(prompt_lower, currency)
            amounts = self._extract_amounts(prompt_lower, amount)
            geographic_indicators = self._extract_geographic_context(prompt_lower)
            urgency_signals = self._extract_urgency_signals(prompt_lower)
            operation_types = self._extract_operation_types(prompt_lower)
            temporal_indicators = self._extract_temporal_indicators(prompt_lower)
            risk_signals = self._extract_risk_signals(prompt_lower)
            entity_hints = self._extract_entity_hints(prompt_lower)

            # Calculate confidence score based on extracted information
            confidence_score = self._calculate_confidence_score(
                currencies, amounts, geographic_indicators, urgency_signals, operation_types
            )

            context = ExtractedContext(
                currencies=currencies,
                amounts=amounts,
                geographic_indicators=geographic_indicators,
                urgency_signals=urgency_signals,
                operation_types=operation_types,
                temporal_indicators=temporal_indicators,
                risk_signals=risk_signals,
                entity_hints=entity_hints,
                confidence_score=confidence_score
            )

            logger.info(f"Context extraction completed with confidence: {confidence_score:.2f}")
            return context

        except Exception as e:
            logger.error(f"Context analysis error: {e}")
            # Return minimal context with fallback values
            return ExtractedContext(
                currencies=[currency] if currency else ["USD"],
                amounts=[amount] if amount else [1000000],
                geographic_indicators=["GLOBAL"],
                urgency_signals=["standard"],
                operation_types=["inception"],
                temporal_indicators=["immediate"],
                risk_signals=["medium"],
                entity_hints=[],
                confidence_score=0.3
            )

    def _extract_currencies(self, prompt: str, override_currency: Optional[str] = None) -> List[str]:
        """Extract currency indicators from prompt"""
        if override_currency:
            return [override_currency.upper()]

        detected_currencies = []

        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{re.escape(pattern)}\b', prompt, re.IGNORECASE):
                    if currency not in detected_currencies:
                        detected_currencies.append(currency)

        return detected_currencies or self._get_intelligent_currency_default(prompt)  # Intelligent default

    def _extract_amounts(self, prompt: str, override_amount: Optional[float] = None) -> List[float]:
        """Extract monetary amounts from prompt"""
        if override_amount:
            return [override_amount]

        amounts = []

        for pattern in self.amount_patterns:
            matches = re.finditer(pattern, prompt, re.IGNORECASE)
            for match in matches:
                try:
                    # Parse the amount
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)

                    # Apply multipliers
                    if 'million' in prompt[match.start():match.end()+20].lower() or 'm' in match.group().lower():
                        amount *= 1000000
                    elif 'billion' in prompt[match.start():match.end()+20].lower() or 'b' in match.group().lower():
                        amount *= 1000000000
                    elif 'k' in match.group().lower():
                        amount *= 1000

                    amounts.append(amount)

                except (ValueError, AttributeError):
                    continue

        return amounts or [1000000]  # Default 1M if none found

    def _extract_geographic_context(self, prompt: str) -> List[str]:
        """Extract geographic/jurisdictional context"""
        detected_regions = []

        for region, patterns in self.geographic_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{re.escape(pattern)}\b', prompt, re.IGNORECASE):
                    if region not in detected_regions:
                        detected_regions.append(region)

        return detected_regions or ["GLOBAL"]

    def _extract_urgency_signals(self, prompt: str) -> List[str]:
        """Extract urgency level indicators"""
        detected_urgency = []

        for urgency, patterns in self.urgency_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{re.escape(pattern)}\b', prompt, re.IGNORECASE):
                    if urgency not in detected_urgency:
                        detected_urgency.append(urgency)

        # Return highest urgency found, or standard as default
        if "urgent" in detected_urgency:
            return ["urgent"]
        elif "high" in detected_urgency:
            return ["high"]
        elif "low" in detected_urgency:
            return ["low"]
        else:
            return ["standard"]

    def _extract_operation_types(self, prompt: str) -> List[str]:
        """Extract operation type indicators"""
        detected_operations = []

        for operation, patterns in self.operation_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{re.escape(pattern)}\b', prompt, re.IGNORECASE):
                    if operation not in detected_operations:
                        detected_operations.append(operation)

        return detected_operations or ["inception"]  # Default to inception

    def _extract_temporal_indicators(self, prompt: str) -> List[str]:
        """Extract temporal/timing indicators"""
        detected_temporal = []

        for temporal, patterns in self.temporal_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{re.escape(pattern)}\b', prompt, re.IGNORECASE):
                    if temporal not in detected_temporal:
                        detected_temporal.append(temporal)

        return detected_temporal or ["immediate"]

    def _extract_risk_signals(self, prompt: str) -> List[str]:
        """Extract risk level indicators"""
        detected_risk = []

        for risk, patterns in self.risk_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{re.escape(pattern)}\b', prompt, re.IGNORECASE):
                    if risk not in detected_risk:
                        detected_risk.append(risk)

        return detected_risk or ["medium"]  # Default to medium risk

    def _extract_entity_hints(self, prompt: str) -> List[str]:
        """Extract entity-specific hints"""
        entity_hints = []

        # Look for subsidiary indicators
        subsidiary_patterns = ["subsidiary", "division", "branch", "office", "entity"]
        for pattern in subsidiary_patterns:
            if pattern in prompt:
                entity_hints.append("subsidiary_indicated")

        # Look for specific entity mentions
        entity_patterns = [r'entity\s*(\d+)', r'fund\s*(\w+)', r'portfolio\s*(\w+)']
        for pattern in entity_patterns:
            matches = re.finditer(pattern, prompt, re.IGNORECASE)
            for match in matches:
                entity_hints.append(f"specific_entity_{match.group(1)}")

        return entity_hints

    def _calculate_confidence_score(self, currencies: List[str], amounts: List[float],
                                  geographic_indicators: List[str], urgency_signals: List[str],
                                  operation_types: List[str]) -> float:
        """Calculate confidence score based on extracted context completeness"""
        score = 0.0

        # Base score for having any information
        if currencies:
            score += 0.2
        if amounts:
            score += 0.2
        if geographic_indicators and geographic_indicators != ["GLOBAL"]:
            score += 0.2
        if urgency_signals and urgency_signals != ["standard"]:
            score += 0.1
        if operation_types and operation_types != ["inception"]:
            score += 0.2

        # Bonus for specific details
        if len(currencies) == 1:  # Single clear currency
            score += 0.1
        if amounts and any(amt > 0 for amt in amounts):  # Specific amounts
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    async def create_hedge_context(self, user_prompt: str, currency: Optional[str] = None,
                                 amount: Optional[float] = None) -> 'HedgeContext':
        """
        Create HedgeContext object from analyzed prompt
        """
        from .ai_decision_engine import HedgeContext

        extracted = await self.analyze_prompt(user_prompt, currency, amount)

        return HedgeContext(
            user_prompt=user_prompt,
            currency=extracted.currencies[0] if extracted.currencies else currency,
            amount=extracted.amounts[0] if extracted.amounts else amount,
            geographic_indicators=extracted.geographic_indicators,
            urgency_level=extracted.urgency_signals[0] if extracted.urgency_signals else "standard",
            operation_type=extracted.operation_types[0] if extracted.operation_types else "inception",
            risk_profile=extracted.risk_signals[0] if extracted.risk_signals else "medium",
            regulatory_domain=self._map_geographic_to_regulatory(extracted.geographic_indicators),
            tenor_indicators=extracted.temporal_indicators,
            market_conditions={}  # Will be populated by market data provider
        )

    def _map_geographic_to_regulatory(self, geographic_indicators: List[str]) -> str:
        """Map geographic context to regulatory domain"""
        if "US" in geographic_indicators:
            return "US_GAAP"
        elif any(region in geographic_indicators for region in ["UK", "EU"]):
            return "IFRS"
        elif "APAC" in geographic_indicators:
            return "ASIA_PACIFIC"
        else:
            return "GLOBAL"

    def _get_intelligent_currency_default(self, prompt: str) -> List[str]:
        """Get intelligent currency default based on context clues"""
        prompt_lower = prompt.lower()

        # Geographic currency mapping
        region_currency_map = {
            "hong kong": ["HKD"],
            "singapore": ["SGD"],
            "japan": ["JPY"],
            "europe": ["EUR"],
            "uk": ["GBP"],
            "australia": ["AUD"],
            "canada": ["CAD"],
            "asia": ["HKD", "SGD", "JPY"],  # Common Asian hedge currencies
            "americas": ["USD", "CAD"],
            "us": ["USD"],
            "united states": ["USD"]
        }

        # Check for geographic clues in prompt
        for region, currencies in region_currency_map.items():
            if region in prompt_lower:
                return currencies

        # Business context clues
        if any(term in prompt_lower for term in ["g3", "major", "liquid"]):
            return ["USD"]  # G3 currencies often default to USD

        if any(term in prompt_lower for term in ["emerging", "asian", "apac"]):
            return ["HKD"]  # Asian hedge funds often use HKD

        # Default fallback based on hedge fund industry standards
        return ["USD"]  # USD remains most common in hedge funds

# Global instance for shared use
context_analyzer = ContextAnalyzer()