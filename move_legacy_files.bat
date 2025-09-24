@echo off
echo Moving legacy backend files to backend-legacy folder...

REM Move legacy backend files
move "optimized_hedge_data_service.py" "backend-legacy\"
move "optimized_dify_endpoint.py" "backend-legacy\"
move "optimized_backend.py" "backend-legacy\"
move "complete_optimized_backend.py" "backend-legacy\"
move "hedge_management_cache_config.py" "backend-legacy\"
move "enhanced_working_hedge_backend.py" "backend-legacy\"
move "optimized_queries_backend.py" "backend-legacy\"
move "complete_hedge_workflow_backend.py" "backend-legacy\"
move "hedge_data.py" "backend-legacy\"
move "payloads.py" "backend-legacy\"
move "ai_dify_workflow_backend.py" "backend-legacy\"
move "comprehensive_hedge_data_backend.py" "backend-legacy\"

REM Move test files
move "test_enhanced_backend.py" "backend-legacy\"
move "test_unified_backend.py" "backend-legacy\"
move "simple_test.py" "backend-legacy\"
move "test_supabase.py" "backend-legacy\"
move "test_currency_extraction.py" "backend-legacy\"
move "test_regex_patterns.py" "backend-legacy\"

REM Move utility files
move "deploy_materialized_views.py" "backend-legacy\"

echo.
echo ✅ Legacy file cleanup complete!
echo.
echo 🎯 PRODUCTION FILES (remaining in root):
echo   - unified_smart_backend.py
echo   - smart_data_extractor.py
echo   - prompt_intelligence_engine.py
echo   - supabase_client.py
echo   - redis_cache_service.py
echo.
echo 📦 LEGACY FILES moved to backend-legacy/
pause