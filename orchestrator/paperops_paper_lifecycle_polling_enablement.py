"""PT-6 active PaperOps paper lifecycle polling enablement.

PT-6 records the runtime gate that lets the PaperOps runner poll Alpaca paper
order lifecycle state after PaperOps-2 has actually submitted a paper order.
It does not call Alpaca itself; the read-only GET remains in PaperOps-3.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paperops_alpaca_paper_post import (
    _endpoint_context,
    build_paperops_alpaca_paper_post,
    paperops_alpaca_paper_post_submission_ledger_path,
    read_latest_paperops_alpaca_paper_post,
    validate_paperops_alpaca_paper_post,
)
from orchestrator.qadam_operator_exploratory_sleeve import (
    CLIENT_ORDER_PREFIX as OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX,
    IDEMPOTENCY_NAMESPACE as OPERATOR_SLEEVE_IDEMPOTENCY_NAMESPACE,
)


PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_SCHEMA_VERSION = 1
PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_RUNTIME_ARTIFACT = (
    "paperops_paper_lifecycle_polling_enablement.json"
)
PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_HISTORY = (
    "paperops_paper_lifecycle_polling_enablement_history.jsonl"
)
PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_EVENT_LOG = (
    "paperops_paper_lifecycle_polling_enablement_events.jsonl"
)
PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_EVENT_TYPE = (
    "paperops_paper_lifecycle_polling_enablement_recorded"
)
PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_COMPONENT = (
    "paperops_paper_lifecycle_polling_enablement"
)

PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_BOUNDARY = (
    "PT-6 records runtime active Alpaca paper lifecycle polling enablement for "
    "PaperOps. It may allow PaperOps-3 to issue read-only Alpaca paper GET "
    "requests only after QADAM_MODE=paper, live capital is disabled, the "
    "Alpaca endpoint is classified as paper, paper credentials are configured, "
    "PaperOps-2 is valid, and PaperOps-2 has successfully submitted a paper "
    "order. PT-6 cannot edit .env or secrets, cannot submit orders, cannot "
    "call Alpaca by itself, cannot call broker POST routes, cannot call live "
    "endpoints, cannot cancel, close, or resize positions, cannot force "
    "trades, cannot grant Phase 7 proof credit, cannot expose credentials, and "
    "cannot enable live capital."
)

PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_written",
    "event_log_event_count",
    "mode",
    "active_lifecycle_polling_enabled",
    "paper_lifecycle_polling_effective",
    "env_file_edited",
    "env_mutation_allowed",
    "paper_poll_path_available",
    "paper_poll_idle_until_submitted_order",
    "explicit_poll_flag_required",
    "poll_now_requested",
    "paperops_2_status",
    "paperops_2_source_present",
    "paperops_2_source_valid",
    "paperops_2_validation_error_count",
    "paperops_2_paper_post_path_available",
    "paperops_2_eligible_submit_record_count",
    "paperops_2_submitted_paper_order_count",
    "endpoint_classification",
    "paper_endpoint_confirmed",
    "alpaca_api_key_configured",
    "alpaca_api_secret_configured",
    "paper_broker_get_allowed",
    "alpaca_paper_get_allowed",
    "broker_get_called_count",
    "alpaca_paper_get_called_count",
    "paper_order_submission_allowed",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "order_cancel_allowed",
    "position_close_allowed",
    "position_resize_allowed",
    "live_endpoint_allowed",
    "live_endpoint_called_count",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
    "forced_trades_allowed",
    "manual_trade_level_override_allowed",
    "secret_value_exposed",
    "raw_payload_exposed",
    "broker_order_identifier_exposed",
    "unsafe_write_counter_total",
    "blockers",
    "blocker_count",
    "next_required_action",
    "boundary",
    "validation_error_count",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def paperops_paper_lifecycle_polling_enablement_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_HISTORY,
        runtime / PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_EVENT_LOG,
    )


def read_latest_paperops_paper_lifecycle_polling_enablement(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_paper_lifecycle_polling_enablement_paths(settings)
    return _read_json(output_path)


def _source_paperops_2(settings: Settings) -> dict[str, Any]:
    source = read_latest_paperops_alpaca_paper_post(settings)
    if source:
        return source
    return build_paperops_alpaca_paper_post(settings=settings, execute_post=False)


def _submitted_paper_order_count(
    source: dict[str, Any],
    settings: Settings,
) -> int:
    records = [
        record
        for record in source.get("selected_post_records", []) or []
        if isinstance(record, dict)
    ]
    source_submitted = sum(
        1
        for record in records
        if record.get("status") == "submitted_to_alpaca_paper"
        and record.get("alpaca_paper_post_succeeded") is True
    )
    if source_submitted:
        return source_submitted
    lifecycle = _read_json(_runtime_dir(settings) / "paperops_paper_lifecycle_poller.json")
    lifecycle_count = _int(lifecycle.get("source_submitted_paper_order_count"))
    if lifecycle_count:
        return lifecycle_count
    return len(
        [
            record
            for record in lifecycle.get("poll_candidate_records", []) or []
            if isinstance(record, dict)
            and str(record.get("client_order_id") or record.get("idempotency_key") or "").strip()
        ]
    )


def _operator_sleeve_submitted_paper_order_count(settings: Settings) -> int:
    ledger = _read_json(paperops_alpaca_paper_post_submission_ledger_path(settings))
    submitted_client_order_ids = set(ledger.get("submitted_client_order_ids", []) or [])
    submitted_source_keys = set(
        ledger.get("submitted_source_idempotency_keys", []) or []
    )
    identities: set[tuple[str, str]] = set()
    for record in ledger.get("submission_records", []) or []:
        if not isinstance(record, dict):
            continue
        request_preview = record.get("request_preview")
        if not isinstance(request_preview, dict):
            request_preview = {}
        client_order_id = str(
            record.get("client_order_id")
            or request_preview.get("client_order_id")
            or record.get("idempotency_key")
            or ""
        ).strip()
        source_key = str(
            record.get("source_idempotency_key")
            or request_preview.get("source_idempotency_key")
            or ""
        ).strip()
        if not (
            record.get("status") == "submitted_to_alpaca_paper"
            and record.get("previously_submitted_to_alpaca_paper") is True
            and record.get("idempotency_namespace")
            == OPERATOR_SLEEVE_IDEMPOTENCY_NAMESPACE
            and record.get("evidence_class") == "operator_exploratory_unvalidated"
            and record.get("proof_credit_allowed") is False
            and client_order_id.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
            and source_key.startswith(OPERATOR_SLEEVE_CLIENT_ORDER_PREFIX)
            and client_order_id in submitted_client_order_ids
            and source_key in submitted_source_keys
        ):
            continue
        identities.add((client_order_id, source_key))
    return len(identities)


def _blockers(
    *,
    settings: Settings,
    source: dict[str, Any],
    source_validation_errors: list[str],
    endpoint: dict[str, Any],
    operator_sleeve_submitted_count: int,
) -> list[str]:
    blockers: list[str] = []
    if settings.mode != "paper":
        blockers.append("mode_not_paper")
    if settings.live_capital_enabled:
        blockers.append("live_capital_enabled")
    if endpoint.get("paper_endpoint_confirmed") is not True:
        blockers.append("alpaca_endpoint_not_paper")
    if endpoint.get("alpaca_api_key_configured") is not True:
        blockers.append("alpaca_api_key_missing")
    if endpoint.get("alpaca_api_secret_configured") is not True:
        blockers.append("alpaca_api_secret_missing")
    if not source:
        blockers.append("paperops_2_source_missing")
    if source_validation_errors:
        blockers.append("paperops_2_source_invalid")
    if (
        source
        and source.get("paper_post_path_available") is not True
        and operator_sleeve_submitted_count < 1
    ):
        blockers.append("paperops_2_paper_post_path_not_available")
    if source and source.get("status") not in {
        "ready_pending_explicit_execute",
        "ready_no_fresh_eligible_order",
        "submitted_to_alpaca_paper",
        "broker_post_failed_sanitized",
    } and operator_sleeve_submitted_count < 1:
        blockers.append("paperops_2_status_not_pollable")
    return sorted(set(blockers))


def _status(blockers: list[str], submitted_count: int) -> str:
    if "mode_not_paper" in blockers:
        return "blocked_not_paper_mode"
    if "live_capital_enabled" in blockers:
        return "blocked_live_capital_enabled"
    if any(blocker.startswith("alpaca_") for blocker in blockers):
        return "blocked_alpaca_paper_endpoint_or_credentials"
    if "paperops_2_source_missing" in blockers:
        return "blocked_missing_paperops_alpaca_post_source"
    if "paperops_2_source_invalid" in blockers:
        return "blocked_invalid_paperops_alpaca_post_source"
    if blockers:
        return "blocked_pending_prerequisites"
    if submitted_count < 1:
        return "enabled_pending_submitted_paper_orders"
    return "enabled_pending_explicit_poll"


def build_paperops_paper_lifecycle_polling_enablement(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    endpoint = _endpoint_context(settings)
    source = _source_paperops_2(settings)
    source_validation_errors = validate_paperops_alpaca_paper_post(source) if source else []
    operator_sleeve_submitted_count = _operator_sleeve_submitted_paper_order_count(
        settings
    )
    submitted_count = max(
        _submitted_paper_order_count(source, settings),
        operator_sleeve_submitted_count,
    )
    blockers = _blockers(
        settings=settings,
        source=source,
        source_validation_errors=source_validation_errors,
        endpoint=endpoint,
        operator_sleeve_submitted_count=operator_sleeve_submitted_count,
    )
    status = _status(blockers, submitted_count)
    enabled = status in {
        "enabled_pending_submitted_paper_orders",
        "enabled_pending_explicit_poll",
    }
    paper_poll_path_available = enabled and submitted_count > 0
    artifact = {
        "schema_version": PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_SCHEMA_VERSION,
        "artifact_type": "paperops_paper_lifecycle_polling_enablement",
        "artifact_id": "paperops:pt-6:paper-lifecycle-polling-enable",
        "phase": "PaperOps",
        "stage": "PT-6",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "active_lifecycle_polling_enabled": enabled,
        "paper_lifecycle_polling_effective": enabled,
        "env_file_edited": False,
        "env_mutation_allowed": False,
        "paper_poll_path_available": paper_poll_path_available,
        "paper_poll_idle_until_submitted_order": enabled and submitted_count < 1,
        "explicit_poll_flag_required": True,
        "poll_now_requested": False,
        "paperops_2_status": source.get("status", "missing"),
        "paperops_2_source_present": bool(source),
        "paperops_2_source_valid": bool(source) and not source_validation_errors,
        "paperops_2_validation_error_count": len(source_validation_errors),
        "paperops_2_validation_errors": source_validation_errors[:12],
        "paperops_2_paper_post_path_available": (
            source.get("paper_post_path_available") is True
        ),
        "paperops_2_eligible_submit_record_count": _int(
            source.get("eligible_submit_record_count")
        ),
        "paperops_2_selected_submit_record_count": _int(
            source.get("selected_submit_record_count")
        ),
        "paperops_2_submitted_paper_order_count": submitted_count,
        "operator_sleeve_submitted_paper_order_count": (
            operator_sleeve_submitted_count
        ),
        "operator_sleeve_read_only_polling_authorized": (
            operator_sleeve_submitted_count > 0
        ),
        "paperops_2_alpaca_paper_post_called_count": _int(
            source.get("alpaca_paper_post_called_count")
        ),
        "paperops_2_alpaca_paper_post_succeeded_count": _int(
            source.get("alpaca_paper_post_succeeded_count")
        ),
        "endpoint_classification": endpoint["endpoint_classification"],
        "paper_endpoint_confirmed": endpoint["paper_endpoint_confirmed"],
        "alpaca_paper_flag": endpoint["alpaca_paper_flag"],
        "alpaca_api_key_configured": endpoint["alpaca_api_key_configured"],
        "alpaca_api_secret_configured": endpoint["alpaca_api_secret_configured"],
        "base_url_exposed": False,
        "authorization_header_exposed": False,
        "paper_broker_get_allowed": enabled,
        "alpaca_paper_get_allowed": enabled,
        "broker_get_called_count": 0,
        "alpaca_paper_get_called_count": 0,
        "paper_order_submission_allowed": False,
        "broker_write_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "order_cancel_allowed": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "live_endpoint_allowed": False,
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "broker_order_identifier_exposed": False,
        "unsafe_write_counter_total": 0,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "next_required_action": (
            "Run PT-6 active polling in the PaperOps cycle after PaperOps-2 submits a "
            "paper order."
            if enabled and submitted_count < 1
            else (
                "PaperOps-3 may poll submitted paper orders through the PT-6 active "
                "polling checker."
                if enabled
                else "Resolve PT-6 blockers before active paper lifecycle polling."
            )
        ),
        "boundary": PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_BOUNDARY,
        "validation_error_count": 0,
    }
    artifact["validation_errors"] = validate_paperops_paper_lifecycle_polling_enablement(
        artifact
    )
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_paper_lifecycle_polling_enablement(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    missing = sorted(
        set(PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_PUBLIC_FIELDS) - set(artifact)
    )
    if missing:
        errors.append(
            "paperops_lifecycle_polling_enablement_missing_fields:" + ",".join(missing)
        )
    if artifact.get("schema_version") != PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_SCHEMA_VERSION:
        errors.append("paperops_lifecycle_polling_enablement_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_paper_lifecycle_polling_enablement":
        errors.append("paperops_lifecycle_polling_enablement_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-6":
        errors.append("paperops_lifecycle_polling_enablement_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_lifecycle_polling_enablement_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_lifecycle_polling_enablement_mode_not_paper")
    for key in (
        "env_file_edited",
        "env_mutation_allowed",
        "poll_now_requested",
        "paper_order_submission_allowed",
        "broker_write_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "order_cancel_allowed",
        "position_close_allowed",
        "position_resize_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "manual_trade_level_override_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "broker_order_identifier_exposed",
        "base_url_exposed",
        "authorization_header_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_lifecycle_polling_enablement_forbidden:{key}")
    for key in (
        "broker_get_called_count",
        "alpaca_paper_get_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(
                f"paperops_lifecycle_polling_enablement_unsafe_counter_nonzero:{key}"
            )
    if artifact.get("explicit_poll_flag_required") is not True:
        errors.append("paperops_lifecycle_polling_enablement_poll_flag_not_required")
    enabled = artifact.get("active_lifecycle_polling_enabled") is True
    if enabled:
        if artifact.get("status") not in {
            "enabled_pending_submitted_paper_orders",
            "enabled_pending_explicit_poll",
        }:
            errors.append("paperops_lifecycle_polling_enablement_status_invalid")
        if artifact.get("paper_lifecycle_polling_effective") is not True:
            errors.append("paperops_lifecycle_polling_enablement_effective_false")
        if artifact.get("paper_broker_get_allowed") is not True:
            errors.append("paperops_lifecycle_polling_enablement_broker_get_not_allowed")
        if artifact.get("alpaca_paper_get_allowed") is not True:
            errors.append("paperops_lifecycle_polling_enablement_alpaca_get_not_allowed")
        if artifact.get("paper_endpoint_confirmed") is not True:
            errors.append("paperops_lifecycle_polling_enablement_endpoint_not_paper")
        if artifact.get("alpaca_api_key_configured") is not True:
            errors.append("paperops_lifecycle_polling_enablement_key_missing")
        if artifact.get("alpaca_api_secret_configured") is not True:
            errors.append("paperops_lifecycle_polling_enablement_secret_missing")
        if artifact.get("paperops_2_source_valid") is not True:
            errors.append("paperops_lifecycle_polling_enablement_source_invalid")
        if (
            artifact.get("paperops_2_paper_post_path_available") is not True
            and artifact.get("operator_sleeve_read_only_polling_authorized") is not True
        ):
            errors.append("paperops_lifecycle_polling_enablement_post_path_unavailable")
        if (
            artifact.get("status") == "enabled_pending_explicit_poll"
            and _int(artifact.get("paperops_2_submitted_paper_order_count")) < 1
        ):
            errors.append("paperops_lifecycle_polling_enablement_poll_without_source")
        if (
            artifact.get("status") == "enabled_pending_submitted_paper_orders"
            and artifact.get("paper_poll_idle_until_submitted_order") is not True
        ):
            errors.append("paperops_lifecycle_polling_enablement_idle_flag_false")
    else:
        if artifact.get("paper_poll_path_available") is True:
            errors.append("paperops_lifecycle_polling_enablement_path_available_while_disabled")
        if artifact.get("paper_broker_get_allowed") is True:
            errors.append("paperops_lifecycle_polling_enablement_broker_get_while_disabled")
        if artifact.get("alpaca_paper_get_allowed") is True:
            errors.append("paperops_lifecycle_polling_enablement_alpaca_get_while_disabled")
    if artifact.get("paper_poll_path_available") is True and _int(
        artifact.get("paperops_2_submitted_paper_order_count")
    ) < 1:
        errors.append("paperops_lifecycle_polling_enablement_path_without_submitted_order")
    if artifact.get("validation_error_count") not in {
        None,
        len(artifact.get("validation_errors", [])),
    }:
        errors.append("paperops_lifecycle_polling_enablement_validation_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "PT-6 records runtime active Alpaca paper lifecycle polling enablement",
        "read-only Alpaca paper GET",
        "successfully submitted a paper order",
        "cannot edit .env",
        "cannot submit orders",
        "cannot call broker POST routes",
        "cannot call live endpoints",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_lifecycle_polling_enablement_boundary_weak")
            break
    return sorted(set(errors))


def write_paperops_paper_lifecycle_polling_enablement(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = (
        paperops_paper_lifecycle_polling_enablement_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_EVENT_TYPE,
            PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_COMPONENT,
            payload={
                "status": written["status"],
                "active_lifecycle_polling_enabled": written[
                    "active_lifecycle_polling_enabled"
                ],
                "paper_poll_path_available": written["paper_poll_path_available"],
                "paperops_2_submitted_paper_order_count": written[
                    "paperops_2_submitted_paper_order_count"
                ],
                "broker_get_called_count": written["broker_get_called_count"],
                "live_endpoint_called_count": written["live_endpoint_called_count"],
                "live_capital_enabled": written["live_capital_enabled"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_paper_lifecycle_polling_enablement(
        written
    )
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "active_lifecycle_polling_enabled": written.get(
            "active_lifecycle_polling_enabled"
        ),
        "paper_poll_path_available": written.get("paper_poll_path_available"),
        "paperops_2_submitted_paper_order_count": written.get(
            "paperops_2_submitted_paper_order_count"
        ),
        "broker_get_called_count": written.get("broker_get_called_count"),
        "live_endpoint_called_count": written.get("live_endpoint_called_count"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_paper_lifecycle_polling_enablement_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_paper_lifecycle_polling_enablement(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_SCHEMA_VERSION,
            "artifact_type": "paperops_paper_lifecycle_polling_enablement",
            "artifact_id": "paperops:pt-6:paper-lifecycle-polling-enable",
            "phase": "PaperOps",
            "stage": "PT-6",
            "status": "not_run",
            "generated_at": None,
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "mode": "paper",
            "active_lifecycle_polling_enabled": False,
            "paper_lifecycle_polling_effective": False,
            "env_file_edited": False,
            "env_mutation_allowed": False,
            "paper_poll_path_available": False,
            "paper_poll_idle_until_submitted_order": False,
            "explicit_poll_flag_required": True,
            "poll_now_requested": False,
            "paperops_2_status": "not_run",
            "paperops_2_source_present": False,
            "paperops_2_source_valid": False,
            "paperops_2_validation_error_count": 0,
            "paperops_2_paper_post_path_available": False,
            "paperops_2_eligible_submit_record_count": 0,
            "paperops_2_submitted_paper_order_count": 0,
            "endpoint_classification": "not_run",
            "paper_endpoint_confirmed": False,
            "alpaca_api_key_configured": False,
            "alpaca_api_secret_configured": False,
            "paper_broker_get_allowed": False,
            "alpaca_paper_get_allowed": False,
            "broker_get_called_count": 0,
            "alpaca_paper_get_called_count": 0,
            "paper_order_submission_allowed": False,
            "broker_write_allowed": False,
            "broker_post_allowed": False,
            "alpaca_post_allowed": False,
            "order_cancel_allowed": False,
            "position_close_allowed": False,
            "position_resize_allowed": False,
            "live_endpoint_allowed": False,
            "live_endpoint_called_count": 0,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "forced_trades_allowed": False,
            "manual_trade_level_override_allowed": False,
            "secret_value_exposed": False,
            "raw_payload_exposed": False,
            "broker_order_identifier_exposed": False,
            "unsafe_write_counter_total": 0,
            "blockers": ["pt6_not_run"],
            "blocker_count": 1,
            "next_required_action": "Run PT-6 active paper lifecycle polling enablement.",
            "validation_error_count": 0,
            "boundary": PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_BOUNDARY,
        }
    public = {
        key: artifact.get(key)
        for key in PAPEROPS_LIFECYCLE_POLLING_ENABLEMENT_PUBLIC_FIELDS
    }
    public["blockers"] = list(public.get("blockers") or [])
    public["validation_error_count"] = len(artifact.get("validation_errors", []))
    return public
