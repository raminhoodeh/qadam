"""Certify Qadam's autonomous, bounded edge-research progression.

This contract deliberately separates an operational research lane from an
empirically validated edge and from a current paper-order opportunity. The
lane may discover and admit a pattern-sourced paper strategy under frozen
policy, but it cannot expand risk, bypass Akber/Router/PaperOps, or claim proof.
"""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_power_market_edge_engine import research_paths_are_ignored

SCHEMA_VERSION = "qadam_active_edge_research_certification.v1"
CERTIFICATION_ARTIFACT = "qadam_active_edge_research_certification.json"
CHECK_ARTIFACT = "qadam_active_edge_research_checks.json"

INPUTS = {
    "power": "qadam_power_market_edge_engine.json",
    "power_checks": "qadam_power_market_edge_engine_checks.json",
    "manifest": "qadam_power_market_acquisition_manifest.json",
    "backtest": "qadam_power_market_backtest.json",
    "strategy": "qadam_power_market_strategy_registry.json",
    "foundry": "qadam_strategy_foundry_v3_checks.json",
    "akber": "qadam_akber_filter_v3_checks.json",
    "shadow": "qadam_forward_shadow_checks.json",
    "risk": "qadam_portfolio_risk_engine_checks.json",
    "router": "qadam_router_v3_paperops_checks.json",
    "why_not": "qadam_router_v3_why_not_trading_now.json",
    "policy": "qadam_experimental_paper_policy.json",
    "operator": "qadam_operator_service_status.json",
    "circuits": "qadam_operator_circuit_breakers.json",
    "wave_f": "qadam_quantum_edge_wave_f_public_view.json",
}


def _service(operator: dict[str, Any], service_id: str) -> dict[str, Any]:
    for row in operator.get("services", []):
        if isinstance(row, dict) and row.get("service_id") == service_id:
            return row
    return {}


def _wave_f_has_strategy(wave_f: dict[str, Any], strategy_family_id: str) -> bool:
    patterns = wave_f.get("pattern_recognition", {}).get("candidates", [])
    emerging = wave_f.get("trading_strategies", {}).get(
        "emerging_strategy_candidates", []
    )
    return any(
        isinstance(row, dict) and row.get("strategy_family_id") == strategy_family_id
        for row in [*patterns, *emerging]
    )


def _check(
    check_id: str,
    passed: bool,
    observed: Any,
    expected: str,
    blocker: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
        "blocker": None if passed else blocker,
    }


