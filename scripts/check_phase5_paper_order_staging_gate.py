#!/usr/bin/env python3
"""Validate the Q5-6 paper-order staging gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_paper_order_staging import (  # noqa: E402
    PAPER_ORDER_STAGING_REQUIRED_CHECKS,
    PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION,
    build_phase5_paper_order_staging_gate,
    phase5_paper_order_staging_paths,
    validate_phase5_paper_order_staging_bundle,
    validate_phase5_paper_order_staging_record,
    write_phase5_paper_order_staging_gate,
)


def _first_record(bundle: dict) -> dict:
    records = bundle.get("records", [])
    if not records:
        raise RuntimeError("no paper-order staging records produced")
    return records[0]


def _staged_probe(record: dict) -> dict:
    probe = deepcopy(record)
    probe["status"] = "staged"
    probe["order_state"] = "staged_ready_for_dry_run"
    probe["staging_allowed"] = True
    probe["blocked_reasons"] = []
    probe["blocked_reason_count"] = 0
    probe["failed_checks"] = []
    probe["failed_check_count"] = 0
    probe["approval_policy_status"] = "eligible"
    probe["risk_decision"] = "paper_size_eligible"
    probe["paper_size_eligible"] = True
    probe["proposed_risk_gbp"] = max(1.0, float(probe.get("proposed_risk_gbp") or 0.0))
    probe["max_loss_gbp"] = min(
        float(probe["proposed_risk_gbp"]),
        max(1.0, float(probe.get("max_loss_gbp") or 0.0)),
    )
    probe["risk_size_gbp"] = probe["max_loss_gbp"]
    probe["kill_switch_clear"] = True
    probe["kill_switch_active_switches"] = []
    probe["kill_switch_validation_error_count"] = 0
    probe["execution_adapter_read_health"] = "read_only_available"
    probe["execution_adapter_write_health"] = "blocked_q5_6_staging_contract"
    probe["side"] = "buy"
    probe["quantity"] = 1.0
    probe["notional_gbp"] = 1.0
    probe["order_type"] = "market"
    probe["time_in_force"] = "day"
    probe["event_log_prewrite_ready"] = True
    probe["idempotency_key"] = "q5-6-test-idempotency-key"
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_paper_order_staging_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_paper_order_staging_gate(settings=settings)
    output_path, history_path, event_log_path, written_bundle = (
        write_phase5_paper_order_staging_gate(
            bundle,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase5_paper_order_staging_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    first_record = _first_record(written_bundle)

    missing_risk_probe = _staged_probe(first_record)
    missing_risk_probe["paper_size_eligible"] = False
    missing_risk_errors = validate_phase5_paper_order_staging_record(missing_risk_probe)

    active_kill_probe = _staged_probe(first_record)
    active_kill_probe["kill_switch_clear"] = False
    active_kill_probe["kill_switch_active_switches"] = ["global:all"]
    active_kill_errors = validate_phase5_paper_order_staging_record(active_kill_probe)

    prewrite_probe = _staged_probe(first_record)
    prewrite_probe["event_log_prewrite_ready"] = False
    prewrite_errors = validate_phase5_paper_order_staging_record(prewrite_probe)

    source_coverage_probe = _staged_probe(first_record)
    source_coverage_probe["source_summary"]["decision_source_usage_complete"] = False
    source_coverage_probe["source_summary"]["decision_source_coverage"][
        "decision_source_usage_complete"
    ] = False
    source_coverage_errors = validate_phase5_paper_order_staging_record(
        source_coverage_probe
    )

    idempotency_probe = _staged_probe(first_record)
    idempotency_probe["idempotency_key"] = None
    idempotency_errors = validate_phase5_paper_order_staging_record(idempotency_probe)

    quantity_probe = _staged_probe(first_record)
    quantity_probe["quantity"] = 0.0
    quantity_errors = validate_phase5_paper_order_staging_record(quantity_probe)

    side_probe = _staged_probe(first_record)
    side_probe["side"] = "hold"
    side_errors = validate_phase5_paper_order_staging_record(side_probe)

    submission_probe = deepcopy(first_record)
    submission_probe["submission_allowed"] = True
    submission_errors = validate_phase5_paper_order_staging_record(submission_probe)

    broker_write_probe = deepcopy(first_record)
    broker_write_probe["broker_write_allowed"] = True
    broker_write_errors = validate_phase5_paper_order_staging_record(broker_write_probe)

    live_capital_probe = deepcopy(first_record)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_phase5_paper_order_staging_record(live_capital_probe)

    exposure_probe = deepcopy(first_record)
    exposure_probe["raw_payload_exposed"] = True
    exposure_errors = validate_phase5_paper_order_staging_record(exposure_probe)

    print("phase5_paper_order_staging_status=" + written_bundle["status"])
    print(
        "phase5_paper_order_staging_schema_version="
        f"{PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION}"
    )
    print(f"phase5_paper_order_staging_artifact_path={output_path}")
    print(f"phase5_paper_order_staging_history_path={history_path}")
    print(f"phase5_paper_order_staging_event_log_path={event_log_path}")
    print(
        "phase5_paper_order_staging_record_count="
        f"{written_bundle['staging_record_count']}"
    )
    print(
        "phase5_paper_order_staging_risk_review_count="
        f"{written_bundle['risk_review_count']}"
    )
    print(
        "phase5_paper_order_staging_paper_size_eligible_count="
        f"{written_bundle['paper_size_eligible_count']}"
    )
    print(
        "phase5_paper_order_staging_staged_order_count="
        f"{written_bundle['staged_order_count']}"
    )
    print(
        "phase5_paper_order_staging_blocked_count="
        f"{written_bundle['blocked_count']}"
    )
    print(
        "phase5_paper_order_staging_required_check_count="
        f"{written_bundle['required_check_count']}"
    )
    print(
        "phase5_paper_order_staging_reconciliation_prerequisite_count="
        f"{written_bundle['reconciliation_prerequisite_count']}"
    )
    print(
        "phase5_paper_order_staging_cancellation_condition_count="
        f"{written_bundle['cancellation_condition_count']}"
    )
    print(
        "phase5_paper_order_staging_event_log_written="
        f"{written_bundle['event_log_written']}"
    )
    print(
        "phase5_paper_order_staging_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_paper_order_staging_validation_error_count="
        f"{len(validation_errors)}"
    )
    print(
        "phase5_paper_order_staging_broker_write_allowed_count="
        f"{written_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_paper_order_staging_broker_post_called_count="
        f"{written_bundle['broker_post_called_count']}"
    )
    print(
        "phase5_paper_order_staging_paper_order_submitted_count="
        f"{written_bundle['paper_order_submitted_count']}"
    )
    print(
        "phase5_paper_order_staging_live_capital_enabled_count="
        f"{written_bundle['live_capital_enabled_count']}"
    )
    print(
        "phase5_paper_order_staging_missing_risk_probe_error_count="
        f"{len(missing_risk_errors)}"
    )
    print(
        "phase5_paper_order_staging_active_kill_probe_error_count="
        f"{len(active_kill_errors)}"
    )
    print(
        "phase5_paper_order_staging_prewrite_probe_error_count="
        f"{len(prewrite_errors)}"
    )
    print(
        "phase5_paper_order_staging_source_coverage_probe_error_count="
        f"{len(source_coverage_errors)}"
    )
    print(
        "phase5_paper_order_staging_idempotency_probe_error_count="
        f"{len(idempotency_errors)}"
    )
    print(
        "phase5_paper_order_staging_quantity_probe_error_count="
        f"{len(quantity_errors)}"
    )
    print(
        "phase5_paper_order_staging_side_probe_error_count="
        f"{len(side_errors)}"
    )
    print(
        "phase5_paper_order_staging_submission_probe_error_count="
        f"{len(submission_errors)}"
    )
    print(
        "phase5_paper_order_staging_broker_write_probe_error_count="
        f"{len(broker_write_errors)}"
    )
    print(
        "phase5_paper_order_staging_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase5_paper_order_staging_exposure_probe_error_count="
        f"{len(exposure_errors)}"
    )
    print("phase5_paper_order_staging_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("paper_order_staging_bundle_not_ok")
    if written_bundle["staging_record_count"] != written_bundle["risk_review_count"]:
        errors.append("paper_order_staging_record_count_mismatch")
    if written_bundle["risk_review_count"] != 5:
        errors.append("paper_order_staging_risk_review_count_not_five")
    if written_bundle["paper_size_eligible_count"] == 0:
        if written_bundle["staged_order_count"] != 0:
            errors.append("paper_order_staging_created_order_without_eligible_risk")
        if written_bundle["blocked_count"] != written_bundle["staging_record_count"]:
            errors.append("paper_order_staging_blocked_count_mismatch")
    else:
        staged_records = [
            record
            for record in written_bundle.get("records", [])
            if isinstance(record, dict) and record.get("status") == "staged"
        ]
        if written_bundle["staged_order_count"] < 1:
            errors.append("paper_order_staging_missing_staged_order_for_eligible_risk")
        if written_bundle["blocked_count"] + written_bundle["staged_order_count"] != written_bundle["staging_record_count"]:
            errors.append("paper_order_staging_status_count_mismatch")
        if not any(record.get("selected_venue") == "alpaca_paper" for record in staged_records):
            errors.append("paper_order_staging_no_alpaca_paper_staged_order")
        for record in staged_records:
            if record.get("submission_allowed") is not False:
                errors.append("paper_order_staging_staged_record_submission_allowed")
            if record.get("broker_write_allowed") is not False:
                errors.append("paper_order_staging_staged_record_broker_write_allowed")
            if record.get("paper_order_submitted") is not False:
                errors.append("paper_order_staging_staged_record_submitted")
            if record.get("live_capital_enabled") is not False:
                errors.append("paper_order_staging_staged_record_live_capital_enabled")
            if not str(record.get("idempotency_key") or "").strip():
                errors.append("paper_order_staging_staged_record_missing_idempotency_key")
            if record.get("event_log_prewrite_ready") is not True:
                errors.append("paper_order_staging_staged_record_missing_prewrite")
    if written_bundle["required_check_count"] != len(PAPER_ORDER_STAGING_REQUIRED_CHECKS):
        errors.append("paper_order_staging_required_check_count_mismatch")
    if written_bundle["event_log_written"] is not True:
        errors.append("paper_order_staging_event_log_not_written")
    if event_replay["total_events"] != written_bundle["staging_record_count"]:
        errors.append("paper_order_staging_event_log_count_mismatch")
    for key in (
        "risk_approval_allowed_count",
        "trade_candidate_created_count",
        "execution_allowed_count",
        "execution_intent_created_count",
        "paper_execution_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submission_allowed_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "broker_submit_receipt_created_count",
        "prediction_market_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "position_created_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "crypto_perps_write_allowed_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"paper_order_staging_boundary_count_not_zero:{key}")
    if "staged_order_without_risk_eligibility" not in missing_risk_errors:
        errors.append("missing_risk_probe_not_rejected")
    if "staged_order_without_kill_switch_clear" not in active_kill_errors:
        errors.append("active_kill_probe_not_rejected")
    if "staged_order_without_event_log_prewrite" not in prewrite_errors:
        errors.append("prewrite_probe_not_rejected")
    if "staged_order_without_decision_source_coverage" not in source_coverage_errors:
        errors.append("source_coverage_probe_not_rejected")
    if "staged_order_without_idempotency_key" not in idempotency_errors:
        errors.append("idempotency_probe_not_rejected")
    if "staged_order_without_positive_quantity" not in quantity_errors:
        errors.append("quantity_probe_not_rejected")
    if "staged_order_invalid_side" not in side_errors:
        errors.append("side_probe_not_rejected")
    if "paper_order_staging_boundary_enabled:submission_allowed" not in submission_errors:
        errors.append("submission_probe_not_rejected")
    if "paper_order_staging_boundary_enabled:broker_write_allowed" not in broker_write_errors:
        errors.append("broker_write_probe_not_rejected")
    if "paper_order_staging_boundary_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_probe_not_rejected")
    if "paper_order_staging_exposure_enabled:raw_payload_exposed" not in exposure_errors:
        errors.append("exposure_probe_not_rejected")

    if errors:
        for error in errors:
            print(f"phase5_paper_order_staging_error={error}")
        print("phase5_paper_order_staging_check=failed")
        return 1

    print("phase5_paper_order_staging_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
