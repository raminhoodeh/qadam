"""PT-1 Q-CTRL product access and paper consultation gate.

PT-1 records whether the guarded PaperOps-Q provider path can actually
authenticate for paper-mode consultation. It is advisory-only: no trade, risk,
execution, order, broker, live endpoint, or live-capital authority is granted.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paper_live_activation import read_latest_paper_live_activation
from orchestrator.paperops_qctrl_consultation import (
    build_paperops_qctrl_consultation,
    read_latest_paperops_qctrl_consultation,
    write_paperops_qctrl_consultation,
)
from orchestrator.quantum import qctrl_readiness


PAPER_LIVE_QCTRL_PRODUCT_ACCESS_SCHEMA_VERSION = 1
PAPER_LIVE_QCTRL_PRODUCT_ACCESS_RUNTIME_ARTIFACT = (
    "paper_live_qctrl_product_access.json"
)
PAPER_LIVE_QCTRL_PRODUCT_ACCESS_HISTORY = "paper_live_qctrl_product_access_history.jsonl"
PAPER_LIVE_QCTRL_PRODUCT_ACCESS_EVENT_LOG = "paper_live_qctrl_product_access_events.jsonl"
PAPER_LIVE_QCTRL_PRODUCT_ACCESS_EVENT_TYPE = (
    "paper_live_qctrl_product_access_recorded"
)
PAPER_LIVE_QCTRL_PRODUCT_ACCESS_COMPONENT = "paper_live_qctrl_product_access"

PAPER_LIVE_QCTRL_PRODUCT_ACCESS_BOUNDARY = (
    "PT-1 verifies Q-CTRL product access only through the guarded PaperOps-Q "
    "paper consultation path. It may attempt one explicit paper-mode provider "
    "authentication/consultation probe after PT-0 approval, with Qadam in paper "
    "mode and live capital disabled. It cannot create trade candidates, approve "
    "risk, approve execution, or create paper orders. It cannot call brokers, "
    "call live endpoints, submit hardware jobs, expose secrets, persist raw "
    "provider responses, or force trades. It cannot grant Phase 7 proof credit."
)

PAPER_LIVE_QCTRL_PRODUCT_ACCESS_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "mode",
    "pt0_activation_status",
    "pt0_activation_approved",
    "pt0_system_approval_logged",
    "product_access_state",
    "product_access_verified",
    "paper_consultation_ready",
    "paper_consultation_recorded",
    "qctrl_paper_consultation_enabled_for_probe",
    "qctrl_readiness_status",
    "qctrl_credential_configured",
    "qctrl_fire_opal_product_required",
    "qctrl_organization_slug_configured",
    "qctrl_organization_config_applied",
    "qctrl_sdk_package_importable",
    "qctrl_sdk_module_selected",
    "provider_call_allowed",
    "provider_call_attempted",
    "provider_call_succeeded",
    "provider_call_count",
    "qctrl_auth_status",
    "provider_failure_category",
    "product_access_blocker",
    "paperops_qctrl_status",
    "head_of_quant_note_status",
    "strategy_lead_attachment_ready",
    "signal_integrity_attachment_ready",
    "risk_agent_attachment_ready",
    "execution_policy_attachment_ready",
    "execution_allowed",
    "paper_order_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_allowed",
    "live_endpoint_called_count",
    "live_capital_enabled",
    "hardware_submission_allowed",
    "phase7_proof_credit_allowed",
    "forced_trades_allowed",
    "secret_value_exposed",
    "raw_response_exposed",
    "raw_provider_response_persisted",
    "provider_failure_message_persisted",
    "next_required_action",
    "boundary",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def paper_live_qctrl_product_access_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_LIVE_QCTRL_PRODUCT_ACCESS_RUNTIME_ARTIFACT,
        runtime / PAPER_LIVE_QCTRL_PRODUCT_ACCESS_HISTORY,
        runtime / PAPER_LIVE_QCTRL_PRODUCT_ACCESS_EVENT_LOG,
    )


def read_latest_paper_live_qctrl_product_access(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paper_live_qctrl_product_access_paths(settings)
    return _read_json(output_path)


def _is_verified_product_access(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("product_access_verified") is True
        and artifact.get("paper_consultation_ready") is True
        and artifact.get("provider_call_succeeded") is True
    )


def _latest_verified_product_access_from_history(settings: Settings) -> dict[str, Any]:
    _, history_path, _ = paper_live_qctrl_product_access_paths(settings)
    if not history_path.exists():
        return {}

    latest: dict[str, Any] = {}
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and _is_verified_product_access(candidate):
            latest = candidate
    return latest


def _is_transient_provider_failure(qctrl_artifact: dict[str, Any]) -> bool:
    return (
        qctrl_artifact.get("provider_call_attempted") is True
        and qctrl_artifact.get("provider_call_succeeded") is not True
        and qctrl_artifact.get("provider_failure_category") == "provider_network_error"
    )


def _activation_ready(activation: dict[str, Any]) -> bool:
    return (
        activation.get("status") == "approved_pending_later_enablement"
        and activation.get("approval_state") == "approved"
        and activation.get("approval_logged") is True
        and activation.get("paper_live_activation_approved") is True
        and activation.get("paper_trading_system_approval_logged") is True
        and activation.get("paper_order_submission_allowed") is False
        and activation.get("live_capital_enabled") is False
    )


def _classify_product_access(
    *,
    settings: Settings,
    activation_ready: bool,
    readiness: dict[str, Any],
    qctrl_artifact: dict[str, Any],
) -> tuple[str, str, str, str]:
    if not activation_ready:
        return (
            "blocked_missing_pt0_activation",
            "not_checked",
            "pt0_activation_not_approved",
            "Run PT-0 paper-live activation charter.",
        )
    if settings.mode != "paper":
        return (
            "blocked_not_paper_mode",
            "not_checked",
            "mode_not_paper",
            "Restore QADAM_MODE=paper before Q-CTRL paper consultation.",
        )
    if settings.live_capital_enabled:
        return (
            "blocked_live_capital_enabled",
            "not_checked",
            "live_capital_enabled",
            "Disable live capital before Q-CTRL paper consultation.",
        )
    if readiness.get("credential_configured") is not True:
        return (
            "blocked_missing_qctrl_credential",
            "not_checked",
            "missing_qctrl_credential",
            "Configure QCTRL_API_KEY without exposing the secret value.",
        )
    if readiness.get("sdk_package_importable") is not True:
        return (
            "blocked_missing_qctrl_sdk",
            "not_checked",
            "missing_qctrl_sdk",
            "Install the Q-CTRL paper SDK package before consultation.",
        )
    if qctrl_artifact.get("provider_call_succeeded") is True:
        return (
            "qctrl_paper_consultation_ready",
            "verified",
            "none",
            "Q-CTRL product access is verified; proceed to PT-2 when other gates allow.",
        )
    if qctrl_artifact.get("provider_call_attempted") is True:
        failure_category = str(qctrl_artifact.get("provider_failure_category") or "")
        if failure_category == "fire_opal_organization_slug_required":
            return (
                "blocked_qctrl_product_access_or_subscription",
                "blocked_missing_fire_opal_organization_slug",
                "qctrl_fire_opal_organization_slug_required",
                "Set QCTRL_ORGANIZATION_SLUG for the Fire Opal organization, then rerun PT-1.",
            )
        if failure_category == "fire_opal_organization_slug_invalid_or_no_product_access":
            return (
                "blocked_qctrl_product_access_or_subscription",
                "blocked_fire_opal_organization_access",
                "qctrl_fire_opal_organization_slug_invalid_or_no_product_access",
                "Verify the configured QCTRL_ORGANIZATION_SLUG belongs to an organization with active Fire Opal access, then rerun PT-1.",
            )
        if failure_category == "fire_opal_subscription_not_active":
            return (
                "blocked_qctrl_product_access_or_subscription",
                "blocked_external_product_access",
                "qctrl_fire_opal_subscription_not_active",
                "Activate Fire Opal access for the Q-CTRL organization used by Qadam, then rerun PT-1.",
            )
        if failure_category == "provider_network_error":
            return (
                "blocked_qctrl_product_access_or_subscription",
                "blocked_provider_network",
                "qctrl_provider_network_unavailable",
                "Allow the Q-CTRL provider probe to reach Fire Opal, then rerun PT-1.",
            )
        return (
            "blocked_qctrl_product_access_or_subscription",
            "blocked_external_product_access",
            "qctrl_product_access_or_subscription_not_active",
            "Resolve Q-CTRL Fire Opal organization/product access, then rerun PT-1.",
        )
    return (
        "ready_for_explicit_qctrl_product_access_probe",
        "not_checked",
        "provider_probe_not_attempted",
        "Run PT-1 with the explicit provider-consultation probe.",
    )


def _qctrl_artifact_from_previous_pt1(previous: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": previous.get("paperops_qctrl_status", previous.get("status")),
        "qctrl_paper_consultation_enabled": previous.get(
            "qctrl_paper_consultation_enabled_for_probe"
        ),
        "qctrl_sdk_module_selected": previous.get("qctrl_sdk_module_selected"),
        "provider_call_allowed": previous.get("provider_call_allowed"),
        "provider_call_attempted": previous.get("provider_call_attempted"),
        "provider_call_succeeded": previous.get("provider_call_succeeded"),
        "provider_call_count": previous.get("provider_call_count"),
        "qctrl_auth_status": previous.get("qctrl_auth_status"),
        "provider_failure_category": previous.get("provider_failure_category"),
        "qctrl_fire_opal_product_required": previous.get(
            "qctrl_fire_opal_product_required"
        ),
        "qctrl_organization_slug_configured": previous.get(
            "qctrl_organization_slug_configured"
        ),
        "qctrl_organization_config_applied": previous.get(
            "qctrl_organization_config_applied"
        ),
        "validation_errors": [],
        "head_of_quant_note": {
            "status": previous.get("head_of_quant_note_status"),
            "attached_to_evidence_packet": previous.get("head_of_quant_note_attached")
            is True,
        },
        "strategy_lead_attachment_ready": previous.get(
            "strategy_lead_attachment_ready"
        ),
        "signal_integrity_attachment_ready": previous.get(
            "signal_integrity_attachment_ready"
        ),
        "risk_agent_attachment_ready": previous.get("risk_agent_attachment_ready"),
        "execution_policy_attachment_ready": previous.get(
            "execution_policy_attachment_ready"
        ),
    }


def build_paper_live_qctrl_product_access(
    settings: Settings | None = None,
    *,
    attempt_provider_consultation: bool = False,
    qctrl_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    activation = read_latest_paper_live_activation(settings)
    activation_ready = _activation_ready(activation)
    readiness = qctrl_readiness(settings)
    previous_pt1 = read_latest_paper_live_qctrl_product_access(settings)
    latest_verified_pt1 = (
        previous_pt1
        if _is_verified_product_access(previous_pt1)
        else _latest_verified_product_access_from_history(settings)
    )
    if qctrl_artifact is None:
        if attempt_provider_consultation and activation_ready:
            probe_settings = replace(settings, qctrl_paper_consultation_enabled=True)
            probe_artifact = build_paperops_qctrl_consultation(
                probe_settings,
                allow_provider_call=True,
            )
            _, _, _, qctrl_artifact = write_paperops_qctrl_consultation(
                probe_artifact,
                probe_settings,
            )
        else:
            qctrl_artifact = read_latest_paperops_qctrl_consultation(settings)
            if (
                qctrl_artifact.get("provider_call_attempted") is not True
                and previous_pt1.get("provider_call_attempted") is True
            ):
                qctrl_artifact = _qctrl_artifact_from_previous_pt1(previous_pt1)
            elif latest_verified_pt1 and _is_transient_provider_failure(qctrl_artifact):
                qctrl_artifact = _qctrl_artifact_from_previous_pt1(latest_verified_pt1)
                qctrl_artifact["latest_provider_probe_status"] = "provider_call_failed_sanitized"
                qctrl_artifact["latest_provider_probe_failure_category"] = (
                    "provider_network_error"
                )

    status, product_state, blocker, next_action = _classify_product_access(
        settings=settings,
        activation_ready=activation_ready,
        readiness=readiness,
        qctrl_artifact=qctrl_artifact,
    )
    note = qctrl_artifact.get("head_of_quant_note", {})
    if not isinstance(note, dict):
        note = {}
    artifact = {
        "schema_version": PAPER_LIVE_QCTRL_PRODUCT_ACCESS_SCHEMA_VERSION,
        "artifact_type": "paper_live_qctrl_product_access",
        "artifact_id": "paperops:pt-1:qctrl-product-access",
        "phase": "PaperOps",
        "stage": "PT-1",
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
        "pt0_activation_status": activation.get("status", "missing"),
        "pt0_activation_approved": activation.get("paper_live_activation_approved")
        is True,
        "pt0_system_approval_logged": activation.get(
            "paper_trading_system_approval_logged"
        )
        is True,
        "product_access_state": product_state,
        "product_access_verified": qctrl_artifact.get("provider_call_succeeded")
        is True,
        "paper_consultation_ready": status == "qctrl_paper_consultation_ready",
        "paper_consultation_recorded": qctrl_artifact.get("status")
        == "consultation_recorded",
        "qctrl_paper_consultation_enabled_for_probe": qctrl_artifact.get(
            "qctrl_paper_consultation_enabled"
        )
        is True,
        "qctrl_readiness_status": readiness.get("status"),
        "qctrl_credential_configured": readiness.get("credential_configured")
        is True,
        "qctrl_fire_opal_product_required": qctrl_artifact.get(
            "qctrl_fire_opal_product_required"
        )
        is True,
        "qctrl_organization_slug_configured": qctrl_artifact.get(
            "qctrl_organization_slug_configured"
        )
        is True,
        "qctrl_organization_config_applied": qctrl_artifact.get(
            "qctrl_organization_config_applied"
        )
        is True,
        "qctrl_sdk_package_importable": readiness.get("sdk_package_importable")
        is True,
        "qctrl_sdk_module_selected": qctrl_artifact.get("qctrl_sdk_module_selected"),
        "provider_call_allowed": qctrl_artifact.get("provider_call_allowed") is True,
        "provider_call_attempted": qctrl_artifact.get("provider_call_attempted")
        is True,
        "provider_call_succeeded": qctrl_artifact.get("provider_call_succeeded")
        is True,
        "provider_call_count": _int(qctrl_artifact.get("provider_call_count")),
        "qctrl_auth_status": qctrl_artifact.get("qctrl_auth_status", "not_run"),
        "provider_failure_category": qctrl_artifact.get("provider_failure_category"),
        "product_access_blocker": blocker,
        "paperops_qctrl_status": qctrl_artifact.get("status", "not_run"),
        "paperops_qctrl_validation_error_count": len(
            qctrl_artifact.get("validation_errors", []) or []
        ),
        "head_of_quant_note_status": note.get("status"),
        "head_of_quant_note_attached": note.get("attached_to_evidence_packet")
        is True,
        "strategy_lead_attachment_ready": qctrl_artifact.get(
            "strategy_lead_attachment_ready"
        )
        is True,
        "signal_integrity_attachment_ready": qctrl_artifact.get(
            "signal_integrity_attachment_ready"
        )
        is True,
        "risk_agent_attachment_ready": qctrl_artifact.get(
            "risk_agent_attachment_ready"
        )
        is True,
        "execution_policy_attachment_ready": qctrl_artifact.get(
            "execution_policy_attachment_ready"
        )
        is True,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "live_endpoint_allowed": False,
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "hardware_submission_allowed": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "secret_value_exposed": False,
        "raw_response_exposed": False,
        "raw_provider_response_persisted": False,
        "provider_failure_message_persisted": False,
        "next_required_action": next_action,
        "boundary": PAPER_LIVE_QCTRL_PRODUCT_ACCESS_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paper_live_qctrl_product_access(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paper_live_qctrl_product_access(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PAPER_LIVE_QCTRL_PRODUCT_ACCESS_PUBLIC_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
        "head_of_quant_note_attached",
        "paperops_qctrl_validation_error_count",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paper_live_qctrl_product_access_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPER_LIVE_QCTRL_PRODUCT_ACCESS_SCHEMA_VERSION:
        errors.append("paper_live_qctrl_product_access_schema_mismatch")
    if artifact.get("artifact_type") != "paper_live_qctrl_product_access":
        errors.append("paper_live_qctrl_product_access_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-1":
        errors.append("paper_live_qctrl_product_access_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paper_live_qctrl_product_access_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paper_live_qctrl_product_access_mode_not_paper")
    if artifact.get("pt0_activation_approved") is not True:
        errors.append("paper_live_qctrl_product_access_pt0_not_approved")
    if artifact.get("pt0_system_approval_logged") is not True:
        errors.append("paper_live_qctrl_product_access_pt0_not_logged")
    if artifact.get("qctrl_credential_configured") is not True:
        errors.append("paper_live_qctrl_product_access_credential_missing")
    if artifact.get("qctrl_fire_opal_product_required") is not True:
        errors.append("paper_live_qctrl_product_access_fire_opal_not_required")
    if (
        artifact.get("qctrl_sdk_package_importable") is not True
        and artifact.get("status") != "blocked_missing_qctrl_sdk"
    ):
        errors.append("paper_live_qctrl_product_access_sdk_missing")
    if (
        artifact.get("qctrl_organization_config_applied") is True
        and artifact.get("qctrl_organization_slug_configured") is not True
    ):
        errors.append("paper_live_qctrl_product_access_org_config_applied_without_slug")
    allowed_statuses = {
        "ready_for_explicit_qctrl_product_access_probe",
        "blocked_qctrl_product_access_or_subscription",
        "qctrl_paper_consultation_ready",
        "blocked_missing_pt0_activation",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "blocked_missing_qctrl_credential",
        "blocked_missing_qctrl_sdk",
    }
    if artifact.get("status") not in allowed_statuses:
        errors.append("paper_live_qctrl_product_access_status_invalid")
    if artifact.get("provider_call_succeeded") is True:
        if artifact.get("product_access_verified") is not True:
            errors.append("paper_live_qctrl_product_access_success_not_verified")
        if artifact.get("paper_consultation_ready") is not True:
            errors.append("paper_live_qctrl_product_access_success_not_ready")
        if _int(artifact.get("provider_call_count")) < 1:
            errors.append("paper_live_qctrl_product_access_success_without_call_count")
    if artifact.get("product_access_verified") is True and artifact.get(
        "provider_call_succeeded"
    ) is not True:
        errors.append("paper_live_qctrl_product_access_verified_without_success")
    if artifact.get("provider_call_attempted") is True:
        if artifact.get("qctrl_paper_consultation_enabled_for_probe") is not True:
            errors.append("paper_live_qctrl_product_access_attempt_without_probe_flag")
        if artifact.get("provider_call_allowed") is not True:
            errors.append("paper_live_qctrl_product_access_attempt_without_allowance")
        if _int(artifact.get("provider_call_count")) < 1:
            errors.append("paper_live_qctrl_product_access_attempt_without_count")
    if (
        artifact.get("status") == "blocked_qctrl_product_access_or_subscription"
        and artifact.get("provider_call_attempted") is not True
    ):
        errors.append("paper_live_qctrl_product_access_blocked_without_attempt")
    if _int(artifact.get("paperops_qctrl_validation_error_count")) != 0:
        errors.append("paper_live_qctrl_product_access_paperops_qctrl_invalid")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "hardware_submission_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "secret_value_exposed",
        "raw_response_exposed",
        "raw_provider_response_persisted",
        "provider_failure_message_persisted",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paper_live_qctrl_product_access_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paper_live_qctrl_product_access_unsafe_counter_nonzero:{key}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "guarded PaperOps-Q",
        "after PT-0 approval",
        "cannot create trade candidates",
        "cannot call brokers",
        "cannot grant Phase 7 proof credit",
    ):
        if phrase not in boundary:
            errors.append("paper_live_qctrl_product_access_boundary_weak")
            break
    if artifact.get("recorded") is True and artifact.get("event_log_written") is not True:
        errors.append("paper_live_qctrl_product_access_event_log_missing")
    if artifact.get("event_log_written") is True:
        if _int(artifact.get("event_log_event_count")) != 1:
            errors.append("paper_live_qctrl_product_access_event_count_mismatch")
        if not artifact.get("event_log_correlation_id"):
            errors.append("paper_live_qctrl_product_access_event_correlation_missing")
    return sorted(set(errors))


def paper_live_qctrl_product_access_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PAPER_LIVE_QCTRL_PRODUCT_ACCESS_PUBLIC_FIELDS
        if field in artifact
    }
    public_status["recorded"] = artifact.get("recorded") is True
    public_status["event_log_written"] = artifact.get("event_log_written") is True
    public_status["event_log_event_count"] = artifact.get("event_log_event_count", 0)
    public_status["validation_error_count"] = len(
        artifact.get("validation_errors", []) or []
    )
    return public_status


def paper_live_qctrl_product_access_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paper_live_qctrl_product_access(settings)
    if artifact:
        return paper_live_qctrl_product_access_public_status_from_artifact(artifact)
    return {
        "schema_version": PAPER_LIVE_QCTRL_PRODUCT_ACCESS_SCHEMA_VERSION,
        "artifact_type": "paper_live_qctrl_product_access",
        "artifact_id": "paperops:pt-1:qctrl-product-access",
        "phase": "PaperOps",
        "stage": "PT-1",
        "status": "not_run",
        "public_safe": True,
        "recorded": False,
        "event_log_written": False,
        "event_log_event_count": 0,
        "product_access_state": "not_checked",
        "product_access_verified": False,
        "paper_consultation_ready": False,
        "paper_consultation_recorded": False,
        "provider_call_attempted": False,
        "provider_call_succeeded": False,
        "provider_call_count": 0,
        "product_access_blocker": "pt1_not_run",
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "live_endpoint_allowed": False,
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "hardware_submission_allowed": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "secret_value_exposed": False,
        "raw_response_exposed": False,
        "raw_provider_response_persisted": False,
        "provider_failure_message_persisted": False,
        "next_required_action": "Run PT-1 Q-CTRL product access probe.",
        "boundary": PAPER_LIVE_QCTRL_PRODUCT_ACCESS_BOUNDARY,
        "validation_error_count": 0,
    }


def attach_paper_live_qctrl_product_access_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path
        or (_runtime_dir(settings) / PAPER_LIVE_QCTRL_PRODUCT_ACCESS_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPER_LIVE_QCTRL_PRODUCT_ACCESS_EVENT_TYPE,
        PAPER_LIVE_QCTRL_PRODUCT_ACCESS_COMPONENT,
        {
            "status": output.get("status"),
            "product_access_state": output.get("product_access_state"),
            "product_access_verified": output.get("product_access_verified"),
            "provider_call_attempted": output.get("provider_call_attempted"),
            "provider_call_succeeded": output.get("provider_call_succeeded"),
            "provider_call_count": output.get("provider_call_count"),
            "product_access_blocker": output.get("product_access_blocker"),
            "execution_allowed": output.get("execution_allowed"),
            "paper_order_allowed": output.get("paper_order_allowed"),
            "broker_post_allowed": output.get("broker_post_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_paper_live_qctrl_product_access(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    return output, entry


def write_paper_live_qctrl_product_access(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = (
        paper_live_qctrl_product_access_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_paper_live_qctrl_product_access_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_paper_live_qctrl_product_access(output)
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_paper_live_qctrl_product_access(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = paper_live_qctrl_product_access_public_status_from_artifact(
        output
    )
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPER_LIVE_QCTRL_PRODUCT_ACCESS_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "recorded_at": _now(),
        "product_access_state": output.get("product_access_state"),
        "product_access_verified": output.get("product_access_verified"),
        "provider_call_attempted": output.get("provider_call_attempted"),
        "provider_call_succeeded": output.get("provider_call_succeeded"),
        "provider_call_count": output.get("provider_call_count"),
        "product_access_blocker": output.get("product_access_blocker"),
        "validation_error_count": len(output.get("validation_errors", []) or []),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def build_and_write_pt1_qctrl_product_access(
    settings: Settings | None = None,
    *,
    attempt_provider_consultation: bool = False,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    artifact = build_paper_live_qctrl_product_access(
        settings,
        attempt_provider_consultation=attempt_provider_consultation,
    )
    return write_paper_live_qctrl_product_access(artifact, settings=settings)
