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
from orchestrator.provider_decision_pass import (  # noqa: E402
    provider_decision_registry,
    provider_decision_state,
)
from orchestrator.source_health import PROMOTED_ADAPTER_STATUS  # noqa: E402
from world_monitor.source_registry import (  # noqa: E402
    EXPECTED_SOURCE_COUNT,
    SOURCE_SPECS,
    get_source,
    source_registry_action_category,
    unresolved_sources,
)


EXPECTED_DECISIONS = {
    "stock_act": {
        "status": "adapter_live_requires_key",
        "endpoint_contains": "capitoltrades.com/trades",
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
        "status": "intentionally_disabled",
        "endpoint_contains": "api.unusualwhales.com/api/option-trades/flow-alerts",
        "promoted": False,
        "selection_status": "optional_disabled",
        "action_category": "intentionally_disabled",
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

EXPECTED_CLEANUP_CATEGORIES = {
    "rapidapi": ("intentionally_disabled", "optional_disabled", "intentionally_disabled"),
    "coinglass": ("needs_adapter", "not_selected", "needs_adapter"),
    "chainlink": ("needs_adapter", "not_selected", "needs_adapter"),
    "github": ("needs_adapter", "not_selected", "needs_adapter"),
    "bookmap": ("local_bridge", "selected", "local_bridge_required"),
    "reddit": ("adapter_live_requires_key", "selected", "needs_credentials"),
    "stock_act": ("adapter_live_requires_key", "selected", "needs_credentials"),
    "kalshi": ("adapter_live_region_deferred", "selected", "needs_credentials"),
}

EXPECTED_PROVIDER_DECISION_STATUSES = {
    "rapidapi": "marketplace_disabled_no_provider",
    "coinglass": "provider_selected_pending_adapter",
    "chainlink": "provider_selected_pending_public_adapter",
    "github": "provider_selected_pending_public_adapter",
    "bookmap": "local_bridge_adapter_ready",
}


def main() -> int:
    errors: list[str] = []
    registry_keys = {source.key for source in SOURCE_SPECS}
    promoted_keys = set(PHASE1_LIVE_ADAPTER_KEYS)
    unresolved = tuple(unresolved_sources())
    provider_decision_registry_state = provider_decision_registry()

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
        if not bool(expectation["promoted"]) and key in promoted_keys:
            errors.append(f"decision_adapter_unexpectedly_promoted:{key}")
        expected_selection = expectation.get("selection_status")
        if expected_selection and source.selection_status != expected_selection:
            errors.append(f"decision_selection_mismatch:{key}:{source.selection_status}:{expected_selection}")
        expected_action = expectation.get("action_category")
        if expected_action and source_registry_action_category(source) != expected_action:
            errors.append(
                f"decision_action_category_mismatch:{key}:{source_registry_action_category(source)}:{expected_action}"
            )

    for key, (expected_status, expected_selection, expected_action) in EXPECTED_CLEANUP_CATEGORIES.items():
        source = get_source(key)
        if source.status != expected_status:
            errors.append(f"cleanup_status_mismatch:{key}:{source.status}:{expected_status}")
        if source.selection_status != expected_selection:
            errors.append(f"cleanup_selection_mismatch:{key}:{source.selection_status}:{expected_selection}")
        if source_registry_action_category(source) != expected_action:
            errors.append(
                f"cleanup_action_category_mismatch:{key}:{source_registry_action_category(source)}:{expected_action}"
            )

    if provider_decision_registry_state.get("decision_count") != len(EXPECTED_PROVIDER_DECISION_STATUSES):
        errors.append("provider_decision_count_mismatch")
    if provider_decision_registry_state.get("credential_required_now_count") != 0:
        errors.append("provider_decision_requires_credentials_unexpectedly")

    for key, expected_decision_status in EXPECTED_PROVIDER_DECISION_STATUSES.items():
        decision = provider_decision_state(key)
        if not decision:
            errors.append(f"provider_decision_missing:{key}")
            continue
        if decision.get("decision_status") != expected_decision_status:
            errors.append(
                f"provider_decision_status_mismatch:{key}:{decision.get('decision_status')}:{expected_decision_status}"
            )
        if decision.get("order_authority") != "none":
            errors.append(f"provider_decision_order_authority_leaked:{key}")
        if decision.get("broker_write_authority") is not False:
            errors.append(f"provider_decision_broker_write_leaked:{key}")
        if decision.get("live_capital_authority") is not False:
            errors.append(f"provider_decision_live_capital_leaked:{key}")
        if decision.get("credential_required_now") is not False:
            errors.append(f"provider_decision_credential_required_now:{key}")

    print("source_registry_blocker_status=" + ("ok" if not errors else "error"))
    print(f"source_registry_blocker_source_count={len(SOURCE_SPECS)}")
    print(f"source_registry_blocker_expected_source_count={EXPECTED_SOURCE_COUNT}")
    print(f"source_registry_blocker_legacy_unresolved_count={len(unresolved)}")
    print(f"source_registry_blocker_generic_adapter_count={len(promoted_keys)}")
    print(f"source_registry_blocker_total_promoted_adapter_count={len(PROMOTED_ADAPTER_STATUS)}")
    print("source_registry_blocker_decision_count=" + str(len(EXPECTED_DECISIONS)))
    print("source_registry_cleanup_category_count=" + str(len(EXPECTED_CLEANUP_CATEGORIES)))
    print(
        "source_registry_provider_decision_count="
        + str(provider_decision_registry_state.get("decision_count", 0))
    )
    print(
        "source_registry_provider_decision_credential_required_now_count="
        + str(provider_decision_registry_state.get("credential_required_now_count", 0))
    )
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
