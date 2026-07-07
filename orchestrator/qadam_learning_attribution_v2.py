"""Learning attribution V2 for Qadam next-generation Phase 11.

This module turns existing research, filter, router, PaperOps, shadow, backtest,
missed-opportunity, and paper-lifecycle outcomes into attribution records. It
also creates review proposals, but those proposals are inert: they cannot mutate
authority, strategy, source trust, model weights, filter thresholds, broker
routes, live capital, paper orders, or proof credit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_learning_attribution_v2.v1"
PHASE_ID = "qadam_next_generation_phase_11_learning_attribution"

PRIMARY_ARTIFACT = "qadam_learning_attribution_v2.json"
RECORDS_ARTIFACT = "qadam_learning_attribution_v2_records.jsonl"
PROPOSALS_ARTIFACT = "qadam_recursive_improvement_proposals.json"
PROPOSAL_RECORDS_ARTIFACT = "qadam_recursive_improvement_proposals.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_learning_attribution_v2_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_learning_attribution_v2_events.jsonl"

NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT = "qadam_next_generation_backtest_dashboard_summary.json"
PATTERN_ENGINE_V2_ARTIFACT = "qadam_pattern_engine_v2.json"
PATTERN_ENGINE_V2_RECORDS_ARTIFACT = "qadam_pattern_engine_v2_records.jsonl"
PATTERN_ENGINE_V2_REJECTIONS_ARTIFACT = "qadam_pattern_engine_v2_rejections.jsonl"
STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT = "qadam_strategy_foundry_v2_hypotheses.jsonl"
STRATEGY_FOUNDRY_V2_REJECTIONS_ARTIFACT = "qadam_strategy_foundry_v2_rejections.jsonl"
AKBER_FILTER_V2_ARTIFACT = "qadam_akber_filter_v2.json"
AKBER_FILTER_V2_RESULTS_ARTIFACT = "qadam_akber_filter_v2_results.jsonl"
AKBER_FILTER_V2_ABLATION_ARTIFACT = "qadam_akber_filter_v2_ablation_tests.jsonl"
SHADOW_SIMULATOR_V2_ARTIFACT = "qadam_shadow_simulator_v2.json"
SHADOW_HISTORICAL_REPLAY_ARTIFACT = "qadam_shadow_simulator_v2_historical_replay.jsonl"
SHADOW_FORWARD_TRACKING_ARTIFACT = "qadam_shadow_simulator_v2_forward_tracking.jsonl"
SHADOW_COUNTERFACTUAL_NO_ORDER_ARTIFACT = "qadam_shadow_simulator_v2_counterfactual_no_order.jsonl"
SHADOW_ALTERNATE_THRESHOLDS_ARTIFACT = "qadam_shadow_simulator_v2_alternate_threshold_outcomes.jsonl"
SHADOW_MISSED_OPPORTUNITIES_ARTIFACT = "qadam_shadow_simulator_v2_missed_opportunities.jsonl"
ROUTER_V2_ARTIFACT = "qadam_router_v2_paperops_handoff.json"
ROUTER_V2_DECISIONS_ARTIFACT = "qadam_router_v2_decisions.jsonl"
ROUTER_V2_REJECTED_HANDOFFS_ARTIFACT = "qadam_paperops_handoff_v2_rejections.jsonl"
PAPER_LIFECYCLE_V2_ARTIFACT = "qadam_paper_lifecycle_v2.json"
PAPER_LIFECYCLE_V2_RECORDS_ARTIFACT = "qadam_paper_lifecycle_v2_records.jsonl"
PAPER_PROOF_BOUNDARY_ARTIFACT = "qadam_paper_proof_boundary_audit.json"
PAPER_PROOF_RECORDS_ARTIFACT = "qadam_paper_proof_boundary_records.jsonl"
PAPER_CLOSED_TRADES_ARTIFACT = "paper_closed_trades.jsonl"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

ATTRIBUTION_COMPONENTS = (
    "source_universe",
    "source_quorum",
    "local_llm_research_analyst",
    "frontier_llm_strategy_lead",
    "python_orchestrator",
    "quantum_review",
    "akber_filter",
    "strategy_foundry",
    "router_v2",
    "paperops",
    "shadow_simulator",
    "backtest_lab",
    "paper_lifecycle",
    "proof_boundary",
)

CONTRIBUTION_LABELS = {
    "helped",
    "hurt",
    "blocked",
    "neutral",
    "unknown",
    "not_applicable",
}

OUTCOME_TYPES = {
    "backtest_success",
    "backtest_failure",
    "shadow_success",
    "shadow_failure",
    "hold",
    "veto",
    "missed_opportunity",
    "paper_trade_win",
    "paper_trade_loss",
    "paper_trade_flat_or_unverified",
    "proof_rejected",
    "proof_eligible_review_only",
    "paperops_watch_only",
    "system_defect",
    "rejected_hypothesis",
}

EVIDENCE_CLASSES = {
    "source_price_backtest",
    "model_or_quant_review",
    "akber_filter_review",
    "router_decision",
    "paperops_state",
    "shadow_replay",
    "missed_opportunity",
    "paper_trade_outcome",
    "proof_boundary",
    "rejected_hypothesis",
    "system_defect",
}

PROPOSAL_TYPES = {
    "source_trust_update_proposal",
    "source_weight_update_proposal",
    "strategy_weight_update_proposal",
    "akber_threshold_update_proposal",
    "model_routing_update_proposal",
    "quantum_review_usage_proposal",
    "dashboard_explanation_update_proposal",
    "paper_lifecycle_repair_proposal",
}

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "attribution_only": True,
    "learning_outputs_are_proposals_only": True,
    "authority_mutation_allowed": False,
    "authority_mutation_created": False,
    "settings_mutation_allowed": False,
    "settings_mutation_created": False,
    "source_trust_update_allowed": False,
    "source_trust_update_applied": False,
    "source_weight_update_allowed": False,
    "source_weight_update_applied": False,
    "strategy_weight_update_allowed": False,
    "strategy_weight_update_applied": False,
    "model_weight_update_allowed": False,
    "model_weight_update_applied": False,
    "filter_threshold_update_allowed": False,
    "filter_threshold_update_applied": False,
    "quantum_usage_policy_update_allowed": False,
    "quantum_usage_policy_update_applied": False,
    "dashboard_copy_update_allowed": False,
    "dashboard_copy_update_applied": False,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "paper_proof_ledger_write_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "proof_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "paper_growth_trial_calendar_advanced": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)

REQUIRED_ATTRIBUTION_FIELDS = (
    "attribution_record_id",
    "outcome_type",
    "evidence_class",
    "source_artifact",
    "source_record_id",
    "lineage",
    "outcome_summary",
    "component_attribution",
    "learning_signal",
    "proposal",
    "authority",
)


@dataclass(frozen=True)
class LearningAttributionV2Bundle:
    primary: dict[str, Any]
    records: list[dict[str, Any]]
    proposals: dict[str, Any]
    proposal_records: list[dict[str, Any]]
    dashboard_summary: dict[str, Any]


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


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _hash_id(prefix: str, parts: list[Any]) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _artifact_ref(filename: str, pointer: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{pointer}" if pointer else base


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "backtest_dashboard": _read_json(runtime / NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT),
        "pattern_engine": _read_json(runtime / PATTERN_ENGINE_V2_ARTIFACT),
        "pattern_records": _read_jsonl(runtime / PATTERN_ENGINE_V2_RECORDS_ARTIFACT, limit=400),
        "pattern_rejections": _read_jsonl(runtime / PATTERN_ENGINE_V2_REJECTIONS_ARTIFACT, limit=400),
        "hypotheses": _read_jsonl(runtime / STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT, limit=400),
        "hypothesis_rejections": _read_jsonl(runtime / STRATEGY_FOUNDRY_V2_REJECTIONS_ARTIFACT, limit=400),
        "akber": _read_json(runtime / AKBER_FILTER_V2_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_V2_RESULTS_ARTIFACT, limit=400),
        "akber_ablation": _read_jsonl(runtime / AKBER_FILTER_V2_ABLATION_ARTIFACT, limit=400),
        "shadow": _read_json(runtime / SHADOW_SIMULATOR_V2_ARTIFACT),
        "shadow_historical": _read_jsonl(runtime / SHADOW_HISTORICAL_REPLAY_ARTIFACT, limit=400),
        "shadow_forward": _read_jsonl(runtime / SHADOW_FORWARD_TRACKING_ARTIFACT, limit=400),
        "shadow_counterfactual": _read_jsonl(runtime / SHADOW_COUNTERFACTUAL_NO_ORDER_ARTIFACT, limit=400),
        "shadow_alternate_thresholds": _read_jsonl(runtime / SHADOW_ALTERNATE_THRESHOLDS_ARTIFACT, limit=400),
        "missed_opportunities": _read_jsonl(runtime / SHADOW_MISSED_OPPORTUNITIES_ARTIFACT, limit=400),
        "router": _read_json(runtime / ROUTER_V2_ARTIFACT),
        "router_decisions": _read_jsonl(runtime / ROUTER_V2_DECISIONS_ARTIFACT, limit=400),
        "router_rejected_handoffs": _read_jsonl(runtime / ROUTER_V2_REJECTED_HANDOFFS_ARTIFACT, limit=400),
        "paper_lifecycle": _read_json(runtime / PAPER_LIFECYCLE_V2_ARTIFACT),
        "paper_lifecycle_records": _read_jsonl(runtime / PAPER_LIFECYCLE_V2_RECORDS_ARTIFACT, limit=1000),
        "proof_boundary": _read_json(runtime / PAPER_PROOF_BOUNDARY_ARTIFACT),
        "proof_records": _read_jsonl(runtime / PAPER_PROOF_RECORDS_ARTIFACT, limit=1000),
        "closed_trades": _read_jsonl(runtime / PAPER_CLOSED_TRADES_ARTIFACT, limit=1000),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
    }


def _component(label: str, reason: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "contribution": label if label in CONTRIBUTION_LABELS else "unknown",
        "reason": reason,
        "evidence_refs": evidence_refs or [],
    }


def _component_attribution(**overrides: dict[str, Any]) -> dict[str, dict[str, Any]]:
    base = {
        component: _component("not_applicable", "No contribution observed for this outcome.")
        for component in ATTRIBUTION_COMPONENTS
    }
    for component, value in overrides.items():
        if component in base:
            base[component] = value
    return base


def _proposal_stub(proposal_type: str, reason: str) -> dict[str, Any]:
    return {
        "proposal_type": proposal_type,
        "reason": reason,
        "proposal_only": True,
        "review_required": True,
        "applied": False,
        "applied_update_count": 0,
        "authority_mutation_allowed": False,
        "authority_mutation_created": False,
        "settings_mutation_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
    }


def _record(
    *,
    generated_at: str,
    outcome_type: str,
    evidence_class: str,
    source_artifact: str,
    source_record_id: str,
    lineage: dict[str, Any],
    outcome_summary: dict[str, Any],
    component_attribution: dict[str, Any],
    learning_signal: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_attribution_v2_record",
        "phase_id": PHASE_ID,
        "attribution_record_id": _hash_id(
            "qadam-learning-attribution-v2",
            [outcome_type, evidence_class, source_artifact, source_record_id],
        ),
        "generated_at": generated_at,
        "outcome_type": outcome_type,
        "evidence_class": evidence_class,
        "source_artifact": source_artifact,
        "source_record_id": source_record_id,
        "strategy_hypothesis_id": lineage.get("strategy_hypothesis_id"),
        "research_goal_id": lineage.get("research_goal_id"),
        "strategy_family_id": lineage.get("strategy_family_id"),
        "instrument": lineage.get("instrument"),
        "lineage": lineage,
        "outcome_summary": outcome_summary,
        "component_attribution": component_attribution,
        "learning_signal": learning_signal,
        "proposal": proposal,
        "proposal_only": True,
        "applied_update_count": 0,
        "paper_order_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority_mutation_created": False,
        "authority": _authority(),
        "artifact_refs": [_artifact_ref(source_artifact, source_record_id)],
    }


def _lineage_from_hypothesis_like(record: dict[str, Any]) -> dict[str, Any]:
    research_goal_lineage = _safe_dict(record.get("research_goal_lineage"))
    candidate_identity = _safe_dict(record.get("candidate_identity_material") or record.get("candidate_identity"))
    evidence_summary = _safe_dict(record.get("evidence_summary") or record.get("source_price_evidence"))
    return {
        "strategy_hypothesis_id": record.get("strategy_hypothesis_id"),
        "research_goal_id": record.get("research_goal_id")
        or research_goal_lineage.get("research_goal_id")
        or candidate_identity.get("research_goal_id"),
        "strategy_family_id": record.get("strategy_family_id")
        or candidate_identity.get("strategy_family_id")
        or research_goal_lineage.get("target_strategy_family"),
        "instrument": record.get("market_or_symbol")
        or record.get("market_affected")
        or candidate_identity.get("observed_instrument")
        or evidence_summary.get("market_or_symbol"),
        "source_pattern_id": record.get("pattern_id")
        or evidence_summary.get("pattern_id")
        or research_goal_lineage.get("source_pattern_id"),
        "candidate_identity_id": candidate_identity.get("candidate_identity_id"),
    }


def _source_price_backtest_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for pattern in context["pattern_records"]:
        linear = _safe_dict(pattern.get("linear_tests"))
        expectancy = _safe_float(linear.get("expectancy"))
        hit_rate = _safe_float(linear.get("hit_rate"))
        sample_count = _safe_int(linear.get("sample_count"))
        outcome_type = "backtest_success" if expectancy > 0 and hit_rate >= 0.5 else "backtest_failure"
        pattern_id = str(pattern.get("pattern_id") or pattern.get("source_baseline_result_id") or "unknown_pattern")
        lineage = _lineage_from_hypothesis_like(pattern)
        lineage.update(
            {
                "source_or_family": pattern.get("source_or_family"),
                "source_price_contract_id": pattern.get("source_price_contract_id"),
                "sample_count": sample_count,
                "rank": pattern.get("rank"),
            }
        )
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type=outcome_type,
                evidence_class="source_price_backtest",
                source_artifact=PATTERN_ENGINE_V2_RECORDS_ARTIFACT,
                source_record_id=pattern_id,
                lineage=lineage,
                outcome_summary={
                    "status": pattern.get("lifecycle_state") or pattern.get("pattern_status"),
                    "expectancy": expectancy,
                    "hit_rate": hit_rate,
                    "sample_count": sample_count,
                    "plain_english": pattern.get("what_qadam_thinks")
                    or "Pattern Engine V2 produced source-price evidence for attribution review.",
                },
                component_attribution=_component_attribution(
                    source_universe=_component(
                        "helped",
                        "The source universe supplied source-price memory for this relationship.",
                        _safe_list(pattern.get("source_record_ids"))[:8],
                    ),
                    source_quorum=_component(
                        "neutral",
                        "Source contribution was useful for research but cannot satisfy trading quorum alone.",
                    ),
                    python_orchestrator=_component(
                        "helped",
                        "The Python orchestrator normalized the pattern into a ranked research record.",
                    ),
                    backtest_lab=_component(
                        "helped" if outcome_type == "backtest_success" else "hurt",
                        "Transparent linear metrics created a measurable historical outcome.",
                    ),
                    quantum_review=_component(
                        "neutral",
                        str(_safe_dict(pattern.get("quantum_classical_review")).get("review_verdict") or "Quantum/classical review was annotation-only."),
                    ),
                    local_llm_research_analyst=_component(
                        "unknown",
                        "No model-specific local LLM decision reference is attached to this pattern record.",
                    ),
                    frontier_llm_strategy_lead=_component(
                        "unknown",
                        "No model-specific frontier LLM decision reference is attached to this pattern record.",
                    ),
                ),
                learning_signal={
                    "specific_lesson": (
                        f"{pattern.get('source_or_family', 'source')} to {pattern.get('market_or_symbol', 'market')} "
                        f"over {pattern.get('time_window', 'unknown window')} has measurable expectancy {expectancy:.6f}; "
                        "it still requires fresh confirmation before any trading path."
                    ),
                    "what_to_monitor_next": "Track whether fresh source evidence and price confirmation repeat this historical relationship.",
                    "confidence_direction": "increase_research_attention" if outcome_type == "backtest_success" else "decrease_research_attention",
                },
                proposal=_proposal_stub(
                    "source_weight_update_proposal",
                    "Review source monitoring weight only after fresh forward evidence confirms the historical relationship.",
                ),
            )
        )
    for rejection in context["pattern_rejections"]:
        rejected_id = str(rejection.get("pattern_id") or rejection.get("rejection_id") or rejection.get("source_baseline_result_id") or "rejected_pattern")
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type="backtest_failure",
                evidence_class="source_price_backtest",
                source_artifact=PATTERN_ENGINE_V2_REJECTIONS_ARTIFACT,
                source_record_id=rejected_id,
                lineage=_lineage_from_hypothesis_like(rejection),
                outcome_summary={
                    "status": rejection.get("rejection_reason") or rejection.get("status") or "rejected_pattern",
                    "plain_english": "A source-price pattern was rejected before strategy formation.",
                },
                component_attribution=_component_attribution(
                    source_universe=_component("hurt", "The source-price evidence was too weak or repetitive for this pattern."),
                    backtest_lab=_component("helped", "The backtest layer prevented a weak pattern from progressing."),
                    python_orchestrator=_component("helped", "The orchestrator preserved the rejection as learning evidence."),
                ),
                learning_signal={
                    "specific_lesson": "Rejected source-price patterns should remain visible so similar weak relationships are not repeatedly promoted.",
                    "what_to_monitor_next": "Require distinct source-price identity and enough forward-window evidence before reconsidering.",
                    "confidence_direction": "reduce_repetition",
                },
                proposal=_proposal_stub(
                    "dashboard_explanation_update_proposal",
                    "Keep rejected pattern reasons visible as research evidence, not as trade blockers hidden in logs.",
                ),
            )
        )
    return records


def _akber_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for result in context["akber_results"]:
        decision = _safe_dict(result.get("decision"))
        filter_decision = str(decision.get("filter_decision") or result.get("status") or "")
        if "veto" in filter_decision:
            outcome_type = "veto"
        elif "hold" in filter_decision:
            outcome_type = "hold"
        else:
            outcome_type = "backtest_success" if result.get("router_eligible") else "hold"
        result_id = str(result.get("akber_filter_result_id") or result.get("strategy_hypothesis_id") or "akber_result")
        missing_context_count = _safe_int(result.get("missing_context_count"))
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type=outcome_type,
                evidence_class="akber_filter_review",
                source_artifact=AKBER_FILTER_V2_RESULTS_ARTIFACT,
                source_record_id=result_id,
                lineage=_lineage_from_hypothesis_like(result),
                outcome_summary={
                    "status": result.get("status"),
                    "filter_decision": filter_decision,
                    "router_eligible": result.get("router_eligible") is True,
                    "missing_context_count": missing_context_count,
                    "plain_english": decision.get("reason")
                    or "Akber reviewed practical confirmation and withheld Router eligibility.",
                },
                component_attribution=_component_attribution(
                    akber_filter=_component(
                        "helped" if outcome_type in {"hold", "veto"} else "neutral",
                        "Akber protected the route from moving forward without practical confirmation.",
                    ),
                    source_universe=_component(
                        "blocked" if missing_context_count else "helped",
                        "Fresh catalyst, technical, volume, volatility, or liquidity context was incomplete."
                        if missing_context_count
                        else "Required practical context was present.",
                    ),
                    quantum_review=_component(
                        "neutral",
                        f"Nonlinear/quantum score observed: {_safe_dict(result.get('scores')).get('nonlinear_quantum_score')}.",
                    ),
                    router_v2=_component("not_applicable", "Router V2 consumes this later; Akber itself did not route."),
                ),
                learning_signal={
                    "specific_lesson": (
                        "Akber held the setup because practical confirmation was incomplete; missing confirmation "
                        "must become a typed evidence target before Router can improve confidence."
                    ),
                    "what_to_monitor_next": ", ".join(_safe_list(decision.get("next_required_evidence"))[:8])
                    or "fresh catalyst, technical confirmation, volume, volatility, liquidity",
                    "confidence_direction": "hold_until_practical_confirmation",
                },
                proposal=_proposal_stub(
                    "akber_threshold_update_proposal",
                    "Review Akber input coverage and thresholds only after historical replay shows the hold improved outcomes.",
                ),
            )
        )
    return records


def _shadow_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    shadow_sources = (
        (SHADOW_HISTORICAL_REPLAY_ARTIFACT, context["shadow_historical"]),
        (SHADOW_FORWARD_TRACKING_ARTIFACT, context["shadow_forward"]),
        (SHADOW_COUNTERFACTUAL_NO_ORDER_ARTIFACT, context["shadow_counterfactual"]),
        (SHADOW_ALTERNATE_THRESHOLDS_ARTIFACT, context["shadow_alternate_thresholds"]),
    )
    for artifact, source_records in shadow_sources:
        for shadow in source_records:
            expectancy = _safe_float(shadow.get("expectancy"))
            positive = expectancy > 0 or shadow.get("positive_expectancy") is True
            replay_id = str(
                shadow.get("shadow_replay_id")
                or shadow.get("forward_tracking_id")
                or shadow.get("counterfactual_no_order_id")
                or shadow.get("alternate_threshold_outcome_id")
                or shadow.get("strategy_hypothesis_id")
                or "shadow_record"
            )
            records.append(
                _record(
                    generated_at=generated_at,
                    outcome_type="shadow_success" if positive else "shadow_failure",
                    evidence_class="shadow_replay",
                    source_artifact=artifact,
                    source_record_id=replay_id,
                    lineage=_lineage_from_hypothesis_like(shadow),
                    outcome_summary={
                        "status": shadow.get("replay_state") or shadow.get("tracking_state") or shadow.get("outcome_state"),
                        "shadow_outcome": shadow.get("shadow_outcome"),
                        "expectancy": expectancy,
                        "plain_english": "Shadow replay created outcome evidence without order or proof authority.",
                    },
                    component_attribution=_component_attribution(
                        shadow_simulator=_component("helped", "Shadow replay supplied counterfactual outcome evidence."),
                        akber_filter=_component(
                            "blocked" if "hold" in str(shadow.get("akber_filter_decision") or "") else "neutral",
                            "Akber state was preserved in shadow rather than bypassed.",
                        ),
                        router_v2=_component(
                            "neutral",
                            "Router confidence cannot increase from shadow evidence alone.",
                        ),
                    ),
                    learning_signal={
                        "specific_lesson": (
                            f"Shadow evidence for {shadow.get('strategy_hypothesis_id', 'a hypothesis')} "
                            f"showed expectancy {expectancy:.6f}; it remains research-only."
                        ),
                        "what_to_monitor_next": "Compare trade-now, wait, veto, and no-order outcomes before changing any filter.",
                        "confidence_direction": "increase_shadow_observation" if positive else "reduce_shadow_confidence",
                    },
                    proposal=_proposal_stub(
                        "strategy_weight_update_proposal",
                        "Review strategy weighting only after shadow outcomes survive forward tracking and PaperOps review.",
                    ),
                )
            )
    for missed in context["missed_opportunities"]:
        missed_id = str(missed.get("missed_opportunity_id") or missed.get("strategy_hypothesis_id") or "missed_opportunity")
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type="missed_opportunity",
                evidence_class="missed_opportunity",
                source_artifact=SHADOW_MISSED_OPPORTUNITIES_ARTIFACT,
                source_record_id=missed_id,
                lineage=_lineage_from_hypothesis_like(missed),
                outcome_summary={
                    "status": missed.get("missed_opportunity_state"),
                    "positive_expectancy": missed.get("positive_expectancy") is True,
                    "plain_english": missed.get("learning_question")
                    or "A possible opportunity was missed because practical confirmation remained incomplete.",
                },
                component_attribution=_component_attribution(
                    shadow_simulator=_component("helped", "The missed-opportunity record exposes a counterfactual to review."),
                    akber_filter=_component("blocked", "Akber missing context prevented unsafe promotion."),
                    source_universe=_component("blocked", "Fresh confirmation evidence was incomplete."),
                ),
                learning_signal={
                    "specific_lesson": "Missed opportunities should be investigated as evidence gaps, not converted into retroactive proof.",
                    "what_to_monitor_next": "Fill fresh catalyst, technical, volume, volatility, and liquidity evidence before the next similar setup.",
                    "confidence_direction": "increase_data_gap_priority",
                },
                proposal=_proposal_stub(
                    "source_trust_update_proposal",
                    "Review whether missing fresh confirmation sources need reliability or freshness work.",
                ),
            )
        )
    return records


def _router_and_paperops_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for decision in context["router_decisions"]:
        final_state = str(decision.get("final_state") or "unknown")
        outcome_type = "veto" if final_state in {"reject", "blocked_safety_boundary"} else "hold"
        decision_id = str(decision.get("router_decision_id") or decision.get("strategy_hypothesis_id") or "router_decision")
        soft_blockers = _safe_list(decision.get("soft_blockers"))
        hard_vetoes = _safe_list(decision.get("hard_vetoes"))
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type=outcome_type,
                evidence_class="router_decision",
                source_artifact=ROUTER_V2_DECISIONS_ARTIFACT,
                source_record_id=decision_id,
                lineage=_lineage_from_hypothesis_like(decision),
                outcome_summary={
                    "status": final_state,
                    "clean_paper_review_candidate": decision.get("clean_paper_review_candidate") is True,
                    "soft_blockers": soft_blockers,
                    "hard_vetoes": hard_vetoes,
                    "plain_english": decision.get("final_state_reason") or "Router assigned one final state.",
                },
                component_attribution=_component_attribution(
                    router_v2=_component(
                        "helped",
                        "Router V2 assigned exactly one final state and preserved PaperOps boundaries.",
                    ),
                    akber_filter=_component(
                        "blocked" if "akber_practical_confirmation_missing" in soft_blockers else "neutral",
                        "Akber confirmation status determined whether the setup could progress.",
                    ),
                    paperops=_component(
                        "blocked" if "long_backtest_research_lock_active" in soft_blockers else "neutral",
                        "PaperOps remained watch-only while the research lock was active.",
                    ),
                    proof_boundary=_component(
                        "not_applicable",
                        "Router output did not create paper proof ledger credit.",
                    ),
                ),
                learning_signal={
                    "specific_lesson": (
                        f"Router held {decision.get('strategy_hypothesis_id', 'a setup')} because "
                        f"{', '.join(soft_blockers[:4]) or final_state}; the final state must remain singular."
                    ),
                    "what_to_monitor_next": "Resolve practical confirmation and research-lock blockers before PaperOps handoff review.",
                    "confidence_direction": "hold_route_confidence",
                },
                proposal=_proposal_stub(
                    "dashboard_explanation_update_proposal",
                    "Surface the single Router reason in plain English so users understand why Qadam did not trade.",
                ),
            )
        )

    paperops = _safe_dict(context.get("paperops_summary"))
    if paperops:
        paper_runtime = _safe_dict(paperops.get("paper_runtime"))
        states = _safe_dict(paperops.get("states"))
        source_id = str(paperops.get("artifact_id") or paperops.get("generated_at") or "paperops_summary")
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type="paperops_watch_only",
                evidence_class="paperops_state",
                source_artifact=PAPEROPS_SUMMARY_ARTIFACT,
                source_record_id=source_id,
                lineage={
                    "paper_ops_cycle_state": states.get("paper_ops_cycle_state"),
                    "active_automation_state": states.get("active_automation_state"),
                },
                outcome_summary={
                    "status": paperops.get("status"),
                    "fresh_eligible_submit_count": paper_runtime.get("fresh_eligible_submit_count"),
                    "submitted_paper_order_count": paper_runtime.get("submitted_paper_order_count"),
                    "idle_reason": paper_runtime.get("idle_reason"),
                    "plain_english": "PaperOps is watch-only during the long research lock and did not submit paper orders.",
                },
                component_attribution=_component_attribution(
                    paperops=_component("helped", "PaperOps respected the research lock and stayed watch-only."),
                    router_v2=_component("neutral", "No clean paper-review candidate reached PaperOps."),
                    proof_boundary=_component("neutral", "No proof credit was created."),
                ),
                learning_signal={
                    "specific_lesson": "Watch-only PaperOps state is intentional while the whole-universe research lock is active.",
                    "what_to_monitor_next": "Resume guarded PaperOps submission only after the research lock and Router blockers clear.",
                    "confidence_direction": "maintain_safety_boundary",
                },
                proposal=_proposal_stub(
                    "dashboard_explanation_update_proposal",
                    "Keep the watch-only reason visible so research-lock safety is not mistaken for a trading failure.",
                ),
            )
        )
    return records


def _paper_trade_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    closed_by_id = {str(trade.get("trade_id")): trade for trade in context["closed_trades"] if trade.get("trade_id")}
    for proof in context["proof_records"]:
        trade_id = str(proof.get("trade_id") or proof.get("proof_boundary_record_id") or "proof_record")
        closed_trade = closed_by_id.get(str(proof.get("trade_id")), {})
        pnl = _safe_float(closed_trade.get("realized_pnl_gbp"), default=0.0)
        if proof.get("proof_eligible") is True:
            outcome_type = "proof_eligible_review_only"
        elif pnl > 0:
            outcome_type = "paper_trade_win"
        elif pnl < 0:
            outcome_type = "paper_trade_loss"
        else:
            outcome_type = "paper_trade_flat_or_unverified"
        if proof.get("proof_rejected") is True:
            proof_outcome = "proof_rejected"
        else:
            proof_outcome = outcome_type
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type=proof_outcome,
                evidence_class="paper_trade_outcome",
                source_artifact=PAPER_PROOF_RECORDS_ARTIFACT,
                source_record_id=trade_id,
                lineage={
                    "trade_id": proof.get("trade_id"),
                    "instrument": proof.get("instrument"),
                    "research_goal_id": closed_trade.get("research_goal_id") or closed_trade.get("source_intent_id"),
                    "source_intent_id": closed_trade.get("source_intent_id"),
                    "postmortem_status": proof.get("postmortem_status"),
                    "missing_lineage": proof.get("missing_lineage"),
                },
                outcome_summary={
                    "status": proof.get("proof_state"),
                    "realized_pnl_gbp": pnl,
                    "proof_eligible": proof.get("proof_eligible") is True,
                    "proof_rejected": proof.get("proof_rejected") is True,
                    "missing_lineage": proof.get("missing_lineage"),
                    "plain_english": "Closed paper trade mirror exists, but proof credit requires complete lineage and postmortem.",
                },
                component_attribution=_component_attribution(
                    paper_lifecycle=_component("helped", "Lifecycle audit made the closed trade state explicit."),
                    proof_boundary=_component(
                        "helped" if proof.get("proof_rejected") is True else "neutral",
                        "Proof boundary prevented incomplete lineage from receiving paper proof ledger credit.",
                    ),
                    paperops=_component(
                        "unknown",
                        "This closed trade is mirrored for postmortem; Qadam did not necessarily originate the order.",
                    ),
                ),
                learning_signal={
                    "specific_lesson": "Closed paper outcomes cannot teach strategy performance unless Research Goal, candidate, Router, order, fill, close, and postmortem lineage are complete.",
                    "what_to_monitor_next": "Repair lineage and complete postmortems before any closed trade can become proof-eligible.",
                    "confidence_direction": "defer_performance_learning_until_lineage_complete",
                },
                proposal=_proposal_stub(
                    "paper_lifecycle_repair_proposal",
                    "Repair missing lineage and postmortem fields before treating the outcome as strategy learning.",
                ),
            )
        )
    return records


def _rejected_hypothesis_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for rejection in context["hypothesis_rejections"]:
        rejection_id = str(
            rejection.get("rejected_strategy_hypothesis_id")
            or rejection.get("strategy_hypothesis_id")
            or rejection.get("rejection_id")
            or "rejected_hypothesis"
        )
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type="rejected_hypothesis",
                evidence_class="rejected_hypothesis",
                source_artifact=STRATEGY_FOUNDRY_V2_REJECTIONS_ARTIFACT,
                source_record_id=rejection_id,
                lineage=_lineage_from_hypothesis_like(rejection),
                outcome_summary={
                    "status": rejection.get("status") or rejection.get("rejection_reason"),
                    "plain_english": "Strategy Foundry rejected a weak, overfit, unsafe, or non-paperable hypothesis before Akber.",
                },
                component_attribution=_component_attribution(
                    strategy_foundry=_component("helped", "Strategy Foundry rejected weak evidence before Akber or Router."),
                    backtest_lab=_component("neutral", "Backtest evidence was preserved for context but not promoted."),
                ),
                learning_signal={
                    "specific_lesson": "Rejected hypotheses prevent weak patterns from consuming Akber, Router, or PaperOps attention.",
                    "what_to_monitor_next": "Only regenerate similar hypotheses if new source-price evidence or paperability changes materially.",
                    "confidence_direction": "reduce_false_discovery_pressure",
                },
                proposal=_proposal_stub(
                    "strategy_weight_update_proposal",
                    "Review under-evidenced strategy families before increasing strategy weight.",
                ),
            )
        )
    return records


def _system_defect_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    backtest = _safe_dict(context.get("backtest_dashboard"))
    missing_windows = _safe_int(backtest.get("missing_forward_window_count"))
    missing_typed = _safe_int(backtest.get("missing_typed_evidence_count"))
    defects = []
    if missing_windows:
        defects.append(("missing_forward_windows", missing_windows, "Historical source-price forward windows remain incomplete."))
    if missing_typed:
        defects.append(("missing_typed_evidence", missing_typed, "Typed evidence contracts still have missing fields."))
    for defect_name, count, message in defects:
        records.append(
            _record(
                generated_at=generated_at,
                outcome_type="system_defect",
                evidence_class="system_defect",
                source_artifact=NEXT_GENERATION_BACKTEST_DASHBOARD_ARTIFACT,
                source_record_id=defect_name,
                lineage={"defect_name": defect_name, "defect_count": count},
                outcome_summary={
                    "status": "defect_under_observation",
                    "defect_count": count,
                    "plain_english": message,
                },
                component_attribution=_component_attribution(
                    source_universe=_component("blocked", message),
                    backtest_lab=_component("blocked", "Missing evidence limits confidence in historical conclusions."),
                    python_orchestrator=_component("helped", "The orchestrator surfaced the defect as typed attribution."),
                ),
                learning_signal={
                    "specific_lesson": f"{defect_name} is a research-system blocker and must be measured as a defect, not hidden as low activity.",
                    "what_to_monitor_next": "Improve evidence coverage before increasing strategy confidence.",
                    "confidence_direction": "reduce_certainty_until_coverage_improves",
                },
                proposal=_proposal_stub(
                    "source_trust_update_proposal",
                    "Prioritize evidence coverage repair before changing trading confidence.",
                ),
            )
        )
    return records


def build_attribution_records(context: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    records.extend(_source_price_backtest_records(context, generated_at))
    records.extend(_rejected_hypothesis_records(context, generated_at))
    records.extend(_akber_records(context, generated_at))
    records.extend(_shadow_records(context, generated_at))
    records.extend(_router_and_paperops_records(context, generated_at))
    records.extend(_paper_trade_records(context, generated_at))
    records.extend(_system_defect_records(context, generated_at))
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record.get("attribution_record_id"))
        if record_id in seen:
            continue
        seen.add(record_id)
        deduped.append(record)
    return deduped


def _proposal_record(
    proposal_type: str,
    title: str,
    reason: str,
    generated_at: str,
    source_record_ids: list[str],
    target: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_recursive_improvement_proposal",
        "phase_id": PHASE_ID,
        "proposal_id": _hash_id("qadam-recursive-improvement-proposal-v2", [proposal_type, title, source_record_ids, target]),
        "generated_at": generated_at,
        "proposal_type": proposal_type,
        "title": title,
        "reason": reason,
        "target": target,
        "source_attribution_record_ids": source_record_ids[:25],
        "status": "proposal_for_review",
        "proposal_only": True,
        "review_required": True,
        "applied": False,
        "applied_update_count": 0,
        "authority_mutation_allowed": False,
        "authority_mutation_created": False,
        "settings_mutation_created": False,
        "paper_order_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority(),
    }


def build_recursive_improvement_proposals(records: list[dict[str, Any]], generated_at: str) -> list[dict[str, Any]]:
    by_outcome: dict[str, list[str]] = {}
    for record in records:
        by_outcome.setdefault(str(record.get("outcome_type")), []).append(str(record.get("attribution_record_id")))
    proposals = [
        _proposal_record(
            "source_trust_update_proposal",
            "Review source freshness and coverage before increasing confidence",
            "Backtest and missed-opportunity attribution shows useful relationships, but missing evidence still blocks tradeability.",
            generated_at,
            by_outcome.get("backtest_success", []) + by_outcome.get("missed_opportunity", []),
            {"target_layer": "source_universe", "applied_change": "none"},
        ),
        _proposal_record(
            "source_weight_update_proposal",
            "Keep source weighting review-only until fresh confirmation exists",
            "Historical source-price relationships should not change weights until fresh forward evidence confirms them.",
            generated_at,
            by_outcome.get("backtest_success", []),
            {"target_layer": "source_quorum", "applied_change": "none"},
        ),
        _proposal_record(
            "strategy_weight_update_proposal",
            "Review strategy weights after shadow outcomes mature",
            "Shadow results and rejected hypotheses should influence future review, but no strategy weight is mutated here.",
            generated_at,
            by_outcome.get("shadow_success", []) + by_outcome.get("rejected_hypothesis", []),
            {"target_layer": "strategy_universe", "applied_change": "none"},
        ),
        _proposal_record(
            "akber_threshold_update_proposal",
            "Improve Akber practical confirmation inputs",
            "Akber holds show the practical trader layer needs fresh catalyst, technical, volume, volatility, liquidity, and pricing-gap inputs.",
            generated_at,
            by_outcome.get("hold", []),
            {"target_layer": "akber_filter", "applied_change": "none"},
        ),
        _proposal_record(
            "model_routing_update_proposal",
            "Attach explicit model decision refs to future attribution",
            "Current records can identify the Python orchestrator and evidence layers, but model-specific local/frontier LLM contribution is often unknown.",
            generated_at,
            [str(record.get("attribution_record_id")) for record in records if _safe_dict(record.get("component_attribution")).get("local_llm_research_analyst", {}).get("contribution") == "unknown"][:25],
            {"target_layer": "model_stack", "applied_change": "none"},
        ),
        _proposal_record(
            "quantum_review_usage_proposal",
            "Keep quantum review as usefulness-scored annotation until it proves incremental value",
            "Quantum/classical annotations are visible, but current records do not justify changing quantum usage policy.",
            generated_at,
            [str(record.get("attribution_record_id")) for record in records if "quantum_review" in _safe_dict(record.get("component_attribution"))][:25],
            {"target_layer": "quantum_review", "applied_change": "none"},
        ),
        _proposal_record(
            "dashboard_explanation_update_proposal",
            "Show attribution as evidence, not as applied learning",
            "Dashboard and Telegram language should say attribution was recorded and proposals are pending review, not that production settings changed.",
            generated_at,
            [str(record.get("attribution_record_id")) for record in records[:25]],
            {"target_layer": "dashboard_and_telegram_copy", "applied_change": "none"},
        ),
        _proposal_record(
            "paper_lifecycle_repair_proposal",
            "Repair closed-trade lineage before proof or performance learning",
            "Proof-boundary attribution shows closed paper records need complete Research Goal, candidate, Router, order, fill, close, and postmortem lineage.",
            generated_at,
            by_outcome.get("proof_rejected", []) + by_outcome.get("paper_trade_flat_or_unverified", []),
            {"target_layer": "paper_lifecycle_and_proof_boundary", "applied_change": "none"},
        ),
    ]
    return proposals


def _dashboard_summary(
    primary: dict[str, Any],
    proposals: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_attribution_v2_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "attribution_record_count": primary.get("attribution_record_count"),
        "backtest_record_count": primary.get("backtest_record_count"),
        "shadow_record_count": primary.get("shadow_record_count"),
        "akber_record_count": primary.get("akber_record_count"),
        "router_record_count": primary.get("router_record_count"),
        "paperops_record_count": primary.get("paperops_record_count"),
        "missed_opportunity_record_count": primary.get("missed_opportunity_record_count"),
        "paper_trade_outcome_record_count": primary.get("paper_trade_outcome_record_count"),
        "proof_rejected_record_count": primary.get("proof_rejected_record_count"),
        "hold_record_count": primary.get("hold_record_count"),
        "veto_record_count": primary.get("veto_record_count"),
        "component_coverage": primary.get("component_coverage"),
        "outcome_type_counts": primary.get("outcome_type_counts"),
        "proposal_count": proposals.get("proposal_count"),
        "proposal_type_counts": proposals.get("proposal_type_counts"),
        "proposal_applied_count": proposals.get("proposal_applied_count"),
        "authority_mutation_count": primary.get("authority_mutation_count"),
        "applied_update_count": primary.get("applied_update_count"),
        "learning_outputs_are_proposals_only": True,
        "message": (
            "Qadam recorded attribution across source, model, quantum, Akber, Router, PaperOps, shadow, "
            "backtest, hold, missed-opportunity, and paper-trade outcomes. All improvement outputs remain review-only proposals."
        ),
        "authority": _authority(),
    }


def build_learning_attribution_v2(settings: Settings | None = None) -> LearningAttributionV2Bundle:
    generated_at = _iso()
    context = _load_context(settings)
    records = build_attribution_records(context, generated_at)
    proposal_records = build_recursive_improvement_proposals(records, generated_at)
    outcome_counts = Counter(str(record.get("outcome_type")) for record in records)
    evidence_class_counts = Counter(str(record.get("evidence_class")) for record in records)
    proposal_type_counts = Counter(str(record.get("proposal_type")) for record in proposal_records)

    component_coverage: dict[str, bool] = {}
    for component in ATTRIBUTION_COMPONENTS:
        component_coverage[component] = any(
            component in _safe_dict(record.get("component_attribution"))
            for record in records
        )

    applied_update_count = sum(_safe_int(record.get("applied_update_count")) for record in records)
    authority_mutation_count = sum(1 for record in records if record.get("authority_mutation_created") is True)
    proposal_applied_count = sum(1 for proposal in proposal_records if proposal.get("applied") is True)
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_learning_attribution_v2",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "learning_attribution_v2_ready",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "attribution_record_count": len(records),
        "supported_outcome_types": sorted(OUTCOME_TYPES),
        "supported_evidence_classes": sorted(EVIDENCE_CLASSES),
        "supported_proposal_types": sorted(PROPOSAL_TYPES),
        "outcome_type_counts": dict(outcome_counts),
        "evidence_class_counts": dict(evidence_class_counts),
        "component_coverage": component_coverage,
        "backtest_record_count": evidence_class_counts.get("source_price_backtest", 0),
        "shadow_record_count": evidence_class_counts.get("shadow_replay", 0),
        "akber_record_count": evidence_class_counts.get("akber_filter_review", 0),
        "router_record_count": evidence_class_counts.get("router_decision", 0),
        "paperops_record_count": evidence_class_counts.get("paperops_state", 0),
        "missed_opportunity_record_count": evidence_class_counts.get("missed_opportunity", 0),
        "paper_trade_outcome_record_count": evidence_class_counts.get("paper_trade_outcome", 0),
        "proof_rejected_record_count": outcome_counts.get("proof_rejected", 0),
        "hold_record_count": outcome_counts.get("hold", 0),
        "veto_record_count": outcome_counts.get("veto", 0),
        "system_defect_record_count": outcome_counts.get("system_defect", 0),
        "proposal_count": len(proposal_records),
        "proposal_applied_count": proposal_applied_count,
        "applied_update_count": applied_update_count,
        "authority_mutation_count": authority_mutation_count,
        "learning_outputs_are_proposals_only": True,
        "proposal_only": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority(),
        "artifact_refs": {
            "records": RECORDS_ARTIFACT,
            "recursive_improvement_proposals": PROPOSALS_ARTIFACT,
            "proposal_records": PROPOSAL_RECORDS_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
    }
    proposals = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_recursive_improvement_proposals",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "recursive_improvement_proposals_ready_for_review",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "proposal_count": len(proposal_records),
        "proposal_type_counts": dict(proposal_type_counts),
        "proposal_applied_count": proposal_applied_count,
        "applied_update_count": 0,
        "authority_mutation_count": 0,
        "settings_mutation_count": 0,
        "learning_outputs_are_proposals_only": True,
        "proposals": proposal_records,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority(),
        "artifact_refs": {"proposal_records": PROPOSAL_RECORDS_ARTIFACT},
    }
    dashboard_summary = _dashboard_summary(primary, proposals, generated_at)
    return LearningAttributionV2Bundle(
        primary=primary,
        records=records,
        proposals=proposals,
        proposal_records=proposal_records,
        dashboard_summary=dashboard_summary,
    )


def write_learning_attribution_v2(bundle: LearningAttributionV2Bundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "records": runtime / RECORDS_ARTIFACT,
        "proposals": runtime / PROPOSALS_ARTIFACT,
        "proposal_records": runtime / PROPOSAL_RECORDS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["records"], bundle.records)
    _write_json(paths["proposals"], bundle.proposals)
    _write_jsonl(paths["proposal_records"], bundle.proposal_records)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "attribution_record_count": bundle.primary.get("attribution_record_count"),
            "proposal_count": bundle.primary.get("proposal_count"),
            "proposal_applied_count": bundle.primary.get("proposal_applied_count"),
            "authority_mutation_count": bundle.primary.get("authority_mutation_count"),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_learning_attribution_v2(settings: Settings | None = None) -> tuple[LearningAttributionV2Bundle, dict[str, str]]:
    bundle = build_learning_attribution_v2(settings)
    written = write_learning_attribution_v2(bundle, settings)
    return bundle, written


def load_learning_attribution_v2(settings: Settings | None = None) -> LearningAttributionV2Bundle:
    runtime = _runtime_dir(settings)
    primary = _read_json(runtime / PRIMARY_ARTIFACT)
    records = _read_jsonl(runtime / RECORDS_ARTIFACT)
    proposals = _read_json(runtime / PROPOSALS_ARTIFACT)
    proposal_records = _read_jsonl(runtime / PROPOSAL_RECORDS_ARTIFACT)
    dashboard_summary = _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT)
    return LearningAttributionV2Bundle(
        primary=primary,
        records=records,
        proposals=proposals,
        proposal_records=proposal_records,
        dashboard_summary=dashboard_summary,
    )


def _authority_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for key in FORBIDDEN_TRUE_FIELDS:
        if payload.get(key) is True or authority.get(key) is True:
            errors.append(f"{prefix}_{key}_must_remain_false")
    for key in FORBIDDEN_NONZERO_FIELDS:
        if _safe_int(payload.get(key), 0) != 0 or _safe_int(authority.get(key), 0) != 0:
            errors.append(f"{prefix}_{key}_must_remain_zero")
    return errors


def validate_learning_attribution_v2_bundle(bundle: LearningAttributionV2Bundle) -> list[str]:
    errors: list[str] = []
    primary = bundle.primary
    proposals = bundle.proposals
    if primary.get("status") != "learning_attribution_v2_ready":
        errors.append("primary_status_not_ready")
    if not bundle.records:
        errors.append("attribution_records_missing")
    if primary.get("attribution_record_count") != len(bundle.records):
        errors.append("attribution_record_count_mismatch")
    if primary.get("proposal_count") != len(bundle.proposal_records):
        errors.append("proposal_count_mismatch")
    if proposals.get("proposal_count") != len(bundle.proposal_records):
        errors.append("proposal_artifact_count_mismatch")

    supported_outcomes = set(_safe_list(primary.get("supported_outcome_types")))
    if not OUTCOME_TYPES.issubset(supported_outcomes):
        errors.append("supported_outcome_types_incomplete")
    supported_proposals = set(_safe_list(primary.get("supported_proposal_types")))
    if not PROPOSAL_TYPES.issubset(supported_proposals):
        errors.append("supported_proposal_types_incomplete")

    coverage = _safe_dict(primary.get("component_coverage"))
    for component in ATTRIBUTION_COMPONENTS:
        if coverage.get(component) is not True:
            errors.append(f"component_coverage_missing_{component}")

    required_present_outcomes = {
        "backtest_success",
        "shadow_success",
        "hold",
        "missed_opportunity",
        "proof_rejected",
        "paperops_watch_only",
        "system_defect",
    }
    observed_outcomes = {str(record.get("outcome_type")) for record in bundle.records}
    for outcome_type in required_present_outcomes:
        if outcome_type not in observed_outcomes:
            errors.append(f"required_current_outcome_missing_{outcome_type}")

    errors.extend(_authority_errors("primary", primary))
    errors.extend(_authority_errors("proposals", proposals))
    if primary.get("proposal_applied_count") != 0 or proposals.get("proposal_applied_count") != 0:
        errors.append("proposal_applied_count_must_be_zero")
    if primary.get("authority_mutation_count") != 0 or proposals.get("authority_mutation_count") != 0:
        errors.append("authority_mutation_count_must_be_zero")
    if primary.get("applied_update_count") != 0 or proposals.get("applied_update_count") != 0:
        errors.append("applied_update_count_must_be_zero")

    for record in bundle.records:
        record_id = str(record.get("attribution_record_id") or "unknown_record")
        for field in REQUIRED_ATTRIBUTION_FIELDS:
            if field not in record:
                errors.append(f"{record_id}_missing_{field}")
        if record.get("outcome_type") not in OUTCOME_TYPES:
            errors.append(f"{record_id}_invalid_outcome_type")
        if record.get("evidence_class") not in EVIDENCE_CLASSES:
            errors.append(f"{record_id}_invalid_evidence_class")
        learning_signal = _safe_dict(record.get("learning_signal"))
        lesson = str(learning_signal.get("specific_lesson") or "")
        if len(lesson) < 40:
            errors.append(f"{record_id}_specific_lesson_too_short")
        proposal = _safe_dict(record.get("proposal"))
        if proposal.get("proposal_only") is not True or proposal.get("applied") is not False:
            errors.append(f"{record_id}_proposal_boundary_invalid")
        components = _safe_dict(record.get("component_attribution"))
        for component in ATTRIBUTION_COMPONENTS:
            if component not in components:
                errors.append(f"{record_id}_missing_component_{component}")
            elif _safe_dict(components.get(component)).get("contribution") not in CONTRIBUTION_LABELS:
                errors.append(f"{record_id}_invalid_component_contribution_{component}")
        errors.extend(_authority_errors(record_id, record))

    for proposal in bundle.proposal_records:
        proposal_id = str(proposal.get("proposal_id") or "unknown_proposal")
        if proposal.get("proposal_type") not in PROPOSAL_TYPES:
            errors.append(f"{proposal_id}_invalid_proposal_type")
        if proposal.get("proposal_only") is not True:
            errors.append(f"{proposal_id}_proposal_only_not_true")
        if proposal.get("applied") is not False:
            errors.append(f"{proposal_id}_proposal_applied")
        if proposal.get("review_required") is not True:
            errors.append(f"{proposal_id}_review_required_not_true")
        errors.extend(_authority_errors(proposal_id, proposal))
    return errors


def validate_negative_learning_attribution_v2_probes() -> list[str]:
    errors: list[str] = []
    generated_at = _iso()
    bad_record = _record(
        generated_at=generated_at,
        outcome_type="backtest_success",
        evidence_class="source_price_backtest",
        source_artifact="probe.json",
        source_record_id="probe",
        lineage={"instrument": "PROBE"},
        outcome_summary={"plain_english": "probe"},
        component_attribution=_component_attribution(),
        learning_signal={
            "specific_lesson": "Probe verifies that authority mutation is blocked by validation.",
            "what_to_monitor_next": "nothing",
        },
        proposal=_proposal_stub("source_trust_update_proposal", "probe"),
    )
    bad_record["authority_mutation_created"] = True
    bad_bundle = LearningAttributionV2Bundle(
        primary={
            "status": "learning_attribution_v2_ready",
            "attribution_record_count": 1,
            "proposal_count": 0,
            "supported_outcome_types": sorted(OUTCOME_TYPES),
            "supported_proposal_types": sorted(PROPOSAL_TYPES),
            "component_coverage": {component: True for component in ATTRIBUTION_COMPONENTS},
            "proposal_applied_count": 0,
            "authority_mutation_count": 1,
            "applied_update_count": 0,
            "authority": _authority(),
        },
        records=[bad_record],
        proposals={
            "proposal_count": 0,
            "proposal_applied_count": 0,
            "authority_mutation_count": 0,
            "applied_update_count": 0,
            "authority": _authority(),
        },
        proposal_records=[],
        dashboard_summary={},
    )
    if not validate_learning_attribution_v2_bundle(bad_bundle):
        errors.append("negative_probe_authority_mutation_not_detected")

    bad_proposal = _proposal_record(
        "source_trust_update_proposal",
        "Probe applied proposal",
        "Probe verifies applied proposals fail.",
        generated_at,
        [],
        {"target_layer": "probe"},
    )
    bad_proposal["applied"] = True
    bad_bundle = LearningAttributionV2Bundle(
        primary={
            "status": "learning_attribution_v2_ready",
            "attribution_record_count": 1,
            "proposal_count": 1,
            "supported_outcome_types": sorted(OUTCOME_TYPES),
            "supported_proposal_types": sorted(PROPOSAL_TYPES),
            "component_coverage": {component: True for component in ATTRIBUTION_COMPONENTS},
            "proposal_applied_count": 1,
            "authority_mutation_count": 0,
            "applied_update_count": 0,
            "authority": _authority(),
        },
        records=[
            _record(
                generated_at=generated_at,
                outcome_type="system_defect",
                evidence_class="system_defect",
                source_artifact="probe.json",
                source_record_id="probe-system-defect",
                lineage={},
                outcome_summary={"plain_english": "probe"},
                component_attribution=_component_attribution(),
                learning_signal={
                    "specific_lesson": "Probe verifies that applied recursive improvement proposals are rejected.",
                    "what_to_monitor_next": "nothing",
                },
                proposal=_proposal_stub("source_trust_update_proposal", "probe"),
            )
        ],
        proposals={
            "proposal_count": 1,
            "proposal_applied_count": 1,
            "authority_mutation_count": 0,
            "applied_update_count": 0,
            "authority": _authority(),
        },
        proposal_records=[bad_proposal],
        dashboard_summary={},
    )
    if not validate_learning_attribution_v2_bundle(bad_bundle):
        errors.append("negative_probe_applied_proposal_not_detected")
    return errors
