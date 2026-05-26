#!/usr/bin/env python3
"""Validate Q5E-3 Alpaca paper dry-run preview from staged Q5E order."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_alpaca_paper_dry_run import (  # noqa: E402
    PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
    build_phase5_alpaca_paper_dry_run,
    phase5_alpaca_paper_dry_run_paths,
    validate_phase5_alpaca_paper_dry_run_bundle,
    write_phase5_alpaca_paper_dry_run,
)
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
    build_phase5_paper_order_staging_gate,
    phase5_paper_order_staging_paths,
    validate_phase5_paper_order_staging_bundle,
    write_phase5_paper_order_staging_gate,
)


def _target_dry_run_record(bundle: dict) -> dict:
    for record in bundle.get("records", []):
        if (
            isinstance(record, dict)
            and record.get("strategy_family_key") == TARGET_STRATEGY_FAMILY_KEY
        ):
            return record
    return {}


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

    _, _, _, q5e1_artifact = write_phase5_exit_risk_evidence_lift(
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

    _, _, staging_event_log_path = phase5_paper_order_staging_paths(settings)
    if staging_event_log_path.exists():
        staging_event_log_path.unlink()
    staging_bundle = build_phase5_paper_order_staging_gate(settings=settings)
    _, _, staging_event_log_path, written_staging_bundle = write_phase5_paper_order_staging_gate(
        staging_bundle,
        settings=settings,
        record_event=True,
        event_log_path=staging_event_log_path,
    )
    staging_errors = validate_phase5_paper_order_staging_bundle(written_staging_bundle)
    target_staged = _target_staged_record(written_staging_bundle)

    output_path, history_path, dry_run_event_log_path = phase5_alpaca_paper_dry_run_paths(
        settings
    )
    if dry_run_event_log_path.exists():
        dry_run_event_log_path.unlink()
    dry_run_bundle = build_phase5_alpaca_paper_dry_run(settings=settings)
    output_path, history_path, dry_run_event_log_path, written_dry_run_bundle = (
        write_phase5_alpaca_paper_dry_run(
            dry_run_bundle,
            settings=settings,
            record_event=True,
            event_log_path=dry_run_event_log_path,
        )
    )
    dry_run_errors = validate_phase5_alpaca_paper_dry_run_bundle(written_dry_run_bundle)
    dry_run_replay = EventLog(dry_run_event_log_path, echo=False).replay()
    target = _target_dry_run_record(written_dry_run_bundle)

    request_preview = target.get("request_preview", {}) if target else {}
    simulated_receipt = target.get("simulated_submit_receipt", {}) if target else {}
    duplicate_guard = target.get("duplicate_order_guard", {}) if target else {}
    pre_trade_snapshot = target.get("pre_trade_snapshot_schema", {}) if target else {}

    if q5e1_errors:
        errors.append("q5e_1_validation_errors:" + ",".join(q5e1_errors))
    if kill_errors:
        errors.append("q5_4_validation_errors:" + ",".join(kill_errors))
    if adapter_errors:
        errors.append("q5_5_validation_errors:" + ",".join(adapter_errors))
    if staging_errors:
        errors.append("q5_6_validation_errors:" + ",".join(staging_errors))
    if dry_run_errors:
        errors.append("q5_7_validation_errors:" + ",".join(dry_run_errors))
    if q5e1_artifact.get("paper_size_eligible_count", 0) < 1:
        errors.append("q5e_3_missing_q5e_1_eligible_setup")
    if written_staging_bundle.get("staged_order_count", 0) < 1:
        errors.append("q5e_3_missing_q5e_2_staged_order")
    if not target_staged:
        errors.append("q5e_3_target_staged_record_missing")
    if written_dry_run_bundle.get("source_staged_order_count", 0) < 1:
        errors.append("q5e_3_dry_run_source_staged_order_missing")
    if written_dry_run_bundle.get("request_preview_count", 0) < 1:
        errors.append("q5e_3_request_preview_missing")
    if written_dry_run_bundle.get("dry_run_receipt_count", 0) < 1:
        errors.append("q5e_3_dry_run_receipt_missing")
    if not target:
        errors.append("q5e_3_target_dry_run_record_missing")
    if target:
        if target.get("selected_venue") != "alpaca_paper":
            errors.append("q5e_3_target_not_alpaca_paper")
        if target.get("source_staged_paper_order_status") != "staged":
            errors.append("q5e_3_target_source_not_staged")
        if target.get("source_staged_paper_order_state") != "staged_ready_for_dry_run":
            errors.append("q5e_3_target_source_not_ready_for_dry_run")
        if target.get("request_preview_allowed") is not True:
            errors.append("q5e_3_target_request_preview_not_allowed")
        if target.get("dry_run_receipt_created") is not True:
            errors.append("q5e_3_target_receipt_not_created")
        if target.get("receipt_state") != "dry_run_receipt_preview_ready":
            errors.append("q5e_3_target_receipt_state_invalid")
        if target.get("paper_mode_confirmed") is not True:
            errors.append("q5e_3_target_paper_mode_not_confirmed")
        if target.get("endpoint_classification") == "live_endpoint":
            errors.append("q5e_3_target_live_endpoint")
        if target.get("alpaca_read_health") != "read_only_available":
            errors.append("q5e_3_target_alpaca_read_not_available")
        if not str(target.get("alpaca_write_health") or "").startswith("blocked"):
            errors.append("q5e_3_target_alpaca_write_not_blocked")
        if not str(target.get("idempotency_key_preview") or "").startswith("q5-7-dryrun-"):
            errors.append("q5e_3_target_idempotency_preview_invalid")
        if request_preview.get("status") != "preview_ready_no_post":
            errors.append("q5e_3_request_preview_not_ready")
        if request_preview.get("post_call_allowed") is not False:
            errors.append("q5e_3_request_preview_post_allowed")
        if request_preview.get("authorization_header_included") is not False:
            errors.append("q5e_3_request_preview_auth_header_included")
        if request_preview.get("base_url_exposed") is not False:
            errors.append("q5e_3_request_preview_base_url_exposed")
        if request_preview.get("raw_payload_exposed") is not False:
            errors.append("q5e_3_request_preview_raw_payload_exposed")
        if simulated_receipt.get("status") != "simulated_ready_no_broker_post":
            errors.append("q5e_3_simulated_receipt_not_ready")
        if simulated_receipt.get("receipt_created") is not True:
            errors.append("q5e_3_simulated_receipt_not_created")
        if simulated_receipt.get("broker_post_called") is not False:
            errors.append("q5e_3_simulated_receipt_broker_post_called")
        if simulated_receipt.get("paper_order_submitted") is not False:
            errors.append("q5e_3_simulated_receipt_paper_order_submitted")
        if duplicate_guard.get("collision_detected") is not False:
            errors.append("q5e_3_duplicate_guard_collision")
        if duplicate_guard.get("guard_write_performed") is not False:
            errors.append("q5e_3_duplicate_guard_write_performed")
        if pre_trade_snapshot.get("capture_performed") is not False:
            errors.append("q5e_3_pre_trade_snapshot_captured")
    if dry_run_replay["total_events"] != written_dry_run_bundle.get("dry_run_record_count"):
        errors.append("q5e_3_event_log_count_mismatch")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "paper_order_submitted_count",
        "paper_order_submission_allowed_count",
        "broker_submit_receipt_created_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
    ):
        if int(written_dry_run_bundle.get(key, 0) or 0) != 0:
            errors.append(f"q5e_3_boundary_count_not_zero:{key}")

    print("phase5_exit_alpaca_paper_dry_run_status=" + written_dry_run_bundle["status"])
    print(
        "phase5_exit_alpaca_paper_dry_run_schema_version="
        f"{PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION}"
    )
    print(f"phase5_exit_alpaca_paper_dry_run_artifact_path={output_path}")
    print(f"phase5_exit_alpaca_paper_dry_run_history_path={history_path}")
    print(f"phase5_exit_alpaca_paper_dry_run_event_log_path={dry_run_event_log_path}")
    print(
        "phase5_exit_alpaca_paper_dry_run_target_strategy_family_key="
        f"{TARGET_STRATEGY_FAMILY_KEY}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_source_staged_order_count="
        f"{written_dry_run_bundle['source_staged_order_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_request_preview_count="
        f"{written_dry_run_bundle['request_preview_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_receipt_count="
        f"{written_dry_run_bundle['dry_run_receipt_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_blocked_count="
        f"{written_dry_run_bundle['blocked_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_target_record_present="
        f"{bool(target)}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_target_request_preview_allowed="
        f"{target.get('request_preview_allowed', False)}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_target_receipt_created="
        f"{target.get('dry_run_receipt_created', False)}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_target_receipt_state="
        f"{target.get('receipt_state', 'missing')}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_target_idempotency_key_present="
        f"{bool(str(target.get('idempotency_key_preview') or '').strip())}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_event_log_total_events="
        f"{dry_run_replay['total_events']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_broker_post_called_count="
        f"{written_dry_run_bundle['broker_post_called_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_alpaca_post_called_count="
        f"{written_dry_run_bundle['alpaca_post_called_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_broker_write_allowed_count="
        f"{written_dry_run_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_paper_order_submitted_count="
        f"{written_dry_run_bundle['paper_order_submitted_count']}"
    )
    print(
        "phase5_exit_alpaca_paper_dry_run_live_capital_enabled_count="
        f"{written_dry_run_bundle['live_capital_enabled_count']}"
    )
    print("phase5_exit_alpaca_paper_dry_run_boundary=" + written_dry_run_bundle["boundary"])

    if errors:
        for error in errors:
            print(f"phase5_exit_alpaca_paper_dry_run_error={error}")
        print("phase5_exit_alpaca_paper_dry_run_check=failed")
        return 1

    print("phase5_exit_alpaca_paper_dry_run_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
