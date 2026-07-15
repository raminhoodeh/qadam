from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.qadam_quantum_edge_page_view_model import (
    GUIDANCE_OPERATING_MODEL,
    GUIDANCE_OUTCOME_STATES,
    GUIDANCE_OUTCOMES,
    GUIDANCE_PROOF_STEPS,
    GUIDANCE_QUESTIONS,
    GUIDANCE_TAKEAWAY,
    GUIDANCE_WORKFLOW_STEPS,
    PAGE_COPY,
    PRESENTATION_CONTRACT_VERSION,
    PURPOSE_PARAGRAPH,
    build_quantum_edge_page_view_model_from_sources,
    stable_hash,
    validate_quantum_edge_page_view_model,
    write_quantum_edge_page_view_model,
)


GENERATED_AT = "2026-07-13T18:00:00+00:00"
SHARED_MANIFEST = "a" * 64
HARDWARE_MANIFEST = "b" * 64


def _rehash(payload: dict) -> dict:
    material = {
        key: value for key, value in payload.items() if key not in {"generated_at", "content_hash"}
    }
    payload["content_hash"] = stable_hash(material)
    return payload


def _proof_ladder() -> list[dict]:
    return [
        {
            "key": "provider_configured",
            "label": "Provider configured",
            "state": "complete",
            "explanation": "The provider path is accessible.",
        },
        {
            "key": "ibm_hardware_executed",
            "label": "IBM hardware executed",
            "state": "not_reached",
            "explanation": "No IBM hardware result exists.",
        },
        {
            "key": "result_reproduced",
            "label": "Result reproduced",
            "state": "partial",
            "explanation": "The local simulator reproduced the control.",
        },
        {
            "key": "classical_baseline_beaten",
            "label": "Classical baseline beaten",
            "state": "not_reached",
            "explanation": "No fair matched comparison exists.",
        },
        {
            "key": "untouched_advantage_survived",
            "label": "Untouched-data advantage survived",
            "state": "not_reached",
            "explanation": "No eligible untouched holdout exists.",
        },
        {
            "key": "paper_decision_improved",
            "label": "Paper decision improved",
            "state": "not_reached",
            "explanation": "No governed paper decision changed.",
        },
    ]


def _wave_f() -> dict:
    payload = {
        "schema_version": "qadam.QuantumEdgeWaveFPublicView.v1",
        "artifact_type": "qadam_quantum_edge_wave_f_public_view",
        "generated_at": "2026-07-13T17:00:00+00:00",
        "quantum_edge": {
            "proof_state": "quantum_edge_not_yet_proven",
            "proof_ladder": _proof_ladder(),
            "strongest_evidence": {
                "title": "Classical and local quantum methods recovered a fixture",
                "summary": "This is a synthetic engineering control, not a market edge.",
                "verdict": "not_measurable",
            },
            "experiments": [
                {
                    "experiment_id": "local-quantum-control",
                    "title": "Local quantum simulation",
                    "kind": "quantum_simulator",
                    "state": "complete",
                    "result": "The known fixture was recovered.",
                    "boundary": "Simulator only; not IBM hardware.",
                }
            ],
            "comparison_summary": {
                "verdict": "not_measurable",
                "verdict_label": "Not measurable yet",
                "empirical_claim_allowed": False,
                "plain_english_summary": "No fair market-data comparison exists yet.",
            },
            "negative_results": [
                {
                    "title": "Independent value is not measurable",
                    "explanation": "Untouched evidence is missing.",
                }
            ],
            "hardware_authenticity": {
                "prepared_manifest_hash": HARDWARE_MANIFEST,
                "ibm_instance_accessible": True,
                "provider_call_count": 0,
                "hardware_execution_authorized": False,
                "hardware_job_submitted": False,
                "hardware_experiment_completed": False,
                "hardware_receipt_verified": False,
            },
            "strategy_influence": {
                "validated_strategy_count": 0,
                "strategy_family_ids": [],
                "summary": "No strategy changed because no contribution is validated.",
            },
            "paper_outcome_lineage": {
                "attributed_paper_decision_count": 0,
                "summary": "No paper decision is attributed to quantum evidence.",
            },
            "provenance": {
                "shared_manifest_hash": SHARED_MANIFEST,
                "hardware_manifest_hash": HARDWARE_MANIFEST,
                "candidate_ids": ["candidate:fixture"],
            },
            "authority": {"hardware_submission_allowed": False},
        },
        "authority": {"dashboard_command_authority": False},
    }
    return _rehash(payload)


