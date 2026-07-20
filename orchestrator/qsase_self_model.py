"""QSASE-1 self-model artifact and validation.

The self-model is a read-only mirror of Qadam's current machinery. It reads
existing runtime artifacts and emits QSASE routing context; it does not create
signals, candidates, approvals, orders, broker writes, proof credit, or
live-capital authority.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_self_model.v1"
PHASE_ID = "qsase_1_self_model_artifact_validation"
PHASE_NAME = "QSASE-1: Self-Model Artifact And Validation"
PRIMARY_ARTIFACT = "qsase_self_model.json"
HISTORY_ARTIFACT = "qsase_self_model_history.jsonl"
EVENTS_ARTIFACT = "qsase_self_model_events.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_self_model_dashboard_summary.json"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

SELF_MODEL_AUTHORITY_FLAGS = {
    "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "prediction_market_write_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "telegram_live_send_allowed": False,
    "quantum_job_authority": False,
    "quantum_hardware_submission_allowed": False,
    "quantum_provider_call_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_weight_update_applied": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
}

RUNTIME_SOURCE_FILES = {
    "governance_safety_contract": "qsase_governance_safety_contract.json",
    "phase0_reliability_baseline": "qsase_phase0_paperops_reliability_baseline.json",
    "paperops_autonomous_pass_summary": "paperops_autonomous_pass_summary.json",
    "cockpit_status": "cockpit-status.json",
    "cockpit_status_signature": "cockpit-status.signature.json",
    "paperops_active_paper_trading_automation": "paperops_active_paper_trading_automation.json",
    "paperops_30_day_operations": "paperops_30_day_operations.json",
    "paperops_completion_gaps": "paperops_completion_gaps.json",
    "paperops_paper_lifecycle_poller": "paperops_paper_lifecycle_poller.json",
    "phase5_risk_sizing_reviews": "phase5_risk_sizing_reviews.json",
    "phase7_drawdown_risk_sentinel": "phase7_drawdown_risk_sentinel.json",
    "alpaca_paper_mirror": "alpaca_paper_mirror.json",
    "local_research_assessments": "local_research_assessments.jsonl",
    "strategy_lead_shadow_packets": "strategy_lead_shadow_packets.jsonl",
    "qctrl_fire_opal_ibm_readiness": "qctrl_fire_opal_ibm_readiness.json",
    "paper_live_qctrl_product_access": "paper_live_qctrl_product_access.json",
    "quantum_mandatory_review_gate": "quantum_mandatory_review_gate.json",
    "paperops_qctrl_paper_consultation": "paperops_qctrl_paper_consultation.json",
    "quantum_meta_review": "quantum_meta_review.json",
    "edge_pattern_ledger": "edge_pattern_ledger.json",
    "pattern_recognition_engine": "pattern_recognition_engine.json",
    "edge_memory_ledger": "edge_memory_ledger.json",
    "hypothesis_lifecycle": "hypothesis_lifecycle.json",
    "strategy_update_record": "strategy_update_record.json",
    "strategy_weight_updates": "strategy_weight_updates.json",
    "phase6_shadow_strategy_replay": "phase6_shadow_strategy_replay.json",
    "phase6_learning_approval_ledger": "phase6_learning_approval_ledger.json",
    "telegram_inbound_intake_summary": "telegram_inbound_intake_summary.json",
    "telegram_human_brief": "telegram_human_brief.json",
    "telegram_trade_notifications": "telegram_trade_notifications.json",
    "telegram_codebase_upgrade_notification": "telegram_codebase_upgrade_notification.json",
    "daily_telegram_learning_brief": "daily_telegram_learning_brief.json",
}

REQUIRED_TOP_LEVEL_FIELDS = [
    "schema_version",
    "generated_at",
    "status",
    "staleness_status",
    "architecture_roles",
    "source_state",
    "data_health",
    "trading_universe_health",
    "model_stack",
    "model_health",
    "quantum_state",
    "quantum_health",
    "paperops_route",
    "execution_health",
    "risk_state",
    "risk_health",
    "learning_health",
    "dashboard_state",
    "telegram_state",
    "visibility_health",
    "strategy_readiness_summary",
    "why_not_trading_now",
    "blockers",
    "degraded_components",
    "missing_components",
    "repair_requests",
    "authority",
    "authority_flags",
    "dashboard_safe_summary",
]


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


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(value: Any, now: datetime) -> int | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return max(0, int((now - parsed).total_seconds()))


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


def _file_snapshot(path: Path, now: datetime) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path.relative_to(_repo_root())) if path.is_absolute() else str(path),
            "exists": False,
            "size_bytes": 0,
            "mtime": None,
            "mtime_age_seconds": None,
        }
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    return {
        "path": str(path.relative_to(_repo_root())) if path.is_absolute() else str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime": _iso(mtime),
        "mtime_age_seconds": max(0, int((now - mtime).total_seconds())),
    }


def _runtime_paths(runtime_dir: Path) -> dict[str, Path]:
    return {key: runtime_dir / filename for key, filename in RUNTIME_SOURCE_FILES.items()}


def _int(value: Any) -> int:
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
            return 0
    return 0


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _last_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    return records[-1] if records else {}


def _artifact_status(payload: dict[str, Any]) -> str | None:
    status = payload.get("status")
    return status if isinstance(status, str) else None


def _build_source_context(settings: Settings | None, now: datetime) -> dict[str, Any]:
    runtime_dir = _runtime_dir(settings)
    paths = _runtime_paths(runtime_dir)
    json_sources: dict[str, dict[str, Any]] = {}
    jsonl_sources: dict[str, list[dict[str, Any]]] = {}
    for key, path in paths.items():
        if path.suffix == ".jsonl":
            jsonl_sources[key] = _read_jsonl(path, limit=100)
        else:
            json_sources[key] = _read_json(path)
    return {
        "runtime_dir": str(runtime_dir),
        "paths": paths,
        "source_artifacts": {key: _file_snapshot(path, now) for key, path in paths.items()},
        "json_sources": json_sources,
        "jsonl_sources": jsonl_sources,
    }


def _build_architecture_roles() -> list[dict[str, Any]]:
    return [
        {
            "role_key": "python_coo",
            "label": "Python COO",
            "current_function": "Deterministic orchestration, runtime artifacts, checks, schedulers, PaperOps wrapper compatibility, and fail-closed validation.",
            "authority_boundary": "Can write QSASE diagnostic artifacts; cannot bypass guarded PaperOps, call brokers directly, or enable live capital.",
        },
        {
            "role_key": "local_gemma_research_analyst",
            "label": "Local Gemma Research Analyst",
            "current_function": "Triage, extraction, compression, clustering, and local shadow research packets.",
            "authority_boundary": "Model output is advisory research evidence only; it is not trade, risk, or execution approval.",
        },
        {
            "role_key": "frontier_gemini_strategy_lead",
            "label": "Frontier Gemini Strategy Lead",
            "current_function": "Challenge, synthesis, contradiction review, and failure-mode critique where provider context exists.",
            "authority_boundary": "Strategy Lead output can challenge or propose; it cannot approve trades, size orders, or mutate strategy.",
        },
        {
            "role_key": "ibm_quantum_gates_oracle",
            "label": "IBM Quantum Gates Oracle",
            "current_function": "Nonlinear ambiguity review, quantum gate state, and provider-readiness context.",
            "authority_boundary": "Quantum review can inform ambiguity; it cannot approve execution, create orders, or grant proof credit.",
        },
        {
            "role_key": "qctrl_paper_consultation",
            "label": "Q-CTRL Paper Consultation",
            "current_function": "Paper-consultation readiness and hold state for quantum-adjacent review.",
            "authority_boundary": "Q-CTRL state must be respected; QSASE cannot submit jobs or bypass holds.",
        },
        {
            "role_key": "source_adapter_layer",
            "label": "Source Adapter Layer",
            "current_function": "Canonical, supplemental, and credential-gated observation sources.",
            "authority_boundary": "Sources can inform evidence; no source can create orders or satisfy authority by itself.",
        },
        {
            "role_key": "historical_memory_layer",
            "label": "Historical Memory Layer",
            "current_function": "Replay, learning, edge memory, and historical context when artifacts are present.",
            "authority_boundary": "Historical records and shadow replays cannot advance the 30-day paper growth trial or paper proof ledger.",
        },
        {
            "role_key": "paperops_route",
            "label": "PaperOps Route",
            "current_function": "Guarded Alpaca Paper route, idempotency, risk, lifecycle, and paper proof ledger boundary.",
            "authority_boundary": "Only existing guarded PaperOps may submit paper orders; QSASE cannot submit or stage orders.",
        },
        {
            "role_key": "dashboard",
            "label": "Dashboard",
            "current_function": "Public-safe read-only cockpit visibility.",
            "authority_boundary": "Dashboard cannot create commands, approve trades, write brokers, or grant proof.",
        },
        {
            "role_key": "telegram",
            "label": "Telegram",
            "current_function": "Review-only inbound intake and notification-only outbound summaries.",
            "authority_boundary": "Telegram cannot become command authority or live-capital authority.",
        },
    ]


def _build_data_health(cockpit: dict[str, Any], paperops_summary: dict[str, Any]) -> dict[str, Any]:
    mission = cockpit.get("mission_control") if isinstance(cockpit.get("mission_control"), dict) else {}
    data_sources = mission.get("data_sources") if isinstance(mission.get("data_sources"), dict) else {}
    source_summary = cockpit.get("source_pipeline_summary")
    if not isinstance(source_summary, list):
        source_summary = []
    ledger = data_sources.get("ledger") if isinstance(data_sources.get("ledger"), list) else []
    missing_credential_records = [
        {
            "source_key": record.get("source_key"),
            "source_name": record.get("source_name"),
            "pipeline": record.get("pipeline"),
            "operator_action": record.get("operator_action"),
        }
        for record in ledger
        if isinstance(record, dict) and record.get("credential_status") in {"missing", "missing_optional"}
    ]
    degraded_records = [
        {
            "source_key": record.get("source_key"),
            "source_name": record.get("source_name"),
            "pipeline": record.get("pipeline"),
            "status": record.get("status"),
            "readiness": record.get("readiness"),
        }
        for record in ledger
        if isinstance(record, dict) and (
            record.get("status") == "degraded" or "degraded" in str(record.get("readiness", ""))
        )
    ]
    source_gap_visibility = paperops_summary.get("source_gap_visibility")
    if not isinstance(source_gap_visibility, dict):
        source_gap_visibility = {}
    return {
        "status": "data_health_degraded" if degraded_records or missing_credential_records else "data_health_ready",
        "source_universe_count": _int(data_sources.get("canonical_source_count")),
        "expected_canonical_source_count": _int(data_sources.get("expected_canonical_source_count")),
        "connected_source_count": len(data_sources.get("connected_sources", []))
        if isinstance(data_sources.get("connected_sources"), list)
        else 0,
        "online_source_count": sum(_int(row.get("online_count")) for row in source_summary if isinstance(row, dict)),
        "degraded_source_count": _int(data_sources.get("degraded_count")),
        "missing_credential_source_count": len(missing_credential_records),
        "quarantined_source_count": 0,
        "pipeline_summary": source_summary,
        "source_freshness": "from_cockpit_runtime_snapshot",
        "source_latency": "latency_fields_sparse",
        "source_trust_posture": "ledger_trust_scores_available",
        "source_quorum_availability": "candidate_level_source_quorum_enforced",
        "durable_replay_state": data_sources.get("durable_replay_status"),
        "raw_archive_availability": "not_materialized_in_qsase_1",
        "full_universe_scan_readiness": "pending_qsase_2_matrix",
        "optional_gap_count": _int(source_gap_visibility.get("optional_gap_count")),
        "source_quorum_blocking_gap_count": _int(
            source_gap_visibility.get("source_quorum_blocking_gap_count")
        ),
        "missing_credential_sources": missing_credential_records[:20],
        "degraded_sources": degraded_records[:20],
    }


def _build_trading_universe_health(cockpit: dict[str, Any]) -> dict[str, Any]:
    mission = cockpit.get("mission_control") if isinstance(cockpit.get("mission_control"), dict) else {}
    strategy = mission.get("strategy") if isinstance(mission.get("strategy"), dict) else {}
    universe = strategy.get("universe") if isinstance(strategy.get("universe"), list) else []
    families = strategy.get("strategy_families")
    if not isinstance(families, list):
        families = []
    paper_tradable = [
        row.get("instrument")
        for row in families
        if isinstance(row, dict) and row.get("route_fit") in {"strong_alpaca_paper_proxy_fit", "clean_alpaca_paper_proxy_fit"}
    ]
    context_only = [
        row.get("instrument")
        for row in families
        if isinstance(row, dict) and "blocked" in str(row.get("route_fit", ""))
    ]
    return {
        "status": "trading_universe_ready_with_context_gaps"
        if context_only
        else "trading_universe_ready",
        "watched_instrument_count": len(universe),
        "instrument_families": universe,
        "available_market_data": "cockpit_market_and_technical_context_available",
        "market_confirmation_availability": "available_where_strategy_family_gate_passed",
        "paper_tradable_proxy_availability": "partial",
        "paper_tradable_instruments": paper_tradable,
        "prediction_market_route_readiness": "context_only_until_governed_route_ready",
        "options_or_volatility_context_availability": "context_only",
        "tradingview_or_technical_context_availability": "technical_context_recorded",
        "supplemental_market_data_status": "supplemental_context_not_source_quorum",
        "non_paperable_instrument_list": context_only,
        "observable_instruments": universe,
        "backtestable_instruments": "pending_qsase_3_historical_memory",
        "calibration_only_instruments": context_only,
    }


def _build_model_health(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    local_records = context["jsonl_sources"].get("local_research_assessments", [])
    lead_records = context["jsonl_sources"].get("strategy_lead_shadow_packets", [])
    latest_local = _last_record(local_records)
    latest_lead = _last_record(lead_records)
    missing_probe = not (_runtime_dir() / "llm_provider_probes.json").exists()
    model_stack = {
        "local_gemma": {
            "availability": "shadow_assessment_recorded" if latest_local else "missing",
            "provider": latest_local.get("provider"),
            "model": latest_local.get("model"),
            "latest_assessment_at": latest_local.get("created_at"),
            "latest_status": latest_local.get("status"),
            "raw_response_status": latest_local.get("raw_response_status"),
            "role": "triage_extraction_compression_clustering",
            "advisory_only": True,
            "output_is_approval": False,
        },
        "frontier_gemini": {
            "availability": "strategy_lead_shadow_packet_recorded" if latest_lead else "missing",
            "latest_packet_at": latest_lead.get("created_at"),
            "latest_status": latest_lead.get("status"),
            "role": "challenge_synthesis_failure_mode_review",
            "advisory_only": True,
            "output_is_approval": False,
        },
        "model_probe_artifact_present": not missing_probe,
        "model_disagreement_state": "not_recorded",
    }
    gaps: list[str] = []
    if missing_probe:
        gaps.append("llm_provider_probes_artifact_missing")
    if not latest_local:
        gaps.append("local_research_assessment_missing")
    if not latest_lead:
        gaps.append("strategy_lead_shadow_packet_missing")
    model_health = {
        "status": "model_health_degraded" if gaps else "model_health_ready",
        "local_gemma_available": bool(latest_local),
        "frontier_gemini_available": bool(latest_lead),
        "model_latency": "not_materialized",
        "model_failure_state": "probe_gap" if missing_probe else "none_recorded",
        "model_disagreement_state": "not_recorded",
        "hallucination_or_unsupported_claim_risk": "requires_source_evidence_before_routing",
        "latest_model_review_freshness": latest_lead.get("created_at") or latest_local.get("created_at"),
        "model_output_advisory_only": True,
        "model_output_can_approve_trades": False,
        "gaps": gaps,
    }
    return model_stack, model_health


def _build_quantum_health(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    qctrl_readiness = context["json_sources"].get("qctrl_fire_opal_ibm_readiness", {})
    qctrl_access = context["json_sources"].get("paper_live_qctrl_product_access", {})
    mandatory_gate = context["json_sources"].get("quantum_mandatory_review_gate", {})
    qctrl_consultation = context["json_sources"].get("paperops_qctrl_paper_consultation", {})
    meta_review = context["json_sources"].get("quantum_meta_review", {})
    hardware_submission_allowed = _bool(qctrl_readiness.get("hardware_submission_allowed")) or _bool(
        qctrl_access.get("hardware_submission_allowed")
    )
    hardware_submitted = _bool(qctrl_readiness.get("hardware_job_submitted"))
    provider_call_allowed = _bool(qctrl_access.get("provider_call_allowed"))
    provider_call_count = _int(qctrl_readiness.get("provider_call_count")) + _int(
        qctrl_access.get("provider_call_count")
    )
    quantum_state = {
        "latest_quantum_backend": qctrl_readiness.get("mode") or qctrl_access.get("mode"),
        "latest_simulation_or_fallback_mode": meta_review.get("loop_level_decision")
        or "deterministic_or_provider_readiness_context",
        "local_simulator_availability": "not_explicitly_recorded",
        "qctrl_readiness": qctrl_readiness.get("status") or qctrl_access.get("qctrl_readiness_status"),
        "ibm_quantum_readiness": {
            "ibm_quantum_instance_configured": qctrl_readiness.get("ibm_quantum_instance_configured"),
            "ibm_quantum_token_configured": qctrl_readiness.get("ibm_quantum_token_configured"),
            "qiskit_ibm_runtime_importable": qctrl_readiness.get("qiskit_ibm_runtime_importable"),
        },
        "aws_braket_readiness": "not_applicable_in_current_artifacts",
        "quantum_mandatory_review_gate_status": mandatory_gate.get("status"),
        "latest_oracle_job_status": qctrl_readiness.get("fire_opal_async_action_status"),
        "latest_oracle_output_route": "review_only",
        "qctrl_paper_consultation_status": qctrl_consultation.get("status"),
    }
    gaps: list[str] = []
    if _age_seconds(qctrl_readiness.get("generated_at"), _now()) and (
        _age_seconds(qctrl_readiness.get("generated_at"), _now()) or 0
    ) > 7 * 24 * 60 * 60:
        gaps.append("qctrl_fire_opal_ibm_readiness_stale")
    if not mandatory_gate:
        gaps.append("quantum_mandatory_review_gate_missing")
    if not qctrl_consultation:
        gaps.append("paperops_qctrl_paper_consultation_missing")
    if provider_call_allowed:
        gaps.append("quantum_provider_call_readiness_recorded_context_only")
    unsafe_quantum_count = int(hardware_submission_allowed) + int(hardware_submitted)
    quantum_health = {
        "status": "quantum_health_blocked" if unsafe_quantum_count else (
            "quantum_health_degraded" if gaps else "quantum_health_ready"
        ),
        "hardware_submission_allowed_count": int(hardware_submission_allowed),
        "hardware_submitted_count": int(hardware_submitted),
        "quantum_provider_call_allowed_count": int(provider_call_allowed),
        "provider_call_count": provider_call_count,
        "quantum_execution_authority": False,
        "quantum_paper_order_authority": False,
        "quantum_can_review_ambiguity": True,
        "quantum_can_approve_execution": False,
        "quantum_output_is_approval": False,
        "gaps": gaps,
    }
    return quantum_state, quantum_health


def _build_execution_health(
    context: dict[str, Any],
    paperops_summary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    active = context["json_sources"].get("paperops_active_paper_trading_automation", {})
    operations = context["json_sources"].get("paperops_30_day_operations", {})
    lifecycle = context["json_sources"].get("paperops_paper_lifecycle_poller", {})
    phase0 = context["json_sources"].get("phase0_reliability_baseline", {})
    paper_runtime = paperops_summary.get("paper_runtime") if isinstance(paperops_summary.get("paper_runtime"), dict) else {}
    why_reason = active.get("why_not_trading_now") or paper_runtime.get("idle_reason") or "not_recorded"
    category = "healthy_idle"
    repair_required = False
    if "idempotency" in str(why_reason) or _int(paper_runtime.get("duplicate_submit_count")):
        category = "duplicate_or_idempotency_hold"
    elif "source" in str(why_reason):
        category = "source_gap"
    elif "risk" in str(why_reason):
        category = "risk_gap"
    elif "route" in str(why_reason):
        category = "paperops_route_gap"
        repair_required = True
    paperops_route = {
        "active_automation_status": active.get("status"),
        "paperops_readiness_status": active.get("paperops_readiness_status")
        or operations.get("paper_operational_cycle_status")
        or paperops_summary.get("states", {}).get("paper_ops_cycle_state")
        if isinstance(paperops_summary.get("states"), dict)
        else None,
        "guarded_alpaca_paper_route_readiness": active.get("rs5_guarded_submit_route"),
        "paper_endpoint_confirmed": active.get("paper_endpoint_confirmed"),
        "live_endpoint_disabled": not _bool(active.get("live_endpoint_allowed")),
        "idempotency_ledger_state": active.get("paperops2_idempotency_ledger_active"),
        "duplicate_submit_state": {
            "paperops2_duplicate_submit_record_count": _int(
                active.get("paperops2_duplicate_submit_record_count")
            ),
            "summary_duplicate_submit_count": _int(paper_runtime.get("duplicate_submit_count")),
        },
        "lifecycle_poller_state": lifecycle.get("status"),
        "exit_path_state": active.get("paperops4_status"),
    }
    execution_health = {
        "status": "execution_health_degraded"
        if phase0.get("status") == "ready_with_gaps"
        else "execution_health_ready",
        "active_automation_status": active.get("status"),
        "paperops_readiness_status": paperops_route["paperops_readiness_status"],
        "guarded_alpaca_paper_route_ready": bool(active.get("paperops2_path_available", True)),
        "paper_endpoint_confirmed": active.get("paper_endpoint_confirmed"),
        "live_endpoint_disabled": True,
        "fresh_eligible_submit_count": _int(paper_runtime.get("fresh_eligible_submit_count")),
        "fresh_distinct_setup_count": _int(active.get("rs5_available_distinct_setup_count")),
        "duplicate_submit_count": _int(paper_runtime.get("duplicate_submit_count")),
        "open_order_count": _int(paper_runtime.get("open_order_count")),
        "open_position_count": _int(paper_runtime.get("open_position_count")),
        "closed_paper_trade_count": _int(paper_runtime.get("closed_paper_trade_count")),
        "submitted_paper_order_count": _int(paper_runtime.get("submitted_paper_order_count")),
        "lifecycle_poller_state": lifecycle.get("status"),
        "exit_path_state": active.get("paperops4_status"),
        "phase0_status": phase0.get("status"),
        "phase0_gap_count": _int(phase0.get("gap_count")),
    }
    why_not_trading_now = {
        "reason": why_reason,
        "category": category,
        "blocking_layer": "paperops",
        "next_allowed_action": "watch_or_wait_for_fresh_distinct_setup",
        "repair_required": repair_required,
        "details": {
            "idempotency_guard_message": paper_runtime.get("idempotency_guard_message")
            or active.get("idempotency_guard_message"),
            "open_order_count": _int(paper_runtime.get("open_order_count")),
            "fresh_eligible_submit_count": _int(paper_runtime.get("fresh_eligible_submit_count")),
            "duplicate_submit_count": _int(paper_runtime.get("duplicate_submit_count")),
        },
    }
    return paperops_route, execution_health, why_not_trading_now


def _build_risk_health(context: dict[str, Any], cockpit: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    mission = cockpit.get("mission_control") if isinstance(cockpit.get("mission_control"), dict) else {}
    portfolio = mission.get("portfolio") if isinstance(mission.get("portfolio"), dict) else {}
    risk_reviews = context["json_sources"].get("phase5_risk_sizing_reviews", {})
    drawdown = context["json_sources"].get("phase7_drawdown_risk_sentinel", {})
    risk_state = {
        "paper_account_state": portfolio.get("connection_status") or "alpaca_paper_readonly_connected",
        "paper_buying_power": "not_exposed_in_public_safe_snapshot",
        "current_exposure": {
            "open_position_count": _int(portfolio.get("open_position_count")),
            "open_order_count": _int(portfolio.get("order_count")),
            "drawdown_pct": portfolio.get("drawdown_pct"),
            "total_pnl_gbp": portfolio.get("total_pnl_gbp"),
        },
        "duplicate_exposure_risk": "managed_by_paperops_idempotency_and_duplicate_guard",
        "drawdown_state": drawdown.get("drawdown_state"),
        "per_strategy_risk_budget": "downstream_risk_agent_only",
        "per_run_submit_attempt_cap": "guarded_submit_cap_per_paperops_run",
        "open_order_and_position_constraints": "active",
        "kill_switch_state": "not_materialized_in_self_model_source_set",
        "risk_agent_availability": risk_reviews.get("status"),
        "execution_policy_availability": "cockpit_execution_policy_available",
    }
    blocked_reviews = _int(risk_reviews.get("blocked_count"))
    risk_health = {
        "status": "risk_health_degraded" if blocked_reviews else "risk_health_ready",
        "risk_review_count": _int(risk_reviews.get("risk_review_count")),
        "blocked_risk_review_count": blocked_reviews,
        "broker_write_allowed_count": _int(risk_reviews.get("broker_write_allowed_count")),
        "execution_allowed_count": _int(risk_reviews.get("execution_allowed_count")),
        "paper_order_allowed_count": _int(risk_reviews.get("paper_order_allowed_count")),
        "live_capital_enabled_count": _int(risk_reviews.get("live_capital_enabled_count")),
        "drawdown_status": drawdown.get("status"),
        "drawdown_state": drawdown.get("drawdown_state"),
        "risk_context_can_route_to_paper_review": blocked_reviews == 0,
        "qsase_can_size_orders": False,
    }
    return risk_state, risk_health


def _build_learning_health(context: dict[str, Any], paperops_summary: dict[str, Any]) -> dict[str, Any]:
    edge_pattern = context["json_sources"].get("edge_pattern_ledger", {})
    learning_sources = {
        "edge_pattern_ledger": edge_pattern,
        "pattern_recognition_engine": context["json_sources"].get("pattern_recognition_engine", {}),
        "edge_memory_ledger": context["json_sources"].get("edge_memory_ledger", {}),
        "hypothesis_lifecycle": context["json_sources"].get("hypothesis_lifecycle", {}),
        "strategy_update_record": context["json_sources"].get("strategy_update_record", {}),
        "strategy_weight_updates": context["json_sources"].get("strategy_weight_updates", {}),
        "quantum_meta_review": context["json_sources"].get("quantum_meta_review", {}),
        "shadow_strategy_replay": context["json_sources"].get("phase6_shadow_strategy_replay", {}),
        "learning_approval_ledger": context["json_sources"].get("phase6_learning_approval_ledger", {}),
    }
    statuses = {key: _artifact_status(value) for key, value in learning_sources.items()}
    paper_proof_ledger = paperops_summary.get("paper_proof_ledger")
    if not isinstance(paper_proof_ledger, dict):
        paper_proof_ledger = {}
    return {
        "status": "learning_health_degraded"
        if _int(edge_pattern.get("validated_edge_count")) == 0
        else "learning_health_ready",
        "artifact_statuses": statuses,
        "edge_pattern_ledger_status": edge_pattern.get("status"),
        "candidate_pattern_count": _int(edge_pattern.get("candidate_pattern_count")),
        "validated_edge_count": _int(edge_pattern.get("validated_edge_count")),
        "hypothesis_lifecycle_status": statuses.get("hypothesis_lifecycle"),
        "strategy_update_record_status": statuses.get("strategy_update_record"),
        "strategy_weight_update_status": statuses.get("strategy_weight_updates"),
        "quantum_meta_review_status": statuses.get("quantum_meta_review"),
        "shadow_strategy_replay_status": statuses.get("shadow_strategy_replay"),
        "postmortem_readiness": "paper_proof_ledger_and_postmortem_artifacts_required",
        "paper_proof_ledger_freshness": "from_paperops_autonomous_pass_summary",
        "paper_proof_ledger": {
            "closed_proof_trade_count": _int(paper_proof_ledger.get("closed_proof_trade_count")),
            "submitted_paper_order_count": _int(paper_proof_ledger.get("submitted_paper_order_count")),
            "qualified_setup_count": _int(paper_proof_ledger.get("qualified_setup_count")),
        },
        "unresolved_blocker_count": len(paperops_summary.get("blockers", []))
        if isinstance(paperops_summary.get("blockers"), list)
        else 0,
        "strategy_proposal_count": _int(context["json_sources"].get("strategy_update_record", {}).get("proposal_count")),
        "learning_entries_are_proposal_only": True,
        "backtests_are_not_proof": True,
        "shadow_replays_are_not_proof": True,
    }


def _build_visibility_health(context: dict[str, Any], cockpit: dict[str, Any], now: datetime) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    artifacts = context["source_artifacts"]
    cockpit_snapshot = artifacts["cockpit_status"]
    signature_snapshot = artifacts["cockpit_status_signature"]
    telegram_inbound = context["json_sources"].get("telegram_inbound_intake_summary", {})
    telegram_human = context["json_sources"].get("telegram_human_brief", {})
    telegram_trade = context["json_sources"].get("telegram_trade_notifications", {})
    codebase_notice = context["json_sources"].get("telegram_codebase_upgrade_notification", {})
    daily_learning = context["json_sources"].get("daily_telegram_learning_brief", {})
    cockpit_age = _age_seconds(cockpit.get("generated_at"), now)
    dashboard_state = {
        "cockpit_status_generated_at": cockpit.get("generated_at"),
        "cockpit_status_age_seconds": cockpit_age,
        "cockpit_status_freshness": "fresh" if cockpit_age is not None and cockpit_age < 2 * 60 * 60 else "stale_or_unknown",
        "dashboard_export_freshness": "from_cockpit_status_runtime",
        "dashboard_signature_exists": bool(signature_snapshot.get("exists")),
        "qsase_dashboard_module_availability": "pending_qsase_13_dashboard_visibility",
        "public_safe_redaction_status": "public_safe_no_secrets",
        "secret_exposure_checks": "no_secret_fields_exposed_by_self_model",
    }
    telegram_state = {
        "inbound_status": telegram_inbound.get("status"),
        "inbound_record_count": _int(telegram_inbound.get("record_count")),
        "inbound_world_event_datapoint_count": _int(telegram_inbound.get("world_event_datapoint_count")),
        "inbound_strategy_consideration_count": _int(telegram_inbound.get("strategy_consideration_count")),
        "inbound_read_only": True,
        "outbound_human_brief_status": telegram_human.get("status"),
        "outbound_trade_notification_status": telegram_trade.get("status"),
        "outbound_codebase_notice_status": codebase_notice.get("status"),
        "outbound_daily_learning_status": daily_learning.get("status"),
        "latest_notification_failure_category": telegram_human.get("failure_category")
        or telegram_trade.get("failure_category")
        or daily_learning.get("failure_category"),
        "generic_repetitive_message_checks": "handled_by_existing_telegram_quality_checks",
        "telegram_changes_trading_authority": False,
    }
    visibility_health = {
        "status": "visibility_health_ready"
        if dashboard_state["dashboard_signature_exists"]
        else "visibility_health_degraded",
        "cockpit_status_freshness": dashboard_state["cockpit_status_freshness"],
        "dashboard_signature_freshness": "present" if signature_snapshot.get("exists") else "missing",
        "telegram_outbound_statuses": {
            "human_brief": telegram_human.get("status"),
            "trade_notifications": telegram_trade.get("status"),
            "codebase_upgrade": codebase_notice.get("status"),
            "daily_learning": daily_learning.get("status"),
        },
        "telegram_inbound_read_only": True,
        "visibility_failure_changes_trading_authority": False,
    }
    return dashboard_state, telegram_state, visibility_health


def _build_strategy_readiness_summary(cockpit: dict[str, Any]) -> list[dict[str, Any]]:
    mission = cockpit.get("mission_control") if isinstance(cockpit.get("mission_control"), dict) else {}
    strategy = mission.get("strategy") if isinstance(mission.get("strategy"), dict) else {}
    families = strategy.get("strategy_families") if isinstance(strategy.get("strategy_families"), list) else []
    rows: list[dict[str, Any]] = []
    for row in families:
        if not isinstance(row, dict):
            continue
        current_state = row.get("current_state") or row.get("setup_state")
        qualified = _bool(row.get("qualified_setup"))
        blocked_reasons = row.get("rejection_reasons") if isinstance(row.get("rejection_reasons"), list) else []
        rows.append(
            {
                "strategy_key": row.get("key"),
                "strategy_label": row.get("label"),
                "strategy_type": "inherited_strategy_family",
                "current_state": current_state,
                "source_readiness": "passed" if qualified else "needs_confirmation",
                "market_readiness": "passed" if qualified else "needs_market_confirmation",
                "model_readiness": "challenge_context_available",
                "quantum_readiness": "review_required_not_authority",
                "akber_filter_readiness": "active_filter",
                "risk_readiness": "ready_for_downstream_review" if qualified else "not_ready",
                "paperops_readiness": "qualified_for_guarded_paper_review" if qualified else "blocked_or_waiting",
                "learning_readiness": "candidate_edge_under_observation",
                "next_allowed_action": "paperops_review_only" if qualified else "watch_or_research",
                "blocked_reasons": blocked_reasons,
                "paper_order_submission_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            }
        )
    return rows


def _build_degraded_and_repairs(
    payload_parts: dict[str, Any],
    phase0: dict[str, Any],
    paperops_summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    degraded: list[dict[str, Any]] = []
    missing: list[str] = []
    repairs: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    def add_degraded(component: str, reason: str, severity: str = "degraded") -> None:
        degraded.append({"component": component, "reason": reason, "severity": severity})

    phase0_gaps = phase0.get("gaps") if isinstance(phase0.get("gaps"), list) else []
    for gap in phase0_gaps:
        add_degraded("operational_phase0", str(gap), "gap")
    if payload_parts["data_health"]["missing_credential_source_count"]:
        add_degraded("source_state", "missing_optional_source_credentials", "gap")
    if payload_parts["model_health"].get("gaps"):
        for gap in payload_parts["model_health"]["gaps"]:
            add_degraded("model_stack", gap, "gap")
    if payload_parts["quantum_health"].get("gaps"):
        for gap in payload_parts["quantum_health"]["gaps"]:
            add_degraded("quantum_state", gap, "gap")
    if payload_parts["risk_health"].get("blocked_risk_review_count"):
        add_degraded("risk_state", "risk_reviews_blocked_or_shadow_only", "gap")
    if payload_parts["learning_health"].get("validated_edge_count") == 0:
        add_degraded("learning_health", "no_validated_edges_yet", "gap")
    if not payload_parts["dashboard_state"].get("dashboard_signature_exists"):
        add_degraded("dashboard_state", "cockpit_status_signature_missing", "degraded")

    for index, item in enumerate(degraded, start=1):
        component = item["component"]
        reason = item["reason"]
        repair_type = "review_request"
        if "scanner" in reason or "stale" in reason:
            repair_type = "stale_artifact_refresh_request"
        elif "credential" in reason:
            repair_type = "missing_source_credential_review"
        elif "lifecycle" in reason or "accepted paper orders" in reason:
            repair_type = "paperops_lifecycle_mirror_repair_request"
        elif "telemetry" in reason:
            repair_type = "telemetry_consistency_repair_request"
        elif "qctrl" in reason or "quantum" in component:
            repair_type = "quantum_readiness_repair_request"
        repairs.append(
            {
                "repair_request_id": f"qsase-1-repair-{index:03d}",
                "repair_type": repair_type,
                "component": component,
                "reason": reason,
                "command_authority": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "next_allowed_action": "queue_human_or_approved_self_healing_review",
            }
        )

    for blocker in paperops_summary.get("blockers", []) if isinstance(paperops_summary.get("blockers"), list) else []:
        blockers.append({"source": "paperops_autonomous_pass_summary", "blocker": blocker})
    return degraded, missing, repairs, blockers


def _build_staleness_status(context: dict[str, Any], now: datetime) -> dict[str, Any]:
    required = [
        "governance_safety_contract",
        "phase0_reliability_baseline",
        "paperops_autonomous_pass_summary",
        "cockpit_status",
    ]
    stale: list[dict[str, Any]] = []
    missing: list[str] = []
    for key in required:
        snapshot = context["source_artifacts"][key]
        if not snapshot.get("exists"):
            missing.append(key)
            continue
        age = snapshot.get("mtime_age_seconds")
        if age is None or age > 6 * 60 * 60:
            stale.append({"artifact": key, "age_seconds": age})
    if missing:
        status = "missing_required_artifact"
    elif stale:
        status = "stale_required_artifact"
    else:
        status = "fresh_enough_for_qsase_1"
    return {
        "status": status,
        "required_artifact_count": len(required),
        "missing_required_artifacts": missing,
        "stale_required_artifacts": stale,
        "freshness_sla_seconds": 6 * 60 * 60,
        "evaluated_at": _iso(now),
    }


def build_qsase_self_model(
    settings: Settings | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated = now or _now()
    context = _build_source_context(settings, generated)
    sources = context["json_sources"]
    paperops_summary = sources.get("paperops_autonomous_pass_summary", {})
    cockpit = sources.get("cockpit_status", {})
    phase0 = sources.get("phase0_reliability_baseline", {})
    governance = sources.get("governance_safety_contract", {})

    data_health = _build_data_health(cockpit, paperops_summary)
    trading_universe_health = _build_trading_universe_health(cockpit)
    model_stack, model_health = _build_model_health(context)
    quantum_state, quantum_health = _build_quantum_health(context)
    paperops_route, execution_health, why_not_trading_now = _build_execution_health(
        context,
        paperops_summary,
    )
    risk_state, risk_health = _build_risk_health(context, cockpit)
    learning_health = _build_learning_health(context, paperops_summary)
    dashboard_state, telegram_state, visibility_health = _build_visibility_health(
        context,
        cockpit,
        generated,
    )
    strategy_readiness_summary = _build_strategy_readiness_summary(cockpit)
    payload_parts = {
        "data_health": data_health,
        "model_health": model_health,
        "quantum_health": quantum_health,
        "risk_health": risk_health,
        "learning_health": learning_health,
        "dashboard_state": dashboard_state,
    }
    degraded_components, missing_components, repair_requests, blockers = _build_degraded_and_repairs(
        payload_parts,
        phase0,
        paperops_summary,
    )
    staleness_status = _build_staleness_status(context, generated)

    status = "qsase_self_model_ready"
    if staleness_status["status"] == "missing_required_artifact":
        status = "qsase_self_model_blocked"
    elif staleness_status["status"] == "stale_required_artifact":
        status = "qsase_self_model_stale"
    elif any(item["severity"] == "degraded" for item in degraded_components):
        status = "qsase_self_model_degraded"
    elif degraded_components:
        status = "qsase_self_model_ready_with_gaps"
    if quantum_health["status"] == "quantum_health_blocked":
        status = "qsase_self_model_blocked"

    authority = universal_authority_flags()
    authority_flags = dict(SELF_MODEL_AUTHORITY_FLAGS)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "qsase:1:self-model",
        "artifact_type": "qsase_self_model",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": _iso(generated),
        "status": status,
        "staleness_status": staleness_status,
        "public_safe": True,
        "boundary": "QSASE self-model is read-only routing context. It cannot create candidates, approvals, orders, broker writes, proof credit, or live-capital authority.",
        "governance_status": governance.get("status"),
        "architecture_roles": _build_architecture_roles(),
        "source_state": {
            "source_artifacts": context["source_artifacts"],
            "source_state_contract": "runtime_artifacts_are_source_of_truth",
        },
        "data_health": data_health,
        "trading_universe_health": trading_universe_health,
        "model_stack": model_stack,
        "model_health": model_health,
        "quantum_state": quantum_state,
        "quantum_health": quantum_health,
        "paperops_route": paperops_route,
        "execution_health": execution_health,
        "risk_state": risk_state,
        "risk_health": risk_health,
        "learning_health": learning_health,
        "dashboard_state": dashboard_state,
        "telegram_state": telegram_state,
        "visibility_health": visibility_health,
        "strategy_readiness_summary": strategy_readiness_summary,
        "why_not_trading_now": why_not_trading_now,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "degraded_components": degraded_components,
        "degraded_component_count": len(degraded_components),
        "missing_components": missing_components,
        "missing_component_count": len(missing_components),
        "repair_requests": repair_requests,
        "repair_request_count": len(repair_requests),
        "authority": authority,
        "authority_flags": authority_flags,
        "model_outputs_are_approvals": False,
        "quantum_outputs_are_approvals": False,
        "dashboard_and_telegram_are_authority": False,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "validation_errors": [],
    }
    payload["dashboard_safe_summary"] = build_qsase_self_model_dashboard_summary(payload, generated)
    return payload


def build_qsase_self_model_dashboard_summary(
    payload: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    generated = now or _now()
    why = payload.get("why_not_trading_now", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_self_model_dashboard_summary",
        "generated_at": _iso(generated),
        "status": payload.get("status"),
        "title": "QSASE Self-Model",
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Source state", "value": payload.get("data_health", {}).get("status")},
            {"label": "Model stack", "value": payload.get("model_health", {}).get("status")},
            {"label": "Quantum", "value": payload.get("quantum_health", {}).get("status")},
            {"label": "PaperOps", "value": payload.get("execution_health", {}).get("status")},
            {"label": "Risk", "value": payload.get("risk_health", {}).get("status")},
            {"label": "Visibility", "value": payload.get("visibility_health", {}).get("status")},
            {"label": "Why not trading now", "value": why.get("reason")},
        ],
        "degraded_component_count": payload.get("degraded_component_count"),
        "missing_component_count": payload.get("missing_component_count"),
        "repair_request_count": payload.get("repair_request_count"),
        "authority_flags_false": all(value is False for value in payload.get("authority_flags", {}).values()),
    }


def validate_qsase_self_model(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in payload:
            errors.append(f"missing_top_level_field:{field}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if payload.get("artifact_type") != "qsase_self_model":
        errors.append("artifact_type_mismatch")
    if payload.get("phase_id") != PHASE_ID:
        errors.append("phase_id_mismatch")
    if payload.get("status") not in {
        "qsase_self_model_ready",
        "qsase_self_model_ready_with_gaps",
        "qsase_self_model_degraded",
        "qsase_self_model_blocked",
        "qsase_self_model_stale",
    }:
        errors.append("invalid_status")
    if payload.get("public_safe") is not True:
        errors.append("public_safe_must_be_true")
    roles = payload.get("architecture_roles")
    role_keys = {role.get("role_key") for role in roles} if isinstance(roles, list) else set()
    for required_role in {
        "python_coo",
        "local_gemma_research_analyst",
        "frontier_gemini_strategy_lead",
        "ibm_quantum_gates_oracle",
        "qctrl_paper_consultation",
        "source_adapter_layer",
        "historical_memory_layer",
        "paperops_route",
        "dashboard",
        "telegram",
    }:
        if required_role not in role_keys:
            errors.append(f"missing_architecture_role:{required_role}")
    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority_missing")
        authority = {}
    for field in universal_authority_flags():
        if field not in authority:
            errors.append(f"authority_missing:{field}")
        elif authority[field] is not False:
            errors.append(f"authority_unsafe_true:{field}")
    flags = payload.get("authority_flags")
    if not isinstance(flags, dict):
        errors.append("authority_flags_missing")
        flags = {}
    for field in SELF_MODEL_AUTHORITY_FLAGS:
        if field not in flags:
            errors.append(f"self_model_authority_missing:{field}")
        elif flags[field] is not False:
            errors.append(f"self_model_authority_unsafe_true:{field}")
    if payload.get("model_outputs_are_approvals") is not False:
        errors.append("model_outputs_are_approvals_must_be_false")
    if payload.get("quantum_outputs_are_approvals") is not False:
        errors.append("quantum_outputs_are_approvals_must_be_false")
    if payload.get("dashboard_and_telegram_are_authority") is not False:
        errors.append("dashboard_and_telegram_are_authority_must_be_false")
    why = payload.get("why_not_trading_now")
    if not isinstance(why, dict):
        errors.append("why_not_trading_now_missing")
    else:
        for field in ("reason", "category", "blocking_layer", "next_allowed_action", "repair_required"):
            if field not in why:
                errors.append(f"why_not_trading_now_missing:{field}")
    if not isinstance(payload.get("strategy_readiness_summary"), list):
        errors.append("strategy_readiness_summary_must_be_list")
    if not isinstance(payload.get("repair_requests"), list):
        errors.append("repair_requests_must_be_list")
    dashboard_summary = payload.get("dashboard_safe_summary")
    if not isinstance(dashboard_summary, dict):
        errors.append("dashboard_safe_summary_missing")
    else:
        if dashboard_summary.get("public_safe") is not True:
            errors.append("dashboard_summary_public_safe_missing")
        if dashboard_summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_command_disabled_missing")
        if dashboard_summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
    if payload.get("quantum_health", {}).get("quantum_can_approve_execution") is not False:
        errors.append("quantum_can_approve_execution_must_be_false")
    if payload.get("model_health", {}).get("model_output_can_approve_trades") is not False:
        errors.append("model_output_can_approve_trades_must_be_false")
    if payload.get("telegram_state", {}).get("telegram_changes_trading_authority") is not False:
        errors.append("telegram_changes_trading_authority_must_be_false")
    return errors


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "degraded_component_count": payload["degraded_component_count"],
        "missing_component_count": payload["missing_component_count"],
        "repair_request_count": payload["repair_request_count"],
        "why_not_trading_now": payload["why_not_trading_now"],
        "paper_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "model_outputs_are_approvals": False,
        "quantum_outputs_are_approvals": False,
        "dashboard_and_telegram_are_authority": False,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": payload["authority"],
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        log_path.read_text(encoding="utf-8")
        if log_path.exists()
        else "# QSASE Implementation Log\n"
    )
    marker = f"<!-- {PHASE_ID} -->"
    why = payload.get("why_not_trading_now", {})
    entry = (
        f"{marker}\n"
        f"## QSASE-1: Self-Model Artifact And Validation\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Degraded components: `{payload.get('degraded_component_count')}`\n"
        f"- Missing components: `{payload.get('missing_component_count')}`\n"
        f"- Why not trading now: `{why.get('reason')}`\n"
        f"- Safety: model and quantum outputs are not approvals; dashboard and Telegram remain non-authoritative; all self-model authority flags are false.\n"
    )
    from orchestrator.qadam_marked_log import upsert_marked_section

    updated = upsert_marked_section(existing, marker, entry)
    log_path.write_text(updated, encoding="utf-8")


def write_qsase_self_model(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    primary_path = runtime_dir / PRIMARY_ARTIFACT
    _write_json(primary_path, payload)
    written["self_model"] = str(primary_path)
    summary_path = runtime_dir / DASHBOARD_SUMMARY_ARTIFACT
    _write_json(summary_path, payload["dashboard_safe_summary"])
    written["dashboard_summary"] = str(summary_path)
    phase_status_path = runtime_dir / PHASE_STATUS_ARTIFACT
    _write_json(phase_status_path, build_qsase_phase_implementation_status(payload))
    written["phase_status"] = str(phase_status_path)
    if append_history:
        history_path = runtime_dir / HISTORY_ARTIFACT
        events_path = runtime_dir / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "degraded_component_count": payload["degraded_component_count"],
                "missing_component_count": payload["missing_component_count"],
                "why_not_trading_now": payload["why_not_trading_now"],
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_self_model_written",
                "status": payload["status"],
                "public_safe": True,
                "authority_flags_false": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_qsase_self_model(
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_qsase_self_model(settings)
    errors = validate_qsase_self_model(payload)
    payload["validation_errors"] = errors
    written = write_qsase_self_model(
        payload,
        settings,
        append_history=append_history,
        append_log=append_log,
    )
    return payload, written, errors


def validate_negative_self_model_probes() -> list[str]:
    errors: list[str] = []
    base = build_qsase_self_model()
    for field in SELF_MODEL_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][field] = True
        probe_errors = validate_qsase_self_model(probe)
        if not any(field in error for error in probe_errors):
            errors.append(f"negative_probe_failed_to_reject:{field}")
    probe = copy.deepcopy(base)
    probe["model_outputs_are_approvals"] = True
    if not any("model_outputs_are_approvals" in error for error in validate_qsase_self_model(probe)):
        errors.append("negative_probe_failed_to_reject_model_approval")
    probe = copy.deepcopy(base)
    probe["quantum_outputs_are_approvals"] = True
    if not any("quantum_outputs_are_approvals" in error for error in validate_qsase_self_model(probe)):
        errors.append("negative_probe_failed_to_reject_quantum_approval")
    probe = copy.deepcopy(base)
    probe["dashboard_and_telegram_are_authority"] = True
    if not any("dashboard_and_telegram_are_authority" in error for error in validate_qsase_self_model(probe)):
        errors.append("negative_probe_failed_to_reject_visibility_authority")
    return errors
