"""Qadam self-healing operations supervisor.

The supervisor is deliberately narrow: it can run known safe refresh builders,
quarantine degraded source records from quorum, and write repair requests. It
cannot edit code, mutate policy, create trades, submit orders, write to brokers,
send Telegram messages, grant proof credit, or enable live capital.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.cockpit_status import export_cockpit_status
from orchestrator.qadam_git_deploy_readiness import build_and_write_git_deploy_readiness
from orchestrator.qsase_dashboard_view_model import build_and_write_dashboard_view_model
from orchestrator.qsase_governance_safety_contract import universal_authority_flags
from orchestrator.qsase_historical_memory_completion import build_and_write_historical_memory_completion
from orchestrator.qsase_market_confirmation import build_and_write_market_confirmation
from orchestrator.qsase_phase11_to14_completion import build_and_write_phase11_to14_completion
from orchestrator.qsase_phase5_to10_completion import build_and_write_phase5_to10_completion
from orchestrator.qsase_source_reliability import build_and_write_source_reliability

SCHEMA_VERSION = "qadam_self_healing_supervisor.v1"

PRIMARY_ARTIFACT = "qadam_self_healing_state.json"
QUARANTINE_ARTIFACT = "qadam_quarantine_state.json"
REPAIR_REQUESTS_ARTIFACT = "qadam_repair_requests.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_self_healing_dashboard_summary.json"
HISTORY_ARTIFACT = "qadam_self_healing_history.jsonl"
EVENTS_ARTIFACT = "qadam_self_healing_events.jsonl"
PHASE_STATUS_ARTIFACT = "qsase_phase_implementation_status.json"

SOURCE_RELIABILITY_ARTIFACT = "qsase_source_reliability.json"
SOURCE_RELIABILITY_RECORDS_ARTIFACT = "qsase_source_reliability_records.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_memory_completion.json"
AKBER_INPUT_COMPLETENESS_ARTIFACT = "qsase_akber_input_completeness.json"
DASHBOARD_COMPLETION_ARTIFACT = "qsase_dashboard_completion_v2.json"
PAPER_LIFECYCLE_ARTIFACT = "qsase_paper_lifecycle_v2.json"
GIT_DEPLOY_ARTIFACT = "qadam_git_deploy_readiness.json"

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "command_disabled": True,
    "safe_refresh_allowed": True,
    "quarantine_allowed": True,
    "repair_request_allowed": True,
    "code_edit_allowed": False,
    "autonomous_code_edit_allowed": False,
    "policy_mutation_allowed": False,
    "policy_mutation_created": False,
    "source_trust_update_created": False,
    "model_weight_update_created": False,
    "filter_threshold_update_created": False,
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


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _public_path(value: Any) -> str:
    text = str(value)
    path = Path(text)
    if not path.is_absolute():
        return text
    try:
        return str(path.relative_to(_repo_root()))
    except ValueError:
        return path.name


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _run_refresh(
    name: str,
    generated_at: str,
    handler: Callable[[Settings | None], Any],
    settings: Settings | None,
) -> dict[str, Any]:
    try:
        result = handler(settings)
    except Exception as exc:  # pragma: no cover - exercised by runtime failures.
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "refresh_name": name,
            "status": "refresh_failed",
            "error": f"{type(exc).__name__}: {exc}",
            "safe_refresh": True,
            "broker_write_allowed": False,
            "paper_order_created": False,
            "live_capital_enabled": False,
        }
    written: dict[str, str] = {}
    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, dict):
                written.update({str(key): _public_path(value) for key, value in item.items() if isinstance(value, (str, Path))})
    elif isinstance(result, dict):
        written = {str(key): _public_path(value) for key, value in result.items() if isinstance(value, (str, Path))}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "refresh_name": name,
        "status": "refresh_ok",
        "safe_refresh": True,
        "written": written,
        "broker_write_allowed": False,
        "paper_order_created": False,
        "live_capital_enabled": False,
    }


def _refresh_cockpit_status(settings: Settings | None = None) -> dict[str, Any]:
    _ = settings
    return export_cockpit_status(landing_repo_path=_repo_root() / "landing-page-repo")


SAFE_REFRESH_HANDLERS: list[tuple[str, Callable[[Settings | None], Any]]] = [
    ("source_reliability", build_and_write_source_reliability),
    ("historical_memory_completion", build_and_write_historical_memory_completion),
    ("market_confirmation", build_and_write_market_confirmation),
    ("phase5_to10_completion", build_and_write_phase5_to10_completion),
    ("phase11_to14_completion", build_and_write_phase11_to14_completion),
    ("dashboard_view_model", build_and_write_dashboard_view_model),
    ("git_deploy_readiness", build_and_write_git_deploy_readiness),
]


def _quarantine_records(runtime: Path, generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_records = _read_jsonl(runtime / SOURCE_RELIABILITY_RECORDS_ARTIFACT)
    quarantined: list[dict[str, Any]] = []
    for record in source_records:
        outage_state = str(record.get("outage_state") or "ok")
        freshness_state = str(record.get("freshness_state") or "unknown")
        quorum = _safe_dict(record.get("source_quorum_contribution"))
        can_contribute = quorum.get("can_contribute") is True
        should_quarantine = outage_state != "ok" or freshness_state in {"stale", "offline", "missing"}
        if not should_quarantine:
            continue
        quarantined.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_quarantine_record",
                "quarantine_record_id": _hash_id(
                    [record.get("source_key"), outage_state, freshness_state, generated_at],
                    "qadam-quarantine",
                ),
                "generated_at": generated_at,
                "source_key": record.get("source_key"),
                "source_name": record.get("source_name"),
                "source_category": record.get("source_category"),
                "outage_state": outage_state,
                "freshness_state": freshness_state,
                "reason": record.get("outage_reason") or quorum.get("reason") or "source_not_fit_for_quorum",
                "removed_from_quorum": True,
                "was_contributing_before_quarantine": can_contribute,
                "source_quorum_contribution_after_quarantine": False,
                "trade_candidate_creation_allowed": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            }
        )
    poison_count = sum(1 for record in quarantined if record["was_contributing_before_quarantine"])
    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_quarantine_state",
        "generated_at": generated_at,
        "status": "qadam_quarantine_ready",
        "quarantine_record_count": len(quarantined),
        "quorum_poison_prevented_count": poison_count,
        "source_quorum_protected": poison_count == 0,
        "records_path": _artifact_ref(REPAIR_REQUESTS_ARTIFACT),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "authority_flags": AUTHORITY_FLAGS,
        "boundary": "Quarantine removes degraded source records from quorum visibility. It does not change credentials, adapters, policies, candidates, or orders.",
    }
    return state, quarantined


def _repair_request(
    generated_at: str,
    defect_type: str,
    severity: str,
    summary: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_repair_request",
        "repair_request_id": _hash_id([defect_type, summary, json.dumps(evidence, sort_keys=True)], "qadam-repair"),
        "generated_at": generated_at,
        "defect_type": defect_type,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
        "state": "repair_requested",
        "autonomous_code_edit_allowed": False,
        "requires_explicit_implementation_workflow": True,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _build_repair_requests(
    runtime: Path,
    generated_at: str,
    refresh_records: list[dict[str, Any]],
    quarantine_state: dict[str, Any],
) -> list[dict[str, Any]]:
    source = _read_json(runtime / SOURCE_RELIABILITY_ARTIFACT)
    historical = _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT)
    akber = _read_json(runtime / AKBER_INPUT_COMPLETENESS_ARTIFACT)
    dashboard = _read_json(runtime / DASHBOARD_COMPLETION_ARTIFACT)
    lifecycle = _read_json(runtime / PAPER_LIFECYCLE_ARTIFACT)
    deploy = _read_json(runtime / GIT_DEPLOY_ARTIFACT)
    requests: list[dict[str, Any]] = []

    for refresh in refresh_records:
        if refresh.get("status") == "refresh_failed":
            requests.append(
                _repair_request(
                    generated_at,
                    "safe_refresh_failed",
                    "critical",
                    f"Safe refresh failed for {refresh.get('refresh_name')}",
                    {"error": refresh.get("error"), "refresh_name": refresh.get("refresh_name")},
                )
            )

    outage_count = _int(source.get("outage_count"), 0)
    if outage_count:
        requests.append(
            _repair_request(
                generated_at,
                "source_outage_quarantine",
                "high",
                f"{outage_count} source records are degraded or stale and were quarantined from quorum.",
                {
                    "source_reliability_status": source.get("status"),
                    "outage_count": outage_count,
                    "quarantine_record_count": quarantine_state.get("quarantine_record_count"),
                    "source_quorum_protected": quarantine_state.get("source_quorum_protected"),
                },
            )
        )

    missing_windows = _int(historical.get("missing_forward_window_count"), 0)
    if missing_windows and historical.get("operational_backtest_memory_passed") is not True:
        requests.append(
            _repair_request(
                generated_at,
                "historical_memory_backfill_required",
                "high",
                f"{missing_windows} source-price forward windows are still incomplete.",
                {
                    "historical_memory_status": historical.get("status"),
                    "complete_forward_window_count": historical.get("complete_forward_window_count"),
                    "missing_forward_window_count": missing_windows,
                    "target_complete_forward_window_passed": historical.get("target_complete_forward_window_passed"),
                },
            )
        )

    missing_context = _int(akber.get("akber_missing_context_count"), 0)
    if missing_context:
        requests.append(
            _repair_request(
                generated_at,
                "akber_input_context_missing",
                "medium",
                f"{missing_context} Akber input packets lack practical confirmation context.",
                {
                    "akber_input_status": akber.get("status"),
                    "missing_input_counts": akber.get("missing_input_counts"),
                    "complete_packet_count": akber.get("complete_packet_count"),
                    "incomplete_packet_count": akber.get("incomplete_packet_count"),
                },
            )
        )

    stale_labels = _int(dashboard.get("stale_labeled_count"), 0)
    if stale_labels:
        requests.append(
            _repair_request(
                generated_at,
                "dashboard_stale_label_review",
                "medium",
                f"{stale_labels} dashboard labels are explicitly stale and need source refresh or copy review.",
                {
                    "dashboard_completion_status": dashboard.get("status"),
                    "stale_labeled_count": stale_labels,
                    "anti_slop_error_count": dashboard.get("anti_slop_error_count"),
                },
            )
        )

    stale_orders = _int(lifecycle.get("stale_accepted_order_count"), 0)
    if stale_orders:
        requests.append(
            _repair_request(
                generated_at,
                "paper_order_lifecycle_review",
                "medium",
                f"{stale_orders} accepted paper order mirrors need lifecycle review.",
                {
                    "paper_lifecycle_status": lifecycle.get("status"),
                    "stale_accepted_order_count": stale_orders,
                    "ambiguous_lifecycle_count": lifecycle.get("ambiguous_lifecycle_count"),
                },
            )
        )

    if deploy and deploy.get("deployment_closure_passed") is not True:
        requests.append(
            _repair_request(
                generated_at,
                "deployment_closure_blocked",
                "medium",
                "Git or deployment closure is not clean.",
                {
                    "git_deploy_status": deploy.get("status"),
                    "blockers": _safe_list(deploy.get("blockers")),
                },
            )
        )

    return requests


def build_self_healing_state(settings: Settings | None = None, *, perform_refresh: bool = True) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    runtime = _runtime_dir(settings)
    generated_at = _iso(_now())
    refresh_records: list[dict[str, Any]] = []
    if perform_refresh:
        for name, handler in SAFE_REFRESH_HANDLERS:
            refresh_records.append(_run_refresh(name, generated_at, handler, settings))
    quarantine_state, quarantine_records = _quarantine_records(runtime, generated_at)
    repair_requests = _build_repair_requests(runtime, generated_at, refresh_records, quarantine_state)
    refresh_failure_count = sum(1 for record in refresh_records if record.get("status") == "refresh_failed")
    unsafe_action_count = 0
    self_healing_passed = refresh_failure_count == 0 and unsafe_action_count == 0
    if refresh_failure_count:
        status = "qadam_self_healing_needs_repair"
    elif repair_requests:
        status = "qadam_self_healing_ready_with_repair_requests"
    else:
        status = "qadam_self_healing_ready"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_state",
        "generated_at": generated_at,
        "status": status,
        "self_healing_passed": self_healing_passed,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "command_disabled": True,
        "authority": universal_authority_flags(),
        "authority_flags": AUTHORITY_FLAGS,
        "refresh_tier": {
            "enabled": perform_refresh,
            "refresh_action_count": len(refresh_records),
            "refresh_success_count": sum(1 for record in refresh_records if record.get("status") == "refresh_ok"),
            "refresh_failure_count": refresh_failure_count,
            "allowed_actions": [name for name, _handler in SAFE_REFRESH_HANDLERS],
        },
        "quarantine_tier": {
            "quarantine_record_count": quarantine_state.get("quarantine_record_count"),
            "source_quorum_protected": quarantine_state.get("source_quorum_protected"),
            "quorum_poison_prevented_count": quarantine_state.get("quorum_poison_prevented_count"),
            "quarantine_path": _artifact_ref(QUARANTINE_ARTIFACT),
        },
        "repair_request_tier": {
            "repair_request_count": len(repair_requests),
            "critical_repair_request_count": sum(1 for record in repair_requests if record.get("severity") == "critical"),
            "repair_requests_path": _artifact_ref(REPAIR_REQUESTS_ARTIFACT),
        },
        "refresh_records": refresh_records,
        "unsafe_action_count": unsafe_action_count,
        "autonomous_code_edit_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "boundary": "Self-healing can refresh safe local artifacts, quarantine degraded source records, and request repairs. It cannot edit code, mutate policy, create trades, send Telegram, write brokers, grant proof credit, or enable live capital.",
    }
    return payload, quarantine_state, quarantine_records, repair_requests


def validate_self_healing(payload: dict[str, Any], repair_requests: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qadam_self_healing_state":
        errors.append("artifact_type_mismatch")
    for field in ("public_safe", "read_only", "paper_only", "proposal_first", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{field}_must_not_be_true")
    if _int(payload.get("paper_order_created_count"), 0) != 0:
        errors.append("paper_order_created_count_must_be_zero")
    if _int(payload.get("broker_write_count"), 0) != 0:
        errors.append("broker_write_count_must_be_zero")
    if payload.get("proof_credit_allowed") is not False:
        errors.append("proof_credit_allowed_must_be_false")
    if payload.get("live_capital_enabled") is not False:
        errors.append("live_capital_enabled_must_be_false")
    for request in repair_requests:
        if not request.get("summary") or not request.get("defect_type"):
            errors.append("repair_request_missing_specificity")
        if request.get("autonomous_code_edit_allowed") is not False:
            errors.append("repair_request_autonomous_code_edit_allowed")
    return sorted(set(errors))


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_dashboard_summary",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "self_healing_passed": payload.get("self_healing_passed"),
        "refresh_success_count": _safe_dict(payload.get("refresh_tier")).get("refresh_success_count"),
        "refresh_failure_count": _safe_dict(payload.get("refresh_tier")).get("refresh_failure_count"),
        "quarantine_record_count": _safe_dict(payload.get("quarantine_tier")).get("quarantine_record_count"),
        "repair_request_count": _safe_dict(payload.get("repair_request_tier")).get("repair_request_count"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "live_capital_enabled": False,
    }


def _phase_record(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "Perfect Operation Phase 15: Self-Healing Operations",
        "status": payload.get("status"),
        "artifact_path": _artifact_ref(PRIMARY_ARTIFACT),
        "self_healing_passed": payload.get("self_healing_passed"),
        "refresh_success_count": _safe_dict(payload.get("refresh_tier")).get("refresh_success_count"),
        "refresh_failure_count": _safe_dict(payload.get("refresh_tier")).get("refresh_failure_count"),
        "quarantine_record_count": _safe_dict(payload.get("quarantine_tier")).get("quarantine_record_count"),
        "repair_request_count": _safe_dict(payload.get("repair_request_tier")).get("repair_request_count"),
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "proposal_first": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "live_capital_enabled": False,
    }


def _update_phase_status(path: Path, payload: dict[str, Any]) -> None:
    current = _read_json(path)
    phases = _safe_dict(current.get("phases"))
    phases["perfect_operation_phase_15_self_healing_operations"] = _phase_record(payload)
    safety = {
        **_safe_dict(current.get("safety")),
        "phase15_self_healing_outputs_are_review_only": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "telegram_command_path_enabled": False,
    }
    _write_json(
        path,
        {
            **current,
            "schema_version": current.get("schema_version", 1),
            "generated_at": payload.get("generated_at"),
            "active_phase": "perfect_operation_phase_15_self_healing_operations",
            "phases": phases,
            "safety": safety,
        },
    )


def build_and_write_self_healing_state(settings: Settings | None = None, *, perform_refresh: bool = True) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload, quarantine_state, quarantine_records, repair_requests = build_self_healing_state(settings, perform_refresh=perform_refresh)
    runtime = _runtime_dir(settings)
    written: dict[str, str] = {}
    _write_json(runtime / PRIMARY_ARTIFACT, payload)
    written["primary"] = str(runtime / PRIMARY_ARTIFACT)
    _write_json(
        runtime / QUARANTINE_ARTIFACT,
        {
            **quarantine_state,
            "records": quarantine_records,
        },
    )
    written["quarantine"] = str(runtime / QUARANTINE_ARTIFACT)
    _write_jsonl(runtime / REPAIR_REQUESTS_ARTIFACT, repair_requests)
    written["repair_requests"] = str(runtime / REPAIR_REQUESTS_ARTIFACT)
    _write_json(runtime / DASHBOARD_SUMMARY_ARTIFACT, _dashboard_summary(payload))
    written["dashboard_summary"] = str(runtime / DASHBOARD_SUMMARY_ARTIFACT)
    if perform_refresh:
        cockpit_refresh = _run_refresh("cockpit_status_export", str(payload.get("generated_at")), _refresh_cockpit_status, settings)
        payload["refresh_records"] = [*_safe_list(payload.get("refresh_records")), cockpit_refresh]
        refresh_tier = _safe_dict(payload.get("refresh_tier"))
        allowed_actions = [*_safe_list(refresh_tier.get("allowed_actions")), "cockpit_status_export"]
        refresh_records = _safe_list(payload.get("refresh_records"))
        refresh_failure_count = sum(1 for record in refresh_records if _safe_dict(record).get("status") == "refresh_failed")
        refresh_tier.update(
            {
                "allowed_actions": allowed_actions,
                "refresh_action_count": len(refresh_records),
                "refresh_success_count": sum(1 for record in refresh_records if _safe_dict(record).get("status") == "refresh_ok"),
                "refresh_failure_count": refresh_failure_count,
            }
        )
        payload["refresh_tier"] = refresh_tier
        if cockpit_refresh.get("status") == "refresh_failed":
            repair_requests.append(
                _repair_request(
                    str(payload.get("generated_at")),
                    "safe_refresh_failed",
                    "critical",
                    "Safe refresh failed for cockpit_status_export",
                    {"error": cockpit_refresh.get("error"), "refresh_name": "cockpit_status_export"},
                )
            )
        payload["self_healing_passed"] = refresh_failure_count == 0 and payload.get("unsafe_action_count") == 0
        if refresh_failure_count:
            payload["status"] = "qadam_self_healing_needs_repair"
        elif repair_requests:
            payload["status"] = "qadam_self_healing_ready_with_repair_requests"
        else:
            payload["status"] = "qadam_self_healing_ready"
        payload["repair_request_tier"] = {
            **_safe_dict(payload.get("repair_request_tier")),
            "repair_request_count": len(repair_requests),
            "critical_repair_request_count": sum(1 for record in repair_requests if record.get("severity") == "critical"),
            "repair_requests_path": _artifact_ref(REPAIR_REQUESTS_ARTIFACT),
        }
        _write_json(runtime / PRIMARY_ARTIFACT, payload)
        _write_jsonl(runtime / REPAIR_REQUESTS_ARTIFACT, repair_requests)
        _write_json(runtime / DASHBOARD_SUMMARY_ARTIFACT, _dashboard_summary(payload))
    event = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": "qadam_self_healing_state_written",
        "status": payload.get("status"),
        "self_healing_passed": payload.get("self_healing_passed"),
        "refresh_success_count": _safe_dict(payload.get("refresh_tier")).get("refresh_success_count"),
        "repair_request_count": len(repair_requests),
    }
    _append_jsonl(runtime / HISTORY_ARTIFACT, event)
    _append_jsonl(runtime / EVENTS_ARTIFACT, event)
    written["history"] = str(runtime / HISTORY_ARTIFACT)
    written["events"] = str(runtime / EVENTS_ARTIFACT)
    _update_phase_status(runtime / PHASE_STATUS_ARTIFACT, payload)
    written["phase_status"] = str(runtime / PHASE_STATUS_ARTIFACT)
    errors = validate_self_healing(payload, repair_requests)
    return payload, written, errors
