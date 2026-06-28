"""QSASE-12 Learning And Attribution Ledger.

This ledger attributes backtest, shadow, paper, non-trade, rejection, blocked
route, and system-defect outcomes across Qadam's QSASE stack. It records
proposal candidates only; it cannot mutate strategy/source/model/filter state,
create trade candidates, create orders, write brokers, grant proof credit, or
advance the 30-day paper growth trial calendar.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_component_attribution_ledger.v1"
PHASE_ID = "qsase_12_learning_attribution_ledger"
PHASE_NAME = "QSASE-12: Learning And Attribution Ledger"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_component_attribution_ledger.json"
LEDGER_JSONL_ARTIFACT = "qsase_component_attribution_ledger.jsonl"
HISTORY_ARTIFACT = "qsase_component_attribution_ledger_history.jsonl"
EVENTS_ARTIFACT = "qsase_component_attribution_ledger_events.jsonl"
STRATEGY_WEIGHT_PROPOSALS_ARTIFACT = "qsase_strategy_weight_proposals.json"
SOURCE_TRUST_PROPOSALS_ARTIFACT = "qsase_source_trust_proposals.json"
MODEL_WEIGHT_PROPOSALS_ARTIFACT = "qsase_model_weight_proposals.json"
FILTER_THRESHOLD_PROPOSALS_ARTIFACT = "qsase_filter_threshold_proposals.json"
LEARNING_APPROVAL_QUEUE_ARTIFACT = "qsase_learning_approval_queue.json"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_learning_attribution_dashboard_summary.json"

SELF_MODEL_ARTIFACT = "qsase_self_model.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
PAPEROPS_GATE_ARTIFACT = "qsase_paperops_gate_interface.json"
PAPEROPS_GATE_RECORDS_ARTIFACT = "qsase_paperops_gate_interface.jsonl"
PAPEROPS_HANDOFF_RECORDS_ARTIFACT = "qsase_paperops_handoff_records.jsonl"
PAPEROPS_REJECTED_HANDOFFS_ARTIFACT = "qsase_paperops_rejected_handoffs.jsonl"
ROUTER_ARTIFACT = "qsase_strategy_router_decisions.json"
ROUTER_DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"
STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_hypotheses.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
REJECTED_STRATEGY_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_integration.json"
AKBER_FILTER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
SHADOW_SIMULATOR_ARTIFACT = "qsase_shadow_strategy_simulator.json"
SHADOW_RESULTS_ARTIFACT = "qsase_shadow_strategy_results.jsonl"
LINEAR_LAB_ARTIFACT = "qsase_linear_pattern_lab.json"
LINEAR_BACKTEST_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
NONLINEAR_LAB_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab.json"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
UNIVERSAL_MATRIX_ARTIFACT = "qsase_universal_source_price_matrix.json"
FULL_PATTERN_SEARCH_ARTIFACT = "qsase_full_universe_pattern_search.json"
PHASE0_ARTIFACT = "qsase_phase0_paperops_reliability_baseline.json"

EVIDENCE_CLASSES = {
    "real_paper_lifecycle",
    "non_trade_decision",
    "shadow_replay",
    "backtest_observation",
    "rejected_hypothesis",
    "blocked_route",
    "system_defect",
}

COMPONENTS = (
    "source_universe",
    "source_quorum",
    "historical_source_price_memory",
    "universal_source_price_pattern_matrix",
    "linear_pattern_recognition_lab",
    "nonlinear_and_quantum_pattern_lab",
    "local_gemma_model",
    "frontier_gemini_model",
    "ibm_quantum_gates_oracle",
    "akber_filter",
    "strategy_foundry",
    "strategy_router",
    "paperops_gate_interface",
    "signal_integrity",
    "strategy_lead",
    "head_of_quant_review",
    "risk_agent",
    "execution_policy",
    "idempotency_ledger",
    "duplicate_exposure_check",
    "daily_drawdown_check",
    "qctrl_paper_consultation_hold",
    "guarded_alpaca_paper_route",
    "paper_lifecycle_poller",
    "self_healing_repair_loop",
)

CONTRIBUTIONS = {"helped", "hurt", "neutral", "unknown", "blocked", "not_applicable"}

CAUSAL_LABELS = {
    "worked_for_expected_reason",
    "worked_for_unexpected_reason",
    "failed_for_expected_reason",
    "failed_for_unexpected_reason",
    "blocked_correctly",
    "blocked_but_opportunity_missed",
    "rejected_correctly",
    "rejected_but_pattern_later_confirmed",
    "route_defect_prevented_evaluation",
    "source_noise_dominated",
    "regime_bias_dominated",
    "execution_luck_dominated",
    "overfit_likely",
    "insufficient_evidence",
}

LEARNING_AUTHORITY_FLAGS = {
    "learning_write_created": False,
    "strategy_mutation_created": False,
    "policy_mutation_created": False,
    "model_weight_update_created": False,
    "trust_score_update_created": False,
    "source_trust_update_created": False,
    "filter_threshold_update_created": False,
    "strategy_weight_update_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": False,
    "broker_write_allowed": False,
    "broker_write_created": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

REQUIRED_RECORD_FIELDS = (
    "attribution_record_id",
    "status",
    "evidence_class",
    "generated_at",
    "lineage",
    "decision_context",
    "outcome_summary",
    "component_attribution",
    "causal_assessment",
    "proposal",
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


def _first_text(*values: Any, default: str = "not_recorded") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _authority_block() -> dict[str, Any]:
    return {
        "proposal_recorded_not_applied": True,
        "learning_ledger_is_not_governance_approval": True,
        "no_order_or_proof_authority": True,
        **LEARNING_AUTHORITY_FLAGS,
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


def _source_refs() -> dict[str, str]:
    return {
        "self_model_ref": f"data/runtime/{SELF_MODEL_ARTIFACT}",
        "paperops_summary_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
        "paperops_gate_ref": f"data/runtime/{PAPEROPS_GATE_ARTIFACT}",
        "paperops_gate_records_ref": f"data/runtime/{PAPEROPS_GATE_RECORDS_ARTIFACT}",
        "router_ref": f"data/runtime/{ROUTER_ARTIFACT}",
        "router_decisions_ref": f"data/runtime/{ROUTER_DECISIONS_ARTIFACT}",
        "strategy_foundry_ref": f"data/runtime/{STRATEGY_FOUNDRY_ARTIFACT}",
        "rejected_strategy_hypotheses_ref": f"data/runtime/{REJECTED_STRATEGY_HYPOTHESES_ARTIFACT}",
        "akber_filter_ref": f"data/runtime/{AKBER_FILTER_ARTIFACT}",
        "akber_filter_results_ref": f"data/runtime/{AKBER_FILTER_RESULTS_ARTIFACT}",
        "shadow_simulator_ref": f"data/runtime/{SHADOW_SIMULATOR_ARTIFACT}",
        "shadow_results_ref": f"data/runtime/{SHADOW_RESULTS_ARTIFACT}",
        "linear_lab_ref": f"data/runtime/{LINEAR_LAB_ARTIFACT}",
        "linear_backtest_results_ref": f"data/runtime/{LINEAR_BACKTEST_RESULTS_ARTIFACT}",
        "nonlinear_lab_ref": f"data/runtime/{NONLINEAR_LAB_ARTIFACT}",
        "nonlinear_results_ref": f"data/runtime/{NONLINEAR_RESULTS_ARTIFACT}",
        "quantum_reviews_ref": f"data/runtime/{QUANTUM_REVIEWS_ARTIFACT}",
        "historical_memory_ref": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
        "universal_matrix_ref": f"data/runtime/{UNIVERSAL_MATRIX_ARTIFACT}",
        "full_pattern_search_ref": f"data/runtime/{FULL_PATTERN_SEARCH_ARTIFACT}",
        "phase0_ref": f"data/runtime/{PHASE0_ARTIFACT}",
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    filenames = {
        "self_model": SELF_MODEL_ARTIFACT,
        "paperops_summary": PAPEROPS_SUMMARY_ARTIFACT,
        "paperops_gate": PAPEROPS_GATE_ARTIFACT,
        "router": ROUTER_ARTIFACT,
        "strategy_foundry": STRATEGY_FOUNDRY_ARTIFACT,
        "akber_filter": AKBER_FILTER_ARTIFACT,
        "shadow_simulator": SHADOW_SIMULATOR_ARTIFACT,
        "linear_lab": LINEAR_LAB_ARTIFACT,
        "nonlinear_lab": NONLINEAR_LAB_ARTIFACT,
        "historical_memory": HISTORICAL_MEMORY_ARTIFACT,
        "universal_matrix": UNIVERSAL_MATRIX_ARTIFACT,
        "full_pattern_search": FULL_PATTERN_SEARCH_ARTIFACT,
        "phase0": PHASE0_ARTIFACT,
    }
    return {
        "runtime_dir": runtime,
        **{key: _read_json(runtime / filename) for key, filename in filenames.items()},
        "paperops_gate_records": _read_jsonl(runtime / PAPEROPS_GATE_RECORDS_ARTIFACT),
        "paperops_handoffs": _read_jsonl(runtime / PAPEROPS_HANDOFF_RECORDS_ARTIFACT),
        "paperops_rejected_handoffs": _read_jsonl(runtime / PAPEROPS_REJECTED_HANDOFFS_ARTIFACT),
        "router_decisions": _read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT),
        "rejected_strategy_hypotheses": _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_RESULTS_ARTIFACT),
        "shadow_results": _read_jsonl(runtime / SHADOW_RESULTS_ARTIFACT),
        "linear_backtest_results": _read_jsonl(runtime / LINEAR_BACKTEST_RESULTS_ARTIFACT),
        "nonlinear_results": _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT),
        "input_snapshots": {name: _runtime_file_snapshot(runtime, filename) for name, filename in filenames.items()},
    }


def _artifact_missing(context: dict[str, Any], key: str) -> bool:
    value = context.get(key)
    return not isinstance(value, dict) or not value


def _record_by_id(records: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    if not value:
        return {}
    for record in records:
        if record.get(key) == value:
            return record
    return {}


def _component_map(default: str = "unknown", reason: str = "No direct evidence available for this component.") -> dict[str, dict[str, str]]:
    return {component: {"contribution": default, "reason": reason} for component in COMPONENTS}


def _set_component(
    components: dict[str, dict[str, str]],
    component: str,
    contribution: str,
    reason: str,
) -> None:
    if component in components:
        components[component] = {"contribution": contribution, "reason": reason}


def _component_attribution_for_backtest(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    components = _component_map("not_applicable", "Not part of this historical backtest observation.")
    _set_component(components, "source_universe", "helped", "Source recipe and source names were preserved for replay.")
    _set_component(components, "historical_source_price_memory", "helped", "Historical memory supplied point-in-time samples.")
    _set_component(components, "universal_source_price_pattern_matrix", "helped", "Matrix lineage was retained through the source pattern.")
    _set_component(components, "linear_pattern_recognition_lab", "helped", "Linear lab produced transparent tests and walk-forward diagnostics.")
    _set_component(components, "nonlinear_and_quantum_pattern_lab", "neutral", "Nonlinear review is downstream evidence, not the source of this backtest.")
    _set_component(components, "ibm_quantum_gates_oracle", "not_applicable", "Quantum review is separated from this linear evidence class.")
    _set_component(components, "akber_filter", "not_applicable", "Akber Filter is downstream of the backtest observation.")
    _set_component(components, "strategy_router", "not_applicable", "Router does not act on raw backtest observations.")
    _set_component(components, "paperops_gate_interface", "not_applicable", "Backtest evidence cannot enter PaperOps directly.")
    _set_component(components, "guarded_alpaca_paper_route", "not_applicable", "Backtest evidence is research-only and route-disabled.")
    if record.get("accepted_as_validated_edge") is False:
        _set_component(components, "linear_pattern_recognition_lab", "helped", "Linear lab withheld validated-edge status and kept evidence research-only.")
    return components


def _component_attribution_for_shadow(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    components = _component_map("not_applicable", "Not part of this shadow replay.")
    learning = record.get("learning_attribution", {})
    decision = record.get("decision", {})
    _set_component(components, "source_universe", "helped", "Source-price lineage remained attached to the shadow replay.")
    _set_component(components, "historical_source_price_memory", "helped", "Historical coverage supplied replay outcome context.")
    _set_component(components, "linear_pattern_recognition_lab", "helped", "Linear pattern IDs were carried into the replay lineage.")
    _set_component(components, "nonlinear_and_quantum_pattern_lab", "neutral", "Nonlinear evidence was reviewed but did not create order authority.")
    _set_component(components, "ibm_quantum_gates_oracle", "neutral", "Quantum refs stayed review-only and did not authorize a trade.")
    _set_component(components, "akber_filter", "helped" if learning.get("akber_contribution") == "reject" else "neutral", "Akber contribution was recorded as no-order shadow evidence.")
    _set_component(components, "strategy_foundry", "helped", "Foundry lineage remained attached without creating active strategy state.")
    _set_component(components, "strategy_router", "neutral", "Shadow result is router-ready evidence only when the replay decision allows it.")
    _set_component(components, "paperops_gate_interface", "not_applicable", "Shadow replay cannot create PaperOps handoffs.")
    _set_component(components, "execution_policy", "helped", "Replay explicitly withheld execution approval.")
    _set_component(components, "guarded_alpaca_paper_route", "blocked", _first_text(decision.get("reason"), default="No guarded paper route was opened by shadow evidence."))
    return components


def _component_attribution_for_router(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    components = _component_map("unknown", "Router record did not provide component-specific evidence.")
    gates = record.get("gates", {})
    _set_component(components, "source_universe", "helped" if gates.get("source_quorum") == "pass" else "blocked", "Router captured source quorum state.")
    _set_component(components, "source_quorum", "helped" if gates.get("source_quorum") == "pass" else "blocked", _first_text(gates.get("source_quorum"), default="not_recorded"))
    _set_component(components, "akber_filter", "blocked" if gates.get("akber_filter") == "reject" else "neutral", _first_text(gates.get("akber_filter"), default="not_recorded"))
    _set_component(components, "strategy_router", "helped", "Router selected a no-order state with explicit why-not-trading-now context.")
    _set_component(components, "paperops_gate_interface", "not_applicable", "Router output is upstream of PaperOps handoff review.")
    _set_component(components, "idempotency_ledger", "helped" if any("idempotency" in str(item) for item in record.get("hard_vetoes", [])) else "unknown", "Router retained idempotency and duplicate-submit holds.")
    _set_component(components, "qctrl_paper_consultation_hold", "neutral", "Q-CTRL was not bypassed by the router.")
    _set_component(components, "guarded_alpaca_paper_route", "blocked" if gates.get("paper_route") else "unknown", _first_text(gates.get("paper_route"), default="not_recorded"))
    _set_component(components, "execution_policy", "helped", "Router output is explicitly not execution approval.")
    return components


def _component_attribution_for_rejection(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    components = _component_map("unknown", "Rejected hypothesis record did not provide direct component evidence.")
    reasons = record.get("rejection_reasons") or []
    _set_component(components, "source_universe", "helped", "Source-price lineage survived into the rejection record.")
    _set_component(components, "strategy_foundry", "helped", "Foundry rejected or demoted a hypothesis before routing.")
    _set_component(components, "linear_pattern_recognition_lab", "neutral", "Linear evidence supported research but not paperability.")
    _set_component(components, "nonlinear_and_quantum_pattern_lab", "blocked" if "nonlinear_not_incremental" in reasons else "neutral", "Nonlinear review did not justify upgrading research confidence.")
    _set_component(components, "ibm_quantum_gates_oracle", "blocked" if "quantum_did_not_upgrade_research_confidence" in reasons else "neutral", "Quantum review did not grant trade authority or upgrade confidence.")
    _set_component(components, "akber_filter", "blocked" if any("instrument_is_observable" in str(reason) for reason in reasons) else "unknown", "Paperability blocker prevented Akber-ready downstream flow.")
    _set_component(components, "guarded_alpaca_paper_route", "blocked" if any("paper_route" in str(reason) or "observable" in str(reason) for reason in reasons) else "unknown", "Rejected hypothesis did not have a guarded paper route expression.")
    _set_component(components, "risk_agent", "neutral", "Risk concept remained conceptual; no risk approval was created.")
    return components


def _component_attribution_for_paperops_gate(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    components = _component_map("unknown", "PaperOps gate record did not provide direct component evidence.")
    decision = record.get("decision", {})
    gate_state = record.get("gate_state", {})
    rejection_reasons = decision.get("rejection_reasons", [])
    hold_reasons = decision.get("hold_reasons", [])
    _set_component(components, "source_quorum", "blocked" if "source_quorum_failed" in rejection_reasons else "helped", "PaperOps gate preserved source quorum state.")
    _set_component(components, "akber_filter", "blocked" if "akber_filter_failed" in rejection_reasons else "neutral", "Akber state was enforced before PaperOps handoff.")
    _set_component(components, "strategy_router", "helped", "Router lineage was retained in the gate record.")
    _set_component(components, "paperops_gate_interface", "helped", "Gate converted router output into context-only review, hold, or rejection.")
    _set_component(components, "idempotency_ledger", "blocked" if "duplicate_idempotency" in str(record.get("idempotency", {})) else "helped", "Idempotency material was generated without creating orders.")
    _set_component(components, "duplicate_exposure_check", "blocked" if "duplicate_exposure_conflict" in rejection_reasons else "neutral", "Duplicate exposure state was checked.")
    _set_component(components, "daily_drawdown_check", "blocked" if "daily_drawdown_breach" in rejection_reasons else "neutral", "Daily drawdown state was checked.")
    _set_component(components, "qctrl_paper_consultation_hold", "blocked" if "qctrl_paper_consultation_hold" in hold_reasons else "neutral", "Q-CTRL hold was not bypassed.")
    _set_component(components, "guarded_alpaca_paper_route", "blocked" if gate_state.get("guarded_alpaca_paper_route") != "available" else "helped", "Only the existing guarded Alpaca Paper route is recognized.")
    _set_component(components, "execution_policy", "helped", "Gate withheld execution approval and broker writes.")
    return components


def _component_attribution_for_system_defect(component: str, reason: str) -> dict[str, dict[str, str]]:
    components = _component_map("not_applicable", "Not implicated by this system-defect record.")
    mapped = {
        "operational_phase0": "self_healing_repair_loop",
        "source_state": "source_universe",
        "model_stack": "local_gemma_model",
        "quantum_state": "ibm_quantum_gates_oracle",
        "risk_state": "risk_agent",
        "learning_health": "self_healing_repair_loop",
        "paperops": "paperops_gate_interface",
        "route": "guarded_alpaca_paper_route",
        "telegram": "signal_integrity",
        "dashboard": "signal_integrity",
    }
    target = mapped.get(component, "self_healing_repair_loop")
    _set_component(components, target, "hurt", reason)
    _set_component(components, "self_healing_repair_loop", "helped", "Defect was separated from strategy failure and routed as a repair/review item.")
    return components


def _proposal(
    proposal_type: str,
    target_surface: str,
    target_id: str,
    evidence_refs: list[str],
    *,
    reason: str,
    current_value: Any = "unchanged",
    proposed_value: Any = "approval_required_review",
    suggested_delta: float = 0.0,
    supporting_record_count: int = 1,
    contradicting_record_count: int = 0,
    real_paper_evidence_count: int = 0,
    shadow_evidence_count: int = 0,
    backtest_evidence_count: int = 0,
    overfit_risk: str = "medium",
    source_noise_risk: str = "medium",
    regime_bias_risk: str = "medium",
    expected_effect: str = "review_only_no_runtime_change",
) -> dict[str, Any]:
    proposal_id = _hash_id([proposal_type, target_surface, target_id, sorted(evidence_refs)], "qsase-proposal")
    return {
        "schema_version": SCHEMA_VERSION,
        "proposal_id": proposal_id,
        "proposal_type": proposal_type,
        "proposal_state": "ready_pending_learning_approval",
        "target_surface": target_surface,
        "target_id": target_id,
        "current_value": current_value,
        "proposed_value": proposed_value,
        "suggested_delta": suggested_delta,
        "evidence_refs": evidence_refs,
        "supporting_record_count": supporting_record_count,
        "contradicting_record_count": contradicting_record_count,
        "real_paper_evidence_count": real_paper_evidence_count,
        "shadow_evidence_count": shadow_evidence_count,
        "backtest_evidence_count": backtest_evidence_count,
        "overfit_risk": overfit_risk,
        "source_noise_risk": source_noise_risk,
        "regime_bias_risk": regime_bias_risk,
        "expected_effect": expected_effect,
        "approval_required": True,
        "apply_allowed": False,
        "applied": False,
    }


def _telegram_summary(outcome: str, cause: str, proposal_type: str) -> dict[str, Any]:
    text = (
        "Qadam learning note\n"
        f"Outcome: {str(outcome)[:48]}\n"
        f"Cause: {str(cause)[:72]}\n"
        f"Proposal: {str(proposal_type)[:48]}\n"
        "Applied: no"
    )
    return {
        "review_only": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "contains_command": False,
        "contains_broker_instruction": False,
        "text": text[:280],
    }


def _base_record(
    *,
    evidence_class: str,
    generated_at: str,
    lineage: dict[str, Any],
    decision_context: dict[str, Any],
    outcome_summary: dict[str, Any],
    component_attribution: dict[str, dict[str, str]],
    causal_assessment: dict[str, Any],
    proposal: dict[str, Any],
    source_refs: dict[str, str],
) -> dict[str, Any]:
    cause = _first_text(causal_assessment.get("label"), causal_assessment.get("primary_driver"), default=evidence_class)
    record_id = _hash_id(
        [SCHEMA_VERSION, evidence_class, lineage, decision_context.get("strategy_family"), outcome_summary.get("outcome_state")],
        "qsase-attribution",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "attribution_record_id": record_id,
        "status": "recorded_proposal_only",
        "evidence_class": evidence_class,
        "generated_at": generated_at,
        "lineage": lineage,
        "decision_context": decision_context,
        "outcome_summary": outcome_summary,
        "component_attribution": component_attribution,
        "causal_assessment": causal_assessment,
        "proposal": proposal,
        "source_refs": source_refs,
        "dashboard_decision_record": {
            "outcome": outcome_summary.get("outcome_state"),
            "cause": cause,
            "attribution": _top_component(component_attribution, "helped") or _top_component(component_attribution, "blocked") or "unknown",
            "proposal": proposal.get("proposal_type"),
            "applied": False,
        },
        "telegram_summary": _telegram_summary(outcome_summary.get("outcome_state", evidence_class), cause, proposal.get("proposal_type", "review")),
        "authority": _authority_block(),
        **LEARNING_AUTHORITY_FLAGS,
    }


def _strategy_family_from_record(record: dict[str, Any]) -> str:
    family = record.get("strategy_family")
    if isinstance(family, str) and family:
        return family
    family_payload = record.get("strategy_family")
    if isinstance(family_payload, dict):
        for key in ("primary_family", "mapped_existing_family", "proposed_new_family"):
            if family_payload.get(key):
                return str(family_payload[key])
    lineage = record.get("strategy_hypothesis_lineage") or record.get("research_goal_lineage") or record.get("lineage") or {}
    for key in ("strategy_family", "target_strategy_family"):
        if lineage.get(key):
            return str(lineage[key])
    market = record.get("market_expression") or {}
    if market.get("asset_class"):
        return str(market["asset_class"])
    return "unmapped_strategy_family"


def build_backtest_attribution_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = _iso(_now())
    source_refs = _source_refs()
    records: list[dict[str, Any]] = []
    for result in context.get("linear_backtest_results", []):
        market = result.get("market_expression", {})
        sample = result.get("sample", {})
        tests = result.get("tests", {})
        event_study = tests.get("event_study", {})
        walk_forward = tests.get("walk_forward_validation", {})
        strategy_family = _strategy_family_from_record(result)
        unique_dates = int(sample.get("unique_decision_date_count") or 0)
        label = "insufficient_evidence" if unique_dates < 3 else "worked_for_expected_reason"
        overfit_risk = "high" if unique_dates < 3 else "medium"
        proposal = _proposal(
            "hold_strategy_weight",
            "strategy_family",
            strategy_family,
            [f"data/runtime/{LINEAR_BACKTEST_RESULTS_ARTIFACT}#{result.get('linear_pattern_id')}"],
            reason="Backtest is research evidence only; hold strategy weighting until independent decision dates and paper evidence improve.",
            current_value="unchanged",
            proposed_value="unchanged_pending_more_evidence",
            backtest_evidence_count=1,
            overfit_risk=overfit_risk,
            expected_effect="keep backtest evidence separated from paper proof ledger",
        )
        records.append(
            _base_record(
                evidence_class="backtest_observation",
                generated_at=generated_at,
                lineage={
                    "source_pattern_id": result.get("source_pattern_id"),
                    "linear_pattern_id": result.get("linear_pattern_id"),
                    "research_goal_id": result.get("research_goal_id"),
                    "paper_proof_ledger_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
                    "source_price_evidence_refs": result.get("source_pattern", {}).get("matrix_row_ids", [])[:8],
                },
                decision_context={
                    "strategy_family": strategy_family,
                    "instrument": market.get("instrument"),
                    "direction": market.get("direction"),
                    "horizon": market.get("horizon"),
                    "market_regime": result.get("source_recipe", {}).get("source_family"),
                    "decision_state": result.get("decision", {}).get("linear_status"),
                },
                outcome_summary={
                    "outcome_state": "backtest_observation",
                    "return_pct": round(_float(event_study.get("mean_forward_return")) * 100, 6),
                    "expectancy": result.get("risk", {}).get("expectancy"),
                    "hit_rate": result.get("risk", {}).get("hit_rate"),
                    "sample_count": event_study.get("sample_count") or sample.get("complete_forward_outcome_count"),
                    "walk_forward_status": walk_forward.get("walk_forward_status"),
                    "invalidation_hit": False,
                    "postmortem_label": label,
                },
                component_attribution=_component_attribution_for_backtest(result),
                causal_assessment={
                    "label": label,
                    "primary_driver": "source_price_backtest_evidence",
                    "secondary_driver": "walk_forward_and_false_positive_controls",
                    "suspected_luck_component": "unknown",
                    "source_noise_risk": "medium",
                    "regime_bias_risk": "high" if unique_dates < 3 else "medium",
                    "overfit_risk": overfit_risk,
                    "confidence": min(0.66, max(0.2, _float(result.get("linear_score"), 0.4))),
                },
                proposal=proposal,
                source_refs=source_refs,
            )
        )
    return records


def build_shadow_attribution_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = _iso(_now())
    source_refs = _source_refs()
    records: list[dict[str, Any]] = []
    for result in context.get("shadow_results", []):
        strategy_family = _strategy_family_from_record(result)
        decision = result.get("decision", {})
        outcome = result.get("outcome", {})
        label = "rejected_correctly" if outcome.get("avoided_false_positive") else "insufficient_evidence"
        proposal = _proposal(
            "hold_strategy_weight",
            "strategy_family",
            strategy_family,
            [f"data/runtime/{SHADOW_RESULTS_ARTIFACT}#{result.get('shadow_replay_id')}"],
            reason="Shadow result remains no-order research evidence and cannot become proof credit.",
            current_value="unchanged",
            proposed_value="unchanged_shadow_only",
            shadow_evidence_count=1,
            overfit_risk="medium",
            expected_effect="keep variant under observation without PaperOps submission",
        )
        records.append(
            _base_record(
                evidence_class="shadow_replay",
                generated_at=generated_at,
                lineage={
                    "strategy_hypothesis_id": result.get("strategy_hypothesis_id"),
                    "rejected_hypothesis_id": result.get("rejected_hypothesis_id"),
                    "shadow_replay_id": result.get("shadow_replay_id"),
                    "akber_filter_result_id": result.get("akber_filter_result_id"),
                    "research_goal_id": result.get("strategy_hypothesis_lineage", {}).get("research_goal_id"),
                    "source_price_lineage": result.get("source_price_lineage", {}),
                    "paper_lifecycle_ref": result.get("actual_decision", {}).get("paper_lifecycle_ref"),
                },
                decision_context={
                    "strategy_family": strategy_family,
                    "instrument": result.get("strategy_hypothesis_lineage", {}).get("instrument"),
                    "direction": result.get("strategy_hypothesis_lineage", {}).get("direction"),
                    "horizon": result.get("replay_mode"),
                    "market_regime": result.get("evidence_class"),
                    "decision_state": decision.get("shadow_status"),
                },
                outcome_summary={
                    "outcome_state": "shadow_replay",
                    "replay_mode": result.get("replay_mode"),
                    "hypothetical_return_pct": round(_float(outcome.get("hypothetical_return_5d")) * 100, 6),
                    "hypothetical_hit": outcome.get("hypothetical_hit"),
                    "avoided_false_positive": outcome.get("avoided_false_positive"),
                    "sample_count": outcome.get("sample_size"),
                    "paper_lifecycle_evidence_count": 0,
                    "proof_credit_allowed": False,
                    "postmortem_label": label,
                },
                component_attribution=_component_attribution_for_shadow(result),
                causal_assessment={
                    "label": label,
                    "primary_driver": "shadow_replay_no_order_evidence",
                    "secondary_driver": "akber_filter_and_route_boundary",
                    "suspected_luck_component": "unknown",
                    "source_noise_risk": "medium",
                    "regime_bias_risk": "medium",
                    "overfit_risk": "medium",
                    "confidence": _float(result.get("scores", {}).get("learning_value_score"), 0.5),
                },
                proposal=proposal,
                source_refs=source_refs,
            )
        )
    return records


def build_non_trade_attribution_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = _iso(_now())
    source_refs = _source_refs()
    router = context.get("router", {})
    paperops = context.get("paperops_summary", {})
    records: list[dict[str, Any]] = []
    why = router.get("why_not_trading_now") or {}
    if not why and context.get("router_decisions"):
        first_decision = context["router_decisions"][0].get("decision", {})
        why = {"reason": first_decision.get("why_not_trading_now"), "source": "router_decision"}
    reason = _first_text(why.get("reason"), why.get("why_not_trading_now"), paperops.get("status"), default="no_current_qsase_paper_trade")
    candidate_count = int(router.get("strategy_input_count") or len(context.get("router_decisions", [])))
    proposal = _proposal(
        "tighten_akber_filter",
        "akber_filter",
        "paperability_and_confirmation_gate",
        [f"data/runtime/{ROUTER_ARTIFACT}", f"data/runtime/{AKBER_FILTER_ARTIFACT}"],
        reason="No-trade decision is attributed to safety boundaries and weak paperability, so filter strictness remains proposal-only.",
        current_value="strict_route_and_confirmation_required",
        proposed_value="strict_route_and_confirmation_required",
        suggested_delta=0.0,
        supporting_record_count=max(candidate_count, 1),
        expected_effect="preserve no-trade discipline until a distinct paperable setup appears",
    )
    records.append(
        _base_record(
            evidence_class="non_trade_decision",
            generated_at=generated_at,
            lineage={
                "router_ref": f"data/runtime/{ROUTER_ARTIFACT}",
                "paperops_summary_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
                "research_goal_id": "aggregate_current_why_not_trading_now",
            },
            decision_context={
                "strategy_family": "aggregate_qsase_router_state",
                "instrument": "multiple_or_none",
                "direction": "no_trade",
                "horizon": "current_runtime",
                "market_regime": "qsase_review_only",
                "decision_state": "no_trade",
            },
            outcome_summary={
                "outcome_state": "non_trade_decision",
                "why_not_trading_now_reason": reason,
                "candidate_count": candidate_count,
                "held_candidate_count": router.get("held_count") or 0,
                "rejected_candidate_count": router.get("blocked_safety_boundary_count") or len(context.get("router_decisions", [])),
                "submitted_paper_order_count": paperops.get("paper_runtime", {}).get("submitted_paper_order_count", 0),
                "discipline_credit_assessment": "safety_boundary_preserved",
                "missed_opportunity_assessment": "not_evaluable_without_fresh_paperable_setup",
                "postmortem_label": "blocked_correctly",
            },
            component_attribution=_component_attribution_for_router(context["router_decisions"][0] if context.get("router_decisions") else {}),
            causal_assessment={
                "label": "blocked_correctly",
                "primary_driver": "akber_filter_and_paperability_safety_boundary",
                "secondary_driver": "router_no_order_state",
                "suspected_luck_component": "not_applicable",
                "source_noise_risk": "medium",
                "regime_bias_risk": "medium",
                "overfit_risk": "medium",
                "confidence": 0.62,
            },
            proposal=proposal,
            source_refs=source_refs,
        )
    )
    return records


def build_rejected_hypothesis_attribution_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = _iso(_now())
    source_refs = _source_refs()
    records: list[dict[str, Any]] = []
    for rejected in context.get("rejected_strategy_hypotheses", []):
        strategy_family = _strategy_family_from_record(rejected)
        reasons = rejected.get("rejection_reasons") or []
        label = "rejected_correctly"
        if not reasons:
            label = "insufficient_evidence"
        proposal = _proposal(
            "require_quantum_review",
            "strategy_family",
            strategy_family,
            [f"data/runtime/{REJECTED_STRATEGY_HYPOTHESES_ARTIFACT}#{rejected.get('rejected_hypothesis_id')}"],
            reason="Rejected hypothesis keeps nonlinear and quantum review explicit before any future strategy upgrade.",
            current_value="research_only_rejected_or_shadow",
            proposed_value="require_quantum_review_before_router_upgrade",
            supporting_record_count=1,
            overfit_risk="medium",
            expected_effect="prevent rejected hypotheses from silently becoming active strategy families",
        )
        records.append(
            _base_record(
                evidence_class="rejected_hypothesis",
                generated_at=generated_at,
                lineage={
                    "rejected_hypothesis_id": rejected.get("rejected_hypothesis_id"),
                    "strategy_hypothesis_id": rejected.get("strategy_hypothesis_id"),
                    "research_goal_id": rejected.get("research_goal_lineage", {}).get("research_goal_id"),
                    "source_price_pattern_lineage": rejected.get("source_price_pattern_lineage", {}),
                },
                decision_context={
                    "strategy_family": strategy_family,
                    "instrument": rejected.get("candidate_identity", {}).get("instrument"),
                    "direction": "not_approved",
                    "horizon": rejected.get("candidate_identity", {}).get("time_window"),
                    "market_regime": rejected.get("proposed_hypothesis_type"),
                    "decision_state": rejected.get("decision_type"),
                },
                outcome_summary={
                    "outcome_state": "rejected_hypothesis",
                    "rejection_reasons": reasons,
                    "paperability_state": rejected.get("paperability", {}).get("paperability_state"),
                    "akber_filter_passed": rejected.get("akber_filter_passed"),
                    "strategy_approved": rejected.get("strategy_approved"),
                    "postmortem_label": label,
                },
                component_attribution=_component_attribution_for_rejection(rejected),
                causal_assessment={
                    "label": label,
                    "primary_driver": "strategy_foundry_rejection",
                    "secondary_driver": "paperability_or_quantum_hold",
                    "suspected_luck_component": "unknown",
                    "source_noise_risk": "medium",
                    "regime_bias_risk": "medium",
                    "overfit_risk": "medium",
                    "confidence": 0.58,
                },
                proposal=proposal,
                source_refs=source_refs,
            )
        )
    return records


def build_component_attribution_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = _iso(_now())
    source_refs = _source_refs()
    records: list[dict[str, Any]] = []
    for gate_record in context.get("paperops_gate_records", []):
        strategy_family = _strategy_family_from_record(gate_record.get("candidate_identity", {}))
        proposal = _proposal(
            "paperops_gate_precheck_review",
            "paperops_gate",
            _first_text(gate_record.get("decision", {}).get("reason"), default="paperops_gate"),
            [f"data/runtime/{PAPEROPS_GATE_RECORDS_ARTIFACT}#{gate_record.get('paperops_gate_record_id')}"],
            reason="Blocked route or gate output should be reviewed as safety/route attribution, not strategy failure.",
            current_value="gate_enforced",
            proposed_value="gate_enforced_review_only",
            expected_effect="keep PaperOps handoff context separate from orders and proof credit",
        )
        records.append(
            _base_record(
                evidence_class="blocked_route",
                generated_at=generated_at,
                lineage={
                    "paperops_gate_record_id": gate_record.get("paperops_gate_record_id"),
                    "paperops_handoff_id": gate_record.get("paperops_handoff_id"),
                    "router_decision_id": gate_record.get("router_decision_id"),
                    "strategy_hypothesis_id": gate_record.get("strategy_hypothesis_id"),
                    "research_goal_id": gate_record.get("research_goal_lineage", {}).get("research_goal_id"),
                    "candidate_identity": gate_record.get("candidate_identity", {}),
                    "idempotency": gate_record.get("idempotency", {}),
                },
                decision_context={
                    "strategy_family": strategy_family,
                    "instrument": gate_record.get("candidate_identity", {}).get("instrument"),
                    "direction": "no_handoff",
                    "horizon": gate_record.get("candidate_identity", {}).get("time_window"),
                    "market_regime": "paperops_gate_review",
                    "decision_state": gate_record.get("status"),
                },
                outcome_summary={
                    "outcome_state": "blocked_route",
                    "gate_output": gate_record.get("status"),
                    "reason": gate_record.get("decision", {}).get("reason"),
                    "hold_reasons": gate_record.get("decision", {}).get("hold_reasons", []),
                    "rejection_reasons": gate_record.get("decision", {}).get("rejection_reasons", []),
                    "paper_order_created": False,
                    "broker_write_created": False,
                    "proof_credit_allowed": False,
                    "postmortem_label": "blocked_correctly",
                },
                component_attribution=_component_attribution_for_paperops_gate(gate_record),
                causal_assessment={
                    "label": "blocked_correctly",
                    "primary_driver": "paperops_gate_or_route_boundary",
                    "secondary_driver": _first_text(gate_record.get("decision", {}).get("reason"), default="gate_review"),
                    "suspected_luck_component": "not_applicable",
                    "source_noise_risk": "medium",
                    "regime_bias_risk": "medium",
                    "overfit_risk": "medium",
                    "confidence": 0.68,
                },
                proposal=proposal,
                source_refs=source_refs,
            )
        )
    return records


def build_system_defect_attribution_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = _iso(_now())
    source_refs = _source_refs()
    records: list[dict[str, Any]] = []
    self_model = context.get("self_model", {})
    defects = list(self_model.get("degraded_components") or [])
    for artifact_key in (
        "self_model",
        "paperops_summary",
        "paperops_gate",
        "router",
        "strategy_foundry",
        "akber_filter",
        "shadow_simulator",
        "linear_lab",
        "nonlinear_lab",
    ):
        if _artifact_missing(context, artifact_key):
            defects.append({"component": artifact_key, "reason": "required_input_artifact_missing", "severity": "defect"})
    seen: set[tuple[str, str]] = set()
    for defect in defects:
        component = str(defect.get("component") or "unknown_component")
        reason = str(defect.get("reason") or "unspecified_system_defect")
        key = (component, reason)
        if key in seen:
            continue
        seen.add(key)
        proposal_type = "source_coverage_repair_request" if component == "source_state" else "paperops_gate_precheck_review"
        if component == "model_stack":
            proposal_type = "hold_model_weight"
        target_surface = "system_repair"
        proposal = _proposal(
            proposal_type,
            target_surface,
            component,
            [f"data/runtime/{SELF_MODEL_ARTIFACT}#{component}:{reason}"],
            reason="System defect is separated from strategy performance and requires review or repair before attribution conclusions are applied.",
            current_value="defect_recorded",
            proposed_value="repair_or_review_required",
            expected_effect="prevent infrastructure defects from becoming strategy-weight changes",
        )
        records.append(
            _base_record(
                evidence_class="system_defect",
                generated_at=generated_at,
                lineage={
                    "self_model_ref": f"data/runtime/{SELF_MODEL_ARTIFACT}",
                    "component": component,
                    "severity": defect.get("severity"),
                    "paper_proof_ledger_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
                },
                decision_context={
                    "strategy_family": "not_strategy_failure",
                    "instrument": "not_applicable",
                    "direction": "repair_review",
                    "horizon": "current_runtime",
                    "market_regime": "system_health",
                    "decision_state": "system_defect_recorded",
                },
                outcome_summary={
                    "outcome_state": "system_defect",
                    "component": component,
                    "reason": reason,
                    "severity": defect.get("severity"),
                    "self_healing_repair_requested": True,
                    "strategy_weight_proposal_allowed": False,
                    "postmortem_label": "route_defect_prevented_evaluation",
                },
                component_attribution=_component_attribution_for_system_defect(component, reason),
                causal_assessment={
                    "label": "route_defect_prevented_evaluation",
                    "primary_driver": component,
                    "secondary_driver": reason,
                    "suspected_luck_component": "not_applicable",
                    "source_noise_risk": "unknown",
                    "regime_bias_risk": "unknown",
                    "overfit_risk": "not_applicable",
                    "confidence": 0.72,
                },
                proposal=proposal,
                source_refs=source_refs,
            )
        )
    return records


def build_real_paper_lifecycle_attribution_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = _iso(_now())
    source_refs = _source_refs()
    records: list[dict[str, Any]] = []
    paperops = context.get("paperops_summary", {})
    paper_runtime = paperops.get("paper_runtime", {})
    close_to_ledger = paperops.get("close_to_ledger", {})
    submitted = int(paper_runtime.get("submitted_paper_order_count") or 0)
    closed = int(close_to_ledger.get("closed_paper_trade_count") or 0)
    if submitted <= 0 and closed <= 0:
        return records
    proposal = _proposal(
        "hold_strategy_weight",
        "paper_lifecycle",
        "aggregate_current_paperops_outcome",
        [f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}"],
        reason="Real paper lifecycle evidence is referenced for attribution only and cannot create proof credit here.",
        current_value="unchanged",
        proposed_value="review_after_postmortem",
        real_paper_evidence_count=max(submitted, closed, 1),
        expected_effect="send paper lifecycle outcomes to review without mutating strategy policy",
    )
    records.append(
        _base_record(
            evidence_class="real_paper_lifecycle",
            generated_at=generated_at,
            lineage={
                "paper_lifecycle_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
                "paper_proof_ledger_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
                "research_goal_id": "aggregate_current_paperops_lifecycle",
            },
            decision_context={
                "strategy_family": "aggregate_paperops_lifecycle",
                "instrument": "paper_account",
                "direction": "paper_lifecycle_reference",
                "horizon": "current_runtime",
                "market_regime": "paperops_summary",
                "decision_state": paperops.get("status"),
            },
            outcome_summary={
                "outcome_state": "real_paper_lifecycle",
                "submitted_paper_order_count": submitted,
                "closed_paper_trade_count": closed,
                "paper_proof_ledger_credit_allowed": False,
                "postmortem_label": "insufficient_evidence",
            },
            component_attribution=_component_map("unknown", "Aggregate PaperOps paper lifecycle reference."),
            causal_assessment={
                "label": "insufficient_evidence",
                "primary_driver": "paperops_lifecycle_reference",
                "secondary_driver": "postmortem_required",
                "suspected_luck_component": "unknown",
                "source_noise_risk": "unknown",
                "regime_bias_risk": "unknown",
                "overfit_risk": "unknown",
                "confidence": 0.3,
            },
            proposal=proposal,
            source_refs=source_refs,
        )
    )
    return records


def _top_component(component_attribution: dict[str, dict[str, str]], contribution: str) -> str | None:
    for component, payload in component_attribution.items():
        if payload.get("contribution") == contribution:
            return component
    return None


def _record_evidence_ref(record: dict[str, Any]) -> str:
    return f"data/runtime/{LEDGER_JSONL_ARTIFACT}#{record.get('attribution_record_id')}"


def _proposal_artifact(
    artifact_type: str,
    proposal_surface: str,
    proposals: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "generated_at": generated_at,
        "status": "proposal_recorded_not_applied",
        "proposal_surface": proposal_surface,
        "proposal_count": len(proposals),
        "approval_required_count": len([proposal for proposal in proposals if proposal.get("approval_required") is True]),
        "approved_proposal_count": 0,
        "applied_update_count": 0,
        "apply_allowed": False,
        "applied": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "proposals": proposals,
        "authority": _authority_block(),
    }


def _dedupe_proposals(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        proposal_id = proposal["proposal_id"]
        if proposal_id not in deduped:
            deduped[proposal_id] = proposal
            continue
        existing = deduped[proposal_id]
        refs = sorted(set(existing.get("evidence_refs", []) + proposal.get("evidence_refs", [])))
        existing["evidence_refs"] = refs
        existing["supporting_record_count"] = int(existing.get("supporting_record_count") or 0) + int(
            proposal.get("supporting_record_count") or 0
        )
        existing["real_paper_evidence_count"] = int(existing.get("real_paper_evidence_count") or 0) + int(
            proposal.get("real_paper_evidence_count") or 0
        )
        existing["shadow_evidence_count"] = int(existing.get("shadow_evidence_count") or 0) + int(
            proposal.get("shadow_evidence_count") or 0
        )
        existing["backtest_evidence_count"] = int(existing.get("backtest_evidence_count") or 0) + int(
            proposal.get("backtest_evidence_count") or 0
        )
    return list(deduped.values())


def build_strategy_weight_proposals(attribution_records: list[dict[str, Any]]) -> dict[str, Any]:
    generated_at = _iso(_now())
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in attribution_records:
        if record.get("evidence_class") == "system_defect":
            continue
        family = _first_text(record.get("decision_context", {}).get("strategy_family"), default="unmapped_strategy_family")
        grouped[family].append(record)
    proposals: list[dict[str, Any]] = []
    for family, records in sorted(grouped.items()):
        evidence_counts = Counter(record["evidence_class"] for record in records)
        proposal_type = "hold_strategy_weight"
        if evidence_counts.get("rejected_hypothesis", 0) > evidence_counts.get("real_paper_lifecycle", 0):
            proposal_type = "decrease_strategy_weight"
        if evidence_counts.get("real_paper_lifecycle", 0) and not evidence_counts.get("rejected_hypothesis", 0):
            proposal_type = "hold_strategy_weight"
        proposals.append(
            _proposal(
                proposal_type,
                "strategy_family",
                family,
                [_record_evidence_ref(record) for record in records[:20]],
                reason="Strategy-weight proposal is evidence-separated and approval-gated; no update is applied by QSASE-12.",
                current_value="unchanged",
                proposed_value="review_required_not_applied",
                suggested_delta=0.0 if proposal_type == "hold_strategy_weight" else -0.02,
                supporting_record_count=len(records),
                real_paper_evidence_count=evidence_counts.get("real_paper_lifecycle", 0),
                shadow_evidence_count=evidence_counts.get("shadow_replay", 0),
                backtest_evidence_count=evidence_counts.get("backtest_observation", 0),
                overfit_risk="high" if evidence_counts.get("backtest_observation", 0) and not evidence_counts.get("real_paper_lifecycle", 0) else "medium",
                expected_effect="proposal_only_strategy_review",
            )
        )
    return _proposal_artifact(
        "qsase_strategy_weight_proposals",
        "strategy_weight",
        _dedupe_proposals(proposals),
        generated_at,
    )


def build_source_trust_proposals(attribution_records: list[dict[str, Any]]) -> dict[str, Any]:
    generated_at = _iso(_now())
    source_records = [
        record
        for record in attribution_records
        if record.get("evidence_class") in {"backtest_observation", "system_defect", "non_trade_decision"}
    ]
    proposal_type = "hold_source_trust"
    if any(record.get("evidence_class") == "system_defect" and record.get("lineage", {}).get("component") == "source_state" for record in source_records):
        proposal_type = "source_coverage_repair_request"
    proposals = [
        _proposal(
            proposal_type,
            "source_universe",
            "aggregate_source_trust_and_coverage",
            [_record_evidence_ref(record) for record in source_records[:30]],
            reason="Source trust remains unchanged until source coverage gaps and later market confirmation are reviewed.",
            current_value="unchanged",
            proposed_value="repair_or_hold_pending_approval",
            supporting_record_count=len(source_records),
            backtest_evidence_count=len([record for record in source_records if record.get("evidence_class") == "backtest_observation"]),
            expected_effect="source_trust_review_only_no_score_mutation",
        )
    ] if source_records else []
    return _proposal_artifact("qsase_source_trust_proposals", "source_trust", proposals, generated_at)


def build_model_weight_proposals(attribution_records: list[dict[str, Any]]) -> dict[str, Any]:
    generated_at = _iso(_now())
    model_records = [
        record
        for record in attribution_records
        if record.get("evidence_class") == "system_defect" and record.get("lineage", {}).get("component") in {"model_stack", "quantum_state"}
    ]
    proposals = [
        _proposal(
            "hold_model_weight",
            "model_stack",
            "local_gemma_frontier_gemini_quantum_review_stack",
            [_record_evidence_ref(record) for record in model_records],
            reason="Model and quantum weights stay unchanged while provider/readiness evidence is degraded or stale.",
            current_value="unchanged",
            proposed_value="unchanged_until_provider_readiness_validated",
            supporting_record_count=len(model_records),
            expected_effect="model_weight_review_only_no_update",
        )
    ] if model_records else []
    return _proposal_artifact("qsase_model_weight_proposals", "model_weight", proposals, generated_at)


def build_filter_threshold_proposals(attribution_records: list[dict[str, Any]]) -> dict[str, Any]:
    generated_at = _iso(_now())
    filter_records = [
        record
        for record in attribution_records
        if record.get("component_attribution", {}).get("akber_filter", {}).get("contribution") in {"helped", "blocked"}
    ]
    proposals = [
        _proposal(
            "tighten_akber_filter",
            "akber_filter",
            "paperability_confirmation_threshold",
            [_record_evidence_ref(record) for record in filter_records[:30]],
            reason="Akber filter is currently preventing non-paperable or weakly confirmed setups; keep any threshold change approval-gated.",
            current_value="strict_paperability_confirmation",
            proposed_value="strict_paperability_confirmation",
            suggested_delta=0.0,
            supporting_record_count=len(filter_records),
            shadow_evidence_count=len([record for record in filter_records if record.get("evidence_class") == "shadow_replay"]),
            expected_effect="filter_threshold_review_only_no_update",
        )
    ] if filter_records else []
    return _proposal_artifact("qsase_filter_threshold_proposals", "filter_threshold", proposals, generated_at)


def build_learning_approval_queue(proposals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    generated_at = _iso(_now())
    queue_items: list[dict[str, Any]] = []
    for artifact_name, artifact in proposals.items():
        for proposal in artifact.get("proposals", []):
            queue_items.append(
                {
                    "approval_queue_id": _hash_id([artifact_name, proposal.get("proposal_id")], "qsase-learning-approval"),
                    "proposal_id": proposal.get("proposal_id"),
                    "proposal_type": proposal.get("proposal_type"),
                    "proposal_surface": proposal.get("target_surface"),
                    "target_id": proposal.get("target_id"),
                    "source_artifact": artifact_name,
                    "approval_required": True,
                    "approved": False,
                    "apply_allowed": False,
                    "applied": False,
                    "evidence_refs": proposal.get("evidence_refs", []),
                    "review_state": "pending_learning_approval",
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_learning_approval_queue",
        "generated_at": generated_at,
        "status": "approval_required_no_updates_applied",
        "approval_required_count": len(queue_items),
        "approved_proposal_count": 0,
        "applied_update_count": 0,
        "queue_items": queue_items,
        "apply_allowed": False,
        "applied": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority_block(),
    }


def _proposal_counts(proposal_artifacts: dict[str, dict[str, Any]]) -> dict[str, int]:
    return {name: int(artifact.get("proposal_count") or 0) for name, artifact in proposal_artifacts.items()}


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    latest = payload.get("attribution_records", [None])[0] if payload.get("attribution_records") else {}
    if payload.get("system_defect_records"):
        latest = payload["system_defect_records"][0]
    decision = (latest or {}).get("dashboard_decision_record", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_learning_attribution_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "decision_record_based": True,
        "essay_free": True,
        "latest_attribution_state": (latest or {}).get("status"),
        "latest_evidence_class": (latest or {}).get("evidence_class"),
        "latest_outcome": decision.get("outcome"),
        "latest_cause": decision.get("cause"),
        "latest_attribution": decision.get("attribution"),
        "latest_proposal": decision.get("proposal"),
        "proposal_applied": False,
        "real_paper_evidence_count": payload["real_paper_lifecycle_record_count"],
        "shadow_evidence_count": payload["shadow_replay_record_count"],
        "backtest_evidence_count": payload["backtest_record_count"],
        "non_trade_learning_count": payload["non_trade_record_count"],
        "rejected_hypothesis_learning_count": payload["rejected_hypothesis_record_count"],
        "system_defect_record_count": payload["system_defect_record_count"],
        "top_credited_component": payload["top_credited_component"],
        "top_blamed_component": payload["top_blamed_component"],
        "active_proposal_count": payload["active_proposal_count"],
        "approval_required_count": payload["approval_required_count"],
        "applied_update_count": payload["applied_update_count"],
        "proof_boundary": "ledger references but cannot create paper proof ledger credit",
        "live_capital_boundary": "live capital disabled",
        "decision_records": [
            {
                "evidence_class": record.get("evidence_class"),
                "outcome": record.get("dashboard_decision_record", {}).get("outcome"),
                "cause": record.get("dashboard_decision_record", {}).get("cause"),
                "attribution": record.get("dashboard_decision_record", {}).get("attribution"),
                "proposal": record.get("dashboard_decision_record", {}).get("proposal"),
                "applied": False,
            }
            for record in payload.get("attribution_records", [])[:8]
        ],
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
    }


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    for key in (
        "attribution_records",
        "real_paper_lifecycle_records",
        "non_trade_records",
        "shadow_replay_records",
        "backtest_records",
        "rejected_hypothesis_records",
        "blocked_route_records",
        "system_defect_records",
    ):
        summary.pop(key, None)
    return summary


def build_learning_attribution_ledger(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    backtest_records = build_backtest_attribution_records(context)
    shadow_records = build_shadow_attribution_records(context)
    non_trade_records = build_non_trade_attribution_records(context)
    rejected_records = build_rejected_hypothesis_attribution_records(context)
    blocked_route_records = build_component_attribution_records(context)
    system_defect_records = build_system_defect_attribution_records(context)
    real_paper_records = build_real_paper_lifecycle_attribution_records(context)
    attribution_records = (
        real_paper_records
        + non_trade_records
        + shadow_records
        + backtest_records
        + rejected_records
        + blocked_route_records
        + system_defect_records
    )
    component_counter: Counter[str] = Counter()
    blame_counter: Counter[str] = Counter()
    for record in attribution_records:
        for component, payload in record.get("component_attribution", {}).items():
            if payload.get("contribution") == "helped":
                component_counter[component] += 1
            if payload.get("contribution") in {"hurt", "blocked"}:
                blame_counter[component] += 1
    strategy_proposals = build_strategy_weight_proposals(attribution_records)
    source_proposals = build_source_trust_proposals(attribution_records)
    model_proposals = build_model_weight_proposals(attribution_records)
    filter_proposals = build_filter_threshold_proposals(attribution_records)
    proposal_artifacts = {
        "strategy_weight_proposals": strategy_proposals,
        "source_trust_proposals": source_proposals,
        "model_weight_proposals": model_proposals,
        "filter_threshold_proposals": filter_proposals,
    }
    approval_queue = build_learning_approval_queue(proposal_artifacts)
    missing_required_state = [
        key
        for key in (
            "self_model",
            "paperops_summary",
            "paperops_gate",
            "router",
            "strategy_foundry",
            "akber_filter",
            "shadow_simulator",
            "linear_lab",
            "nonlinear_lab",
        )
        if _artifact_missing(context, key)
    ]
    status = "qsase_learning_attribution_ledger_ready"
    if missing_required_state:
        status = "qsase_learning_attribution_ledger_blocked"
    elif system_defect_records or not real_paper_records:
        status = "qsase_learning_attribution_ledger_degraded"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_component_attribution_ledger",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "approval_required": True,
        "attribution_record_count": len(attribution_records),
        "real_paper_lifecycle_record_count": len(real_paper_records),
        "non_trade_record_count": len(non_trade_records),
        "shadow_replay_record_count": len(shadow_records),
        "backtest_record_count": len(backtest_records),
        "rejected_hypothesis_record_count": len(rejected_records),
        "blocked_route_record_count": len(blocked_route_records),
        "system_defect_record_count": len(system_defect_records),
        "strategy_weight_proposal_count": strategy_proposals["proposal_count"],
        "source_trust_proposal_count": source_proposals["proposal_count"],
        "model_weight_proposal_count": model_proposals["proposal_count"],
        "filter_threshold_proposal_count": filter_proposals["proposal_count"],
        "active_proposal_count": sum(_proposal_counts(proposal_artifacts).values()),
        "approval_required_count": approval_queue["approval_required_count"],
        "approved_proposal_count": 0,
        "applied_update_count": 0,
        "learning_write_created": False,
        "strategy_mutation_created": False,
        "policy_mutation_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "live_capital_enabled": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "strategy_source_model_filter_changes_are_proposals_only": True,
        "paper_proof_ledger_credit_created": False,
        "input_artifacts": _source_refs(),
        "input_snapshots": context.get("input_snapshots", {}),
        "missing_required_state": missing_required_state,
        "top_credited_component": component_counter.most_common(1)[0][0] if component_counter else "unknown",
        "top_blamed_component": blame_counter.most_common(1)[0][0] if blame_counter else "unknown",
        "attribution_records": attribution_records,
        "real_paper_lifecycle_records": real_paper_records,
        "non_trade_records": non_trade_records,
        "shadow_replay_records": shadow_records,
        "backtest_records": backtest_records,
        "rejected_hypothesis_records": rejected_records,
        "blocked_route_records": blocked_route_records,
        "system_defect_records": system_defect_records,
        "strategy_weight_proposals": strategy_proposals,
        "source_trust_proposals": source_proposals,
        "model_weight_proposals": model_proposals,
        "filter_threshold_proposals": filter_proposals,
        "learning_approval_queue": approval_queue,
        "authority": universal_authority_flags(),
        "authority_flags": dict(LEARNING_AUTHORITY_FLAGS),
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def load_learning_attribution_ledger(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        records = _read_jsonl(runtime / LEDGER_JSONL_ARTIFACT)
        payload["attribution_records"] = records
        payload["real_paper_lifecycle_records"] = [record for record in records if record.get("evidence_class") == "real_paper_lifecycle"]
        payload["non_trade_records"] = [record for record in records if record.get("evidence_class") == "non_trade_decision"]
        payload["shadow_replay_records"] = [record for record in records if record.get("evidence_class") == "shadow_replay"]
        payload["backtest_records"] = [record for record in records if record.get("evidence_class") == "backtest_observation"]
        payload["rejected_hypothesis_records"] = [record for record in records if record.get("evidence_class") == "rejected_hypothesis"]
        payload["blocked_route_records"] = [record for record in records if record.get("evidence_class") == "blocked_route"]
        payload["system_defect_records"] = [record for record in records if record.get("evidence_class") == "system_defect"]
        payload["strategy_weight_proposals"] = _read_json(runtime / STRATEGY_WEIGHT_PROPOSALS_ARTIFACT)
        payload["source_trust_proposals"] = _read_json(runtime / SOURCE_TRUST_PROPOSALS_ARTIFACT)
        payload["model_weight_proposals"] = _read_json(runtime / MODEL_WEIGHT_PROPOSALS_ARTIFACT)
        payload["filter_threshold_proposals"] = _read_json(runtime / FILTER_THRESHOLD_PROPOSALS_ARTIFACT)
        payload["learning_approval_queue"] = _read_json(runtime / LEARNING_APPROVAL_QUEUE_ARTIFACT)
        payload["dashboard_safe_summary"] = _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT)
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in LEARNING_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def _validate_proposal(proposal: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for field in (
        "proposal_id",
        "proposal_type",
        "proposal_state",
        "target_surface",
        "target_id",
        "evidence_refs",
        "approval_required",
        "apply_allowed",
        "applied",
    ):
        if field not in proposal:
            errors.append(f"{prefix}_proposal_missing_{field}")
    if not proposal.get("evidence_refs"):
        errors.append(f"{prefix}_proposal_missing_evidence_refs")
    if proposal.get("approval_required") is not True:
        errors.append(f"{prefix}_proposal_approval_required_must_be_true")
    if proposal.get("apply_allowed") is not False:
        errors.append(f"{prefix}_proposal_apply_allowed_must_be_false")
    if proposal.get("applied") is not False:
        errors.append(f"{prefix}_proposal_applied_must_be_false")
    return errors


def _validate_proposal_artifact(artifact: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    if artifact.get("status") != "proposal_recorded_not_applied":
        errors.append(f"{prefix}_status_invalid")
    if artifact.get("apply_allowed") is not False or artifact.get("applied") is not False:
        errors.append(f"{prefix}_must_not_apply")
    if int(artifact.get("applied_update_count", -1) or 0) != 0:
        errors.append(f"{prefix}_applied_update_count_must_be_zero")
    if int(artifact.get("approved_proposal_count", -1) or 0) != 0:
        errors.append(f"{prefix}_approved_proposal_count_must_be_zero")
    if int(artifact.get("paper_order_created_count", -1) or 0) != 0:
        errors.append(f"{prefix}_paper_order_created_count_must_be_zero")
    if int(artifact.get("broker_write_count", -1) or 0) != 0:
        errors.append(f"{prefix}_broker_write_count_must_be_zero")
    if artifact.get("proof_credit_allowed") is not False or artifact.get("live_capital_enabled") is not False:
        errors.append(f"{prefix}_proof_or_live_boundary_failed")
    proposals = artifact.get("proposals")
    if not isinstance(proposals, list):
        errors.append(f"{prefix}_proposals_missing")
        proposals = []
    if artifact.get("proposal_count") != len(proposals):
        errors.append(f"{prefix}_proposal_count_mismatch")
    for proposal in proposals:
        errors.extend(_validate_proposal(proposal, prefix))
    errors.extend(_validate_authority(artifact.get("authority", {}), f"{prefix}_authority"))
    return errors


def validate_learning_attribution_ledger(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_component_attribution_ledger":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_learning_attribution_ledger_ready",
        "qsase_learning_attribution_ledger_degraded",
        "qsase_learning_attribution_ledger_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    for key in (
        "paper_only",
        "research_only",
        "proposal_first",
        "approval_required",
        "strategy_source_model_filter_changes_are_proposals_only",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "proof_credit_allowed",
        "paper_proof_ledger_credit_allowed",
        "live_capital_enabled",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
        "learning_write_created",
        "strategy_mutation_created",
        "policy_mutation_created",
        "model_weight_update_created",
        "trust_score_update_created",
        "paper_proof_ledger_credit_created",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    for key in ("applied_update_count", "approved_proposal_count", "paper_order_created_count", "broker_write_count"):
        if int(payload.get(key, -1) or 0) != 0:
            errors.append(f"{key}_must_be_zero")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "ledger"))
    records = payload.get("attribution_records")
    if not isinstance(records, list):
        errors.append("attribution_records_missing")
        records = []
    if payload.get("attribution_record_count") != len(records):
        errors.append("attribution_record_count_mismatch")
    count_by_class = Counter(record.get("evidence_class") for record in records)
    expected_count_fields = {
        "real_paper_lifecycle": "real_paper_lifecycle_record_count",
        "non_trade_decision": "non_trade_record_count",
        "shadow_replay": "shadow_replay_record_count",
        "backtest_observation": "backtest_record_count",
        "rejected_hypothesis": "rejected_hypothesis_record_count",
        "blocked_route": "blocked_route_record_count",
        "system_defect": "system_defect_record_count",
    }
    for evidence_class, count_field in expected_count_fields.items():
        if payload.get(count_field) != count_by_class.get(evidence_class, 0):
            errors.append(f"{count_field}_mismatch")
    for required_class in ("non_trade_decision", "shadow_replay", "backtest_observation", "rejected_hypothesis", "system_defect"):
        if count_by_class.get(required_class, 0) <= 0:
            errors.append(f"{required_class}_must_be_first_class_record")
    for record in records:
        record_id = record.get("attribution_record_id")
        for field in REQUIRED_RECORD_FIELDS:
            if field not in record:
                errors.append(f"record_{record_id}_missing_{field}")
        if record.get("status") != "recorded_proposal_only":
            errors.append(f"record_{record_id}_status_invalid")
        if record.get("evidence_class") not in EVIDENCE_CLASSES:
            errors.append(f"record_{record_id}_evidence_class_invalid")
        components = record.get("component_attribution", {})
        for component in COMPONENTS:
            if component not in components:
                errors.append(f"record_{record_id}_missing_component_{component}")
            elif components[component].get("contribution") not in CONTRIBUTIONS:
                errors.append(f"record_{record_id}_component_{component}_contribution_invalid")
        causal = record.get("causal_assessment", {})
        if causal.get("label") not in CAUSAL_LABELS:
            errors.append(f"record_{record_id}_causal_label_invalid")
        if record.get("evidence_class") in {"shadow_replay", "backtest_observation"}:
            if record.get("outcome_summary", {}).get("proof_credit_allowed") is not False and record.get("proof_credit_allowed") is not False:
                errors.append(f"record_{record_id}_shadow_or_backtest_proof_boundary_failed")
        if record.get("evidence_class") == "system_defect":
            if record.get("outcome_summary", {}).get("strategy_weight_proposal_allowed") is not False:
                errors.append(f"record_{record_id}_system_defect_strategy_weight_proposal_allowed")
        errors.extend(_validate_proposal(record.get("proposal", {}), f"record_{record_id}"))
        errors.extend(_validate_authority(record.get("authority", {}), f"record_{record_id}_authority"))
        telegram = record.get("telegram_summary", {})
        if telegram.get("review_only") is not True or telegram.get("command_disabled") is not True:
            errors.append(f"record_{record_id}_telegram_not_review_only")
        if telegram.get("contains_command") is not False or telegram.get("contains_broker_instruction") is not False:
            errors.append(f"record_{record_id}_telegram_command_or_broker_language")
        if len(str(telegram.get("text") or "")) > 320:
            errors.append(f"record_{record_id}_telegram_too_long")
        for key in LEARNING_AUTHORITY_FLAGS:
            if record.get(key) is not False:
                errors.append(f"record_{record_id}_{key}_must_be_false")
    for artifact_key, prefix in (
        ("strategy_weight_proposals", "strategy_weight_proposals"),
        ("source_trust_proposals", "source_trust_proposals"),
        ("model_weight_proposals", "model_weight_proposals"),
        ("filter_threshold_proposals", "filter_threshold_proposals"),
    ):
        artifact = payload.get(artifact_key, {})
        errors.extend(_validate_proposal_artifact(artifact, prefix))
    for proposal in payload.get("strategy_weight_proposals", {}).get("proposals", []):
        for evidence_ref in proposal.get("evidence_refs", []):
            record = _record_by_id(records, "attribution_record_id", str(evidence_ref).split("#")[-1])
            if record.get("evidence_class") == "system_defect":
                errors.append("system_defect_must_not_create_strategy_weight_proposals")
    queue = payload.get("learning_approval_queue", {})
    if queue.get("status") != "approval_required_no_updates_applied":
        errors.append("learning_approval_queue_status_invalid")
    if queue.get("apply_allowed") is not False or queue.get("applied") is not False:
        errors.append("learning_approval_queue_must_not_apply")
    if int(queue.get("applied_update_count", -1) or 0) != 0:
        errors.append("learning_approval_queue_applied_update_count_must_be_zero")
    if int(queue.get("approved_proposal_count", -1) or 0) != 0:
        errors.append("learning_approval_queue_approved_proposal_count_must_be_zero")
    for item in queue.get("queue_items", []):
        if item.get("approval_required") is not True or item.get("approved") is not False:
            errors.append("learning_approval_queue_item_state_invalid")
        if item.get("apply_allowed") is not False or item.get("applied") is not False:
            errors.append("learning_approval_queue_item_must_not_apply")
    summary = payload.get("dashboard_safe_summary", {})
    if summary:
        if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_public_safe_required")
        if summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
        if summary.get("decision_record_based") is not True or summary.get("essay_free") is not True:
            errors.append("dashboard_summary_must_be_decision_record_based")
        if summary.get("proposal_applied") is not False:
            errors.append("dashboard_summary_proposal_applied_must_be_false")
    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "ledger_records_path": f"data/runtime/{LEDGER_JSONL_ARTIFACT}",
        "strategy_weight_proposals_path": f"data/runtime/{STRATEGY_WEIGHT_PROPOSALS_ARTIFACT}",
        "source_trust_proposals_path": f"data/runtime/{SOURCE_TRUST_PROPOSALS_ARTIFACT}",
        "model_weight_proposals_path": f"data/runtime/{MODEL_WEIGHT_PROPOSALS_ARTIFACT}",
        "filter_threshold_proposals_path": f"data/runtime/{FILTER_THRESHOLD_PROPOSALS_ARTIFACT}",
        "learning_approval_queue_path": f"data/runtime/{LEARNING_APPROVAL_QUEUE_ARTIFACT}",
        "attribution_record_count": payload["attribution_record_count"],
        "real_paper_lifecycle_record_count": payload["real_paper_lifecycle_record_count"],
        "non_trade_record_count": payload["non_trade_record_count"],
        "shadow_replay_record_count": payload["shadow_replay_record_count"],
        "backtest_record_count": payload["backtest_record_count"],
        "rejected_hypothesis_record_count": payload["rejected_hypothesis_record_count"],
        "blocked_route_record_count": payload["blocked_route_record_count"],
        "system_defect_record_count": payload["system_defect_record_count"],
        "active_proposal_count": payload["active_proposal_count"],
        "approval_required_count": payload["approval_required_count"],
        "applied_update_count": payload["applied_update_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "changes_are_proposals_only": True,
        "no_strategy_mutations": True,
        "no_source_trust_mutations": True,
        "no_model_weight_mutations": True,
        "no_filter_threshold_mutations": True,
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
        f"## QSASE-12: Learning And Attribution Ledger\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Attribution records: `{payload.get('attribution_record_count')}`\n"
        f"- Evidence classes: real paper `{payload.get('real_paper_lifecycle_record_count')}`, non-trade `{payload.get('non_trade_record_count')}`, shadow `{payload.get('shadow_replay_record_count')}`, backtest `{payload.get('backtest_record_count')}`, rejected `{payload.get('rejected_hypothesis_record_count')}`, blocked route `{payload.get('blocked_route_record_count')}`, system defect `{payload.get('system_defect_record_count')}`\n"
        f"- Proposals: strategy `{payload.get('strategy_weight_proposal_count')}`, source `{payload.get('source_trust_proposal_count')}`, model `{payload.get('model_weight_proposal_count')}`, filter `{payload.get('filter_threshold_proposal_count')}`, approval queue `{payload.get('approval_required_count')}`\n"
        f"- Safety: strategy, source, model, and filter changes are proposals only; no applied updates, paper orders, broker writes, live capital, 30-day paper growth trial calendar advancement, or paper proof ledger credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_learning_attribution_ledger(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "component_attribution_ledger": runtime_dir / PRIMARY_ARTIFACT,
        "ledger_records": runtime_dir / LEDGER_JSONL_ARTIFACT,
        "strategy_weight_proposals": runtime_dir / STRATEGY_WEIGHT_PROPOSALS_ARTIFACT,
        "source_trust_proposals": runtime_dir / SOURCE_TRUST_PROPOSALS_ARTIFACT,
        "model_weight_proposals": runtime_dir / MODEL_WEIGHT_PROPOSALS_ARTIFACT,
        "filter_threshold_proposals": runtime_dir / FILTER_THRESHOLD_PROPOSALS_ARTIFACT,
        "learning_approval_queue": runtime_dir / LEARNING_APPROVAL_QUEUE_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["component_attribution_ledger"], _summary_without_records(payload))
    _write_jsonl(paths["ledger_records"], payload["attribution_records"])
    _write_json(paths["strategy_weight_proposals"], payload["strategy_weight_proposals"])
    _write_json(paths["source_trust_proposals"], payload["source_trust_proposals"])
    _write_json(paths["model_weight_proposals"], payload["model_weight_proposals"])
    _write_json(paths["filter_threshold_proposals"], payload["filter_threshold_proposals"])
    _write_json(paths["learning_approval_queue"], payload["learning_approval_queue"])
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
                "attribution_record_count": payload["attribution_record_count"],
                "real_paper_lifecycle_record_count": payload["real_paper_lifecycle_record_count"],
                "non_trade_record_count": payload["non_trade_record_count"],
                "shadow_replay_record_count": payload["shadow_replay_record_count"],
                "backtest_record_count": payload["backtest_record_count"],
                "rejected_hypothesis_record_count": payload["rejected_hypothesis_record_count"],
                "blocked_route_record_count": payload["blocked_route_record_count"],
                "system_defect_record_count": payload["system_defect_record_count"],
                "active_proposal_count": payload["active_proposal_count"],
                "applied_update_count": 0,
                "no_paper_orders_created": True,
                "no_proof_credit_granted": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_learning_attribution_ledger_written",
                "status": payload["status"],
                "proposal_first": True,
                "authority_flags_false": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_learning_attribution_ledger(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_learning_attribution_ledger(settings)
    errors = validate_learning_attribution_ledger(payload)
    written = write_learning_attribution_ledger(payload, settings)
    return payload, written, errors


def validate_negative_learning_attribution_ledger_probes() -> list[str]:
    base = build_learning_attribution_ledger()
    errors: list[str] = []
    for flag in LEARNING_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_learning_attribution_ledger(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    applied_probe = copy.deepcopy(base)
    applied_probe["applied_update_count"] = 1
    if not any("applied_update_count" in error for error in validate_learning_attribution_ledger(applied_probe)):
        errors.append("negative_probe_failed_for_applied_update_count")
    if base["attribution_records"]:
        record_probe = copy.deepcopy(base)
        record_probe["attribution_records"][0]["proposal"]["applied"] = True
        if not any("proposal_applied" in error for error in validate_learning_attribution_ledger(record_probe)):
            errors.append("negative_probe_failed_for_applied_proposal")
        authority_probe = copy.deepcopy(base)
        authority_probe["attribution_records"][0]["authority"]["paper_order_created"] = True
        if not any("paper_order_created" in error for error in validate_learning_attribution_ledger(authority_probe)):
            errors.append("negative_probe_failed_for_record_order_authority")
        class_probe = copy.deepcopy(base)
        class_probe["attribution_records"][0]["evidence_class"] = "model_narrative"
        if not any("evidence_class_invalid" in error for error in validate_learning_attribution_ledger(class_probe)):
            errors.append("negative_probe_failed_for_invalid_evidence_class")
    strategy_probe = copy.deepcopy(base)
    if strategy_probe.get("system_defect_records"):
        defect_id = strategy_probe["system_defect_records"][0]["attribution_record_id"]
        strategy_probe["strategy_weight_proposals"]["proposals"].append(
            _proposal(
                "hold_strategy_weight",
                "strategy_family",
                "invalid_system_defect_strategy_change",
                [f"data/runtime/{LEDGER_JSONL_ARTIFACT}#{defect_id}"],
                reason="invalid probe",
            )
        )
        strategy_probe["strategy_weight_proposals"]["proposal_count"] += 1
        if not any("system_defect" in error for error in validate_learning_attribution_ledger(strategy_probe)):
            errors.append("negative_probe_failed_for_system_defect_strategy_proposal")
    dashboard_probe = copy.deepcopy(base)
    dashboard_probe["dashboard_safe_summary"]["live_send_allowed"] = True
    if not any("dashboard_summary_live_send" in error for error in validate_learning_attribution_ledger(dashboard_probe)):
        errors.append("negative_probe_failed_for_dashboard_live_send")
    return errors


if __name__ == "__main__":
    artifact = build_learning_attribution_ledger()
    print(_json_dump(_summary_without_records(artifact)))