def _public_lifecycle() -> list[dict]:
    states = [
        "candidate noticed",
        "experiment prepared",
        "experiment executed",
        "result reproduced",
        "evidence strengthened",
        "edge validated",
        "strategy influenced",
        "paper outcome observed",
    ]
    complete = {"candidate noticed", "experiment prepared", "result reproduced"}
    return [
        {
            "state": state,
            "status": "complete" if state in complete else "not reached",
            "explanation": f"Public lifecycle explanation for {state}.",
        }
        for state in states
    ]


def _wave_g() -> dict:
    payload = {
        "schema_version": "qadam.QuantumEdgeWaveGHybridLoop.v1",
        "artifact_type": "qadam_quantum_edge_wave_g_hybrid_loop",
        "generated_at": "2026-07-13T17:05:00+00:00",
        "evidence_date": "2026-07-13",
        "cycle_id": "wave-g-cycle:fixture",
        "status": "wave_g_cycle_complete_safe_idle",
        "validated_edge_admissions": [],
        "postmortems": [],
        "daily_stages": {
            "classical_discovery": {
                "state": "classical result reproduced",
                "shared_manifest_hash": SHARED_MANIFEST,
                "contract_fixture_only": True,
            },
            "local_quantum_simulation": {
                "state": "local quantum result reproduced",
                "shared_manifest_hash": SHARED_MANIFEST,
                "contract_fixture_only": True,
                "hardware_experiment_completed": False,
            },
            "hardware_experiment_preparation": {
                "state": "experiment prepared",
                "prepared_manifest_hash": HARDWARE_MANIFEST,
                "hardware_job_submitted_by_wave_g": False,
            },
        },
        "public_lifecycle": _public_lifecycle(),
        "paper_integration": {
            "strategy_count": 0,
            "risk_review_count": 0,
            "paperops_review_handoff_count": 0,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "route_contract": {
                "wave_g_calls_broker": False,
                "wave_g_submits_orders": False,
                "stages": ["Trading Strategy", "Akber filter", "PaperOps"],
            },
            "why_not": {
                "status": "no_paper_review_candidate",
                "reason": "No validated edge exists.",
                "read_only": True,
                "paper_order_created": False,
            },
            "authority": {"paper_order_allowed": False},
        },
        "telegram_brief": {
            "text": "The local control reproduced; nothing in this update can place an order.",
            "human_readable": True,
            "telegram_send_allowed": False,
            "telegram_command_authority": False,
        },
        "automation": {
            "provider_calls_this_cycle": 0,
            "hardware_submission_allowed": False,
            "forced_promotion_allowed": False,
            "forced_strategy_allowed": False,
            "forced_trade_allowed": False,
        },
        "authority": {"broker_write_allowed": False},
    }
    return _rehash(payload)


def _check(key: str, *, passed: bool, status: str, category: str) -> dict:
    return {
        "key": key,
        "category": category,
        "passed": passed,
        "status": status,
        "explanation": f"The {key.replace('_', ' ')} condition is recorded as {status}.",
    }


