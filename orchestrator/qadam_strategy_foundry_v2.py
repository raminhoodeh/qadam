"""Strategy Foundry V2 for Qadam next-generation flow Phase 6.

This module turns evidence-backed strategy maps into research-only strategy
hypotheses and rejects weak hypotheses before Akber. A hypothesis produced here
is not a trade candidate, qualified setup, approval, route decision, order,
broker write, or proof-ledger item.
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

SCHEMA_VERSION = "qadam_strategy_foundry_v2.v1"
PHASE_ID = "qadam_next_generation_phase_6_strategy_foundry_v2"

PRIMARY_ARTIFACT = "qadam_strategy_foundry_v2.json"
HYPOTHESES_ARTIFACT = "qadam_strategy_foundry_v2_hypotheses.jsonl"
REJECTIONS_ARTIFACT = "qadam_strategy_foundry_v2_rejections.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_strategy_foundry_v2_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_strategy_foundry_v2_events.jsonl"

STRATEGY_EVIDENCE_MAP_ARTIFACT = "qadam_strategy_evidence_map.json"
STRATEGY_EVIDENCE_RECORDS_ARTIFACT = "qadam_strategy_evidence_map_records.jsonl"
PATTERN_ENGINE_V2_RECORDS_ARTIFACT = "qadam_pattern_engine_v2_records.jsonl"

REQUIRED_HYPOTHESIS_SECTIONS = (
    "research_goal_lineage",
    "candidate_identity_material",
    "instrument_proxy_mapping",
    "invalidation_fields",
    "risk_concept_fields",
    "blocker_state",
    "evidence_summary",
)

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "research_only": True,
    "strategy_hypothesis_only": True,
    "research_strategy_hypothesis_generation_allowed": True,
    "akber_filter_run": False,
    "akber_filter_passed": False,
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
    "strategy_approved": False,
    "strategy_family_active": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "source_weight_update_allowed": False,
    "source_weight_update_applied": False,
    "model_weight_update_allowed": False,
    "model_weight_update_created": False,
    "filter_threshold_update_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)

MIN_CONFIDENCE_SCORE_FOR_HYPOTHESIS = 0.35
MAX_HYPOTHESES_PER_STRATEGY = 4


@dataclass(frozen=True)
class StrategyFoundryBundle:
    primary: dict[str, Any]
    hypotheses: list[dict[str, Any]]
    rejections: list[dict[str, Any]]
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
        "strategy_evidence_map": _read_json(runtime / STRATEGY_EVIDENCE_MAP_ARTIFACT),
        "strategy_records": _read_jsonl(runtime / STRATEGY_EVIDENCE_RECORDS_ARTIFACT),
        "pattern_records": _read_jsonl(runtime / PATTERN_ENGINE_V2_RECORDS_ARTIFACT),
    }


def _patterns_by_id(patterns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(pattern.get("pattern_id")): pattern
        for pattern in patterns
        if pattern.get("pattern_id")
    }


def _primary_proxy(strategy_record: dict[str, Any], pattern: dict[str, Any]) -> str | None:
    paperability = _safe_dict(strategy_record.get("paperability_limits"))
    paperable = [str(item) for item in _safe_list(paperability.get("paperable_proxy_symbols")) if item]
    observed = str(pattern.get("market_or_symbol") or "")
    if observed and observed in paperable:
        return observed
    for preferred in ("USO", "SLV", "SMH", "ITA", "XLE", "SOXX", "BNO"):
        if preferred in paperable:
            return preferred
    return paperable[0] if paperable else None


def _research_goal_lineage(strategy_record: dict[str, Any], pattern: dict[str, Any]) -> dict[str, Any]:
    family_id = str(strategy_record.get("strategy_family_id"))
    pattern_id = str(pattern.get("pattern_id"))
    research_goal_id = _hash_id("qadam-rg-v2", [family_id, pattern_id, pattern.get("time_window")])
    return {
        "research_goal_id": research_goal_id,
        "origin_phase": "Phase 4 Pattern Engine V2",
        "foundry_phase": PHASE_ID,
        "target_strategy_family": family_id,
        "strategy_evidence_map_id": strategy_record.get("strategy_evidence_map_id"),
        "source_pattern_id": pattern_id,
        "source_pattern_rank": pattern.get("rank"),
        "evidence_chain": [
            "Phase 4 Pattern Engine V2 ranked research pattern",
            "Phase 5 Strategy Evidence Map evidence-backed family",
            "Phase 6 Strategy Foundry V2 research-only hypothesis",
        ],
        "paper_growth_trial_calendar_advance_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
    }


def _candidate_identity_material(
    strategy_record: dict[str, Any],
    pattern: dict[str, Any],
    research_goal_lineage: dict[str, Any],
    primary_proxy: str | None,
) -> dict[str, Any]:
    family_id = str(strategy_record.get("strategy_family_id"))
    observed = str(pattern.get("market_or_symbol") or "")
    time_window = str(pattern.get("time_window") or "")
    thesis = (
        f"{strategy_record.get('label')} may express a repeatable {time_window} "
        f"source-price relationship in {observed}."
    )
    identity_seed = [family_id, pattern.get("pattern_id"), observed, primary_proxy, time_window]
    invalidation_id = _hash_id("qadam-invalidation-v2", identity_seed)
    risk_concept_id = _hash_id("qadam-risk-concept-v2", identity_seed)
    source_packet_id = _hash_id(
        "qadam-source-packet-v2",
        [family_id, pattern.get("source_record_ids"), strategy_record.get("source_contribution", {}).get("strongest_sources")],
    )
    return {
        "candidate_identity_id": _hash_id("qadam-strategy-identity-v2", identity_seed),
        "identity_type": "strategy_hypothesis_identity_material_not_trade_candidate",
        "research_goal_id": research_goal_lineage.get("research_goal_id"),
        "strategy_family_id": family_id,
        "source_pattern_id": pattern.get("pattern_id"),
        "observed_instrument": observed,
        "paperable_proxy_expression": primary_proxy,
        "time_window": time_window,
        "thesis": thesis,
        "source_packet_id": source_packet_id,
        "source_recipe_fingerprint": _hash_id("qadam-source-recipe-v2", [family_id, pattern.get("source_or_family"), observed]),
        "invalidation_id": invalidation_id,
        "risk_concept_id": risk_concept_id,
        "not_idempotency_key_for_orders": True,
        "idempotency_key_created": False,
        "not_trade_candidate": True,
    }


def _instrument_proxy_mapping(strategy_record: dict[str, Any], pattern: dict[str, Any], primary_proxy: str | None) -> dict[str, Any]:
    paperability = _safe_dict(strategy_record.get("paperability_limits"))
    observed = str(pattern.get("market_or_symbol") or "")
    paperable = [str(item) for item in _safe_list(paperability.get("paperable_proxy_symbols")) if item]
    context_only = [str(item) for item in _safe_list(paperability.get("context_or_research_only_symbols")) if item]
    return {
        "observed_market_expression": observed,
        "observed_market_is_directly_paperable": observed in paperable,
        "primary_proxy": primary_proxy,
        "paperable_proxy_symbols": paperable,
        "context_or_research_only_symbols": context_only,
        "proxy_review_required": observed not in paperable,
        "proxy_review_only_no_order_authority": True,
        "paper_route_required_later": True,
        "paper_order_allowed": False,
        "mapping_limitations": _safe_list(paperability.get("limits")),
    }


def _invalidation_fields(strategy_record: dict[str, Any], pattern: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "invalidation_id": identity.get("invalidation_id"),
        "summary": (
            "Invalidate if the source-price relationship disappears, source evidence reverses, "
            "fresh price context is missing, Akber practical confirmation fails, or later risk/route gates block."
        ),
        "hard_invalidators": [
            "source_quorum_missing",
            "source_direction_reversal",
            "opposite_market_confirmation",
            "missing_price_or_volatility_context",
            "akber_filter_hold_or_veto",
            "shadow_replay_failure",
            "duplicate_exposure_conflict",
            "paper_route_unavailable",
        ],
        "pattern_specific_invalidators": [
            f"pattern_lifecycle_state_not_ranked:{pattern.get('lifecycle_state')}",
            f"quantum_classical_verdict:{pattern.get('quantum_classical_review', {}).get('review_verdict')}",
            f"stale_data_sensitivity:{strategy_record.get('stale_data_sensitivity', {}).get('sensitivity')}",
        ],
        "invalidation_created_no_order": True,
    }


def _risk_concept_fields(strategy_record: dict[str, Any], pattern: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    linear = _safe_dict(pattern.get("linear_tests"))
    failures = _safe_list(strategy_record.get("failure_modes"))
    return {
        "risk_concept_id": identity.get("risk_concept_id"),
        "risk_shape": "source_price_lag_false_positive_and_proxy_basis_risk",
        "expected_holding_window": pattern.get("time_window"),
        "risk_budget_required_later": True,
        "risk_approval_created": False,
        "max_loss_concept": "requires_later_risk_budget_no_sizing_here",
        "drawdown_proxy": linear.get("drawdown_proxy"),
        "expectancy": linear.get("expectancy"),
        "primary_risks": [
            "false_positive_source_price_relationship",
            "market_already_repriced",
            "proxy_basis_risk",
            "missing_volume_or_flow_confirmation",
            "technical_confirmation_gap",
            "duplicate_exposure_conflict",
        ],
        "failure_modes_inherited": [
            failure.get("failure_mode") for failure in failures if failure.get("failure_mode")
        ],
        "stop_concept": "invalidate_on_source_reversal_or_failed_later_confirmation",
    }


def _blocker_state(strategy_record: dict[str, Any], pattern: dict[str, Any]) -> dict[str, Any]:
    blockers = [
        "akber_filter_not_run",
        "shadow_replay_not_run",
        "strategy_router_not_run",
        "risk_budget_not_approved",
        "paperops_handoff_not_allowed_in_phase_6",
    ]
    akber_state = strategy_record.get("akber_sensitivity", {}).get("state")
    if akber_state != "akber_inputs_available_for_research_review":
        blockers.append("akber_practical_confirmation_missing")
    if strategy_record.get("stale_data_sensitivity", {}).get("sensitivity") in {"medium", "high"}:
        blockers.append("stale_or_missing_data_sensitivity")
    if pattern.get("quantum_classical_review", {}).get("review_verdict") == "downgrade_overfit":
        blockers.append("quantum_classical_review_downgraded_pattern")
    return {
        "phase6_state": "accepted_for_phase_7_akber_input_builder",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "weak_hypothesis": False,
        "rejected_before_akber": False,
        "next_allowed_action": "Phase 7 may build Akber inputs from this research hypothesis.",
        "paper_review_candidate": False,
        "paperops_handoff_allowed": False,
    }


def _evidence_summary(strategy_record: dict[str, Any], pattern: dict[str, Any]) -> dict[str, Any]:
    linear = _safe_dict(pattern.get("linear_tests"))
    return {
        "strategy_evidence_map_id": strategy_record.get("strategy_evidence_map_id"),
        "strategy_evidence_state": strategy_record.get("evidence_state"),
        "confidence_class": strategy_record.get("confidence_class"),
        "pattern_id": pattern.get("pattern_id"),
        "pattern_rank": pattern.get("rank"),
        "pattern_lifecycle_state": pattern.get("lifecycle_state"),
        "pattern_rank_score": pattern.get("rank_score"),
        "sample_count": linear.get("sample_count"),
        "hit_rate": linear.get("hit_rate"),
        "expectancy": linear.get("expectancy"),
        "drawdown_proxy": linear.get("drawdown_proxy"),
        "source_contribution_score": strategy_record.get("source_contribution", {}).get("average_contribution_score"),
        "instrument_contribution_score": strategy_record.get("instrument_contribution", {}).get("average_contribution_score"),
        "akber_state": strategy_record.get("akber_sensitivity", {}).get("state"),
        "quantum_classical_verdict": pattern.get("quantum_classical_review", {}).get("review_verdict"),
        "nonlinear_state": pattern.get("nonlinear_interaction_review", {}).get("review_state"),
    }


def _hypothesis_from_strategy_pattern(strategy_record: dict[str, Any], pattern: dict[str, Any], generated_at: str) -> dict[str, Any]:
    primary_proxy = _primary_proxy(strategy_record, pattern)
    research_goal_lineage = _research_goal_lineage(strategy_record, pattern)
    identity = _candidate_identity_material(strategy_record, pattern, research_goal_lineage, primary_proxy)
    hypothesis_id = _hash_id(
        "qadam-strategy-hypothesis-v2",
        [
            strategy_record.get("strategy_family_id"),
            pattern.get("pattern_id"),
            identity.get("candidate_identity_id"),
        ],
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "strategy_hypothesis_id": hypothesis_id,
        "status": "research_strategy_hypothesis_ready_for_akber_input_builder",
        "hypothesis_type": "evidence_backed_existing_family_hypothesis",
        "name": f"{strategy_record.get('label')} Hypothesis ({pattern.get('time_window')})",
        "strategy_family_id": strategy_record.get("strategy_family_id"),
        "strategy_label": strategy_record.get("label"),
        "probationary_strategy_hypothesis": True,
        "strategy_approved": False,
        "strategy_family_active": False,
        "research_goal_lineage": research_goal_lineage,
        "candidate_identity_material": identity,
        "instrument_proxy_mapping": _instrument_proxy_mapping(strategy_record, pattern, primary_proxy),
        "invalidation_fields": _invalidation_fields(strategy_record, pattern, identity),
        "risk_concept_fields": _risk_concept_fields(strategy_record, pattern, identity),
        "blocker_state": _blocker_state(strategy_record, pattern),
        "evidence_summary": _evidence_summary(strategy_record, pattern),
        "strategy_logic": {
            "entry_logic_summary": "Later phases may evaluate whether source evidence confirms before market repricing.",
            "exit_logic_summary": "Later phases must define exit through risk and lifecycle review; no exit order is created here.",
            "no_trade_conditions": [
                "Akber filter not passed",
                "shadow replay not passed",
                "router not paper-review candidate",
                "risk budget not approved",
                "duplicate exposure conflict",
                "guarded paper route unavailable",
            ],
            "required_later_gates": [
                "Phase 7 Akber Filter V2",
                "Phase 8 Shadow Simulator V2",
                "Phase 9 Strategy Router V2",
                "PaperOps guarded Alpaca Paper route",
            ],
        },
        "akber_filter_run": False,
        "akber_filter_passed": False,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paperops_direct_handoff_allowed": False,
        "paper_order_allowed": False,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _reject_strategy(strategy_record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    reasons = []
    if strategy_record.get("evidence_state") != "evidence_backed_research_map":
        reasons.append("strategy_family_under_evidenced")
    confidence = _safe_dict(strategy_record.get("confidence_class"))
    if confidence.get("label") == "under_evidenced":
        reasons.append("confidence_class_under_evidenced")
    if not strategy_record.get("supporting_pattern_count"):
        reasons.append("no_direct_supporting_pattern")
    reasons.extend(
        [
            failure.get("failure_mode")
            for failure in _safe_list(strategy_record.get("failure_modes"))
            if failure.get("severity") == "high" and failure.get("failure_mode")
        ]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "rejected_hypothesis_id": _hash_id(
            "qadam-strategy-hypothesis-v2-reject",
            [strategy_record.get("strategy_family_id"), "strategy_rejected_before_akber"],
        ),
        "decision_type": "strategy_family_rejected_before_akber",
        "strategy_family_id": strategy_record.get("strategy_family_id"),
        "strategy_label": strategy_record.get("label"),
        "source_strategy_evidence_map_id": strategy_record.get("strategy_evidence_map_id"),
        "rejection_reasons": sorted(set(reasons)),
        "evidence_state": strategy_record.get("evidence_state"),
        "confidence_class": confidence.get("label"),
        "rejected_before_akber": True,
        "akber_filter_run": False,
        "akber_filter_passed": False,
        "retest_allowed": True,
        "retest_condition": "More complete source-price history or explicit exploratory authorization is required.",
        "trade_candidate_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _reject_pattern(strategy_record: dict[str, Any], pattern: dict[str, Any], generated_at: str) -> dict[str, Any]:
    linear = _safe_dict(pattern.get("linear_tests"))
    reasons = []
    if pattern.get("lifecycle_state") != "ranked_research_pattern":
        reasons.append(f"pattern_lifecycle_not_ranked:{pattern.get('lifecycle_state')}")
    if pattern.get("quantum_classical_review", {}).get("review_verdict") == "downgrade_overfit":
        reasons.append("quantum_classical_review_downgraded_overfit")
    if _safe_int(linear.get("sample_count")) < 10:
        reasons.append("sample_count_below_hypothesis_threshold")
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "rejected_hypothesis_id": _hash_id(
            "qadam-strategy-hypothesis-v2-reject",
            [strategy_record.get("strategy_family_id"), pattern.get("pattern_id"), "weak_pattern"],
        ),
        "decision_type": "weak_pattern_rejected_before_akber",
        "strategy_family_id": strategy_record.get("strategy_family_id"),
        "strategy_label": strategy_record.get("label"),
        "source_strategy_evidence_map_id": strategy_record.get("strategy_evidence_map_id"),
        "source_pattern_id": pattern.get("pattern_id"),
        "pattern_lifecycle_state": pattern.get("lifecycle_state"),
        "rejection_reasons": sorted(set(reasons or ["weak_pattern_not_promoted"])),
        "rejected_before_akber": True,
        "akber_filter_run": False,
        "akber_filter_passed": False,
        "retest_allowed": True,
        "retest_condition": "Retest after more samples, lower overfit risk, and practical confirmation evidence.",
        "trade_candidate_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _accepted_pattern(pattern: dict[str, Any]) -> bool:
    linear = _safe_dict(pattern.get("linear_tests"))
    if pattern.get("lifecycle_state") != "ranked_research_pattern":
        return False
    if _safe_int(linear.get("sample_count")) < 10:
        return False
    if pattern.get("quantum_classical_review", {}).get("review_verdict") == "downgrade_overfit":
        return False
    return True


def _strategy_eligible(strategy_record: dict[str, Any]) -> bool:
    confidence = _safe_dict(strategy_record.get("confidence_class"))
    if strategy_record.get("evidence_state") != "evidence_backed_research_map":
        return False
    if _safe_float(confidence.get("confidence_score")) < MIN_CONFIDENCE_SCORE_FOR_HYPOTHESIS:
        return False
    if not strategy_record.get("supporting_pattern_count"):
        return False
    return True


def _dashboard_summary(primary: dict[str, Any], hypotheses: list[dict[str, Any]], rejections: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    rejection_counts = Counter(str(record.get("decision_type") or "unknown") for record in rejections)
    family_counts = Counter(str(record.get("strategy_family_id") or "unknown") for record in hypotheses)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_foundry_v2_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "strategy_hypothesis_count": len(hypotheses),
        "accepted_for_akber_input_builder_count": len(hypotheses),
        "rejected_before_akber_count": len(rejections),
        "weak_pattern_rejection_count": rejection_counts.get("weak_pattern_rejected_before_akber", 0),
        "strategy_family_rejection_count": rejection_counts.get("strategy_family_rejected_before_akber", 0),
        "hypothesis_family_counts": dict(family_counts),
        "cards": [
            {
                "strategy_hypothesis_id": hypothesis.get("strategy_hypothesis_id"),
                "strategy_family_id": hypothesis.get("strategy_family_id"),
                "strategy_label": hypothesis.get("strategy_label"),
                "status": hypothesis.get("status"),
                "observed_market_expression": hypothesis.get("instrument_proxy_mapping", {}).get("observed_market_expression"),
                "primary_proxy": hypothesis.get("instrument_proxy_mapping", {}).get("primary_proxy"),
                "blocker_count": hypothesis.get("blocker_state", {}).get("blocker_count"),
                "blockers": hypothesis.get("blocker_state", {}).get("blockers"),
                "akber_filter_run": hypothesis.get("akber_filter_run"),
                "trade_candidate_created": hypothesis.get("trade_candidate_created"),
            }
            for hypothesis in hypotheses[:8]
        ],
        "message": (
            "Strategy Foundry V2 creates research-only strategy hypotheses from evidence-backed patterns "
            "and rejects weak hypotheses before Akber. It does not create trade candidates or orders."
        ),
        "next_allowed_action": "Phase 7 may build Akber inputs for accepted research hypotheses.",
        "akber_filter_run": False,
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "primary": PRIMARY_ARTIFACT,
            "hypotheses": HYPOTHESES_ARTIFACT,
            "rejections": REJECTIONS_ARTIFACT,
        },
    }


def build_strategy_foundry_v2(settings: Settings | None = None) -> StrategyFoundryBundle:
    generated_at = _iso()
    context = _load_context(settings)
    pattern_by_id = _patterns_by_id(context["pattern_records"])
    hypotheses: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []

    for strategy_record in context["strategy_records"]:
        pattern_ids = [str(item) for item in _safe_list(strategy_record.get("supporting_pattern_ids")) if item]
        patterns = [pattern_by_id[pattern_id] for pattern_id in pattern_ids if pattern_id in pattern_by_id]
        if not _strategy_eligible(strategy_record):
            rejections.append(_reject_strategy(strategy_record, generated_at))
            continue
        accepted_count = 0
        for pattern in patterns:
            if _accepted_pattern(pattern) and accepted_count < MAX_HYPOTHESES_PER_STRATEGY:
                hypotheses.append(_hypothesis_from_strategy_pattern(strategy_record, pattern, generated_at))
                accepted_count += 1
            else:
                rejections.append(_reject_pattern(strategy_record, pattern, generated_at))

    status = "strategy_foundry_v2_ready" if hypotheses or rejections else "strategy_foundry_v2_blocked_no_evidence_map"
    rejection_counts = Counter(str(record.get("decision_type") or "unknown") for record in rejections)
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_foundry_v2",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "input_artifacts": {
            "strategy_evidence_map": STRATEGY_EVIDENCE_MAP_ARTIFACT,
            "strategy_evidence_records": STRATEGY_EVIDENCE_RECORDS_ARTIFACT,
            "pattern_engine_v2_records": PATTERN_ENGINE_V2_RECORDS_ARTIFACT,
        },
        "source_strategy_count": len(context["strategy_records"]),
        "strategy_hypothesis_count": len(hypotheses),
        "accepted_for_akber_input_builder_count": len(hypotheses),
        "rejected_before_akber_count": len(rejections),
        "weak_pattern_rejection_count": rejection_counts.get("weak_pattern_rejected_before_akber", 0),
        "strategy_family_rejection_count": rejection_counts.get("strategy_family_rejected_before_akber", 0),
        "weak_hypotheses_rejected_before_akber": True,
        "research_strategy_hypothesis_generation_allowed": True,
        "akber_filter_run": False,
        "akber_filter_passed": False,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paperops_direct_handoff_allowed": False,
        "paper_order_allowed": False,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "hypotheses": HYPOTHESES_ARTIFACT,
            "rejections": REJECTIONS_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
    }
    return StrategyFoundryBundle(
        primary=primary,
        hypotheses=hypotheses,
        rejections=rejections,
        dashboard_summary=_dashboard_summary(primary, hypotheses, rejections, generated_at),
    )


def write_strategy_foundry_v2(bundle: StrategyFoundryBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "hypotheses": runtime / HYPOTHESES_ARTIFACT,
        "rejections": runtime / REJECTIONS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["hypotheses"], bundle.hypotheses)
    _write_jsonl(paths["rejections"], bundle.rejections)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "event_type": "strategy_foundry_v2_written",
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "strategy_hypothesis_count": len(bundle.hypotheses),
            "rejected_before_akber_count": len(bundle.rejections),
            "akber_filter_run": False,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
            "authority": _authority(),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_strategy_foundry_v2(settings: Settings | None = None) -> tuple[StrategyFoundryBundle, dict[str, str]]:
    bundle = build_strategy_foundry_v2(settings)
    written = write_strategy_foundry_v2(bundle, settings)
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


def validate_strategy_hypothesis(hypothesis: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if hypothesis.get("schema_version") != SCHEMA_VERSION:
        errors.append("hypothesis_schema_version_invalid")
    if hypothesis.get("phase_id") != PHASE_ID:
        errors.append("hypothesis_phase_id_invalid")
    if not hypothesis.get("strategy_hypothesis_id"):
        errors.append("hypothesis_id_missing")
    if hypothesis.get("status") != "research_strategy_hypothesis_ready_for_akber_input_builder":
        errors.append("hypothesis_status_invalid")
    for section in REQUIRED_HYPOTHESIS_SECTIONS:
        if not isinstance(hypothesis.get(section), dict):
            errors.append(f"hypothesis_{section}_missing")
    identity = _safe_dict(hypothesis.get("candidate_identity_material"))
    if identity.get("not_trade_candidate") is not True:
        errors.append("hypothesis_identity_not_trade_candidate_missing")
    if identity.get("not_idempotency_key_for_orders") is not True:
        errors.append("hypothesis_identity_not_idempotency_key_missing")
    if identity.get("idempotency_key_created") is not False:
        errors.append("hypothesis_idempotency_key_created_must_be_false")
    blocker_state = _safe_dict(hypothesis.get("blocker_state"))
    if blocker_state.get("rejected_before_akber") is not False:
        errors.append("accepted_hypothesis_rejected_before_akber_invalid")
    if blocker_state.get("paperops_handoff_allowed") is not False:
        errors.append("accepted_hypothesis_paperops_handoff_allowed_must_be_false")
    if hypothesis.get("akber_filter_run") is not False:
        errors.append("hypothesis_akber_filter_run_must_be_false")
    errors.extend(_validate_authority(hypothesis, "hypothesis"))
    return errors


def validate_rejection(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("rejection_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append("rejection_phase_id_invalid")
    if not record.get("rejected_hypothesis_id"):
        errors.append("rejection_id_missing")
    if record.get("decision_type") not in {
        "strategy_family_rejected_before_akber",
        "weak_pattern_rejected_before_akber",
    }:
        errors.append("rejection_decision_type_invalid")
    if record.get("rejected_before_akber") is not True:
        errors.append("rejection_before_akber_must_be_true")
    if record.get("akber_filter_run") is not False:
        errors.append("rejection_akber_filter_run_must_be_false")
    if not record.get("rejection_reasons"):
        errors.append("rejection_reasons_missing")
    errors.extend(_validate_authority(record, "rejection"))
    return errors


def validate_strategy_foundry_v2_bundle(bundle: StrategyFoundryBundle | dict[str, Any]) -> list[str]:
    if isinstance(bundle, StrategyFoundryBundle):
        primary = bundle.primary
        hypotheses = bundle.hypotheses
        rejections = bundle.rejections
        dashboard_summary = bundle.dashboard_summary
    else:
        primary = _safe_dict(bundle.get("primary"))
        hypotheses = _safe_list(bundle.get("hypotheses"))
        rejections = _safe_list(bundle.get("rejections"))
        dashboard_summary = _safe_dict(bundle.get("dashboard_summary"))
    errors: list[str] = []
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("primary_schema_version_invalid")
    if primary.get("phase_id") != PHASE_ID:
        errors.append("primary_phase_id_invalid")
    if primary.get("artifact_type") != "qadam_strategy_foundry_v2":
        errors.append("primary_artifact_type_invalid")
    if primary.get("status") != "strategy_foundry_v2_ready":
        errors.append("primary_status_not_ready")
    for key in ("public_safe", "read_only", "paper_only", "proposal_first", "research_only"):
        if primary.get(key) is not True:
            errors.append(f"primary_{key}_must_be_true")
    if not hypotheses:
        errors.append("hypotheses_missing")
    if not rejections:
        errors.append("rejections_missing")
    if primary.get("strategy_hypothesis_count") != len(hypotheses):
        errors.append("primary_hypothesis_count_mismatch")
    if primary.get("rejected_before_akber_count") != len(rejections):
        errors.append("primary_rejection_count_mismatch")
    if primary.get("weak_hypotheses_rejected_before_akber") is not True:
        errors.append("weak_hypotheses_rejected_before_akber_not_true")
    errors.extend(_validate_authority(primary, "primary"))
    ids = [hypothesis.get("strategy_hypothesis_id") for hypothesis in hypotheses]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_strategy_hypothesis_ids")
    for index, hypothesis in enumerate(hypotheses, start=1):
        for error in validate_strategy_hypothesis(hypothesis):
            errors.append(f"hypothesis_{index}_{error}")
    for index, rejection in enumerate(rejections, start=1):
        for error in validate_rejection(rejection):
            errors.append(f"rejection_{index}_{error}")
    if dashboard_summary.get("artifact_type") != "qadam_strategy_foundry_v2_dashboard_summary":
        errors.append("dashboard_summary_artifact_type_invalid")
    if dashboard_summary.get("strategy_hypothesis_count") != len(hypotheses):
        errors.append("dashboard_summary_hypothesis_count_mismatch")
    if dashboard_summary.get("rejected_before_akber_count") != len(rejections):
        errors.append("dashboard_summary_rejection_count_mismatch")
    if dashboard_summary.get("trade_candidate_creation_allowed") is not False:
        errors.append("dashboard_summary_trade_candidate_creation_allowed_must_be_false")
    if dashboard_summary.get("paper_order_allowed") is not False:
        errors.append("dashboard_summary_paper_order_allowed_must_be_false")
    return errors


def validate_negative_strategy_foundry_v2_probes(settings: Settings | None = None) -> list[str]:
    bundle = build_strategy_foundry_v2(settings)
    if not bundle.hypotheses:
        return ["negative_probe_skipped_missing_hypotheses"]
    errors: list[str] = []
    unsafe_hypothesis = json.loads(json.dumps(bundle.hypotheses[0]))
    unsafe_hypothesis["trade_candidate_created"] = True
    unsafe_hypothesis["authority"]["trade_candidate_created"] = True
    if not validate_strategy_hypothesis(unsafe_hypothesis):
        errors.append("negative_probe_failed_for_trade_candidate_boundary")

    unsafe_order = json.loads(json.dumps(bundle.hypotheses[0]))
    unsafe_order["paper_order_created"] = True
    unsafe_order["authority"]["paper_order_created"] = True
    if not validate_strategy_hypothesis(unsafe_order):
        errors.append("negative_probe_failed_for_paper_order_boundary")

    missing_section = json.loads(json.dumps(bundle.hypotheses[0]))
    missing_section.pop("risk_concept_fields", None)
    if not validate_strategy_hypothesis(missing_section):
        errors.append("negative_probe_failed_for_missing_required_section")

    unsafe_rejection = json.loads(json.dumps(bundle.rejections[0]))
    unsafe_rejection["akber_filter_run"] = True
    unsafe_rejection["authority"]["akber_filter_run"] = True
    if not validate_rejection(unsafe_rejection):
        errors.append("negative_probe_failed_for_rejection_before_akber_boundary")
    return errors


def load_strategy_foundry_v2(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "primary": _read_json(runtime / PRIMARY_ARTIFACT),
        "hypotheses": _read_jsonl(runtime / HYPOTHESES_ARTIFACT),
        "rejections": _read_jsonl(runtime / REJECTIONS_ARTIFACT),
        "dashboard_summary": _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    }
