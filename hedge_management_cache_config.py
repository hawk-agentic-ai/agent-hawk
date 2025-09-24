# Hedge Management Cache Configuration - Optimized for 30 Users Max
# Realistic caching strategy for small hedge fund operations

HEDGE_CACHE_STRATEGY = {
    # PERMANENT CACHE - Cache forever after ANY usage (perfect for 30 users)
    # Strategic data that gets reused frequently by small team
    'hedge_positions': 0,                    # Hedge positions are strategic, permanent cache
    'compliance_reports': 0,                 # Historical compliance data, permanent cache
    'performance_analysis': 0,               # Historical performance insights, permanent cache
    'risk_framework': 0,                     # Risk management frameworks, permanent cache
    'dify_strategic_insights': 0,            # AI strategic recommendations, permanent cache
    'portfolio_structure': 0,                # Fund structure doesn't change, permanent cache
    
    # PERMANENT CACHE - Previously time-limited, now permanent for small users
    # High repetition probability with only 30 users
    'risk_metrics': 0,                       # Changed from 86400 to 0 - permanent for small team
    'exposure_analysis': 0,                  # Changed from 86400 to 0 - permanent for small team
    'hedge_effectiveness': 0,                # Changed from 86400 to 0 - permanent for small team
    'var_calculations': 0,                   # Changed from 86400 to 0 - permanent for small team
    'stress_test_results': 0,                # Changed from 86400 to 0 - permanent for small team
    'portfolio_valuation': 0,                # Changed from 14400 to 0 - permanent for small team
    'nav_calculations': 0,                   # Changed from 14400 to 0 - permanent for small team
    'allocation_drift': 0,                   # Changed from 14400 to 0 - permanent for small team
    
    # VERY SHORT CACHE - Only for real-time data (reduced from 30min to 5min)
    'market_data': 300,                      # 5 minutes - live FX rates need frequent updates
    'real_time_pnl': 300,                    # 5 minutes - live P&L needs frequent updates
    'liquidity_metrics': 300,                # 5 minutes - live liquidity needs frequent updates
    
    # NEW TEMPLATE TESTING - For brand new templates only
    'new_template_validation': 300,          # 5 minutes for testing new templates
    
    # HEDGE INSTRUCTION TEMPLATES - All permanent for small users
    'inception_template': 0,                 # Permanent cache - high reuse for 30 users
    'utilisation_template': 0,               # Permanent cache - high reuse for 30 users  
    'rollover_template': 0,                  # Permanent cache - high reuse for 30 users
    'termination_template': 0,               # Permanent cache - high reuse for 30 users
}

# Smart cache key generation optimized for 30 user hedge fund
def get_hedge_cache_key(query_type: str, user_id: str, params: dict = None) -> str:
    """Generate cache keys optimized for 30 user hedge fund operations"""
    import hashlib
    
    # Expanded fund-level caching for small user base - more aggressive sharing
    fund_level_cache = [
        'hedge_positions', 'compliance_reports', 'risk_framework', 'portfolio_structure',
        'risk_metrics', 'exposure_analysis', 'hedge_effectiveness', 'var_calculations', 
        'portfolio_valuation', 'nav_calculations', 'stress_test_results',
        'inception_template', 'utilisation_template', 'rollover_template', 'termination_template'
    ]
    
    if query_type in fund_level_cache:
        base_key = f"hedge_fund_30users:{query_type}"
    else:
        base_key = f"hedge_user:{user_id}:{query_type}"
    
    if params:
        param_hash = hashlib.md5(str(sorted(params.items())).encode()).hexdigest()[:8]
        base_key += f":{param_hash}"
    
    return base_key

# Cache duration lookup optimized for 30 users
def get_cache_duration(query_type: str, usage_count: int = 1) -> int:
    """
    Get cache duration optimized for hedge fund with 30 users maximum
    
    Key principle: ANY usage (even 1x) gets permanent cache because:
    - Only 30 users means high repetition probability
    - Every Dify API call saved = significant cost reduction  
    - User experience: blazing fast responses for repeated operations
    """
    
    # Real-time data - always short cache regardless of usage
    if query_type in ['market_data', 'real_time_pnl', 'liquidity_metrics']:
        return 300  # 5 minutes - always fresh for market data
    
    # New template testing - short cache until first real usage
    if query_type == 'new_template_validation' and usage_count == 0:
        return 300  # 5 minutes for testing new templates
    
    # Everything else - check strategy first, then apply 30-user logic
    base_duration = HEDGE_CACHE_STRATEGY.get(query_type, 300)  # Default 5 min for new items
    
    # If base strategy is permanent (0), keep it permanent
    if base_duration == 0:
        return 0
    
    # For non-permanent items, make permanent after any usage (30 user optimization)
    if usage_count >= 1:
        return 0  # Permanent cache - every use matters with small team
    
    # Brand new items - short testing cache
    return 300  # 5 minutes for initial validation

# Enhanced cache logic for hedge management (30 users optimized)
HEDGE_QUERY_PATTERNS = {
    'portfolio_analysis': 'performance_analysis',        # Permanent cache
    'risk_exposure': 'risk_metrics',                     # Permanent cache (optimized from 24h)
    'hedge_effectiveness': 'hedge_effectiveness',        # Permanent cache (optimized from 24h)
    'compliance_check': 'compliance_reports',            # Permanent cache
    'var_calculation': 'var_calculations',               # Permanent cache (optimized from 24h)
    'stress_test': 'stress_test_results',                # Permanent cache (optimized from 24h)
    'position_analysis': 'hedge_positions',              # Permanent cache
    'nav_report': 'nav_calculations',                    # Permanent cache (optimized from 4h)
    
    # Hedge instruction templates - all permanent for small users
    'inception_query': 'inception_template',             # Permanent cache - I instructions
    'utilisation_query': 'utilisation_template',         # Permanent cache - U instructions
    'rollover_query': 'rollover_template',               # Permanent cache - R instructions
    'termination_query': 'termination_template',         # Permanent cache - T instructions
    
    # Template-based analysis (all permanent for 30 users)
    'hedge_instruction_analysis': 'hedge_positions',     # Permanent cache
    'murex_integration_query': 'hedge_positions',        # Permanent cache
    'gl_booking_query': 'hedge_positions',               # Permanent cache
}

# Performance expectations for 30 users
OPTIMIZATION_STATS = {
    "user_base_size": 30,
    "cache_hit_rate_target": "98%",           # Very high due to repetitive operations
    "avg_response_time_cached": "50ms",       # Blazing fast for cached responses
    "avg_response_time_fresh": "2500ms",      # Acceptable for rare fresh calls
    "monthly_dify_calls_target": 100,          # Massive API cost savings vs 18000 without cache
    "cost_reduction_percentage": 95,           # 95% cost reduction with aggressive caching
    "optimization_type": "small_user_base_permanent_cache"
}