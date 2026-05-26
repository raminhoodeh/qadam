#!/usr/bin/env python3
"""Validate the Q5-5 execution adapter status contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.execution import execution_registry  # noqa: E402
from orchestrator.phase5_execution_adapter_status import (  # noqa: E402
    EXECUTION_ADAPTER_REQUIRED_CHECKS,
    PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION,
    build_phase5_execution_adapter_status,
    phase5_execution_adapter_status_paths,
    validate_phase5_execution_adapter_status,
    validate_phase5_execution_adapter_status_bundle,
    write_phase5_execution_adapter_status,
)


def _first_record(bundle: dict, venue_key: str = "alpaca_paper") -> dict:
    for record in bundle.get("statuses", []):
        if record.get("venue_key") == venue_key:
            return record
    statuses = bundle.get("statuses", [])
    if not statuses:
        raise RuntimeError("no execution adapter statuses produced")
    return statuses[0]


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_execution_adapter_status_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_execution_adapter_status(settings=settings)
    output_path, history_path, event_log_path, written_bundle = (
        write_phase5_execution_adapter_status(
            bundle,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase5_execution_adapter_status_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    alpaca_record = _first_record(written_bundle, "alpaca_paper")
    prediction_record = _first_record(written_bundle, "prediction_market_router")

    missing_credentials_probe = deepcopy(alpaca_record)
    missing_credentials_probe["credentials_configured"] = False
    missing_credentials_probe["credential_status"] = "missing_credentials"
    missing_credentials_probe["status"] = "eligible"
    missing_credentials_probe["blocked_reasons"] = []
    missing_credentials_probe["blocked_reason_count"] = 0
    missing_credentials_errors = validate_phase5_execution_adapter_status(
        missing_credentials_probe
    )

    wrong_mode_probe = deepcopy(alpaca_record)
    wrong_mode_probe["account_mode"] = "live"
    wrong_mode_probe["status"] = "hold"
    wrong_mode_probe["blocked_reasons"] = []
    wrong_mode_probe["blocked_reason_count"] = 0
    wrong_mode_errors = validate_phase5_execution_adapter_status(wrong_mode_probe)

    live_endpoint_probe = deepcopy(alpaca_record)
    live_endpoint_probe["endpoint_classification"] = "live_endpoint"
    live_endpoint_probe["status"] = "hold"
    live_endpoint_errors = validate_phase5_execution_adapter_status(live_endpoint_probe)

    degraded_probe = deepcopy(alpaca_record)
    degraded_probe["degraded"] = True
    degraded_probe["status"] = "eligible"
    degraded_probe["downstream_staging_allowed"] = True
    degraded_errors = validate_phase5_execution_adapter_status(degraded_probe)

    active_kill_probe = deepcopy(alpaca_record)
    active_kill_probe["kill_switch_active"] = True
    active_kill_probe["kill_switch_status"] = "blocked"
    active_kill_probe["status"] = "hold"
    active_kill_probe["downstream_staging_allowed"] = True
    active_kill_errors = validate_phase5_execution_adapter_status(active_kill_probe)

    broker_write_probe = deepcopy(alpaca_record)
    broker_write_probe["broker_write_allowed"] = True
    broker_write_errors = validate_phase5_execution_adapter_status(broker_write_probe)

    prediction_write_probe = deepcopy(prediction_record)
    prediction_write_probe["prediction_market_write_allowed"] = True
    prediction_write_errors = validate_phase5_execution_adapter_status(
        prediction_write_probe
    )

    secret_probe = deepcopy(alpaca_record)
    secret_probe["secret_value_exposed"] = True
    secret_errors = validate_phase5_execution_adapter_status(secret_probe)

    print("phase5_execution_adapter_status=" + written_bundle["status"])
    print(
        "phase5_execution_adapter_schema_version="
        f"{PHASE5_EXECUTION_ADAPTER_SCHEMA_VERSION}"
    )
    print(f"phase5_execution_adapter_artifact_path={output_path}")
    print(f"phase5_execution_adapter_history_path={history_path}")
    print(f"phase5_execution_adapter_event_log_path={event_log_path}")
    print(
        "phase5_execution_adapter_status_count="
        f"{written_bundle['adapter_status_count']}"
    )
    print(
        "phase5_execution_adapter_first_release_allowed_count="
        f"{written_bundle['first_release_allowed_count']}"
    )
    print(
        "phase5_execution_adapter_read_allowed_count="
        f"{written_bundle['read_allowed_count']}"
    )
    print(
        "phase5_execution_adapter_downstream_staging_allowed_count="
        f"{written_bundle['downstream_staging_allowed_count']}"
    )
    print(
        "phase5_execution_adapter_active_kill_switch_block_count="
        f"{written_bundle['active_kill_switch_block_count']}"
    )
    print(
        "phase5_execution_adapter_required_check_count="
        f"{written_bundle['required_check_count']}"
    )
    print(
        "phase5_execution_adapter_reconciliation_prerequisite_count="
        f"{written_bundle['reconciliation_prerequisite_count']}"
    )
    print(
        "phase5_execution_adapter_event_log_written="
        f"{written_bundle['event_log_written']}"
    )
    print(
        "phase5_execution_adapter_event_log_total_events="
        f"{event_replay['total_events']}"
    )
    print(
        "phase5_execution_adapter_validation_error_count="
        f"{len(validation_errors)}"
    )
    print(
        "phase5_execution_adapter_alpaca_status="
        f"{alpaca_record.get('status')}"
    )
    print(
        "phase5_execution_adapter_alpaca_read_health="
        f"{alpaca_record.get('read_health')}"
    )
    print(
        "phase5_execution_adapter_alpaca_write_health="
        f"{alpaca_record.get('write_health')}"
    )
    print(
        "phase5_execution_adapter_alpaca_credentials_configured="
        f"{alpaca_record.get('credentials_configured')}"
    )
    print(
        "phase5_execution_adapter_alpaca_account_mode="
        f"{alpaca_record.get('account_mode')}"
    )
    print(
        "phase5_execution_adapter_alpaca_current_balance_gbp="
        f"{alpaca_record.get('current_balance_gbp')}"
    )
    print(
        "phase5_execution_adapter_alpaca_open_order_count="
        f"{alpaca_record.get('open_order_count')}"
    )
    print(
        "phase5_execution_adapter_alpaca_open_position_count="
        f"{alpaca_record.get('open_position_count')}"
    )
    print(
        "phase5_execution_adapter_broker_write_allowed_count="
        f"{written_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_execution_adapter_prediction_market_write_allowed_count="
        f"{written_bundle['prediction_market_write_allowed_count']}"
    )
    print(
        "phase5_execution_adapter_crypto_perps_write_allowed_count="
        f"{written_bundle['crypto_perps_write_allowed_count']}"
    )
    print(
        "phase5_execution_adapter_live_capital_enabled_count="
        f"{written_bundle['live_capital_enabled_count']}"
    )
    print(
        "phase5_execution_adapter_secret_value_exposed_count="
        f"{written_bundle['secret_value_exposed_count']}"
    )
    print(
        "phase5_execution_adapter_missing_credentials_probe_error_count="
        f"{len(missing_credentials_errors)}"
    )
    print(
        "phase5_execution_adapter_wrong_mode_probe_error_count="
        f"{len(wrong_mode_errors)}"
    )
    print(
        "phase5_execution_adapter_live_endpoint_probe_error_count="
        f"{len(live_endpoint_errors)}"
    )
    print(
        "phase5_execution_adapter_degraded_probe_error_count="
        f"{len(degraded_errors)}"
    )
    print(
        "phase5_execution_adapter_active_kill_probe_error_count="
        f"{len(active_kill_errors)}"
    )
    print(
        "phase5_execution_adapter_broker_write_probe_error_count="
        f"{len(broker_write_errors)}"
    )
    print(
        "phase5_execution_adapter_prediction_write_probe_error_count="
        f"{len(prediction_write_errors)}"
    )
    print(
        "phase5_execution_adapter_secret_probe_error_count="
        f"{len(secret_errors)}"
    )
    print("phase5_execution_adapter_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("execution_adapter_bundle_not_ok")
    if written_bundle["adapter_status_count"] != len(execution_registry()):
        errors.append("execution_adapter_status_count_mismatch")
    if written_bundle["required_check_count"] != len(EXECUTION_ADAPTER_REQUIRED_CHECKS):
        errors.append("execution_adapter_required_check_count_mismatch")
    if written_bundle["event_log_written"] is not True:
        errors.append("execution_adapter_event_log_not_written")
    if event_replay["total_events"] != written_bundle["adapter_status_count"]:
        errors.append("execution_adapter_event_log_count_mismatch")
    if written_bundle["downstream_staging_allowed_count"] not in {0, 1}:
        errors.append("execution_adapter_downstream_staging_count_invalid")
    if written_bundle["downstream_staging_allowed_count"] == 1:
        if alpaca_record.get("downstream_staging_allowed") is not True:
            errors.append("alpaca_downstream_staging_not_flagged")
        if alpaca_record.get("staging_readiness_scope") != "guarded_q5e_lifecycle_readiness":
            errors.append("alpaca_staging_readiness_scope_invalid")
        if alpaca_record.get("guarded_postmortem_due_ready") is not True:
            errors.append("alpaca_guarded_postmortem_due_not_ready")
        if alpaca_record.get("status") != "eligible":
            errors.append("alpaca_staging_ready_not_eligible")
    for key in (
        "execution_adapter_write_authority_count",
        "paper_order_staging_allowed_count",
        "paper_order_submission_allowed_count",
        "paper_order_allowed_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "broker_submit_receipt_created_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_capital_enabled_count",
        "live_endpoint_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "reconciliation_ready_for_submit_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"execution_adapter_boundary_count_not_zero:{key}")
    if alpaca_record.get("credentials_configured") is True:
        if alpaca_record.get("read_health") != "read_only_available":
            errors.append("alpaca_configured_but_read_not_available")
        if alpaca_record.get("account_mode") != "paper":
            errors.append("alpaca_configured_wrong_account_mode")
    if alpaca_record.get("write_health") != "blocked_q5_5_status_contract":
        errors.append("alpaca_write_health_not_blocked")
    if "missing_credentials_not_blocking" not in missing_credentials_errors:
        errors.append("missing_credentials_probe_not_rejected")
    if "wrong_account_mode_not_blocking" not in wrong_mode_errors:
        errors.append("wrong_mode_probe_not_rejected")
    if "live_endpoint_not_blocked" not in live_endpoint_errors:
        errors.append("live_endpoint_probe_not_rejected")
    if "degraded_venue_allows_downstream_staging" not in degraded_errors:
        errors.append("degraded_probe_not_rejected")
    if "active_kill_switch_not_blocking" not in active_kill_errors:
        errors.append("active_kill_probe_not_rejected")
    if "execution_adapter_boundary_enabled:broker_write_allowed" not in broker_write_errors:
        errors.append("broker_write_probe_not_rejected")
    if (
        "execution_adapter_boundary_enabled:prediction_market_write_allowed"
        not in prediction_write_errors
    ):
        errors.append("prediction_write_probe_not_rejected")
    if "adapter_status_exposure_enabled:secret_value_exposed" not in secret_errors:
        errors.append("secret_probe_not_rejected")

    if errors:
        for error in errors:
            print(f"phase5_execution_adapter_error={error}")
        print("phase5_execution_adapter_check=failed")
        return 1

    print("phase5_execution_adapter_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
