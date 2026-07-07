"""Qadam self-healing operations supervisor.

The supervisor is deliberately narrow: it can run known safe refresh builders,
quarantine degraded source records from quorum, and write repair requests. It
cannot edit code, mutate policy, create trades, submit orders, write to brokers,
send Telegram messages, grant proof credit, or enable live capital.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.cockpit_status import export_cockpit_status
from orchestrator.qadam_dashboard_vnext import build_and_write_dashboard_vnext
from orchestrator.qadam_git_deploy_readiness import build_and_write_git_deploy_readiness
from orchestrator.qadam_telegram_vnext import build_and_write_telegram_vnext
from orchestrator.qsase_dashboard_view_model import build_and_write_dashboard_view_model
from orchestrator.qsase_governance_safety_contract import universal_authority_flags
from orchestrator.qsase_historical_memory_completion import build_and_write_historical_memory_completion
from orchestrator.qsase_market_confirmation import build_and_write_market_confirmation
from orchestrator.qsase_phase11_to14_completion import build_and_write_phase11_to14_completion
from orchestrator.qsase_phase5_to10_completion import build_and_write_phase5_to10_completion
from orchestrator.qsase_source_reliability import build_and_write_source_reliability

SCHEMA_VERSION = "qadam_self_healing_supervisor.v1"
PHASE_ID = "qadam_next_generation_phase_14_self_healing_operations"

PRIMARY_ARTIFACT = "qadam_self_healing_state.json"
STATUS_ARTIFACT = "qadam_self_healing_status.json"
REPAIR_QUEUE_ARTIFACT = "qadam_self_healing_repair_queue.json"
QUARANTINE_ARTIFACT = "qadam_quarantine_state.json"
REPAIR_REQUESTS_ARTIFACT = "qadam_repair_requests.jsonl"
REFRESH_RETRY_POLICY_ARTIFACT = "qadam_self_healing_refresh_retry_policy.json"
PROVIDER_OUTAGES_ARTIFACT = "qadam_self_healing_provider_outages.json"
STALE_ARTIFACT_RECOVERY_ARTIFACT = "qadam_self_healing_stale_artifact_recovery.json"
BACKFILL_RESUME_ARTIFACT = "qadam_self_healing_backfill_resume.json"
CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT = "qadam_self_healing_code_defect_repair_requests.jsonl"
WHY_NOT_WORKING_ARTIFACT = "qadam_self_healing_why_not_working.json"
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
QADAM_NEXT_GENERATION_PHASE0_LOCK_ARTIFACT = "qadam_next_generation_phase0_safety_lock.json"
WHOLE_UNIVERSE_BACKFILL_STATE_ARTIFACT = "qsase_whole_universe_backfill_backtest_state.json"
WHOLE_UNIVERSE_BACKFILL_SUMMARY_ARTIFACT = "qsase_whole_universe_backfill_backtest_summary.json"
WHOLE_UNIVERSE_BACKFILL_DASHBOARD_ARTIFACT = "qsase_whole_universe_backfill_backtest_dashboard_summary.json"
QADAM_DASHBOARD_VNEXT_ARTIFACT = "qadam_dashboard_vnext_dashboard_summary.json"
QADAM_TELEGRAM_VNEXT_ARTIFACT = "qadam_telegram_vnext_dashboard_summary.json"
QSASE_DASHBOARD_STATUS_ARTIFACT = "qsase_dashboard_status.json"

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
ZERO_AUTHORITY_FIELDS = {key for key, value in AUTHORITY_FLAGS.items() if type(value) is int and value == 0}


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


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _refreshable_artifacts() -> set[str]:
    return {
        SOURCE_RELIABILITY_ARTIFACT,
        HISTORICAL_MEMORY_ARTIFACT,
        AKBER_INPUT_COMPLETENESS_ARTIFACT,
        DASHBOARD_COMPLETION_ARTIFACT,
        PAPER_LIFECYCLE_ARTIFACT,
        GIT_DEPLOY_ARTIFACT,
        QADAM_DASHBOARD_VNEXT_ARTIFACT,
        QADAM_TELEGRAM_VNEXT_ARTIFACT,
        QSASE_DASHBOARD_STATUS_ARTIFACT,
    }


def _artifact_freshness(runtime: Path, filename: str, generated_at: str, *, stale_after_seconds: int = 7200) -> dict[str, Any]:
    path = runtime / filename
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact": _artifact_ref(filename),
            "exists": False,
            "generated_at": None,
            "age_seconds": None,
            "stale_after_seconds": stale_after_seconds,
            "freshness_state": "missing",
            "recoverable_by_safe_refresh": filename in _refreshable_artifacts(),
        }
    payload = _read_json(path)
    observed = _parse_timestamp(payload.get("generated_at")) or datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    reference = _parse_timestamp(generated_at) or _now()
    age_seconds = max(0, int((reference - observed).total_seconds()))
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": _artifact_ref(filename),
        "exists": True,
        "generated_at": payload.get("generated_at"),
        "mtime": _iso(datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)),
        "age_seconds": age_seconds,
        "stale_after_seconds": stale_after_seconds,
        "freshness_state": "fresh" if age_seconds <= stale_after_seconds else "stale",
        "recoverable_by_safe_refresh": filename in _refreshable_artifacts(),
    }


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
    ("dashboard_vnext", build_and_write_dashboard_vnext),
    ("telegram_vnext", build_and_write_telegram_vnext),
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


def _monitored_artifacts() -> list[tuple[str, str, int]]:
    return [
        (SOURCE_RELIABILITY_ARTIFACT, "source_reliability", 7200),
        (HISTORICAL_MEMORY_ARTIFACT, "historical_memory", 7200),
        (AKBER_INPUT_COMPLETENESS_ARTIFACT, "akber_context", 7200),
        (DASHBOARD_COMPLETION_ARTIFACT, "dashboard_completion", 7200),
        (PAPER_LIFECYCLE_ARTIFACT, "paper_lifecycle", 7200),
        (GIT_DEPLOY_ARTIFACT, "deploy_hygiene", 7200),
        (QADAM_DASHBOARD_VNEXT_ARTIFACT, "dashboard_vnext", 7200),
        (QADAM_TELEGRAM_VNEXT_ARTIFACT, "telegram_vnext", 7200),
        (QSASE_DASHBOARD_STATUS_ARTIFACT, "public_dashboard_status", 7200),
        (WHOLE_UNIVERSE_BACKFILL_STATE_ARTIFACT, "whole_universe_backfill", 21600),
        (WHOLE_UNIVERSE_BACKFILL_SUMMARY_ARTIFACT, "whole_universe_backfill", 21600),
        (QADAM_NEXT_GENERATION_PHASE0_LOCK_ARTIFACT, "safety_lock", 21600),
    ]


def _artifact_refresh_name(filename: str) -> str | None:
    return {
        SOURCE_RELIABILITY_ARTIFACT: "source_reliability",
        HISTORICAL_MEMORY_ARTIFACT: "historical_memory_completion",
        AKBER_INPUT_COMPLETENESS_ARTIFACT: "phase5_to10_completion",
        DASHBOARD_COMPLETION_ARTIFACT: "phase11_to14_completion",
        PAPER_LIFECYCLE_ARTIFACT: "phase11_to14_completion",
        GIT_DEPLOY_ARTIFACT: "git_deploy_readiness",
        QADAM_DASHBOARD_VNEXT_ARTIFACT: "dashboard_vnext",
        QADAM_TELEGRAM_VNEXT_ARTIFACT: "telegram_vnext",
        QSASE_DASHBOARD_STATUS_ARTIFACT: "dashboard_view_model",
    }.get(filename)


def _build_refresh_retry_policy(runtime: Path, generated_at: str, refresh_records: list[dict[str, Any]]) -> dict[str, Any]:
    refresh_by_name = {str(record.get("refresh_name")): record for record in refresh_records}
    artifact_records: list[dict[str, Any]] = []
    for filename, category, stale_after in _monitored_artifacts():
        freshness = _artifact_freshness(runtime, filename, generated_at, stale_after_seconds=stale_after)
        refresh_name = _artifact_refresh_name(filename)
        refresh_record = refresh_by_name.get(str(refresh_name))
        state = freshness["freshness_state"]
        retry_state = "not_needed"
        if state in {"missing", "stale"} and refresh_name:
            retry_state = "safe_retry_succeeded" if _safe_dict(refresh_record).get("status") == "refresh_ok" else "safe_retry_requested"
        elif state in {"missing", "stale"}:
            retry_state = "manual_repair_request_required"
        artifact_records.append(
            {
                **freshness,
                "artifact_category": category,
                "safe_refresh_name": refresh_name,
                "retry_state": retry_state,
                "retry_attempted_this_pass": bool(refresh_record),
                "retry_result": _safe_dict(refresh_record).get("status"),
                "code_edit_allowed": False,
                "secret_change_allowed": False,
                "authority_change_allowed": False,
            }
        )
    stale_or_missing = [record for record in artifact_records if record["freshness_state"] in {"missing", "stale"}]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_refresh_retry_policy",
        "generated_at": generated_at,
        "status": "refresh_retry_policy_ready",
        "safe_refresh_only": True,
        "max_attempts_per_pass": 1,
        "requires_validation_after_retry": True,
        "refresh_action_count": len(refresh_records),
        "refresh_success_count": sum(1 for record in refresh_records if record.get("status") == "refresh_ok"),
        "refresh_failure_count": sum(1 for record in refresh_records if record.get("status") == "refresh_failed"),
        "stale_or_missing_artifact_count": len(stale_or_missing),
        "artifact_records": artifact_records,
        "allowed_refreshes": [name for name, _handler in SAFE_REFRESH_HANDLERS] + ["cockpit_status_export"],
        "prohibited_actions": [
            "silent_code_edit",
            "secret_edit",
            "test_bypass",
            "authority_change",
            "broker_write",
            "paper_order",
            "proof_credit",
            "live_capital_enablement",
        ],
        "authority_flags": AUTHORITY_FLAGS,
    }


def _classify_provider_outages(runtime: Path, generated_at: str) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for source in _read_jsonl(runtime / SOURCE_RELIABILITY_RECORDS_ARTIFACT):
        outage_state = str(source.get("outage_state") or "ok")
        freshness_state = str(source.get("freshness_state") or "unknown")
        adapter_status = str(source.get("adapter_status") or "unknown")
        credential_status = str(source.get("credential_status") or "unknown")
        outage_reason = str(source.get("outage_reason") or "")
        impaired = (
            outage_state != "ok"
            or freshness_state in {"stale", "offline", "missing"}
            or adapter_status in {"offline", "not_seen_in_current_cycle", "error"}
        )
        if not impaired:
            continue
        if "credential" in credential_status or "credential" in outage_reason:
            classification = "credential_or_permission_blocked"
        elif freshness_state == "stale":
            classification = "stale_provider_data"
        elif freshness_state in {"offline", "missing"} or adapter_status in {"offline", "not_seen_in_current_cycle", "error"}:
            classification = "provider_or_adapter_offline"
        else:
            classification = "provider_degraded"
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_self_healing_provider_outage",
                "provider_outage_id": _hash_id(
                    [source.get("source_key"), classification, freshness_state, outage_state],
                    "qadam-provider-outage",
                ),
                "generated_at": generated_at,
                "source_key": source.get("source_key"),
                "source_name": source.get("source_name"),
                "source_category": source.get("source_category"),
                "classification": classification,
                "outage_state": outage_state,
                "freshness_state": freshness_state,
                "adapter_status": adapter_status,
                "credential_status": credential_status,
                "outage_reason": outage_reason or "not recorded",
                "source_quorum_contribution_allowed": False,
                "safe_refresh_allowed": True,
                "manual_secret_change_allowed": False,
                "trade_candidate_creation_allowed": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
                "live_capital_enabled": False,
            }
        )
    counts = Counter(record["classification"] for record in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_provider_outages",
        "generated_at": generated_at,
        "status": "provider_outage_classification_ready",
        "provider_outage_count": len(records),
        "classification_counts": dict(sorted(counts.items())),
        "records": records,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "authority_flags": AUTHORITY_FLAGS,
    }


def _build_stale_artifact_recovery(refresh_policy: dict[str, Any], generated_at: str) -> dict[str, Any]:
    recovery_records: list[dict[str, Any]] = []
    for artifact in _safe_list(refresh_policy.get("artifact_records")):
        if _safe_dict(artifact).get("freshness_state") not in {"missing", "stale"}:
            continue
        retry_state = _safe_dict(artifact).get("retry_state")
        if retry_state == "safe_retry_succeeded":
            recovery_state = "safe_refresh_attempted_verify_next_pass"
        elif retry_state == "safe_retry_requested":
            recovery_state = "safe_refresh_requested"
        else:
            recovery_state = "repair_request_required"
        recovery_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_self_healing_stale_artifact_recovery_record",
                "recovery_record_id": _hash_id(
                    [artifact.get("artifact"), artifact.get("freshness_state"), recovery_state],
                    "qadam-stale-recovery",
                ),
                "generated_at": generated_at,
                "artifact": artifact.get("artifact"),
                "artifact_category": artifact.get("artifact_category"),
                "freshness_state": artifact.get("freshness_state"),
                "age_seconds": artifact.get("age_seconds"),
                "safe_refresh_name": artifact.get("safe_refresh_name"),
                "retry_attempted_this_pass": artifact.get("retry_attempted_this_pass"),
                "retry_result": artifact.get("retry_result"),
                "recovery_state": recovery_state,
                "next_action": "verify artifact freshness on the next pass" if recovery_state.startswith("safe_refresh_attempted") else "queue repair request",
                "code_edit_allowed": False,
                "secret_change_allowed": False,
                "test_bypass_allowed": False,
                "authority_change_allowed": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_stale_artifact_recovery",
        "generated_at": generated_at,
        "status": "stale_artifact_recovery_ready",
        "stale_or_missing_artifact_count": len(recovery_records),
        "safe_retry_attempted_count": sum(1 for record in recovery_records if record.get("retry_attempted_this_pass")),
        "repair_required_count": sum(1 for record in recovery_records if record.get("recovery_state") == "repair_request_required"),
        "records": recovery_records,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "authority_flags": AUTHORITY_FLAGS,
    }


def _build_backfill_resume_state(runtime: Path, generated_at: str) -> dict[str, Any]:
    state = _read_json(runtime / WHOLE_UNIVERSE_BACKFILL_STATE_ARTIFACT)
    summary = _read_json(runtime / WHOLE_UNIVERSE_BACKFILL_SUMMARY_ARTIFACT)
    lock = _read_json(runtime / QADAM_NEXT_GENERATION_PHASE0_LOCK_ARTIFACT)
    pending_count = _int(state.get("pending_job_count"), 0)
    failed_count = _int(state.get("failed_job_count"), 0)
    current_job_id = state.get("current_job_id")
    safe_to_resume = state.get("safe_to_resume") is True
    interrupted = pending_count > 0 or failed_count > 0 or bool(current_job_id)
    if interrupted and safe_to_resume:
        status = "backfill_resume_available_review_only"
        next_action = "operator may run the documented resume command"
    elif state.get("status") in {"complete_with_provider_gaps", "complete"}:
        status = "backfill_resume_not_required_baseline_complete"
        next_action = "no resume needed unless new provider data appears"
    else:
        status = "backfill_resume_blocked_or_not_required"
        next_action = "review state before any resume"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_backfill_resume",
        "generated_at": generated_at,
        "status": status,
        "interrupted_backfill_detected": interrupted,
        "safe_to_resume": safe_to_resume,
        "resume_executed": False,
        "resume_command_proposal": ".venv/bin/python scripts/run_qsase_whole_universe_backfill_backtest.py --resume --max-runtime-hours 120",
        "next_action": next_action,
        "backfill_state_status": state.get("status"),
        "backfill_summary_status": summary.get("status"),
        "pending_job_count": pending_count,
        "failed_job_count": failed_count,
        "current_job_id": current_job_id,
        "complete_forward_window_count": summary.get("complete_forward_window_count"),
        "missing_forward_window_count": summary.get("missing_forward_window_count"),
        "long_backtest_lock_active": lock.get("long_backtest_lock_active") is True,
        "paperops_watch_only_mode": lock.get("paperops_watch_only_mode") is True,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "authority_flags": AUTHORITY_FLAGS,
    }


def _code_defect_request(generated_at: str, defect_type: str, severity: str, summary: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_code_defect_repair_request",
        "code_defect_repair_request_id": _hash_id([defect_type, summary, json.dumps(evidence, sort_keys=True)], "qadam-code-defect"),
        "generated_at": generated_at,
        "defect_type": defect_type,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
        "state": "repair_requested",
        "self_healing_may_edit_code": False,
        "requires_explicit_development_workflow": True,
        "tests_required_before_claiming_fixed": True,
        "secret_change_allowed": False,
        "authority_change_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _build_code_defect_repair_requests(runtime: Path, generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    safety_lock = _read_json(runtime / QADAM_NEXT_GENERATION_PHASE0_LOCK_ARTIFACT)
    dashboard = _read_json(runtime / QADAM_DASHBOARD_VNEXT_ARTIFACT)
    telegram = _read_json(runtime / QADAM_TELEGRAM_VNEXT_ARTIFACT)
    anti_slop = _read_json(runtime / "qsase_dashboard_anti_slop_audit.json")
    validation_errors = _safe_list(safety_lock.get("validation_errors"))
    if validation_errors:
        records.append(
            _code_defect_request(
                generated_at,
                "safety_lock_validation_error",
                "critical",
                "Safety lock validation errors require explicit code repair.",
                {"validation_errors": validation_errors},
            )
        )
    if dashboard and (
        dashboard.get("protected_sections_not_reordered") is False
        or dashboard.get("protected_sections_not_renamed") is False
        or dashboard.get("protected_sections_not_removed") is False
        or dashboard.get("protected_sections_not_structurally_overhauled") is False
    ):
        records.append(
            _code_defect_request(
                generated_at,
                "dashboard_protected_section_contract_breach",
                "critical",
                "Protected dashboard sections were changed outside the allowed enrichment boundary.",
                {
                    "protected_sections_not_reordered": dashboard.get("protected_sections_not_reordered"),
                    "protected_sections_not_renamed": dashboard.get("protected_sections_not_renamed"),
                    "protected_sections_not_removed": dashboard.get("protected_sections_not_removed"),
                    "protected_sections_not_structurally_overhauled": dashboard.get("protected_sections_not_structurally_overhauled"),
                },
            )
        )
    if _int(anti_slop.get("error_count"), 0) > 0:
        records.append(
            _code_defect_request(
                generated_at,
                "dashboard_anti_slop_failure",
                "medium",
                "Dashboard anti-slop checks found copy or duplication defects.",
                {"anti_slop_error_count": anti_slop.get("error_count"), "errors": anti_slop.get("errors")},
            )
        )
    if _int(telegram.get("message_rejected_quality_count"), 0) or _int(telegram.get("message_rejected_unsafe_count"), 0):
        records.append(
            _code_defect_request(
                generated_at,
                "telegram_vnext_message_quality_defect",
                "medium",
                "Telegram VNext produced quality or safety rejects that require copy repair.",
                {
                    "message_rejected_quality_count": telegram.get("message_rejected_quality_count"),
                    "message_rejected_unsafe_count": telegram.get("message_rejected_unsafe_count"),
                },
            )
        )
    return records


def _repair_queue_entry_from_request(request: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_repair_queue_entry",
        "repair_queue_id": request.get("repair_request_id") or request.get("code_defect_repair_request_id") or _hash_id(
            [source, request.get("defect_type"), request.get("summary")],
            "qadam-repair-queue",
        ),
        "source": source,
        "defect_type": request.get("defect_type"),
        "severity": request.get("severity", "medium"),
        "summary": request.get("summary"),
        "state": request.get("state", "repair_requested"),
        "evidence": request.get("evidence", {}),
        "allowed_self_healing_action": "safe_refresh_or_request_only",
        "prohibited_actions": [
            "silent_code_edit",
            "secret_change",
            "test_bypass",
            "authority_change",
            "paper_order",
            "broker_write",
            "proof_credit",
            "live_capital_enablement",
        ],
        "requires_explicit_development_workflow": request.get("requires_explicit_development_workflow", False)
        or request.get("requires_explicit_implementation_workflow", False),
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _build_repair_queue(
    generated_at: str,
    repair_requests: list[dict[str, Any]],
    code_defects: list[dict[str, Any]],
    provider_outages: dict[str, Any],
    stale_recovery: dict[str, Any],
    backfill_resume: dict[str, Any],
) -> dict[str, Any]:
    entries = [_repair_queue_entry_from_request(request, "repair_request") for request in repair_requests]
    entries.extend(_repair_queue_entry_from_request(request, "code_defect") for request in code_defects)
    for outage in _safe_list(provider_outages.get("records")):
        entries.append(
            _repair_queue_entry_from_request(
                _repair_request(
                    generated_at,
                    "provider_outage",
                    "high" if outage.get("classification") != "stale_provider_data" else "medium",
                    f"{outage.get('source_name') or outage.get('source_key')} is {outage.get('classification')}.",
                    outage,
                ),
                "provider_outage",
            )
        )
    for recovery in _safe_list(stale_recovery.get("records")):
        if recovery.get("recovery_state") == "safe_refresh_attempted_verify_next_pass":
            continue
        entries.append(
            _repair_queue_entry_from_request(
                _repair_request(
                    generated_at,
                    "stale_artifact_recovery",
                    "medium",
                    f"{recovery.get('artifact')} needs stale-artifact recovery.",
                    recovery,
                ),
                "stale_artifact_recovery",
            )
        )
    if backfill_resume.get("interrupted_backfill_detected") is True and backfill_resume.get("safe_to_resume") is True:
        entries.append(
            _repair_queue_entry_from_request(
                _repair_request(
                    generated_at,
                    "interrupted_backfill_resume_available",
                    "medium",
                    "Whole-universe backfill can be resumed by the documented operator command.",
                    backfill_resume,
                ),
                "backfill_resume",
            )
        )
    counts = Counter(entry.get("severity", "medium") for entry in entries)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_repair_queue",
        "generated_at": generated_at,
        "status": "repair_queue_ready",
        "repair_queue_count": len(entries),
        "critical_repair_queue_count": counts.get("critical", 0),
        "high_repair_queue_count": counts.get("high", 0),
        "medium_repair_queue_count": counts.get("medium", 0),
        "entries": entries,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "code_edit_allowed": False,
        "secret_change_allowed": False,
        "test_bypass_allowed": False,
        "authority_change_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority_flags": AUTHORITY_FLAGS,
    }


def _build_why_not_working(payload: dict[str, Any]) -> dict[str, Any]:
    refresh_tier = _safe_dict(payload.get("refresh_tier"))
    repair_queue_tier = _safe_dict(payload.get("repair_queue_tier"))
    provider_outages = _safe_dict(payload.get("provider_outage_classification"))
    stale_recovery = _safe_dict(payload.get("stale_artifact_recovery"))
    backfill_resume = _safe_dict(payload.get("backfill_resume"))
    refresh_failure_count = _int(refresh_tier.get("refresh_failure_count"), 0)
    repair_queue_count = _int(repair_queue_tier.get("repair_queue_count"), 0)
    critical_count = _int(repair_queue_tier.get("critical_repair_queue_count"), 0)
    if refresh_failure_count:
        state = "safe_refresh_failed"
        reason = "One or more safe refreshes failed and explicit repair is required."
    elif critical_count:
        state = "critical_repair_requested"
        reason = "A critical repair request exists and must be handled by an explicit development workflow."
    elif repair_queue_count:
        state = "running_with_repair_queue"
        reason = "Qadam is running, but self-healing found items that require safe refresh verification or explicit repair."
    else:
        state = "no_self_healing_blocker_detected"
        reason = "No self-healing blocker was detected in this pass."
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_why_not_working",
        "generated_at": payload.get("generated_at"),
        "status": state,
        "plain_english_reason": reason,
        "safe_refresh_failure_count": refresh_failure_count,
        "repair_queue_count": repair_queue_count,
        "critical_repair_queue_count": critical_count,
        "provider_outage_count": provider_outages.get("provider_outage_count"),
        "stale_or_missing_artifact_count": stale_recovery.get("stale_or_missing_artifact_count"),
        "backfill_resume_status": backfill_resume.get("status"),
        "self_healing_may_retry_safe_refreshes": True,
        "self_healing_may_write_repair_requests": True,
        "self_healing_may_edit_code": False,
        "secret_change_allowed": False,
        "test_bypass_allowed": False,
        "authority_change_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "authority_flags": AUTHORITY_FLAGS,
    }


def _attach_phase14_diagnostics(
    payload: dict[str, Any],
    runtime: Path,
    repair_requests: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    generated_at = str(payload.get("generated_at"))
    refresh_records = [_safe_dict(record) for record in _safe_list(payload.get("refresh_records"))]
    refresh_retry_policy = _build_refresh_retry_policy(runtime, generated_at, refresh_records)
    provider_outages = _classify_provider_outages(runtime, generated_at)
    stale_artifact_recovery = _build_stale_artifact_recovery(refresh_retry_policy, generated_at)
    backfill_resume = _build_backfill_resume_state(runtime, generated_at)
    code_defects = _build_code_defect_repair_requests(runtime, generated_at)
    repair_queue = _build_repair_queue(
        generated_at,
        repair_requests,
        code_defects,
        provider_outages,
        stale_artifact_recovery,
        backfill_resume,
    )
    refresh_tier = _safe_dict(payload.get("refresh_tier"))
    refresh_failure_count = _int(refresh_tier.get("refresh_failure_count"), 0)
    unsafe_action_count = _int(payload.get("unsafe_action_count"), 0)
    repair_queue_count = _int(repair_queue.get("repair_queue_count"), 0)
    if refresh_failure_count:
        status = "qadam_self_healing_needs_repair"
    elif repair_queue_count:
        status = "qadam_self_healing_ready_with_repair_requests"
    else:
        status = "qadam_self_healing_ready"
    payload.update(
        {
            "phase_id": PHASE_ID,
            "status": status,
            "self_healing_passed": refresh_failure_count == 0 and unsafe_action_count == 0,
            "self_healing_status_path": _artifact_ref(STATUS_ARTIFACT),
            "repair_queue_path": _artifact_ref(REPAIR_QUEUE_ARTIFACT),
            "refresh_retry_policy_path": _artifact_ref(REFRESH_RETRY_POLICY_ARTIFACT),
            "provider_outage_classification_path": _artifact_ref(PROVIDER_OUTAGES_ARTIFACT),
            "stale_artifact_recovery_path": _artifact_ref(STALE_ARTIFACT_RECOVERY_ARTIFACT),
            "backfill_resume_path": _artifact_ref(BACKFILL_RESUME_ARTIFACT),
            "code_defect_repair_requests_path": _artifact_ref(CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT),
            "why_not_working_path": _artifact_ref(WHY_NOT_WORKING_ARTIFACT),
            "refresh_retry_policy": refresh_retry_policy,
            "provider_outage_classification": provider_outages,
            "stale_artifact_recovery": stale_artifact_recovery,
            "backfill_resume": backfill_resume,
            "code_defect_repair_requests": code_defects,
            "code_defect_repair_request_count": len(code_defects),
            "repair_queue": repair_queue,
            "repair_queue_tier": {
                "repair_queue_count": repair_queue_count,
                "critical_repair_queue_count": repair_queue.get("critical_repair_queue_count"),
                "high_repair_queue_count": repair_queue.get("high_repair_queue_count"),
                "medium_repair_queue_count": repair_queue.get("medium_repair_queue_count"),
                "repair_queue_path": _artifact_ref(REPAIR_QUEUE_ARTIFACT),
            },
            "safe_refresh_only": True,
            "code_edit_allowed": False,
            "secret_change_allowed": False,
            "test_bypass_allowed": False,
            "authority_change_allowed": False,
        }
    )
    why_not_working = _build_why_not_working(payload)
    payload["why_not_working"] = why_not_working
    return code_defects, repair_queue, why_not_working


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
    _attach_phase14_diagnostics(payload, runtime, repair_requests)
    return payload, quarantine_state, quarantine_records, repair_requests


def validate_self_healing(payload: dict[str, Any], repair_requests: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qadam_self_healing_state":
        errors.append("artifact_type_mismatch")
    if payload.get("phase_id") != PHASE_ID:
        errors.append("phase_id_mismatch")
    for field in ("public_safe", "read_only", "paper_only", "proposal_first", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{field}_must_not_be_true")
    for field in ZERO_AUTHORITY_FIELDS:
        if _int(payload.get(field), 0) != 0:
            errors.append(f"{field}_must_be_zero")
    if payload.get("safe_refresh_only") is not True:
        errors.append("safe_refresh_only_must_be_true")
    for field in ("code_edit_allowed", "secret_change_allowed", "test_bypass_allowed", "authority_change_allowed"):
        if payload.get(field) is not False:
            errors.append(f"{field}_must_be_false")
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
    retry_policy = _safe_dict(payload.get("refresh_retry_policy"))
    if retry_policy.get("safe_refresh_only") is not True:
        errors.append("refresh_retry_policy_not_safe_refresh_only")
    backfill_resume = _safe_dict(payload.get("backfill_resume"))
    if backfill_resume.get("resume_executed") is not False:
        errors.append("backfill_resume_must_not_execute")
    repair_queue = _safe_dict(payload.get("repair_queue"))
    repair_queue_tier = _safe_dict(payload.get("repair_queue_tier"))
    if _int(repair_queue.get("repair_queue_count"), 0) != _int(repair_queue_tier.get("repair_queue_count"), 0):
        errors.append("repair_queue_count_mismatch")
    for request in _safe_list(payload.get("code_defect_repair_requests")):
        code_defect = _safe_dict(request)
        if code_defect.get("self_healing_may_edit_code") is not False:
            errors.append("code_defect_self_healing_may_edit_code")
        if code_defect.get("secret_change_allowed") is not False:
            errors.append("code_defect_secret_change_allowed")
        if code_defect.get("authority_change_allowed") is not False:
            errors.append("code_defect_authority_change_allowed")
    for entry in _safe_list(repair_queue.get("entries")):
        queue_entry = _safe_dict(entry)
        if queue_entry.get("paper_order_allowed") is not False:
            errors.append("repair_queue_paper_order_allowed")
        if queue_entry.get("broker_write_allowed") is not False:
            errors.append("repair_queue_broker_write_allowed")
        if queue_entry.get("live_capital_enabled") is not False:
            errors.append("repair_queue_live_capital_enabled")
    why_not_working = _safe_dict(payload.get("why_not_working"))
    if why_not_working.get("self_healing_may_edit_code") is not False:
        errors.append("why_not_working_self_healing_may_edit_code")
    return sorted(set(errors))


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    repair_queue_tier = _safe_dict(payload.get("repair_queue_tier"))
    provider_outages = _safe_dict(payload.get("provider_outage_classification"))
    stale_recovery = _safe_dict(payload.get("stale_artifact_recovery"))
    backfill_resume = _safe_dict(payload.get("backfill_resume"))
    why_not_working = _safe_dict(payload.get("why_not_working"))
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_self_healing_dashboard_summary",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "phase_id": payload.get("phase_id"),
        "self_healing_passed": payload.get("self_healing_passed"),
        "refresh_success_count": _safe_dict(payload.get("refresh_tier")).get("refresh_success_count"),
        "refresh_failure_count": _safe_dict(payload.get("refresh_tier")).get("refresh_failure_count"),
        "quarantine_record_count": _safe_dict(payload.get("quarantine_tier")).get("quarantine_record_count"),
        "repair_request_count": _safe_dict(payload.get("repair_request_tier")).get("repair_request_count"),
        "repair_queue_count": repair_queue_tier.get("repair_queue_count"),
        "critical_repair_queue_count": repair_queue_tier.get("critical_repair_queue_count"),
        "provider_outage_count": provider_outages.get("provider_outage_count"),
        "stale_or_missing_artifact_count": stale_recovery.get("stale_or_missing_artifact_count"),
        "safe_retry_attempted_count": stale_recovery.get("safe_retry_attempted_count"),
        "backfill_resume_status": backfill_resume.get("status"),
        "why_not_working_status": why_not_working.get("status"),
        "plain_english_reason": why_not_working.get("plain_english_reason"),
        "safe_refresh_only": True,
        "code_edit_allowed": False,
        "secret_change_allowed": False,
        "test_bypass_allowed": False,
        "authority_change_allowed": False,
        "repair_queue_path": _artifact_ref(REPAIR_QUEUE_ARTIFACT),
        "refresh_retry_policy_path": _artifact_ref(REFRESH_RETRY_POLICY_ARTIFACT),
        "provider_outages_path": _artifact_ref(PROVIDER_OUTAGES_ARTIFACT),
        "stale_artifact_recovery_path": _artifact_ref(STALE_ARTIFACT_RECOVERY_ARTIFACT),
        "backfill_resume_path": _artifact_ref(BACKFILL_RESUME_ARTIFACT),
        "code_defect_repair_requests_path": _artifact_ref(CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT),
        "why_not_working_path": _artifact_ref(WHY_NOT_WORKING_ARTIFACT),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _phase_record(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "Next-Generation Phase 14: Self-Healing Operations",
        "status": payload.get("status"),
        "artifact_path": _artifact_ref(PRIMARY_ARTIFACT),
        "status_artifact_path": _artifact_ref(STATUS_ARTIFACT),
        "repair_queue_path": _artifact_ref(REPAIR_QUEUE_ARTIFACT),
        "self_healing_passed": payload.get("self_healing_passed"),
        "refresh_success_count": _safe_dict(payload.get("refresh_tier")).get("refresh_success_count"),
        "refresh_failure_count": _safe_dict(payload.get("refresh_tier")).get("refresh_failure_count"),
        "quarantine_record_count": _safe_dict(payload.get("quarantine_tier")).get("quarantine_record_count"),
        "repair_request_count": _safe_dict(payload.get("repair_request_tier")).get("repair_request_count"),
        "repair_queue_count": _safe_dict(payload.get("repair_queue_tier")).get("repair_queue_count"),
        "provider_outage_count": _safe_dict(payload.get("provider_outage_classification")).get("provider_outage_count"),
        "stale_or_missing_artifact_count": _safe_dict(payload.get("stale_artifact_recovery")).get("stale_or_missing_artifact_count"),
        "backfill_resume_status": _safe_dict(payload.get("backfill_resume")).get("status"),
        "safe_refresh_only": True,
        "paper_only": True,
        "public_safe": True,
        "read_only": True,
        "proposal_first": True,
        "code_edit_allowed": False,
        "secret_change_allowed": False,
        "test_bypass_allowed": False,
        "authority_change_allowed": False,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "live_capital_enabled": False,
    }


def _update_phase_status(path: Path, payload: dict[str, Any]) -> None:
    current = _read_json(path)
    phases = _safe_dict(current.get("phases"))
    phase_record = _phase_record(payload)
    phases[PHASE_ID] = phase_record
    phases["perfect_operation_phase_15_self_healing_operations"] = {
        **phase_record,
        "superseded_by": PHASE_ID,
    }
    safety = {
        **_safe_dict(current.get("safety")),
        "phase14_self_healing_outputs_are_review_only": True,
        "phase14_self_healing_safe_refresh_only": True,
        "phase14_self_healing_code_edit_allowed": False,
        "phase14_self_healing_secret_change_allowed": False,
        "phase14_self_healing_test_bypass_allowed": False,
        "phase14_self_healing_authority_change_allowed": False,
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
            "active_phase": PHASE_ID,
            "phases": phases,
            "safety": safety,
        },
    )


def _status_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "artifact_type": "qadam_self_healing_status",
        "primary_artifact_path": _artifact_ref(PRIMARY_ARTIFACT),
    }


def _write_phase14_artifacts(
    runtime: Path,
    payload: dict[str, Any],
    repair_requests: list[dict[str, Any]],
    written: dict[str, str],
) -> None:
    _write_json(runtime / PRIMARY_ARTIFACT, payload)
    written["primary"] = str(runtime / PRIMARY_ARTIFACT)
    _write_json(runtime / STATUS_ARTIFACT, _status_payload(payload))
    written["status"] = str(runtime / STATUS_ARTIFACT)
    _write_json(runtime / REPAIR_QUEUE_ARTIFACT, _safe_dict(payload.get("repair_queue")))
    written["repair_queue"] = str(runtime / REPAIR_QUEUE_ARTIFACT)
    _write_json(runtime / REFRESH_RETRY_POLICY_ARTIFACT, _safe_dict(payload.get("refresh_retry_policy")))
    written["refresh_retry_policy"] = str(runtime / REFRESH_RETRY_POLICY_ARTIFACT)
    _write_json(runtime / PROVIDER_OUTAGES_ARTIFACT, _safe_dict(payload.get("provider_outage_classification")))
    written["provider_outages"] = str(runtime / PROVIDER_OUTAGES_ARTIFACT)
    _write_json(runtime / STALE_ARTIFACT_RECOVERY_ARTIFACT, _safe_dict(payload.get("stale_artifact_recovery")))
    written["stale_artifact_recovery"] = str(runtime / STALE_ARTIFACT_RECOVERY_ARTIFACT)
    _write_json(runtime / BACKFILL_RESUME_ARTIFACT, _safe_dict(payload.get("backfill_resume")))
    written["backfill_resume"] = str(runtime / BACKFILL_RESUME_ARTIFACT)
    _write_jsonl(runtime / CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT, _safe_list(payload.get("code_defect_repair_requests")))
    written["code_defect_repair_requests"] = str(runtime / CODE_DEFECT_REPAIR_REQUESTS_ARTIFACT)
    _write_json(runtime / WHY_NOT_WORKING_ARTIFACT, _safe_dict(payload.get("why_not_working")))
    written["why_not_working"] = str(runtime / WHY_NOT_WORKING_ARTIFACT)
    _write_jsonl(runtime / REPAIR_REQUESTS_ARTIFACT, repair_requests)
    written["repair_requests"] = str(runtime / REPAIR_REQUESTS_ARTIFACT)
    _write_json(runtime / DASHBOARD_SUMMARY_ARTIFACT, _dashboard_summary(payload))
    written["dashboard_summary"] = str(runtime / DASHBOARD_SUMMARY_ARTIFACT)


def build_and_write_self_healing_state(settings: Settings | None = None, *, perform_refresh: bool = True) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload, quarantine_state, quarantine_records, repair_requests = build_self_healing_state(settings, perform_refresh=perform_refresh)
    runtime = _runtime_dir(settings)
    written: dict[str, str] = {}
    _write_json(
        runtime / QUARANTINE_ARTIFACT,
        {
            **quarantine_state,
            "records": quarantine_records,
        },
    )
    written["quarantine"] = str(runtime / QUARANTINE_ARTIFACT)
    _write_phase14_artifacts(runtime, payload, repair_requests, written)
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
        payload["repair_request_tier"] = {
            **_safe_dict(payload.get("repair_request_tier")),
            "repair_request_count": len(repair_requests),
            "critical_repair_request_count": sum(1 for record in repair_requests if record.get("severity") == "critical"),
            "repair_requests_path": _artifact_ref(REPAIR_REQUESTS_ARTIFACT),
        }
        _attach_phase14_diagnostics(payload, runtime, repair_requests)
        _write_phase14_artifacts(runtime, payload, repair_requests, written)
    event = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": payload.get("generated_at"),
        "event": "qadam_self_healing_state_written",
        "status": payload.get("status"),
        "self_healing_passed": payload.get("self_healing_passed"),
        "refresh_success_count": _safe_dict(payload.get("refresh_tier")).get("refresh_success_count"),
        "repair_request_count": len(repair_requests),
        "repair_queue_count": _safe_dict(payload.get("repair_queue_tier")).get("repair_queue_count"),
        "provider_outage_count": _safe_dict(payload.get("provider_outage_classification")).get("provider_outage_count"),
        "stale_or_missing_artifact_count": _safe_dict(payload.get("stale_artifact_recovery")).get("stale_or_missing_artifact_count"),
        "backfill_resume_status": _safe_dict(payload.get("backfill_resume")).get("status"),
    }
    _append_jsonl(runtime / HISTORY_ARTIFACT, event)
    _append_jsonl(runtime / EVENTS_ARTIFACT, event)
    written["history"] = str(runtime / HISTORY_ARTIFACT)
    written["events"] = str(runtime / EVENTS_ARTIFACT)
    _update_phase_status(runtime / PHASE_STATUS_ARTIFACT, payload)
    written["phase_status"] = str(runtime / PHASE_STATUS_ARTIFACT)
    errors = validate_self_healing(payload, repair_requests)
    return payload, written, errors
