"""
Shared Business Logic - Core components for FastAPI and MCP server integration
Contains PromptIntelligenceEngine and SmartDataExtractor for shared use
Extracted from prompt_intelligence_engine.py and smart_data_extractor.py
"""

import re
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, date
from collections import defaultdict

class PromptIntent(Enum):
    """All supported prompt intent categories"""
    # Hedge Instructions
    HEDGE_INCEPTION = "hedge_inception"
    HEDGE_UTILIZATION = "hedge_utilization"  
    HEDGE_ROLLOVER = "hedge_rollover"
    HEDGE_TERMINATION = "hedge_termination"
    HEDGE_AMENDMENT = "hedge_amendment"
    HEDGE_INQUIRY = "hedge_inquiry"
    
    # Risk Analysis
    RISK_ANALYSIS = "risk_analysis"
    VAR_CALCULATION = "var_calculation"
    STRESS_TEST = "stress_test"
    CORRELATION_ANALYSIS = "correlation_analysis"
    
    # Compliance & Regulatory
    COMPLIANCE_REPORT = "compliance_report"
    REGULATORY_REPORT = "regulatory_report"
    THRESHOLD_MONITORING = "threshold_monitoring"
    AUDIT_TRAIL = "audit_trail"
    
    # Performance Analysis
    PERFORMANCE_METRICS = "performance_metrics"
    HEDGE_EFFECTIVENESS = "hedge_effectiveness"
    PNL_ATTRIBUTION = "pnl_attribution"
    PERFORMANCE_COMPARISON = "performance_comparison"
    
    # Monitoring & Status
    POSITION_MONITORING = "position_monitoring"
    EXPOSURE_ANALYSIS = "exposure_analysis"
    PORTFOLIO_STATUS = "portfolio_status"
    SYSTEM_STATUS = "system_status"
    
    # New instruction types from CSV analysis
    HEDGE_MONITORING = "hedge_monitoring"     # MONITOR type
    MX_BOOKINGS = "mx_bookings"               # MX Bookings type  
    GL_ENTRIES_QUERY = "gl_entries_query"     # GL Entries type
    GENERAL_PORTFOLIO = "general_portfolio"   # General/Others type
    
    # General Analysis
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    MARKET_ANALYSIS = "market_analysis"
    GENERAL_QUERY = "general_query"

@dataclass
class PromptAnalysisResult:
    """Result of prompt analysis"""
    intent: PromptIntent
    confidence: float
    required_tables: List[str]
    extracted_params: Dict[str, Any]
    instruction_type: Optional[str] = None
    data_scope: str = "targeted"  # "targeted" | "comprehensive" | "minimal"

