#!/usr/bin/env python3
"""Validate the Q5-8 Alpaca paper-submit path contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_paper_submit_enablement import (  # noqa: E402
    PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS,
    PAPER_SUBMIT_PATH_KEY,
    _paper_submit_record,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_enablement_record,
)


def _first_record(bundle: dict) -> dict:
    records = bundle.get("records", [])
    if not records:
        raise RuntimeError("no paper-submit enablement records produced")
    return records[0]


def _ready_source(record: dict) -> dict:
    source = deepcopy(record)
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
    source["duplicate_order_guard"] = duplicate
    return source


def _approval() -> dict:
    return {
        "approval_state": "approved",
        "approval_scope": "alpaca_paper_submit",
        "approval_present": True,
        "approval_logged": True,
        "explicit_paper_submit_approval": True,
        "paper_account_mode_confirmed": True,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
    }


def _ready_record(record: dict) -> dict:
    return _paper_submit_record(
        _ready_source(record),
        dry_run_errors=[],
        approval=_approval(),
        account_context={"mode": "paper"},
        generated_at=str(record.get("generated_at") or "2026-05-24T00:00:00+00:00"),
        force_ready=True,
    )


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    bundle = build_phase5_paper_submit_enablement_gate(settings=settings)
    first_record = _first_record(bundle)
    ready = _ready_record(first_record)
    ready_errors = validate_phase5_paper_submit_enablement_record(ready)
    submit_path = ready.get("submit_path", {})
    retry_policy = submit_path.get("retry_policy", {})
    failure_recording = submit_path.get("failure_recording", {})

    print(f"phase5_alpaca_paper_submit_contract_path_key={submit_path.get('path_key')}")
    print(f"phase5_alpaca_paper_submit_contract_available={ready.get('submit_path_available')}")
    print(f"phase5_alpaca_paper_submit_contract_adapter={submit_path.get('adapter')}")
    print(f"phase5_alpaca_paper_submit_contract_venue={submit_path.get('selected_venue')}")
    print(f"phase5_alpaca_paper_submit_contract_method={submit_path.get('http_method')}")
    print(f"phase5_alpaca_paper_submit_contract_path={submit_path.get('broker_path_template')}")
    print(f"phase5_alpaca_paper_submit_contract_timeout_seconds={submit_path.get('timeout_seconds')}")
    print(f"phase5_alpaca_paper_submit_contract_retry_max_attempts={retry_policy.get('max_attempts')}")
    print(
        "phase5_alpaca_paper_submit_contract_retry_same_idempotency="
        f"{retry_policy.get('retry_requires_same_idempotency_key')}"
    )
    print(
        "phase5_alpaca_paper_submit_contract_failure_event_log_required="
        f"{failure_recording.get('event_log_failure_required')}"
    )
    print(
        "phase5_alpaca_paper_submit_contract_authority_count="
        f"{sum(1 for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS if ready.get(field) is True)}"
    )
    print(f"phase5_alpaca_paper_submit_contract_validation_error_count={len(ready_errors)}")

    if ready_errors:
        errors.append("alpaca_paper_submit_contract_ready_record_invalid")
    if ready.get("submit_path_available") is not True:
        errors.append("alpaca_paper_submit_contract_ready_path_unavailable")
    if ready.get("submit_path_available_count") != 1:
        errors.append("alpaca_paper_submit_contract_path_count_not_one")
    if submit_path.get("path_key") != PAPER_SUBMIT_PATH_KEY:
        errors.append("alpaca_paper_submit_contract_path_key_invalid")
    if submit_path.get("adapter") != "alpaca":
        errors.append("alpaca_paper_submit_contract_adapter_invalid")
    if submit_path.get("selected_venue") != "alpaca_paper":
        errors.append("alpaca_paper_submit_contract_venue_invalid")
    if submit_path.get("account_mode_required") != "paper":
        errors.append("alpaca_paper_submit_contract_account_mode_not_paper")
    if submit_path.get("paper_only") is not True:
        errors.append("alpaca_paper_submit_contract_not_paper_only")
    if submit_path.get("http_method") != "POST":
        errors.append("alpaca_paper_submit_contract_method_not_post")
    if submit_path.get("broker_path_template") != "/v2/orders":
        errors.append("alpaca_paper_submit_contract_broker_path_invalid")
    if submit_path.get("base_url_exposed") is not False:
        errors.append("alpaca_paper_submit_contract_base_url_exposed")
    if submit_path.get("authorization_header_included") is not False:
        errors.append("alpaca_paper_submit_contract_authorization_header_included")
    if submit_path.get("post_call_performed") is not False:
        errors.append("alpaca_paper_submit_contract_post_call_performed")
    if float(submit_path.get("timeout_seconds", 0.0) or 0.0) <= 0:
        errors.append("alpaca_paper_submit_contract_timeout_missing")
    if retry_policy.get("max_attempts") != 2:
        errors.append("alpaca_paper_submit_contract_retry_attempts_invalid")
    if retry_policy.get("retry_requires_same_idempotency_key") is not True:
        errors.append("alpaca_paper_submit_contract_retry_not_idempotent")
    if "timeout" not in retry_policy.get("retry_on", []):
        errors.append("alpaca_paper_submit_contract_retry_timeout_missing")
    if failure_recording.get("event_log_failure_required") is not True:
        errors.append("alpaca_paper_submit_contract_failure_log_not_required")
    if failure_recording.get("raw_broker_payload_stored") is not False:
        errors.append("alpaca_paper_submit_contract_raw_payload_stored")
    for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS:
        if ready.get(field) is not True:
            errors.append(f"alpaca_paper_submit_contract_authority_missing:{field}")
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "paper_order_submitted",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "telegram_live_notifications_allowed",
        "position_monitor_write_authority",
    ):
        if ready.get(field) is not False:
            errors.append(f"alpaca_paper_submit_contract_forbidden_field_enabled:{field}")

    if errors:
        for error in errors:
            print(f"phase5_alpaca_paper_submit_contract_error={error}")
        print("phase5_alpaca_paper_submit_contract_check=failed")
        return 1

    print("phase5_alpaca_paper_submit_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
