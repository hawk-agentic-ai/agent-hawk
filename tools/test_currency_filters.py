import json
from typing import List, Tuple

from shared.data_extractor import SmartDataExtractor


class MockQuery:
    def __init__(self, table: str):
        self.table = table
        self.calls: List[Tuple[str, tuple, dict]] = []

    # Query builder methods (chainable)
    def select(self, *_args, **_kwargs):
        self.calls.append(("select", _args, _kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args, kwargs))
        return self

    def or_(self, *args, **kwargs):
        self.calls.append(("or_", args, kwargs))
        return self

    def in_(self, *args, **kwargs):
        self.calls.append(("in_", args, kwargs))
        return self

    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self.calls.append(("limit", args, kwargs))
        return self

    # Terminal method used by extractor; return empty data
    def execute(self):
        return type("Res", (), {"data": []})


class MockSupabase:
    def table(self, name: str):
        return MockQuery(name)


def run_checks():
    supa = MockSupabase()
    extractor = SmartDataExtractor(supa, redis_client=None)

    params = {"currency": "HKD"}

    tables = [
        "entity_master",
        "position_nav_master",
        "allocation_engine",
        "threshold_configuration",
        "currency_rates",
    ]

    results = {}
    for t in tables:
        q = extractor._build_smart_query(t, params, comprehensive=False)
        # Capture calls for assertions
        results[t] = q.calls

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    run_checks()

