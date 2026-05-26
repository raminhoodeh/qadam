#!/usr/bin/env python3
"""Validate the Q5-4 kill-switch ledger."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_kill_switch import (  # noqa: E402
    KILL_SWITCH_SCOPE_TYPES,
    PHASE5_KILL_SWITCH_SCHEMA_VERSION,
    build_phase5_kill_switch_ledger,
    phase5_kill_switch_paths,
    validate_phase5_kill_switch_event,
    validate_phase5_kill_switch_ledger,
    write_phase5_kill_switch_ledger,
)


def _first_switch(bundle: dict) -> dict:
    switches = bundle.get("switches", [])
    if not switches:
        raise RuntimeError("no kill-switch events produced")
    return switches[0]


def _fail_closed_probe(event: dict, *, state: object) -> dict:
    probe = deepcopy(event)
    probe["switch_state"] = state
    probe["status"] = "blocked"
    probe["switch_active"] = True
    probe["blocks_new_actions"] = True
    probe["switch_clear_for_downstream_gate"] = False
    probe["downstream_action_allowed"] = False
    probe["downstream_action_blocked"] = True
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_kill_switch_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_kill_switch_ledger(settings=settings)
    output_path, history_path, event_log_path, written_bundle = write_phase5_kill_switch_ledger(
        bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_kill_switch_ledger(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    first_switch = _first_switch(written_bundle)

    missing_state_probe = _fail_closed_probe(first_switch, state=None)
    missing_state_errors = validate_phase5_kill_switch_event(missing_state_probe)

    corrupt_state_probe = _fail_closed_probe(first_switch, state="broken_state")
    corrupt_state_errors = validate_phase5_kill_switch_event(corrupt_state_probe)

    active_not_blocking_probe = deepcopy(first_switch)
    active_not_blocking_probe["switch_state"] = "engaged_block_new_actions"
    active_not_blocking_probe["status"] = "blocked"
    active_not_blocking_probe["switch_active"] = True
    active_not_blocking_probe["blocks_new_actions"] = False
    active_not_blocking_probe["switch_clear_for_downstream_gate"] = True
    active_not_blocking_probe["downstream_action_allowed"] = True
    active_not_blocking_probe["downstream_action_blocked"] = False
    active_not_blocking_errors = validate_phase5_kill_switch_event(
        active_not_blocking_probe
    )

    ack_without_event_probe = deepcopy(first_switch)
    ack_without_event_probe["acknowledged"] = True
    ack_without_event_probe["mutation_event_logged"] = False
    ack_without_event_probe["event_log_written"] = False
    ack_without_event_probe["acknowledged_at"] = None
    ack_without_event_errors = validate_phase5_kill_switch_event(ack_without_event_probe)

    live_capital_probe = deepcopy(first_switch)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_phase5_kill_switch_event(live_capital_probe)

    execution_probe = deepcopy(first_switch)
    execution_probe["execution_allowed"] = True
    execution_errors = validate_phase5_kill_switch_event(execution_probe)

    mutation_authority_probe = deepcopy(first_switch)
    mutation_authority_probe["kill_switch_mutation_authority"] = True
    mutation_authority_errors = validate_phase5_kill_switch_event(
        mutation_authority_probe
    )

    print("phase5_kill_switch_status=" + written_bundle["status"])
    print(f"phase5_kill_switch_schema_version={PHASE5_KILL_SWITCH_SCHEMA_VERSION}")
    print(f"phase5_kill_switch_artifact_path={output_path}")
    print(f"phase5_kill_switch_history_path={history_path}")
    print(f"phase5_kill_switch_event_log_path={event_log_path}")
    print(f"phase5_kill_switch_switch_count={written_bundle['switch_count']}")
    print(
        "phase5_kill_switch_required_scope_type_count="
        f"{written_bundle['required_scope_type_count']}"
    )
    print(
        "phase5_kill_switch_required_enforcement_point_count="
        f"{written_bundle['required_enforcement_point_count']}"
    )
    print(
        "phase5_kill_switch_active_switch_count="
        f"{written_bundle['active_switch_count']}"
    )
    print(
        "phase5_kill_switch_blocking_switch_count="
        f"{written_bundle['blocking_switch_count']}"
    )
    print(
        "phase5_kill_switch_fail_closed_default_count="
        f"{written_bundle['fail_closed_default_count']}"
    )
    print(
        "phase5_kill_switch_q5_3_risk_review_count="
        f"{written_bundle['q5_3_risk_review_count']}"
    )
    print(
        "phase5_kill_switch_q5_3_paper_size_eligible_count="
        f"{written_bundle['q5_3_paper_size_eligible_count']}"
    )
    print(f"phase5_kill_switch_event_log_written={written_bundle['event_log_written']}")
    print(f"phase5_kill_switch_event_log_total_events={event_replay['total_events']}")
    print(f"phase5_kill_switch_validation_error_count={len(validation_errors)}")
    print(
        "phase5_kill_switch_execution_allowed_count="
        f"{written_bundle['execution_allowed_count']}"
    )
    print(
        "phase5_kill_switch_paper_order_allowed_count="
        f"{written_bundle['paper_order_allowed_count']}"
    )
    print(
        "phase5_kill_switch_broker_write_allowed_count="
        f"{written_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_kill_switch_telegram_live_notifications_allowed_count="
        f"{written_bundle['telegram_live_notifications_allowed_count']}"
    )
    print(
        "phase5_kill_switch_live_capital_enabled_count="
        f"{written_bundle['live_capital_enabled_count']}"
    )
    print(
        "phase5_kill_switch_mutation_authority_count="
        f"{written_bundle['kill_switch_mutation_authority_count']}"
    )
    print(
        "phase5_kill_switch_missing_state_probe_error_count="
        f"{len(missing_state_errors)}"
    )
    print(
        "phase5_kill_switch_corrupt_state_probe_error_count="
        f"{len(corrupt_state_errors)}"
    )
    print(
        "phase5_kill_switch_active_not_blocking_probe_error_count="
        f"{len(active_not_blocking_errors)}"
    )
    print(
        "phase5_kill_switch_ack_without_event_probe_error_count="
        f"{len(ack_without_event_errors)}"
    )
    print(
        "phase5_kill_switch_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase5_kill_switch_execution_probe_error_count="
        f"{len(execution_errors)}"
    )
    print(
        "phase5_kill_switch_mutation_authority_probe_error_count="
        f"{len(mutation_authority_errors)}"
    )
    print("phase5_kill_switch_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("kill_switch_bundle_not_ok")
    if written_bundle["switch_count"] < len(KILL_SWITCH_SCOPE_TYPES):
        errors.append("kill_switch_count_below_required_scope_types")
    if written_bundle["required_scope_type_count"] != len(KILL_SWITCH_SCOPE_TYPES):
        errors.append("kill_switch_required_scope_type_count_mismatch")
    if written_bundle["q5_3_risk_review_count"] != 5:
        errors.append("kill_switch_q5_3_review_count_not_five")
    if written_bundle["active_switch_count"] != written_bundle["blocking_switch_count"]:
        errors.append("kill_switch_active_blocking_count_mismatch")
    if written_bundle["fail_closed_default_count"] != written_bundle["switch_count"]:
        errors.append("kill_switch_fail_closed_default_count_mismatch")
    if written_bundle["event_log_written"] is not True:
        errors.append("kill_switch_event_log_not_written")
    if event_replay["total_events"] != written_bundle["switch_count"]:
        errors.append("kill_switch_event_log_count_mismatch")
    for scope_type in KILL_SWITCH_SCOPE_TYPES:
        if written_bundle.get("scope_counts", {}).get(scope_type, 0) < 1:
            errors.append(f"kill_switch_scope_type_missing:{scope_type}")
    for key in (
        "risk_approval_allowed_count",
        "risk_agent_handoff_allowed_count",
        "trade_candidate_created_count",
        "execution_policy_handoff_allowed_count",
        "execution_allowed_count",
        "execution_intent_created_count",
        "paper_order_allowed_count",
        "staged_order_created_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_submit_receipt_created_count",
        "prediction_market_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "position_created_count",
        "live_capital_enabled_count",
        "kill_switch_mutation_authority_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"kill_switch_boundary_count_not_zero:{key}")
    if "switch_state_missing_fail_closed" not in missing_state_errors:
        errors.append("missing_state_probe_not_fail_closed")
    if "switch_state_corrupt_fail_closed" not in corrupt_state_errors:
        errors.append("corrupt_state_probe_not_fail_closed")
    if "active_switch_not_blocking" not in active_not_blocking_errors:
        errors.append("active_switch_not_blocking_probe_not_rejected")
    if "acknowledged_without_logged_mutation" not in ack_without_event_errors:
        errors.append("ack_without_event_probe_not_rejected")
    if "kill_switch_boundary_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_probe_not_rejected")
    if "kill_switch_boundary_enabled:execution_allowed" not in execution_errors:
        errors.append("execution_probe_not_rejected")
    if "phase5_authority_enabled:kill_switch_mutation_authority" not in (
        mutation_authority_errors
    ):
        errors.append("mutation_authority_probe_not_rejected")

    if errors:
        for error in errors:
            print(f"phase5_kill_switch_error={error}")
        print("phase5_kill_switch_check=failed")
        return 1

    print("phase5_kill_switch_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