def _wave_h() -> dict:
    engineering_checks = [
        _check(
            f"engineering_check_{index}",
            passed=True,
            status="passed",
            category="engineering",
        )
        for index in range(1, 12)
    ]
    scientific_checks = [
        _check(
            "provider_accessible",
            passed=True,
            status="passed",
            category="hardware_evidence",
        ),
        _check(
            "provider_history_complete",
            passed=False,
            status="blocked",
            category="empirical_evidence",
        ),
        _check(
            "untouched_holdout_available",
            passed=False,
            status="blocked",
            category="empirical_evidence",
        ),
        _check(
            "ibm_hardware_result",
            passed=False,
            status="not_run",
            category="hardware_evidence",
        ),
        _check(
            "untouched_control_suite",
            passed=False,
            status="not_run",
            category="statistical_controls",
        ),
        _check(
            "matched_quantum_value_measured",
            passed=False,
            status="not_measurable",
            category="scientific_verdict",
        ),
    ]
    payload = {
        "schema_version": "qadam.QuantumEdgeWaveHCrudeOilCertification.v1",
        "artifact_type": "wave_h_crude_oil_pilot_certification",
        "generated_at": "2026-07-13T17:10:00+00:00",
        "status": "mechanism_certified_result_unproven",
        "mechanism_certified": True,
        "scientific_result_certified": False,
        "scientific_verdict": "not_measurable",
        "public_proof_state": "unproven",
        "proof_state_key": [
            {"state": "unproven", "current": True, "meaning": "No market edge is proven."},
            {"state": "classically_dominated", "current": False, "meaning": "Classical wins."},
        ],
        "certification": {
            "engineering_checks": engineering_checks,
            "engineering_pass_count": 11,
            "engineering_check_count": 11,
            "scientific_checks": scientific_checks,
            "scientific_pass_count": 1,
            "scientific_check_count": 6,
        },
        "engineering_fixture": {
            "contract_fixture_only": True,
            "shared_manifest_hash": SHARED_MANIFEST,
            "hardware_smoke_manifest_hash": HARDWARE_MANIFEST,
            "hardware_smoke_manifest_prepared": True,
            "provider_call_count": 0,
            "hardware_job_submitted": False,
            "hardware_experiment_completed": False,
        },
        "hardware_authorization_checkpoint": {
            "authorized": False,
            "engineering_manifest_hash": HARDWARE_MANIFEST,
            "provider_readiness_status": "device_probe_recorded",
            "provider_blocker": "none",
        },
        "pilot_manifest": {
            "pilot_id": "quantum-edge-pilot:crude-oil-v1",
            "schema_version": "qadam.QuantumEdgeCrudeOilPilotManifest.v1",
            "engineering_smoke_manifest_hash": HARDWARE_MANIFEST,
            "hardware_submission_authorized": False,
            "market_sleeve": "crude_oil",
            "authority": {"hardware_submission_allowed": False},
        },
        "evidence_truth": {
            "classified_window_count": 6232,
            "eligible_window_count": 0,
            "provider_row_count": 0,
            "completed_partition_count": 0,
        },
        "run_ledger": [
            {
                "run": "Ideal quantum simulation",
                "status": "engineering_control_reproduced",
                "fixture_only": True,
                "result": "Local result reproduced; this is not market proof.",
            }
        ],
        "controls": [],
        "downstream_truth": {
            "validated_edge_count": 0,
            "strategy_count": 0,
            "risk_review_count": 0,
            "paperops_review_handoff_count": 0,
            "paper_order_count": 0,
            "broker_write_count": 0,
        },
        "blockers": ["no_eligible_point_in_time_windows"],
        "next_actions": ["Build eligible untouched market evidence."],
        "authority": {"candidate_promotion_allowed": False},
    }
    return _rehash(payload)


def _sources() -> dict[str, dict]:
    return {"wave_f": _wave_f(), "wave_g": _wave_g(), "wave_h": _wave_h()}


def _make_fair_comparison_eligible(sources: dict[str, dict]) -> None:
    f_quantum = sources["wave_f"]["quantum_edge"]
    f_quantum["provenance"]["evaluation_policy_hash"] = "c" * 64
    f_hardware = f_quantum["hardware_authenticity"]
    f_hardware.update(
        {
            "hardware_execution_authorized": True,
            "hardware_job_submitted": True,
            "hardware_experiment_completed": True,
            "hardware_receipt_verified": True,
        }
    )

    g = sources["wave_g"]
    g["daily_stages"]["feature_construction"] = {
        "state": "point-in-time features ready",
        "point_in_time_checks_passed": True,
        "contract_fixture_only": False,
    }

    h = sources["wave_h"]
    h["engineering_fixture"].update(
        {
            "contract_fixture_only": False,
            "hardware_job_submitted": True,
            "hardware_experiment_completed": True,
        }
    )
    h["hardware_authorization_checkpoint"]["authorized"] = True
    h["evidence_truth"].update(
        {
            "eligible_window_count": 64,
            "leakage_violation_count": 0,
        }
    )
    h["pilot_manifest"].update(
        {
            "manifest_hash": "d" * 64,
            "research_question": "Do both methods improve the same five-day return forecast?",
            "evaluation_metric": "net directional accuracy after declared costs",
            "point_in_time_features": [{"key": "source_density"}],
            "matched_methods": {
                "classical": ["strongest frozen classical method"],
                "quantum": ["frozen quantum-assisted method"],
            },
            "outcomes": ["five-day net return"],
            "chronology": {
                "training": "expanding chronological training",
                "validation": "later chronological calibration with embargo",
                "untouched_holdout": "final chronological period",
            },
            "controls": ["placebo target", "multiple-testing correction"],
            "policy": {
                "false_discovery_rate_alpha": 0.05,
                "transaction_cost_bps": 10.0,
                "minimum_holdout_observations": 32,
                "comparable_tuning_budget": "same frozen search budget",
                "statistical_rule": "false-discovery-adjusted holdout comparison",
            },
        }
    )
    for source in sources.values():
        _rehash(source)


