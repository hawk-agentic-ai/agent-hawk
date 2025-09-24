# Backend Cleanup Plan

## 🎯 PRODUCTION FILES (Keep in root)
- `unified_smart_backend.py` - Main production backend (v5.0.0)
- `smart_data_extractor.py` - Smart data fetching engine
- `prompt_intelligence_engine.py` - Currency extraction & prompt analysis
- `supabase_client.py` - Database client
- `redis_cache_service.py` - Cache service

## 📦 LEGACY FILES (Move to backend-legacy/)
- `optimized_hedge_data_service.py`
- `optimized_dify_endpoint.py` 
- `optimized_backend.py`
- `complete_optimized_backend.py`
- `hedge_management_cache_config.py`
- `enhanced_working_hedge_backend.py`
- `optimized_queries_backend.py`
- `complete_hedge_workflow_backend.py`
- `hedge_data.py`
- `payloads.py`
- `ai_dify_workflow_backend.py`
- `comprehensive_hedge_data_backend.py`

## 🧪 TEST FILES (Move to backend-legacy/)
- `test_enhanced_backend.py`
- `test_unified_backend.py`
- `simple_test.py`
- `test_supabase.py`
- `test_currency_extraction.py`
- `test_regex_patterns.py`

## 🛠️ UTILITY FILES (Move to backend-legacy/)
- `deploy_materialized_views.py`

## 🚀 FINAL RESULT
Root directory will have only 5 production Python files instead of 24!