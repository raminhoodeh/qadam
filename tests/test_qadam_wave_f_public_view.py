from __future__ import annotations

from copy import deepcopy
import json

import pytest

from orchestrator.qadam_wave_f_public_view import (
    PATTERN_ROUTE,
    QUANTUM_EDGE_ROUTE,
    STRATEGY_ROUTE,
    build_wave_f_public_view,
    build_wave_f_public_view_from_artifacts,
    validate_wave_f_public_view,
    write_wave_f_public_view,
)

GENERATED_AT = "2026-07-12T12:00:00+00:00"


def _legacy_relationship(*, validated: bool = False) -> dict:
    return {
        "pattern_id": "pattern:classical-oil",
        "title": "Classical oil disruption relationship",
        "stage": "validated_edge" if validated else "awaiting_historical_evidence",
        "stage_label": "Validated edge" if validated else "Awaiting historical evidence",
        "source_chain": ["acled", "ais_maritime"],
        "target_market": "Crude oil",
        "target_instruments": ["BNO"],
        "plain_english_question": "Do shipping disruptions precede crude-oil repricing?",
        "what_qadam_thinks": "Conflict and vessel-flow evidence may precede price response.",
        "evidence_quality_score": 0.545,
        "confidence_score": 0.545,
        "what_would_confirm": "Untouched outcomes remain positive after costs.",
        "falsifiers": ["The relationship disappears on holdout evidence."],
        "blocked_by": [] if validated else ["No untouched holdout exists."],
        "next_action": "Run the frozen historical test.",
        "strategy_family_id": "oil_strategy",
    }


def _hybrid_candidate() -> dict:
    return {
        "candidate_id": "hybrid-candidate:fixture",
        "discovery_origin": "joint_discovery",
        "validation_contribution": "not_tested",
        "relationship": "Source density and agreement move together nonlinearly.",
        "source_chain": {"feature_pair": ["source_density", "source_agreement"]},
        "market": "Crude oil repricing",
        "observed_instruments": ["BNO"],
        "interpretation": "The joint source regime may precede repricing.",
        "confirmation": "Repeat on untouched point-in-time evidence.",
        "falsifier": "No improvement over the classical baseline.",
        "evidence_state": "fixture_only",
        "lifecycle_state": "candidate_relationship",
        "blocker": "No empirical holdout exists.",
        "next_action": "Backfill provider evidence.",
        "contract_fixture_only": True,
        "empirical_evidence_count": 0,
        "evidence_records": [
            {
                "discovery_origin": "classical_discovery",
                "method": "tree_interaction",
                "execution_mode": "classical",
                "structural_score": 0.9,
                "quantum_simulation_completed": False,
                "hardware_experiment_completed": False,
                "hardware_receipt_hash": None,
            },
            {
                "discovery_origin": "quantum_assisted_discovery",
                "method": "fidelity_kernel",
                "execution_mode": "qiskit_statevector_ideal",
                "structural_score": 0.6,
                "quantum_simulation_completed": True,
                "hardware_experiment_completed": False,
                "hardware_receipt_hash": None,
            },
        ],
    }


def _evaluation() -> dict:
    return {
        "evaluation_id": "evaluation:fixture",
        "candidate_id": "hybrid-candidate:fixture",
        "validation_contribution": "not_measurable",
        "empirical_claim_allowed": False,
        "measurability_blockers": ["empirical_untouched_holdout_missing"],
    }


def _strategy(*, validated: bool = False) -> dict:
    return {
        "strategy_family_id": "oil_strategy",
        "label": "Oil disruption playbook",
        "validated_edge_count": 1 if validated else 0,
        "catalyst_class": "physical disruption",
        "plain_english_summary": "Investigate delayed energy repricing.",
        "what_qadam_watches": "Conflict and vessel-flow evidence.",
        "current_evidence_state": "Validated" if validated else "Awaiting validation",
        "current_blocker_plain_english": "No validated edge exists yet.",
        "next_action_plain_english": "Run the frozen holdout test.",
        "current_state": "validated" if validated else "research_only",
        "core_instruments_explained": [{"symbol": "BNO"}],
    }