def _make_validated_quantum_positive(sources: dict[str, dict]) -> None:
    _make_fair_comparison_eligible(sources)
    comparison = sources["wave_f"]["quantum_edge"]["comparison_summary"]
    comparison.update(
        {
            "verdict": "quantum_strengthened",
            "verdict_label": "Quantum positive",
            "empirical_claim_allowed": True,
            "plain_english_summary": (
                "The quantum-assisted method added information under the frozen comparison."
            ),
        }
    )
    h = sources["wave_h"]
    h["public_proof_state"] = "validated"
    h["scientific_verdict"] = "validated"
    h["scientific_result_certified"] = True
    for row in h["certification"]["scientific_checks"]:
        row["passed"] = True
        row["status"] = "passed"
        row["explanation"] = "The condition passed the frozen scientific contract."
    h["certification"]["scientific_pass_count"] = 6
    for source in sources.values():
        _rehash(source)


def test_ready_projection_has_one_truth_and_three_sections():
    payload = build_quantum_edge_page_view_model_from_sources(
        _sources(),
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "ready"
    assert payload["copy_version"] == "quantum-edge-elegant-simplification-v1"
    assert payload["contract_version"] == PRESENTATION_CONTRACT_VERSION
    assert len(payload["render_contract_hash"]) == 64
    assert payload["page_copy"] == PAGE_COPY
    assert payload["page_explainer"]["eyebrow"] == "Quantum Benchmark Framework"
    assert payload["page_explainer"]["purpose_paragraph"] == PURPOSE_PARAGRAPH
    assert payload["page_explainer"]["guidance"]["workflow_steps"] == GUIDANCE_WORKFLOW_STEPS
    assert payload["page_explainer"]["guidance"]["operating_model"] == GUIDANCE_OPERATING_MODEL
    current_capability = payload["page_explainer"]["guidance"]["current_capability"]
    assert current_capability["local_simulation_reproduced"] is True
    assert current_capability["provider_accessible"] is True
    assert current_capability["hardware_authorized"] is False
    assert current_capability["hardware_submitted"] is False
    assert current_capability["hardware_completed"] is False
    assert "No IBM hardware experiment has been authorized" in current_capability["body"]
    assert payload["page_explainer"]["guidance"]["questions"] == GUIDANCE_QUESTIONS
    assert payload["page_explainer"]["guidance"]["proof_steps"] == GUIDANCE_PROOF_STEPS
    assert payload["page_explainer"]["guidance"]["possible_outcomes"] == GUIDANCE_OUTCOMES
    assert payload["page_explainer"]["guidance"]["outcome_states"] == GUIDANCE_OUTCOME_STATES
    assert payload["page_explainer"]["guidance"]["takeaway"] == GUIDANCE_TAKEAWAY
    assert [step["question"] for step in GUIDANCE_PROOF_STEPS] == GUIDANCE_QUESTIONS
    assert len({step["key"] for step in GUIDANCE_PROOF_STEPS}) == 6
    assert len({step["key"] for step in GUIDANCE_WORKFLOW_STEPS}) == 5
    assert len({state["key"] for state in GUIDANCE_OUTCOME_STATES}) == 5
    assert payload["page_explainer"]["section_order"] == [
        "evidence",
        "consequence",
        "answer",
    ]
    axes = payload["state_axes"]
    assert set(axes) == {"proof", "comparison", "execution", "downstream", "freshness"}
    assert axes["proof"]["key"] == "unproven"
    assert axes["comparison"]["key"] == "not_measurable"
    assert axes["comparison"]["eligible"] is False
    assert len(axes["comparison"]["eligibility_checks"]) == 8
    assert axes["execution"]["key"] == "provider_ready_hardware_not_run"
    assert axes["execution"]["local_simulation_reproduced"] is True
    assert axes["execution"]["provider_accessible"] is True
    assert axes["execution"]["hardware_completed"] is False
    assert axes["downstream"]["key"] == "no_downstream_change"
    assert axes["downstream"]["summary"] == (
        "No validated strategy or governed paper decision has changed because of quantum evidence."
    )
    assert axes["freshness"]["key"] == "current"

    presentation = payload["presentation"]
    assert presentation["section_order"] == ["evidence", "consequence", "answer"]
    assert all(
        presentation["rows"][key]["collapsed_by_default"] is True
        for key in presentation["section_order"]
    )
    assert presentation["rows"]["evidence"]["summary"] == (
        "The experimental loop reproduced locally; provider access is ready, IBM "
        "hardware has not run, and no fair untouched market comparison is available."
    )
    assert presentation["rows"]["consequence"]["summary"] == axes["downstream"]["summary"]
    assert presentation["rows"]["answer"]["summary"] == (
        "Unproven — the engineering pathway works, but market-level quantum "
        "advantage is not measurable yet."
    )
    assert [row["value"] for row in presentation["evidence"]["facts"]] == [
        "Same frozen evidence",
        "Local simulator reproduced / hardware not run",
        "Untouched comparison unavailable",
    ]
    assert "source_count" not in presentation["evidence"]["shared_basis"]
    assert "method_count" not in presentation["evidence"]["conventional_lane"]
    assert [row["label"] for row in presentation["impact"]["gates"]] == [
        "Does the experiment work?",
        "Does hardware evidence exist?",
        "Does the market comparison hold up?",
        "Did it improve a strategy or paper decision?",
    ]
    assert [row["state"] for row in presentation["impact"]["gates"]] == [
        "passed",
        "not_run",
        "not_run",
        "waiting",
    ]
    assert [row["value"] for row in presentation["verdict"]["metrics"]] == [
        "Reproduced locally",
        "Not measurable yet",
        "No strategy or paper-decision change",
    ]
    assert presentation["verdict"]["summary"] == (
        "Qadam's hybrid classical-quantum experimental pathway is implemented and "
        "reproducible locally. A genuine market-level quantum advantage remains "
        "unproven because no authorized IBM hardware result, untouched market "
        "comparison, or forward-validated strategy impact exists yet."
    )
    assert presentation["technical_record"]["closed_by_default"] is True
    assert {row["path"] for row in presentation["technical_record"]["index"]} >= {
        "answer.proof_ladder",
        "evidence.experiments",
        "consequence.hybrid_lifecycle",
        "source_artifacts",
        "freshness",
    }
    assert payload["answer"] and payload["evidence"] and payload["consequence"]
    assert payload["answer"]["proof_state"] == "unproven"
    assert payload["answer"]["scientific_verdict"] == "not_measurable"
    assert payload["answer"]["engineering_checks"]["score_label"] == "11/11"
    assert payload["answer"]["market_proof_prerequisites"]["score_label"] == "1/6"
    assert payload["source_lineage"]["semantic_coherence_passed"] is True
    assert validate_quantum_edge_page_view_model(payload) == []


def test_projection_is_deterministic_and_generated_at_is_not_proof_material():
    sources = _sources()
    first = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at="2026-07-13T18:00:00+00:00",
    )
    second = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at="2026-07-13T18:01:00+00:00",
    )

    assert first["generated_at"] != second["generated_at"]
    assert first["content_hash"] == second["content_hash"]
    first_without_time = {key: value for key, value in first.items() if key != "generated_at"}
    second_without_time = {key: value for key, value in second.items() if key != "generated_at"}
    assert first_without_time == second_without_time


