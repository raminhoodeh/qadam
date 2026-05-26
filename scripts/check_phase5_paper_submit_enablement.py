#!/usr/bin/env python3
"""Validate the Q5-8 paper-submit enablement gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_paper_submit_enablement import (  # noqa: E402
    PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS,
    PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS,
    PAPER_SUBMIT_PATH_KEY,
    PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
    _paper_submit_record,
    build_phase5_paper_submit_enablement_gate,
    paper_submit_enablement_paths,
    validate_phase5_paper_submit_enablement_bundle,
    validate_phase5_paper_submit_enablement_record,
    write_phase5_paper_submit_enablement_gate,
)


def _first_record(bundle: dict) -> dict:
    records = bundle.get("records", [])
    if not records:
        raise RuntimeError("no paper-submit enablement records produced")
    return records[0]


def ready_source_record(record: dict) -> dict:
    source = deepcopy(record)
    source["stage"] = "Q5-7"
    source["source_request_preview_allowed"] = True
    source["source_dry_run_receipt_created"] = True
    source["request_preview_allowed"] = True
    source["dry_run_receipt_created"] = True
    source["receipt_state"] = "dry_run_receipt_preview_ready"
    source["paper_mode_confirmed"] = True
    source["endpoint_classification"] = "alpaca_paper_endpoint"
    source["live_endpoint_allowed"] = False
    source["live_capital_enabled"] = False
    source["prediction_market_write_allowed"] = False
    source["broker_post_called"] = False
    source["paper_order_submitted"] = False
    source["kill_switch_clear"] = True
    request_preview = dict(source.get("request_preview") or source.get("submit_request_preview") or {})
    request_preview["status"] = "preview_ready_no_post"
    request_preview["post_call_allowed"] = False
    request_preview["authorization_header_included"] = False
    request_preview["base_url_exposed"] = False
    request_preview["raw_payload_exposed"] = False
    request_preview["http_method_preview"] = "POST_DISABLED_PREVIEW_ONLY"
    source["request_preview"] = request_preview
    simulated = dict(source.get("simulated_submit_receipt") or {})
    simulated["status"] = "simulated_ready_no_broker_post"
    simulated["receipt_created"] = True
    simulated["broker_post_called"] = False
    simulated["paper_order_submitted"] = False
    simulated["raw_broker_payload_stored"] = False
    simulated["broker_order_id_exposed"] = False
    source["simulated_submit_receipt"] = simulated
    duplicate = dict(source.get("duplicate_order_guard") or {})
    duplicate["collision_checked"] = True
    duplicate["collision_detected"] = False
    duplicate["duplicate_detected"] = False
    duplicate["lookup_performed"] = False
    duplicate["guard_write_performed"] = False
    source["duplicate_order_guard"] = duplicate
    snapshot = dict(source.get("pre_trade_snapshot_schema") or {})
    snapshot["status"] = "schema_ready_not_captured"
    snapshot["write_authority"] = False
    snapshot["live_capital_enabled"] = False
    snapshot["raw_payload_exposed"] = False
    source["pre_trade_snapshot_schema"] = snapshot
    return source


def approved_submit_approval() -> dict:
    return {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "approval_state": "approved",
        "approval_scope": "alpaca_paper_submit",
        "approval_present": True,
        "approval_logged": True,
        "explicit_paper_submit_approval": True,
        "paper_account_mode_confirmed": True,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "approval_artifact_present": True,
        "approval_artifact_path_exposed": False,
    }


def ready_probe(record: dict) -> dict:
    return _paper_submit_record(
        ready_source_record(record),
        dry_run_errors=[],
        approval=approved_submit_approval(),
        account_context={"mode": "paper"},
        generated_at=str(record.get("generated_at") or "2026-05-24T00:00:00+00:00"),
        force_ready=True,
    )


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paper_submit_enablement_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_paper_submit_enablement_gate(settings=settings)
    output_path, history_path, event_log_path, written_bundle = (
        write_phase5_paper_submit_enablement_gate(
            bundle,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase5_paper_submit_enablement_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    first_record = _first_record(written_bundle)

    ready = ready_probe(first_record)
    ready_errors = validate_phase5_paper_submit_enablement_record(ready)

    missing_approval_probe = deepcopy(ready)
    missing_approval_probe["paper_submit_approval_present"] = False
    missing_approval_errors = validate_phase5_paper_submit_enablement_record(missing_approval_probe)

    live_endpoint_probe = deepcopy(ready)
    live_endpoint_probe["live_endpoint_allowed"] = True
    live_endpoint_errors = validate_phase5_paper_submit_enablement_record(live_endpoint_probe)

    missing_prewrite_probe = deepcopy(ready)
    missing_prewrite_probe["event_log_prewrite"] = dict(missing_prewrite_probe["event_log_prewrite"])
    missing_prewrite_probe["event_log_prewrite"]["prewrite_complete"] = False
    missing_prewrite_errors = validate_phase5_paper_submit_enablement_record(missing_prewrite_probe)

    missing_snapshot_probe = deepcopy(ready)
    missing_snapshot_probe["pre_trade_snapshot"] = dict(missing_snapshot_probe["pre_trade_snapshot"])
    missing_snapshot_probe["pre_trade_snapshot"]["captured"] = False
    missing_snapshot_errors = validate_phase5_paper_submit_enablement_record(missing_snapshot_probe)

    duplicate_probe = deepcopy(ready)
    duplicate_probe["duplicate_order_guard"] = dict(duplicate_probe["duplicate_order_guard"])
    duplicate_probe["duplicate_order_guard"]["collision_detected"] = True
    duplicate_errors = validate_phase5_paper_submit_enablement_record(duplicate_probe)

    idempotency_probe = deepcopy(ready)
    idempotency_probe["idempotency_key_allocated_for_submit"] = False
    idempotency_errors = validate_phase5_paper_submit_enablement_record(idempotency_probe)

    broker_post_probe = deepcopy(ready)
    broker_post_probe["broker_post_called"] = True
    broker_post_errors = validate_phase5_paper_submit_enablement_record(broker_post_probe)

    live_capital_probe = deepcopy(ready)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_phase5_paper_submit_enablement_record(live_capital_probe)

    prediction_write_probe = deepcopy(ready)
    prediction_write_probe["prediction_market_write_allowed"] = True
    prediction_write_errors = validate_phase5_paper_submit_enablement_record(
        prediction_write_probe
    )

    exposure_probe = deepcopy(ready)
    exposure_probe["authorization_header_exposed"] = True
    exposure_errors = validate_phase5_paper_submit_enablement_record(exposure_probe)

    print("phase5_paper_submit_enablement_status=" + written_bundle["status"])
    print(
        "phase5_paper_submit_enablement_schema_version="
        f"{PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION}"
    )
    print(f"phase5_paper_submit_enablement_artifact_path={output_path}")
    print(f"phase5_paper_submit_enablement_history_path={history_path}")
    print(f"phase5_paper_submit_enablement_event_log_path={event_log_path}")
    print(
        "phase5_paper_submit_enablement_record_count="
        f"{written_bundle['submit_enablement_record_count']}"
    )
    print(
        "phase5_paper_submit_enablement_source_dry_run_record_count="
        f"{written_bundle['source_dry_run_record_count']}"
    )
    print(
        "phase5_paper_submit_enablement_source_request_preview_count="
        f"{written_bundle['source_request_preview_count']}"
    )
    print(
        "phase5_paper_submit_enablement_source_dry_run_receipt_count="
        f"{written_bundle['source_dry_run_receipt_count']}"
    )
    print(
        "phase5_paper_submit_enablement_submit_path_available_count="
        f"{written_bundle['submit_path_available_count']}"
    )
    print(
        "phase5_paper_submit_enablement_blocked_count="
        f"{written_bundle['blocked_count']}"
    )
    print(
        "phase5_paper_submit_enablement_approval_state="
        f"{written_bundle['paper_submit_approval_state']}"
    )
    print(
        "phase5_paper_submit_enablement_approval_present="
        f"{written_bundle['paper_submit_approval_present']}"
    )
    print(
        "phase5_paper_submit_enablement_event_log_written="
        f"{written_bundle['event_log_written']}"
    )
    print(
        "phase5_paper_submit_enablement_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_paper_submit_enablement_validation_error_count="
        f"{len(validation_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_idempotency_collision_count="
        f"{written_bundle['idempotency_collision_count']}"
    )
    print(
        "phase5_paper_submit_enablement_duplicate_guard_collision_count="
        f"{written_bundle['duplicate_guard_collision_count']}"
    )
    for key in (
        "execution_adapter_write_authority_count",
        "paper_execution_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submission_allowed_count",
        "broker_write_allowed_count",
        "broker_submit_receipt_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "paper_order_submitted_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "prediction_market_write_allowed_count",
    ):
        print(f"phase5_paper_submit_enablement_{key}={written_bundle[key]}")
    print(f"phase5_paper_submit_enablement_ready_probe_error_count={len(ready_errors)}")
    print(
        "phase5_paper_submit_enablement_ready_probe_path_key="
        f"{ready['submit_path_key']}"
    )
    print(
        "phase5_paper_submit_enablement_ready_probe_authority_count="
        f"{sum(1 for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS if ready.get(field) is True)}"
    )
    print(
        "phase5_paper_submit_enablement_missing_approval_probe_error_count="
        f"{len(missing_approval_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_live_endpoint_probe_error_count="
        f"{len(live_endpoint_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_missing_prewrite_probe_error_count="
        f"{len(missing_prewrite_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_missing_snapshot_probe_error_count="
        f"{len(missing_snapshot_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_duplicate_probe_error_count="
        f"{len(duplicate_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_idempotency_probe_error_count="
        f"{len(idempotency_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_broker_post_probe_error_count="
        f"{len(broker_post_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_prediction_write_probe_error_count="
        f"{len(prediction_write_errors)}"
    )
    print(
        "phase5_paper_submit_enablement_exposure_probe_error_count="
        f"{len(exposure_errors)}"
    )
    print("phase5_paper_submit_enablement_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("paper_submit_enablement_bundle_not_ok")
    if written_bundle["submit_enablement_record_count"] != written_bundle["source_dry_run_record_count"]:
        errors.append("paper_submit_enablement_record_count_mismatch")
    if written_bundle["submit_enablement_record_count"] != 5:
        errors.append("paper_submit_enablement_record_count_not_five")
    source_request_preview_count = int(written_bundle["source_request_preview_count"] or 0)
    source_dry_run_receipt_count = int(written_bundle["source_dry_run_receipt_count"] or 0)
    if source_request_preview_count != source_dry_run_receipt_count:
        errors.append("paper_submit_enablement_source_preview_receipt_count_mismatch")
    expected_submit_path_available_count = (
        source_request_preview_count
        if written_bundle["paper_submit_approval_present"] is True
        else 0
    )
    if written_bundle["submit_path_available_count"] != expected_submit_path_available_count:
        errors.append("paper_submit_enablement_submit_path_available_count_mismatch")
    expected_blocked_count = (
        written_bundle["submit_enablement_record_count"]
        - int(written_bundle.get("paper_order_submitted_count", 0) or 0)
    )
    if written_bundle["blocked_count"] != expected_blocked_count:
        errors.append("paper_submit_enablement_blocked_count_mismatch")
    approval_present = written_bundle["paper_submit_approval_present"] is True
    if approval_present:
        if written_bundle["paper_submit_approval_state"] != "approved":
            errors.append("paper_submit_enablement_approval_state_not_approved")
        if written_bundle["paper_submit_approval_logged"] is not True:
            errors.append("paper_submit_enablement_approval_not_logged")
        if any(
            "paper_submit_approval_present" in record.get("failed_checks", [])
            for record in written_bundle.get("records", [])
            if isinstance(record, dict)
        ):
            errors.append("paper_submit_enablement_approval_still_failed")
    else:
        if written_bundle["paper_submit_approval_state"] != "missing":
            errors.append("paper_submit_enablement_approval_state_should_be_missing")
    if written_bundle["required_check_count"] != len(PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS):
        errors.append("paper_submit_enablement_required_check_count_mismatch")
    if written_bundle["event_log_written"] is not True:
        errors.append("paper_submit_enablement_event_log_not_written")
    if event_replay["total_events"] != written_bundle["submit_enablement_record_count"]:
        errors.append("paper_submit_enablement_event_log_count_mismatch")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "prediction_market_write_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "base_url_exposed_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"paper_submit_enablement_boundary_count_not_zero:{key}")
    if written_bundle.get("broker_submit_receipt_created_count") != written_bundle.get(
        "paper_order_submitted_count"
    ):
        errors.append("paper_submit_enablement_receipt_count_mismatch")
    if int(written_bundle.get("paper_order_submitted_count", 0) or 0) > int(
        written_bundle.get("submit_path_available_count", 0) or 0
    ):
        errors.append("paper_submit_enablement_submitted_count_exceeds_path_count")
    for key in (
        "execution_adapter_write_authority_count",
        "paper_execution_allowed_count",
        "paper_order_allowed_count",
        "paper_order_submission_allowed_count",
        "broker_write_allowed_count",
    ):
        if written_bundle.get(key) != written_bundle["submit_path_available_count"]:
            errors.append(f"paper_submit_enablement_allowed_authority_count_mismatch:{key}")
    if written_bundle["idempotency_collision_count"] != 0:
        errors.append("paper_submit_enablement_idempotency_collision")
    if written_bundle["duplicate_guard_collision_count"] != 0:
        errors.append("paper_submit_enablement_duplicate_guard_collision")
    if ready_errors:
        errors.append("paper_submit_enablement_ready_probe_rejected")
    if ready["submit_path_key"] != PAPER_SUBMIT_PATH_KEY:
        errors.append("paper_submit_enablement_ready_probe_path_key_mismatch")
    if ready["submit_path_available"] is not True:
        errors.append("paper_submit_enablement_ready_probe_path_unavailable")
    if ready["broker_post_called"] is not False:
        errors.append("paper_submit_enablement_ready_probe_performed_broker_post")
    for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS:
        if ready.get(field) is not True:
            errors.append(f"paper_submit_enablement_ready_probe_authority_missing:{field}")
    if "submit_path_available_without_paper_submit_approval" not in missing_approval_errors:
        errors.append("paper_submit_enablement_missing_approval_probe_not_rejected")
    if "live_endpoint_allowed" not in live_endpoint_errors:
        errors.append("paper_submit_enablement_live_endpoint_probe_not_rejected")
    if "submit_path_available_without_event_log_prewrite" not in missing_prewrite_errors:
        errors.append("paper_submit_enablement_missing_prewrite_probe_not_rejected")
    if "submit_path_available_without_pre_trade_snapshot" not in missing_snapshot_errors:
        errors.append("paper_submit_enablement_missing_snapshot_probe_not_rejected")
    if "duplicate_guard_collision_detected" not in duplicate_errors:
        errors.append("paper_submit_enablement_duplicate_probe_not_rejected")
    if "submit_path_available_without_submit_idempotency" not in idempotency_errors:
        errors.append("paper_submit_enablement_idempotency_probe_not_rejected")
    if "broker_post_called_before_submit" not in broker_post_errors:
        errors.append("paper_submit_enablement_broker_post_probe_not_rejected")
    if "live_capital_enabled" not in live_capital_errors:
        errors.append("paper_submit_enablement_live_capital_probe_not_rejected")
    if "prediction_market_write_allowed" not in prediction_write_errors:
        errors.append("paper_submit_enablement_prediction_write_probe_not_rejected")
    if "paper_submit_enablement_exposure_enabled:authorization_header_exposed" not in exposure_errors:
        errors.append("paper_submit_enablement_exposure_probe_not_rejected")
    if "cannot enable live capital" not in written_bundle["boundary"]:
        errors.append("paper_submit_enablement_boundary_weak")

    if errors:
        for error in errors:
            print(f"phase5_paper_submit_enablement_error={error}")
        print("phase5_paper_submit_enablement_check=failed")
        return 1

    print("phase5_paper_submit_enablement_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
