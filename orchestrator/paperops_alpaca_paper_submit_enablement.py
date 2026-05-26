"""PT-5 Alpaca paper-submit runtime enablement.

PT-5 enables the PaperOps Alpaca paper-submit path through a recorded runtime
artifact instead of editing environment files. It does not submit orders. The
actual Alpaca POST still belongs to PaperOps-2 and still requires an explicit
submit command.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paper_account import ALPACA_PAPER_BASE_URL
from orchestrator.paperops_auto_approval_staged_order import (
    read_latest_paperops_auto_approval_staged_order,
    validate_paperops_auto_approval_staged_order,
)
from orchestrator.paperops_qualified_setup_production import (
    read_latest_paperops_qualified_setup_production,
    validate_paperops_qualified_setup_production,
)
from orchestrator.secrets import secret_status, secret_value


PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_SCHEMA_VERSION = 1
PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT = (
    "paperops_alpaca_paper_submit_enablement.json"
)
PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_HISTORY = (
    "paperops_alpaca_paper_submit_enablement_history.jsonl"
)
PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_EVENT_LOG = (
    "paperops_alpaca_paper_submit_enablement_events.jsonl"
)
PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_EVENT_TYPE = (
    "paperops_alpaca_paper_submit_enablement_recorded"
)
PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_COMPONENT = (
    "paperops_alpaca_paper_submit_enablement"
)

PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_BOUNDARY = (
    "PT-5 records runtime Alpaca paper-submit enablement for PaperOps. It may "
    "make PaperOps-2 eligible to submit PT-4 staged Alpaca paper orders only "
    "when QADAM_MODE=paper, live capital is disabled, PT-3 has a qualified "
    "setup path, PT-4 has a staged paper order, the Alpaca endpoint is "
    "classified as paper, paper credentials are configured, and PaperOps-2 is "
    "called with the explicit submit flag. PT-5 cannot edit .env or secrets, "
    "cannot call Alpaca, cannot call live endpoints, cannot submit orders by "
    "itself, cannot force trades, cannot grant Phase 7 proof credit, cannot "
    "expose credentials, and cannot enable live capital."
)

PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_PUBLIC_FIELDS: tuple[str, ...] = (
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
    "paper_submit_runtime_enablement_enabled",
    "alpaca_paper_submit_enabled",
    "alpaca_paper_submit_effective",
    "settings_alpaca_paper_submit_enabled",
    "runtime_artifact_override_enabled",
    "env_file_edited",
    "env_mutation_allowed",
    "paper_post_path_available",
    "explicit_submit_flag_required",
    "execute_post_requested",
    "pt3_status",
    "pt3_path_ready",
    "pt3_qualified_setup_count",
    "pt4_status",
    "pt4_ready_for_paperops2_submit",
    "pt4_staged_order_count",
    "endpoint_classification",
    "paper_endpoint_confirmed",
    "alpaca_api_key_configured",
    "alpaca_api_secret_configured",
    "paper_order_submission_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_allowed",
    "live_endpoint_called_count",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
    "forced_trades_allowed",
    "manual_trade_level_override_allowed",
    "secret_value_exposed",
    "raw_payload_exposed",
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


def paperops_alpaca_paper_submit_enablement_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_HISTORY,
        runtime / PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_EVENT_LOG,
    )


def read_latest_paperops_alpaca_paper_submit_enablement(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_alpaca_paper_submit_enablement_paths(settings)
    return _read_json(output_path)


def _source_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    return {
        "pt0": _read_json(runtime / "paper_live_activation.json"),
        "pt2": _read_json(runtime / "paper_operational_mode.json"),
        "pt3": read_latest_paperops_qualified_setup_production(settings),
        "pt4": read_latest_paperops_auto_approval_staged_order(settings),
    }


def _endpoint_context(settings: Settings) -> dict[str, Any]:
    paper_flag = (secret_value("ALPACA_PAPER", settings) or "true").strip().lower()
    endpoint = (
        secret_value("ALPACA_ENDPOINT", settings)
        or secret_value("ALPACA_BASE_URL", settings)
        or ALPACA_PAPER_BASE_URL
    ).rstrip("/")
    endpoint_is_paper = (
        paper_flag != "false"
        and endpoint.startswith("https://paper-api.alpaca.markets")
        and "paper-api.alpaca.markets" in endpoint
    )
    key_ready = secret_status("ALPACA_API_KEY", settings)
    secret_ready = secret_status("ALPACA_API_SECRET", settings)
    return {
        "alpaca_api_key_configured": key_ready.configured,
        "alpaca_api_secret_configured": secret_ready.configured,
        "alpaca_paper_flag": paper_flag != "false",
        "endpoint_classification": (
            "alpaca_paper_endpoint" if endpoint_is_paper else "blocked_non_paper_endpoint"
        ),
        "paper_endpoint_confirmed": endpoint_is_paper,
        "base_url_exposed": False,
        "authorization_header_exposed": False,
        "secret_value_exposed": False,
    }


def _pt0_ready(pt0: dict[str, Any]) -> bool:
    return (
        pt0.get("status") == "approved_pending_later_enablement"
        and pt0.get("approval_state") == "approved"
        and pt0.get("approval_logged") is True
        and pt0.get("paper_live_activation_approved") is True
        and pt0.get("paper_trading_system_approval_logged") is True
        and pt0.get("paper_live_mode") == "alpaca_paper_only"
        and pt0.get("paper_order_submission_allowed") is False
        and pt0.get("live_capital_enabled") is False
        and pt0.get("forced_trades_allowed") is False
    )


def _pt2_ready(pt2: dict[str, Any]) -> bool:
    return (
        pt2.get("status") == "enabled_pending_downstream_gates"
        and pt2.get("paper_operational_mode_effective") is True
        and pt2.get("paper_operational_enabled") is True
        and pt2.get("env_file_edited") is False
        and pt2.get("paper_order_submission_allowed") is False
        and pt2.get("broker_post_allowed") is False
        and pt2.get("live_capital_enabled") is False
        and _int(pt2.get("broker_post_called_count")) == 0
        and _int(pt2.get("alpaca_post_called_count")) == 0
        and _int(pt2.get("live_endpoint_called_count")) == 0
    )


def _pt3_ready(pt3: dict[str, Any]) -> bool:
    return (
        pt3.get("status")
        in {
            "production_path_ready_with_qualified_setup",
            "production_path_ready_no_current_qualified_setup",
        }
        and pt3.get("qualified_setup_production_path_ready") is True
        and pt3.get("paper_operational_mode_effective") is True
        and _int(pt3.get("production_candidate_count")) >= 1
        and pt3.get("paper_order_submission_allowed") is False
        and pt3.get("broker_post_allowed") is False
        and pt3.get("live_capital_enabled") is False
        and pt3.get("forced_trades_allowed") is False
        and pt3.get("qualified_setup_creation_forced") is False
        and _int(pt3.get("unsafe_write_counter_total")) == 0
        and not validate_paperops_qualified_setup_production(pt3)
    )


def _pt4_ready(pt4: dict[str, Any]) -> bool:
    return (
        pt4.get("status") == "staged_paper_order_ready"
        and pt4.get("ready_for_paperops2_submit") is True
        and _int(pt4.get("staged_order_count")) >= 1
        and _int(pt4.get("event_log_prewrite_written_count"))
        == _int(pt4.get("staged_order_count"))
        and pt4.get("paper_order_submission_allowed") is False
        and pt4.get("broker_post_allowed") is False
        and pt4.get("live_capital_enabled") is False
        and pt4.get("phase7_proof_credit_allowed") is False
        and pt4.get("forced_trades_allowed") is False
        and _int(pt4.get("broker_post_called_count")) == 0
        and _int(pt4.get("alpaca_post_called_count")) == 0
        and _int(pt4.get("unsafe_write_counter_total")) == 0
        and not validate_paperops_auto_approval_staged_order(pt4)
    )


def _blockers(
    *,
    settings: Settings,
    sources: dict[str, dict[str, Any]],
    endpoint: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if settings.mode != "paper":
        blockers.append("mode_not_paper")
    if settings.live_capital_enabled:
        blockers.append("live_capital_enabled")
    if not _pt0_ready(sources["pt0"]):
        blockers.append("pt0_paper_live_activation_not_ready")
    if not _pt2_ready(sources["pt2"]):
        blockers.append("pt2_paper_operational_mode_not_ready")
    if not _pt3_ready(sources["pt3"]):
        blockers.append("pt3_qualified_setup_production_not_ready")
    if not _pt4_ready(sources["pt4"]):
        blockers.append("pt4_staged_order_not_ready_for_submit")
    if endpoint.get("paper_endpoint_confirmed") is not True:
        blockers.append("alpaca_endpoint_not_paper")
    if endpoint.get("alpaca_api_key_configured") is not True:
        blockers.append("alpaca_api_key_missing")
    if endpoint.get("alpaca_api_secret_configured") is not True:
        blockers.append("alpaca_api_secret_missing")
    return sorted(set(blockers))


def _status(blockers: list[str]) -> str:
    if "mode_not_paper" in blockers:
        return "blocked_not_paper_mode"
    if "live_capital_enabled" in blockers:
        return "blocked_live_capital_enabled"
    if any(blocker.startswith("alpaca_") for blocker in blockers):
        return "blocked_alpaca_paper_endpoint_or_credentials"
    if blockers:
        return "blocked_pending_prerequisites"
    return "enabled_pending_explicit_submit"


def build_paperops_alpaca_paper_submit_enablement(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    sources = _source_snapshot(settings)
    endpoint = _endpoint_context(settings)
    blockers = _blockers(settings=settings, sources=sources, endpoint=endpoint)
    status = _status(blockers)
    enabled = status == "enabled_pending_explicit_submit"
    pt3 = sources["pt3"]
    pt4 = sources["pt4"]
    artifact = {
        "schema_version": PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_type": "paperops_alpaca_paper_submit_enablement",
        "artifact_id": "paperops:pt-5:alpaca-paper-submit-enable",
        "phase": "PaperOps",
        "stage": "PT-5",
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
        "paper_submit_runtime_enablement_enabled": enabled,
        "alpaca_paper_submit_enabled": settings.alpaca_paper_submit_enabled or enabled,
        "alpaca_paper_submit_effective": settings.alpaca_paper_submit_enabled or enabled,
        "settings_alpaca_paper_submit_enabled": settings.alpaca_paper_submit_enabled,
        "runtime_artifact_override_enabled": (
            enabled and not settings.alpaca_paper_submit_enabled
        ),
        "env_file_edited": False,
        "env_mutation_allowed": False,
        "paper_post_path_available": enabled,
        "explicit_submit_flag_required": True,
        "execute_post_requested": False,
        "pt0_activation_status": sources["pt0"].get("status", "missing"),
        "pt0_activation_approved": _pt0_ready(sources["pt0"]),
        "pt2_paper_operational_mode_status": sources["pt2"].get("status", "missing"),
        "pt2_paper_operational_mode_effective": _pt2_ready(sources["pt2"]),
        "pt3_status": pt3.get("status", "missing"),
        "pt3_path_ready": pt3.get("qualified_setup_production_path_ready") is True,
        "pt3_candidate_count": _int(pt3.get("production_candidate_count")),
        "pt3_qualified_setup_count": _int(pt3.get("qualified_setup_count")),
        "pt3_ready_to_stage_q7_order": pt3.get("ready_to_stage_q7_order") is True,
        "pt4_status": pt4.get("status", "missing"),
        "pt4_ready_for_paperops2_submit": (
            pt4.get("ready_for_paperops2_submit") is True
        ),
        "pt4_staged_order_count": _int(pt4.get("staged_order_count")),
        "pt4_event_log_prewrite_written_count": _int(
            pt4.get("event_log_prewrite_written_count")
        ),
        "endpoint_classification": endpoint["endpoint_classification"],
        "paper_endpoint_confirmed": endpoint["paper_endpoint_confirmed"],
        "alpaca_paper_flag": endpoint["alpaca_paper_flag"],
        "alpaca_api_key_configured": endpoint["alpaca_api_key_configured"],
        "alpaca_api_secret_configured": endpoint["alpaca_api_secret_configured"],
        "base_url_exposed": False,
        "authorization_header_exposed": False,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "live_endpoint_allowed": False,
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "unsafe_write_counter_total": 0,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "next_required_action": (
            "Run PaperOps-2 with --submit-paper-order when an explicit broker "
            "POST is desired."
            if enabled
            else "Resolve PT-5 blockers before using the Alpaca paper submit path."
        ),
        "boundary": PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_BOUNDARY,
        "validation_error_count": 0,
    }
    artifact["validation_errors"] = validate_paperops_alpaca_paper_submit_enablement(
        artifact
    )
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_alpaca_paper_submit_enablement(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    missing = sorted(set(PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_PUBLIC_FIELDS) - set(artifact))
    if missing:
        errors.append("paperops_alpaca_submit_enablement_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_SCHEMA_VERSION:
        errors.append("paperops_alpaca_submit_enablement_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_alpaca_paper_submit_enablement":
        errors.append("paperops_alpaca_submit_enablement_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-5":
        errors.append("paperops_alpaca_submit_enablement_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_alpaca_submit_enablement_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_alpaca_submit_enablement_mode_not_paper")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paperops_alpaca_submit_enablement_forbidden:live_capital_enabled")
    for key in (
        "env_file_edited",
        "env_mutation_allowed",
        "execute_post_requested",
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "manual_trade_level_override_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "base_url_exposed",
        "authorization_header_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_alpaca_submit_enablement_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_alpaca_submit_enablement_unsafe_counter_nonzero:{key}")
    if artifact.get("explicit_submit_flag_required") is not True:
        errors.append("paperops_alpaca_submit_enablement_submit_flag_not_required")
    if artifact.get("paper_submit_runtime_enablement_enabled") is True:
        if artifact.get("status") != "enabled_pending_explicit_submit":
            errors.append("paperops_alpaca_submit_enablement_status_invalid")
        if artifact.get("alpaca_paper_submit_effective") is not True:
            errors.append("paperops_alpaca_submit_enablement_effective_false")
        if artifact.get("paper_post_path_available") is not True:
            errors.append("paperops_alpaca_submit_enablement_path_unavailable")
        if artifact.get("paper_endpoint_confirmed") is not True:
            errors.append("paperops_alpaca_submit_enablement_endpoint_not_paper")
        if artifact.get("alpaca_api_key_configured") is not True:
            errors.append("paperops_alpaca_submit_enablement_key_missing")
        if artifact.get("alpaca_api_secret_configured") is not True:
            errors.append("paperops_alpaca_submit_enablement_secret_missing")
        if artifact.get("pt3_path_ready") is not True:
            errors.append("paperops_alpaca_submit_enablement_pt3_not_ready")
        if artifact.get("pt4_ready_for_paperops2_submit") is not True:
            errors.append("paperops_alpaca_submit_enablement_pt4_not_ready")
        if _int(artifact.get("pt4_staged_order_count")) < 1:
            errors.append("paperops_alpaca_submit_enablement_no_staged_order")
    else:
        if artifact.get("paper_post_path_available") is True:
            errors.append("paperops_alpaca_submit_enablement_path_available_while_disabled")
    if artifact.get("validation_error_count") not in {None, len(artifact.get("validation_errors", []))}:
        errors.append("paperops_alpaca_submit_enablement_validation_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "PT-5 records runtime Alpaca paper-submit enablement",
        "explicit submit flag",
        "cannot edit .env",
        "cannot call Alpaca",
        "cannot call live endpoints",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_alpaca_submit_enablement_boundary_weak")
            break
    return sorted(set(errors))


def write_paperops_alpaca_paper_submit_enablement(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = (
        paperops_alpaca_paper_submit_enablement_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_EVENT_TYPE,
            PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_COMPONENT,
            payload={
                "status": written["status"],
                "alpaca_paper_submit_effective": written[
                    "alpaca_paper_submit_effective"
                ],
                "runtime_artifact_override_enabled": written[
                    "runtime_artifact_override_enabled"
                ],
                "paper_post_path_available": written["paper_post_path_available"],
                "pt4_staged_order_count": written["pt4_staged_order_count"],
                "broker_post_called_count": written["broker_post_called_count"],
                "alpaca_post_called_count": written["alpaca_post_called_count"],
                "live_endpoint_called_count": written["live_endpoint_called_count"],
                "live_capital_enabled": written["live_capital_enabled"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_alpaca_paper_submit_enablement(
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
        "schema_version": PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "alpaca_paper_submit_effective": written.get("alpaca_paper_submit_effective"),
        "runtime_artifact_override_enabled": written.get(
            "runtime_artifact_override_enabled"
        ),
        "paper_post_path_available": written.get("paper_post_path_available"),
        "pt4_staged_order_count": written.get("pt4_staged_order_count"),
        "broker_post_called_count": written.get("broker_post_called_count"),
        "alpaca_post_called_count": written.get("alpaca_post_called_count"),
        "live_endpoint_called_count": written.get("live_endpoint_called_count"),
        "validation_error_count": len(written.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_alpaca_paper_submit_enablement_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_alpaca_paper_submit_enablement(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
            "artifact_type": "paperops_alpaca_paper_submit_enablement",
            "artifact_id": "paperops:pt-5:alpaca-paper-submit-enable",
            "phase": "PaperOps",
            "status": "not_run",
            "stage": "PT-5",
            "generated_at": None,
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "mode": "paper",
            "paper_submit_runtime_enablement_enabled": False,
            "alpaca_paper_submit_enabled": False,
            "alpaca_paper_submit_effective": False,
            "settings_alpaca_paper_submit_enabled": False,
            "runtime_artifact_override_enabled": False,
            "env_file_edited": False,
            "env_mutation_allowed": False,
            "paper_post_path_available": False,
            "explicit_submit_flag_required": True,
            "execute_post_requested": False,
            "pt3_status": "not_run",
            "pt3_path_ready": False,
            "pt3_qualified_setup_count": 0,
            "pt4_status": "not_run",
            "pt4_ready_for_paperops2_submit": False,
            "pt4_staged_order_count": 0,
            "endpoint_classification": "not_run",
            "paper_endpoint_confirmed": False,
            "alpaca_api_key_configured": False,
            "alpaca_api_secret_configured": False,
            "paper_order_submission_allowed": False,
            "broker_post_allowed": False,
            "alpaca_post_allowed": False,
            "broker_post_called_count": 0,
            "alpaca_post_called_count": 0,
            "live_endpoint_allowed": False,
            "live_endpoint_called_count": 0,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "forced_trades_allowed": False,
            "manual_trade_level_override_allowed": False,
            "secret_value_exposed": False,
            "raw_payload_exposed": False,
            "unsafe_write_counter_total": 0,
            "blockers": ["pt5_not_run"],
            "blocker_count": 1,
            "next_required_action": "Run PT-5 Alpaca paper-submit runtime enablement.",
            "validation_error_count": 0,
            "boundary": PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_BOUNDARY,
        }
    public = {
        key: artifact.get(key)
        for key in PAPEROPS_ALPACA_SUBMIT_ENABLEMENT_PUBLIC_FIELDS
        if key in artifact
    }
    public["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return public