def build_active_edge_research_certification(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    inputs = {key: read_json(runtime / name) for key, name in INPUTS.items()}
    power = inputs["power"]
    power_checks = inputs["power_checks"]
    manifest = inputs["manifest"]
    backtest = inputs["backtest"]
    strategy = inputs["strategy"]
    foundry = inputs["foundry"]
    akber = inputs["akber"]
    shadow = inputs["shadow"]
    risk = inputs["risk"]
    router = inputs["router"]
    why_not = inputs["why_not"]
    policy = inputs["policy"]
    operator = inputs["operator"]
    circuits = inputs["circuits"]
    wave_f = inputs["wave_f"]
    service = _service(operator, "power_market_research")
    strategy_rows = [
        row for row in strategy.get("strategies", []) if isinstance(row, dict)
    ]
    power_strategy = next(
        (
            row
            for row in strategy_rows
            if row.get("strategy_family_id") == "power_scarcity_congestion"
        ),
        {},
    )
    power_circuit = circuits.get("services", {}).get("power_market_research", {})
    wave_f_has_power = _wave_f_has_strategy(wave_f, "power_scarcity_congestion")
    authority_counters = {
        "paper_orders": int(power.get("paper_order_created_count") or 0),
        "broker_writes": int(power.get("broker_write_count") or 0),
        "proof_credits": int(power.get("proof_credit_count") or 0),
    }
    score_count = int(power.get("current_pattern_score_count") or 0)
    shadow_decision_count = int(shadow.get("decision_count") or 0)
    shadow_eligible_count = int(shadow.get("eligible_hypothesis_count") or 0)
    checks = [
        _check(
            "providers.live_and_real",
            power_checks.get("provider_backed_live_refresh") is True
            and power.get("provider_state", {}).get("caiso_oasis") == "provider_backed_live"
            and power.get("provider_state", {}).get("alpaca_iex") == "provider_backed_live",
            power.get("provider_state"),
            "CAISO OASIS and Alpaca IEX both provider_backed_live",
            "The mechanism research lane lacks a fresh real-provider input.",
        ),
        _check(
            "acquisition.resumable_and_idempotent",
            manifest.get("resumable") is True and manifest.get("idempotent") is True,
            {
                "resumable": manifest.get("resumable"),
                "idempotent": manifest.get("idempotent"),
                "complete": manifest.get("complete_job_count"),
                "remaining": manifest.get("remaining_job_count"),
            },
            "resumable=true and idempotent=true",
            "The historical acquisition cannot safely survive interruption.",
        ),
        _check(
            "research.point_in_time_and_cost_adjusted",
            backtest.get("point_in_time_safe") is True
            and backtest.get("cost_adjusted") is True,
            {
                "point_in_time_safe": backtest.get("point_in_time_safe"),
                "cost_adjusted": backtest.get("cost_adjusted"),
                "status": backtest.get("status"),
            },
            "point-in-time safe and cost adjusted",
            "The backtest contract can leak future data or omit trading costs.",
        ),
        _check(
            "strategy.automatic_bounded_admission",
            strategy.get("automatic_strategy_admission_enabled") is True
            and strategy.get("automatic_risk_envelope_expansion_enabled") is False
            and bool(power_strategy),
            {
                "automatic_strategy_admission_enabled": strategy.get(
                    "automatic_strategy_admission_enabled"
                ),
                "automatic_risk_envelope_expansion_enabled": strategy.get(
                    "automatic_risk_envelope_expansion_enabled"
                ),
                "admission_state": power_strategy.get("admission_state"),
            },
            "automatic bounded admission enabled with no automatic risk expansion",
            "The pattern-sourced strategy cannot progress safely under frozen policy.",
        ),
        _check(
            "downstream.foundry_and_akber",
            foundry.get("status") == "passed" and akber.get("status") == "passed",
            {"foundry": foundry.get("status"), "akber": akber.get("status")},
            "both checks passed",
            "The emerging strategy cannot progress through Foundry and Akber contracts.",
        ),
        _check(
            "downstream.shadow_learning",
            shadow.get("implementation_ready") is True
            and int(shadow.get("validation_error_count") or 0) == 0
            and (
                score_count == 0
                or (shadow_eligible_count > 0 and shadow_decision_count > 0)
            ),
            {
                "implementation_ready": shadow.get("implementation_ready"),
                "eligible_hypothesis_count": shadow_eligible_count,
                "trade_progression_eligible_hypothesis_count": shadow.get(
                    "trade_progression_eligible_hypothesis_count"
                ),
                "counterfactual_observation_hypothesis_count": shadow.get(
                    "counterfactual_observation_hypothesis_count"
                ),
                "decision_count": shadow_decision_count,
                "outcome_count": shadow.get("outcome_count"),
            },
            (
                "forward-shadow implementation ready; every current strategy signal has a "
                "frozen decision-time observation"
            ),
            (
                "The current strategy signal is not being observed forward, so Qadam cannot "
                "learn whether Akber's pass, hold, or veto improved the outcome."
            ),
        ),
        _check(
            "downstream.risk_and_router",
            risk.get("status") == "passed"
            and int(risk.get("validation_error_count") or 0) == 0
            and router.get("status") == "passed"
            and int(router.get("validation_error_count") or 0) == 0
            and (
                score_count == 0
                or int(router.get("decision_count") or 0) > 0
            )
            and why_not.get("status") in {"not_trading", "paper_review_candidate"},
            {
                "risk": risk.get("status"),
                "router": router.get("status"),
                "router_decision_count": router.get("decision_count"),
                "current_router_state": why_not.get("current_router_state"),
                "why_not_status": why_not.get("status"),
            },
            "risk and Router checks passed with exactly one current decision state per setup",
            "The strategy lane is not reaching a deterministic risk and Router conclusion.",
        ),
        _check(
            "operator.service_registered_and_running",
            bool(service)
            and operator.get("service_running") is True
            and service.get("current_execution_allowed") is True
            and power_circuit.get("state") == "closed",
            {
                "registered": bool(service),
                "operator_running": operator.get("service_running"),
                "execution_allowed": service.get("current_execution_allowed"),
                "circuit": power_circuit.get("state"),
            },
            "registered, running, allowed, and circuit closed",
            "The autonomous operator is not currently supervising the research lane.",
        ),
        _check(
            "dashboard.pattern_and_strategy_visible",
            wave_f_has_power,
            wave_f_has_power,
            "the power_scarcity_congestion strategy ID is present in the current Wave F view model",
            "The live dashboard model does not expose the new research lane.",
        ),
        _check(
            "storage.bulk_data_ignored",
            research_paths_are_ignored(),
            research_paths_are_ignored(),
            "bulk research path is Git-ignored",
            "Provider data could enter Git or deployment artifacts.",
        ),
        _check(
            "safety.no_unauthorized_authority",
            not any(authority_counters.values())
            and power.get("live_capital_enabled") is False
            and policy.get("risk", {}).get("risk_or_authority_mutation_allowed") is False,
            {
                **authority_counters,
                "live_capital_enabled": power.get("live_capital_enabled"),
                "risk_mutation_allowed": policy.get("risk", {}).get(
                    "risk_or_authority_mutation_allowed"
                ),
            },
            "zero unauthorized writes or proof and no live capital or risk mutation",
            "The research lane crossed an authority boundary.",
        ),
    ]
    blockers = [row["blocker"] for row in checks if not row["passed"]]
    hypothesis_count = int(power.get("backtest_hypothesis_count") or 0)
    edge_candidate_count = int(power.get("validated_candidate_count") or 0)
    empirical_state = (
        "current_strategy_signal_active"
        if score_count
        else "hypotheses_tested_no_current_signal"
        if hypothesis_count
        else "historical_evidence_collecting"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_edge_research_certification",
        "generated_at": generated_at or now_iso(),
        "status": "operational" if not blockers else "blocked",
        "operational": not blockers,
        "automatic_strategy_progression_operational": not blockers,
        "empirical_state": empirical_state,
        "edge_proven": edge_candidate_count > 0,
        "current_strategy_signal_count": score_count,
        "backtest_hypothesis_count": hypothesis_count,
        "validated_candidate_count": edge_candidate_count,
        "paper_order_created_count": authority_counters["paper_orders"],
        "broker_write_count": authority_counters["broker_writes"],
        "proof_credit_count": authority_counters["proof_credits"],
        "checks": checks,
        "blockers": unique_errors(blockers),
        "plain_english": (
            "Qadam is autonomously collecting real power-market evidence, testing the frozen mechanism, and can admit a bounded pattern-sourced strategy when the empirical and current-signal rules pass."
            if not blockers
            else "The active edge-research lane is not safe to rely on until the listed operational blockers are repaired."
        ),
        "authority": authority_flags(),
    }


def validate_active_edge_research_certification(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("active_edge_research_schema_invalid")
    if payload.get("status") not in {"operational", "blocked"}:
        errors.append("active_edge_research_status_invalid")
    if payload.get("operational") is not (not bool(payload.get("blockers"))):
        errors.append("active_edge_research_operational_blocker_mismatch")
    for field in ("paper_order_created_count", "broker_write_count", "proof_credit_count"):
        if int(payload.get(field) or 0) != 0:
            errors.append(f"active_edge_research_forbidden_count:{field}")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="active_edge_research"))
    return unique_errors(errors)


def build_and_write_active_edge_research_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    payload = build_active_edge_research_certification(settings)
    errors = validate_active_edge_research_certification(payload)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_edge_research_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors and payload.get("operational") is True else "blocked",
        "implementation_ready": not errors,
        "operational": payload.get("operational") is True,
        "automatic_strategy_progression_operational": payload.get(
            "automatic_strategy_progression_operational"
        ),
        "empirical_state": payload.get("empirical_state"),
        "edge_proven": payload.get("edge_proven"),
        "blockers": payload.get("blockers", []),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(CERTIFICATION_ARTIFACT, payload)
    store.write_json(CHECK_ARTIFACT, checks)
    return payload, checks, errors


__all__ = [
    "CERTIFICATION_ARTIFACT",
    "CHECK_ARTIFACT",
    "build_active_edge_research_certification",
    "build_and_write_active_edge_research_certification",
    "validate_active_edge_research_certification",
]