def test_fair_comparison_requires_all_eight_explicit_protocol_facts():
    sources = _sources()
    _make_fair_comparison_eligible(sources)

    eligible = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )
    checks = eligible["state_axes"]["comparison"]["eligibility_checks"]
    assert len(checks) == 8
    assert all(row["passed"] is True for row in checks)
    assert eligible["state_axes"]["comparison"]["eligible"] is True

    sources["wave_h"]["pilot_manifest"].pop("evaluation_metric")
    _rehash(sources["wave_h"])
    missing_metric = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )
    checks = missing_metric["state_axes"]["comparison"]["eligibility_checks"]
    metric_check = next(
        row for row in checks if row["key"] == "same_metric_cost_and_statistical_rule"
    )
    assert metric_check["passed"] is False
    assert missing_metric["state_axes"]["comparison"]["eligible"] is False
    assert missing_metric["state_axes"]["comparison"]["key"] == "not_measurable"


def test_state_axes_are_independent_and_presentation_cannot_drift():
    payload = build_quantum_edge_page_view_model_from_sources(
        _sources(),
        generated_at=GENERATED_AT,
    )
    assert [
        payload["state_axes"][key]["key"]
        for key in ["proof", "comparison", "execution", "downstream", "freshness"]
    ] == [
        "unproven",
        "not_measurable",
        "provider_ready_hardware_not_run",
        "no_downstream_change",
        "current",
    ]

    payload["state_axes"]["execution"]["key"] = "hardware_verified"
    _rehash(payload)
    errors = validate_quantum_edge_page_view_model(payload)
    assert "quantum_edge_page_state_axes_invalid" in errors

    payload = build_quantum_edge_page_view_model_from_sources(
        _sources(),
        generated_at=GENERATED_AT,
    )
    payload["presentation"]["rows"]["answer"]["summary"] = "Unsupported copy"
    _rehash(payload)
    errors = validate_quantum_edge_page_view_model(payload)
    assert "quantum_edge_page_presentation_invalid" in errors


