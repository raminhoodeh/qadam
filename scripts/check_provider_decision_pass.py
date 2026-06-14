#!/usr/bin/env python3
"""Validate optional provider decisions without activating sources.

The provider decision pass records which optional/local providers Qadam would
use if those evidence surfaces are promoted later. It must not create missing
credential pressure, source-quorum credit, signal authority, order authority, or
broker write authority.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase1_live_adapters import PHASE1_LIVE_ADAPTER_KEYS  # noqa: E402
from orchestrator.provider_decision_pass import (  # noqa: E402
    provider_decision_keys,
    provider_decision_registry,
    provider_decision_state,
)
from orchestrator.source_health import build_data_environment_map  # noqa: E402
from world_monitor.source_registry import get_source, source_registry_action_category  # noqa: E402


EXPECTED_PROVIDER_DECISIONS = {
    "rapidapi": {
        "source_status": "intentionally_disabled",
        "selection_status": "optional_disabled",
        "action_category": "intentionally_disabled",
        "decision_status": "marketplace_disabled_no_provider",
        "selected_provider": "none",
        "promoted": False,
    },
    "coinglass": {
        "source_status": "needs_adapter",
        "selection_status": "not_selected",
        "action_category": "needs_adapter",
        "decision_status": "provider_selected_pending_adapter",
        "selected_provider": "CoinGlass API",
        "promoted": False,
    },
    "chainlink": {
        "source_status": "needs_adapter",
        "selection_status": "not_selected",
        "action_category": "needs_adapter",
        "decision_status": "provider_selected_pending_public_adapter",
        "selected_provider": "Chainlink Data Feeds",
        "promoted": False,
    },
    "github": {
        "source_status": "needs_adapter",
        "selection_status": "not_selected",
        "action_category": "needs_adapter",
        "decision_status": "provider_selected_pending_public_adapter",
        "selected_provider": "GitHub REST API",
        "promoted": False,
    },
    "bookmap": {
        "source_status": "local_bridge",
        "selection_status": "selected",
        "action_category": "local_bridge_required",
        "decision_status": "local_bridge_selected",
        "selected_provider": "Bookmap local API bridge",
        "promoted": True,
    },
}

SECRET_LIKE_PATTERNS = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bPVZ[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
)


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _assert_authority_boundary(state: dict[str, Any], errors: list[str]) -> None:
    source_key = str(state.get("source_key"))
    if state.get("public_safe") is not True:
        errors.append(f"public_safe_mismatch:{source_key}")
    if state.get("source_authority") != "observation_only_after_adapter_exists":
        errors.append(f"source_authority_mismatch:{source_key}")
    if state.get("signal_authority") != "none_without_strategy_and_risk_gates":
        errors.append(f"signal_authority_mismatch:{source_key}")
    if state.get("order_authority") != "none":
        errors.append(f"order_authority_leaked:{source_key}")
    if state.get("broker_write_authority") is not False:
        errors.append(f"broker_write_authority_leaked:{source_key}")
    if state.get("live_capital_authority") is not False:
        errors.append(f"live_capital_authority_leaked:{source_key}")
    if state.get("paper_trading_blocking") is not False:
        errors.append(f"paper_trading_blocking_changed:{source_key}")
    if state.get("credential_required_now") is not False:
        errors.append(f"credential_required_now_unexpected:{source_key}")


def main() -> int:
    errors: list[str] = []
    registry = provider_decision_registry()
    states = {
        source_key: provider_decision_state(source_key)
        for source_key in provider_decision_keys()
    }

    if set(states) != set(EXPECTED_PROVIDER_DECISIONS):
        errors.append("provider_decision_key_set_mismatch")
    if registry.get("decision_count") != len(EXPECTED_PROVIDER_DECISIONS):
        errors.append("provider_decision_count_mismatch")
    if registry.get("provider_selected_pending_adapter_count") != 3:
        errors.append("provider_selected_pending_adapter_count_mismatch")
    if registry.get("marketplace_disabled_count") != 1:
        errors.append("marketplace_disabled_count_mismatch")
    if registry.get("local_bridge_selected_count") != 1:
        errors.append("local_bridge_selected_count_mismatch")
    if registry.get("credential_required_now_count") != 0:
        errors.append("credential_required_now_count_mismatch")

    promoted = set(PHASE1_LIVE_ADAPTER_KEYS)
    for source_key, expectation in EXPECTED_PROVIDER_DECISIONS.items():
        source = get_source(source_key)
        state = states.get(source_key) or {}
        if source.status != expectation["source_status"]:
            errors.append(
                f"source_status_mismatch:{source_key}:{source.status}:{expectation['source_status']}"
            )
        if source.selection_status != expectation["selection_status"]:
            errors.append(
                "selection_status_mismatch:"
                f"{source_key}:{source.selection_status}:{expectation['selection_status']}"
            )
        action_category = source_registry_action_category(source)
        if action_category != expectation["action_category"]:
            errors.append(
                f"action_category_mismatch:{source_key}:{action_category}:{expectation['action_category']}"
            )
        if state.get("decision_status") != expectation["decision_status"]:
            errors.append(
                "decision_status_mismatch:"
                f"{source_key}:{state.get('decision_status')}:{expectation['decision_status']}"
            )
        if state.get("selected_provider") != expectation["selected_provider"]:
            errors.append(f"selected_provider_mismatch:{source_key}")
        if (source_key in promoted) is not bool(expectation["promoted"]):
            errors.append(f"promotion_mismatch:{source_key}")
        _assert_authority_boundary(state, errors)

    data_map = build_data_environment_map(Settings.from_env())
    summary = data_map.get("summary", {})
    if summary.get("provider_decision_source_count") != len(EXPECTED_PROVIDER_DECISIONS):
        errors.append("data_map_provider_decision_source_count_mismatch")
    if summary.get("provider_selected_pending_adapter_count") != 3:
        errors.append("data_map_provider_selected_pending_adapter_count_mismatch")
    if summary.get("provider_decision_marketplace_disabled_count") != 1:
        errors.append("data_map_marketplace_disabled_count_mismatch")
    if summary.get("provider_decision_local_bridge_count") != 1:
        errors.append("data_map_local_bridge_count_mismatch")
    if summary.get("provider_decision_credential_required_now_count") != 0:
        errors.append("data_map_credential_required_now_count_mismatch")
    data_sources = {source["source_key"]: source for source in data_map.get("sources", [])}
    for source_key, state in states.items():
        source_record = data_sources.get(source_key) or {}
        if source_record.get("provider_decision_status") != (state or {}).get("decision_status"):
            errors.append(f"data_map_provider_status_missing:{source_key}")
        if source_record.get("provider_selected_provider") != (state or {}).get("selected_provider"):
            errors.append(f"data_map_provider_name_missing:{source_key}")
        if source_record.get("provider_decision_credential_required_now") is not False:
            errors.append(f"data_map_provider_credential_required_now_unexpected:{source_key}")

    if _contains_secret_like_value({"registry": registry, "data_map": data_map}):
        errors.append("secret_like_value_detected")

    print("provider_decision_pass_status=" + ("ok" if not errors else "error"))
    print(f"provider_decision_pass_decision_count={len(EXPECTED_PROVIDER_DECISIONS)}")
    print(
        "provider_decision_pass_provider_selected_pending_adapter_count="
        f"{registry.get('provider_selected_pending_adapter_count')}"
    )
    print(
        "provider_decision_pass_marketplace_disabled_count="
        f"{registry.get('marketplace_disabled_count')}"
    )
    print(
        "provider_decision_pass_local_bridge_selected_count="
        f"{registry.get('local_bridge_selected_count')}"
    )
    print(
        "provider_decision_pass_credential_required_now_count="
        f"{registry.get('credential_required_now_count')}"
    )
    print(
        "provider_decision_pass_authority_unchanged="
        + str(not any("authority" in error or "blocking_changed" in error for error in errors))
    )
    print(
        "provider_decision_pass_boundary="
        "Read-only provider-decision metadata only; no source can approve signals, submit orders, call brokers, or enable live capital."
    )
    for error in errors:
        print(f"provider_decision_pass_error={error}")
    if errors:
        return 1
    print("provider_decision_pass_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
