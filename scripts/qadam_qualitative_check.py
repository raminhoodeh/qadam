#!/usr/bin/env python3
"""Shared dispatcher for qualitative evidence and all-lane check scripts."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_agent_reach_certification import build_agent_reach_certification
from orchestrator.qadam_agent_reach_operator import run_agent_reach_operator
from orchestrator.qadam_agent_reach_sandbox import build_agent_reach_baseline, build_agent_reach_sandbox
from orchestrator.qadam_all_lane_conversion_certification import build_all_lane_conversion_certification
from orchestrator.qadam_evidence_contracts import lane_capability_index, validate_lane_contribution
from orchestrator.qadam_external_acquisition import run_external_acquisition
from orchestrator.qadam_external_evidence_lake import build_external_evidence_lake
from orchestrator.qadam_external_origin_registry import build_external_origin_state
from orchestrator.qadam_lane_conversion import build_lane_conversion
from orchestrator.qadam_lane_reachability import build_lane_reachability
from orchestrator.qadam_lane_trigger_fast_path import run_lane_trigger_fast_path
from orchestrator.qadam_prediction_market_research import build_prediction_market_research
from orchestrator.qadam_qualitative_akber_bridge import build_qualitative_akber_bridge
from orchestrator.qadam_qualitative_claim_challenge import challenge_qualitative_claims
from orchestrator.qadam_qualitative_claim_extraction import extract_qualitative_claims
from orchestrator.qadam_qualitative_common import read_json, read_jsonl, research_root, runtime_dir, sha256_json
from orchestrator.qadam_qualitative_evidence_graph import build_qualitative_evidence_graph
from orchestrator.qadam_qualitative_history import build_qualitative_history
from orchestrator.qadam_qualitative_pattern_lab import run_qualitative_pattern_lab
from orchestrator.qadam_qualitative_strategy_bridge import build_qualitative_strategy_bridge
from orchestrator.qadam_qualitative_visibility import build_qualitative_visibility
from orchestrator.qadam_tradeability_pipeline import build_and_write_tradeability_pipeline


CheckFunction = Callable[[], tuple[Any, list[str]]]


def _artifact(name: str) -> dict[str, Any]:
    return read_json(runtime_dir() / name)


def _rows(name: str) -> list[dict[str, Any]]:
    return read_jsonl(runtime_dir() / name)


def _validate_source_count() -> tuple[dict[str, Any], list[str]]:
    payload = _artifact("qadam_source_count_contract.json")
    errors = []
    if payload.get("canonical_source_count") != 41:
        errors.append("canonical_source_count_not_41")
    if payload.get("canonical_instrument_count") != 19:
        errors.append("canonical_instrument_count_not_19")
    if payload.get("transport_included_in_canonical_source_count") is not False:
        errors.append("transport_inflated_source_count")
    return payload, errors


def _validate_grounding() -> tuple[dict[str, Any], list[str]]:
    claims = _rows("qadam_qualitative_claims.jsonl")
    errors = []
    for claim in claims:
        span = claim.get("supporting_span") or {}
        path = research_root() / "evidence_lake" / f"{str(claim.get('document_id')).replace(':', '_')}.json"
        try:
            text = str(json.loads(path.read_text(encoding="utf-8")).get("text") or "")
        except (OSError, json.JSONDecodeError):
            errors.append(f"claim_source_unreadable:{claim.get('claim_id')}")
            continue
        start = int(span.get("start") or 0)
        end = int(span.get("end") or 0)
        if start < 0 or end <= start or text[start:end] != span.get("text"):
            errors.append(f"claim_span_not_exact:{claim.get('claim_id')}")
    return {"status": "passed" if not errors else "blocked", "claim_count": len(claims)}, errors


def _validate_point_in_time() -> tuple[dict[str, Any], list[str]]:
    coverage = _artifact("qadam_qualitative_history_coverage.json")
    labels = _rows("qadam_qualitative_label_manifest.jsonl")
    errors = []
    if any(row.get("point_in_time_safe") is not True for row in labels):
        errors.append("qualitative_label_leakage_detected")
    if int(coverage.get("paper_growth_trial_advanced") or 0) != 0:
        errors.append("historical_replay_advanced_paper_calendar")
    return coverage, errors


def _validate_pattern_controls() -> tuple[dict[str, Any], list[str]]:
    summary = _artifact("qadam_qualitative_backtest_summary.json")
    patterns = _rows("qadam_qualitative_pattern_candidates.jsonl")
    errors = []
    if int(summary.get("negative_control_promoted_count") or 0) != 0:
        errors.append("negative_control_promoted")
    for row in patterns:
        if row.get("holdout_state") != "passed" or row.get("strategy_nomination_allowed") is not True:
            errors.append(f"unvalidated_pattern_promoted:{row.get('pattern_id')}")
        if float(row.get("net_expectancy") or 0) <= 0:
            errors.append(f"nonpositive_pattern_promoted:{row.get('pattern_id')}")
    return summary, errors


def _validate_prediction() -> tuple[dict[str, Any], list[str]]:
    result, errors = build_prediction_market_research()
    summary = result.get("summary") or result
    if summary.get("direct_prediction_market_trade_allowed") is not False:
        errors.append("prediction_market_direct_trade_enabled")
    if int(summary.get("liquidity_qualified_disagreement_count") or 0) == 0 and int(summary.get("strategy_nomination_count") or 0) != 0:
        errors.append("prediction_strategy_nominated_without_liquidity")
    return summary, errors


def _validate_prediction_contracts() -> tuple[dict[str, Any], list[str]]:
    result, errors = build_prediction_market_research()
    rows = _rows("qadam_prediction_contracts.jsonl")
    for row in rows:
        if not row.get("contract_id") or not row.get("venue_contract_identity"):
            errors.append("prediction_contract_identity_missing")
        if not row.get("canonical_question") or not row.get("coverage_start"):
            errors.append(f"prediction_contract_semantics_or_time_missing:{row.get('contract_id')}")
        if row.get("direct_venue_paperability") is not False:
            errors.append(f"prediction_contract_direct_paperability_enabled:{row.get('contract_id')}")
    return {"status": "passed" if not errors else "blocked", "contract_count": len(rows)}, sorted(set(errors))


def _validate_prediction_transactions() -> tuple[dict[str, Any], list[str]]:
    build_prediction_market_research()
    quality = _artifact("qadam_prediction_market_quality.json")
    errors = []
    if int(quality.get("naive_gross_activity_labelled_as_volume_count") or 0) != 0:
        errors.append("prediction_naive_gross_activity_volume_inflation")
    retained = int(quality.get("retained_onchain_activity_record_count") or 0)
    if retained == 0 and quality.get("transaction_decomposition_state") != "not_applicable_no_onchain_activity_records_retained":
        errors.append("prediction_transaction_decomposition_missing_typed_state")
    return quality, errors


def _validate_prediction_graph() -> tuple[dict[str, Any], list[str]]:
    build_prediction_market_research()
    graph = _artifact("qadam_prediction_contract_graph.json")
    errors = []
    if int(graph.get("false_deterministic_arbitrage_count") or 0) != 0:
        errors.append("prediction_false_deterministic_arbitrage")
    for edge in graph.get("edges") or []:
        if edge.get("deterministic_arbitrage_claimed") is not False:
            errors.append(f"prediction_unvalidated_graph_edge_promoted:{edge.get('edge_id')}")
        if edge.get("semantic_compatibility") != "requires_human_or_model_semantics_review":
            errors.append(f"prediction_edge_semantics_state_invalid:{edge.get('edge_id')}")
    return graph, sorted(set(errors))


def _validate_prediction_beliefs() -> tuple[dict[str, Any], list[str]]:
    result, errors = build_prediction_market_research()
    rows = _rows("qadam_prediction_belief_states.jsonl")
    for row in rows:
        probability = row.get("probability")
        if not isinstance(probability, (int, float)) or not 0 < float(probability) < 1:
            errors.append(f"prediction_probability_invalid:{row.get('belief_state_id')}")
        if not row.get("decision_time"):
            errors.append(f"prediction_decision_time_missing:{row.get('belief_state_id')}")
        if row.get("direct_trade_allowed") is not False:
            errors.append(f"prediction_belief_direct_trade_enabled:{row.get('belief_state_id')}")
    return {"status": "passed" if not errors else "blocked", "belief_count": len(rows), "research": result}, sorted(set(errors))


def _validate_prediction_controls() -> tuple[dict[str, Any], list[str]]:
    result, errors = build_prediction_market_research()
    quality = _artifact("qadam_prediction_market_quality.json")
    if int(quality.get("withdrawn_paper_empirical_credit_count") or 0) != 0:
        errors.append("withdrawn_prediction_paper_received_credit")
    if int(result.get("liquidity_qualified_disagreement_count") or 0) == 0 and int(result.get("strategy_nomination_count") or 0) != 0:
        errors.append("prediction_nomination_without_liquidity")
    if result.get("negative_controls_required_before_promotion") is not True:
        errors.append("prediction_negative_controls_not_required")
    return result, errors


def _validate_prediction_bridge() -> tuple[dict[str, Any], list[str]]:
    result, errors = build_prediction_market_research()
    signals = _rows("qadam_prediction_market_cross_asset_signals.jsonl")
    for row in signals:
        if row.get("liquidity_qualified") is not True or row.get("decision_time_eligible") is not True:
            errors.append(f"prediction_cross_asset_signal_unqualified:{row.get('signal_id')}")
        if not row.get("mapped_instruments"):
            errors.append(f"prediction_cross_asset_signal_unmapped:{row.get('signal_id')}")
    if result.get("direct_prediction_market_trade_allowed") is not False:
        errors.append("prediction_direct_execution_enabled")
    return {"status": "passed" if not errors else "blocked", "signal_count": len(signals)}, sorted(set(errors))


def _validate_acquisition_idempotency() -> tuple[dict[str, Any], list[str]]:
    run_external_acquisition(allow_network=False)
    before = _rows("qadam_external_document_manifest.jsonl")
    run_external_acquisition(allow_network=False)
    after = _rows("qadam_external_document_manifest.jsonl")
    errors = []
    if sha256_json(before) != sha256_json(after):
        errors.append("external_retrieval_not_idempotent")
    if len({row.get("document_id") for row in after}) != len(after):
        errors.append("external_logical_document_duplicate")
    return {"status": "passed" if not errors else "blocked", "document_count": len(after)}, errors


def _validate_lane_registry() -> tuple[dict[str, Any], list[str]]:
    lanes = lane_capability_index()
    errors = []
    if not lanes:
        errors.append("lane_registry_empty")
    for lane_id, row in lanes.items():
        if not row.get("owner") or not row.get("maximum_authority"):
            errors.append(f"lane_capability_incomplete:{lane_id}")
        if row.get("direct_broker_authority") is not False:
            errors.append(f"lane_direct_broker_authority:{lane_id}")
    return {"status": "passed" if not errors else "blocked", "lane_count": len(lanes)}, errors


def _validate_lane_contributions() -> tuple[dict[str, Any], list[str]]:
    conversion, errors = build_lane_conversion()
    rows = conversion.get("contributions") or []
    for row in rows:
        errors.extend(validate_lane_contribution(row))
    return conversion.get("funnel") or {}, sorted(set(errors))


def _validate_security() -> tuple[dict[str, Any], list[str]]:
    audit = _artifact("qadam_external_evidence_security_audit.json")
    errors = []
    if audit.get("status") != "passed":
        errors.append("external_evidence_security_not_passed")
    if audit.get("quarantined_content_reaches_models") is not False:
        errors.append("quarantined_content_reaches_models")
    return audit, errors


def _validate_provenance() -> tuple[dict[str, Any], list[str]]:
    audit = _artifact("qadam_external_evidence_provenance_audit.json")
    errors = []
    if audit.get("status") != "passed":
        errors.append("external_evidence_provenance_not_passed")
    if audit.get("public_artifacts_contain_full_raw_text") is not False:
        errors.append("public_raw_text_exposure")
    if audit.get("public_artifacts_contain_local_paths") is not False:
        errors.append("public_local_path_exposure")
    return audit, errors


def _validate_resource_limits() -> tuple[dict[str, Any], list[str]]:
    run_agent_reach_operator(allow_network=False, run_fast_path=False)
    resource = _artifact("qadam_agent_reach_resource_state.json")
    return resource, list(resource.get("validation_errors") or [])


def _validate_tradeability_compiler() -> tuple[dict[str, Any], list[str]]:
    _state, checks, errors = build_and_write_tradeability_pipeline()
    return checks, errors


DISPATCH: dict[str, CheckFunction] = {
    "check_qadam_agent_reach_baseline.py": lambda: build_agent_reach_baseline(),
    "check_qadam_source_count_contract.py": _validate_source_count,
    "check_qadam_agent_reach_supply_chain.py": lambda: build_agent_reach_sandbox(),
    "check_qadam_agent_reach_sandbox.py": lambda: build_agent_reach_sandbox(),
    "check_qadam_external_origin_registry.py": lambda: build_external_origin_state(),
    "check_qadam_external_origin_terms.py": lambda: build_external_origin_state(),
    "check_qadam_external_acquisition.py": lambda: run_external_acquisition(allow_network=False),
    "check_qadam_external_retrieval_idempotency.py": _validate_acquisition_idempotency,
    "check_qadam_external_evidence_contracts.py": lambda: build_external_evidence_lake(),
    "check_qadam_external_evidence_provenance.py": _validate_provenance,
    "check_qadam_external_evidence_security.py": _validate_security,
    "check_qadam_qualitative_claim_extraction.py": lambda: extract_qualitative_claims(),
    "check_qadam_qualitative_claim_grounding.py": _validate_grounding,
    "check_qadam_qualitative_temporal_graph.py": lambda: build_qualitative_evidence_graph(),
    "check_qadam_qualitative_instrument_mapping.py": lambda: build_qualitative_evidence_graph(),
    "check_qadam_qualitative_history.py": lambda: build_qualitative_history(),
    "check_qadam_qualitative_point_in_time.py": _validate_point_in_time,
    "check_qadam_qualitative_forward_labels.py": _validate_point_in_time,
    "check_qadam_qualitative_pattern_lab.py": lambda: run_qualitative_pattern_lab(),
    "check_qadam_qualitative_negative_controls.py": _validate_pattern_controls,
    "check_qadam_qualitative_quantum_comparison.py": _validate_pattern_controls,
    "check_qadam_qualitative_pattern_bridge.py": lambda: build_qualitative_strategy_bridge(),
    "check_qadam_qualitative_strategy_bridge.py": lambda: build_qualitative_strategy_bridge(),
    "check_qadam_qualitative_akber_bridge.py": lambda: build_qualitative_akber_bridge(),
    "check_qadam_agent_reach_operations.py": lambda: run_agent_reach_operator(allow_network=False, run_fast_path=False),
    "check_qadam_agent_reach_resource_limits.py": _validate_resource_limits,
    "check_qadam_qualitative_dashboard.py": lambda: build_qualitative_visibility(),
    "check_qadam_qualitative_telegram.py": lambda: build_qualitative_visibility(),
    "check_qadam_prediction_contracts.py": _validate_prediction_contracts,
    "check_qadam_prediction_transaction_decomposition.py": _validate_prediction_transactions,
    "check_qadam_prediction_contract_graph.py": _validate_prediction_graph,
    "check_qadam_prediction_belief_state.py": _validate_prediction_beliefs,
    "check_qadam_prediction_negative_controls.py": _validate_prediction_controls,
    "check_qadam_prediction_strategy_bridge.py": _validate_prediction_bridge,
    "check_qadam_lane_capability_registry.py": _validate_lane_registry,
    "check_qadam_lane_contribution_contracts.py": _validate_lane_contributions,
    "check_qadam_tradeability_envelope_compiler.py": _validate_tradeability_compiler,
    "check_qadam_lane_generation_integrity.py": _validate_tradeability_compiler,
    "check_qadam_lane_trigger_fast_path.py": lambda: run_lane_trigger_fast_path(allow_network=False),
    "check_qadam_lane_blocker_ownership.py": _validate_lane_contributions,
    "check_qadam_lane_golden_journeys.py": lambda: build_lane_reachability(),
    "check_qadam_lane_reachability.py": lambda: build_lane_reachability(),
    "check_qadam_all_lane_conversion.py": lambda: build_all_lane_conversion_certification(),
    "check_qadam_agent_reach_enrichment.py": lambda: build_agent_reach_certification(),
}


def main() -> int:
    name = Path(sys.argv[0]).name
    function = DISPATCH.get(name)
    if function is None:
        print(f"error=unknown_check:{name}")
        return 2
    payload, errors = function()
    status = payload.get("status") if isinstance(payload, dict) else None
    print(f"check={name}")
    print(f"status={status or ('passed' if not errors else 'blocked')}")
    print(f"validation_error_count={len(errors)}")
    for error in sorted(set(errors)):
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
