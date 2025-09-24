#!/usr/bin/env python3
"""
Test shared component imports and basic initialization
"""
import sys
import os

def test_shared_imports():
    """Test importing shared components"""

    print("Testing shared component imports...")

    try:
        # Test core imports
        print("Importing shared.hedge_processor...")
        from shared.hedge_processor import hedge_processor
        print("[OK] hedge_processor imported")

        print("Importing shared.business_logic...")
        from shared.business_logic import PromptIntelligenceEngine
        print("[OK] business_logic imported")

        print("Importing shared.data_extractor...")
        from shared.data_extractor import SmartDataExtractor
        print("[OK] data_extractor imported")

        print("Importing shared.supabase_client...")
        from shared.supabase_client import DatabaseManager
        print("[OK] supabase_client imported")

        print("Importing shared.cache_manager...")
        from shared.cache_manager import get_cache_duration
        print("[OK] cache_manager imported")

        print("Importing shared.agent_report_generator...")
        from shared.agent_report_generator import agent_report_generator
        print("[OK] agent_report_generator imported")

        print("[OK] All shared components imported successfully!")
        return True

    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

def test_processor_initialization():
    """Test basic processor initialization"""
    try:
        print("Testing processor initialization...")
        from shared.hedge_processor import hedge_processor

        print(f"Processor state - db_manager: {hedge_processor.db_manager}")
        print(f"Processor state - supabase_client: {hedge_processor.supabase_client}")
        print(f"Processor state - data_extractor: {hedge_processor.data_extractor}")

        # Test if we can access basic methods
        health = hedge_processor.get_system_health()
        print(f"[OK] System health check: {health.get('status', 'unknown')}")

        return True
    except Exception as e:
        print(f"[ERROR] Processor test failed: {e}")
        return False

if __name__ == "__main__":
    import_success = test_shared_imports()

    if import_success:
        init_success = test_processor_initialization()
    else:
        init_success = False

    print(f"Final result - Imports: {'OK' if import_success else 'FAILED'}, Initialization: {'OK' if init_success else 'FAILED'}")
    sys.exit(0 if (import_success and init_success) else 1)