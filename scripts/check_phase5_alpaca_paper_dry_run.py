#!/usr/bin/env python3
"""Validate the Q5-7 Alpaca paper adapter dry-run contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_alpaca_paper_dry_run import (  # noqa: E402
    ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS,
    PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION,
    build_phase5_alpaca_paper_dry_run,
    phase5_alpaca_paper_dry_run_paths,
    validate_phase5_alpaca_paper_dry_run_bundle,
    validate_phase5_alpaca_paper_dry_run_record,
    write_phase5_alpaca_paper_dry_run,
)


def _first_record(bundle: dict) -> dict:
    records = bundle.get("records", [])
    if not records:
        raise RuntimeError("no Alpaca paper dry-run records produced")
    return records[0]


def _ready_probe(record: dict) -> dict:
    probe = deepcopy(record)
    probe["source_staged_paper_order_status"] = "staged"
    probe["source_staged_paper_order_state"] = "staged_ready_for_dry_run"
    probe["selected_venue"] = "alpaca_paper"
    probe["paper_mode_confirmed"] = True
    probe["alpaca_read_health"] = "read_only_available"
    probe["alpaca_write_health"] = "blocked_q5_7_dry_run_contract"
    probe["endpoint_classification"] = "alpaca_paper_endpoint"
    probe["request_preview_allowed"] = True
    probe["dry_run_receipt_created"] = True
    probe["receipt_state"] = "dry_run_receipt_preview_ready"
    probe["blocked_reasons"] = ["q5_8_paper_submit_gate_not_implemented"]
    probe["blocked_reason_count"] = 1
    probe["failed_checks"] = []
    probe["failed_check_count"] = 0
    request_preview = dict(probe.get("request_preview", {}))
    request_preview["status"] = "preview_ready_no_post"
    request_preview["post_call_allowed"] = False
    request_preview["authorization_header_included"] = False
    request_preview["base_url_exposed"] = False
    request_preview["raw_payload_exposed"] = False
    probe["request_preview"] = request_preview
    simulated = dict(probe.get("simulated_submit_receipt", {}))
    simulated["status"] = "simulated_ready_no_broker_post"
    simulated["receipt_created"] = True
    simulated["broker_post_called"] = False
    simulated["paper_order_submitted"] = False
    simulated["raw_broker_payload_stored"] = False
    simulated["broker_order_id_exposed"] = False
    probe["simulated_submit_receipt"] = simulated
    probe["simulated_receipt"] = simulated
    duplicate_guard = dict(probe.get("duplicate_order_guard", {}))
    duplicate_guard["status"] = "preview_clear"
    duplicate_guard["collision_checked"] = True
    duplicate_guard["collision_detected"] = False
    duplicate_guard["duplicate_detected"] = False
    duplicate_guard["lookup_performed"] = False
    duplicate_guard["guard_write_performed"] = False
    probe["duplicate_order_guard"] = duplicate_guard
    snapshot = dict(probe.get("pre_trade_snapshot_schema", {}))
    snapshot["status"] = "schema_ready_not_captured"
    snapshot["capture_performed"] = False
    snapshot["snapshot_ref"] = "not_captured"
    snapshot["write_authority"] = False
    snapshot["live_capital_enabled"] = False
    probe["pre_trade_snapshot_schema"] = snapshot
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_alpaca_paper_dry_run_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_alpaca_paper_dry_run(settings=settings)
    output_path, history_path, event_log_path, written_bundle = write_phase5_alpaca_paper_dry_run(
        bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_alpaca_paper_dry_run_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    first_record = _first_record(written_bundle)

    ready_errors = validate_phase5_alpaca_paper_dry_run_record(_ready_probe(first_record))

    live_endpoint_probe = _ready_probe(first_record)
    live_endpoint_probe["endpoint_classification"] = "live_endpoint"
    live_endpoint_errors = validate_phase5_alpaca_paper_dry_run_record(live_endpoint_probe)

    missing_paper_mode_probe = _ready_probe(first_record)
    missing_paper_mode_probe["paper_mode_confirmed"] = False
    missing_paper_mode_errors = validate_phase5_alpaca_paper_dry_run_record(
        missing_paper_mode_probe
    )

    broker_post_probe = deepcopy(first_record)
    broker_post_probe["broker_post_called"] = True
    broker_post_errors = validate_phase5_alpaca_paper_dry_run_record(broker_post_probe)

    broker_write_probe = deepcopy(first_record)
    broker_write_probe["broker_write_allowed"] = True
    broker_write_errors = validate_phase5_alpaca_paper_dry_run_record(broker_write_probe)

    submitted_probe = deepcopy(first_record)
    submitted_probe["paper_order_submitted"] = True
    submitted_errors = validate_phase5_alpaca_paper_dry_run_record(submitted_probe)

    live_capital_probe = deepcopy(first_record)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_phase5_alpaca_paper_dry_run_record(live_capital_probe)

    idempotency_probe = deepcopy(first_record)
    idempotency_probe["idempotency_key"] = "q5-7-dryrun-mutated"
    idempotency_errors = validate_phase5_alpaca_paper_dry_run_record(idempotency_probe)

    duplicate_probe = deepcopy(first_record)
    duplicate_probe["duplicate_order_guard"] = dict(duplicate_probe.get("duplicate_order_guard", {}))
    duplicate_probe["duplicate_order_guard"]["collision_detected"] = True
    duplicate_errors = validate_phase5_alpaca_paper_dry_run_record(duplicate_probe)

    request_post_probe = deepcopy(first_record)
    request_post_probe["request_preview"] = dict(request_post_probe.get("request_preview", {}))
    request_post_probe["request_preview"]["post_call_allowed"] = True
    request_post_errors = validate_phase5_alpaca_paper_dry_run_record(request_post_probe)

    receipt_post_probe = deepcopy(first_record)
    receipt_post_probe["simulated_submit_receipt"] = dict(
        receipt_post_probe.get("simulated_submit_receipt", {})
    )
    receipt_post_probe["simulated_submit_receipt"]["broker_post_called"] = True
    receipt_post_errors = validate_phase5_alpaca_paper_dry_run_record(receipt_post_probe)

    exposure_probe = deepcopy(first_record)
    exposure_probe["authorization_header_exposed"] = True
    exposure_errors = validate_phase5_alpaca_paper_dry_run_record(exposure_probe)

    print("phase5_alpaca_paper_dry_run_status=" + written_bundle["status"])
    print(
        "phase5_alpaca_paper_dry_run_schema_version="
        f"{PHASE5_ALPACA_PAPER_DRY_RUN_SCHEMA_VERSION}"
    )
    print(f"phase5_alpaca_paper_dry_run_artifact_path={output_path}")
    print(f"phase5_alpaca_paper_dry_run_history_path={history_path}")
    print(f"phase5_alpaca_paper_dry_run_event_log_path={event_log_path}")
    print(
        "phase5_alpaca_paper_dry_run_record_count="
        f"{written_bundle['dry_run_record_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_source_staging_record_count="
        f"{written_bundle['source_staging_record_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_source_staged_order_count="
        f"{written_bundle['source_staged_order_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_request_preview_count="
        f"{written_bundle['request_preview_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_receipt_count="
        f"{written_bundle['dry_run_receipt_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_blocked_count="
        f"{written_bundle['blocked_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_required_check_count="
        f"{written_bundle['required_check_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_event_log_written="
        f"{written_bundle['event_log_written']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_validation_error_count="
        f"{len(validation_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_idempotency_collision_count="
        f"{written_bundle['idempotency_collision_count']}"
    )
    print(
        "phase5_alpaca_paper_dry_run_duplicate_guard_collision_count="
        f"{written_bundle['duplicate_guard_collision_count']}"
    )
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "paper_order_submitted_count",
        "paper_order_submission_allowed_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
    ):
        print(f"phase5_alpaca_paper_dry_run_{key}={written_bundle[key]}")
    print(f"phase5_alpaca_paper_dry_run_ready_probe_error_count={len(ready_errors)}")
    print(
        "phase5_alpaca_paper_dry_run_live_endpoint_probe_error_count="
        f"{len(live_endpoint_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_missing_paper_mode_probe_error_count="
        f"{len(missing_paper_mode_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_broker_post_probe_error_count="
        f"{len(broker_post_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_broker_write_probe_error_count="
        f"{len(broker_write_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_submitted_probe_error_count="
        f"{len(submitted_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_idempotency_probe_error_count="
        f"{len(idempotency_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_duplicate_probe_error_count="
        f"{len(duplicate_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_request_post_probe_error_count="
        f"{len(request_post_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_receipt_post_probe_error_count="
        f"{len(receipt_post_errors)}"
    )
    print(
        "phase5_alpaca_paper_dry_run_exposure_probe_error_count="
        f"{len(exposure_errors)}"
    )
    print("phase5_alpaca_paper_dry_run_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("alpaca_paper_dry_run_bundle_not_ok")
    if written_bundle["dry_run_record_count"] != written_bundle["source_staging_record_count"]:
        errors.append("alpaca_paper_dry_run_record_count_mismatch")
    if written_bundle["dry_run_record_count"] != 5:
        errors.append("alpaca_paper_dry_run_record_count_not_five")
    source_staged_order_count = int(written_bundle["source_staged_order_count"] or 0)
    if source_staged_order_count == 0:
        if written_bundle["request_preview_count"] != 0:
            errors.append("alpaca_paper_dry_run_request_preview_created_without_staged_order")
        if written_bundle["dry_run_receipt_count"] != 0:
            errors.append("alpaca_paper_dry_run_receipt_created_without_staged_order")
    else:
        if written_bundle["request_preview_count"] != source_staged_order_count:
            errors.append("alpaca_paper_dry_run_request_preview_count_mismatch")
        if written_bundle["dry_run_receipt_count"] != source_staged_order_count:
            errors.append("alpaca_paper_dry_run_receipt_count_mismatch")
    if written_bundle["blocked_count"] != written_bundle["dry_run_record_count"]:
        errors.append("alpaca_paper_dry_run_blocked_count_mismatch")
    if written_bundle["required_check_count"] != len(ALPACA_PAPER_DRY_RUN_REQUIRED_CHECKS):
        errors.append("alpaca_paper_dry_run_required_check_count_mismatch")
    if written_bundle["event_log_written"] is not True:
        errors.append("alpaca_paper_dry_run_event_log_not_written")
    if event_replay["total_events"] != written_bundle["dry_run_record_count"]:
        errors.append("alpaca_paper_dry_run_event_log_count_mismatch")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_write_allowed_count",
        "paper_order_submitted_count",
        "paper_order_submission_allowed_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"alpaca_paper_dry_run_boundary_count_not_zero:{key}")
    if written_bundle["idempotency_collision_count"] != 0:
        errors.append("alpaca_paper_dry_run_idempotency_collision")
    if written_bundle["duplicate_guard_collision_count"] != 0:
        errors.append("alpaca_paper_dry_run_duplicate_guard_collision")
    if ready_errors:
        errors.append("alpaca_paper_dry_run_ready_probe_rejected")
    if "request_preview_live_endpoint" not in live_endpoint_errors:
        errors.append("alpaca_paper_dry_run_live_endpoint_probe_not_rejected")
    if "request_preview_without_paper_mode" not in missing_paper_mode_errors:
        errors.append("alpaca_paper_dry_run_missing_paper_mode_probe_not_rejected")
    if "alpaca_dry_run_boundary_enabled:broker_post_called" not in broker_post_errors:
        errors.append("alpaca_paper_dry_run_broker_post_probe_not_rejected")
    if "alpaca_dry_run_boundary_enabled:broker_write_allowed" not in broker_write_errors:
        errors.append("alpaca_paper_dry_run_broker_write_probe_not_rejected")
    if "alpaca_dry_run_boundary_enabled:paper_order_submitted" not in submitted_errors:
        errors.append("alpaca_paper_dry_run_submission_probe_not_rejected")
    if "alpaca_dry_run_boundary_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("alpaca_paper_dry_run_live_capital_probe_not_rejected")
    if "idempotency_key_not_deterministic" not in idempotency_errors:
        errors.append("alpaca_paper_dry_run_idempotency_probe_not_rejected")
    if "duplicate_guard_collision_detected" not in duplicate_errors:
        errors.append("alpaca_paper_dry_run_duplicate_probe_not_rejected")
    if "request_preview_authority_or_exposure_enabled:post_call_allowed" not in request_post_errors:
        errors.append("alpaca_paper_dry_run_request_post_probe_not_rejected")
    if "simulated_receipt_authority_enabled:broker_post_called" not in receipt_post_errors:
        errors.append("alpaca_paper_dry_run_receipt_post_probe_not_rejected")
    if "alpaca_dry_run_exposure_enabled:authorization_header_exposed" not in exposure_errors:
        errors.append("alpaca_paper_dry_run_exposure_probe_not_rejected")
    if "cannot call Alpaca POST routes" not in written_bundle["boundary"]:
        errors.append("alpaca_paper_dry_run_boundary_weak")

    if errors:
        for error in errors:
            print(f"phase5_alpaca_paper_dry_run_error={error}")
        print("phase5_alpaca_paper_dry_run_check=failed")
        return 1

    print("phase5_alpaca_paper_dry_run_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
