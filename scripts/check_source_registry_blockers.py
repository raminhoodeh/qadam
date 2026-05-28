#!/usr/bin/env python3
"""Validate Qadam source-registry blocker decisions.

This check focuses on the May 2026 blocker class: stale `needs_*` registry
states that made implemented or decisioned sources look unresolved.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase1_live_adapters import PHASE1_LIVE_ADAPTER_KEYS  # noqa: E402
from orchestrator.source_health import PROMOTED_ADAPTER_STATUS  # noqa: E402
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS, get_source, unresolved_sources  # noqa: E402


EXPECTED_DECISIONS = {
    "stock_act": {
        "status": "adapter_live_requires_key",
        "endpoint_contains": "api.unusualwhales.com/api/congress/recent-trades",
        "promoted": True,
    },
    "usgs": {
        "status": "adapter_live_optional",
        "endpoint_contains": "earthquake.usgs.gov/fdsnws/event/1/query",
        "promoted": True,
    },
    "space_track_celestrak": {
        "status": "adapter_live_optional",
        "endpoint_contains": "celestrak.org/NORAD/elements/gp.php",
        "promoted": True,
    },
    "ais_maritime": {
        "status": "adapter_live_requires_key",
        "endpoint_contains": "stream.aisstream.io/v0/stream",
        "promoted": True,
    },
    "unusual_whales": {
        "status": "adapter_live_requires_key",
        "endpoint_contains": "api.unusualwhales.com/api/option-trades/flow-alerts",
        "promoted": True,
    },
    "polymarket": {
        "status": "adapter_live_optional",
        "endpoint_contains": "clob.polymarket.com/markets",
        "promoted": True,
    },
    "kalshi": {
        "status": "adapter_live_region_deferred",
        "endpoint_contains": "trading-api.kalshi.com/trade-api/v2/markets",
        "promoted": True,
    },
    "alpaca": {
        "status": "adapter_live_broker_split",
        "endpoint_contains": "paper-api.alpaca.markets/v2/account",
        "promoted": True,
    },
}


def main() -> int:
    errors: list[str] = []
    registry_keys = {source.key for source in SOURCE_SPECS}
    promoted_keys = set(PHASE1_LIVE_ADAPTER_KEYS)
    unresolved = tuple(unresolved_sources())

    if len(SOURCE_SPECS) != EXPECTED_SOURCE_COUNT:
        errors.append("source_count_mismatch")
    if unresolved:
        errors.append("legacy_unresolved_sources_present:" + ",".join(source.key for source in unresolved))

    for key, expectation in EXPECTED_DECISIONS.items():
        if key not in registry_keys:
            errors.append(f"decision_source_missing:{key}")
            continue
        source = get_source(key)
        expected_status = expectation["status"]
        if source.status != expected_status:
            errors.append(f"decision_status_mismatch:{key}:{source.status}:{expected_status}")
        expected_endpoint = expectation["endpoint_contains"]
        if not any(expected_endpoint in endpoint for endpoint in source.endpoints):
            errors.append(f"decision_endpoint_missing:{key}:{expected_endpoint}")
        if bool(expectation["promoted"]) and key not in promoted_keys:
            errors.append(f"decision_adapter_not_promoted:{key}")

    print("source_registry_blocker_status=" + ("ok" if not errors else "error"))
    print(f"source_registry_blocker_source_count={len(SOURCE_SPECS)}")
    print(f"source_registry_blocker_expected_source_count={EXPECTED_SOURCE_COUNT}")
    print(f"source_registry_blocker_legacy_unresolved_count={len(unresolved)}")
    print(f"source_registry_blocker_generic_adapter_count={len(promoted_keys)}")
    print(f"source_registry_blocker_total_promoted_adapter_count={len(PROMOTED_ADAPTER_STATUS)}")
    print("source_registry_blocker_decision_count=" + str(len(EXPECTED_DECISIONS)))
    print(
        "source_registry_blocker_boundary="
        "Read-only source registry decisions only; this check does not authorize signals, risk, or orders."
    )
    for error in errors:
        print(f"source_registry_blocker_error={error}")

    if errors:
        return 1
    print("source_registry_blocker_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