def _artifacts(*, validated: bool = False) -> dict:
    return {
        "pattern_discovery": {
            "relationships": [_legacy_relationship(validated=validated)]
        },
        "hybrid_candidates": [_hybrid_candidate()],
        "evaluations": [_evaluation()],
        "evaluation_summary": {
            "verdict_counts": {"quantum_strengthened": 0, "weakened": 0},
            "empirical_measured_count": 0,
            "evaluator_policy_hash": "policy-hash",
        },
        "classical_discovery": {"result_id": "classical:fixture"},
        "local_quantum": {
            "status": "local_quantum_discovery_ready",
            "ideal_result": {
                "quantum_simulation_completed": True,
                "qubit_count": 6,
                "circuit_evaluation_count": 100,
            },
            "finite_shot_result": {
                "quantum_simulation_completed": True,
                "shots": 256,
            },
        },
        "provider_readiness": {
            "credentials_configured": True,
            "product_entitled": True,
            "backend_discovered": False,
            "blocker": "ibm_token_instance_access_mismatch",
        },
        "hardware_public": {
            "manifest_hash": "hardware-manifest",
            "lifecycle_status": "prepared",
            "provider_call_count": 0,
            "hardware_execution_authorized": False,
            "hardware_job_submitted": False,
            "hardware_experiment_completed": False,
            "receipt_hash": None,
            "manifest": {
                "shared_manifest_hash": "shared-manifest",
                "circuit_count": 100,
                "shots_per_circuit": 256,
            },
        },
        "strategy_universe": {"all_strategy_rows": [_strategy(validated=validated)]},
        "universal_matrix": {
            "summary_rows": [
                {"label": "Source universe", "value": 41},
                {"label": "Watched instruments", "value": 19},
                {
                    "label": "Matrix scope",
                    "value": "all_sources_x_all_watched_markets_x_time_windows",
                },
            ]
        },
        "full_universe_search": {
            "summary_rows": [{"label": "Matrix rows scanned", "value": 6232}]
        },
        "source_network": {
            "source_row_count": 41,
            "category_row_count": 6,
            "trading_universe_row_count": 19,
        },
    }


def test_current_runtime_projection_is_honest_and_route_stable():
    payload = build_wave_f_public_view("data/runtime", generated_at=GENERATED_AT)

    assert payload["routes"] == {
        "pattern_recognition": PATTERN_ROUTE,
        "quantum_edge": QUANTUM_EDGE_ROUTE,
        "trading_strategies": STRATEGY_ROUTE,
    }
    assert payload["pattern_recognition"]["candidate_count"] == len(
        payload["pattern_recognition"]["candidates"]
    )
    assert payload["quantum_edge"]["proof_state"] == "quantum_edge_not_yet_proven"
    assert payload["quantum_edge"]["hardware_authenticity"][
        "hardware_experiment_completed"
    ] is False
    assert payload["trading_strategies"]["validated_strategy_count"] == 0
    validate_wave_f_public_view(payload)


def test_regenerated_edge_pattern_ids_do_not_change_public_candidate_identity():
    first_artifacts = _artifacts()
    second_artifacts = deepcopy(first_artifacts)
    first_artifacts["pattern_discovery"]["relationships"][0]["pattern_id"] = (
        "edge-pattern:ephemeral-first"
    )
    second_artifacts["pattern_discovery"]["relationships"][0]["pattern_id"] = (
        "edge-pattern:ephemeral-second"
    )

    first = build_wave_f_public_view_from_artifacts(
        first_artifacts, generated_at=GENERATED_AT
    )
    second = build_wave_f_public_view_from_artifacts(
        second_artifacts, generated_at=GENERATED_AT
    )

    first_id = next(
        row["candidate_id"]
        for row in first["pattern_recognition"]["candidates"]
        if row["discovery_origin"] == "classical_discovery"
    )
    second_id = next(
        row["candidate_id"]
        for row in second["pattern_recognition"]["candidates"]
        if row["discovery_origin"] == "classical_discovery"
    )
    assert first_id == second_id
    assert first_id.startswith("edge-pattern:")
    assert first["content_hash"] == second["content_hash"]


