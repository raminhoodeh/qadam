#!/usr/bin/env python3
"""Validate Q5E-2 staged paper-order creation from Q5E-1 eligibility."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_execution_adapter_status import (  # noqa: E402
    build_phase5_execution_adapter_status,
    phase5_execution_adapter_status_paths,
    validate_phase5_execution_adapter_status_bundle,
    write_phase5_execution_adapter_status,
)
from orchestrator.phase5_exit_evidence_lift import (  # noqa: E402
    TARGET_STRATEGY_FAMILY_KEY,
    validate_phase5_exit_risk_evidence_lift,
    write_phase5_exit_risk_evidence_lift,
)
from orchestrator.phase5_kill_switch import (  # noqa: E402
    build_phase5_kill_switch_ledger,
    phase5_kill_switch_paths,
    validate_phase5_kill_switch_ledger,
    write_phase5_kill_switch_ledger,
)
from orchestrator.phase5_paper_order_staging import (  # noqa: E402
    PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION,
    build_phase5_paper_order_staging_gate,
    phase5_paper_order_staging_paths,
    validate_phase5_paper_order_staging_bundle,
    write_phase5_paper_order_staging_gate,
)


def _adapter_by_venue(bundle: dict) -> dict[str, dict]:
    return {
        str(record.get("venue_key") or ""): record
        for record in bundle.get("statuses", [])
        if isinstance(record, dict)
    }


def _target_staged_record(bundle: dict) -> dict:
    for record in bundle.get("records", []):
        if (
            isinstance(record, dict)
            and record.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY
            and record.get("status") == "staged"
        ):
            return record
    return {}


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()

    _, _, q5e1_event_log_path, q5e1_artifact = write_phase5_exit_risk_evidence_lift(
        settings=settings,
        record_event=True,
    )
    q5e1_errors = validate_phase5_exit_risk_evidence_lift(q5e1_artifact)

    _, _, kill_event_log_path = phase5_kill_switch_paths(settings)
    if kill_event_log_path.exists():
        kill_event_log_path.unlink()
    kill_bundle = build_phase5_kill_switch_ledger(settings=settings)
    _, _, kill_event_log_path, written_kill_bundle = write_phase5_kill_switch_ledger(
        kill_bundle,
        settings=settings,
        record_event=True,
        event_log_path=kill_event_log_path,
    )
    kill_errors = validate_phase5_kill_switch_ledger(written_kill_bundle)

    _, _, adapter_event_log_path = phase5_execution_adapter_status_paths(settings)
    if adapter_event_log_path.exists():
        adapter_event_log_path.unlink()
    adapter_bundle = build_phase5_execution_adapter_status(settings=settings)
    _, _, adapter_event_log_path, written_adapter_bundle = write_phase5_execution_adapter_status(
        adapter_bundle,
        settings=settings,
        record_event=True,
        event_log_path=adapter_event_log_path,
    )
    adapter_errors = validate_phase5_execution_adapter_status_bundle(written_adapter_bundle)
    alpaca_adapter = _adapter_by_venue(written_adapter_bundle).get("alpaca_paper", {})

    output_path, history_path, staging_event_log_path = phase5_paper_order_staging_paths(settings)
    if staging_event_log_path.exists():
        staging_event_log_path.unlink()
    staging_bundle = build_phase5_paper_order_staging_gate(settings=settings)
    output_path, history_path, staging_event_log_path, written_staging_bundle = (
        write_phase5_paper_order_staging_gate(
            staging_bundle,
            settings=settings,
            record_event=True,
            event_log_path=staging_event_log_path,
        )
    )
    staging_errors = validate_phase5_paper_order_staging_bundle(written_staging_bundle)
    staging_replay = EventLog(staging_event_log_path, echo=False).replay()
    target = _target_staged_record(written_staging_bundle)

    if q5e1_errors:
        errors.append("q5e_1_validation_errors:" + ",".join(q5e1_errors))
    if kill_errors:
        errors.append("q5_4_validation_errors:" + ",".join(kill_errors))
    if adapter_errors:
        errors.append("q5_5_validation_errors:" + ",".join(adapter_errors))
    if staging_errors:
        errors.append("q5_6_validation_errors:" + ",".join(staging_errors))
    if q5e1_artifact.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_2_missing_q5e_1_eligible_setup")
    if written_staging_bundle.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_2_staging_source_has_no_eligible_risk")
    if written_staging_bundle.get("staged_order_count", 0) < 1:
        errors.append("q5e_2_missing_staged_paper_order")
    if not target:
        errors.append("q5e_2_target_staged_record_missing")
    if target:
        if target.get("selected_venue") != "alpaca_paper":
            errors.append("q5e_2_target_not_alpaca_paper")
        if target.get("order_state") != "staged_ready_for_dry_run":
            errors.append("q5e_2_target_order_state_invalid")
        if target.get("staging_allowed") is not True:
            errors.append("q5e_2_target_staging_not_allowed")
        if target.get("submission_allowed") is not False:
            errors.append("q5e_2_target_submission_allowed")
        if target.get("broker_write_allowed") is not False:
            errors.append("q5e_2_target_broker_write_allowed")
        if target.get("paper_order_submitted") is not False:
            errors.append("q5e_2_target_paper_order_submitted")
        if target.get("live_capital_enabled") is not False:
            errors.append("q5e_2_target_live_capital_enabled")
        if target.get("event_log_prewrite_ready") is not True:
            errors.append("q5e_2_target_prewrite_not_ready")
        if not str(target.get("idempotency_key") or "").strip():
            errors.append("q5e_2_target_idempotency_key_missing")
        if target.get("side") not in {"buy", "sell"}:
            errors.append("q5e_2_target_side_invalid")
        if float(target.get("quantity", 0.0) or 0.0) <= 0:
            errors.append("q5e_2_target_quantity_not_positive")
        if target.get("order_type") != "market":
            errors.append("q5e_2_target_order_type_not_market")
        if target.get("time_in_force") != "day":
            errors.append("q5e_2_target_tif_not_day")
    if alpaca_adapter.get("read_health") != "read_only_available":
        errors.append("q5e_2_alpaca_read_not_available")
    if not str(alpaca_adapter.get("write_health") or "").startswith("blocked"):
        errors.append("q5e_2_alpaca_write_not_blocked")
    if written_kill_bundle.get("blocking_switch_count", 0) != 0:
        errors.append("q5e_2_kill_switch_blocking")
    if staging_replay["total_events"] != written_staging_bundle.get("staging_record_count"):
        errors.append("q5e_2_staging_event_log_count_mismatch")
    for key in (
        "paper_order_submission_allowed_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "broker_submit_receipt_created_count",
        "prediction_market_write_allowed_count",
        "position_created_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
    ):
        if int(written_staging_bundle.get(key, 0) or 0) != 0:
            errors.append(f"q5e_2_boundary_count_not_zero:{key}")

    print("phase5_exit_paper_order_staging_status=" + written_staging_bundle["status"])
    print(
        "phase5_exit_paper_order_staging_schema_version="
        f"{PHASE5_PAPER_ORDER_STAGING_SCHEMA_VERSION}"
    )
    print(f"phase5_exit_paper_order_staging_artifact_path={output_path}")
    print(f"phase5_exit_paper_order_staging_history_path={history_path}")
    print(f"phase5_exit_paper_order_staging_event_log_path={staging_event_log_path}")
    print(f"phase5_exit_paper_order_staging_q5e1_event_log_path={q5e1_event_log_path}")
    print(
        "phase5_exit_paper_order_staging_target_strategy_family_key="
        f"{TARGET_STRATEGY_FAMILY_KEY}"
    )
    print(
        "phase5_exit_paper_order_staging_paper_size_eligible_count="
        f"{written_staging_bundle['paper_size_eligible_count']}"
    )
    print(
        "phase5_exit_paper_order_staging_staged_order_count="
        f"{written_staging_bundle['staged_order_count']}"
    )
    print(
        "phase5_exit_paper_order_staging_blocked_count="
        f"{written_staging_bundle['blocked_count']}"
    )
    print(
        "phase5_exit_paper_order_staging_target_record_present="
        f"{bool(target)}"
    )
    print(
        "phase5_exit_paper_order_staging_target_selected_venue="
        f"{target.get('selected_venue', 'missing')}"
    )
    print(
        "phase5_exit_paper_order_staging_target_order_state="
        f"{target.get('order_state', 'missing')}"
    )
    print(
        "phase5_exit_paper_order_staging_target_idempotency_key_present="
        f"{bool(str(target.get('idempotency_key') or '').strip())}"
    )
    print(
        "phase5_exit_paper_order_staging_target_side="
        f"{target.get('side', 'missing')}"
    )
    print(
        "phase5_exit_paper_order_staging_target_quantity="
        f"{target.get('quantity', 'missing')}"
    )
    print(
        "phase5_exit_paper_order_staging_target_order_type="
        f"{target.get('order_type', 'missing')}"
    )
    print(
        "phase5_exit_paper_order_staging_target_time_in_force="
        f"{target.get('time_in_force', 'missing')}"
    )
    print(
        "phase5_exit_paper_order_staging_event_log_total_events="
        f"{staging_replay['total_events']}"
    )
    print(
        "phase5_exit_paper_order_staging_broker_write_allowed_count="
        f"{written_staging_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_exit_paper_order_staging_broker_post_called_count="
        f"{written_staging_bundle['broker_post_called_count']}"
    )
    print(
        "phase5_exit_paper_order_staging_paper_order_submitted_count="
        f"{written_staging_bundle['paper_order_submitted_count']}"
    )
    print(
        "phase5_exit_paper_order_staging_live_capital_enabled_count="
        f"{written_staging_bundle['live_capital_enabled_count']}"
    )
    print("phase5_exit_paper_order_staging_boundary=" + written_staging_bundle["boundary"])

    if errors:
        for error in errors:
            print(f"phase5_exit_paper_order_staging_error={error}")
        print("phase5_exit_paper_order_staging_check=failed")
        return 1

    print("phase5_exit_paper_order_staging_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