def test_hardware_source_contradiction_fails_all_presentation_axes_closed():
    sources = _sources()
    sources["wave_f"]["quantum_edge"]["hardware_authenticity"]["hardware_experiment_completed"] = (
        True
    )
    _rehash(sources["wave_f"])

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )
    assert payload["projection_status"] == "source_truth_conflict"
    assert (
        "hardware_state_conflict:hardware_completed" in payload["source_lineage"]["semantic_errors"]
    )
    assert payload["state_axes"]["comparison"]["key"] == "unavailable"
    assert payload["state_axes"]["freshness"]["key"] == "contradictory"
    assert payload["state_axes"]["execution"]["hardware_completed"] is None
    assert payload["state_axes"]["downstream"]["strategy_count"] is None
    assert all(
        gate["state"] == "unavailable" for gate in payload["presentation"]["impact"]["gates"]
    )


def test_passed_waiting_contradiction_fails_closed_without_false_numerator():
    sources = _sources()
    check = sources["wave_h"]["certification"]["scientific_checks"][0]
    check["passed"] = True
    check["status"] = "waiting"
    check["explanation"] = "IBM provider readiness has not yet been certified."
    _rehash(sources["wave_h"])

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "source_truth_conflict"
    assert payload["answer"]["proof_state"] == "unproven"
    assert payload["answer"]["scientific_verdict"] == "unavailable"
    assert payload["answer"]["engineering_checks"]["score_label"] == "11/11"
    market = payload["answer"]["market_proof_prerequisites"]
    assert market["available"] is False
    assert market["pass_count"] is None
    assert market["score_label"] == "Unavailable"
    public_check = next(row for row in market["checks"] if row["key"] == "provider_accessible")
    assert public_check["passed"] is None
    assert public_check["status"] == "source_truth_conflict"
    assert any(
        error.startswith("semantic_contradiction:scientific_checks:provider_accessible")
        for error in payload["source_lineage"]["semantic_errors"]
    )
    assert validate_quantum_edge_page_view_model(payload) == []


def test_passed_not_certified_explanation_is_also_a_conflict():
    sources = _sources()
    check = sources["wave_h"]["certification"]["scientific_checks"][0]
    check["explanation"] = "This provider path is not certified."
    _rehash(sources["wave_h"])

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "source_truth_conflict"
    assert any(
        error.endswith("provider_accessible:passed_vs_explanation")
        for error in payload["source_lineage"]["semantic_errors"]
    )


def test_recovered_provider_cannot_coexist_with_blocked_access_copy():
    sources = _sources()
    sources["wave_f"]["quantum_edge"]["negative_results"].append(
        {
            "title": "IBM hardware access is blocked",
            "explanation": "A stale provider blocker.",
        }
    )
    _rehash(sources["wave_f"])

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "source_truth_conflict"
    assert (
        "provider_readiness_conflict:wave_f_negative_evidence"
        in payload["source_lineage"]["semantic_errors"]
    )
    assert payload["answer"]["market_proof_prerequisites"]["pass_count"] is None


def test_classical_preferred_is_comparison_state_while_proof_remains_unproven():
    sources = _sources()
    _make_fair_comparison_eligible(sources)
    comparison = sources["wave_f"]["quantum_edge"]["comparison_summary"]
    comparison.update(
        {
            "verdict": "classical_preferred",
            "verdict_label": "Classical preferred",
            "empirical_claim_allowed": True,
            "plain_english_summary": (
                "The conventional method matched or beat the quantum-assisted method."
            ),
        }
    )
    _rehash(sources["wave_f"])

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "ready"
    assert payload["state_axes"]["proof"]["key"] == "unproven"
    assert payload["state_axes"]["comparison"]["key"] == "classical_preferred"
    assert payload["state_axes"]["comparison"]["label"] == "Classical preferred"
    assert payload["state_axes"]["execution"]["key"] == "hardware_verified"
    assert payload["presentation"]["verdict"]["proof_state"] == "unproven"
    assert payload["presentation"]["verdict"]["comparison_state"] == ("classical_preferred")
    assert payload["evidence"]["provenance"]["raw_public_proof_state"] == "unproven"


