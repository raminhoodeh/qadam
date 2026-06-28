"""QSASE-11 PaperOps Gate Interface.

This interface converts Strategy Router paper-review candidates into upstream
PaperOps handoff records only. A handoff is context for the existing guarded
PaperOps chain; it is not a qualified setup, risk approval, execution approval,
paper order, broker write, or paper proof ledger entry.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_paperops_gate_interface.v1"
PHASE_ID = "qsase_11_paperops_handoff_interface"
PHASE_NAME = "QSASE-11: PaperOps Handoff Interface"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_paperops_gate_interface.json"
GATE_RECORDS_ARTIFACT = "qsase_paperops_gate_interface.jsonl"
HISTORY_ARTIFACT = "qsase_paperops_gate_interface_history.jsonl"
EVENTS_ARTIFACT = "qsase_paperops_gate_interface_events.jsonl"
HANDOFF_RECORDS_ARTIFACT = "qsase_paperops_handoff_records.jsonl"
REJECTED_HANDOFFS_ARTIFACT = "qsase_paperops_rejected_handoffs.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_paperops_gate_interface_dashboard_summary.json"

ROUTER_ARTIFACT = "qsase_strategy_router_decisions.json"
ROUTER_DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"
SELF_MODEL_ARTIFACT = "qsase_self_model.json"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_integration.json"
SHADOW_SIMULATOR_ARTIFACT = "qsase_shadow_strategy_simulator.json"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
ALPACA_PAPER_MIRROR_ARTIFACT = "alpaca_paper_mirror.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
PAPER_LIVE_QCTRL_ARTIFACT = "paper_live_qctrl_product_access.json"
PAPEROPS_QCTRL_CONSULTATION_ARTIFACT = "paperops_qctrl_paper_consultation.json"
PHASE7_DRAWDOWN_SENTINEL_ARTIFACT = "phase7_drawdown_risk_sentinel.json"

GATE_STATES = {
    "eligible_for_existing_paperops_review",
    "hold_missing_context",
    "hold_route_unavailable",
    "rejected_before_paperops",
    "repair_requested",
}

HANDOFF_AUTHORITY_FLAGS = {
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_creation_allowed": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "execution_intent_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_staged": False,
    "broker_write_allowed": False,
    "broker_write_created": False,
    "live_broker_endpoint_allowed": False,
    "alpaca_paper_submit_called": False,
    "alpaca_live_submit_allowed": False,
    "prediction_market_write_allowed": False,
    "crypto_perps_write_allowed": False,
    "paperops_direct_call_allowed": False,
    "paperops_bypass_allowed": False,
    "signal_integrity_bypass_allowed": False,
    "strategy_lead_bypass_allowed": False,
    "head_of_quant_bypass_allowed": False,
    "risk_agent_bypass_allowed": False,
    "execution_policy_bypass_allowed": False,
    "qctrl_bypass_allowed": False,
    "idempotency_bypass_allowed": False,
    "duplicate_exposure_bypass_allowed": False,
    "daily_drawdown_bypass_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_write_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

REQUIRED_GATE_RECORD_FIELDS = (
    "paperops_gate_record_id",
    "status",
    "router_decision_id",
    "research_goal_lineage",
    "candidate_identity",
    "idempotency",
    "gate_state",
    "decision",
    "telegram_summary",
    "authority",
)

REQUIRED_HANDOFF_FIELDS = (
    "paperops_handoff_id",
    "status",
    "router_decision_id",
    "research_goal_lineage",
    "candidate_identity",
    "idempotency",
    "gate_state",
    "decision",
    "authority",
)


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


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _authority_block() -> dict[str, Any]:
    return {
        "handoff_context_only": True,
        "not_qualified_setup": True,
        "not_order": True,
        "existing_paperops_only": True,
        **HANDOFF_AUTHORITY_FLAGS,
    }


def _runtime_file_snapshot(runtime_dir: Path, filename: str) -> dict[str, Any]:
    path = runtime_dir / filename
    if not path.exists():
        return {"path": f"data/runtime/{filename}", "exists": False, "mtime": None, "mtime_age_seconds": None}
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return {
        "path": f"data/runtime/{filename}",
        "exists": True,
        "mtime": _iso(mtime),
        "mtime_age_seconds": int((_now() - mtime).total_seconds()),
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "router": _read_json(runtime / ROUTER_ARTIFACT),
        "router_decisions": _read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT),
        "self_model": _read_json(runtime / SELF_MODEL_ARTIFACT),
        "akber_filter": _read_json(runtime / AKBER_FILTER_ARTIFACT),
        "shadow_simulator": _read_json(runtime / SHADOW_SIMULATOR_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "alpaca_paper_mirror": _read_json(runtime / ALPACA_PAPER_MIRROR_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        "paper_live_qctrl": _read_json(runtime / PAPER_LIVE_QCTRL_ARTIFACT),
        "paperops_qctrl_consultation": _read_json(runtime / PAPEROPS_QCTRL_CONSULTATION_ARTIFACT),
        "drawdown_sentinel": _read_json(runtime / PHASE7_DRAWDOWN_SENTINEL_ARTIFACT),
        "alpaca_paper_mirror_snapshot": _runtime_file_snapshot(runtime, ALPACA_PAPER_MIRROR_ARTIFACT),
    }


def _source_refs() -> dict[str, str]:
    return {
        "router_ref": f"data/runtime/{ROUTER_ARTIFACT}",
        "router_decisions_ref": f"data/runtime/{ROUTER_DECISIONS_ARTIFACT}",
        "self_model_ref": f"data/runtime/{SELF_MODEL_ARTIFACT}",
        "akber_ref": f"data/runtime/{AKBER_FILTER_ARTIFACT}",
        "shadow_ref": f"data/runtime/{SHADOW_SIMULATOR_ARTIFACT}",
        "historical_memory_ref": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
        "paperops_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
        "paper_account_mirror_ref": f"data/runtime/{ALPACA_PAPER_MIRROR_ARTIFACT}",
        "qctrl_ref": f"data/runtime/{PAPER_LIVE_QCTRL_ARTIFACT}",
        "qctrl_consultation_ref": f"data/runtime/{PAPEROPS_QCTRL_CONSULTATION_ARTIFACT}",
        "drawdown_ref": f"data/runtime/{PHASE7_DRAWDOWN_SENTINEL_ARTIFACT}",
    }


def _paper_route_state(context: dict[str, Any]) -> dict[str, Any]:
    route = context["self_model"].get("paperops_route", {})
    return {
        "paperops_readiness_status": route.get("paperops_readiness_status"),
        "guarded_alpaca_paper_route": "existing guarded Alpaca Paper route only",
        "guarded_alpaca_paper_route_state": (
            "available_for_review"
            if route.get("paper_endpoint_confirmed") is True and route.get("live_endpoint_disabled") is True
            else "unavailable_or_unsafe"
        ),
        "paper_endpoint_confirmed": route.get("paper_endpoint_confirmed") is True,
        "live_endpoint_disabled": route.get("live_endpoint_disabled") is True,
        "active_automation_status": route.get("active_automation_status"),
        "lifecycle_poller_state": route.get("lifecycle_poller_state"),
        "exit_path_state": route.get("exit_path_state"),
        "raw_route_reference": route.get("guarded_alpaca_paper_route_readiness"),
    }


def _risk_state(context: dict[str, Any]) -> dict[str, Any]:
    exposure = context["self_model"].get("risk_state", {}).get("current_exposure", {})
    drawdown = context["drawdown_sentinel"]
    return {
        "duplicate_exposure": context["self_model"].get("risk_state", {}).get("duplicate_exposure_risk"),
        "open_order_count": int(_float(exposure.get("open_order_count"), 0)),
        "open_position_count": int(_float(exposure.get("open_position_count"), 0)),
        "drawdown_pct": _float(exposure.get("drawdown_pct"), 0.0),
        "daily_drawdown": "breach" if drawdown.get("drawdown_cap_breached") is True else "pass",
        "drawdown_state": drawdown.get("drawdown_state") or context["self_model"].get("risk_state", {}).get("drawdown_state"),
        "risk_budget_precheck": "downstream_risk_agent_required",
        "risk_budget_breach": False,
    }


def _qctrl_state(context: dict[str, Any]) -> dict[str, Any]:
    qctrl = context["paper_live_qctrl"]
    consultation = context["paperops_qctrl_consultation"]
    missing = not qctrl and not consultation
    hold = missing or qctrl.get("product_access_blocker") not in {None, "", "none"}
    return {
        "qctrl_state_present": not missing,
        "qctrl_product_access_status": qctrl.get("status"),
        "qctrl_product_access_verified": qctrl.get("product_access_verified") is True,
        "qctrl_consultation_status": consultation.get("status"),
        "qctrl_provider_call_recorded": consultation.get("provider_call_recorded") is True
        or qctrl.get("provider_call_succeeded") is True,
        "qctrl_paper_consultation": "hold" if hold else "not_bypassed",
        "qctrl_bypass_allowed": False,
        "qctrl_job_submitted": False,
    }


def _paper_account_mirror_state(context: dict[str, Any]) -> dict[str, Any]:
    mirror = context["alpaca_paper_mirror"]
    snapshot = context["alpaca_paper_mirror_snapshot"]
    age = snapshot.get("mtime_age_seconds")
    fresh = bool(snapshot.get("exists") and isinstance(age, int) and age <= 3600)
    return {
        "status": mirror.get("status"),
        "exists": snapshot.get("exists") is True,
        "mtime": snapshot.get("mtime"),
        "mtime_age_seconds": age,
        "paper_account_mirror": "fresh" if fresh else "stale_or_missing",
        "open_order_count": int(_float(mirror.get("order_count"), 0)),
        "open_position_count": int(_float(mirror.get("position_count"), 0)),
        "live_capital_enabled": mirror.get("live_capital_enabled") is True,
        "write_authority": mirror.get("write_authority"),
    }


def _research_goal_lineage(router_decision: dict[str, Any]) -> dict[str, Any]:
    lineage = router_decision.get("lineage", {})
    return {
        "research_goal_id": lineage.get("research_goal_id"),
        "source_pattern_ids": [lineage.get("source_pattern_id")] if lineage.get("source_pattern_id") else [],
        "foundry_ref": lineage.get("foundry_ref") or f"data/runtime/{ROUTER_ARTIFACT}",
        "router_ref": f"data/runtime/{ROUTER_ARTIFACT}",
        "router_decision_ref": f"data/runtime/{ROUTER_DECISIONS_ARTIFACT}",
        "akber_ref": lineage.get("akber_ref"),
        "shadow_ref": lineage.get("shadow_ref"),
        "shadow_replay_ids": lineage.get("shadow_replay_ids", []),
        "paper_growth_trial_calendar_advance_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
    }


def _candidate_identity(router_decision: dict[str, Any]) -> dict[str, Any]:
    identity = router_decision.get("candidate_identity", {})
    family = router_decision.get("strategy_family", {})
    seed = "|".join(
        str(part or "")
        for part in (
            identity.get("candidate_identity_key"),
            family.get("primary_family"),
            identity.get("instrument"),
            identity.get("time_window"),
            identity.get("invalidation_id"),
        )
    )
    return {
        "candidate_id": identity.get("candidate_identity_key"),
        "candidate_identity_hash": _hash_id([SCHEMA_VERSION, seed], "qsase-candidate-hash"),
        "strategy_family": family.get("primary_family"),
        "instrument": identity.get("instrument"),
        "direction": "not_selected_by_qsase_handoff",
        "time_horizon": identity.get("time_window"),
        "thesis": identity.get("thesis"),
        "invalidation_summary": identity.get("invalidation_id") or "invalidation_required_before_paperops",
        "source_packet_id": identity.get("source_packet_id"),
        "risk_concept_id": identity.get("risk_concept_id"),
    }


def _idempotency_material(router_decision: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    lineage = _research_goal_lineage(router_decision)
    identity = _candidate_identity(router_decision)
    seed = ":".join(
        str(part or "missing")
        for part in (
            lineage.get("research_goal_id"),
            identity.get("candidate_id"),
            identity.get("instrument"),
            router_decision.get("router_decision_id"),
        )
    )
    key = _hash_id([SCHEMA_VERSION, seed], "qsase-paperops-review")
    why = context["self_model"].get("why_not_trading_now", {})
    router_hard_vetoes = router_decision.get("hard_vetoes", [])
    duplicate_runtime = why.get("category") == "duplicate_or_idempotency_hold"
    duplicate_router = any("idempotency" in str(veto) or "duplicate" in str(veto) for veto in router_hard_vetoes)
    return {
        "idempotency_namespace": "qsase_paperops_review",
        "idempotency_seed": seed,
        "idempotency_key": key,
        "duplicate_idempotency_detected": bool(duplicate_runtime or duplicate_router),
        "duplicate_idempotency_state": why.get("reason") if duplicate_runtime else "not_detected_in_qsase_gate",
        "idempotency_source": "qsase_router_plus_self_model",
    }


def _gate_state(router_decision: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    gates = router_decision.get("gates", {})
    route = _paper_route_state(context)
    risk = _risk_state(context)
    qctrl = _qctrl_state(context)
    mirror = _paper_account_mirror_state(context)
    return {
        "router_output": router_decision.get("decision", {}).get("router_output"),
        "source_quorum": gates.get("source_quorum"),
        "akber_filter": gates.get("akber_filter"),
        "quantum_review": gates.get("quantum_review"),
        "shadow_replay": gates.get("shadow_replay"),
        "duplicate_exposure": risk["duplicate_exposure"],
        "daily_drawdown": risk["daily_drawdown"],
        "risk_budget_precheck": risk["risk_budget_precheck"],
        "paper_account_mirror": mirror["paper_account_mirror"],
        "qctrl_paper_consultation": qctrl["qctrl_paper_consultation"],
        "guarded_alpaca_paper_route": route["guarded_alpaca_paper_route_state"],
        "guarded_alpaca_paper_route_name": route["guarded_alpaca_paper_route"],
        "live_capital_enabled": False,
        "broker_bypass_detected": False,
        "telegram_command_origin_detected": False,
        "open_order_count": risk["open_order_count"],
        "open_position_count": risk["open_position_count"],
        "paper_route_state": route,
        "risk_state": risk,
        "qctrl_state": qctrl,
        "paper_account_mirror_state": mirror,
    }


def _failure_reasons(
    router_decision: dict[str, Any],
    context: dict[str, Any],
    idempotency: dict[str, Any],
    gate_state: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    holds: list[str] = []
    rejections: list[str] = []
    repairs: list[str] = []
    if router_decision.get("decision", {}).get("router_output") != "paper_review_candidate":
        rejections.append("router_output_not_paper_review_candidate")
    lineage = _research_goal_lineage(router_decision)
    identity = _candidate_identity(router_decision)
    if not lineage.get("research_goal_id"):
        holds.append("missing_research_goal_lineage")
    if not identity.get("candidate_id") or not identity.get("candidate_identity_hash"):
        holds.append("missing_candidate_identity")
    if not idempotency.get("idempotency_seed") or not idempotency.get("idempotency_key"):
        holds.append("missing_idempotency_seed")
    if idempotency.get("duplicate_idempotency_detected") is True:
        rejections.append("duplicate_idempotency_key")
    if gate_state.get("source_quorum") != "pass":
        rejections.append("source_quorum_failed")
    if gate_state.get("akber_filter") != "pass":
        rejections.append("akber_filter_failed")
    if gate_state.get("quantum_review") in {None, "", "missing", "not_recorded"}:
        rejections.append("quantum_review_required_but_missing")
    if str(gate_state.get("quantum_review")) == "downgrade_or_hold":
        holds.append("qctrl_or_quantum_review_hold")
    if gate_state.get("daily_drawdown") == "breach":
        rejections.append("daily_drawdown_breach")
    if gate_state.get("risk_state", {}).get("risk_budget_breach") is True:
        rejections.append("risk_budget_breach")
    if gate_state.get("paper_account_mirror") != "fresh":
        holds.append("paper_account_mirror_stale")
    if gate_state.get("qctrl_paper_consultation") == "hold":
        holds.append("qctrl_paper_consultation_hold")
    if gate_state.get("guarded_alpaca_paper_route") != "available_for_review":
        holds.append("route_status_stale")
    if gate_state.get("live_capital_enabled") is True:
        rejections.append("live_capital_route_detected")
    if gate_state.get("broker_bypass_detected") is True:
        rejections.append("broker_bypass_detected")
    if gate_state.get("telegram_command_origin_detected") is True:
        rejections.append("telegram_command_origin_detected")
    if any("observable_or_futures_symbol_not_guarded_paper_route" in str(veto) for veto in router_decision.get("hard_vetoes", [])):
        rejections.append("non_paperable_market_expression")
    for name, artifact in (
        ("strategy_router_missing", context["router"]),
        ("qsase_self_model_missing", context["self_model"]),
        ("paperops_route_state_missing", context["paperops_summary"]),
        ("paper_account_mirror_missing", context["alpaca_paper_mirror"]),
        ("qctrl_state_missing", context["paper_live_qctrl"] or context["paperops_qctrl_consultation"]),
    ):
        if not artifact:
            repairs.append(name)
    return sorted(set(holds)), sorted(set(rejections)), sorted(set(repairs))


def _decision_state(holds: list[str], rejections: list[str], repairs: list[str]) -> dict[str, Any]:
    if repairs:
        output = "repair_requested"
        reason = repairs[0]
        next_system = "self_healing_repair_requested"
    elif rejections:
        output = "rejected_before_paperops"
        reason = rejections[0]
        next_system = "no_paper_handoff"
    elif any(reason in {"paper_account_mirror_stale", "market_session_closed", "qctrl_paper_consultation_hold", "route_status_stale"} for reason in holds):
        output = "hold_route_unavailable"
        reason = holds[0]
        next_system = "refresh_route_context_then_recheck"
    elif holds:
        output = "hold_missing_context"
        reason = holds[0]
        next_system = "complete_missing_context_then_recheck"
    else:
        output = "eligible_for_existing_paperops_review"
        reason = "router_candidate_complete_for_existing_paperops_review"
        next_system = "existing_guarded_paperops_route"
    return {
        "paperops_gate_output": output,
        "reason": reason,
        "hold_reasons": holds,
        "rejection_reasons": rejections,
        "repair_reasons": repairs,
        "next_required_system": next_system,
        "paper_order_ready": False,
        "qualified_setup_created": False,
        "paper_order_created": False,
        "broker_write_created": False,
        "proof_credit_allowed": False,
    }


def _telegram_summary(record: dict[str, Any]) -> dict[str, Any]:
    identity = record.get("candidate_identity", {})
    decision = record.get("decision", {})
    setup = identity.get("thesis") or identity.get("strategy_family") or "strategy candidate"
    output = decision.get("paperops_gate_output", "hold")
    action = "existing PaperOps review" if output == "eligible_for_existing_paperops_review" else "no paper handoff"
    return {
        "review_only": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "contains_command": False,
        "contains_broker_instruction": False,
        "text": (
            f"Qadam PaperOps gate {output}\n"
            f"Setup: {str(setup)[:72]}\n"
            f"Reason: {str(decision.get('reason'))[:96]}\n"
            f"Next: {action}\n"
            "No order submitted"
        ),
    }


def _build_gate_record(router_decision: dict[str, Any], context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    idempotency = _idempotency_material(router_decision, context)
    gate_state = _gate_state(router_decision, context)
    holds, rejections, repairs = _failure_reasons(router_decision, context, idempotency, gate_state)
    decision = _decision_state(holds, rejections, repairs)
    lineage = _research_goal_lineage(router_decision)
    identity = _candidate_identity(router_decision)
    record = {
        "schema_version": SCHEMA_VERSION,
        "paperops_gate_record_id": _hash_id([SCHEMA_VERSION, router_decision.get("router_decision_id")], "qsase-paperops-gate"),
        "paperops_handoff_id": _hash_id([SCHEMA_VERSION, router_decision.get("router_decision_id"), "handoff"], "qsase-paperops-handoff"),
        "generated_at": generated_at,
        "status": decision["paperops_gate_output"],
        "router_decision_id": router_decision.get("router_decision_id"),
        "strategy_hypothesis_id": router_decision.get("strategy_hypothesis_id"),
        "rejected_hypothesis_id": router_decision.get("rejected_hypothesis_id"),
        "router_output": router_decision.get("decision", {}).get("router_output"),
        "research_goal_lineage": lineage,
        "candidate_identity": identity,
        "idempotency": idempotency,
        "gate_state": gate_state,
        "decision": decision,
        "source_refs": _source_refs(),
        "paperops_boundary": {
            "existing_paperops_only": True,
            "guarded_route": "existing guarded Alpaca Paper route only",
            "handoff_is_not_submit_record": True,
            "handoff_is_not_qualified_setup": True,
            "handoff_is_not_order": True,
            "qctrl_hold_not_bypassed": True,
            "idempotency_not_bypassed": True,
            "duplicate_exposure_not_bypassed": True,
            "daily_drawdown_not_bypassed": True,
        },
        "calendar_and_proof_boundary": {
            "paper_growth_trial_calendar_advance_allowed": False,
            "simulated_elapsed_time_allowed": False,
            "historical_backtest_to_handoff_allowed": False,
            "shadow_replay_to_proof_allowed": False,
            "paper_proof_ledger_credit_allowed": False,
        },
        "telegram_summary": {},
        "authority": _authority_block(),
        **HANDOFF_AUTHORITY_FLAGS,
    }
    record["telegram_summary"] = _telegram_summary(record)
    return record


def build_paperops_handoff_records(
    router_decisions: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    records = []
    generated_at = _iso(_now())
    for router_decision in router_decisions:
        record = _build_gate_record(router_decision, context, generated_at)
        if record["status"] == "eligible_for_existing_paperops_review":
            records.append(record)
    return records


def reject_unfit_paperops_handoffs(
    records: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    del context
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "rejected_handoff_id": _hash_id([record["paperops_gate_record_id"], "reject"], "qsase-paperops-reject"),
            "paperops_gate_record_id": record["paperops_gate_record_id"],
            "paperops_handoff_id": record["paperops_handoff_id"],
            "router_decision_id": record["router_decision_id"],
            "status": "rejected_handoff_recorded" if record["status"] == "rejected_before_paperops" else "held_handoff_recorded",
            "gate_output": record["status"],
            "reason": record["decision"]["reason"],
            "hold_reasons": record["decision"].get("hold_reasons", []),
            "rejection_reasons": record["decision"].get("rejection_reasons", []),
            "repair_reasons": record["decision"].get("repair_reasons", []),
            "research_goal_lineage": record["research_goal_lineage"],
            "candidate_identity": record["candidate_identity"],
            "idempotency": record["idempotency"],
            "gate_state": record["gate_state"],
            "paper_order_created": False,
            "qualified_setup_created": False,
            "proof_credit_allowed": False,
            "authority": _authority_block(),
            **HANDOFF_AUTHORITY_FLAGS,
        }
        for record in records
        if record["status"] != "eligible_for_existing_paperops_review"
    ]


def _all_gate_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    return [_build_gate_record(decision, context, generated_at) for decision in context["router_decisions"]]


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top_record = payload.get("handoff_records", [None])[0] if payload.get("handoff_records") else None
    if not top_record and payload.get("rejected_handoffs"):
        top_record = payload["rejected_handoffs"][0]
    top_identity = (top_record or {}).get("candidate_identity", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_paperops_gate_interface_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "PaperOps gate", "value": payload["status"]},
            {"label": "Router candidates", "value": payload["router_candidate_count"]},
            {"label": "Eligible handoffs", "value": payload["eligible_for_paperops_review_count"]},
            {"label": "Held handoffs", "value": payload["held_handoff_count"]},
            {"label": "Rejected handoffs", "value": payload["rejected_handoff_count"]},
            {"label": "Q-CTRL", "value": payload["qctrl_paper_consultation_state"]},
            {"label": "Authority", "value": "no order submitted"},
        ],
        "top_handoff_candidate": (top_record or {}).get("paperops_handoff_id"),
        "top_setup": top_identity.get("thesis") or top_identity.get("strategy_family"),
        "blocking_gate": payload["top_blocking_gate"],
        "idempotency_state": payload["idempotency_state"],
        "duplicate_exposure_state": payload["duplicate_exposure_state"],
        "drawdown_state": payload["drawdown_state"],
        "qctrl_paper_consultation_state": payload["qctrl_paper_consultation_state"],
        "guarded_alpaca_paper_route_state": payload["guarded_alpaca_paper_route_state"],
        "proof_boundary": "handoff is not paper proof ledger credit",
        "authority_state": "paperops_handoff_context_only_no_order",
        "no_qualified_setups_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
    }


def validate_paperops_handoff_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_HANDOFF_FIELDS:
        if field not in record:
            errors.append(f"handoff_missing_{field}")
    if record.get("status") != "eligible_for_existing_paperops_review":
        errors.append("handoff_status_not_eligible")
    lineage = record.get("research_goal_lineage", {})
    if not lineage.get("research_goal_id"):
        errors.append("handoff_missing_research_goal_lineage")
    identity = record.get("candidate_identity", {})
    if not identity.get("candidate_id") or not identity.get("candidate_identity_hash"):
        errors.append("handoff_missing_candidate_identity")
    idempotency = record.get("idempotency", {})
    if not idempotency.get("idempotency_namespace") or not idempotency.get("idempotency_seed") or not idempotency.get("idempotency_key"):
        errors.append("handoff_missing_idempotency_material")
    if idempotency.get("duplicate_idempotency_detected") is not False:
        errors.append("handoff_duplicate_idempotency_detected")
    gate = record.get("gate_state", {})
    for field in (
        "source_quorum",
        "akber_filter",
        "quantum_review",
        "duplicate_exposure",
        "daily_drawdown",
        "qctrl_paper_consultation",
        "guarded_alpaca_paper_route",
    ):
        if field not in gate:
            errors.append(f"handoff_missing_gate_{field}")
    if record.get("decision", {}).get("paper_order_ready") is not False:
        errors.append("handoff_paper_order_ready_must_be_false")
    if record.get("decision", {}).get("qualified_setup_created") is not False:
        errors.append("handoff_qualified_setup_created_must_be_false")
    errors.extend(_validate_authority(record.get("authority", {}), "handoff_authority"))
    return sorted(set(errors))


def build_paperops_gate_interface(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    gate_records = _all_gate_records(context, generated_at)
    handoff_records = [record for record in gate_records if record["status"] == "eligible_for_existing_paperops_review"]
    rejected_handoffs = reject_unfit_paperops_handoffs(gate_records, context)
    router_candidates = [
        decision
        for decision in context["router_decisions"]
        if decision.get("decision", {}).get("router_output") == "paper_review_candidate"
    ]
    repair_required = any(record["status"] == "repair_requested" for record in gate_records)
    held = [record for record in gate_records if record["status"].startswith("hold_")]
    rejected = [record for record in gate_records if record["status"] == "rejected_before_paperops"]
    duplicate_idempotency_count = sum(1 for record in gate_records if record["idempotency"].get("duplicate_idempotency_detected"))
    duplicate_exposure_count = sum(
        1 for record in gate_records if "duplicate_exposure_conflict" in record["decision"].get("rejection_reasons", [])
    )
    source_quorum_block_count = sum(
        1 for record in gate_records if "source_quorum_failed" in record["decision"].get("rejection_reasons", [])
    )
    drawdown_block_count = sum(
        1 for record in gate_records if "daily_drawdown_breach" in record["decision"].get("rejection_reasons", [])
    )
    qctrl_hold_count = sum(
        1 for record in gate_records if "qctrl_paper_consultation_hold" in record["decision"].get("hold_reasons", [])
    )
    paper_route_unavailable_count = sum(
        1
        for record in gate_records
        if "route_status_stale" in record["decision"].get("hold_reasons", [])
        or "non_paperable_market_expression" in record["decision"].get("rejection_reasons", [])
    )
    top_blocking_gate = "none"
    if rejected_handoffs:
        top_blocking_gate = rejected_handoffs[0]["reason"]
    elif held:
        top_blocking_gate = held[0]["decision"]["reason"]
    route = _paper_route_state(context)
    risk = _risk_state(context)
    qctrl = _qctrl_state(context)
    missing_inputs = [
        name
        for name, value in (
            ("strategy_router_missing", context["router"]),
            ("qsase_self_model_missing", context["self_model"]),
            ("paperops_route_state_missing", context["paperops_summary"]),
            ("paper_account_mirror_missing", context["alpaca_paper_mirror"]),
            ("qctrl_state_missing", context["paper_live_qctrl"] or context["paperops_qctrl_consultation"]),
        )
        if not value
    ]
    status = "qsase_paperops_gate_interface_ready"
    if missing_inputs:
        status = "qsase_paperops_gate_interface_blocked"
    elif not handoff_records or rejected or held:
        status = "qsase_paperops_gate_interface_degraded"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_paperops_gate_interface",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "handoff_context_only": True,
        "router_decision_count": len(context["router_decisions"]),
        "router_candidate_count": len(router_candidates),
        "gate_record_count": len(gate_records),
        "handoff_record_count": len(handoff_records),
        "eligible_for_paperops_review_count": len(handoff_records),
        "held_handoff_count": len(held),
        "rejected_handoff_count": len(rejected_handoffs),
        "duplicate_idempotency_count": duplicate_idempotency_count,
        "duplicate_exposure_count": duplicate_exposure_count,
        "source_quorum_block_count": source_quorum_block_count,
        "drawdown_block_count": drawdown_block_count,
        "qctrl_hold_count": qctrl_hold_count,
        "paper_route_unavailable_count": paper_route_unavailable_count,
        "paper_order_created_count": 0,
        "qualified_setup_created_count": 0,
        "trade_candidate_created_count": 0,
        "risk_approval_created_count": 0,
        "execution_approval_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "qualified_setup_created": False,
        "trade_candidate_created": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "existing_paperops_remains_only_submit_route": True,
        "guarded_alpaca_paper_route_state": route["guarded_alpaca_paper_route_state"],
        "guarded_alpaca_paper_route_name": route["guarded_alpaca_paper_route"],
        "qctrl_paper_consultation_state": qctrl["qctrl_paper_consultation"],
        "idempotency_state": "duplicate_detected" if duplicate_idempotency_count else "distinct_or_not_applicable",
        "duplicate_exposure_state": risk["duplicate_exposure"],
        "drawdown_state": risk["drawdown_state"],
        "top_blocking_gate": top_blocking_gate,
        "self_healing_repair_requested": repair_required,
        "missing_required_state": missing_inputs,
        "input_artifacts": _source_refs(),
        "gate_records": gate_records,
        "handoff_records": handoff_records,
        "rejected_handoffs": rejected_handoffs,
        "authority": universal_authority_flags(),
        "authority_flags": dict(HANDOFF_AUTHORITY_FLAGS),
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    summary.pop("gate_records", None)
    summary.pop("handoff_records", None)
    summary.pop("rejected_handoffs", None)
    return summary


def load_paperops_gate_interface(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        payload["gate_records"] = _read_jsonl(runtime / GATE_RECORDS_ARTIFACT)
        payload["handoff_records"] = _read_jsonl(runtime / HANDOFF_RECORDS_ARTIFACT)
        payload["rejected_handoffs"] = _read_jsonl(runtime / REJECTED_HANDOFFS_ARTIFACT)
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in HANDOFF_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_paperops_gate_interface(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_paperops_gate_interface":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_paperops_gate_interface_ready",
        "qsase_paperops_gate_interface_degraded",
        "qsase_paperops_gate_interface_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    for key in (
        "handoff_context_only",
        "existing_paperops_remains_only_submit_route",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "proof_credit_allowed",
        "live_capital_enabled",
        "paper_order_allowed",
        "broker_write_allowed",
        "qualified_setup_created",
        "trade_candidate_created",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    for key in (
        "paper_order_created_count",
        "qualified_setup_created_count",
        "trade_candidate_created_count",
        "risk_approval_created_count",
        "execution_approval_created_count",
        "broker_write_count",
    ):
        if int(payload.get(key, -1) or 0) != 0:
            errors.append(f"{key}_must_be_zero")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "paperops_gate"))
    gate_records = payload.get("gate_records")
    if not isinstance(gate_records, list):
        errors.append("gate_records_missing")
        gate_records = []
    if payload.get("gate_record_count") != len(gate_records):
        errors.append("gate_record_count_mismatch")
    for record in gate_records:
        record_id = record.get("paperops_gate_record_id")
        for field in REQUIRED_GATE_RECORD_FIELDS:
            if field not in record:
                errors.append(f"gate_record_{record_id}_missing_{field}")
        if record.get("status") not in GATE_STATES:
            errors.append(f"gate_record_{record_id}_invalid_status")
        if not record.get("research_goal_lineage", {}).get("research_goal_id"):
            errors.append(f"gate_record_{record_id}_missing_research_goal_lineage")
        identity = record.get("candidate_identity", {})
        if not identity.get("candidate_id") or not identity.get("candidate_identity_hash"):
            errors.append(f"gate_record_{record_id}_missing_candidate_identity")
        idempotency = record.get("idempotency", {})
        for field in ("idempotency_namespace", "idempotency_seed", "idempotency_key"):
            if not idempotency.get(field):
                errors.append(f"gate_record_{record_id}_missing_{field}")
        gate = record.get("gate_state", {})
        for field in (
            "source_quorum",
            "akber_filter",
            "quantum_review",
            "duplicate_exposure",
            "daily_drawdown",
            "qctrl_paper_consultation",
            "guarded_alpaca_paper_route",
        ):
            if field not in gate:
                errors.append(f"gate_record_{record_id}_missing_gate_{field}")
        if gate.get("guarded_alpaca_paper_route_name") != "existing guarded Alpaca Paper route only":
            errors.append(f"gate_record_{record_id}_guarded_route_name_invalid")
        if record.get("paperops_boundary", {}).get("qctrl_hold_not_bypassed") is not True:
            errors.append(f"gate_record_{record_id}_qctrl_hold_boundary_missing")
        if record.get("calendar_and_proof_boundary", {}).get("paper_proof_ledger_credit_allowed") is not False:
            errors.append(f"gate_record_{record_id}_paper_proof_ledger_credit_allowed")
        decision = record.get("decision", {})
        if not decision.get("reason"):
            errors.append(f"gate_record_{record_id}_missing_decision_reason")
        for field in ("paper_order_ready", "qualified_setup_created", "paper_order_created", "broker_write_created", "proof_credit_allowed"):
            if decision.get(field) is not False:
                errors.append(f"gate_record_{record_id}_{field}_must_be_false")
        if idempotency.get("duplicate_idempotency_detected") is True and record.get("status") == "eligible_for_existing_paperops_review":
            errors.append(f"gate_record_{record_id}_duplicate_idempotency_eligible")
        telegram = record.get("telegram_summary", {})
        if telegram.get("review_only") is not True or telegram.get("command_disabled") is not True:
            errors.append(f"gate_record_{record_id}_telegram_not_review_only")
        if telegram.get("contains_command") is not False or telegram.get("contains_broker_instruction") is not False:
            errors.append(f"gate_record_{record_id}_telegram_command_or_broker_language")
        if len(str(telegram.get("text") or "")) > 320:
            errors.append(f"gate_record_{record_id}_telegram_too_long")
        for key in HANDOFF_AUTHORITY_FLAGS:
            if record.get(key) is not False:
                errors.append(f"gate_record_{record_id}_{key}_must_be_false")
            if record.get("authority", {}).get(key) is not False:
                errors.append(f"gate_record_{record_id}_authority_{key}_must_be_false")
    handoffs = payload.get("handoff_records")
    if not isinstance(handoffs, list):
        errors.append("handoff_records_missing")
        handoffs = []
    if payload.get("handoff_record_count") != len(handoffs):
        errors.append("handoff_record_count_mismatch")
    for handoff in handoffs:
        errors.extend(validate_paperops_handoff_record(handoff))
    rejected = payload.get("rejected_handoffs")
    if not isinstance(rejected, list):
        errors.append("rejected_handoffs_missing")
        rejected = []
    if payload.get("rejected_handoff_count") != len(rejected):
        errors.append("rejected_handoff_count_mismatch")
    for record in rejected:
        record_id = record.get("rejected_handoff_id")
        if not record.get("reason"):
            errors.append(f"rejected_handoff_{record_id}_missing_reason")
        if record.get("paper_order_created") is not False:
            errors.append(f"rejected_handoff_{record_id}_paper_order_created")
        if record.get("qualified_setup_created") is not False:
            errors.append(f"rejected_handoff_{record_id}_qualified_setup_created")
        errors.extend(_validate_authority(record.get("authority", {}), f"rejected_handoff_{record_id}_authority"))
    summary = payload.get("dashboard_safe_summary", {})
    if summary:
        if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_public_safe_required")
        if summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
        if summary.get("authority_state") != "paperops_handoff_context_only_no_order":
            errors.append("dashboard_summary_authority_boundary_required")
    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "gate_records_path": f"data/runtime/{GATE_RECORDS_ARTIFACT}",
        "handoff_records_path": f"data/runtime/{HANDOFF_RECORDS_ARTIFACT}",
        "rejected_handoffs_path": f"data/runtime/{REJECTED_HANDOFFS_ARTIFACT}",
        "router_candidate_count": payload["router_candidate_count"],
        "handoff_record_count": payload["handoff_record_count"],
        "eligible_for_paperops_review_count": payload["eligible_for_paperops_review_count"],
        "held_handoff_count": payload["held_handoff_count"],
        "rejected_handoff_count": payload["rejected_handoff_count"],
        "duplicate_idempotency_count": payload["duplicate_idempotency_count"],
        "duplicate_exposure_count": payload["duplicate_exposure_count"],
        "drawdown_block_count": payload["drawdown_block_count"],
        "qctrl_hold_count": payload["qctrl_hold_count"],
        "paper_route_unavailable_count": payload["paper_route_unavailable_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "handoff_records_are_not_qualified_setups": True,
        "handoff_records_are_not_orders": True,
        "existing_paperops_remains_only_submit_route": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "authority_flags_false": True,
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
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# QSASE Implementation Log\n"
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-11: PaperOps Handoff Interface\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Router candidates: `{payload.get('router_candidate_count')}`\n"
        f"- Eligible / held / rejected handoffs: `{payload.get('eligible_for_paperops_review_count')}` / `{payload.get('held_handoff_count')}` / `{payload.get('rejected_handoff_count')}`\n"
        f"- Duplicate idempotency / duplicate exposure / drawdown / Q-CTRL / route blocks: `{payload.get('duplicate_idempotency_count')}` / `{payload.get('duplicate_exposure_count')}` / `{payload.get('drawdown_block_count')}` / `{payload.get('qctrl_hold_count')}` / `{payload.get('paper_route_unavailable_count')}`\n"
        f"- Top blocking gate: `{payload.get('top_blocking_gate')}`\n"
        f"- Safety: handoff records are upstream context only; no qualified setups, trade candidates, risk approvals, execution intents, paper orders, broker writes, live capital, or proof credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_paperops_gate_interface(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "paperops_gate_interface": runtime_dir / PRIMARY_ARTIFACT,
        "gate_records": runtime_dir / GATE_RECORDS_ARTIFACT,
        "handoff_records": runtime_dir / HANDOFF_RECORDS_ARTIFACT,
        "rejected_handoffs": runtime_dir / REJECTED_HANDOFFS_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["paperops_gate_interface"], _summary_without_records(payload))
    _write_jsonl(paths["gate_records"], payload["gate_records"])
    _write_jsonl(paths["handoff_records"], payload["handoff_records"])
    _write_jsonl(paths["rejected_handoffs"], payload["rejected_handoffs"])
    _write_json(paths["dashboard_summary"], payload["dashboard_safe_summary"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        history_path = runtime_dir / HISTORY_ARTIFACT
        events_path = runtime_dir / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "router_candidate_count": payload["router_candidate_count"],
                "handoff_record_count": payload["handoff_record_count"],
                "eligible_for_paperops_review_count": payload["eligible_for_paperops_review_count"],
                "held_handoff_count": payload["held_handoff_count"],
                "rejected_handoff_count": payload["rejected_handoff_count"],
                "top_blocking_gate": payload["top_blocking_gate"],
                "no_paper_orders_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_paperops_gate_interface_written",
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


def build_and_write_paperops_gate_interface(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_paperops_gate_interface(settings)
    errors = validate_paperops_gate_interface(payload)
    written = write_paperops_gate_interface(payload, settings)
    return payload, written, errors


def validate_negative_paperops_gate_interface_probes() -> list[str]:
    base = build_paperops_gate_interface()
    errors: list[str] = []
    for flag in HANDOFF_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_paperops_gate_interface(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    order_probe = copy.deepcopy(base)
    order_probe["paper_order_created_count"] = 1
    if not any("paper_order_created_count" in error for error in validate_paperops_gate_interface(order_probe)):
        errors.append("negative_probe_failed_for_paper_order_count")
    if base["gate_records"]:
        lineage_probe = copy.deepcopy(base)
        lineage_probe["gate_records"][0]["research_goal_lineage"]["research_goal_id"] = None
        if not any("missing_research_goal_lineage" in error for error in validate_paperops_gate_interface(lineage_probe)):
            errors.append("negative_probe_failed_for_lineage")
        idempotency_probe = copy.deepcopy(base)
        idempotency_probe["gate_records"][0]["idempotency"]["idempotency_key"] = ""
        if not any("missing_idempotency_key" in error for error in validate_paperops_gate_interface(idempotency_probe)):
            errors.append("negative_probe_failed_for_idempotency")
        qctrl_probe = copy.deepcopy(base)
        qctrl_probe["gate_records"][0]["paperops_boundary"]["qctrl_hold_not_bypassed"] = False
        if not any("qctrl_hold_boundary" in error for error in validate_paperops_gate_interface(qctrl_probe)):
            errors.append("negative_probe_failed_for_qctrl_boundary")
        setup_probe = copy.deepcopy(base)
        setup_probe["gate_records"][0]["decision"]["qualified_setup_created"] = True
        if not any("qualified_setup_created" in error for error in validate_paperops_gate_interface(setup_probe)):
            errors.append("negative_probe_failed_for_qualified_setup")
    dashboard_probe = copy.deepcopy(base)
    dashboard_probe["dashboard_safe_summary"]["live_send_allowed"] = True
    if not any("dashboard_summary_live_send" in error for error in validate_paperops_gate_interface(dashboard_probe)):
        errors.append("negative_probe_failed_for_dashboard_live_send")
    return errors


if __name__ == "__main__":
    artifact = build_paperops_gate_interface()
    print(_json_dump(_summary_without_records(artifact)))
