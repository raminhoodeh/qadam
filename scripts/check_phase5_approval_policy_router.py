#!/usr/bin/env python3
"""Validate the Q5-2 approval policy router."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_approval_policy import (  # noqa: E402
    PHASE5_APPROVAL_POLICY_SCHEMA_VERSION,
    build_phase5_approval_policy_decisions,
    phase5_approval_policy_paths,
    validate_phase5_approval_policy_bundle,
    validate_phase5_approval_policy_decision,
    write_phase5_approval_policy_decisions,
)


def _first_decision(bundle: dict) -> dict:
    decisions = bundle.get("decisions", [])
    if not decisions:
        raise RuntimeError("no approval policy decisions produced")
    return decisions[0]


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_approval_policy_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_approval_policy_decisions(settings=settings)
    output_path, history_path, event_log_path, written_bundle = (
        write_phase5_approval_policy_decisions(
            bundle,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase5_approval_policy_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()

    unapproved_probe = deepcopy(_first_decision(written_bundle))
    unapproved_probe["approved_strategy_toggle_state"] = "draft"
    unapproved_probe["status"] = "eligible"
    unapproved_probe["policy_decision"] = "eligible_for_q5_3_risk_sizing_contract"
    unapproved_errors = validate_phase5_approval_policy_decision(unapproved_probe)

    broker_probe = deepcopy(_first_decision(written_bundle))
    broker_probe["broker_write_allowed"] = True
    broker_errors = validate_phase5_approval_policy_decision(broker_probe)

    staged_order_probe = deepcopy(_first_decision(written_bundle))
    staged_order_probe["staged_order_created"] = True
    staged_order_errors = validate_phase5_approval_policy_decision(staged_order_probe)

    receipt_probe = deepcopy(_first_decision(written_bundle))
    receipt_probe["broker_post_called"] = True
    receipt_errors = validate_phase5_approval_policy_decision(receipt_probe)

    position_probe = deepcopy(_first_decision(written_bundle))
    position_probe["position_created"] = True
    position_errors = validate_phase5_approval_policy_decision(position_probe)

    yahoo_probe = deepcopy(_first_decision(written_bundle))
    yahoo_probe["yahoo_finance_role"] = "canonical_source"
    yahoo_errors = validate_phase5_approval_policy_decision(yahoo_probe)

    preference_probe = deepcopy(_first_decision(written_bundle))
    preference_probe["preference_mcp_source_36"] = True
    preference_probe["preference_source_quorum_credit_allowed"] = True
    preference_errors = validate_phase5_approval_policy_decision(preference_probe)

    print("phase5_approval_policy_status=" + written_bundle["status"])
    print(f"phase5_approval_policy_schema_version={PHASE5_APPROVAL_POLICY_SCHEMA_VERSION}")
    print(f"phase5_approval_policy_artifact_path={output_path}")
    print(f"phase5_approval_policy_history_path={history_path}")
    print(f"phase5_approval_policy_event_log_path={event_log_path}")
    print(f"phase5_approval_policy_decision_count={written_bundle['decision_count']}")
    print(f"phase5_approval_policy_eligible_count={written_bundle['eligible_count']}")
    print(f"phase5_approval_policy_hold_count={written_bundle['hold_count']}")
    print(f"phase5_approval_policy_blocked_count={written_bundle['blocked_count']}")
    print(
        "phase5_approval_policy_approved_shadow_toggle_count="
        f"{written_bundle['approved_shadow_toggle_count']}"
    )
    print(
        "phase5_approval_policy_phase5_implementation_allowed="
        f"{written_bundle['phase5_layer_b_implementation_allowed']}"
    )
    print(
        "phase5_approval_policy_orchestration_start_allowed="
        f"{written_bundle['phase5_orchestration_start_allowed']}"
    )
    print(f"phase5_approval_policy_phase4_certified={written_bundle['phase4_certified']}")
    print(f"phase5_approval_policy_phase5_handoff_allowed={written_bundle['phase5_handoff_allowed']}")
    print(f"phase5_approval_policy_event_log_written={written_bundle['event_log_written']}")
    print(f"phase5_approval_policy_event_log_total_events={event_replay['total_events']}")
    print(f"phase5_approval_policy_validation_error_count={len(validation_errors)}")
    print(f"phase5_approval_policy_global_error_count={written_bundle['global_policy_error_count']}")
    print(
        "phase5_approval_policy_trade_candidate_created_count="
        f"{written_bundle['trade_candidate_created_count']}"
    )
    print(
        "phase5_approval_policy_risk_handoff_allowed_count="
        f"{written_bundle['risk_agent_handoff_allowed_count']}"
    )
    print(
        "phase5_approval_policy_execution_allowed_count="
        f"{written_bundle['execution_allowed_count']}"
    )
    print(
        "phase5_approval_policy_paper_order_allowed_count="
        f"{written_bundle['paper_order_allowed_count']}"
    )
    print(
        "phase5_approval_policy_broker_write_allowed_count="
        f"{written_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_approval_policy_position_created_count="
        f"{written_bundle['position_created_count']}"
    )
    print(
        "phase5_approval_policy_preference_source36="
        f"{written_bundle['preference_mcp_source_36']}"
    )
    print(f"phase5_approval_policy_yahoo_role={written_bundle['yahoo_finance_role']}")
    print(f"phase5_approval_policy_unapproved_probe_error_count={len(unapproved_errors)}")
    print(f"phase5_approval_policy_broker_probe_error_count={len(broker_errors)}")
    print(f"phase5_approval_policy_staged_order_probe_error_count={len(staged_order_errors)}")
    print(f"phase5_approval_policy_receipt_probe_error_count={len(receipt_errors)}")
    print(f"phase5_approval_policy_position_probe_error_count={len(position_errors)}")
    print(f"phase5_approval_policy_yahoo_probe_error_count={len(yahoo_errors)}")
    print(f"phase5_approval_policy_preference_probe_error_count={len(preference_errors)}")
    print("phase5_approval_policy_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("approval_policy_bundle_not_ok")
    if written_bundle["decision_count"] != 5:
        errors.append("approval_policy_decision_count_not_five")
    if written_bundle["eligible_count"] != 5:
        errors.append("approval_policy_eligible_count_not_five")
    if written_bundle["hold_count"] != 0:
        errors.append("approval_policy_hold_count_not_zero")
    if written_bundle["blocked_count"] != 0:
        errors.append("approval_policy_blocked_count_not_zero")
    if written_bundle["global_policy_error_count"] != 0:
        errors.append("approval_policy_global_errors_present")
    if written_bundle["phase4_certified"] is not True:
        errors.append("phase4_not_certified")
    if written_bundle["phase5_handoff_allowed"] is not True:
        errors.append("phase5_handoff_not_allowed")
    if written_bundle["phase5_layer_b_implementation_allowed"] is not True:
        errors.append("phase5_implementation_not_allowed")
    if written_bundle["phase5_orchestration_start_allowed"] is not False:
        errors.append("phase5_orchestration_start_allowed")
    if written_bundle["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if event_replay["total_events"] != written_bundle["decision_count"]:
        errors.append("event_log_decision_count_mismatch")
    for key in (
        "trade_candidate_created_count",
        "risk_agent_handoff_allowed_count",
        "risk_sizing_review_created_count",
        "execution_allowed_count",
        "execution_intent_created_count",
        "paper_order_allowed_count",
        "staged_order_created_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_submit_receipt_created_count",
        "position_created_count",
        "live_capital_enabled_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"approval_policy_boundary_count_not_zero:{key}")
    if "eligible_without_approved_shadow_toggle" not in unapproved_errors:
        errors.append("unapproved_probe_not_rejected")
    if "policy_decision_order_boundary_enabled:broker_write_allowed" not in broker_errors:
        errors.append("broker_probe_not_rejected")
    if "policy_decision_order_boundary_enabled:staged_order_created" not in staged_order_errors:
        errors.append("staged_order_probe_not_rejected")
    if "policy_decision_order_boundary_enabled:broker_post_called" not in receipt_errors:
        errors.append("receipt_probe_not_rejected")
    if "policy_decision_order_boundary_enabled:position_created" not in position_errors:
        errors.append("position_probe_not_rejected")
    if "yahoo_finance_role_not_supplemental" not in yahoo_errors:
        errors.append("yahoo_probe_not_rejected")
    if "preference_mcp_source_36" not in preference_errors:
        errors.append("preference_source36_probe_not_rejected")
    if "preference_source_quorum_credit_allowed" not in preference_errors:
        errors.append("preference_source_quorum_probe_not_rejected")

    if errors:
        for error in errors:
            print(f"phase5_approval_policy_error={error}")
        print("phase5_approval_policy_check=failed")
        return 1

    print("phase5_approval_policy_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
