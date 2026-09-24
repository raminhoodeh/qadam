"""Qadam-owned paper research decisions, without the retired Akber filter.

The V3 input/result ID aliases are transport compatibility only. No historical
Akber pass, veto, replay or threshold proposal has current decision authority.
Portfolio risk, Router and the single PaperOps execution owner remain separate.
"""

from collections import Counter
from copy import deepcopy
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import (
    build_akber_input,
    INACTIVE_TRIGGER_STATES,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags, now_iso, read_json, read_jsonl, runtime_dir, unique_errors,
)
from orchestrator.qadam_wave_b_common import stable_id

SCHEMA_VERSION = "qadam_strategy_decision.v1"
POLICY_VERSION = "qadam-autonomous-paper.1"
DECISION_OWNER = "qadam_autonomous"
INPUTS_ARTIFACT = "qadam_strategy_decision_inputs.jsonl"
RESULTS_ARTIFACT = "qadam_strategy_decision_results.jsonl"
DASHBOARD_ARTIFACT = "qadam_strategy_decision_summary.json"
CHECK_ARTIFACT = "qadam_strategy_decision_checks.json"
REQUIRED_FIELDS = (
    "source_price_context", "fresh_catalyst", "invalidation_clarity",
    "liquidity_and_spread", "paperability_proxy",
)
OPTIONAL_FIELDS = (
    "technical_confirmation", "volume_or_flow_confirmation",
    "volatility_context", "pricing_gap_evidence", "nonlinear_quantum_review",
)


def current_decision(record: dict[str, Any]) -> bool:
    """Fail closed on archived approvals and older decision policies."""
    return bool(
        record.get("decision_owner") == DECISION_OWNER
        and record.get("policy_version") == POLICY_VERSION
        and record.get("schema_version") == SCHEMA_VERSION
        and record.get("strategy_decision_id")
        and record.get("strategy_decision_id") == record.get("akber_result_id")
        and record.get("akber_authority_retired") is True
    )


def build_strategy_input(hypothesis, context, *, generated_at, strict_provenance=True):
    # Reuse evidence normalization, not the legacy evaluator or its required set.
    row = build_akber_input(
        hypothesis, context, generated_at=generated_at,
        strict_provenance=strict_provenance,
    )
    evidence = row["evidence"]
    for item in evidence.values():
        if strict_provenance and (
            item.get("provenance_complete") is not True
            or item.get("fixture_backed") is True
            or item.get("freshness_state") == "stale"
        ):
            item["available"] = False
    missing = [key for key in REQUIRED_FIELDS if evidence[key].get("available") is not True]
    input_id = stable_id(
        "qadam-strategy-input", POLICY_VERSION, row.get("decision_generation_id"),
        hypothesis["hypothesis_id"], evidence,
    )
    row.update(
        schema_version=SCHEMA_VERSION, policy_version=POLICY_VERSION,
        artifact_type="qadam_strategy_decision_input", decision_owner=DECISION_OWNER,
        strategy_input_id=input_id, akber_input_id=input_id,
        akber_authority_retired=True, required_context_fields=list(REQUIRED_FIELDS),
        missing_critical_context=missing, missing_critical_context_count=len(missing),
        missing_context_reasons=[{"field": key, "code": "required_execution_evidence_missing"}
                                 for key in missing],
        context_complete=not missing,
        direction=hypothesis.get("direction_horizon", {}).get("direction"),
    )
    return row


def evaluate_strategy_input(row):
    evidence = row["evidence"]
    missing = list(row["missing_critical_context"])
    if row.get("direction") not in {"long", "short"}:
        missing.append("direction")
    inactive = str(row.get("current_trigger_state") or "").lower() in INACTIVE_TRIGGER_STATES
    if inactive:
        missing = [key for key in missing if key != "fresh_catalyst"]
    adverse = [
        f"unsafe_execution_evidence:{key}"
        for key in REQUIRED_FIELDS
        if evidence[key].get("state") in {"unsafe", "invalid", "untradeable", "veto"}
    ]
    # Optional market disagreement changes conviction, not admission. Economics
    # and position sizing are decided once, by the portfolio-risk engine.
    missing_optional = [key for key in OPTIONAL_FIELDS if evidence[key].get("available") is not True]
    multiplier = round(max(0.25, 0.85 ** len(missing_optional)), 6)
    decision = "veto" if adverse else "watchlist_inactive_trigger" if inactive else "hold_missing_context" if missing else "pass"
    result_id = stable_id("qadam-strategy-decision", POLICY_VERSION, row["strategy_input_id"], decision)
    explanation = {
        "pass": "Qadam selected this setup for independent portfolio-risk and paper execution checks.",
        "veto": "Current evidence contains an unsafe execution condition.",
        "watchlist_inactive_trigger": "The research idea remains on watch; its entry trigger is inactive.",
        "hold_missing_context": "Execution evidence must be refreshed or completed: " + ", ".join(missing),
    }[decision]
    result = {key: deepcopy(value) for key, value in row.items() if key != "evidence"}
    result.update(
        artifact_type="qadam_strategy_decision_result",
        strategy_decision_id=result_id, akber_result_id=result_id,
        decision=decision,
        layered_decision="pass_reduced_size" if decision == "pass" and multiplier < 1 else "pass_full" if decision == "pass" else decision,
        stages=[], akber_stages_evaluated=False,
        missing_critical_context=missing, missing_critical_context_count=len(missing),
        hard_vetoes=adverse, router_eligible=decision == "pass",
        soft_evidence_size_multiplier=multiplier,
        soft_evidence_size_multiplier_components={key: 0.85 for key in missing_optional},
        uncertainty_actions=[{"field_id": key, "action": "soft_size_haircut"} for key in missing_optional],
        plain_english_explanation=explanation, consequence=explanation,
        risk_approval_created=False, execution_approval_created=False,
        trade_candidate_created=False, paper_order_created=False,
        akber_pass_is_execution_approval=False,
        authority=authority_flags(),
    )
    return result


