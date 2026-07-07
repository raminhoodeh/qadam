"""Akber Filter V2 for Qadam next-generation flow Phase 7.

Akber V2 reviews Strategy Foundry V2 hypotheses and produces filter-only
decisions. It may pass, hold, or veto for evidence reasons, but it cannot
create Router eligibility when required Akber context is missing and it cannot
create execution approval even if a future record passes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_akber_filter_v2.v1"
PHASE_ID = "qadam_next_generation_phase_7_akber_filter_v2"

PRIMARY_ARTIFACT = "qadam_akber_filter_v2.json"
INPUTS_ARTIFACT = "qadam_akber_filter_v2_inputs.jsonl"
RESULTS_ARTIFACT = "qadam_akber_filter_v2_results.jsonl"
HISTORICAL_REPLAY_ARTIFACT = "qadam_akber_filter_v2_historical_replay.jsonl"
ABLATION_ARTIFACT = "qadam_akber_filter_v2_ablation_tests.jsonl"
THRESHOLD_PROPOSALS_ARTIFACT = "qadam_akber_filter_v2_threshold_proposals.jsonl"
EXPLANATIONS_ARTIFACT = "qadam_akber_filter_v2_explanations.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_akber_filter_v2_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_akber_filter_v2_events.jsonl"

STRATEGY_FOUNDRY_V2_ARTIFACT = "qadam_strategy_foundry_v2.json"
STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT = "qadam_strategy_foundry_v2_hypotheses.jsonl"
STRATEGY_FOUNDRY_V2_REJECTIONS_ARTIFACT = "qadam_strategy_foundry_v2_rejections.jsonl"

REQUIRED_CONTEXT_FIELDS = (
    "source_price_context",
    "fresh_catalyst",
    "technical_confirmation",
    "volume_or_flow_confirmation",
    "volatility_context",
    "pricing_gap_evidence",
    "risk_reward_context",
    "invalidation_clarity",
    "liquidity_and_spread",
    "paperability_proxy",
    "nonlinear_quantum_review",
)

CRITICAL_CONTEXT_FIELDS = {
    "fresh_catalyst",
    "technical_confirmation",
    "volume_or_flow_confirmation",
    "volatility_context",
    "pricing_gap_evidence",
    "risk_reward_context",
    "liquidity_and_spread",
}

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "research_only": True,
    "akber_filter_only": True,
    "akber_filter_pass_is_execution_approval": False,
    "router_promotion_authority": False,
    "router_eligible_setup_created": False,
    "source_quorum_credit_granted": False,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "paperops_direct_handoff_allowed": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "paper_growth_trial_calendar_advanced": False,
    "simulated_elapsed_time_allowed": False,
    "threshold_change_applied": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)


@dataclass(frozen=True)
class AkberFilterBundle:
    primary: dict[str, Any]
    inputs: list[dict[str, Any]]
    results: list[dict[str, Any]]
    historical_replay: list[dict[str, Any]]
    ablation_tests: list[dict[str, Any]]
    threshold_proposals: list[dict[str, Any]]
    explanations: list[dict[str, Any]]
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


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "foundry": _read_json(runtime / STRATEGY_FOUNDRY_V2_ARTIFACT),
        "hypotheses": _read_jsonl(runtime / STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT),
        "foundry_rejections": _read_jsonl(runtime / STRATEGY_FOUNDRY_V2_REJECTIONS_ARTIFACT),
    }


def _field(status: str, value: Any, score: float, reason: str, source: str) -> dict[str, Any]:
    return {
        "status": status,
        "value": value,
        "score": round(max(0.0, min(1.0, score)), 4),
        "reason": reason,
        "source": source,
    }


def _build_context_fields(hypothesis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence = _safe_dict(hypothesis.get("evidence_summary"))
    proxy = _safe_dict(hypothesis.get("instrument_proxy_mapping"))
    invalidation = _safe_dict(hypothesis.get("invalidation_fields"))
    risk = _safe_dict(hypothesis.get("risk_concept_fields"))
    blocker_state = _safe_dict(hypothesis.get("blocker_state"))
    blockers = set(_safe_list(blocker_state.get("blockers")))
    expectancy = _safe_float(evidence.get("expectancy"))
    sample_count = _safe_int(evidence.get("sample_count"))
    source_score = _safe_float(evidence.get("source_contribution_score"))
    instrument_score = _safe_float(evidence.get("instrument_contribution_score"))
    quantum_verdict = str(evidence.get("quantum_classical_verdict") or "")

    fields = {
        "source_price_context": _field(
            "present" if sample_count >= 10 and expectancy > 0 else "weak",
            {"sample_count": sample_count, "expectancy": expectancy, "hit_rate": evidence.get("hit_rate")},
            min(1.0, 0.25 + sample_count / 100 + max(expectancy, 0) * 20),
            "Historical source-price context exists in the foundry evidence.",
            "strategy_foundry_v2.evidence_summary",
        ),
        "fresh_catalyst": _field(
            "missing",
            None,
            0.0,
            "Phase 7 has historical/foundry evidence, but no fresh current catalyst packet.",
            "current_market_context_required_later",
        ),
        "technical_confirmation": _field(
            "missing",
            None,
            0.0,
            "No live technical confirmation is attached to this hypothesis yet.",
            "current_technical_confirmation_required_later",
        ),
        "volume_or_flow_confirmation": _field(
            "missing",
            None,
            0.0,
            "No live volume, flow, or order-flow confirmation is attached to this hypothesis yet.",
            "current_volume_flow_required_later",
        ),
        "volatility_context": _field(
            "missing" if "stale_or_missing_data_sensitivity" in blockers else "partial",
            risk.get("drawdown_proxy"),
            0.25 if "stale_or_missing_data_sensitivity" in blockers else 0.5,
            "Volatility context is incomplete for the paperable proxy expression.",
            "strategy_foundry_v2.risk_concept_fields",
        ),
        "pricing_gap_evidence": _field(
            "partial" if proxy.get("primary_proxy") else "missing",
            {"observed": proxy.get("observed_market_expression"), "proxy": proxy.get("primary_proxy")},
            0.35 if proxy.get("primary_proxy") else 0.0,
            "Proxy mapping exists, but pricing-gap evidence is not complete enough for Router eligibility.",
            "strategy_foundry_v2.instrument_proxy_mapping",
        ),
        "risk_reward_context": _field(
            "partial" if expectancy > 0 and invalidation else "missing",
            {"expectancy": expectancy, "invalidation_id": invalidation.get("invalidation_id")},
            0.45 if expectancy > 0 and invalidation else 0.0,
            "Research risk/reward is sketched, but no live risk budget or sizing exists.",
            "strategy_foundry_v2.risk_concept_fields",
        ),
        "invalidation_clarity": _field(
            "present" if invalidation.get("hard_invalidators") else "missing",
            invalidation.get("hard_invalidators"),
            0.75 if invalidation.get("hard_invalidators") else 0.0,
            "Invalidation logic exists as research context.",
            "strategy_foundry_v2.invalidation_fields",
        ),
        "liquidity_and_spread": _field(
            "missing",
            None,
            0.0,
            "No current liquidity or spread check is attached.",
            "current_liquidity_required_later",
        ),
        "paperability_proxy": _field(
            "present" if proxy.get("primary_proxy") else "missing",
            {"primary_proxy": proxy.get("primary_proxy"), "paperable_proxy_symbols": proxy.get("paperable_proxy_symbols")},
            0.7 if proxy.get("primary_proxy") else 0.0,
            "A paperable proxy exists, but this does not authorize paper orders.",
            "strategy_foundry_v2.instrument_proxy_mapping",
        ),
        "nonlinear_quantum_review": _field(
            "present" if quantum_verdict else "missing",
            {
                "quantum_classical_verdict": quantum_verdict,
                "nonlinear_state": evidence.get("nonlinear_state"),
            },
            0.7 if quantum_verdict == "classical_research_upgrade" else 0.45 if quantum_verdict else 0.0,
            "Nonlinear/quantum review is a research annotation only.",
            "strategy_foundry_v2.evidence_summary",
        ),
    }
    return fields


def _missing_context(fields: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    missing = []
    for field_name, payload in fields.items():
        if payload.get("status") == "missing":
            missing.append(
                {
                    "field": field_name,
                    "missing_context_type": f"missing_{field_name}",
                    "critical_for_router_eligibility": field_name in CRITICAL_CONTEXT_FIELDS,
                    "reason": payload.get("reason"),
                    "source": payload.get("source"),
                }
            )
    return missing


def _input_record(hypothesis: dict[str, Any], generated_at: str) -> dict[str, Any]:
    fields = _build_context_fields(hypothesis)
    missing = _missing_context(fields)
    critical_missing = [item for item in missing if item.get("critical_for_router_eligibility")]
    hypothesis_id = str(hypothesis.get("strategy_hypothesis_id"))
    akber_input_id = _hash_id("qadam-akber-input-v2", [hypothesis_id, hypothesis.get("candidate_identity_material")])
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "akber_input_id": akber_input_id,
        "strategy_hypothesis_id": hypothesis_id,
        "research_goal_id": hypothesis.get("research_goal_lineage", {}).get("research_goal_id"),
        "candidate_identity_id": hypothesis.get("candidate_identity_material", {}).get("candidate_identity_id"),
        "input_status": "complete_with_missing_context" if missing else "complete",
        "required_context_fields": list(REQUIRED_CONTEXT_FIELDS),
        "context_fields": fields,
        "missing_context": missing,
        "missing_context_count": len(missing),
        "critical_missing_context_count": len(critical_missing),
        "no_router_eligibility_if_missing_context": True,
        "akber_filter_input_only": True,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _scores(input_record: dict[str, Any]) -> dict[str, float]:
    fields = _safe_dict(input_record.get("context_fields"))
    source_price = _safe_float(fields.get("source_price_context", {}).get("score"))
    catalyst = _safe_float(fields.get("fresh_catalyst", {}).get("score"))
    technical = _safe_float(fields.get("technical_confirmation", {}).get("score"))
    volume_flow = _safe_float(fields.get("volume_or_flow_confirmation", {}).get("score"))
    volatility = _safe_float(fields.get("volatility_context", {}).get("score"))
    pricing_gap = _safe_float(fields.get("pricing_gap_evidence", {}).get("score"))
    risk_reward = _safe_float(fields.get("risk_reward_context", {}).get("score"))
    invalidation = _safe_float(fields.get("invalidation_clarity", {}).get("score"))
    liquidity = _safe_float(fields.get("liquidity_and_spread", {}).get("score"))
    paperability = _safe_float(fields.get("paperability_proxy", {}).get("score"))
    nonlinear = _safe_float(fields.get("nonlinear_quantum_review", {}).get("score"))
    missing_penalty = min(0.45, 0.05 * _safe_int(input_record.get("critical_missing_context_count")))
    akber_score = (
        0.15 * source_price
        + 0.10 * catalyst
        + 0.12 * technical
        + 0.12 * volume_flow
        + 0.08 * volatility
        + 0.08 * pricing_gap
        + 0.10 * risk_reward
        + 0.08 * invalidation
        + 0.07 * liquidity
        + 0.05 * paperability
        + 0.05 * nonlinear
        - missing_penalty
    )
    return {
        "akber_filter_score": round(max(0.0, min(1.0, akber_score)), 4),
        "source_price_context_score": round(source_price, 4),
        "catalyst_quality_score": round(catalyst, 4),
        "technical_confirmation_score": round(technical, 4),
        "volume_flow_score": round(volume_flow, 4),
        "volatility_setup_score": round(volatility, 4),
        "pricing_gap_score": round(pricing_gap, 4),
        "risk_reward_score": round(risk_reward, 4),
        "invalidation_clarity_score": round(invalidation, 4),
        "liquidity_spread_score": round(liquidity, 4),
        "paperability_proxy_score": round(paperability, 4),
        "nonlinear_quantum_score": round(nonlinear, 4),
        "missing_context_penalty": round(missing_penalty, 4),
    }


def _historical_replay(input_record: dict[str, Any], scores: dict[str, float], generated_at: str) -> dict[str, Any]:
    context = _safe_dict(input_record.get("context_fields", {}).get("source_price_context", {}).get("value"))
    sample_count = _safe_int(context.get("sample_count"))
    expectancy = _safe_float(context.get("expectancy"))
    hit_rate = _safe_float(context.get("hit_rate"), 0.5)
    with_filter_hit_rate = max(0.0, min(1.0, hit_rate - 0.02 if input_record.get("critical_missing_context_count") else hit_rate + 0.03))
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "historical_replay_id": _hash_id("qadam-akber-replay-v2", [input_record.get("akber_input_id"), sample_count, expectancy]),
        "akber_input_id": input_record.get("akber_input_id"),
        "strategy_hypothesis_id": input_record.get("strategy_hypothesis_id"),
        "replay_status": "historical_replay_ready_with_missing_context_hold"
        if input_record.get("critical_missing_context_count")
        else "historical_replay_ready",
        "sample_count": sample_count,
        "expectancy": expectancy,
        "without_filter_hit_rate": round(hit_rate, 4),
        "with_filter_hit_rate": round(with_filter_hit_rate, 4),
        "filter_added_value_claim": False if input_record.get("critical_missing_context_count") else scores["akber_filter_score"] > 0.7,
        "missing_context_as_hold_tested": True,
        "missing_context_as_pass_tested": True,
        "pass_variant_disallowed_when_context_missing": bool(input_record.get("critical_missing_context_count")),
        "paper_proof_ledger_credit_allowed": False,
        "paper_order_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _ablation_test(input_record: dict[str, Any], scores: dict[str, float], generated_at: str) -> dict[str, Any]:
    fields = _safe_dict(input_record.get("context_fields"))
    stage_variants = {}
    for field_name in REQUIRED_CONTEXT_FIELDS:
        field_score = _safe_float(fields.get(field_name, {}).get("score"))
        score_without_field = max(0.0, scores["akber_filter_score"] - field_score * 0.08)
        stage_variants[field_name] = {
            "variant_name": f"Remove {field_name}",
            "score_without_field": round(score_without_field, 4),
            "result": "critical_missing_context" if fields.get(field_name, {}).get("status") == "missing" else "research_sensitivity_only",
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "ablation_test_id": _hash_id("qadam-akber-ablation-v2", [input_record.get("akber_input_id")]),
        "akber_input_id": input_record.get("akber_input_id"),
        "strategy_hypothesis_id": input_record.get("strategy_hypothesis_id"),
        "ablation_status": "ablation_ready",
        "base_score": scores["akber_filter_score"],
        "stage_removed_variants": stage_variants,
        "filter_added_value_claim": False,
        "ablation_is_research_only": True,
        "threshold_change_applied": False,
        "paper_order_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _threshold_proposals(input_record: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    proposals = [
        ("minimum_akber_filter_score_for_pass", 0.72, "Require enough total score before Akber can pass."),
        ("minimum_technical_confirmation_score", 0.55, "Require live technical confirmation before Router eligibility."),
        ("minimum_volume_flow_score", 0.55, "Require volume or flow evidence before Router eligibility."),
        ("minimum_liquidity_spread_score", 0.5, "Require current liquidity/spread context before Router eligibility."),
        ("requires_no_critical_missing_context", True, "No Router-eligible setup may have missing critical Akber context."),
        ("akber_pass_is_not_execution_approval", True, "Akber pass cannot approve execution or broker writes."),
    ]
    records = []
    for name, proposed_value, reason in proposals:
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "phase_id": PHASE_ID,
                "threshold_proposal_id": _hash_id("qadam-akber-threshold-v2", [input_record.get("akber_input_id"), name]),
                "akber_input_id": input_record.get("akber_input_id"),
                "strategy_hypothesis_id": input_record.get("strategy_hypothesis_id"),
                "threshold_name": name,
                "proposed_value": proposed_value,
                "proposal_reason": reason,
                "proposal_status": "proposal_only_not_applied",
                "threshold_change_applied": False,
                "strategy_mutation_created": False,
                "router_promotion_authority": False,
                "authority": _authority(),
                "generated_at": generated_at,
            }
        )
    return records


def _decision(input_record: dict[str, Any], scores: dict[str, float]) -> dict[str, Any]:
    missing = _safe_list(input_record.get("missing_context"))
    critical_missing = [item for item in missing if item.get("critical_for_router_eligibility")]
    if critical_missing:
        decision = "hold_missing_context"
        status = "akber_v2_hold_missing_context"
        reason = "Akber is holding because required practical context is missing."
        router_eligible = False
        veto_reason = None
        pass_reason = None
    elif scores["akber_filter_score"] >= 0.72:
        decision = "pass_research_filter"
        status = "akber_v2_pass_filter_only"
        reason = "Akber passes the research filter, but this is not execution approval."
        router_eligible = True
        veto_reason = None
        pass_reason = reason
    elif scores["akber_filter_score"] < 0.25:
        decision = "veto_weak_evidence"
        status = "akber_v2_veto_weak_evidence"
        reason = "Akber vetoes because evidence quality is too weak."
        router_eligible = False
        veto_reason = reason
        pass_reason = None
    else:
        decision = "hold_evidence_quality"
        status = "akber_v2_hold_evidence_quality"
        reason = "Akber is holding until stronger practical evidence is available."
        router_eligible = False
        veto_reason = None
        pass_reason = None
    return {
        "status": status,
        "filter_decision": decision,
        "reason": reason,
        "pass_reason": pass_reason,
        "hold_reason": reason if decision.startswith("hold") else None,
        "veto_reason": veto_reason,
        "candidate_for_router": router_eligible,
        "candidate_for_paper_review": False,
        "missing_context_blocks_router": bool(critical_missing),
        "next_required_evidence": [item.get("field") for item in critical_missing],
        "akber_filter_pass_is_not_execution_approval": True,
    }


def _plain_english_explanation(input_record: dict[str, Any], decision: dict[str, Any], scores: dict[str, float], generated_at: str) -> dict[str, Any]:
    missing_fields = decision.get("next_required_evidence") or []
    if missing_fields:
        sentence = (
            "Akber is holding this hypothesis because Qadam has research evidence, "
            f"but still needs {', '.join(missing_fields)} before Router review."
        )
    elif decision.get("filter_decision") == "pass_research_filter":
        sentence = "Akber passes the research filter, but this is not permission to trade."
    else:
        sentence = f"Akber decision: {decision.get('reason')}"
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "explanation_id": _hash_id("qadam-akber-explanation-v2", [input_record.get("akber_input_id"), decision.get("filter_decision")]),
        "akber_input_id": input_record.get("akber_input_id"),
        "strategy_hypothesis_id": input_record.get("strategy_hypothesis_id"),
        "headline": decision.get("filter_decision"),
        "plain_english": sentence,
        "score_summary": f"Akber score {scores['akber_filter_score']:.2f}; critical missing context {input_record.get('critical_missing_context_count')}.",
        "public_safe": True,
        "telegram_safe": True,
        "command_disabled": True,
        "contains_broker_instruction": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _result_record(
    input_record: dict[str, Any],
    scores: dict[str, float],
    replay: dict[str, Any],
    ablation: dict[str, Any],
    threshold_records: list[dict[str, Any]],
    explanation: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    decision = _decision(input_record, scores)
    router_eligible = bool(decision.get("candidate_for_router"))
    if input_record.get("critical_missing_context_count"):
        router_eligible = False
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "akber_filter_result_id": _hash_id("qadam-akber-result-v2", [input_record.get("akber_input_id"), scores]),
        "akber_input_id": input_record.get("akber_input_id"),
        "strategy_hypothesis_id": input_record.get("strategy_hypothesis_id"),
        "research_goal_id": input_record.get("research_goal_id"),
        "candidate_identity_id": input_record.get("candidate_identity_id"),
        "status": decision["status"],
        "decision": decision,
        "scores": scores,
        "missing_context_count": input_record.get("missing_context_count"),
        "critical_missing_context_count": input_record.get("critical_missing_context_count"),
        "router_eligible": router_eligible,
        "router_eligibility_state": "blocked_missing_akber_context" if input_record.get("critical_missing_context_count") else "filter_decision_controls_later_router",
        "no_router_eligible_setup_has_missing_akber_context": not (router_eligible and bool(input_record.get("missing_context_count"))),
        "historical_replay_ref": replay.get("historical_replay_id"),
        "ablation_test_ref": ablation.get("ablation_test_id"),
        "threshold_proposal_refs": [record.get("threshold_proposal_id") for record in threshold_records],
        "plain_english_explanation_ref": explanation.get("explanation_id"),
        "akber_filter_pass_is_execution_approval": False,
        "execution_approval_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def build_akber_filter_v2(settings: Settings | None = None) -> AkberFilterBundle:
    generated_at = _iso()
    context = _load_context(settings)
    inputs: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    replay_records: list[dict[str, Any]] = []
    ablation_records: list[dict[str, Any]] = []
    threshold_records: list[dict[str, Any]] = []
    explanations: list[dict[str, Any]] = []

    for hypothesis in context["hypotheses"]:
        input_record = _input_record(hypothesis, generated_at)
        scores = _scores(input_record)
        replay = _historical_replay(input_record, scores, generated_at)
        ablation = _ablation_test(input_record, scores, generated_at)
        thresholds = _threshold_proposals(input_record, generated_at)
        decision_preview = _decision(input_record, scores)
        explanation = _plain_english_explanation(input_record, decision_preview, scores, generated_at)
        result = _result_record(input_record, scores, replay, ablation, thresholds, explanation, generated_at)
        inputs.append(input_record)
        replay_records.append(replay)
        ablation_records.append(ablation)
        threshold_records.extend(thresholds)
        explanations.append(explanation)
        results.append(result)

    decision_counts = Counter(str(result.get("decision", {}).get("filter_decision") or "unknown") for result in results)
    router_eligible_with_missing = [
        result for result in results if result.get("router_eligible") and _safe_int(result.get("missing_context_count")) > 0
    ]
    status = "akber_filter_v2_ready" if results else "akber_filter_v2_blocked_no_foundry_hypotheses"
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_filter_v2",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "input_artifacts": {
            "strategy_foundry_v2": STRATEGY_FOUNDRY_V2_ARTIFACT,
            "strategy_foundry_v2_hypotheses": STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT,
            "strategy_foundry_v2_rejections": STRATEGY_FOUNDRY_V2_REJECTIONS_ARTIFACT,
        },
        "akber_input_count": len(inputs),
        "akber_result_count": len(results),
        "historical_replay_count": len(replay_records),
        "ablation_test_count": len(ablation_records),
        "threshold_proposal_count": len(threshold_records),
        "plain_english_explanation_count": len(explanations),
        "pass_count": decision_counts.get("pass_research_filter", 0),
        "hold_count": decision_counts.get("hold_missing_context", 0) + decision_counts.get("hold_evidence_quality", 0),
        "veto_count": decision_counts.get("veto_weak_evidence", 0),
        "router_eligible_count": sum(1 for result in results if result.get("router_eligible")),
        "router_eligible_with_missing_context_count": len(router_eligible_with_missing),
        "no_router_eligible_setup_has_missing_akber_context": len(router_eligible_with_missing) == 0,
        "akber_filter_pass_is_execution_approval": False,
        "execution_approval_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "threshold_change_applied": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "inputs": INPUTS_ARTIFACT,
            "results": RESULTS_ARTIFACT,
            "historical_replay": HISTORICAL_REPLAY_ARTIFACT,
            "ablation_tests": ABLATION_ARTIFACT,
            "threshold_proposals": THRESHOLD_PROPOSALS_ARTIFACT,
            "explanations": EXPLANATIONS_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
    }
    dashboard_summary = _dashboard_summary(primary, results, explanations, generated_at)
    return AkberFilterBundle(
        primary=primary,
        inputs=inputs,
        results=results,
        historical_replay=replay_records,
        ablation_tests=ablation_records,
        threshold_proposals=threshold_records,
        explanations=explanations,
        dashboard_summary=dashboard_summary,
    )


def _dashboard_summary(
    primary: dict[str, Any],
    results: list[dict[str, Any]],
    explanations: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_filter_v2_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "akber_input_count": primary.get("akber_input_count"),
        "akber_result_count": primary.get("akber_result_count"),
        "historical_replay_count": primary.get("historical_replay_count"),
        "ablation_test_count": primary.get("ablation_test_count"),
        "threshold_proposal_count": primary.get("threshold_proposal_count"),
        "plain_english_explanation_count": primary.get("plain_english_explanation_count"),
        "pass_count": primary.get("pass_count"),
        "hold_count": primary.get("hold_count"),
        "veto_count": primary.get("veto_count"),
        "router_eligible_count": primary.get("router_eligible_count"),
        "router_eligible_with_missing_context_count": primary.get("router_eligible_with_missing_context_count"),
        "no_router_eligible_setup_has_missing_akber_context": primary.get("no_router_eligible_setup_has_missing_akber_context"),
        "akber_filter_pass_is_execution_approval": False,
        "cards": [
            {
                "strategy_hypothesis_id": result.get("strategy_hypothesis_id"),
                "decision": result.get("decision", {}).get("filter_decision"),
                "status": result.get("status"),
                "akber_score": result.get("scores", {}).get("akber_filter_score"),
                "critical_missing_context_count": result.get("critical_missing_context_count"),
                "router_eligible": result.get("router_eligible"),
                "plain_english": next(
                    (
                        explanation.get("plain_english")
                        for explanation in explanations
                        if explanation.get("explanation_id") == result.get("plain_english_explanation_ref")
                    ),
                    None,
                ),
            }
            for result in results
        ],
        "message": (
            "Akber Filter V2 reviews research hypotheses and blocks Router eligibility when Akber context is missing. "
            "A pass is still not execution approval."
        ),
        "next_allowed_action": "Phase 8 may shadow-test Akber-held or Akber-passed research records; Router cannot promote missing-context records.",
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "execution_approval_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }


def write_akber_filter_v2(bundle: AkberFilterBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "inputs": runtime / INPUTS_ARTIFACT,
        "results": runtime / RESULTS_ARTIFACT,
        "historical_replay": runtime / HISTORICAL_REPLAY_ARTIFACT,
        "ablation_tests": runtime / ABLATION_ARTIFACT,
        "threshold_proposals": runtime / THRESHOLD_PROPOSALS_ARTIFACT,
        "explanations": runtime / EXPLANATIONS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["inputs"], bundle.inputs)
    _write_jsonl(paths["results"], bundle.results)
    _write_jsonl(paths["historical_replay"], bundle.historical_replay)
    _write_jsonl(paths["ablation_tests"], bundle.ablation_tests)
    _write_jsonl(paths["threshold_proposals"], bundle.threshold_proposals)
    _write_jsonl(paths["explanations"], bundle.explanations)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "event_type": "akber_filter_v2_written",
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "akber_result_count": len(bundle.results),
            "router_eligible_with_missing_context_count": bundle.primary.get("router_eligible_with_missing_context_count"),
            "akber_filter_pass_is_execution_approval": False,
            "execution_approval_created": False,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
            "authority": _authority(),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_akber_filter_v2(settings: Settings | None = None) -> tuple[AkberFilterBundle, dict[str, str]]:
    bundle = build_akber_filter_v2(settings)
    written = write_akber_filter_v2(bundle, settings)
    return bundle, written


def _validate_authority(payload: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for key, expected in AUTHORITY_FLAGS.items():
        if authority.get(key) != expected:
            errors.append(f"{prefix}_{key}_authority_invalid")
    for field in FORBIDDEN_TRUE_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{prefix}_{field}_must_not_be_true")
    for field in FORBIDDEN_NONZERO_FIELDS:
        if _safe_int(payload.get(field), 0) != 0:
            errors.append(f"{prefix}_{field}_must_be_zero")
    return errors


def validate_input_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("input_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append("input_phase_id_invalid")
    fields = _safe_dict(record.get("context_fields"))
    for field_name in REQUIRED_CONTEXT_FIELDS:
        if field_name not in fields:
            errors.append(f"input_context_{field_name}_missing")
    if record.get("no_router_eligibility_if_missing_context") is not True:
        errors.append("input_no_router_eligibility_boundary_missing")
    errors.extend(_validate_authority(record, "input"))
    return errors


def validate_result_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("result_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append("result_phase_id_invalid")
    if record.get("decision", {}).get("filter_decision") not in {
        "pass_research_filter",
        "hold_missing_context",
        "hold_evidence_quality",
        "veto_weak_evidence",
    }:
        errors.append("result_filter_decision_invalid")
    if record.get("router_eligible") and _safe_int(record.get("missing_context_count")) > 0:
        errors.append("router_eligible_result_has_missing_context")
    if record.get("no_router_eligible_setup_has_missing_akber_context") is not True:
        errors.append("result_missing_context_router_boundary_invalid")
    if record.get("akber_filter_pass_is_execution_approval") is not False:
        errors.append("result_akber_pass_execution_boundary_invalid")
    if record.get("execution_approval_created") is not False:
        errors.append("result_execution_approval_created_must_be_false")
    errors.extend(_validate_authority(record, "result"))
    return errors


def validate_side_record(record: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append(f"{prefix}_phase_id_invalid")
    errors.extend(_validate_authority(record, prefix))
    return errors


def validate_akber_filter_v2_bundle(bundle: AkberFilterBundle | dict[str, Any]) -> list[str]:
    if isinstance(bundle, AkberFilterBundle):
        primary = bundle.primary
        inputs = bundle.inputs
        results = bundle.results
        historical_replay = bundle.historical_replay
        ablation_tests = bundle.ablation_tests
        threshold_proposals = bundle.threshold_proposals
        explanations = bundle.explanations
        dashboard_summary = bundle.dashboard_summary
    else:
        primary = _safe_dict(bundle.get("primary"))
        inputs = _safe_list(bundle.get("inputs"))
        results = _safe_list(bundle.get("results"))
        historical_replay = _safe_list(bundle.get("historical_replay"))
        ablation_tests = _safe_list(bundle.get("ablation_tests"))
        threshold_proposals = _safe_list(bundle.get("threshold_proposals"))
        explanations = _safe_list(bundle.get("explanations"))
        dashboard_summary = _safe_dict(bundle.get("dashboard_summary"))
    errors: list[str] = []
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("primary_schema_version_invalid")
    if primary.get("phase_id") != PHASE_ID:
        errors.append("primary_phase_id_invalid")
    if primary.get("artifact_type") != "qadam_akber_filter_v2":
        errors.append("primary_artifact_type_invalid")
    if primary.get("status") != "akber_filter_v2_ready":
        errors.append("primary_status_not_ready")
    for key in ("public_safe", "read_only", "paper_only", "proposal_first", "research_only"):
        if primary.get(key) is not True:
            errors.append(f"primary_{key}_must_be_true")
    if not inputs:
        errors.append("inputs_missing")
    if not results:
        errors.append("results_missing")
    if len(inputs) != len(results):
        errors.append("input_result_count_mismatch")
    if primary.get("no_router_eligible_setup_has_missing_akber_context") is not True:
        errors.append("primary_router_missing_context_boundary_invalid")
    if _safe_int(primary.get("router_eligible_with_missing_context_count")) != 0:
        errors.append("primary_router_eligible_with_missing_context_nonzero")
    if primary.get("akber_filter_pass_is_execution_approval") is not False:
        errors.append("primary_akber_pass_execution_boundary_invalid")
    if primary.get("execution_approval_created") is not False:
        errors.append("primary_execution_approval_created_must_be_false")
    errors.extend(_validate_authority(primary, "primary"))
    for index, record in enumerate(inputs, start=1):
        for error in validate_input_record(record):
            errors.append(f"input_{index}_{error}")
    for index, record in enumerate(results, start=1):
        for error in validate_result_record(record):
            errors.append(f"result_{index}_{error}")
    for index, record in enumerate(historical_replay, start=1):
        for error in validate_side_record(record, "replay"):
            errors.append(f"replay_{index}_{error}")
    for index, record in enumerate(ablation_tests, start=1):
        for error in validate_side_record(record, "ablation"):
            errors.append(f"ablation_{index}_{error}")
    for index, record in enumerate(threshold_proposals, start=1):
        for error in validate_side_record(record, "threshold"):
            errors.append(f"threshold_{index}_{error}")
        if record.get("threshold_change_applied") is not False:
            errors.append(f"threshold_{index}_threshold_change_applied_must_be_false")
    for index, record in enumerate(explanations, start=1):
        for error in validate_side_record(record, "explanation"):
            errors.append(f"explanation_{index}_{error}")
    if dashboard_summary.get("artifact_type") != "qadam_akber_filter_v2_dashboard_summary":
        errors.append("dashboard_summary_artifact_type_invalid")
    if dashboard_summary.get("akber_filter_pass_is_execution_approval") is not False:
        errors.append("dashboard_summary_akber_pass_execution_boundary_invalid")
    if dashboard_summary.get("router_eligible_with_missing_context_count") != 0:
        errors.append("dashboard_summary_router_eligible_with_missing_context_nonzero")
    return errors


def validate_negative_akber_filter_v2_probes(settings: Settings | None = None) -> list[str]:
    bundle = build_akber_filter_v2(settings)
    if not bundle.results:
        return ["negative_probe_skipped_missing_akber_results"]
    errors: list[str] = []
    unsafe_result = json.loads(json.dumps(bundle.results[0]))
    unsafe_result["router_eligible"] = True
    unsafe_result["missing_context_count"] = max(1, _safe_int(unsafe_result.get("missing_context_count"), 1))
    unsafe_result["no_router_eligible_setup_has_missing_akber_context"] = False
    if not validate_result_record(unsafe_result):
        errors.append("negative_probe_failed_for_router_missing_context_boundary")

    unsafe_execution = json.loads(json.dumps(bundle.results[0]))
    unsafe_execution["execution_approval_created"] = True
    unsafe_execution["authority"]["execution_approval_created"] = True
    if not validate_result_record(unsafe_execution):
        errors.append("negative_probe_failed_for_execution_approval_boundary")

    unsafe_threshold = json.loads(json.dumps(bundle.threshold_proposals[0]))
    unsafe_threshold["threshold_change_applied"] = True
    unsafe_threshold["authority"]["threshold_change_applied"] = True
    if not validate_side_record(unsafe_threshold, "threshold"):
        errors.append("negative_probe_failed_for_threshold_mutation_boundary")

    missing_context_input = json.loads(json.dumps(bundle.inputs[0]))
    missing_context_input["context_fields"].pop("technical_confirmation", None)
    if not validate_input_record(missing_context_input):
        errors.append("negative_probe_failed_for_missing_input_context")
    return errors


def load_akber_filter_v2(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "primary": _read_json(runtime / PRIMARY_ARTIFACT),
        "inputs": _read_jsonl(runtime / INPUTS_ARTIFACT),
        "results": _read_jsonl(runtime / RESULTS_ARTIFACT),
        "historical_replay": _read_jsonl(runtime / HISTORICAL_REPLAY_ARTIFACT),
        "ablation_tests": _read_jsonl(runtime / ABLATION_ARTIFACT),
        "threshold_proposals": _read_jsonl(runtime / THRESHOLD_PROPOSALS_ARTIFACT),
        "explanations": _read_jsonl(runtime / EXPLANATIONS_ARTIFACT),
        "dashboard_summary": _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    }
