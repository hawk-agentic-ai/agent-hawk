import asyncio
from typing import Any, Dict, List, Optional

from shared.hedge_processor import HedgeFundProcessor
from shared.business_logic import PromptIntelligenceEngine


class MockExtractor:
    def __init__(self):
        self.redis_available = False

    def get_cache_stats(self) -> Dict[str, Any]:
        return {"cache_hits": 0, "cache_misses": 1, "redis_available": False}

    async def extract_data_for_prompt(self, analysis_result, use_cache: bool = True) -> Dict[str, Any]:
        # Return synthetic large lists to verify row capping
        big_list = [{"i": i} for i in range(100)]
        return {
            "entity_master": big_list.copy(),
            "position_nav_master": big_list.copy(),
            "_extraction_metadata": {"intent": analysis_result.intent.value, "data_scope": analysis_result.data_scope}
        }


async def main():
    proc = HedgeFundProcessor()
    proc.prompt_engine = PromptIntelligenceEngine()
    proc.data_extractor = MockExtractor()

    # Call with a prompt that maps to utilization; apply small max_rows
    resp = await proc.universal_prompt_processor(
        user_prompt="Process Utilization check for 50000 HKD",
        template_category="hedge_utilization",
        currency="HKD",
        amount=50000,
        operation_type="read",
        stage_mode="1A",
        agent_role="allocation",
        output_format="json",
        max_rows=5,
        max_kb=64,
        use_cache=False,
    )

    extracted = resp.get("extracted_data", {})
    print("entity_master_len=", len(extracted.get("entity_master", [])))
    print("position_nav_master_len=", len(extracted.get("position_nav_master", [])))
    print("processing_metadata=", resp.get("processing_metadata", {}))


if __name__ == "__main__":
    asyncio.run(main())