def test_proof_can_advance_without_rederiving_the_comparison_axis():
    sources = _sources()
    _make_fair_comparison_eligible(sources)
    comparison = sources["wave_f"]["quantum_edge"]["comparison_summary"]
    comparison.update(
        {
            "verdict": "quantum_strengthened",
            "verdict_label": "Quantum positive",
            "empirical_claim_allowed": True,
        }
    )
    _rehash(sources["wave_f"])

    unproven = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )
    assert unproven["state_axes"]["proof"]["key"] == "unproven"
    assert unproven["state_axes"]["comparison"]["key"] == "quantum_positive"

    sources["wave_h"]["public_proof_state"] = "provisional"
    sources["wave_h"]["scientific_verdict"] = "quantum_strengthened"
    _rehash(sources["wave_h"])
    provisional = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )
    assert provisional["state_axes"]["proof"]["key"] == "provisional"
    assert provisional["state_axes"]["comparison"] == unproven["state_axes"]["comparison"]
    assert provisional["state_axes"]["execution"] == unproven["state_axes"]["execution"]


def test_validated_proof_and_quantum_positive_comparison_are_separate_axes():
    sources = _sources()
    _make_validated_quantum_positive(sources)

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["state_axes"]["proof"] == {
        "key": "validated",
        "label": "Validated",
        "fact_refs": ["answer.raw_proof_state", "answer.historical_proof_state"],
    }
    assert payload["state_axes"]["comparison"]["key"] == "quantum_positive"
    assert payload["state_axes"]["execution"]["key"] == "hardware_verified"
    assert payload["state_axes"]["freshness"]["key"] == "current"
    assert payload["presentation"]["verdict"]["proof_state"] == "validated"
    assert payload["presentation"]["verdict"]["comparison_state"] == ("quantum_positive")


def test_decayed_freshness_preserves_historical_proof_and_execution_axes():
    sources = _sources()
    _make_validated_quantum_positive(sources)
    h = sources["wave_h"]
    h["prior_public_proof_state"] = "validated"
    h["public_proof_state"] = "decayed"
    h["scientific_verdict"] = "decayed"
    _rehash(h)

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "ready"
    assert payload["answer"]["raw_proof_state"] == "decayed"
    assert payload["answer"]["historical_proof_state"] == "validated"
    assert payload["state_axes"]["proof"]["key"] == "validated"
    assert payload["state_axes"]["comparison"]["key"] == "quantum_positive"
    assert payload["state_axes"]["execution"]["key"] == "hardware_verified"
    assert payload["state_axes"]["freshness"]["key"] == "decayed"
    assert payload["state_axes"]["freshness"]["current_claim_allowed"] is False
    assert payload["presentation"]["verdict"]["proof_state"] == "validated"
    assert payload["presentation"]["verdict"]["freshness_state"] == "decayed"
    assert (
        "historical proof and execution record remains intact"
        in payload["presentation"]["verdict"]["summary"]
    )


def test_manifest_lineage_conflict_fails_closed():
    sources = _sources()
    sources["wave_g"]["daily_stages"]["local_quantum_simulation"]["shared_manifest_hash"] = "c" * 64
    _rehash(sources["wave_g"])

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "source_truth_conflict"
    assert (
        "evidence_identity_conflict:shared_manifest_hash"
        in payload["source_lineage"]["semantic_errors"]
    )
    assert payload["answer"]["market_proof_prerequisites"]["pass_count"] is None


def test_content_hash_tamper_fails_closed_and_is_not_silently_accepted():
    sources = _sources()
    sources["wave_h"]["status"] = "tampered-without-rehash"

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "source_truth_conflict"
    assert "source_content_hash_mismatch:wave_h" in payload["source_lineage"]["integrity_errors"]
    wave_h_lineage = next(
        row for row in payload["source_artifacts"] if row["source_id"] == "wave_h"
    )
    assert wave_h_lineage["content_hash_verified"] is False


