"""PaperOps-Q Q-CTRL paper consultation gate.

This module keeps Q-CTRL as a paper-mode advisory provider. It can only attempt
provider authentication when the explicit PaperOps-Q flag is enabled, Qadam is
in paper mode, live capital is disabled, the local SDK is importable, and the
Q-CTRL credential is configured. It never grants trade, risk, execution, paper
order, broker, or live-capital authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
import os
import re
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.quantum import QCTRL_SDK_MODULE_CANDIDATES, qctrl_readiness, quantum_oracle_summary
from orchestrator.secrets import secret_value


PAPEROPS_QCTRL_CONSULTATION_SCHEMA_VERSION = 1
PAPEROPS_QCTRL_RUNTIME_ARTIFACT = "paperops_qctrl_paper_consultation.json"
PAPEROPS_QCTRL_HISTORY = "paperops_qctrl_paper_consultation_history.jsonl"
PAPEROPS_QCTRL_EVENT_LOG = "paperops_qctrl_paper_consultation_events.jsonl"
PAPEROPS_QCTRL_EVENT_TYPE = "paperops_qctrl_paper_consultation_recorded"
PAPEROPS_QCTRL_COMPONENT = "paperops_qctrl_paper_consultation"

PAPEROPS_QCTRL_AUTHORITY_FALSE_FIELDS = (
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "prediction_market_write_allowed",
    "crypto_perps_write_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "hardware_submission_allowed",
    "hardware_scheduler_enabled",
    "secret_value_exposed",
    "raw_provider_response_persisted",
    "raw_response_exposed",
)

PAPEROPS_QCTRL_BOUNDARY = (
    "PaperOps-Q is a Q-CTRL paper-mode advisory gate. It may authenticate or "
    "probe Q-CTRL only when QADAM_QCTRL_PAPER_CONSULTATION_ENABLED=true, "
    "QADAM_MODE=paper, live capital is disabled, the SDK is importable, and the "
    "credential is configured. It cannot create trade candidates, approve risk, "
    "approve execution, create staged paper orders, call brokers, call live "
    "endpoints, submit hardware jobs, expose secrets, persist raw provider "
    "responses, or promote live capital. It cannot call brokers under any "
    "Q-CTRL consultation path."
)

PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"vcp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"sb_secret_[0-9A-Za-z_-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"pref_agent_[0-9A-Za-z_-]{12,}"),
    re.compile(r"[0-9]{6,}:[A-Za-z0-9_-]{20,}"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def paperops_qctrl_consultation_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_QCTRL_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_QCTRL_HISTORY,
        runtime / PAPEROPS_QCTRL_EVENT_LOG,
    )


def read_latest_paperops_qctrl_consultation(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_qctrl_consultation_paths(settings)
    if not output_path.exists():
        return {}
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _contains_secret_shape(value: object) -> bool:
    text = json.dumps(value, sort_keys=True, default=str)
    return any(pattern.search(text) for pattern in PROHIBITED_VALUE_PATTERNS)


def _fingerprint(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _select_sdk_module(readiness: dict[str, Any]) -> str | None:
    importable = readiness.get("importable_modules")
    if not isinstance(importable, list):
        return None
    for module in QCTRL_SDK_MODULE_CANDIDATES:
        if module in importable:
            return module
    return str(importable[0]) if importable else None


def _paper_settings(settings: Settings, **overrides: Any) -> Settings:
    return replace(settings, **overrides)


def _provider_auth_probe(
    *,
    module_name: str,
    settings: Settings,
) -> dict[str, Any]:
    api_key = secret_value("QCTRL_API_KEY", settings)
    if not api_key:
        return {
            "provider_call_attempted": False,
            "provider_call_succeeded": False,
            "provider_call_count": 0,
            "auth_status": "missing_credential",
            "provider_failure_class": None,
        }

    os.environ.setdefault("FIRE_OPAL_CLIENT_DISABLE_TRACKING", "true")
    try:
        workflow_utils = importlib.import_module("qctrlworkflowclient.utils")
        installed_version = getattr(workflow_utils, "get_installed_version", lambda _: None)
        workflow_utils.get_latest_pypi_version = (  # type: ignore[attr-defined]
            lambda package: installed_version(package) or "0"
        )
    except Exception:
        pass

    module = importlib.import_module(module_name)
    auth = getattr(module, "authenticate_qctrl_account", None)
    if not callable(auth):
        return {
            "provider_call_attempted": False,
            "provider_call_succeeded": False,
            "provider_call_count": 0,
            "auth_status": "auth_function_missing",
            "provider_failure_class": None,
        }

    try:
        auth(api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - persistence must stay sanitized.
        return {
            "provider_call_attempted": True,
            "provider_call_succeeded": False,
            "provider_call_count": 1,
            "auth_status": "provider_call_failed_sanitized",
            "provider_failure_class": type(exc).__name__,
        }

    return {
        "provider_call_attempted": True,
        "provider_call_succeeded": True,
        "provider_call_count": 1,
        "auth_status": "authenticated",
        "provider_failure_class": None,
    }


def build_paperops_qctrl_consultation(
    settings: Settings | None = None,
    *,
    allow_provider_call: bool | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    readiness = qctrl_readiness(settings)
    oracle = quantum_oracle_summary(settings)
    sdk_module = _select_sdk_module(readiness)
    provider_preconditions = {
        "mode_is_paper": settings.mode == "paper",
        "live_capital_disabled": settings.live_capital_enabled is False,
        "paper_consultation_flag_enabled": settings.qctrl_paper_consultation_enabled,
        "credential_configured": readiness.get("credential_configured") is True,
        "sdk_package_importable": readiness.get("sdk_package_importable") is True,
        "sdk_module_selected": bool(sdk_module),
    }
    provider_call_allowed = all(provider_preconditions.values())
    should_attempt_provider = provider_call_allowed if allow_provider_call is None else (
        provider_call_allowed and allow_provider_call
    )

    auth_probe = {
        "provider_call_attempted": False,
        "provider_call_succeeded": False,
        "provider_call_count": 0,
        "auth_status": "not_attempted",
        "provider_failure_class": None,
    }
    if should_attempt_provider and sdk_module:
        auth_probe = _provider_auth_probe(module_name=sdk_module, settings=settings)

    if settings.mode != "paper":
        status = "blocked_not_paper_mode"
    elif settings.live_capital_enabled:
        status = "blocked_live_capital_enabled"
    elif not settings.qctrl_paper_consultation_enabled:
        status = "disabled_pending_enablement"
        auth_probe["auth_status"] = "not_attempted_disabled"
    elif readiness.get("credential_configured") is not True:
        status = "blocked_missing_qctrl_credential"
        auth_probe["auth_status"] = "not_attempted_missing_credential"
    elif readiness.get("sdk_package_importable") is not True:
        status = "blocked_missing_qctrl_sdk"
        auth_probe["auth_status"] = "not_attempted_missing_sdk"
    elif auth_probe["provider_call_succeeded"]:
        status = "consultation_recorded"
    else:
        status = str(auth_probe["auth_status"])

    paper_request_metadata = {
        "request_type": "qctrl_paper_advisory_auth_status_probe",
        "source": "head_of_quant_latest_shadow_oracle",
        "latest_backend": oracle.get("latest_backend", "classical_fallback"),
        "latest_recommendation": oracle.get("latest_recommendation", "not_run"),
        "latest_output_route_type": oracle.get("latest_output_route_type", "not_run"),
        "latest_input_fingerprint": oracle.get("latest_input_fingerprint"),
        "result_count": oracle.get("result_count", 0),
        "hardware_submitted_count": oracle.get("hardware_submitted_count", 0),
    }
    head_of_quant_note = {
        "status": status,
        "note_type": "qctrl_paper_consultation_note",
        "attached_to_evidence_packet": True,
        "summary": (
            "Q-CTRL paper consultation is recorded as a bounded Head of Quant "
            "annotation."
            if status == "consultation_recorded"
            else "Q-CTRL paper consultation gate exists, but no provider advisory call is recorded yet."
        ),
        "qctrl_role": "paper_advisory_shadow_annotation_only",
        "latest_oracle_backend": paper_request_metadata["latest_backend"],
        "latest_oracle_recommendation": paper_request_metadata["latest_recommendation"],
        "counts_as_execution_truth": False,
        "counts_as_proof": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_post_allowed": False,
    }
    artifact = {
        "schema_version": PAPEROPS_QCTRL_CONSULTATION_SCHEMA_VERSION,
        "artifact_type": "paperops_qctrl_paper_consultation",
        "artifact_id": "paperops:qctrl:paper-consultation:latest",
        "phase": "PaperOps",
        "stage": "PaperOps-Q",
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
        "paper_operational_enabled": settings.paper_operational_enabled,
        "qctrl_paper_consultation_enabled": settings.qctrl_paper_consultation_enabled,
        "quantum_paper_parity_required": settings.quantum_paper_parity_required,
        "live_capital_enabled": settings.live_capital_enabled,
        "qctrl_readiness_status": readiness.get("status"),
        "qctrl_credential_configured": readiness.get("credential_configured") is True,
        "qctrl_sdk_package_importable": readiness.get("sdk_package_importable") is True,
        "qctrl_sdk_module_candidates": list(QCTRL_SDK_MODULE_CANDIDATES),
        "qctrl_importable_modules": readiness.get("importable_modules", []),
        "qctrl_sdk_module_selected": sdk_module,
        "provider_preconditions": provider_preconditions,
        "provider_call_allowed": provider_call_allowed,
        "provider_call_attempted": auth_probe["provider_call_attempted"],
        "provider_call_succeeded": auth_probe["provider_call_succeeded"],
        "provider_call_recorded": auth_probe["provider_call_attempted"],
        "provider_call_count": auth_probe["provider_call_count"],
        "qctrl_auth_status": auth_probe["auth_status"],
        "provider_failure_class": auth_probe["provider_failure_class"],
        "provider_failure_message_persisted": False,
        "sdk_import_network_version_check_suppressed": True,
        "sdk_analytics_tracking_disabled": True,
        "paper_request_metadata": paper_request_metadata,
        "paper_request_fingerprint": _fingerprint(paper_request_metadata),
        "head_of_quant_note": head_of_quant_note,
        "strategy_lead_attachment_ready": True,
        "signal_integrity_attachment_ready": True,
        "risk_agent_attachment_ready": True,
        "execution_policy_attachment_ready": True,
        "trade_candidate_creation_allowed": False,
        "risk_approval_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "live_endpoint_allowed": False,
        "hardware_submission_allowed": False,
        "hardware_scheduler_enabled": False,
        "optimization_job_submitted": False,
        "secret_value_exposed": False,
        "raw_provider_response_persisted": False,
        "raw_response_exposed": False,
        "boundary": PAPEROPS_QCTRL_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_qctrl_consultation(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_qctrl_consultation(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_type",
        "boundary",
        "event_log_required",
        "event_log_written",
        "head_of_quant_note",
        "mode",
        "paper_request_fingerprint",
        "paper_request_metadata",
        "phase",
        "provider_call_allowed",
        "provider_call_attempted",
        "provider_call_count",
        "provider_call_recorded",
        "provider_call_succeeded",
        "provider_failure_message_persisted",
        "public_safe",
        "qctrl_auth_status",
        "qctrl_credential_configured",
        "qctrl_paper_consultation_enabled",
        "qctrl_sdk_package_importable",
        "raw_provider_response_persisted",
        "recorded",
        "schema_version",
        "stage",
        "status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_qctrl_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_QCTRL_CONSULTATION_SCHEMA_VERSION:
        errors.append("paperops_qctrl_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_qctrl_paper_consultation":
        errors.append("paperops_qctrl_artifact_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PaperOps-Q":
        errors.append("paperops_qctrl_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paperops_qctrl_mode_not_paper")
    for key in PAPEROPS_QCTRL_AUTHORITY_FALSE_FIELDS:
        if artifact.get(key) is not False:
            errors.append(f"paperops_qctrl_forbidden:{key}")
    for key in ("broker_post_called_count", "alpaca_post_called_count"):
        if int(artifact.get(key, 0) or 0) != 0:
            errors.append(f"paperops_qctrl_unsafe_counter_nonzero:{key}")
    if artifact.get("provider_failure_message_persisted") is not False:
        errors.append("paperops_qctrl_provider_failure_message_persisted")
    if artifact.get("provider_call_succeeded") is True and artifact.get(
        "provider_call_recorded"
    ) is not True:
        errors.append("paperops_qctrl_success_without_recorded_call")
    if artifact.get("provider_call_recorded") is True and int(
        artifact.get("provider_call_count", 0) or 0
    ) < 1:
        errors.append("paperops_qctrl_recorded_without_provider_call_count")
    if artifact.get("provider_call_succeeded") is True and int(
        artifact.get("provider_call_count", 0) or 0
    ) < 1:
        errors.append("paperops_qctrl_success_without_provider_call_count")
    if artifact.get("provider_call_attempted") is True and artifact.get(
        "provider_call_allowed"
    ) is not True:
        errors.append("paperops_qctrl_attempt_without_allowance")
    if artifact.get("qctrl_paper_consultation_enabled") is not True and int(
        artifact.get("provider_call_count", 0) or 0
    ) != 0:
        errors.append("paperops_qctrl_provider_call_without_flag")
    note = artifact.get("head_of_quant_note", {})
    if not isinstance(note, dict):
        errors.append("paperops_qctrl_head_of_quant_note_missing")
        note = {}
    if note.get("attached_to_evidence_packet") is not True:
        errors.append("paperops_qctrl_head_note_not_attached")
    for key in (
        "counts_as_execution_truth",
        "counts_as_proof",
        "execution_allowed",
        "paper_order_allowed",
        "broker_post_allowed",
    ):
        if note.get(key) is not False:
            errors.append(f"paperops_qctrl_head_note_forbidden:{key}")
    metadata = artifact.get("paper_request_metadata", {})
    if not isinstance(metadata, dict):
        errors.append("paperops_qctrl_request_metadata_invalid")
    elif artifact.get("paper_request_fingerprint") != _fingerprint(metadata):
        errors.append("paperops_qctrl_request_fingerprint_mismatch")
    if artifact.get("event_log_required") is not True:
        errors.append("paperops_qctrl_event_log_not_required")
    if artifact.get("recorded") is True and artifact.get("event_log_written") is not True:
        errors.append("paperops_qctrl_event_log_missing")
    boundary = str(artifact.get("boundary") or "")
    if "QADAM_QCTRL_PAPER_CONSULTATION_ENABLED=true" not in boundary:
        errors.append("paperops_qctrl_boundary_missing_explicit_flag")
    if "cannot create trade candidates" not in boundary or "cannot call brokers" not in boundary:
        errors.append("paperops_qctrl_boundary_weak")
    if _contains_secret_shape(artifact):
        errors.append("paperops_qctrl_secret_shape_exposed")
    return errors


def write_paperops_qctrl_consultation(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
    event_log_path: Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, default_event_path = paperops_qctrl_consultation_paths(settings)
    event_path = event_log_path or default_event_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    written["runtime_artifact_path"] = str(output_path)
    written["history_log_path"] = str(history_path)
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_QCTRL_EVENT_TYPE,
            PAPEROPS_QCTRL_COMPONENT,
            payload={
                "status": written["status"],
                "provider_call_count": written["provider_call_count"],
                "provider_call_succeeded": written["provider_call_succeeded"],
                "execution_allowed": written["execution_allowed"],
                "paper_order_allowed": written["paper_order_allowed"],
                "broker_post_allowed": written["broker_post_allowed"],
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_paperops_qctrl_consultation(written)
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(json.dumps(written, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(written, sort_keys=True) + "\n")
    return output_path, history_path, event_path, written


def paperops_qctrl_public_status(settings: Settings | None = None) -> dict[str, Any]:
    artifact = read_latest_paperops_qctrl_consultation(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_QCTRL_CONSULTATION_SCHEMA_VERSION,
            "status": "not_run",
            "stage": "PaperOps-Q",
            "provider_call_count": 0,
            "provider_call_succeeded": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_post_allowed": False,
            "boundary": PAPEROPS_QCTRL_BOUNDARY,
        }
    return {
        "schema_version": artifact.get("schema_version"),
        "status": artifact.get("status"),
        "stage": artifact.get("stage"),
        "qctrl_paper_consultation_enabled": artifact.get("qctrl_paper_consultation_enabled"),
        "qctrl_readiness_status": artifact.get("qctrl_readiness_status"),
        "qctrl_credential_configured": artifact.get("qctrl_credential_configured"),
        "qctrl_sdk_package_importable": artifact.get("qctrl_sdk_package_importable"),
        "qctrl_sdk_module_selected": artifact.get("qctrl_sdk_module_selected"),
        "provider_call_allowed": artifact.get("provider_call_allowed"),
        "provider_call_attempted": artifact.get("provider_call_attempted"),
        "provider_call_succeeded": artifact.get("provider_call_succeeded"),
        "provider_call_count": artifact.get("provider_call_count", 0),
        "head_of_quant_note_status": (artifact.get("head_of_quant_note") or {}).get("status"),
        "execution_allowed": artifact.get("execution_allowed"),
        "paper_order_allowed": artifact.get("paper_order_allowed"),
        "broker_post_allowed": artifact.get("broker_post_allowed"),
        "live_capital_enabled": artifact.get("live_capital_enabled"),
        "secret_value_exposed": artifact.get("secret_value_exposed"),
        "raw_response_exposed": artifact.get("raw_response_exposed"),
        "boundary": artifact.get("boundary", PAPEROPS_QCTRL_BOUNDARY),
    }


def paperops_qctrl_shadow_annotation_context(settings: Settings | None = None) -> dict[str, Any]:
    artifact = read_latest_paperops_qctrl_consultation(settings)
    note = artifact.get("head_of_quant_note", {}) if isinstance(artifact, dict) else {}
    return {
        "present": bool(artifact),
        "role": "quantum_shadow_annotation_only",
        "counts_as_execution_truth": False,
        "counts_as_proof": False,
        "status": artifact.get("status", "not_run") if isinstance(artifact, dict) else "not_run",
        "provider_call_count": int(artifact.get("provider_call_count", 0) or 0)
        if isinstance(artifact, dict)
        else 0,
        "provider_call_succeeded": artifact.get("provider_call_succeeded") is True
        if isinstance(artifact, dict)
        else False,
        "head_of_quant_note_status": note.get("status") if isinstance(note, dict) else None,
        "head_of_quant_summary": note.get("summary") if isinstance(note, dict) else None,
    }


def build_disabled_probe_settings(settings: Settings | None = None) -> Settings:
    settings = settings or Settings.from_env()
    return _paper_settings(settings, qctrl_paper_consultation_enabled=False)
