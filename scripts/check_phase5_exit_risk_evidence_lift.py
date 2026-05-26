#!/usr/bin/env python3
"""Validate Q5E-1 Phase 5 exit risk-evidence lift."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_exit_evidence_lift import (  # noqa: E402
    PHASE5_EXIT_RISK_EVIDENCE_LIFT_SCHEMA_VERSION,
    TARGET_STRATEGY_FAMILY_KEY,
    phase5_exit_risk_evidence_lift_paths,
    validate_phase5_exit_risk_evidence_lift,
    write_phase5_exit_risk_evidence_lift,
)
from orchestrator.phase5_risk_sizing import (  # noqa: E402
    validate_phase5_risk_sizing_bundle,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_exit_risk_evidence_lift_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    output_path, history_path, event_log_path, artifact = write_phase5_exit_risk_evidence_lift(
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_exit_risk_evidence_lift(artifact)
    event_replay = EventLog(event_log_path, echo=False).replay()

    risk_validation_error_count = int(artifact.get("risk_sizing_validation_error_count", 0) or 0)
    if validation_errors:
        errors.extend(validation_errors)
    if artifact.get("status") != "ok":
        errors.append("q5e_1_artifact_not_ok")
    if risk_validation_error_count != 0:
        errors.append("q5e_1_risk_sizing_validation_errors_present")
    if artifact.get("target_strategy_family_key") != TARGET_STRATEGY_FAMILY_KEY:
        errors.append("q5e_1_target_strategy_mismatch")
    if artifact.get("signal_integrity_status") != "passed_to_risk_shadow":
        errors.append("q5e_1_signal_integrity_not_passed")
    if artifact.get("market_confirmation_status") != "market_confirmation_corroboration_available":
        errors.append("q5e_1_market_confirmation_not_available")
    if artifact.get("pricing_gap") != "pass_pricing_gap_confirmed":
        errors.append("q5e_1_pricing_gap_not_confirmed")
    if artifact.get("uses_yahoo_finance") is not False:
        errors.append("q5e_1_yahoo_finance_not_supplemental")
    if int(artifact.get("paper_size_eligible_count", 0) or 0) < 1:
        errors.append("q5e_1_no_paper_size_eligible_setup")
    if artifact.get("target_paper_size_eligible") is not True:
        errors.append("q5e_1_target_not_paper_size_eligible")
    if float(artifact.get("target_proposed_risk_gbp", 0.0) or 0.0) <= 0:
        errors.append("q5e_1_target_risk_not_positive")
    if int(artifact.get("target_risk_blocker_count", 0) or 0) != 0:
        errors.append("q5e_1_target_has_risk_blockers")
    for key in (
        "risk_approval_allowed_count",
        "trade_candidate_created_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "staged_order_created_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_submit_receipt_created_count",
        "position_created_count",
        "live_capital_enabled_count",
    ):
        if int(artifact.get(key, 0) or 0) != 0:
            errors.append(f"q5e_1_authority_count_not_zero:{key}")
    if artifact.get("event_log_written") is not True:
        errors.append("q5e_1_event_log_not_written")
    if event_replay["total_events"] != 2 and event_replay["total_events"] != 1:
        errors.append("q5e_1_event_log_unexpected_count")

    print("phase5_exit_risk_evidence_lift_status=" + str(artifact["status"]))
    print(
        "phase5_exit_risk_evidence_lift_schema_version="
        f"{PHASE5_EXIT_RISK_EVIDENCE_LIFT_SCHEMA_VERSION}"
    )
    print(f"phase5_exit_risk_evidence_lift_artifact_path={output_path}")
    print(f"phase5_exit_risk_evidence_lift_history_path={history_path}")
    print(f"phase5_exit_risk_evidence_lift_event_log_path={event_log_path}")
    print(
        "phase5_exit_risk_evidence_lift_target_strategy_family_key="
        f"{artifact['target_strategy_family_key']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_signal_integrity_status="
        f"{artifact['signal_integrity_status']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_market_confirmation_status="
        f"{artifact['market_confirmation_status']}"
    )
    print(f"phase5_exit_risk_evidence_lift_pricing_gap={artifact['pricing_gap']}")
    print(
        "phase5_exit_risk_evidence_lift_uses_yahoo_finance="
        f"{artifact['uses_yahoo_finance']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_paper_size_eligible_count="
        f"{artifact['paper_size_eligible_count']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_target_paper_size_eligible="
        f"{artifact['target_paper_size_eligible']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_target_proposed_risk_gbp="
        f"{artifact['target_proposed_risk_gbp']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_target_max_risk_gbp="
        f"{artifact['target_max_risk_gbp']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_target_risk_blocker_count="
        f"{artifact['target_risk_blocker_count']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_risk_validation_error_count="
        f"{risk_validation_error_count}"
    )
    print(
        "phase5_exit_risk_evidence_lift_event_log_written="
        f"{artifact['event_log_written']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_broker_write_allowed_count="
        f"{artifact['broker_write_allowed_count']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_paper_order_submitted_count="
        f"{artifact['paper_order_submitted_count']}"
    )
    print(
        "phase5_exit_risk_evidence_lift_live_capital_enabled_count="
        f"{artifact['live_capital_enabled_count']}"
    )
    print("phase5_exit_risk_evidence_lift_boundary=" + artifact["boundary"])

    if errors:
        for error in errors:
            print(f"phase5_exit_risk_evidence_lift_error={error}")
        print("phase5_exit_risk_evidence_lift_check=failed")
        return 1

    print("phase5_exit_risk_evidence_lift_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