def build_strategy_decision_state(settings: Settings | None = None):
    runtime = runtime_dir(settings)
    generated = now_iso()
    hypotheses = read_jsonl(runtime / "qadam_strategy_hypotheses_v3.jsonl")
    foundry = read_json(runtime / "qadam_canonical_tradeability_foundry_summary.json")
    packets = read_jsonl(runtime / "qadam_decision_evidence_packets.jsonl")
    errors = []
    if foundry.get("implementation_complete") is not True:
        errors.append("canonical_foundry_incomplete")
    if foundry.get("hypothesis_count") != len(hypotheses):
        errors.append("canonical_hypothesis_count_mismatch")
    inputs, results = [], []
    for hypothesis in hypotheses:
        if hypothesis.get("akber_review_allowed") is not True:
            continue
        matches = [row for row in packets if row.get("hypothesis_id") == hypothesis.get("hypothesis_id")]
        if len(matches) != 1:
            errors.append(f"decision_packet_cardinality:{hypothesis.get('hypothesis_id')}")
            continue
        packet = matches[0]
        if (packet.get("mixed_generation_join") is not False
            or not packet.get("decision_evidence_packet_id")
            or not packet.get("decision_generation_id")
            or packet.get("decision_generation_id") != hypothesis.get("decision_generation_id")
            or not hypothesis.get("tradeability_envelope_id")):
            errors.append(f"decision_packet_lineage:{hypothesis.get('hypothesis_id')}")
            continue
        context = deepcopy(packet.get("akber_context") or {})
        context["_decision_evidence_packet_id"] = packet["decision_evidence_packet_id"]
        context["_decision_generation_id"] = packet["decision_generation_id"]
        row = build_strategy_input(hypothesis, context, generated_at=generated)
        inputs.append(row)
        results.append(evaluate_strategy_input(row))
    errors = unique_errors(errors)
    if errors:
        inputs, results = [], []
    dashboard = {
        "schema_version": SCHEMA_VERSION, "generated_at": generated,
        "status": "blocked_invalid_input" if errors else "qadam_decisions_ready" if results else "no_current_hypotheses",
        "implementation_complete": not errors, "decision_owner": DECISION_OWNER,
        "policy_version": POLICY_VERSION, "akber_authority_retired": True,
        "headline": "Qadam autonomous strategy decisions",
        "plain_english": "Qadam selects paper setups; portfolio limits, reconciliation and exits remain mandatory. Akber is retired.",
        "hypothesis_count": len(hypotheses), "input_count": len(inputs), "result_count": len(results),
        "decision_counts": dict(Counter(row["decision"] for row in results)),
        "valid_no_current_hypothesis_outcome": not errors and not hypotheses,
        "historical_measurement_state": "akber_retired_not_required",
        "net_historical_contribution_measurable": False,
        "historical_replay_count": 0, "ablation_count": 0,
        "threshold_proposal_count": 0, "authority": authority_flags(),
    }
    return {"inputs": inputs, "results": results, "dashboard": dashboard,
            "input_errors": errors, "input_lineage": {"complete": not errors},
            "replay": [], "ablation": [], "threshold_proposals": []}


def build_and_write_strategy_decision(settings: Settings | None = None):
    state = build_strategy_decision_state(settings)
    store = AtomicArtifactStore(runtime_dir(settings))
    errors = state["input_errors"]
    checks = {
        **state["dashboard"], "status": "blocked" if errors else "passed",
        "implementation_ready": not errors, "safe_to_consume": not errors,
        "validation_errors": errors, "validation_error_count": len(errors),
        "input_lineage": state["input_lineage"],
        "pass_count": sum(row["decision"] == "pass" for row in state["results"]),
        "broker_write_count": 0, "order_created_count": 0,
        "execution_approval_created_count": 0, "risk_approval_created_count": 0,
    }
    store.write_jsonl(INPUTS_ARTIFACT, state["inputs"])
    store.write_jsonl(RESULTS_ARTIFACT, state["results"])
    store.write_json(DASHBOARD_ARTIFACT, state["dashboard"])
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
