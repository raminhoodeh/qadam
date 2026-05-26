"""PT-0 paper-live activation charter.

This contract records explicit Fund Manager approval for paper-live operation:
Alpaca paper POST/GET/close paths may be enabled by later gates, while live
capital and live endpoints remain forbidden. PT-0 does not submit orders,
change environment flags, edit secrets, or grant Phase 7 proof credit.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry


PAPER_LIVE_ACTIVATION_SCHEMA_VERSION = 1
PAPER_LIVE_ACTIVATION_RUNTIME_ARTIFACT = "paper_live_activation.json"
PAPER_LIVE_ACTIVATION_HISTORY = "paper_live_activation_history.jsonl"
PAPER_LIVE_ACTIVATION_EVENT_LOG = "paper_live_activation_events.jsonl"
PAPER_LIVE_ACTIVATION_EVENT_TYPE = "paper_live_activation_charter_recorded"
PAPER_LIVE_ACTIVATION_COMPONENT = "paper_live_activation"

PAPER_LIVE_APPROVAL_INSTRUCTION = (
    "Fund Manager instruction in the Codex thread on 2026-05-26: proceed with "
    "PT-0: Paper-Live Activation Charter. This records system-level approval "
    "for Qadam to operate against the Alpaca paper account after later PT "
    "enablement gates pass. It is not live-capital approval and is not an "
    "immediate broker-submit instruction."
)

PAPER_LIVE_BOUNDARY = (
    "PT-0 defines paper-live as Alpaca paper-only broker POST, GET, and close "
    "paths that can be enabled by later guarded PT stages after qualified "
    "setups, Q-CTRL advisory checks, kill switches, duplicate guards, and "
    "pre-trade snapshots pass. PT-0 cannot submit paper orders by itself, "
    "cannot edit .env or secrets, cannot call live endpoints, cannot load live "
    "credentials, cannot enable live capital, cannot force trades, cannot grant "
    "Phase 7 proof credit, and cannot give Q-CTRL execution or broker authority."
)

PAPER_LIVE_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "mode",
    "approval_state",
    "approval_scope",
    "approval_logged",
    "paper_live_activation_approved",
    "paper_trading_system_approval_logged",
    "paper_live_mode_defined",
    "paper_live_mode",
    "broker_scope",
    "paper_endpoint_required",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "live_credentials_loaded",
    "paper_operational_env_mutation_allowed",
    "env_file_edited",
    "per_trade_manual_approval_required",
    "manual_trade_level_approval_required",
    "paper_order_submission_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_called_count",
    "phase7_proof_credit_allowed",
    "phase7_proof_rules_separate",
    "forced_trades_allowed",
    "qualified_setup_required",
    "qctrl_consultation_required",
    "qctrl_direct_execution_allowed",
    "qctrl_broker_post_allowed",
    "max_order_notional_gbp",
    "daily_trade_cap",
    "max_concurrent_positions",
    "max_daily_loss_fraction",
    "max_drawdown_fraction",
    "regular_market_hours_only",
    "duplicate_guard_required",
    "idempotency_required",
    "pretrade_snapshot_required",
    "event_log_prewrite_required",
    "emergency_kill_switch_required",
    "no_automatic_order_post_retry",
    "next_required_stage",
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


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def paper_live_activation_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_LIVE_ACTIVATION_RUNTIME_ARTIFACT,
        runtime / PAPER_LIVE_ACTIVATION_HISTORY,
        runtime / PAPER_LIVE_ACTIVATION_EVENT_LOG,
    )


def read_latest_paper_live_activation(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = paper_live_activation_paths(settings)
    return _read_json(output_path)


def _risk_policy(settings: Settings) -> dict[str, Any]:
    max_notional = max(1, int(settings.paper_operational_max_notional_gbp or 1000))
    return {
        "max_order_notional_gbp": max_notional,
        "daily_trade_cap": 3,
        "max_concurrent_positions": 1,
        "max_daily_loss_fraction": 0.02,
        "max_drawdown_fraction": 0.20,
        "regular_market_hours_only": True,
        "duplicate_guard_required": True,
        "idempotency_required": True,
        "pretrade_snapshot_required": True,
        "event_log_prewrite_required": True,
        "emergency_kill_switch_required": True,
        "no_automatic_order_post_retry": True,
    }


def _approval_record(generated_at: str) -> dict[str, Any]:
    return {
        "approval_state": "approved",
        "approval_scope": "system_level_alpaca_paper_trading_only",
        "approver_label": "fund_manager_ramin",
        "approver_role": "Fund Manager",
        "approval_source": "codex_thread_pt_0_request",
        "approval_instruction": PAPER_LIVE_APPROVAL_INSTRUCTION,
        "approval_timestamp": generated_at,
        "approval_logged": False,
        "per_trade_manual_approval_required": False,
        "manual_trade_level_approval_required": False,
        "paper_live_activation_approved": True,
        "paper_trading_system_approval_logged": False,
        "live_capital_enabled": False,
        "boundary": (
            "This approval covers system-level Alpaca paper operation only. It "
            "does not approve live capital, live endpoints, forced trades, or "
            "per-trade manual bypasses."
        ),
    }


def build_paper_live_activation(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    approval = _approval_record(generated_at)
    risk_policy = _risk_policy(settings)
    artifact = {
        "schema_version": PAPER_LIVE_ACTIVATION_SCHEMA_VERSION,
        "artifact_type": "paper_live_activation_charter",
        "artifact_id": "paperops:pt-0:paper-live-activation-charter",
        "phase": "PaperOps",
        "stage": "PT-0",
        "status": "approved_pending_later_enablement",
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
        "alpaca_paper_submit_enabled": settings.alpaca_paper_submit_enabled,
        "alpaca_paper_exit_enabled": settings.alpaca_paper_exit_enabled,
        "approval_state": approval["approval_state"],
        "approval_scope": approval["approval_scope"],
        "approver_label": approval["approver_label"],
        "approver_role": approval["approver_role"],
        "approval_source": approval["approval_source"],
        "approval_instruction": approval["approval_instruction"],
        "approval_timestamp": approval["approval_timestamp"],
        "approval_logged": False,
        "approval_record": approval,
        "paper_live_activation_approved": True,
        "paper_trading_system_approval_logged": False,
        "paper_live_mode_defined": True,
        "paper_live_mode": "alpaca_paper_only",
        "broker_scope": "alpaca_paper_account_only",
        "broker_operations_covered": ["paper_post_order", "paper_get_order", "paper_close_position"],
        "paper_endpoint_required": True,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "live_credentials_loaded": False,
        "paper_operational_env_mutation_allowed": False,
        "env_file_edited": False,
        "per_trade_manual_approval_required": False,
        "manual_trade_level_approval_required": False,
        "paper_order_submission_allowed": False,
        "paper_submit_enablement_allowed_next": True,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "live_endpoint_called_count": 0,
        "phase7_proof_credit_allowed": False,
        "phase7_proof_rules_separate": True,
        "forced_trades_allowed": False,
        "qualified_setup_required": True,
        "qctrl_consultation_required": True,
        "qctrl_direct_execution_allowed": False,
        "qctrl_broker_post_allowed": False,
        "risk_policy": risk_policy,
        **risk_policy,
        "next_required_stage": (
            "PT-1 Q-CTRL paper consultation product access, then PT-2 explicit "
            "paper operational flag enablement and PT-3 Alpaca paper submit path."
        ),
        "boundary": PAPER_LIVE_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paper_live_activation(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    artifact["public_status"] = paper_live_activation_public_status_from_artifact(
        artifact
    )
    return artifact


def validate_paper_live_activation(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PAPER_LIVE_PUBLIC_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
        "approval_record",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paper_live_activation_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPER_LIVE_ACTIVATION_SCHEMA_VERSION:
        errors.append("paper_live_activation_schema_mismatch")
    if artifact.get("artifact_type") != "paper_live_activation_charter":
        errors.append("paper_live_activation_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-0":
        errors.append("paper_live_activation_phase_stage_mismatch")
    if artifact.get("mode") != "paper":
        errors.append("paper_live_activation_mode_not_paper")
    if artifact.get("public_safe") is not True:
        errors.append("paper_live_activation_not_public_safe")
    if artifact.get("approval_state") != "approved":
        errors.append("paper_live_activation_not_approved")
    if artifact.get("approval_scope") != "system_level_alpaca_paper_trading_only":
        errors.append("paper_live_activation_scope_invalid")
    if artifact.get("paper_live_activation_approved") is not True:
        errors.append("paper_live_activation_approved_false")
    if artifact.get("paper_live_mode_defined") is not True:
        errors.append("paper_live_activation_mode_not_defined")
    if artifact.get("paper_live_mode") != "alpaca_paper_only":
        errors.append("paper_live_activation_mode_invalid")
    if artifact.get("paper_endpoint_required") is not True:
        errors.append("paper_live_activation_paper_endpoint_not_required")
    for key in (
        "live_endpoint_allowed",
        "live_capital_enabled",
        "live_credentials_loaded",
        "paper_operational_env_mutation_allowed",
        "env_file_edited",
        "per_trade_manual_approval_required",
        "manual_trade_level_approval_required",
        "paper_order_submission_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "qctrl_direct_execution_allowed",
        "qctrl_broker_post_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paper_live_activation_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paper_live_activation_unsafe_counter_nonzero:{key}")
    if artifact.get("phase7_proof_rules_separate") is not True:
        errors.append("paper_live_activation_phase7_rules_not_separate")
    if artifact.get("qualified_setup_required") is not True:
        errors.append("paper_live_activation_qualified_setup_not_required")
    if artifact.get("qctrl_consultation_required") is not True:
        errors.append("paper_live_activation_qctrl_not_required")
    if _int(artifact.get("max_order_notional_gbp")) <= 0:
        errors.append("paper_live_activation_max_order_notional_invalid")
    if _int(artifact.get("daily_trade_cap")) <= 0:
        errors.append("paper_live_activation_daily_trade_cap_invalid")
    if _int(artifact.get("max_concurrent_positions")) <= 0:
        errors.append("paper_live_activation_max_concurrent_positions_invalid")
    if not 0 < _float(artifact.get("max_daily_loss_fraction")) <= 0.05:
        errors.append("paper_live_activation_daily_loss_fraction_invalid")
    if not 0 < _float(artifact.get("max_drawdown_fraction")) <= 0.20:
        errors.append("paper_live_activation_drawdown_fraction_invalid")
    for key in (
        "regular_market_hours_only",
        "duplicate_guard_required",
        "idempotency_required",
        "pretrade_snapshot_required",
        "event_log_prewrite_required",
        "emergency_kill_switch_required",
        "no_automatic_order_post_retry",
    ):
        if artifact.get(key) is not True:
            errors.append(f"paper_live_activation_control_missing:{key}")
    approval_record = artifact.get("approval_record", {})
    if not isinstance(approval_record, dict):
        errors.append("paper_live_activation_approval_record_invalid")
    else:
        if approval_record.get("approval_state") != "approved":
            errors.append("paper_live_activation_record_not_approved")
        if approval_record.get("approval_scope") != artifact.get("approval_scope"):
            errors.append("paper_live_activation_record_scope_mismatch")
        if approval_record.get("live_capital_enabled") is not False:
            errors.append("paper_live_activation_record_live_capital_enabled")
    if (
        artifact.get("recorded") is True
        and artifact.get("event_log_required") is True
        and artifact.get("event_log_written") is not True
    ):
        errors.append("paper_live_activation_event_log_missing")
    if artifact.get("event_log_written") is True:
        if artifact.get("event_log_event_count") != 1:
            errors.append("paper_live_activation_event_count_mismatch")
        if not artifact.get("event_log_correlation_id"):
            errors.append("paper_live_activation_event_correlation_missing")
        if artifact.get("approval_logged") is not True:
            errors.append("paper_live_activation_approval_not_logged")
        if artifact.get("paper_trading_system_approval_logged") is not True:
            errors.append("paper_live_activation_system_approval_not_logged")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "paper-live as Alpaca paper-only",
        "cannot submit paper orders by itself",
        "cannot edit .env or secrets",
        "cannot call live endpoints",
        "cannot force trades",
        "cannot grant Phase 7 proof credit",
        "cannot give Q-CTRL execution",
    ):
        if phrase not in boundary:
            errors.append("paper_live_activation_boundary_weak")
            break
    return sorted(set(errors))


def paper_live_activation_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PAPER_LIVE_PUBLIC_FIELDS
        if field in artifact
    }
    public_status["recorded"] = artifact.get("recorded") is True
    public_status["event_log_written"] = artifact.get("event_log_written") is True
    public_status["event_log_event_count"] = artifact.get("event_log_event_count", 0)
    public_status["validation_error_count"] = len(
        artifact.get("validation_errors", []) or []
    )
    return public_status


def paper_live_activation_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paper_live_activation(settings)
    if not artifact:
        return {
            "schema_version": PAPER_LIVE_ACTIVATION_SCHEMA_VERSION,
            "artifact_type": "paper_live_activation_charter",
            "artifact_id": "paperops:pt-0:paper-live-activation-charter",
            "phase": "PaperOps",
            "stage": "PT-0",
            "status": "not_run",
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "approval_state": "missing",
            "approval_scope": "system_level_alpaca_paper_trading_only",
            "approval_logged": False,
            "paper_live_activation_approved": False,
            "paper_trading_system_approval_logged": False,
            "paper_live_mode_defined": True,
            "paper_live_mode": "alpaca_paper_only",
            "broker_scope": "alpaca_paper_account_only",
            "paper_endpoint_required": True,
            "live_endpoint_allowed": False,
            "live_capital_enabled": False,
            "live_credentials_loaded": False,
            "paper_operational_env_mutation_allowed": False,
            "env_file_edited": False,
            "per_trade_manual_approval_required": False,
            "manual_trade_level_approval_required": False,
            "paper_order_submission_allowed": False,
            "broker_post_called_count": 0,
            "alpaca_post_called_count": 0,
            "live_endpoint_called_count": 0,
            "phase7_proof_credit_allowed": False,
            "phase7_proof_rules_separate": True,
            "forced_trades_allowed": False,
            "qualified_setup_required": True,
            "qctrl_consultation_required": True,
            "qctrl_direct_execution_allowed": False,
            "qctrl_broker_post_allowed": False,
            "max_order_notional_gbp": (settings or Settings.from_env()).paper_operational_max_notional_gbp,
            "daily_trade_cap": 3,
            "max_concurrent_positions": 1,
            "max_daily_loss_fraction": 0.02,
            "max_drawdown_fraction": 0.20,
            "regular_market_hours_only": True,
            "duplicate_guard_required": True,
            "idempotency_required": True,
            "pretrade_snapshot_required": True,
            "event_log_prewrite_required": True,
            "emergency_kill_switch_required": True,
            "no_automatic_order_post_retry": True,
            "next_required_stage": "Run PT-0 paper-live activation charter.",
            "validation_error_count": 0,
            "boundary": PAPER_LIVE_BOUNDARY,
        }
    return paper_live_activation_public_status_from_artifact(artifact)


def attach_paper_live_activation_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PAPER_LIVE_ACTIVATION_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPER_LIVE_ACTIVATION_EVENT_TYPE,
        PAPER_LIVE_ACTIVATION_COMPONENT,
        {
            "status": output.get("status"),
            "approval_state": output.get("approval_state"),
            "approval_scope": output.get("approval_scope"),
            "paper_live_activation_approved": output.get(
                "paper_live_activation_approved"
            ),
            "paper_trading_system_approval_logged": True,
            "per_trade_manual_approval_required": output.get(
                "per_trade_manual_approval_required"
            ),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "paper_order_submission_allowed": output.get(
                "paper_order_submission_allowed"
            ),
            "broker_post_called_count": output.get("broker_post_called_count"),
            "alpaca_post_called_count": output.get("alpaca_post_called_count"),
            "qctrl_consultation_required": output.get("qctrl_consultation_required"),
            "forced_trades_allowed": output.get("forced_trades_allowed"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        },
    )
    output["recorded"] = True
    output["approval_logged"] = True
    output["paper_trading_system_approval_logged"] = True
    approval_record = deepcopy(output.get("approval_record", {}))
    approval_record["approval_logged"] = True
    approval_record["paper_trading_system_approval_logged"] = True
    approval_record["event_log_correlation_id"] = entry.correlation_id
    approval_record["event_log_created_at"] = entry.created_at
    output["approval_record"] = approval_record
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_paper_live_activation(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = paper_live_activation_public_status_from_artifact(output)
    return output, entry


def write_paper_live_activation(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = paper_live_activation_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_paper_live_activation_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_paper_live_activation(output)
        output["public_status"] = paper_live_activation_public_status_from_artifact(output)
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_paper_live_activation(output)
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = paper_live_activation_public_status_from_artifact(output)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPER_LIVE_ACTIVATION_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "recorded_at": _now(),
        "approval_state": output.get("approval_state"),
        "approval_logged": output.get("approval_logged"),
        "paper_live_activation_approved": output.get("paper_live_activation_approved"),
        "paper_trading_system_approval_logged": output.get(
            "paper_trading_system_approval_logged"
        ),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "paper_order_submission_allowed": output.get("paper_order_submission_allowed"),
        "broker_post_called_count": output.get("broker_post_called_count"),
        "alpaca_post_called_count": output.get("alpaca_post_called_count"),
        "validation_error_count": len(output.get("validation_errors", []) or []),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
