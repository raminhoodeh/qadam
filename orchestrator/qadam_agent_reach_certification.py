"""End-to-end certification for qualitative enrichment and lane conversion."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_all_lane_conversion_certification import (
    build_all_lane_conversion_certification,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    AGENT_REACH_ACTIVATION_ARTIFACT,
    AGENT_REACH_BASELINE_ARTIFACT,
    AGENT_REACH_CERTIFICATION_ARTIFACT,
    AGENT_REACH_OPERATOR_ARTIFACT,
    AGENT_REACH_RESOURCE_ARTIFACT,
    AGENT_REACH_SANDBOX_ARTIFACT,
    AGENT_REACH_SOAK_ARTIFACT,
    AGENT_REACH_SUPPLY_CHAIN_ARTIFACT,
    EXTERNAL_ACQUISITION_ARTIFACT,
    EXTERNAL_PROVENANCE_ARTIFACT,
    EXTERNAL_SECURITY_ARTIFACT,
    EXTERNAL_TERMS_ARTIFACT,
    PREDICTION_RESEARCH_ARTIFACT,
    QUALITATIVE_AKBER_INPUTS_ARTIFACT,
    QUALITATIVE_BACKTEST_ARTIFACT,
    QUALITATIVE_CHALLENGES_ARTIFACT,
    QUALITATIVE_CLAIMS_ARTIFACT,
    QUALITATIVE_CLAIM_SUMMARY_ARTIFACT,
    QUALITATIVE_COMMUNICATIONS_ARTIFACT,
    QUALITATIVE_DASHBOARD_ARTIFACT,
    QUALITATIVE_FORWARD_WINDOWS_ARTIFACT,
    QUALITATIVE_GRAPH_SUMMARY_ARTIFACT,
    QUALITATIVE_HISTORY_ARTIFACT,
    QUALITATIVE_IMPACT_ARTIFACT,
    QUALITATIVE_PAPER_ELIGIBILITY_ARTIFACT,
    QUALITATIVE_PATTERN_BRIDGE_ARTIFACT,
    SOURCE_COUNT_CONTRACT_ARTIFACT,
    now_iso,
    public_authority,
    read_json,
    read_jsonl,
    runtime_dir,
)
from orchestrator.qadam_qualitative_visibility import validate_qualitative_visibility


def _phase(phase_id: str, name: str, passed: bool, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase_id": phase_id,
        "name": name,
        "status": "passed" if passed else "blocked",
        "detail": detail,
    }


def build_agent_reach_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    baseline = read_json(runtime / AGENT_REACH_BASELINE_ARTIFACT)
    source_count = read_json(runtime / SOURCE_COUNT_CONTRACT_ARTIFACT)
    supply_chain = read_json(runtime / AGENT_REACH_SUPPLY_CHAIN_ARTIFACT)
    sandbox = read_json(runtime / AGENT_REACH_SANDBOX_ARTIFACT)
    terms = read_json(runtime / EXTERNAL_TERMS_ARTIFACT)
    acquisition = read_json(runtime / EXTERNAL_ACQUISITION_ARTIFACT)
    security = read_json(runtime / EXTERNAL_SECURITY_ARTIFACT)
    provenance = read_json(runtime / EXTERNAL_PROVENANCE_ARTIFACT)
    claim_rows = read_jsonl(runtime / QUALITATIVE_CLAIMS_ARTIFACT)
    challenge_rows = read_jsonl(runtime / QUALITATIVE_CHALLENGES_ARTIFACT)
    claims = read_json(runtime / QUALITATIVE_CLAIM_SUMMARY_ARTIFACT)
    graph = read_json(runtime / QUALITATIVE_GRAPH_SUMMARY_ARTIFACT)
    history = read_json(runtime / QUALITATIVE_HISTORY_ARTIFACT)
    windows = read_json(runtime / QUALITATIVE_FORWARD_WINDOWS_ARTIFACT)
    backtest = read_json(runtime / QUALITATIVE_BACKTEST_ARTIFACT)
    bridge = read_json(runtime / QUALITATIVE_PATTERN_BRIDGE_ARTIFACT)
    akber_inputs = read_jsonl(runtime / QUALITATIVE_AKBER_INPUTS_ARTIFACT)
    eligibility = read_json(runtime / QUALITATIVE_PAPER_ELIGIBILITY_ARTIFACT)
    operator = read_json(runtime / AGENT_REACH_OPERATOR_ARTIFACT)
    resource = read_json(runtime / AGENT_REACH_RESOURCE_ARTIFACT)
    soak = read_json(runtime / AGENT_REACH_SOAK_ARTIFACT)
    dashboard = read_json(runtime / QUALITATIVE_DASHBOARD_ARTIFACT)
    communications = read_json(runtime / QUALITATIVE_COMMUNICATIONS_ARTIFACT)
    prediction = read_json(runtime / PREDICTION_RESEARCH_ARTIFACT)
    all_lane, lane_errors = build_all_lane_conversion_certification(settings)

    accepted_claim_ids = {
        str(row.get("claim_id")) for row in claim_rows if row.get("claim_id")
    }
    challenged_claim_ids = {
        str(row.get("claim_id")) for row in challenge_rows if row.get("claim_id")
    }
    challenge_coverage_complete = bool(accepted_claim_ids) and accepted_claim_ids.issubset(
        challenged_claim_ids
    )
    forward_windows = windows.get("windows") or []
    point_in_time_safe = (
        int(history.get("leakage_violation_count") or 0) == 0
        and history.get("paper_growth_trial_advanced") is False
        and history.get("proof_credit_created") is False
        and all(row.get("point_in_time_safe") is True for row in forward_windows)
    )
    qualified_pattern_count = int(backtest.get("candidate_count") or 0)
    canonical_strategy_draft_count = int(
        bridge.get("canonical_strategy_draft_count") or 0
    )
    strategy_translation_complete = (
        bridge.get("status")
        in {
            "ready_no_qualified_pattern",
            "ready_strategy_foundry_nominations",
            "passed",
        }
        and canonical_strategy_draft_count == qualified_pattern_count
    )
    accepted_claim_count = int(claims.get("accepted_claim_count") or 0)
    akber_fit_complete = (
        len(akber_inputs) == accepted_claim_count
        and int(eligibility.get("spread_or_liquidity_fabricated_count") or 0) == 0
        and int(eligibility.get("expected_return_fabricated_count") or 0) == 0
    )
    visibility_errors = validate_qualitative_visibility(
        {"dashboard": dashboard, "communications": communications}
    )

    phases = [
        _phase("AR-0", "Baseline and source-count truth", baseline.get("status") == "passed" and source_count.get("canonical_source_count") == 41 and source_count.get("transport_included_in_canonical_source_count") is False, {"canonical_source_count": source_count.get("canonical_source_count")}),
        _phase("AR-1", "Supply chain and sandbox", supply_chain.get("status") == "passed" and sandbox.get("status") == "passed", {"runtime_import_allowed": supply_chain.get("runtime_import_allowed")}),
        _phase("AR-2", "Origin and trust policy", terms.get("status") == "passed", {"enabled_origin_count": terms.get("enabled_origin_count")}),
        _phase(
            "AR-3",
            "Zero-auth acquisition",
            acquisition.get("status")
            in {
                "passed",
                "ready_cached_documents",
                "ready_network_not_requested",
                "complete",
                "completed",
                "completed_with_isolated_failures",
            }
            and int(acquisition.get("document_count") or 0) > 0
            and acquisition.get("ever_completed_real_network_fetch") is True,
            {
                "document_count": acquisition.get("document_count"),
                "last_successful_network_at": acquisition.get(
                    "last_successful_network_at"
                ),
                "real_network_fetch_proven": acquisition.get(
                    "ever_completed_real_network_fetch"
                )
                is True,
            },
        ),
        _phase("AR-4", "Provenance and evidence security", security.get("status") == "passed" and provenance.get("status") == "passed", {"research_eligible_document_count": provenance.get("research_eligible_count")}),
        _phase(
            "AR-5",
            "Grounded claims and challenge",
            claims.get("status") == "passed"
            and float(claims.get("grounded_span_coverage") or 0) == 1.0
            and challenge_coverage_complete,
            {
                "accepted_claim_count": accepted_claim_count,
                "challenged_claim_count": len(challenged_claim_ids),
                "challenge_coverage_complete": challenge_coverage_complete,
            },
        ),
        _phase("AR-6", "Temporal evidence graph", graph.get("status") == "passed", {"record_type_counts": graph.get("record_type_counts")}),
        _phase(
            "AR-7",
            "Point-in-time outcomes",
            windows.get("status") in {"ready", "ready_no_claims"}
            and point_in_time_safe,
            {
                "pending_window_count": windows.get("pending_window_count"),
                "point_in_time_safe": point_in_time_safe,
            },
        ),
        _phase("AR-8", "Pattern and challenger tests", backtest.get("status") in {"complete_no_qualified_pattern", "complete_candidates_require_holdout", "complete_validated_patterns"} and int(backtest.get("negative_control_promoted_count") or 0) == 0, {"candidate_count": backtest.get("candidate_count")}),
        _phase(
            "AR-9",
            "Strategy translation",
            strategy_translation_complete,
            {
                "qualified_pattern_count": qualified_pattern_count,
                "canonical_strategy_draft_count": canonical_strategy_draft_count,
            },
        ),
        _phase(
            "AR-10",
            "Akber evidence fit",
            akber_fit_complete,
            {
                "akber_input_count": len(akber_inputs),
                "accepted_claim_count": accepted_claim_count,
                "fabricated_execution_field_count": int(
                    eligibility.get("spread_or_liquidity_fabricated_count") or 0
                )
                + int(eligibility.get("expected_return_fabricated_count") or 0),
            },
        ),
        _phase(
            "AR-11",
            "Autonomous operation",
            operator.get("status") == "operational"
            and resource.get("status") == "within_limits"
            and soak.get("status") == "soak_complete"
            and int(soak.get("consecutive_successful_cycles") or 0)
            >= int(soak.get("required_successful_cycles") or 7),
            {
                "soak_status": soak.get("status"),
                "consecutive_successful_cycles": soak.get(
                    "consecutive_successful_cycles"
                ),
                "required_successful_cycles": soak.get("required_successful_cycles"),
            },
        ),
        _phase(
            "AR-12",
            "Public-safe visibility",
            not visibility_errors,
            {
                "dashboard_structure_preserved": dashboard.get(
                    "existing_dashboard_structure_preserved"
                ),
                "communications_state": communications.get("status"),
                "visibility_errors": visibility_errors,
            },
        ),
        _phase("AR-13", "All-lane reachability", all_lane.get("status") == "passed", {"accepted_broker_disabled_handoff_count": all_lane.get("accepted_broker_disabled_handoff_count")}),
    ]
    errors = list(lane_errors)
    errors.extend(
        f"phase_blocked:{row['phase_id']}" for row in phases if row["status"] != "passed"
    )
    if int(security.get("quarantined_document_count") or 0) < 0:
        errors.append("security_quarantine_count_invalid")
    if (dashboard.get("authority") or {}).get("live_capital_enabled") is not False:
        errors.append("public_visibility_live_capital_authority")
    unique_errors = sorted(set(errors))
    passed = not unique_errors
    impact = {
        "schema_version": "qadam_qualitative_evidence_impact_report.v1",
        "artifact_type": "qadam_qualitative_evidence_impact_report",
        "generated_at": now_iso(),
        "measurement_state": "baseline_collecting_real_outcomes",
        "official_document_count": int(acquisition.get("document_count") or 0),
        "grounded_claim_count": int(claims.get("accepted_claim_count") or 0),
        "mature_forward_label_count": int(backtest.get("label_count") or 0),
        "qualified_pattern_count": int(backtest.get("candidate_count") or 0),
        "prediction_contract_count": int(prediction.get("contract_count") or 0),
        "prediction_disagreement_count": int(prediction.get("disagreement_count") or 0),
        "liquidity_qualified_prediction_disagreement_count": int(prediction.get("liquidity_qualified_disagreement_count") or 0),
        "a4_nomination_count": int(all_lane.get("a4_nomination_count") or 0),
        "additional_real_paper_orders_attributed_to_new_lane": 0,
        "profitability_claim_allowed": False,
        "first_controlled_review_requires_market_days": 20,
        "first_controlled_review_requires_independent_events": 30,
        "authority": public_authority(),
    }
    payload = {
        "schema_version": "qadam_agent_reach_enrichment_certification.v1",
        "artifact_type": "qadam_agent_reach_enrichment_certification",
        "generated_at": now_iso(),
        "status": "passed" if passed else "blocked",
        "implementation_complete": passed,
        "phase_count": len(phases),
        "passed_phase_count": sum(row["status"] == "passed" for row in phases),
        "phases": phases,
        "all_lane_conversion_status": all_lane.get("status"),
        "live_capital_enabled": False,
        "direct_broker_authority_granted": False,
        "paper_order_created_by_certification": False,
        "proof_credit_created": False,
        "validation_errors": unique_errors,
        "authority": public_authority(),
    }
    activation = {
        "schema_version": "qadam_agent_reach_activation_receipt.v1",
        "artifact_type": "qadam_agent_reach_activation_receipt",
        "generated_at": payload["generated_at"],
        "status": "active_research_enrichment" if passed else "activation_blocked",
        "enabled_origins": int(terms.get("enabled_origin_count") or 0) if passed else 0,
        "lane_conversion_enabled": passed,
        "router_or_paperops_bypass_enabled": False,
        "direct_broker_authority_granted": False,
        "live_capital_enabled": False,
        "authority": public_authority(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(QUALITATIVE_IMPACT_ARTIFACT, impact)
    store.write_json(AGENT_REACH_CERTIFICATION_ARTIFACT, payload)
    store.write_json(AGENT_REACH_ACTIVATION_ARTIFACT, activation)
    return payload, unique_errors


__all__ = ["build_agent_reach_certification"]