def test_clean_checkout_falls_back_to_tracked_qsase_pattern_intelligence(tmp_path):
    legacy = _legacy_relationship()
    qsase_finding = {
        "pattern_id": legacy["pattern_id"],
        "title": legacy["title"],
        "stage_key": "documented",
        "lifecycle_label": "Documented research finding",
        "source_chain": legacy["source_chain"],
        "market_affected": legacy["target_market"],
        "instrument_symbols": legacy["target_instruments"],
        "detected_signal": legacy["plain_english_question"],
        "what_qadam_thinks": legacy["what_qadam_thinks"],
        "evidence_quality_score": legacy["evidence_quality_score"],
        "confidence_score": legacy["confidence_score"],
        "what_would_confirm": legacy["what_would_confirm"],
        "what_blocks_trade": legacy["falsifiers"][0],
        "blockers": legacy["blocked_by"],
        "next_action": legacy["next_action"],
        "readiness": {"validated_edge": False},
    }
    (tmp_path / "qsase_pattern_intelligence.json").write_text(
        json.dumps({"findings": [qsase_finding]}),
        encoding="utf-8",
    )
    (tmp_path / "qadam_hybrid_candidates.jsonl").write_text(
        json.dumps(_hybrid_candidate()) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "qadam_independent_quantum_value_evaluations.jsonl").write_text(
        json.dumps(_evaluation()) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "qadam_independent_quantum_value_summary.json").write_text(
        json.dumps(_artifacts()["evaluation_summary"]),
        encoding="utf-8",
    )
    (tmp_path / "qadam_local_quantum_discovery_contract.json").write_text(
        json.dumps(_artifacts()["local_quantum"]),
        encoding="utf-8",
    )
    (tmp_path / "qsase_dashboard_strategy_universe.json").write_text(
        json.dumps(_artifacts()["strategy_universe"]),
        encoding="utf-8",
    )
    (tmp_path / "qsase_universal_source_price_matrix_dashboard_summary.json").write_text(
        json.dumps(_artifacts()["universal_matrix"]),
        encoding="utf-8",
    )
    (tmp_path / "qsase_full_universe_pattern_search_dashboard_summary.json").write_text(
        json.dumps(_artifacts()["full_universe_search"]),
        encoding="utf-8",
    )
    (tmp_path / "qsase_dashboard_source_network.json").write_text(
        json.dumps(_artifacts()["source_network"]),
        encoding="utf-8",
    )

    payload = build_wave_f_public_view(tmp_path, generated_at=GENERATED_AT)

    filters = {
        row["key"]: row["count"] for row in payload["pattern_recognition"]["filters"]
    }
    assert filters == {
        "all": 2,
        "classical_discovery": 1,
        "quantum_assisted_discovery": 0,
        "joint_discovery": 1,
    }
    classical = next(
        row
        for row in payload["pattern_recognition"]["candidates"]
        if row["discovery_origin"] == "classical_discovery"
    )
    assert classical["market"] == "Crude oil"
    assert classical["relationship"] == legacy["plain_english_question"]


def test_pattern_recognition_separates_classical_and_joint_origins():
    payload = build_wave_f_public_view_from_artifacts(
        _artifacts(), generated_at=GENERATED_AT
    )
    filters = {
        row["key"]: row["count"] for row in payload["pattern_recognition"]["filters"]
    }

    assert filters == {
        "all": 2,
        "classical_discovery": 1,
        "quantum_assisted_discovery": 0,
        "joint_discovery": 1,
    }
    joint = next(
        row
        for row in payload["pattern_recognition"]["candidates"]
        if row["discovery_origin"] == "joint_discovery"
    )
    assert joint["execution_mode_label"] == "Local quantum simulation"
    assert joint["hardware_receipt_verified"] is False
    assert joint["validation_contribution"] == "not_measurable"
    assert joint["evidence_label"] == "System test only"
    assert joint["research_score"]["display"] == "0.600"
    assert joint["research_score"]["is_probability"] is False
    assert "synthetic control data" in joint["potential_pattern_summary"]