class PromptIntelligenceEngine:
    """Analyzes prompts and determines required data extraction strategy"""
    
    def __init__(self):
        self.setup_intent_patterns()
        self.setup_table_mappings()
        self.setup_parameter_extractors()
    
    def setup_intent_patterns(self):
        """Define regex patterns for intent recognition"""
        self.intent_patterns = {
            # Hedge Instructions
            PromptIntent.HEDGE_UTILIZATION: [
                r'(?i)(check|can I|available|capacity|utilize|hedge today)',
                r'(?i)(utilization|utilisation|available.*hedge|hedge.*capacity)',
                r'(?i)(execute.*utilization|process.*utilization|run.*utilization)',
                r'(?i)(utilization.*check|hedge.*utilization|allocation.*check)',
                r'(?i)(150k|[0-9]+[km]?)\s+(?:cny|usd|eur|gbp|jpy|twd|aud|hkd)\s+(?:today|now|check|utilization)'
            ],
            PromptIntent.HEDGE_INCEPTION: [
                r'(?i)(start|create|initiate|begin|new).*hedge',
                r'(?i)(inception|new.*position|establish.*hedge)',
                r'(?i)(hedge.*inception|start.*hedge.*position)'
            ],
            PromptIntent.HEDGE_ROLLOVER: [
                r'(?i)(rollover|roll.*over|extend|renew).*hedge',
                r'(?i)(extend.*maturity|renew.*position)',
                r'(?i)(rollover.*existing|modify.*existing.*hedge)'
            ],
            PromptIntent.HEDGE_TERMINATION: [
                r'(?i)(terminate|close|end|maturity).*hedge',
                r'(?i)(termination|closure|settlement)',
                r'(?i)(close.*position|settle.*hedge|mature.*hedge)'
            ],
            PromptIntent.HEDGE_AMENDMENT: [
                r'(?i)(amend|modify|change|update).*order',
                r'(?i)(amendment|modification|change.*notional)',
                r'(?i)(order.*ord-[0-9]+|previous.*ord-[0-9]+)'
            ],
            PromptIntent.HEDGE_INQUIRY: [
                r'(?i)(status|check.*status|inquiry|query)',
                r'(?i)(what.*status|how.*doing|current.*state)',
                r'(?i)(status.*instruction|check.*hedge.*status)'
            ],
            
            # Risk Analysis
            PromptIntent.VAR_CALCULATION: [
                r'(?i)(var|value.*at.*risk|calculate.*var)',
                r'(?i)(risk.*metric|downside.*risk|portfolio.*var)',
                r'(?i)(95%|99%|confidence.*level)'
            ],
            PromptIntent.STRESS_TEST: [
                r'(?i)(stress.*test|scenario.*analysis|shock.*test)',
                r'(?i)(stress.*scenario|market.*shock|crisis.*scenario)',
                r'(?i)(stress.*against|test.*scenario)'
            ],
            PromptIntent.CORRELATION_ANALYSIS: [
                r'(?i)(correlation|correl.*between|relationship.*between)',
                r'(?i)(correlation.*analysis|correlation.*matrix)',
                r'(?i)(how.*related|correlation.*coefficient)'
            ],
            
            # Compliance
            PromptIntent.COMPLIANCE_REPORT: [
                r'(?i)(compliance|regulatory.*report|compliance.*check)',
                r'(?i)(generate.*compliance|monthly.*compliance|quarterly.*report)',
                r'(?i)(compliance.*status|regulatory.*status)'
            ],
            PromptIntent.THRESHOLD_MONITORING: [
                r'(?i)(threshold|limit|breach|violation)',
                r'(?i)(threshold.*monitoring|limit.*monitoring|breach.*alert)',
                r'(?i)(exceeded.*threshold|above.*limit)'
            ],
            PromptIntent.AUDIT_TRAIL: [
                r'(?i)(audit|audit.*trail|transaction.*history)',
                r'(?i)(who.*changed|when.*modified|change.*history)',
                r'(?i)(audit.*log|transaction.*log)'
            ],
            
            # Performance
            PromptIntent.PERFORMANCE_METRICS: [
                r'(?i)(performance|return|metrics|kpi)',
                r'(?i)(performance.*metric|return.*metric|fund.*performance)',
                r'(?i)(how.*performing|performance.*summary)'
            ],
            PromptIntent.HEDGE_EFFECTIVENESS: [
                r'(?i)(effectiveness|effective|hedge.*performance)',
                r'(?i)(hedge.*effectiveness|effective.*hedge|hedge.*ratio)',
                r'(?i)(how.*effective|effectiveness.*test)'
            ],
            
            # Monitoring
            PromptIntent.POSITION_MONITORING: [
                r'(?i)(position|exposure|current.*position)',
                r'(?i)(position.*summary|exposure.*summary|current.*exposure)',
                r'(?i)(what.*position|show.*position)'
            ],
            PromptIntent.EXPOSURE_ANALYSIS: [
                r'(?i)(exposure|risk.*exposure|currency.*exposure)',
                r'(?i)(exposure.*analysis|analyze.*exposure|exposure.*summary)',
                r'(?i)(fx.*exposure|foreign.*exchange.*exposure)'
            ],
            PromptIntent.PORTFOLIO_ANALYSIS: [
                r'(?i)(portfolio|fund|portfolio.*analysis)',
                r'(?i)(analyze.*portfolio|portfolio.*summary|fund.*analysis)',
                r'(?i)(portfolio.*breakdown|fund.*composition)'
            ],
            
            # New instruction types from CSV analysis
            PromptIntent.HEDGE_MONITORING: [
                r'(?i)(monitor|monitoring|real.*time|breach.*check)',
                r'(?i)(status.*check|current.*status|position.*query)',
                r'(?i)(risk.*monitoring|threshold.*breach|violation)'
            ],
            PromptIntent.MX_BOOKINGS: [
                r'(?i)(mx.*booking|deal.*booking|murex.*booking)',
                r'(?i)(booking.*detail|deal.*detail|order.*ord-[0-9]+)',
                r'(?i)(show.*booking|get.*deal|fetch.*booking)'
            ],
            PromptIntent.GL_ENTRIES_QUERY: [
                r'(?i)(gl.*entries|journal.*entries|accounting.*entries)',
                r'(?i)(show.*gl|get.*journal|fetch.*entries)',
                r'(?i)(debit.*credit|accounting.*detail|posting.*detail)'
            ],
            PromptIntent.GENERAL_PORTFOLIO: [
                r'(?i)(list.*all|show.*all|get.*all|summary.*all)',
                r'(?i)(portfolio.*summary|fund.*overview|entity.*summary)',
                r'(?i)(hedges.*for|positions.*for|exposure.*for)'
            ]
        }
    
    def setup_table_mappings(self):
        """Map each intent to required database tables"""
        self.table_mappings = {
            # Hedge Instructions - targeted data based on instruction type
            PromptIntent.HEDGE_UTILIZATION: [
                "entity_master", "position_nav_master", "allocation_engine",
                "currency_configuration", "threshold_configuration", "buffer_configuration", "currency_rates"
            ],
            PromptIntent.HEDGE_INCEPTION: [
                "entity_master", "position_nav_master", "hedge_instruments",
                "instruction_event_config", "murex_book_config", "waterfall_logic_configuration",
                "currency_configuration"
            ],
            PromptIntent.HEDGE_ROLLOVER: [
                "hedge_instructions", "hedge_business_events", "rollover_configuration",
                "entity_master", "position_nav_master", "allocation_engine"
            ],
            PromptIntent.HEDGE_TERMINATION: [
                "hedge_instructions", "hedge_business_events", "gl_entries", 
                "hedge_effectiveness", "termination_configuration"
            ],
            PromptIntent.HEDGE_AMENDMENT: [
                "hedge_instructions", "hedge_business_events", "business_event_rules",
                "gl_entries", "allocation_engine"
            ],
            PromptIntent.HEDGE_INQUIRY: [
                "hedge_instructions", "hedge_business_events", "allocation_engine",
                "system_configuration"
            ],
            
            # Risk Analysis
            PromptIntent.VAR_CALCULATION: [
                "position_nav_master", "currency_rates", "var_calculations",
                "risk_monitoring", "market_data"
            ],
            PromptIntent.STRESS_TEST: [
                "position_nav_master", "stress_test_results", "risk_scenarios",
                "currency_rates", "market_data"
            ],
            PromptIntent.CORRELATION_ANALYSIS: [
                "currency_rates", "position_nav_master", "market_data",
                "performance_data", "correlation_matrix"
            ],
            
            # Compliance
            PromptIntent.COMPLIANCE_REPORT: [
                "compliance_checks", "audit_trail", "regulatory_data",
                "threshold_configuration", "position_nav_master"
            ],
            PromptIntent.THRESHOLD_MONITORING: [
                "threshold_configuration", "threshold_breaches", "monitoring_alerts",
                "position_nav_master", "risk_monitoring"
            ],
            PromptIntent.AUDIT_TRAIL: [
                "audit_trail", "system_logs", "user_activity", "change_history"
            ],
            
            # Performance
            PromptIntent.PERFORMANCE_METRICS: [
                "performance_data", "hedge_effectiveness", "pnl_data",
                "position_nav_master", "allocation_engine"
            ],
            PromptIntent.HEDGE_EFFECTIVENESS: [
                "hedge_effectiveness", "hedge_instructions", "market_data",
                "currency_rates", "position_nav_master"
            ],
            
            # Monitoring
            PromptIntent.POSITION_MONITORING: [
                "position_nav_master", "allocation_engine", "car_master",
                "entity_master", "currency_configuration"
            ],
            PromptIntent.EXPOSURE_ANALYSIS: [
                "position_nav_master", "currency_rates", "hedge_instructions",
                "entity_master", "exposure_summary"
            ],
            PromptIntent.PORTFOLIO_ANALYSIS: [
                "entity_master", "position_nav_master", "allocation_engine",
                "performance_data", "risk_monitoring"
            ],
            
            # New instruction types from CSV analysis - with required tables
            PromptIntent.HEDGE_MONITORING: [
                "position_nav_master", "hedge_business_events", "usd_pb_deposit", 
                "risk_monitoring", "audit_trail", "entity_master"
            ],
            PromptIntent.MX_BOOKINGS: [
                "deal_bookings", "hedge_instructions", "hedge_business_events"
            ],
            PromptIntent.GL_ENTRIES_QUERY: [
                "gl_entries", "gl_entries_detail", "hedge_instructions", 
                "entity_master"
            ],
            PromptIntent.GENERAL_PORTFOLIO: [
                "hedge_business_events", "usd_pb_deposit", "allocation_engine", 
                "car_master", "entity_master", "position_nav_master"
            ]
        }
    
    def setup_parameter_extractors(self):
        """Setup regex patterns for parameter extraction"""
        # Valid currency codes for context validation
        self.valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'HKD', 'SGD', 'CAD', 'AUD', 
            'CNY', 'KRW', 'TWD', 'NZD', 'CHF', 'MXN', 'BRL', 'INR'
        }
        
        self.param_extractors = {
            # Enhanced currency extraction with context awareness
            'currency': r'(?i)(?:\d+[kmb]?\s+)([A-Z]{3})(?:\s+(?:today|hedge|exposure|position|capacity|for|\d))|hedge\s+\d+[kmb]?\s+([A-Z]{3})|new\s+([A-Z]{3})\s+hedge|(?:amount|with)\s+\d+\s*([A-Z]{3})|([A-Z]{3})\s+(?:exposure|position|capacity)',
            # Enhanced patterns with more extraction options
            'order_id': r'(?i)(?:order|ord)[-_]?([a-zA-Z0-9]+)',
            'previous_order_id': r'(?i)(?:previous|existing|old).*(?:order|ord)[-_]?([a-zA-Z0-9]+)',
            'amount': r'(?i)(?:amount|with amount|for)\s+([0-9]+(?:\.[0-9]+)?)\s*([kmb]?)\b',
            'entity_id': r'(?i)(?:for|entity)\s+([A-Z]+[0-9]+[A-Z0-9]*)',
            'order_id': r'(?i)(?:order|using order)\s+([A-Z0-9_-]+)',
            'sub_order_id': r'(?i)(?:sub-order|suborder)\s+([A-Z0-9_-]+)',
            'previous_order_id': r'(?i)(?:previous|prev).*?(?:order|ord)[-_]?([0-9A-Z-]+)',
            'nav_type': r'(?i)\b(COI|RE|RE_Reserve)\b',
            'time_period': r'(?i)(\d{4}-\d{2}-\d{2})|(Q[1-4][-\s]?20[0-9]{2})',
            'month_year': r'(?i)((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s-]?20[0-9]{2})|(\d{1,2}[-/]20[0-9]{2})',
            'confidence_level': r'(?i)([0-9]{1,2})%?\s*(?:confidence|conf)',
            'portfolio': r'(?i)(?:portfolio|fund|account)[:=\s]+([A-Z0-9_]+)',
            'hedge_method': r'(?i)\b(COH|MTM|MT|Swap\s+Pt|Fringe)\b',
            'entity_filter': r'(?i)(?:entity|for\s+entity|filter\s+by)\s+([A-Z]+[0-9]+)',
            'query_type': r'(?i)(position\s+query|breach\s+check|status\s+check)'
        }
    
    def analyze_prompt_hybrid(self, user_prompt: str, template_category: Optional[str] = None, 
                            user_input_fields: Optional[Dict[str, Any]] = None) -> PromptAnalysisResult:
        """
        HYBRID ANALYSIS: Combines user input fields + regex extraction + instruction type inference
        Priority: User Fields > Enhanced Regex > Template Defaults
        """
        # Step 1: Determine intent
        intent, confidence = self.detect_intent(user_prompt, template_category)
        
        # Step 2: HYBRID Parameter Extraction
        extracted_params = self.extract_parameters_hybrid(user_prompt, user_input_fields or {})
        
        # Step 3: Determine required tables with hybrid context
        required_tables = self.get_required_tables(intent, extracted_params)
        
        # Step 4: Infer instruction type for hedge operations
        instruction_type = self.infer_instruction_type(intent)
        
        # Step 5: Determine data scope
        data_scope = self.determine_data_scope(intent, extracted_params)
        
        return PromptAnalysisResult(
            intent=intent,
            confidence=confidence,
            required_tables=required_tables,
            extracted_params=extracted_params,
            instruction_type=instruction_type,
            data_scope=data_scope
        )
    
    def extract_parameters_hybrid(self, user_prompt: str, user_input_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        HYBRID parameter extraction: User fields take priority, regex as fallback
        """
        # Start with regex extraction from prompt
        regex_params = self.extract_parameters(user_prompt)
        
        # Apply priority logic: user input fields override regex extraction
        final_params = regex_params.copy()
        
        # Priority 1: User input fields (highest priority)
        for field, value in user_input_fields.items():
            if value and value != "":  # Only use non-empty user inputs
                final_params[field] = value
        
        # Priority 2: Enhanced currency validation (fix "CAN vs HKD" issue)
        if 'currency' in final_params:
            final_params['currency'] = self.validate_and_fix_currency(
                final_params['currency'], user_prompt, user_input_fields.get('currency')
            )
        
        return final_params
    
    def validate_and_fix_currency(self, extracted_currency: str, user_prompt: str, user_currency: Optional[str]) -> str:
        """
        Fix currency extraction issues like "CAN vs HKD"
        """
        # Priority 1: User explicitly selected currency
        if user_currency and user_currency.upper() in self.valid_currencies:
            return user_currency.upper()
        
        # Priority 2: Validate extracted currency
        if extracted_currency and extracted_currency.upper() in self.valid_currencies:
            return extracted_currency.upper()
        
        # Priority 3: Context-aware re-extraction
        # Find all potential 3-letter codes
        all_codes = re.findall(r'\b[A-Z]{3}\b', user_prompt.upper())
        valid_codes = [code for code in all_codes if code in self.valid_currencies]
        
        if valid_codes:
            # If multiple valid currencies, prioritize ones near numbers
            for code in valid_codes:
                # Look for currency near amounts
                amount_pattern = f'(?i)\\d+[kmb]?\\s*{code}|{code}\\s*\\d+[kmb]?'
                if re.search(amount_pattern, user_prompt):
                    return code
            
            # Return first valid currency found
            return valid_codes[0]
        
        # Fallback: return original or intelligent default
        if extracted_currency:
            return extracted_currency
        else:
            # Use context analyzer for intelligent default
            from shared.context_analyzer import context_analyzer
            smart_defaults = context_analyzer._get_intelligent_currency_default(user_prompt)
            return smart_defaults[0] if smart_defaults else "USD"

    def analyze_prompt(self, user_prompt: str, template_category: Optional[str] = None) -> PromptAnalysisResult:
        """
        LEGACY METHOD: For backward compatibility - redirects to hybrid method
        """
        return self.analyze_prompt_hybrid(user_prompt, template_category)
        
    def analyze_prompt_original(self, user_prompt: str, template_category: Optional[str] = None) -> PromptAnalysisResult:
        """
        ORIGINAL analysis method (kept for reference)
        """
        # Step 1: Determine intent
        intent, confidence = self.detect_intent(user_prompt, template_category)
        
        # Step 2: Extract parameters
        extracted_params = self.extract_parameters(user_prompt)
        
        # Step 3: Determine required tables
        required_tables = self.get_required_tables(intent, extracted_params)
        
        # Step 4: Infer instruction type for hedge operations
        instruction_type = self.infer_instruction_type(intent)
        
        # Step 5: Determine data scope
        data_scope = self.determine_data_scope(intent, extracted_params)
        
        return PromptAnalysisResult(
            intent=intent,
            confidence=confidence,
            required_tables=required_tables,
            extracted_params=extracted_params,
            instruction_type=instruction_type,
            data_scope=data_scope
        )
    
    def detect_intent(self, user_prompt: str, template_category: Optional[str] = None) -> tuple[PromptIntent, float]:
        """Detect the most likely intent from the user prompt"""
        intent_scores = {}
        
        # Check against all intent patterns
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, user_prompt):
                    score += 1
            
            if score > 0:
                intent_scores[intent] = score / len(patterns)
        
        # Boost score if template category matches intent family
        if template_category:
            for intent in intent_scores:
                if self.intent_matches_category(intent, template_category):
                    intent_scores[intent] *= 1.5
        
        # Return highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[best_intent], 1.0)
            return best_intent, confidence
        
        # Default to general query
        return PromptIntent.GENERAL_QUERY, 0.3
    
    def intent_matches_category(self, intent: PromptIntent, category: str) -> bool:
        """Check if intent matches template category"""
        category_mappings = {
            'hedge_accounting': [PromptIntent.HEDGE_INCEPTION, PromptIntent.HEDGE_UTILIZATION, 
                               PromptIntent.HEDGE_ROLLOVER, PromptIntent.HEDGE_TERMINATION],
            'risk_management': [PromptIntent.RISK_ANALYSIS, PromptIntent.VAR_CALCULATION, 
                              PromptIntent.STRESS_TEST, PromptIntent.CORRELATION_ANALYSIS],
            'compliance': [PromptIntent.COMPLIANCE_REPORT, PromptIntent.THRESHOLD_MONITORING, 
                          PromptIntent.AUDIT_TRAIL],
            'performance': [PromptIntent.PERFORMANCE_METRICS, PromptIntent.HEDGE_EFFECTIVENESS],
            'monitoring': [PromptIntent.POSITION_MONITORING, PromptIntent.EXPOSURE_ANALYSIS]
        }
        
        return intent in category_mappings.get(category, [])
    
    def extract_parameters(self, user_prompt: str) -> Dict[str, Any]:
        """Extract parameters from the prompt using regex patterns"""
        extracted = {}
        
        for param, pattern in self.param_extractors.items():
            match = re.search(pattern, user_prompt)
            if match:
                if param == 'amount':
                    # Handle amount with multipliers (K, M, B)
                    value = float(match.group(1))
                    multiplier = match.group(2).upper() if match.group(2) else ''
                    if multiplier == 'K':
                        value *= 1000
                    elif multiplier == 'M':
                        value *= 1000000
                    elif multiplier == 'B':
                        value *= 1000000000
                    extracted[param] = value
                elif param == 'currency':
                    # Handle multiple groups in currency regex
                    currency_code = None
                    for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                        if match.group(i):
                            currency_code = match.group(i)
                            break
                    if currency_code:
                        extracted[param] = currency_code.upper()
                elif param == 'amount':
                    # Handle multiple groups in amount regex
                    amount_value = None
                    multiplier = ''
                    for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                        if match.group(i) and match.group(i).replace('.', '').isdigit():
                            amount_value = float(match.group(i))
                            if i + 1 <= match.lastindex and match.group(i + 1):
                                multiplier = match.group(i + 1).upper()
                            break
                    if amount_value is not None:
                        if multiplier == 'K':
                            amount_value *= 1000
                        elif multiplier == 'M':
                            amount_value *= 1000000
                        elif multiplier == 'B':
                            amount_value *= 1000000000
                        extracted[param] = amount_value
                elif param == 'time_period':
                    # Handle multiple groups in time_period regex
                    time_value = None
                    for i in range(1, match.lastindex + 1 if match.lastindex else 1):
                        if match.group(i):
                            time_value = match.group(i)
                            break
                    if time_value:
                        extracted[param] = time_value
                else:
                    extracted[param] = match.group(1)
        
        return extracted
    
    def get_required_tables(self, intent: PromptIntent, params: Dict[str, Any]) -> List[str]:
        """Get required database tables based on intent and parameters"""
        base_tables = self.table_mappings.get(intent, ["entity_master", "position_nav_master"])
        
        # Add additional tables based on parameters
        additional_tables = []
        
        if 'currency' in params:
            additional_tables.extend(["currency_configuration", "currency_rates"])
        
        if 'entity_id' in params:
            additional_tables.append("entity_master")
        
        if 'order_id' in params or 'previous_order_id' in params:
            additional_tables.extend(["hedge_instructions", "hedge_business_events"])
        
        # Remove duplicates and return
        all_tables = list(set(base_tables + additional_tables))
        return all_tables
    
    def infer_instruction_type(self, intent: PromptIntent) -> Optional[str]:
        """Infer single-letter instruction type for hedge operations"""
        instruction_mapping = {
            PromptIntent.HEDGE_INCEPTION: "I",
            PromptIntent.HEDGE_UTILIZATION: "U", 
            PromptIntent.HEDGE_ROLLOVER: "R",
            PromptIntent.HEDGE_TERMINATION: "T",
            PromptIntent.HEDGE_AMENDMENT: "A",
            PromptIntent.HEDGE_INQUIRY: "Q"
        }
        
        return instruction_mapping.get(intent)
    
    def determine_data_scope(self, intent: PromptIntent, params: Dict[str, Any]) -> str:
        """Determine how much data to fetch"""
        # Comprehensive scope for complex analysis
        comprehensive_intents = [
            PromptIntent.PORTFOLIO_ANALYSIS, PromptIntent.PERFORMANCE_METRICS,
            PromptIntent.COMPLIANCE_REPORT, PromptIntent.HEDGE_EFFECTIVENESS
        ]
        
        # Minimal scope for simple queries
        minimal_intents = [
            PromptIntent.HEDGE_INQUIRY, PromptIntent.SYSTEM_STATUS,
            PromptIntent.AUDIT_TRAIL
        ]
        
        if intent in comprehensive_intents:
            return "comprehensive"
        elif intent in minimal_intents:
            return "minimal"
        else:
            return "targeted"

# Initialize global instance
prompt_intelligence = PromptIntelligenceEngine()

def analyze_prompt(user_prompt: str, template_category: Optional[str] = None) -> PromptAnalysisResult:
    """Global function to analyze prompts"""
    return prompt_intelligence.analyze_prompt(user_prompt, template_category)