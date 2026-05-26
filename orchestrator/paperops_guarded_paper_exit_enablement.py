"""PT-7 guarded PaperOps paper-exit runtime enablement.

PT-7 records the runtime gate that lets PaperOps-4 become an operational paper
exit path without editing environment files. It does not close positions. The
actual Alpaca paper DELETE remains in PaperOps-4 and still requires an explicit
paper-exit command plus a valid open-position readback from PaperOps-3.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paperops_alpaca_paper_post import _endpoint_context
from orchestrator.paperops_paper_lifecycle_poller import (
    READBACK_READY_STATUSES,
    build_paperops_paper_lifecycle_poller,
    read_latest_paperops_paper_lifecycle_poller,
    validate_paperops_paper_lifecycle_poller,
)
from orchestrator.paperops_paper_lifecycle_polling_enablement import (
    read_latest_paperops_paper_lifecycle_polling_enablement,
    validate_paperops_paper_lifecycle_polling_enablement,
)


PAPEROPS_GUARDED_EXIT_ENABLEMENT_SCHEMA_VERSION = 1
PAPEROPS_GUARDED_EXIT_ENABLEMENT_RUNTIME_ARTIFACT = (
    "paperops_guarded_paper_exit_enablement.json"
)
PAPEROPS_GUARDED_EXIT_ENABLEMENT_HISTORY = (
    "paperops_guarded_paper_exit_enablement_history.jsonl"
)
PAPEROPS_GUARDED_EXIT_ENABLEMENT_EVENT_LOG = (
    "paperops_guarded_paper_exit_enablement_events.jsonl"
)
PAPEROPS_GUARDED_EXIT_ENABLEMENT_EVENT_TYPE = (
    "paperops_guarded_paper_exit_enablement_recorded"
)
PAPEROPS_GUARDED_EXIT_ENABLEMENT_COMPONENT = "paperops_guarded_paper_exit_enablement"

PAPEROPS_GUARDED_EXIT_ENABLEMENT_READY_STATUSES = frozenset(
    {
        "enabled_pending_open_position_readback",
        "enabled_pending_explicit_exit",
    }
)

PAPEROPS_GUARDED_EXIT_ENABLEMENT_BOUNDARY = (
    "PT-7 records runtime guarded Alpaca paper-exit enablement for PaperOps. "
    "It may make PaperOps-4 eligible to close Alpaca paper positions only "
    "when QADAM_MODE=paper, live capital is disabled, PT-6 active paper "
    "lifecycle polling is enabled, PaperOps-3 has a valid readback, the "
    "Alpaca endpoint is classified as paper, paper credentials are configured, "
    "an open-position readback exists, and PaperOps-4 is called with the "
    "explicit paper-exit flag. PT-7 cannot edit .env or secrets, cannot call "
    "Alpaca, cannot call broker POST routes, cannot close, cancel, or resize "
    "positions by itself, cannot call live endpoints, cannot force trades, "
    "cannot grant Phase 7 proof credit, cannot expose credentials, and cannot "
    "enable live capital."
)

PAPEROPS_GUARDED_EXIT_ENABLEMENT_PUBLIC_FIELDS: tuple[str, ...] = (
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
    "guarded_paper_exit_enabled",
    "alpaca_paper_exit_effective",
    "settings_alpaca_paper_exit_enabled",
    "runtime_artifact_override_enabled",
    "env_file_edited",
    "env_mutation_allowed",
    "paper_exit_path_available",
    "paper_exit_idle_until_open_position",
    "explicit_exit_flag_required",
    "execute_exit_requested",
    "lifecycle_polling_enablement_status",
    "lifecycle_polling_enablement_ready",
    "paperops_3_status",
    "paperops_3_source_present",
    "paperops_3_source_valid",
    "paperops_3_validation_error_count",
    "paperops_3_open_position_count",
    "paperops_3_lifecycle_record_count",
    "endpoint_classification",
    "paper_endpoint_confirmed",
    "alpaca_api_key_configured",
    "alpaca_api_secret_configured",
    "position_close_allowed",
    "paper_position_close_called_count",
    "broker_write_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "order_cancel_allowed",
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


def paperops_guarded_paper_exit_enablement_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_GUARDED_EXIT_ENABLEMENT_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_GUARDED_EXIT_ENABLEMENT_HISTORY,
        runtime / PAPEROPS_GUARDED_EXIT_ENABLEMENT_EVENT_LOG,
    )


def read_latest_paperops_guarded_paper_exit_enablement(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_guarded_paper_exit_enablement_paths(settings)
    return _read_json(output_path)


def _source_paperops_3(settings: Settings) -> tuple[dict[str, Any], bool]:
    source = read_latest_paperops_paper_lifecycle_poller(settings)
    if source:
        return source, True
    return build_paperops_paper_lifecycle_poller(
        settings=settings,
        poll_paper_orders=False,
    ), False


def _lifecycle_polling_enablement_ready(enablement: dict[str, Any]) -> bool:
    return (
        enablement.get("status")
        in {
            "enabled_pending_submitted_paper_orders",
            "enabled_pending_explicit_poll",
        }
        and enablement.get("active_lifecycle_polling_enabled") is True
        and enablement.get("paper_lifecycle_polling_effective") is True
        and enablement.get("paper_endpoint_confirmed") is True
        and enablement.get("paperops_2_source_valid") is True
        and enablement.get("live_capital_enabled") is False
        and enablement.get("broker_post_allowed") is False
        and enablement.get("live_endpoint_allowed") is False
        and enablement.get("phase7_proof_credit_allowed") is False
        and _int(enablement.get("broker_get_called_count")) == 0
        and _int(enablement.get("live_endpoint_called_count")) == 0
        and _int(enablement.get("unsafe_write_counter_total")) == 0
        and not validate_paperops_paper_lifecycle_polling_enablement(enablement)
    )


def _lifecycle_record_count(source: dict[str, Any]) -> int:
    return len(
        [
            record
            for record in source.get("lifecycle_mirror_records", []) or []
            if isinstance(record, dict)
        ]
    )


def _open_position_count(source: dict[str, Any]) -> int:
    explicit_count = _int(source.get("open_position_count"))
    if explicit_count:
        return explicit_count
    return sum(
        1
        for record in source.get("lifecycle_mirror_records", []) or []
        if isinstance(record, dict) and record.get("lifecycle_state") == "open_position"
    )


def _blockers(
    *,
    settings: Settings,
    endpoint: dict[str, Any],
    lifecycle_enablement_ready: bool,
    source: dict[str, Any],
    source_validation_errors: list[str],
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
    if not lifecycle_enablement_ready:
        blockers.append("pt6_lifecycle_polling_enablement_not_ready")
    if not source:
        blockers.append("paperops_3_source_missing")
    if source_validation_errors:
        blockers.append("paperops_3_source_invalid")
    if source and source.get("status") not in READBACK_READY_STATUSES:
        blockers.append("paperops_3_status_not_exit_eligible")
    return sorted(set(blockers))


def _status(blockers: list[str], open_position_count: int) -> str:
    if "mode_not_paper" in blockers:
        return "blocked_not_paper_mode"
    if "live_capital_enabled" in blockers:
        return "blocked_live_capital_enabled"
    if any(blocker.startswith("alpaca_") for blocker in blockers):
        return "blocked_alpaca_paper_endpoint_or_credentials"
    if "pt6_lifecycle_polling_enablement_not_ready" in blockers:
        return "blocked_lifecycle_polling_enablement_not_ready"
    if "paperops_3_source_missing" in blockers:
        return "blocked_missing_paper_lifecycle_source"
    if "paperops_3_source_invalid" in blockers:
        return "blocked_invalid_paper_lifecycle_source"
    if blockers:
        return "blocked_pending_prerequisites"
    if open_position_count < 1:
        return "enabled_pending_open_position_readback"
    return "enabled_pending_explicit_exit"


def build_paperops_guarded_paper_exit_enablement(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    endpoint = _endpoint_context(settings)
    lifecycle_enablement = read_latest_paperops_paper_lifecycle_polling_enablement(
        settings
    )
    lifecycle_enablement_ready = _lifecycle_polling_enablement_ready(
        lifecycle_enablement
    )
    source, source_recorded = _source_paperops_3(settings)
    source_validation_errors = validate_paperops_paper_lifecycle_poller(source) if source else []
    open_position_count = _open_position_count(source)
    blockers = _blockers(
        settings=settings,
        endpoint=endpoint,
        lifecycle_enablement_ready=lifecycle_enablement_ready,
        source=source,
        source_validation_errors=source_validation_errors,
    )
    status = _status(blockers, open_position_count)
    enabled = status in PAPEROPS_GUARDED_EXIT_ENABLEMENT_READY_STATUSES
    paper_exit_path_available = enabled and open_position_count > 0
    artifact = {
        "schema_version": PAPEROPS_GUARDED_EXIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_type": "paperops_guarded_paper_exit_enablement",
        "artifact_id": "paperops:pt-7:guarded-paper-exit-enable",
        "phase": "PaperOps",
        "stage": "PT-7",
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
        "guarded_paper_exit_enabled": enabled,
        "alpaca_paper_exit_effective": settings.alpaca_paper_exit_enabled or enabled,
        "settings_alpaca_paper_exit_enabled": settings.alpaca_paper_exit_enabled,
        "runtime_artifact_override_enabled": enabled
        and not settings.alpaca_paper_exit_enabled,
        "env_file_edited": False,
        "env_mutation_allowed": False,
        "paper_exit_path_available": paper_exit_path_available,
        "paper_exit_idle_until_open_position": enabled and open_position_count < 1,
        "explicit_exit_flag_required": True,
        "execute_exit_requested": False,
        "lifecycle_polling_enablement_status": lifecycle_enablement.get(
            "status",
            "missing",
        ),
        "lifecycle_polling_enablement_ready": lifecycle_enablement_ready,
        "paperops_3_status": source.get("status", "missing"),
        "paperops_3_source_present": bool(source),
        "paperops_3_source_recorded": source_recorded,
        "paperops_3_source_valid": bool(source) and not source_validation_errors,
        "paperops_3_validation_error_count": len(source_validation_errors),
        "paperops_3_validation_errors": source_validation_errors[:12],
        "paperops_3_open_position_count": open_position_count,
        "paperops_3_lifecycle_record_count": _lifecycle_record_count(source),
        "paperops_3_source_submitted_order_count": _int(
            source.get("source_submitted_paper_order_count")
        ),
        "endpoint_classification": endpoint["endpoint_classification"],
        "paper_endpoint_confirmed": endpoint["paper_endpoint_confirmed"],
        "alpaca_paper_flag": endpoint["alpaca_paper_flag"],
        "alpaca_api_key_configured": endpoint["alpaca_api_key_configured"],
        "alpaca_api_secret_configured": endpoint["alpaca_api_secret_configured"],
        "base_url_exposed": False,
        "authorization_header_exposed": False,
        "position_close_allowed": False,
        "paper_position_close_called_count": 0,
        "broker_write_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "order_cancel_allowed": False,
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
            "PaperOps-4 is enabled but idle until PaperOps-3 reads back an open "
            "paper position."
            if enabled and open_position_count < 1
            else (
                "PaperOps-4 may be called with --execute-paper-exit after explicit "
                "Fund Manager review of the open paper position."
                if enabled
                else "Resolve PT-7 blockers before enabling the guarded paper exit path."
            )
        ),
        "boundary": PAPEROPS_GUARDED_EXIT_ENABLEMENT_BOUNDARY,
        "validation_error_count": 0,
    }
    artifact["validation_errors"] = validate_paperops_guarded_paper_exit_enablement(
        artifact
    )
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_guarded_paper_exit_enablement(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    missing = sorted(set(PAPEROPS_GUARDED_EXIT_ENABLEMENT_PUBLIC_FIELDS) - set(artifact))
    if missing:
        errors.append("paperops_guarded_exit_enablement_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_GUARDED_EXIT_ENABLEMENT_SCHEMA_VERSION:
        errors.append("paperops_guarded_exit_enablement_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_guarded_paper_exit_enablement":
        errors.append("paperops_guarded_exit_enablement_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-7":
        errors.append("paperops_guarded_exit_enablement_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_guarded_exit_enablement_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_guarded_exit_enablement_mode_not_paper")
    for key in (
        "env_file_edited",
        "env_mutation_allowed",
        "execute_exit_requested",
        "position_close_allowed",
        "broker_write_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "order_cancel_allowed",
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
            errors.append(f"paperops_guarded_exit_enablement_forbidden:{key}")
    for key in (
        "paper_position_close_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_guarded_exit_enablement_unsafe_counter_nonzero:{key}")
    if artifact.get("explicit_exit_flag_required") is not True:
        errors.append("paperops_guarded_exit_enablement_exit_flag_not_required")
    enabled = artifact.get("guarded_paper_exit_enabled") is True
    if enabled:
        if artifact.get("status") not in PAPEROPS_GUARDED_EXIT_ENABLEMENT_READY_STATUSES:
            errors.append("paperops_guarded_exit_enablement_status_invalid")
        if artifact.get("alpaca_paper_exit_effective") is not True:
            errors.append("paperops_guarded_exit_enablement_effective_false")
        if (
            artifact.get("settings_alpaca_paper_exit_enabled") is not True
            and artifact.get("runtime_artifact_override_enabled") is not True
        ):
            errors.append("paperops_guarded_exit_enablement_runtime_override_false")
        if artifact.get("paper_endpoint_confirmed") is not True:
            errors.append("paperops_guarded_exit_enablement_endpoint_not_paper")
        if artifact.get("alpaca_api_key_configured") is not True:
            errors.append("paperops_guarded_exit_enablement_key_missing")
        if artifact.get("alpaca_api_secret_configured") is not True:
            errors.append("paperops_guarded_exit_enablement_secret_missing")
        if artifact.get("lifecycle_polling_enablement_ready") is not True:
            errors.append("paperops_guarded_exit_enablement_pt6_not_ready")
        if artifact.get("paperops_3_source_valid") is not True:
            errors.append("paperops_guarded_exit_enablement_source_invalid")
        if artifact.get("paperops_3_status") not in READBACK_READY_STATUSES:
            errors.append("paperops_guarded_exit_enablement_source_status_invalid")
        if (
            artifact.get("status") == "enabled_pending_explicit_exit"
            and _int(artifact.get("paperops_3_open_position_count")) < 1
        ):
            errors.append("paperops_guarded_exit_enablement_exit_without_open_position")
        if (
            artifact.get("status") == "enabled_pending_open_position_readback"
            and artifact.get("paper_exit_idle_until_open_position") is not True
        ):
            errors.append("paperops_guarded_exit_enablement_idle_flag_false")
    else:
        if artifact.get("paper_exit_path_available") is True:
            errors.append("paperops_guarded_exit_enablement_path_available_while_disabled")
        if artifact.get("alpaca_paper_exit_effective") is True:
            errors.append("paperops_guarded_exit_enablement_effective_while_disabled")
    if artifact.get("paper_exit_path_available") is True and _int(
        artifact.get("paperops_3_open_position_count")
    ) < 1:
        errors.append("paperops_guarded_exit_enablement_path_without_open_position")
    if artifact.get("validation_error_count") not in {
        None,
        len(artifact.get("validation_errors", [])),
    }:
        errors.append("paperops_guarded_exit_enablement_validation_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "PT-7 records runtime guarded Alpaca paper-exit enablement",
        "explicit paper-exit flag",
        "cannot edit .env",
        "cannot call Alpaca",
        "cannot close, cancel, or resize positions by itself",
        "cannot call live endpoints",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_guarded_exit_enablement_boundary_weak")
            break
    return sorted(set(errors))


def write_paperops_guarded_paper_exit_enablement(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = (
        paperops_guarded_paper_exit_enablement_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_GUARDED_EXIT_ENABLEMENT_EVENT_TYPE,
            PAPEROPS_GUARDED_EXIT_ENABLEMENT_COMPONENT,
            payload={
                "status": written["status"],
                "guarded_paper_exit_enabled": written["guarded_paper_exit_enabled"],
                "alpaca_paper_exit_effective": written[
                    "alpaca_paper_exit_effective"
                ],
                "runtime_artifact_override_enabled": written[
                    "runtime_artifact_override_enabled"
                ],
                "paper_exit_path_available": written["paper_exit_path_available"],
                "paperops_3_open_position_count": written[
                    "paperops_3_open_position_count"
                ],
                "paper_position_close_called_count": written[
                    "paper_position_close_called_count"
                ],
                "live_endpoint_called_count": written["live_endpoint_called_count"],
                "live_capital_enabled": written["live_capital_enabled"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_guarded_paper_exit_enablement(
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
        "schema_version": PAPEROPS_GUARDED_EXIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "guarded_paper_exit_enabled": written.get("guarded_paper_exit_enabled"),
        "alpaca_paper_exit_effective": written.get("alpaca_paper_exit_effective"),
        "runtime_artifact_override_enabled": written.get(
            "runtime_artifact_override_enabled"
        ),
        "paper_exit_path_available": written.get("paper_exit_path_available"),
        "paperops_3_open_position_count": written.get("paperops_3_open_position_count"),
        "paper_position_close_called_count": written.get(
            "paper_position_close_called_count"
        ),
        "live_endpoint_called_count": written.get("live_endpoint_called_count"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_guarded_paper_exit_enablement_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_guarded_paper_exit_enablement(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_GUARDED_EXIT_ENABLEMENT_SCHEMA_VERSION,
            "artifact_type": "paperops_guarded_paper_exit_enablement",
            "artifact_id": "paperops:pt-7:guarded-paper-exit-enable",
            "phase": "PaperOps",
            "stage": "PT-7",
            "status": "not_run",
            "generated_at": None,
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "mode": "paper",
            "guarded_paper_exit_enabled": False,
            "alpaca_paper_exit_effective": False,
            "settings_alpaca_paper_exit_enabled": False,
            "runtime_artifact_override_enabled": False,
            "env_file_edited": False,
            "env_mutation_allowed": False,
            "paper_exit_path_available": False,
            "paper_exit_idle_until_open_position": False,
            "explicit_exit_flag_required": True,
            "execute_exit_requested": False,
            "lifecycle_polling_enablement_status": "not_run",
            "lifecycle_polling_enablement_ready": False,
            "paperops_3_status": "not_run",
            "paperops_3_source_present": False,
            "paperops_3_source_valid": False,
            "paperops_3_validation_error_count": 0,
            "paperops_3_open_position_count": 0,
            "paperops_3_lifecycle_record_count": 0,
            "endpoint_classification": "not_run",
            "paper_endpoint_confirmed": False,
            "alpaca_api_key_configured": False,
            "alpaca_api_secret_configured": False,
            "position_close_allowed": False,
            "paper_position_close_called_count": 0,
            "broker_write_allowed": False,
            "broker_post_allowed": False,
            "alpaca_post_allowed": False,
            "order_cancel_allowed": False,
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
            "blockers": ["pt7_not_run"],
            "blocker_count": 1,
            "next_required_action": "Run PT-7 guarded paper-exit enablement.",
            "validation_error_count": 0,
            "boundary": PAPEROPS_GUARDED_EXIT_ENABLEMENT_BOUNDARY,
        }
    public = {
        key: artifact.get(key)
        for key in PAPEROPS_GUARDED_EXIT_ENABLEMENT_PUBLIC_FIELDS
    }
    public["blockers"] = list(public.get("blockers") or [])
    public["validation_error_count"] = len(artifact.get("validation_errors", []))
    return public