def test_pattern_rows_explain_score_scope_strategy_fit_and_plain_states():
    payload = build_wave_f_public_view_from_artifacts(
        _artifacts(), generated_at=GENERATED_AT
    )
    pattern_view = payload["pattern_recognition"]
    classical = next(
        row
        for row in pattern_view["candidates"]
        if row["discovery_origin"] == "classical_discovery"
    )

    assert pattern_view["comparison_scope"]["source_count"] == 41
    assert pattern_view["comparison_scope"]["instrument_count"] == 19
    assert pattern_view["comparison_scope"]["matrix_row_count"] == 6232
    assert classical["research_score"]["display"] == "0.545"
    assert classical["research_score"]["is_probability"] is False
    assert classical["evidence_label"] == "Research idea, not yet proven"
    assert classical["blocker"].startswith("No untouched")
    assert classical["blocker"].endswith(".")
    assert classical["next_action"].startswith("Run")
    assert classical["next_action"].endswith(".")
    assert "potential relationship under study" in classical[
        "potential_pattern_summary"
    ]
    lens_ids = {row["lens_id"] for row in classical["strategy_lenses"]}
    assert "event_conditioned_lead_lag_repricing" in lens_ids
    assert "signal_generator" in lens_ids
    assert "entry_confirmation" in lens_ids
    assert classical["recommended_rank"] < next(
        row["recommended_rank"]
        for row in pattern_view["candidates"]
        if row["contract_fixture_only"] is True
    )


def test_quantum_edge_proof_ladder_keeps_simulation_partial():
    payload = build_wave_f_public_view_from_artifacts(
        _artifacts(), generated_at=GENERATED_AT
    )
    steps = {row["key"]: row for row in payload["quantum_edge"]["proof_ladder"]}

    assert steps["result_reproduced"]["state"] == "partial"
    assert steps["ibm_hardware_executed"]["state"] == "not_reached"
    assert steps["classical_baseline_beaten"]["state"] == "not_reached"
    assert steps["untouched_advantage_survived"]["state"] == "not_reached"
    assert payload["quantum_edge"]["completed_proof_step_count"] == 0
    assert payload["quantum_edge"]["comparison_summary"]["verdict"] == "not_measurable"
    assert payload["quantum_edge"]["comparison_summary"][
        "empirical_claim_allowed"
    ] is False
    assert payload["quantum_edge"]["strategy_influence"][
        "validated_strategy_count"
    ] == 0
    assert payload["quantum_edge"]["paper_outcome_lineage"][
        "attributed_paper_decision_count"
    ] == 0


def test_provider_proof_step_completes_only_after_backend_discovery():
    artifacts = _artifacts()
    artifacts["provider_readiness"].update(
        {
            "qctrl_authenticated": True,
            "ibm_configured_instance_accessible": True,
            "backend_discovered": True,
            "circuit_validation_available": True,
            "supported_device_count": 3,
            "blocker": "none",
        }
    )

    payload = build_wave_f_public_view_from_artifacts(
        artifacts, generated_at=GENERATED_AT
    )
    provider_step = next(
        row
        for row in payload["quantum_edge"]["proof_ladder"]
        if row["key"] == "provider_configured"
    )

    assert provider_step["state"] == "complete"
    assert "Access is ready" in provider_step["explanation"]
    assert "no hardware experiment was authorized or run" in provider_step[
        "explanation"
    ]
    authenticity = payload["quantum_edge"]["hardware_authenticity"]
    assert authenticity["ibm_instance_accessible"] is True
    assert authenticity["hardware_experiment_completed"] is False
    assert authenticity["provider_status_summary"].startswith(
        "Provider access is healthy"
    )
    provider_result = next(
        row
        for row in payload["quantum_edge"]["negative_results"]
        if row["title"].startswith("IBM hardware")
    )
    assert provider_result["title"] == "IBM hardware has not been run"
    assert "blocked" not in provider_result["explanation"].lower()
    assert "No hardware experiment has been authorized or submitted" in provider_result[
        "explanation"
    ]


