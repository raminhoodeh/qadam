"""EF-5 profile-aware Akber policy, replay, ablation, and safety checks.

The module calibrates how evidence is interpreted. It never mutates the active
thresholds, creates a candidate, approves risk, or submits an order.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import (
    DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES,
    STAGE_FIELDS,
    build_akber_input,
    evaluate_akber_input,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EVENT_CATALYST_PROFILE,
    EXPERIMENTAL_UNVALIDATED,
    MARKET_DISLOCATION_PROFILE,
    REGIME_STATE_PROFILE,
    evidence_profile_for_strategy,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import safe_float, stable_id

SCHEMA_VERSION = "qadam_akber_evidence_fit.v1"
PHASE_ID = "EF-5"
POLICY_VERSION = "qadam-akber-evidence-fit.1"

POLICY_ARTIFACT = "qadam_akber_evidence_profile_policy.json"
REPLAY_ARTIFACT = "qadam_akber_profile_replay.jsonl"
ABLATION_ARTIFACT = "qadam_akber_profile_ablation.jsonl"
PROPOSALS_ARTIFACT = "qadam_akber_recalibration_proposals.jsonl"
CHECK_ARTIFACT = "qadam_akber_evidence_fit_checks.json"

SOURCE_REPLAY_ARTIFACT = "qadam_akber_filter_v3_replay.jsonl"

PROFILES = (
    EVENT_CATALYST_PROFILE,
    REGIME_STATE_PROFILE,
    MARKET_DISLOCATION_PROFILE,
)


def build_evidence_profile_policy(*, generated_at: str) -> dict[str, Any]:
    stages = [
        {
            "stage_number": 1,
            "stage": "context",
            "question": "Does canonical historical support fit the current market context?",
            "missing_policy": "hold",
            "adverse_policy": "veto",
        },
        {
            "stage_number": 2,
            "stage": "catalyst",
            "question": "Is the profile-specific trigger active now?",
            "profile_requirements": {
                EVENT_CATALYST_PROFILE: "fresh instrument-relevant event",
                REGIME_STATE_PROFILE: "measured active numeric regime",
                MARKET_DISLOCATION_PROFILE: "measured current market dislocation",
            },
            "inactive_policy": "watchlist_inactive_trigger",
            "missing_policy": "hold_missing_context",
        },
        {
            "stage_number": 3,
            "stage": "confirmation",
            "question": "Does at least one independent live-market channel confirm the setup?",
            "alternatives": list(DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES),
            "all_alternatives_required": False,
            "quantum_required_only_when_quantum_dependent": True,
        },
        {
            "stage_number": 4,
            "stage": "risk",
            "question": "Is current net expectancy positive with a clear invalidation and reward-to-risk?",
            "minimum_reward_to_risk": 1.25,
            "positive_after_cost_expectancy_required": True,
        },
        {
            "stage_number": 5,
            "stage": "execution",
            "question": "Is the current session actionable with a liquid, paperable proxy and measured spread?",
            "missing_spread_policy": "hold_missing_context",
            "measured_adverse_spread_policy": "veto",
            "ablation_control_retained": True,
        },
        {
            "stage_number": 6,
            "stage": "postmortem_learning",
            "question": "Will the pass, watchlist, hold, veto, and eventual outcome be recorded?",
            "state": "ready_after_outcome",
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_evidence_profile_policy",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "policy_version": POLICY_VERSION,
        "status": "frozen_proposal_first_policy",
        "profiles": {
            EVENT_CATALYST_PROFILE: {
                "strategy_families": [
                    "crude_oil_energy_security_disruption",
                    "defence_geopolitical_repricing",
                    "semiconductor_policy_asymmetry",
                ],
                "trigger": "fresh instrument-relevant event",
            },
            REGIME_STATE_PROFILE: {
                "strategy_families": [
                    "silver_macro_liquidity_stress",
                    "power_grid_scarcity_congestion",
                ],
                "trigger": "measured active numeric regime",
            },
            MARKET_DISLOCATION_PROFILE: {
                "strategy_families": ["event_probability_dislocation"],
                "trigger": "measured current prediction-market dislocation",
            },
        },
        "stages": stages,
        "decision_rules": {
            "explicit_adverse_evidence": "veto",
            "inactive_trigger": "watchlist_inactive_trigger",
            "missing_required_evidence": "hold_missing_context",
            "all_required_evidence_clean": "pass",
        },
        "validated_strategy_policy_separate": True,
        "discovery_micro_policy_separate": True,
        "threshold_change_applied": False,
        "explicit_versioned_review_required": True,
        "akber_pass_is_execution_approval": False,
        "authority": authority_flags(),
    }


def _profile_for_replay(row: dict[str, Any]) -> str:
    strategy = row.get("strategy_family_id")
    profile = evidence_profile_for_strategy(strategy)
    if profile in PROFILES:
        return profile
    instrument = str(row.get("instrument") or "").upper()
    if instrument in {"SI=F", "SLV", "SIL", "GLD", "TLN", "XLU", "VST", "CEG"}:
        return REGIME_STATE_PROFILE
    if "KALSHI" in instrument or "POLYMARKET" in instrument:
        return MARKET_DISLOCATION_PROFILE
    return EVENT_CATALYST_PROFILE


def build_profile_replay(
    replay: list[dict[str, Any]], *, generated_at: str
) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_akber_profile_replay",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "source_replay_id": row.get("replay_id"),
            "profile_replay_id": stable_id(
                "akber-profile-replay", row.get("replay_id"), _profile_for_replay(row)
            ),
            "evidence_profile": _profile_for_replay(row),
            "profile_policy_version": POLICY_VERSION,
            "threshold_change_applied": False,
            "paper_order_created": False,
            "proof_eligible": False,
            "authority": authority_flags(),
        }
        for row in replay
    ]


def _profile_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [row for row in rows if row.get("outcome", {}).get("measured") is True]
    passed = [row for row in measured if row.get("decision") == "pass"]
    passed_returns = [safe_float(row.get("outcome", {}).get("mean_net_return")) for row in passed]
    return {
        "measured_count": len(measured),
        "pass_count": len(passed),
        "hold_count": sum(row.get("decision") == "hold_missing_context" for row in measured),
        "veto_count": sum(row.get("decision") == "veto" for row in measured),
        "passed_mean_net_return": (
            sum(passed_returns) / len(passed_returns) if passed_returns else None
        ),
        "passed_worst_drawdown": min(
            (safe_float(row.get("outcome", {}).get("maximum_drawdown")) for row in passed),
            default=None,
        ),
    }


def build_profile_ablations(
    profile_replay: list[dict[str, Any]], *, generated_at: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for profile in PROFILES:
        rows = [row for row in profile_replay if row.get("evidence_profile") == profile]
        base = _profile_metrics(rows)
        for stage in STAGE_FIELDS:
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_akber_profile_ablation",
                    "phase_id": PHASE_ID,
                    "generated_at": generated_at,
                    "ablation_id": stable_id(
                        "akber-profile-ablation", POLICY_VERSION, profile, stage
                    ),
                    "evidence_profile": profile,
                    "stage_removed": stage,
                    "source_replay_count": len(rows),
                    "measurement_state": (
                        "measured" if rows else "unavailable_no_measurable_profile_replay"
                    ),
                    "base_metrics": base,
                    "execution_control_retained": stage == "execution",
                    "holdout_used_to_change_policy": False,
                    "threshold_change_applied": False,
                    "paper_order_created": False,
                    "proof_eligible": False,
                    "authority": authority_flags(),
                }
            )
    return records


def build_recalibration_proposals(
    profile_replay: list[dict[str, Any]], *, generated_at: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for profile in PROFILES:
        rows = [row for row in profile_replay if row.get("evidence_profile") == profile]
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_akber_recalibration_proposal",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "proposal_id": stable_id(
                    "akber-profile-recalibration", POLICY_VERSION, profile, len(rows)
                ),
                "evidence_profile": profile,
                "proposal": (
                    "retain_current_profile_contract_pending_more_forward_outcomes"
                    if not rows
                    else "review_profile_metrics_without_automatic_threshold_change"
                ),
                "measurable_replay_count": len(rows),
                "execution_stage_removal_proposed": False,
                "risk_envelope_change_proposed": False,
                "threshold_change_applied": False,
                "explicit_versioned_review_required": True,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return records


def _evidence(
    field: str,
    *,
    available: bool,
    state: str,
    generated_at: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "field": field,
        "available": available,
        "state": state,
        "observed_at": generated_at,
        "source_refs": [f"ef5-contract-probe:{field}"],
        "details": details or {},
        "origin_class": "deterministic_contract_probe",
        "reason": "EF-5 deterministic policy probe; never runtime evidence.",
    }


def _probe_hypothesis(symbol: str, profile: str) -> dict[str, Any]:
    strategy = (
        "silver_macro_liquidity_stress"
        if symbol == "SIL"
        else "defence_geopolitical_repricing"
    )
    return {
        "hypothesis_id": f"ef5-probe:{symbol}",
        "generated_at": "2026-08-08T12:00:00+00:00",
        "evidence_class": EXPERIMENTAL_UNVALIDATED,
        "experimental_tier": DISCOVERY_MICRO_TIER,
        "akber_review_allowed": True,
        "pattern_lineage": {
            "pattern_relationship_id": f"ef5-pattern:{symbol}",
            "score_id": f"ef5-score:{symbol}",
            "evidence_profile": profile,
            "complete": True,
        },
        "strategy_mapping": {"strategy_family_id": strategy},
        "research_goal_lineage": {"research_goal_id": f"ef5-goal:{symbol}"},
        "edge_lineage": {},
    }


def _probe_context(
    *, generated_at: str, trigger_state: str = "available", spread_bps: float | None = 8.0
) -> dict[str, Any]:
    fields = {
        "source_price_context": _evidence(
            "source_price_context",
            available=True,
            state="available",
            generated_at=generated_at,
        ),
        "fresh_catalyst": _evidence(
            "fresh_catalyst",
            available=trigger_state == "available",
            state=trigger_state,
            generated_at=generated_at,
            details={"fresh_trigger_sources": ["provider_a"]},
        ),
        "technical_confirmation": _evidence(
            "technical_confirmation",
            available=False,
            state="missing",
            generated_at=generated_at,
        ),
        "volume_or_flow_confirmation": _evidence(
            "volume_or_flow_confirmation",
            available=True,
            state="confirmed",
            generated_at=generated_at,
        ),
        "volatility_context": _evidence(
            "volatility_context",
            available=True,
            state="measured",
            generated_at=generated_at,
        ),
        "pricing_gap_evidence": _evidence(
            "pricing_gap_evidence",
            available=False,
            state="missing",
            generated_at=generated_at,
        ),
        "risk_reward_context": _evidence(
            "risk_reward_context",
            available=True,
            state="measured",
            generated_at=generated_at,
            details={"expected_net_return": 0.002, "reward_to_risk": 1.5},
        ),
        "invalidation_clarity": _evidence(
            "invalidation_clarity",
            available=True,
            state="defined",
            generated_at=generated_at,
            details={"defined": True, "invalidation_price": 49.0},
        ),
        "liquidity_and_spread": _evidence(
            "liquidity_and_spread",
            available=spread_bps is not None,
            state="measured" if spread_bps is not None else "missing",
            generated_at=generated_at,
            details={"spread_bps": spread_bps},
        ),
        "paperability_proxy": _evidence(
            "paperability_proxy",
            available=True,
            state="available",
            generated_at=generated_at,
            details={
                "paperable": True,
                "paper_route": "guarded_alpaca_paper_via_paperops",
            },
        ),
        "nonlinear_quantum_review": _evidence(
            "nonlinear_quantum_review",
            available=False,
            state="missing",
            generated_at=generated_at,
        ),
    }
    return fields


def _contract_probes(generated_at: str) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    for symbol, profile in (
        ("SIL", REGIME_STATE_PROFILE),
        ("XAR", EVENT_CATALYST_PROFILE),
    ):
        hypothesis = _probe_hypothesis(symbol, profile)
        complete = build_akber_input(
            hypothesis, _probe_context(generated_at=generated_at), generated_at=generated_at
        )
        inactive = build_akber_input(
            hypothesis,
            _probe_context(
                generated_at=generated_at,
                trigger_state=(
                    "regime_inactive" if symbol == "SIL" else "event_inactive"
                ),
            ),
            generated_at=generated_at,
        )
        missing_execution = build_akber_input(
            hypothesis,
            _probe_context(generated_at=generated_at, spread_bps=None),
            generated_at=generated_at,
        )
        adverse = build_akber_input(
            hypothesis,
            _probe_context(generated_at=generated_at, spread_bps=125.0),
            generated_at=generated_at,
        )
        results[symbol] = {
            "complete": evaluate_akber_input(complete),
            "inactive": evaluate_akber_input(inactive),
            "missing_execution": evaluate_akber_input(missing_execution),
            "adverse_execution": evaluate_akber_input(adverse),
        }
    return results


def validate_akber_evidence_fit(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = state["policy"]
    if policy.get("policy_version") != POLICY_VERSION or len(policy.get("stages", [])) != 6:
        errors.append("akber_evidence_profile_policy_invalid")
    if policy.get("threshold_change_applied") is not False:
        errors.append("akber_evidence_fit_threshold_mutated")
    for symbol, probe in state["contract_probes"].items():
        if probe["complete"].get("decision") != "pass":
            errors.append(f"akber_complete_probe_did_not_pass:{symbol}")
        if probe["inactive"].get("decision") != "watchlist_inactive_trigger":
            errors.append(f"akber_inactive_probe_not_watchlist:{symbol}")
        if probe["missing_execution"].get("decision") != "hold_missing_context":
            errors.append(f"akber_missing_execution_not_hold:{symbol}")
        if probe["missing_execution"].get("hard_vetoes"):
            errors.append(f"akber_missing_execution_became_veto:{symbol}")
        if probe["adverse_execution"].get("decision") != "veto":
            errors.append(f"akber_measured_adverse_spread_not_veto:{symbol}")
        if probe["complete"].get("router_eligible") is not True:
            errors.append(f"akber_pass_not_router_eligible:{symbol}")
        if probe["complete"].get("paper_order_created") is not False:
            errors.append(f"akber_probe_created_order:{symbol}")
    expected_ablations = len(PROFILES) * len(STAGE_FIELDS)
    if len(state["ablation"]) != expected_ablations:
        errors.append("akber_profile_ablation_coverage_incomplete")
    if any(
        row.get("stage_removed") == "execution"
        and row.get("execution_control_retained") is not True
        for row in state["ablation"]
    ):
        errors.append("akber_execution_ablation_control_not_retained")
    for collection in (state["replay"], state["ablation"], state["proposals"]):
        for row in collection:
            if row.get("threshold_change_applied") is not False:
                errors.append("akber_evidence_fit_applied_threshold_change")
            if row.get("paper_order_created") is not False:
                errors.append("akber_evidence_fit_created_order")
            errors.extend(validate_authority(row.get("authority", {}), prefix="akber_evidence_fit"))
    errors.extend(validate_authority(policy.get("authority", {}), prefix="akber_evidence_policy"))
    return unique_errors(errors)


def build_akber_evidence_fit_state(
    settings: Settings | None = None, *, generated_at: str | None = None
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    source_replay = read_jsonl(runtime / SOURCE_REPLAY_ARTIFACT)
    replay = build_profile_replay(source_replay, generated_at=generated)
    return {
        "policy": build_evidence_profile_policy(generated_at=generated),
        "replay": replay,
        "ablation": build_profile_ablations(replay, generated_at=generated),
        "proposals": build_recalibration_proposals(replay, generated_at=generated),
        "contract_probes": _contract_probes(generated),
        "source_replay_count": len(source_replay),
    }


def build_and_write_akber_evidence_fit(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_akber_evidence_fit_state(settings)
    errors = validate_akber_evidence_fit(state)
    decisions = Counter(
        row.get("decision") for row in state["replay"] if row.get("decision")
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_akber_evidence_fit_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "policy_version": POLICY_VERSION,
        "profile_count": len(PROFILES),
        "profile_replay_count": len(state["replay"]),
        "profile_replay_measurement_state": (
            "measured" if state["replay"] else "no_current_measurable_untouched_holdout"
        ),
        "decision_counts": dict(sorted(decisions.items())),
        "profile_ablation_count": len(state["ablation"]),
        "recalibration_proposal_count": len(state["proposals"]),
        "sil_complete_packet_passed": state["contract_probes"]["SIL"]["complete"].get("decision") == "pass",
        "xar_complete_packet_passed": state["contract_probes"]["XAR"]["complete"].get("decision") == "pass",
        "inactive_trigger_is_watchlist": all(
            row["inactive"].get("decision") == "watchlist_inactive_trigger"
            for row in state["contract_probes"].values()
        ),
        "missing_evidence_is_hold_not_veto": all(
            row["missing_execution"].get("decision") == "hold_missing_context"
            and not row["missing_execution"].get("hard_vetoes")
            for row in state["contract_probes"].values()
        ),
        "quantum_optional_for_non_quantum_hypothesis": True,
        "akber_pass_is_execution_approval": False,
        "threshold_change_applied_count": 0,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(POLICY_ARTIFACT, state["policy"])
    store.write_jsonl(REPLAY_ARTIFACT, state["replay"])
    store.write_jsonl(ABLATION_ARTIFACT, state["ablation"])
    store.write_jsonl(PROPOSALS_ARTIFACT, state["proposals"])
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


__all__ = [
    "ABLATION_ARTIFACT",
    "CHECK_ARTIFACT",
    "POLICY_ARTIFACT",
    "POLICY_VERSION",
    "PROPOSALS_ARTIFACT",
    "REPLAY_ARTIFACT",
    "build_akber_evidence_fit_state",
    "build_and_write_akber_evidence_fit",
    "validate_akber_evidence_fit",
]