def test_missing_source_is_unavailable_and_never_marked_verified():
    sources = _sources()
    sources["wave_g"] = {}

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at=GENERATED_AT,
    )

    assert payload["projection_status"] == "source_unavailable"
    assert payload["answer"]["proof_state"] == "unproven"
    assert payload["answer"]["scientific_verdict"] == "unavailable"
    assert payload["state_axes"]["freshness"]["key"] == "unavailable"
    wave_g_lineage = next(
        row for row in payload["source_artifacts"] if row["source_id"] == "wave_g"
    )
    assert wave_g_lineage["content_hash_verified"] is False
    assert "source_missing:wave_g" in payload["source_lineage"]["integrity_errors"]


def test_stale_sources_fail_closed_only_after_coherence_passes():
    payload = build_quantum_edge_page_view_model_from_sources(
        _sources(),
        generated_at="2026-07-25T18:00:00+00:00",
    )

    assert payload["projection_status"] == "source_stale"
    assert payload["freshness"]["semantic_coherence_passed"] is True
    assert payload["freshness"]["stale_source_ids"] == ["wave_f", "wave_g", "wave_h"]
    assert payload["answer"]["proof_state"] == "unproven"
    assert payload["answer"]["scientific_verdict"] == "unavailable"
    assert payload["state_axes"]["proof"]["key"] == "unproven"
    assert payload["state_axes"]["execution"]["key"] == ("provider_ready_hardware_not_run")
    assert payload["state_axes"]["freshness"]["key"] == "stale"
    assert payload["state_axes"]["freshness"]["current_claim_allowed"] is False


def test_stale_freshness_does_not_rewrite_validated_proof_or_execution():
    sources = _sources()
    _make_validated_quantum_positive(sources)

    payload = build_quantum_edge_page_view_model_from_sources(
        sources,
        generated_at="2026-07-25T18:00:00+00:00",
    )

    assert payload["projection_status"] == "source_stale"
    assert payload["answer"]["proof_state"] == "unproven"
    assert payload["state_axes"]["proof"]["key"] == "validated"
    assert payload["state_axes"]["execution"]["key"] == "hardware_verified"
    assert payload["state_axes"]["freshness"]["key"] == "stale"
    assert payload["state_axes"]["comparison"]["key"] == "unavailable"
    assert payload["presentation"]["verdict"]["proof_state"] == "validated"
    assert payload["presentation"]["verdict"]["freshness_state"] == "stale"


def test_secret_and_authority_bearing_sources_are_rejected_before_projection():
    secret_sources = _sources()
    secret_sources["wave_h"]["token"] = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    _rehash(secret_sources["wave_h"])
    with pytest.raises(ValueError, match="unsafe_quantum_edge_source"):
        build_quantum_edge_page_view_model_from_sources(
            secret_sources,
            generated_at=GENERATED_AT,
        )

    authority_sources = _sources()
    authority_sources["wave_g"]["authority"]["broker_write_allowed"] = True
    _rehash(authority_sources["wave_g"])
    with pytest.raises(ValueError, match="authority_escalated"):
        build_quantum_edge_page_view_model_from_sources(
            authority_sources,
            generated_at=GENERATED_AT,
        )

    detached_authority_sources = _sources()
    detached_authority_sources["wave_f"]["paper_order_allowed"] = True
    _rehash(detached_authority_sources["wave_f"])
    with pytest.raises(ValueError, match="authority_field_escalated"):
        build_quantum_edge_page_view_model_from_sources(
            detached_authority_sources,
            generated_at=GENERATED_AT,
        )


def test_writer_exports_byte_equivalent_runtime_and_site_mirrors(tmp_path):
    payload = build_quantum_edge_page_view_model_from_sources(
        _sources(),
        generated_at=GENERATED_AT,
    )
    outputs = write_quantum_edge_page_view_model(
        payload,
        runtime_dir=tmp_path / "runtime",
        site_root=tmp_path / "site",
    )

    runtime_payload = json.loads(outputs["runtime"].read_text(encoding="utf-8"))
    site_payload = json.loads(outputs["site"].read_text(encoding="utf-8"))
    assert runtime_payload == site_payload == payload
    assert runtime_payload["content_hash"] == payload["content_hash"]


def test_aggregator_source_contains_no_provider_research_or_trading_client_calls():
    root = Path(__file__).resolve().parents[1]
    source = (root / "orchestrator/qadam_quantum_edge_page_view_model.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "requests.",
        "httpx.",
        "qiskit_ibm_runtime",
        "paperops_alpaca_paper_post",
        "run_classical_discovery",
        "QiskitLocalQuantumDiscoveryBackend",
    ):
        assert forbidden not in source