def test_strategy_admission_requires_validated_pattern_lineage():
    held = build_wave_f_public_view_from_artifacts(
        _artifacts(validated=False), generated_at=GENERATED_AT
    )
    admitted = build_wave_f_public_view_from_artifacts(
        _artifacts(validated=True), generated_at=GENERATED_AT
    )

    assert held["trading_strategies"]["validated_strategy_count"] == 0
    assert held["trading_strategies"]["research_playbook_count"] == 1
    assert admitted["trading_strategies"]["validated_strategy_count"] == 1
    strategy = admitted["trading_strategies"]["admitted_strategies"][0]
    assert strategy["underlying_pattern_ids"] == ["pattern:classical-oil"]
    assert strategy["pattern_recognition_route"] == PATTERN_ROUTE


def test_unearned_hardware_and_quantum_edge_claims_are_rejected():
    payload = build_wave_f_public_view_from_artifacts(
        _artifacts(), generated_at=GENERATED_AT
    )
    hardware_tamper = deepcopy(payload)
    joint = next(
        row
        for row in hardware_tamper["pattern_recognition"]["candidates"]
        if row["discovery_origin"] == "joint_discovery"
    )
    joint["execution_mode_label"] = "IBM Quantum via Q-CTRL Fire Opal"
    with pytest.raises(ValueError, match="wave_f_unearned_hardware_label"):
        validate_wave_f_public_view(hardware_tamper)

    claim_tamper = deepcopy(payload)
    claim_tamper["quantum_edge"]["proof_state"] = "validated_quantum_contribution"
    with pytest.raises(ValueError, match="wave_f_unearned_quantum_edge_claim"):
        validate_wave_f_public_view(claim_tamper)


def test_public_projection_has_zero_dashboard_or_broker_authority():
    payload = build_wave_f_public_view_from_artifacts(
        _artifacts(), generated_at=GENERATED_AT
    )

    assert not any(payload["authority"].values())
    assert not any(payload["pattern_recognition"]["authority"].values())
    assert not any(payload["quantum_edge"]["authority"].values())
    assert not any(payload["trading_strategies"]["authority"].values())
    assert payload["quantum_edge"]["hardware_authenticity"]["provider_call_count"] == 0


def test_content_hash_and_forbidden_keys_are_tamper_evident():
    payload = build_wave_f_public_view_from_artifacts(
        _artifacts(), generated_at=GENERATED_AT
    )
    hash_tamper = deepcopy(payload)
    hash_tamper["pattern_recognition"]["headline"] = "tampered"
    with pytest.raises(ValueError, match="wave_f_content_hash_mismatch"):
        validate_wave_f_public_view(hash_tamper)

    forbidden = deepcopy(payload)
    forbidden["quantum_edge"]["raw_provider_response"] = {"value": "hidden"}
    forbidden["content_hash"] = payload["content_hash"]
    with pytest.raises(ValueError):
        validate_wave_f_public_view(forbidden)


def test_writer_exports_matching_runtime_and_site_artifacts(tmp_path):
    payload = build_wave_f_public_view_from_artifacts(
        _artifacts(), generated_at=GENERATED_AT
    )
    runtime = tmp_path / "runtime"
    site = tmp_path / "site"
    outputs = write_wave_f_public_view(
        payload,
        runtime_dir=runtime,
        site_root=site,
    )

    assert json.loads(outputs["runtime"].read_text(encoding="utf-8")) == payload
    assert json.loads(outputs["site"].read_text(encoding="utf-8")) == payload
