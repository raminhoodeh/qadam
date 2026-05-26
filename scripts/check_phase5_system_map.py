#!/usr/bin/env python3
"""Validate the Q5-13 functional system map dashboard contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status, export_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_system_map import (  # noqa: E402
    LAYER_B_NODE_KEYS,
    PHASE5_SYSTEM_MAP_SCHEMA_VERSION,
    REQUIRED_NODE_KEYS,
    phase5_system_map_paths,
    validate_phase5_system_map_bundle,
    write_phase5_system_map,
)


def _probe_errors(bundle: dict, *, path: tuple[str, ...], value: object) -> list[str]:
    probe = deepcopy(bundle)
    target = probe
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return validate_phase5_system_map_bundle(probe)


def _first_node_probe_errors(bundle: dict, **updates: object) -> list[str]:
    probe = deepcopy(bundle)
    probe["nodes"][0].update(updates)
    return validate_phase5_system_map_bundle(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_system_map_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    base_status = build_cockpit_status(settings)
    base_bundle = base_status["phase5_system_map"]
    output_path, history_path, event_log_path, written_bundle = write_phase5_system_map(
        base_bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_system_map_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()

    export_cockpit_status(settings=settings)
    refreshed_status = build_cockpit_status(settings)
    public_bundle = refreshed_status["phase5_system_map"]

    node_status_probe_errors = _first_node_probe_errors(
        written_bundle,
        display_status="dishonest_status",
    )
    node_inferred_probe_errors = _first_node_probe_errors(written_bundle, ui_inferred=True)
    node_authority_probe_errors = _first_node_probe_errors(
        written_bundle,
        broker_write_allowed=True,
    )
    source_role_probe_errors = _probe_errors(
        written_bundle,
        path=("source_posture", "yahoo_finance", "role"),
        value="canonical_execution_source",
    )
    preference_source_probe_errors = _probe_errors(
        written_bundle,
        path=("source_posture", "preference_mcp", "source_36"),
        value=True,
    )
    live_capital_probe_errors = _probe_errors(
        written_bundle,
        path=("guardrails", "live_capital_enabled"),
        value=True,
    )
    trading_claim_probe_errors = _probe_errors(
        written_bundle,
        path=("guardrails", "dashboard_claims_trading_now"),
        value=True,
    )

    print("phase5_system_map_status=" + written_bundle["status"])
    print(f"phase5_system_map_schema_version={PHASE5_SYSTEM_MAP_SCHEMA_VERSION}")
    print(f"phase5_system_map_artifact_path={output_path}")
    print(f"phase5_system_map_history_path={history_path}")
    print(f"phase5_system_map_event_log_path={event_log_path}")
    print(f"phase5_system_map_node_count={written_bundle['node_count']}")
    print(f"phase5_system_map_lane_count={written_bundle['lane_count']}")
    print(f"phase5_system_map_layer_b_node_count={written_bundle['layer_b_node_count']}")
    print(f"phase5_system_map_required_node_count={len(REQUIRED_NODE_KEYS)}")
    print(f"phase5_system_map_expected_layer_b_node_count={len(LAYER_B_NODE_KEYS)}")
    print(f"phase5_system_map_backend_parity_check_count={written_bundle['backend_parity_check_count']}")
    print(f"phase5_system_map_backend_parity_error_count={written_bundle['backend_parity_error_count']}")
    print(f"phase5_system_map_unsafe_control_count={written_bundle['unsafe_control_count']}")
    print(f"phase5_system_map_ui_inferred_node_count={written_bundle['ui_inferred_node_count']}")
    print(f"phase5_system_map_event_log_written={written_bundle['event_log_written']}")
    print(f"phase5_system_map_event_log_total_events={event_replay['total_events']}")
    print(f"phase5_system_map_validation_error_count={len(validation_errors)}")
    print(f"phase5_system_map_public_status={public_bundle['status']}")
    print(f"phase5_system_map_public_recorded={public_bundle['recorded']}")
    print(f"phase5_system_map_public_event_log_written={public_bundle['event_log_written']}")
    print(
        "phase5_system_map_canonical_replay="
        f"{written_bundle['source_posture']['canonical']['replayed_source_count']}/"
        f"{written_bundle['source_posture']['canonical']['expected_source_count']}"
    )
    print(
        "phase5_system_map_yahoo_finance_role="
        f"{written_bundle['source_posture']['yahoo_finance']['role']}"
    )
    print(
        "phase5_system_map_preference_source_36="
        f"{written_bundle['source_posture']['preference_mcp']['source_36']}"
    )
    print(
        "phase5_system_map_dashboard_claims_trading_now="
        f"{written_bundle['guardrails']['dashboard_claims_trading_now']}"
    )
    print(
        "phase5_system_map_trading_state_present="
        f"{written_bundle['guardrails']['trading_state_present']}"
    )
    print(
        "phase5_system_map_live_capital_enabled="
        f"{written_bundle['guardrails']['live_capital_enabled']}"
    )
    print(
        "phase5_system_map_paper_submit_path_available_count="
        f"{written_bundle['guardrails']['paper_submit_path_available_count']}"
    )
    print(f"phase5_system_map_node_status_probe_error_count={len(node_status_probe_errors)}")
    print(f"phase5_system_map_node_inferred_probe_error_count={len(node_inferred_probe_errors)}")
    print(f"phase5_system_map_node_authority_probe_error_count={len(node_authority_probe_errors)}")
    print(f"phase5_system_map_source_role_probe_error_count={len(source_role_probe_errors)}")
    print(
        "phase5_system_map_preference_source_probe_error_count="
        f"{len(preference_source_probe_errors)}"
    )
    print(f"phase5_system_map_live_capital_probe_error_count={len(live_capital_probe_errors)}")
    print(f"phase5_system_map_trading_claim_probe_error_count={len(trading_claim_probe_errors)}")
    print("phase5_system_map_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("system_map_not_ok")
    if public_bundle.get("status") != "ok":
        errors.append("system_map_public_not_ok")
    if public_bundle.get("recorded") is not True:
        errors.append("system_map_public_not_recorded")
    if public_bundle.get("event_log_written") is not True:
        errors.append("system_map_public_event_log_not_written")
    if written_bundle["node_count"] != len(REQUIRED_NODE_KEYS):
        errors.append("system_map_node_count_mismatch")
    if written_bundle["layer_b_node_count"] != len(LAYER_B_NODE_KEYS):
        errors.append("system_map_layer_b_node_count_mismatch")
    if written_bundle["backend_parity_error_count"] != 0:
        errors.append("system_map_backend_parity_errors")
    if written_bundle["unsafe_control_count"] != 0:
        errors.append("system_map_unsafe_controls")
    if written_bundle["ui_inferred_node_count"] != 0:
        errors.append("system_map_ui_inferred_nodes")
    if event_replay["total_events"] != 1:
        errors.append("system_map_event_log_count_mismatch")
    if written_bundle["source_posture"]["yahoo_finance"]["role"] != "supplemental_market_confirmation_only":
        errors.append("system_map_yahoo_role_mismatch")
    if written_bundle["source_posture"]["preference_mcp"]["source_36"] is not False:
        errors.append("system_map_preference_source_36")
    if written_bundle["source_posture"]["preference_mcp"]["source_quorum_credit_allowed"] is not False:
        errors.append("system_map_preference_source_quorum_enabled")
    if written_bundle["guardrails"]["live_capital_enabled"] is not False:
        errors.append("system_map_live_capital_enabled")
    if written_bundle["guardrails"]["dashboard_claims_trading_now"] is True:
        errors.append("system_map_claims_trading_now")

    expected_probe_markers = [
        ("system_map_node_status_mismatch", node_status_probe_errors),
        ("system_map_node_ui_inferred", node_inferred_probe_errors),
        ("system_map_node_authority_enabled", node_authority_probe_errors),
        ("system_map_yahoo_role_invalid", source_role_probe_errors),
        ("system_map_preference_source_36", preference_source_probe_errors),
        ("system_map_live_capital_enabled", live_capital_probe_errors),
    ]
    if written_bundle["guardrails"]["trading_state_present"] is False:
        expected_probe_markers.append(
            ("system_map_claims_trading_without_backend_state", trading_claim_probe_errors)
        )
    for marker, probe_errors in expected_probe_markers:
        if not any(marker in error for error in probe_errors):
            errors.append(f"system_map_probe_not_rejected:{marker}")

    if errors:
        for error in errors:
            print(f"phase5_system_map_error={error}")
        print("phase5_system_map_check=failed")
        return 1

    print("phase5_system_map_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
