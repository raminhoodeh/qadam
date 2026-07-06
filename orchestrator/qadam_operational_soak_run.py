"""Qadam operational soak run and final declaration.

The soak run is calendar-honest. It records the current certification state and
incidents, but it does not simulate seven days or declare completion early.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operational_perfection import build_and_write_operational_perfection_certification
from orchestrator.qsase_governance_safety_contract import universal_authority_flags

SCHEMA_VERSION = "qadam_operational_soak_run.v1"

PRIMARY_ARTIFACT = "qadam_operational_soak_run.json"
DAILY_SUMMARIES_ARTIFACT = "qadam_operational_soak_daily_summaries.jsonl"
INCIDENT_LOG_ARTIFACT = "qadam_operational_incident_log.jsonl"
FINAL_DECLARATION_ARTIFACT = "qadam_final_live_declaration.json"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_operational_soak_dashboard_summary.json"
HISTORY_ARTIFACT = "qadam_operational_soak_history.jsonl"
EVENTS_ARTIFACT = "qadam_operational_soak_events.jsonl"
PHASE_STATUS_ARTIFACT = "qsase_phase_implementation_status.json"

CERTIFICATION_ARTIFACT = "qadam_operational_perfection_certification.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
DASHBOARD_COMPLETION_ARTIFACT = "qsase_dashboard_completion_v2.json"
TELEGRAM_SUMMARY_ARTIFACT = "qsase_telegram_summary_v2.json"

REQUIRED_SOAK_DAYS = 7

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "command_disabled": True,
    "soak_monitor_only": True,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "telegram_live_send_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_created": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "live_capital_enabled": False,
}

FALSE_AUTHORITY_FIELDS = {key for key, value in AUTHORITY_FLAGS.items() if value is False}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _artifact_ref(filename: str) -> str:
    return f"data/runtime/{filename}"


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _today(generated_at: datetime) -> str:
    return generated_at.date().isoformat()


def _dedupe_by_date(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for record in records:
        date_key = str(record.get("soak_date") or "")
        if date_key:
            by_date[date_key] = record
    return by_date


def _build_incidents(generated_at: str, certification: dict[str, Any]) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []
    for blocker in _safe_list(certification.get("unresolved_blockers")):
        incidents.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_operational_incident",
                "generated_at": generated_at,
                "incident_type": "certification_blocker",
                "severity": "critical" if blocker.get("gate") in {"safety_boundaries", "self_healing"} else "high",
                "gate": blocker.get("gate"),
                "summary": blocker.get("reason"),
                "artifact_ref": blocker.get("artifact_ref"),
                "state": "open",
                "paper_order_created": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return incidents


def build_operational_soak_run(settings: Settings | None = None, *, refresh_certification: bool = True) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    runtime = _runtime_dir(settings)
    if refresh_certification:
        build_and_write_operational_perfection_certification(settings, refresh_self_healing=True)
    certification = _read_json(runtime / CERTIFICATION_ARTIFACT)
    paperops = _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT)
    dashboard = _read_json(runtime / DASHBOARD_COMPLETION_ARTIFACT)
    telegram = _read_json(runtime / TELEGRAM_SUMMARY_ARTIFACT)
    generated_dt = _now()
    generated_at = _iso(generated_dt)
    soak_date = _today(generated_dt)
    existing_summaries = _read_jsonl(runtime / DAILY_SUMMARIES_ARTIFACT, limit=500)
    by_date = _dedupe_by_date(existing_summaries)
    daily_summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operational_soak_daily_summary",
        "generated_at": generated_at,
        "soak_date": soak_date,
        "certification_status": certification.get("status"),
        "operationally_complete": certification.get("operationally_complete"),
        "failed_gate_count": certification.get("failed_gate_count"),
        "why_not_trading_now": certification.get("why_not_trading_now"),
        "paperops_status": paperops.get("status") or paperops.get("cycle_state"),
        "dashboard_status": dashboard.get("status"),
        "telegram_status": telegram.get("status"),
        "paper_review_candidate_count": certification.get("paper_review_candidate_count"),
        "active_paper_position_count": certification.get("active_paper_position_count"),
        "paper_order_created": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    by_date[soak_date] = daily_summary
    daily_summaries = [by_date[key] for key in sorted(by_date)]
    incidents = _build_incidents(generated_at, certification)
    unique_soak_days = len({record.get("soak_date") for record in daily_summaries if record.get("soak_date")})
    unresolved_critical = [incident for incident in incidents if incident.get("severity") == "critical"]
    unresolved_incident_count = len(incidents)
    soak_complete = unique_soak_days >= REQUIRED_SOAK_DAYS and certification.get("operationally_complete") is True and unresolved_incident_count == 0
    if soak_complete:
        status = "qadam_soak_run_complete"
    elif unique_soak_days:
        status = "qadam_soak_run_in_progress"
    else:
        status = "qadam_soak_run_not_started"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operational_soak_run",
        "generated_at": generated_at,
        "status": status,
        "required_soak_days": REQUIRED_SOAK_DAYS,
        "observed_soak_day_count": unique_soak_days,
        "soak_complete": soak_complete,
        "calendar_honest": True,
        "simulated_elapsed_time_allowed": False,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "command_disabled": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "certification_status": certification.get("status"),
        "operationally_complete": certification.get("operationally_complete"),
        "unresolved_incident_count": unresolved_incident_count,
        "unresolved_critical_incident_count": len(unresolved_critical),
        "daily_summaries_path": _artifact_ref(DAILY_SUMMARIES_ARTIFACT),
        "incident_log_path": _artifact_ref(INCIDENT_LOG_ARTIFACT),
        "why_not_trading_now": certification.get("why_not_trading_now"),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "boundary": "The soak run records real calendar observations only. It cannot simulate elapsed time, force trades, write brokers, or declare completion before seven actual days pass.",
    }
    final_declaration = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_final_live_declaration",
        "generated_at": generated_at,
        "status": "qadam_final_declaration_ready" if soak_complete else "qadam_final_declaration_not_ready",
        "declaration": (
            "Yes. Qadam is operationally complete and running as designed."
            if soak_complete
            else f"No. Qadam is not operationally complete yet. The current blocker is: {certification.get('why_not_trading_now', 'soak incomplete')}."
        ),
        "soak_complete": soak_complete,
        "operationally_complete": certification.get("operationally_complete"),
        "observed_soak_day_count": unique_soak_days,
        "required_soak_days": REQUIRED_SOAK_DAYS,
        "unresolved_incident_count": unresolved_incident_count,
        "calendar_honest": True,
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
    }
    return payload, daily_summaries, incidents, final_declaration


def validate_operational_soak(payload: dict[str, Any], final_declaration: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qadam_operational_soak_run":
        errors.append("artifact_type_mismatch")
    for field in ("calendar_honest", "public_safe", "read_only", "paper_only", "proposal_first", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{field}_must_not_be_true")
    if payload.get("simulated_elapsed_time_allowed") is not False:
        errors.append("simulated_elapsed_time_allowed_must_be_false")
    if payload.get("soak_complete") is True and _int(payload.get("observed_soak_day_count"), 0) < REQUIRED_SOAK_DAYS:
        errors.append("soak_complete_before_required_days")
    if final_declaration.get("status") == "qadam_final_declaration_ready" and payload.get("soak_complete") is not True:
        errors.append("final_declaration_ready_before_soak_complete")
    if _int(payload.get("paper_order_created_count"), 0) != 0:
        errors.append("paper_order_created_count_must_be_zero")
    if _int(payload.get("broker_write_count"), 0) != 0:
        errors.append("broker_write_count_must_be_zero")
    if payload.get("proof_credit_allowed") is not False:
        errors.append("proof_credit_allowed_must_be_false")
    if payload.get("live_capital_enabled") is not False:
        errors.append("live_capital_enabled_must_be_false")
    return sorted(set(errors))


def _dashboard_summary(payload: dict[str, Any], final_declaration: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operational_soak_dashboard_summary",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "soak_complete": payload.get("soak_complete"),
        "observed_soak_day_count": payload.get("observed_soak_day_count"),
        "required_soak_days": payload.get("required_soak_days"),
        "final_declaration_status": final_declaration.get("status"),
        "declaration": final_declaration.get("declaration"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
    }


def _phase_record(payload: dict[str, Any], final_declaration: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "Perfect Operation Phase 17: Soak Run And Final Live Declaration",
        "status": payload.get("status"),
        "artifact_path": _artifact_ref(PRIMARY_ARTIFACT),
        "soak_complete": payload.get("soak_complete"),
        "observed_soak_day_count": payload.get("observed_soak_day_count"),
        "required_soak_days": payload.get("required_soak_days"),
        "final_declaration_status": final_declaration.get("status"),
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "proposal_first": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "live_capital_enabled": False,
    }


def _update_phase_status(path: Path, payload: dict[str, Any], final_declaration: dict[str, Any]) -> None:
    current = _read_json(path)
    phases = _safe_dict(current.get("phases"))
    phases["perfect_operation_phase_17_soak_run_final_declaration"] = _phase_record(payload, final_declaration)
    safety = {
        **_safe_dict(current.get("safety")),
        "phase17_soak_outputs_are_review_only": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "telegram_command_path_enabled": False,
    }
    _write_json(
        path,
        {
            **current,
            "schema_version": current.get("schema_version", 1),
            "generated_at": payload.get("generated_at"),
            "active_phase": "perfect_operation_phase_17_soak_run_final_declaration",
            "phases": phases,
            "safety": safety,
        },
    )


def build_and_write_operational_soak_run(settings: Settings | None = None, *, refresh_certification: bool = True) -> tuple[dict[str, Any], dict[str, Any], dict[str, str], list[str]]:
    payload, daily_summaries, incidents, final_declaration = build_operational_soak_run(settings, refresh_certification=refresh_certification)
    runtime = _runtime_dir(settings)
    written: dict[str, str] = {}
    _write_json(runtime / PRIMARY_ARTIFACT, payload)
    written["primary"] = str(runtime / PRIMARY_ARTIFACT)
    _write_jsonl(runtime / DAILY_SUMMARIES_ARTIFACT, daily_summaries)
    written["daily_summaries"] = str(runtime / DAILY_SUMMARIES_ARTIFACT)
    _write_jsonl(runtime / INCIDENT_LOG_ARTIFACT, incidents)
    written["incident_log"] = str(runtime / INCIDENT_LOG_ARTIFACT)
    _write_json(runtime / FINAL_DECLARATION_ARTIFACT, final_declaration)
    written["final_declaration"] = str(runtime / FINAL_DECLARATION_ARTIFACT)
    _write_json(runtime / DASHBOARD_SUMMARY_ARTIFACT, _dashboard_summary(payload, final_declaration))
    written["dashboard_summary"] = str(runtime / DASHBOARD_SUMMARY_ARTIFACT)
    event = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": "qadam_operational_soak_run_written",
        "status": payload.get("status"),
        "soak_complete": payload.get("soak_complete"),
        "observed_soak_day_count": payload.get("observed_soak_day_count"),
        "unresolved_incident_count": payload.get("unresolved_incident_count"),
    }
    _append_jsonl(runtime / HISTORY_ARTIFACT, event)
    _append_jsonl(runtime / EVENTS_ARTIFACT, event)
    written["history"] = str(runtime / HISTORY_ARTIFACT)
    written["events"] = str(runtime / EVENTS_ARTIFACT)
    _update_phase_status(runtime / PHASE_STATUS_ARTIFACT, payload, final_declaration)
    written["phase_status"] = str(runtime / PHASE_STATUS_ARTIFACT)
    errors = validate_operational_soak(payload, final_declaration)
    return payload, final_declaration, written, errors
