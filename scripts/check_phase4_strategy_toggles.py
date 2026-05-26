#!/usr/bin/env python3
"""Validate the Q4-9 Phase 4 strategy toggle contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase4_strategy_toggles import (  # noqa: E402
    STRATEGY_TOGGLE_CONTRACT_SCHEMA_VERSION,
    TOGGLE_EVENT_LOG,
    build_strategy_toggle_snapshot,
    validate_strategy_toggle_snapshot,
    write_strategy_toggle_snapshot,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    event_log_path = runtime_dir / TOGGLE_EVENT_LOG
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_strategy_toggle_snapshot(settings=settings)
    output_path, written_artifact = write_strategy_toggle_snapshot(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_strategy_toggle_snapshot(written_artifact)
    event_replay = EventLog(event_log_path, echo=False).replay()
    latest_event = event_replay["last_by_component"].get("phase4_strategy_toggles", {})

    approved_shadow_probe = deepcopy(written_artifact)
    approved_shadow_probe["approval_state"] = "not_requested"
    approved_shadow_probe["approval_event_logged"] = False
    approved_shadow_probe["approved_shadow_ready"] = False
    approved_shadow_probe["toggles"][0]["toggle_state"] = "approved_shadow"
    approved_shadow_probe["toggles"][0]["approval_state"] = "not_requested"
    approved_shadow_probe["toggles"][0]["approval_event_logged"] = False
    approved_shadow_probe["approved_shadow_toggle_count"] = 1
    approved_shadow_probe["draft_toggle_count"] = max(0, written_artifact["toggle_count"] - 1)
    approved_shadow_errors = validate_strategy_toggle_snapshot(approved_shadow_probe)

    authority_probe = deepcopy(written_artifact)
    authority_probe["toggles"][0]["broker_write_allowed"] = True
    authority_errors = validate_strategy_toggle_snapshot(authority_probe)

    event_log_probe = deepcopy(written_artifact)
    event_log_probe["event_log_required"] = False
    event_log_errors = validate_strategy_toggle_snapshot(event_log_probe)

    risk_probe = deepcopy(written_artifact)
    risk_probe["toggles"][0]["risk_agent_handoff_allowed"] = True
    risk_errors = validate_strategy_toggle_snapshot(risk_probe)

    state_probe = deepcopy(written_artifact)
    state_probe["toggles"][0]["toggle_state"] = "active"
    state_errors = validate_strategy_toggle_snapshot(state_probe)

    trade_candidate_probe = deepcopy(written_artifact)
    trade_candidate_probe["trade_candidate_count"] = 1
    trade_candidate_errors = validate_strategy_toggle_snapshot(trade_candidate_probe)

    authority_flag_probe = deepcopy(written_artifact)
    authority_flag_probe["toggles"][0]["authority_flags"]["execution_authority"] = True
    authority_flag_errors = validate_strategy_toggle_snapshot(authority_flag_probe)

    print("phase4_strategy_toggle_status=" + ("ok" if not validation_errors else "error"))
    print(f"phase4_strategy_toggle_schema_version={STRATEGY_TOGGLE_CONTRACT_SCHEMA_VERSION}")
    print(f"phase4_strategy_toggle_artifact_path={output_path}")
    print(f"phase4_strategy_toggle_event_log_path={event_log_path}")
    print(f"phase4_strategy_toggle_count={written_artifact['toggle_count']}")
    print(f"phase4_strategy_toggle_draft_count={written_artifact['draft_toggle_count']}")
    print(f"phase4_strategy_toggle_inactive_count={written_artifact['inactive_toggle_count']}")
    print(
        "phase4_strategy_toggle_approved_shadow_count="
        f"{written_artifact['approved_shadow_toggle_count']}"
    )
    print(f"phase4_strategy_toggle_approval_state={written_artifact['approval_state']}")
    print(
        "phase4_strategy_toggle_approval_event_logged="
        f"{written_artifact['approval_event_logged']}"
    )
    print(
        "phase4_strategy_toggle_approved_shadow_ready="
        f"{written_artifact['approved_shadow_ready']}"
    )
    print(f"phase4_strategy_toggle_event_log_required={written_artifact['event_log_required']}")
    print(f"phase4_strategy_toggle_event_log_written={written_artifact['event_log_written']}")
    print(f"phase4_strategy_toggle_event_log_total_events={event_replay['total_events']}")
    print(f"phase4_strategy_toggle_event_type={latest_event.get('event_type')}")
    print(f"phase4_strategy_toggle_validation_error_count={len(validation_errors)}")
    print(f"phase4_strategy_toggle_approved_shadow_probe_error_count={len(approved_shadow_errors)}")
    print(f"phase4_strategy_toggle_authority_probe_error_count={len(authority_errors)}")
    print(f"phase4_strategy_toggle_event_log_probe_error_count={len(event_log_errors)}")
    print(f"phase4_strategy_toggle_risk_probe_error_count={len(risk_errors)}")
    print(f"phase4_strategy_toggle_state_probe_error_count={len(state_errors)}")
    print(f"phase4_strategy_toggle_trade_candidate_probe_error_count={len(trade_candidate_errors)}")
    print(f"phase4_strategy_toggle_authority_flag_probe_error_count={len(authority_flag_errors)}")
    print(
        "phase4_strategy_toggle_trade_candidate_count="
        f"{written_artifact['trade_candidate_count']}"
    )
    print(
        "phase4_strategy_toggle_risk_handoff_allowed_count="
        f"{written_artifact['risk_agent_handoff_allowed_count']}"
    )
    print(
        "phase4_strategy_toggle_execution_policy_handoff_allowed_count="
        f"{written_artifact['execution_policy_handoff_allowed_count']}"
    )
    print(
        "phase4_strategy_toggle_execution_allowed_count="
        f"{written_artifact['execution_allowed_count']}"
    )
    print(
        "phase4_strategy_toggle_paper_order_allowed_count="
        f"{written_artifact['paper_order_allowed_count']}"
    )
    print(
        "phase4_strategy_toggle_broker_write_allowed_count="
        f"{written_artifact['broker_write_allowed_count']}"
    )
    print(
        "phase4_strategy_toggle_live_capital_enabled_count="
        f"{written_artifact['live_capital_enabled_count']}"
    )
    print(f"phase4_strategy_toggle_boundary={written_artifact['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if written_artifact["toggle_count"] != 5:
        errors.append("toggle_count_not_five")
    if written_artifact["approval_state"] == "approved":
        if written_artifact["draft_toggle_count"] != 0:
            errors.append("approved_draft_toggle_count_not_zero")
        if written_artifact["approved_shadow_toggle_count"] != 5:
            errors.append("approved_shadow_count_not_five")
        if written_artifact["approval_event_logged"] is not True:
            errors.append("approval_event_logged_not_true")
        if written_artifact["approved_shadow_ready"] is not True:
            errors.append("approved_shadow_ready_not_true")
    elif written_artifact["approval_state"] == "not_requested":
        if written_artifact["draft_toggle_count"] != 5:
            errors.append("draft_toggle_count_not_five")
        if written_artifact["approved_shadow_toggle_count"] != 0:
            errors.append("approved_shadow_count_not_zero")
        if written_artifact["approval_event_logged"] is not False:
            errors.append("approval_event_logged_not_false")
        if written_artifact["approved_shadow_ready"] is not False:
            errors.append("approved_shadow_ready_not_false")
    else:
        errors.append("approval_state_not_supported_for_toggle_gate")
    if written_artifact["event_log_required"] is not True:
        errors.append("event_log_required_not_true")
    if written_artifact["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if event_replay["total_events"] != 1:
        errors.append("event_log_event_count_mismatch")
    if latest_event.get("event_type") != "phase4_strategy_toggle_snapshot_written":
        errors.append("event_log_event_type_mismatch")
    if "approved_shadow_without_logged_approval" not in approved_shadow_errors:
        errors.append("approved_shadow_probe_not_rejected")
    if not any(error.endswith(":broker_write_allowed") for error in authority_errors):
        errors.append("authority_probe_not_rejected")
    if "event_log_required_not_true" not in event_log_errors:
        errors.append("event_log_probe_not_rejected")
    if not any(error.endswith(":risk_agent_handoff_allowed") for error in risk_errors):
        errors.append("risk_probe_not_rejected")
    if not any("strategy_toggle_state_invalid" in error for error in state_errors):
        errors.append("state_probe_not_rejected")
    if "trade_candidate_count_not_zero" not in trade_candidate_errors:
        errors.append("trade_candidate_probe_not_rejected")
    if not any(
        "strategy_toggle_authority_flag_enabled" in error
        for error in authority_flag_errors
    ):
        errors.append("authority_flag_probe_not_rejected")
    for key in (
        "risk_agent_handoff_allowed_count",
        "execution_policy_handoff_allowed_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "authority_flag_violation_count",
    ):
        if written_artifact.get(key) != 0:
            errors.append(f"artifact_authority_count_not_zero:{key}")

    if errors:
        for error in errors:
            print(f"phase4_strategy_toggle_error={error}")
        print("phase4_strategy_toggle_check=failed")
        return 1

    print("phase4_strategy_toggle_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
