"""PT-2 global PaperOps runtime mode.

PT-2 enables Qadam's global paper-operational runtime mode through a recorded
artifact instead of editing environment files. It removes the disabled PaperOps
runtime blocker while keeping broker submits, live endpoints, live capital,
forced trades, Q-CTRL execution authority, and Phase 7 proof credit blocked
until their own guarded gates allow them.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paper_live_activation import read_latest_paper_live_activation
from orchestrator.paper_live_qctrl_product_access import (
    read_latest_paper_live_qctrl_product_access,
)


PAPER_OPERATIONAL_MODE_SCHEMA_VERSION = 1
PAPER_OPERATIONAL_MODE_RUNTIME_ARTIFACT = "paper_operational_mode.json"
PAPER_OPERATIONAL_MODE_HISTORY = "paper_operational_mode_history.jsonl"
PAPER_OPERATIONAL_MODE_EVENT_LOG = "paper_operational_mode_events.jsonl"
PAPER_OPERATIONAL_MODE_EVENT_TYPE = "paper_operational_mode_recorded"
PAPER_OPERATIONAL_MODE_COMPONENT = "paper_operational_mode"

PAPER_OPERATIONAL_MODE_BOUNDARY = (
    "PT-2 records runtime PaperOps mode as enabled through a public-safe "
    "artifact. It does not edit .env or secrets, does not submit paper orders, "
    "does not call brokers or live endpoints, does not enable live capital, "
    "does not force trades, does not grant Phase 7 proof credit, and cannot "
    "give Q-CTRL execution, paper-order, or broker authority. Downstream paper "
    "submit, lifecycle, and exit paths still require their explicit guarded "
    "gates."
)

PAPER_OPERATIONAL_MODE_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "mode",
    "paper_operational_mode_enabled",
    "paper_operational_mode_effective",
    "paper_operational_enabled",
    "settings_paper_operational_enabled",
    "runtime_artifact_override_enabled",
    "paper_operational_flag_disabled",
    "paper_operational_flag_effective",
    "env_file_edited",
    "env_mutation_allowed",
    "pt0_activation_status",
    "pt0_activation_approved",
    "pt0_system_approval_logged",
    "pt1_product_access_status",
    "pt1_product_access_checked",
    "pt1_provider_call_attempted",
    "pt1_provider_call_count",
    "qctrl_product_access_required_for_full_parity",
    "qctrl_product_access_verified",
    "qctrl_product_access_blocker",
    "execution_allowed",
    "paper_order_allowed",
    "paper_order_submission_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_allowed",
    "live_endpoint_called_count",
    "live_capital_enabled",
    "live_credentials_loaded",
    "qctrl_direct_execution_allowed",
    "qctrl_paper_order_allowed",
    "qctrl_broker_post_allowed",
    "qctrl_broker_post_called_count",
    "qctrl_alpaca_post_called_count",
    "qctrl_live_endpoint_called_count",
    "hardware_submission_allowed",
    "phase7_proof_credit_allowed",
    "forced_trades_allowed",
    "secret_value_exposed",
    "raw_response_exposed",
    "next_required_action",
    "boundary",
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


def paper_operational_mode_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_OPERATIONAL_MODE_RUNTIME_ARTIFACT,
        runtime / PAPER_OPERATIONAL_MODE_HISTORY,
        runtime / PAPER_OPERATIONAL_MODE_EVENT_LOG,
    )


def read_latest_paper_operational_mode(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paper_operational_mode_paths(settings)
    return _read_json(output_path)


def _pt0_activation_ready(activation: dict[str, Any]) -> bool:
    return (
        activation.get("status") == "approved_pending_later_enablement"
        and activation.get("approval_state") == "approved"
        and activation.get("approval_logged") is True
        and activation.get("paper_live_activation_approved") is True
        and activation.get("paper_trading_system_approval_logged") is True
        and activation.get("paper_live_mode") == "alpaca_paper_only"
        and activation.get("paper_order_submission_allowed") is False
        and activation.get("live_capital_enabled") is False
        and activation.get("forced_trades_allowed") is False
    )


def _pt1_product_access_checked(product_access: dict[str, Any]) -> bool:
    return (
        product_access.get("status")
        in {
            "blocked_qctrl_product_access_or_subscription",
            "qctrl_paper_consultation_ready",
        }
        and product_access.get("pt0_activation_approved") is True
        and product_access.get("pt0_system_approval_logged") is True
        and product_access.get("provider_call_attempted") is True
        and _int(product_access.get("provider_call_count")) >= 1
        and product_access.get("execution_allowed") is False
        and product_access.get("paper_order_allowed") is False
        and product_access.get("broker_post_allowed") is False
        and product_access.get("live_capital_enabled") is False
        and product_access.get("phase7_proof_credit_allowed") is False
        and _int(product_access.get("broker_post_called_count")) == 0
        and _int(product_access.get("alpaca_post_called_count")) == 0
        and _int(product_access.get("live_endpoint_called_count")) == 0
    )


def _classify_mode(
    *,
    settings: Settings,
    pt0_ready: bool,
    pt1_checked: bool,
) -> tuple[str, bool, str]:
    if settings.mode != "paper":
        return (
            "blocked_not_paper_mode",
            False,
            "Restore QADAM_MODE=paper before enabling global PaperOps mode.",
        )
    if settings.live_capital_enabled:
        return (
            "blocked_live_capital_enabled",
            False,
            "Disable live capital before enabling global PaperOps mode.",
        )
    if not pt0_ready:
        return (
            "blocked_missing_pt0_activation",
            False,
            "Run PT-0 paper-live activation charter first.",
        )
    if not pt1_checked:
        return (
            "blocked_missing_pt1_qctrl_product_access",
            False,
            "Run PT-1 Q-CTRL product-access probe first.",
        )
    return (
        "enabled_pending_downstream_gates",
        True,
        (
            "Resolve Q-CTRL product access for full paper parity, then proceed "
            "to the guarded Alpaca paper submit and paper exit enablement gates."
        ),
    )


def build_paper_operational_mode(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    activation = read_latest_paper_live_activation(settings)
    product_access = read_latest_paper_live_qctrl_product_access(settings)
    pt0_ready = _pt0_activation_ready(activation)
    pt1_checked = _pt1_product_access_checked(product_access)
    status, effective, next_action = _classify_mode(
        settings=settings,
        pt0_ready=pt0_ready,
        pt1_checked=pt1_checked,
    )
    artifact = {
        "schema_version": PAPER_OPERATIONAL_MODE_SCHEMA_VERSION,
        "artifact_type": "paper_operational_mode",
        "artifact_id": "paperops:pt-2:global-paper-operational-mode",
        "phase": "PaperOps",
        "stage": "PT-2",
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
        "paper_operational_mode_enabled": effective,
        "paper_operational_mode_effective": effective,
        "paper_operational_enabled": effective,
        "settings_paper_operational_enabled": settings.paper_operational_enabled,
        "runtime_artifact_override_enabled": (
            effective and not settings.paper_operational_enabled
        ),
        "paper_operational_flag_disabled": not effective,
        "paper_operational_flag_effective": effective,
        "env_file_edited": False,
        "env_mutation_allowed": False,
        "pt0_activation_status": activation.get("status", "missing"),
        "pt0_activation_approved": pt0_ready,
        "pt0_system_approval_logged": (
            activation.get("paper_trading_system_approval_logged") is True
        ),
        "pt1_product_access_status": product_access.get("status", "missing"),
        "pt1_product_access_checked": pt1_checked,
        "pt1_provider_call_attempted": (
            product_access.get("provider_call_attempted") is True
        ),
        "pt1_provider_call_count": _int(product_access.get("provider_call_count")),
        "qctrl_product_access_required_for_full_parity": (
            settings.quantum_paper_parity_required
        ),
        "qctrl_product_access_verified": (
            product_access.get("product_access_verified") is True
        ),
        "qctrl_product_access_blocker": product_access.get(
            "product_access_blocker",
            "missing",
        ),
        "execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "live_endpoint_allowed": False,
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "live_credentials_loaded": False,
        "qctrl_direct_execution_allowed": False,
        "qctrl_paper_order_allowed": False,
        "qctrl_broker_post_allowed": False,
        "qctrl_broker_post_called_count": 0,
        "qctrl_alpaca_post_called_count": 0,
        "qctrl_live_endpoint_called_count": 0,
        "hardware_submission_allowed": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "secret_value_exposed": False,
        "raw_response_exposed": False,
        "next_required_action": next_action,
        "boundary": PAPER_OPERATIONAL_MODE_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paper_operational_mode(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paper_operational_mode(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PAPER_OPERATIONAL_MODE_PUBLIC_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paper_operational_mode_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPER_OPERATIONAL_MODE_SCHEMA_VERSION:
        errors.append("paper_operational_mode_schema_mismatch")
    if artifact.get("artifact_type") != "paper_operational_mode":
        errors.append("paper_operational_mode_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-2":
        errors.append("paper_operational_mode_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paper_operational_mode_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paper_operational_mode_mode_not_paper")
    allowed_statuses = {
        "enabled_pending_downstream_gates",
        "blocked_not_paper_mode",
        "blocked_live_capital_enabled",
        "blocked_missing_pt0_activation",
        "blocked_missing_pt1_qctrl_product_access",
        "not_run",
    }
    if artifact.get("status") not in allowed_statuses:
        errors.append("paper_operational_mode_status_invalid")
    enabled = artifact.get("status") == "enabled_pending_downstream_gates"
    if enabled:
        if artifact.get("paper_operational_mode_enabled") is not True:
            errors.append("paper_operational_mode_enabled_false")
        if artifact.get("paper_operational_mode_effective") is not True:
            errors.append("paper_operational_mode_effective_false")
        if artifact.get("paper_operational_enabled") is not True:
            errors.append("paper_operational_mode_public_enabled_false")
        if artifact.get("paper_operational_flag_disabled") is not False:
            errors.append("paper_operational_mode_flag_still_disabled")
        if artifact.get("paper_operational_flag_effective") is not True:
            errors.append("paper_operational_mode_flag_not_effective")
        if artifact.get("pt0_activation_approved") is not True:
            errors.append("paper_operational_mode_pt0_not_approved")
        if artifact.get("pt0_system_approval_logged") is not True:
            errors.append("paper_operational_mode_pt0_system_not_logged")
        if artifact.get("pt1_product_access_checked") is not True:
            errors.append("paper_operational_mode_pt1_not_checked")
        if artifact.get("pt1_provider_call_attempted") is not True:
            errors.append("paper_operational_mode_pt1_provider_call_missing")
        if _int(artifact.get("pt1_provider_call_count")) < 1:
            errors.append("paper_operational_mode_pt1_provider_call_count_missing")
    for key in (
        "env_file_edited",
        "env_mutation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "live_credentials_loaded",
        "qctrl_direct_execution_allowed",
        "qctrl_paper_order_allowed",
        "qctrl_broker_post_allowed",
        "hardware_submission_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "secret_value_exposed",
        "raw_response_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paper_operational_mode_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "qctrl_broker_post_called_count",
        "qctrl_alpaca_post_called_count",
        "qctrl_live_endpoint_called_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paper_operational_mode_unsafe_counter_nonzero:{key}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "runtime PaperOps mode",
        "does not edit .env",
        "does not submit paper orders",
        "does not grant Phase 7 proof credit",
        "cannot give Q-CTRL execution",
    ):
        if phrase not in boundary:
            errors.append("paper_operational_mode_boundary_weak")
            break
    if artifact.get("recorded") is True and artifact.get("event_log_written") is not True:
        errors.append("paper_operational_mode_event_log_missing")
    if artifact.get("event_log_written") is True:
        if _int(artifact.get("event_log_event_count")) != 1:
            errors.append("paper_operational_mode_event_count_mismatch")
        if not artifact.get("event_log_correlation_id"):
            errors.append("paper_operational_mode_event_correlation_missing")
    return sorted(set(errors))


def paper_operational_mode_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PAPER_OPERATIONAL_MODE_PUBLIC_FIELDS
        if field in artifact
    }
    public_status["recorded"] = artifact.get("recorded") is True
    public_status["event_log_written"] = artifact.get("event_log_written") is True
    public_status["event_log_event_count"] = artifact.get("event_log_event_count", 0)
    public_status["validation_error_count"] = len(
        artifact.get("validation_errors", []) or []
    )
    return public_status


def paper_operational_mode_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paper_operational_mode(settings)
    if artifact:
        return paper_operational_mode_public_status_from_artifact(artifact)
    return {
        "schema_version": PAPER_OPERATIONAL_MODE_SCHEMA_VERSION,
        "artifact_type": "paper_operational_mode",
        "artifact_id": "paperops:pt-2:global-paper-operational-mode",
        "phase": "PaperOps",
        "stage": "PT-2",
        "status": "not_run",
        "public_safe": True,
        "recorded": False,
        "event_log_written": False,
        "event_log_event_count": 0,
        "mode": (settings or Settings.from_env()).mode,
        "paper_operational_mode_enabled": False,
        "paper_operational_mode_effective": False,
        "paper_operational_enabled": False,
        "settings_paper_operational_enabled": (
            settings or Settings.from_env()
        ).paper_operational_enabled,
        "runtime_artifact_override_enabled": False,
        "paper_operational_flag_disabled": True,
        "paper_operational_flag_effective": False,
        "env_file_edited": False,
        "env_mutation_allowed": False,
        "pt0_activation_status": "missing",
        "pt0_activation_approved": False,
        "pt0_system_approval_logged": False,
        "pt1_product_access_status": "missing",
        "pt1_product_access_checked": False,
        "pt1_provider_call_attempted": False,
        "pt1_provider_call_count": 0,
        "qctrl_product_access_required_for_full_parity": (
            settings or Settings.from_env()
        ).quantum_paper_parity_required,
        "qctrl_product_access_verified": False,
        "qctrl_product_access_blocker": "pt2_not_run",
        "execution_allowed": False,
        "paper_order_allowed": False,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "live_endpoint_allowed": False,
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "live_credentials_loaded": False,
        "qctrl_direct_execution_allowed": False,
        "qctrl_paper_order_allowed": False,
        "qctrl_broker_post_allowed": False,
        "qctrl_broker_post_called_count": 0,
        "qctrl_alpaca_post_called_count": 0,
        "qctrl_live_endpoint_called_count": 0,
        "hardware_submission_allowed": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "secret_value_exposed": False,
        "raw_response_exposed": False,
        "next_required_action": "Run PT-2 global PaperOps mode enablement.",
        "boundary": PAPER_OPERATIONAL_MODE_BOUNDARY,
        "validation_error_count": 0,
    }


def paper_operational_mode_effective(settings: Settings | None = None) -> bool:
    settings = settings or Settings.from_env()
    artifact = read_latest_paper_operational_mode(settings)
    if (
        artifact
        and artifact.get("paper_operational_mode_effective") is True
        and artifact.get("status") == "enabled_pending_downstream_gates"
        and not validate_paper_operational_mode(artifact)
    ):
        return True
    return settings.paper_operational_enabled


def attach_paper_operational_mode_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path
        or (_runtime_dir(settings) / PAPER_OPERATIONAL_MODE_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPER_OPERATIONAL_MODE_EVENT_TYPE,
        PAPER_OPERATIONAL_MODE_COMPONENT,
        {
            "status": output.get("status"),
            "paper_operational_mode_enabled": output.get(
                "paper_operational_mode_enabled"
            ),
            "paper_operational_mode_effective": output.get(
                "paper_operational_mode_effective"
            ),
            "settings_paper_operational_enabled": output.get(
                "settings_paper_operational_enabled"
            ),
            "runtime_artifact_override_enabled": output.get(
                "runtime_artifact_override_enabled"
            ),
            "pt0_activation_approved": output.get("pt0_activation_approved"),
            "pt1_product_access_checked": output.get("pt1_product_access_checked"),
            "qctrl_product_access_verified": output.get(
                "qctrl_product_access_verified"
            ),
            "qctrl_product_access_blocker": output.get(
                "qctrl_product_access_blocker"
            ),
            "paper_order_submission_allowed": output.get(
                "paper_order_submission_allowed"
            ),
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
    output["validation_errors"] = validate_paper_operational_mode(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    return output, entry


def write_paper_operational_mode(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = paper_operational_mode_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        if event_path.exists():
            event_path.unlink()
        output, _ = attach_paper_operational_mode_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_paper_operational_mode(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(output, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
