from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from orchestrator.qadam_wave_g_hybrid_loop import (
    AUTOMATION_STAGES,
    PUBLIC_LIFECYCLE_STATES,
    WaveGBudgets,
    WaveGInterrupted,
    build_guarded_paper_integration,
    build_postmortems_and_proposals,
    build_validated_edge_admissions,
    load_wave_g_artifacts,
    run_wave_g_cycle,
    validate_wave_g_broker_boundary,
    validate_wave_g_payload,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-07-12T12:00:00+00:00"


def _pattern(candidate_id: str = "candidate:validated") -> dict:
    return {
        "candidate_id": candidate_id,
        "title": "Validated crude-oil repricing relationship",
        "discovery_origin": "joint_discovery",
        "validation_contribution": "quantum_strengthened",
        "validated_edge": True,
        "contract_fixture_only": False,
        "empirical_evidence_count": 80,
        "strategy_family_id": "crude_oil_energy_security_disruption",
        "market": "crude oil repricing",
        "instruments": ["BNO"],
    }


def _evaluation(candidate_id: str = "candidate:validated") -> dict:
    return {
        "candidate_id": candidate_id,
        "validation_contribution": "quantum_strengthened",
        "empirical_claim_allowed": True,
        "holdout_manifest_hash": f"holdout:{candidate_id}",
        "training_validation_manifest_hash": f"training:{candidate_id}",
        "thresholds_frozen_at": "2026-06-01T00:00:00+00:00",
    }


def _operational_context(*, risk_ready: bool = True) -> dict:
    return {
        "akber_context_complete": True,
        "akber_missing_inputs": [],
        "forward_shadow_validation": {
            "state": "passed_on_matured_outcomes",
            "complete_outcome_count": 30,
            "leakage_audit_passed": True,
            "costs_included": True,
        },
        "risk_review": {
            "paper_mode_confirmed": risk_ready,
            "kill_switch_clear": risk_ready,
            "source_freshness_clear": risk_ready,
            "duplicate_exposure_clear": risk_ready,
            "notional_within_policy_cap": risk_ready,
            "qctrl_paper_consultation_satisfied": risk_ready,
        },
    }


def _artifacts(
    *,
    validated: bool = True,
    fixture: bool = False,
    risk_ready: bool = True,
    with_outcome: bool = False,
) -> dict:
    pattern = _pattern()
    pattern["validated_edge"] = validated
    pattern["contract_fixture_only"] = fixture
    evaluation = _evaluation()
    if not validated:
        evaluation["empirical_claim_allowed"] = False
        evaluation["validation_contribution"] = "not_measurable"
        pattern["validation_contribution"] = "not_measurable"
    outcomes = []
    if with_outcome:
        outcomes.append(
            {
                "outcome_id": "paper-outcome:1",
                "strategy_hypothesis_id": "placeholder",
                "outcome_matured": True,
                "result": "paper trade closed with a small gain",
                "classical_evidence_summary": "Shipping evidence arrived before price confirmation.",
                "quantum_contribution_summary": "The validated nonlinear interaction raised research priority.",
                "strategy_logic_summary": "The oil disruption playbook translated the edge into a testable thesis.",
                "akber_and_risk_summary": "Akber and risk held until confirmation and limits passed.",
                "execution_quality_summary": "The paper fill stayed within the expected spread.",
                "market_movement_summary": "Oil repriced after the observed disruption intensified.",
            }
        )
    return {
        "wave_f": {"pattern_recognition": {"candidates": [pattern]}},
        "hybrid_candidates": [
            {
                "candidate_id": pattern["candidate_id"],
                "contract_fixture_only": fixture,
                "empirical_evidence_count": pattern["empirical_evidence_count"],
            }
        ],
        "evaluations": [evaluation],
        "evaluation_summary": {},
        "source_rows": [
            {"source_key": "acled", "freshness_state": "fresh"},
            {"source_key": "ais_maritime", "freshness_state": "fresh"},
        ],
        "point_in_time": {"status": "passed"},
        "feature_manifest": {
            "shared_manifest_hash": "shared-manifest",
            "contract_fixture_only": False,
        },
        "classical_discovery": {
            "shared_manifest_hash": "shared-manifest",
            "contract_fixture_only": False,
            "method_results": [{"method": "tree"}],
        },
        "local_quantum": {
            "status": "local_quantum_discovery_ready",
            "shared_manifest_hash": "shared-manifest",
            "contract_fixture_only": False,
            "ideal_result": {"circuit_evaluation_count": 100},
            "finite_shot_result": {"circuit_evaluation_count": 100},
        },
        "hardware_public": {
            "manifest_hash": "prepared-manifest",
            "lifecycle_status": "prepared",
            "provider_call_count": 0,
            "hardware_experiment_completed": False,
        },
        "operational_context": {
            "candidates": {
                pattern["candidate_id"]: _operational_context(risk_ready=risk_ready)
            }
        },
        "paper_outcomes": outcomes,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _write_runtime(runtime: Path, artifacts: dict) -> None:
    _write_json(runtime / "qadam_quantum_edge_wave_f_public_view.json", artifacts["wave_f"])
    _write_jsonl(runtime / "qadam_hybrid_candidates.jsonl", artifacts["hybrid_candidates"])
    _write_jsonl(
        runtime / "qadam_independent_quantum_value_evaluations.jsonl",
        artifacts["evaluations"],
    )
    _write_json(
        runtime / "qadam_independent_quantum_value_summary.json",
        artifacts["evaluation_summary"],
    )
    _write_jsonl(runtime / "qadam_source_operational_state.jsonl", artifacts["source_rows"])
    _write_json(runtime / "qadam_point_in_time_evidence_checks.json", artifacts["point_in_time"])
    _write_json(
        runtime / "qadam_quantum_discovery_manifest_contract.json",
        artifacts["feature_manifest"],
    )
    _write_json(
        runtime / "qadam_classical_discovery_contract.json",
        artifacts["classical_discovery"],
    )
    _write_json(
        runtime / "qadam_local_quantum_discovery_contract.json",
        artifacts["local_quantum"],
    )
    _write_json(
        runtime / "qadam_fire_opal_ibm_discovery" / "prepared.public.json",
        artifacts["hardware_public"],
    )
    _write_json(
        runtime / "qadam_quantum_edge_wave_g_operational_context.json",
        artifacts["operational_context"],
    )
    _write_jsonl(
        runtime / "qadam_quantum_edge_wave_g_paper_outcomes.jsonl",
        artifacts["paper_outcomes"],
    )


def test_current_runtime_remains_safe_idle_when_optional_artifacts_are_absent():
    artifacts = load_wave_g_artifacts(ROOT / "data/runtime")
    admitted, rejected = build_validated_edge_admissions(
        artifacts,
        generated_at=GENERATED_AT,
        budgets=WaveGBudgets(),
    )

    assert admitted == []
    assert isinstance(rejected, list)
    integration = build_guarded_paper_integration(admitted, generated_at=GENERATED_AT)
    assert integration["strategy_count"] == 0
    assert integration["paperops_review_handoff_count"] == 0
    assert integration["paper_order_created_count"] == 0
    assert integration["broker_write_count"] == 0


def test_engineering_fixture_is_not_admitted():
    admitted, rejected = build_validated_edge_admissions(
        _artifacts(fixture=True),
        generated_at=GENERATED_AT,
        budgets=WaveGBudgets(),
    )

    assert admitted == []
    assert rejected
    assert any(
        "engineering fixture cannot enter a trading strategy" in row["blockers"]
        for row in rejected
    )


def test_validated_edge_routes_through_every_review_without_creating_order():
    artifacts = _artifacts()
    admitted, rejected = build_validated_edge_admissions(
        artifacts,
        generated_at=GENERATED_AT,
        budgets=WaveGBudgets(),
    )
    assert len(admitted) == 1
    assert rejected == []

    integration = build_guarded_paper_integration(admitted, generated_at=GENERATED_AT)

    assert integration["strategy_count"] == 1
    assert integration["akber"]["pass_count"] == 1
    assert integration["shadow"]["shadow_support_count"] == 1
    assert integration["router"]["paper_review_candidate_count"] == 1
    assert integration["risk_review_count"] == 1
    assert integration["paperops_review_handoff_count"] == 1
    assert integration["paper_order_created_count"] == 0
    assert integration["broker_write_count"] == 0
    pipeline = integration["pipeline_records"][0]
    assert [row["stage"] for row in pipeline["stages"]] == [
        "Trading Strategy",
        "Akber filter",
        "forward shadow validation",
        "Router",
        "Risk",
        "guarded PaperOps",
        "Alpaca Paper",
    ]
    assert pipeline["quantum_role"] == "documented validated strategy evidence only"


def test_risk_can_hold_but_quantum_cannot_size_or_approve():
    artifacts = _artifacts(risk_ready=False)
    admitted, _ = build_validated_edge_admissions(
        artifacts,
        generated_at=GENERATED_AT,
        budgets=WaveGBudgets(),
    )
    integration = build_guarded_paper_integration(admitted, generated_at=GENERATED_AT)

    review = integration["risk_reviews"][0]
    assert review["state"] == "held_by_risk_review"
    assert review["position_size_created"] is False
    assert review["risk_approval_created"] is False
    assert integration["paperops_review_handoff_count"] == 0
    assert all(value is False for value in review["authority"].values())


def test_postmortem_keeps_six_attribution_factors_and_governed_proposals():
    artifacts = _artifacts(with_outcome=True)
    admitted, _ = build_validated_edge_admissions(
        artifacts,
        generated_at=GENERATED_AT,
        budgets=WaveGBudgets(),
    )
    integration = build_guarded_paper_integration(admitted, generated_at=GENERATED_AT)
    artifacts["paper_outcomes"][0]["strategy_hypothesis_id"] = integration[
        "strategy_hypotheses"
    ][0]["strategy_hypothesis_id"]

    postmortems, proposals = build_postmortems_and_proposals(
        artifacts,
        integration,
        generated_at=GENERATED_AT,
        budgets=WaveGBudgets(),
    )

    assert len(postmortems) == 1
    assert list(postmortems[0]["attribution"]) == [
        "classical_evidence",
        "quantum_contribution",
        "strategy_logic",
        "akber_and_risk",
        "execution_quality",
        "market_movement",
    ]
    assert {row["proposal_type"] for row in proposals} == {
        "feature",
        "experiment",
        "strategy",
    }
    assert all(row["automatic_application_allowed"] is False for row in proposals)
    assert all(row["human_review_required"] is True for row in proposals)


def test_cycle_is_resumable_idempotent_budgeted_and_public_safe(tmp_path: Path):
    runtime = tmp_path / "runtime"
    site = tmp_path / "site"
    _write_runtime(runtime, _artifacts())

    with pytest.raises(WaveGInterrupted, match="feature_construction"):
        run_wave_g_cycle(
            runtime,
            site_root=site,
            generated_at=GENERATED_AT,
            evidence_date="2026-07-12",
            interrupt_after_stage="feature_construction",
        )

    payload = run_wave_g_cycle(
        runtime,
        site_root=site,
        generated_at="2026-07-12T12:05:00+00:00",
        evidence_date="2026-07-12",
    )
    repeated = run_wave_g_cycle(
        runtime,
        site_root=site,
        generated_at="2026-07-12T12:10:00+00:00",
        evidence_date="2026-07-12",
    )

    assert payload == repeated
    assert payload["automation"]["resumed_from_checkpoint"] is True
    assert payload["automation"]["completed_stages"] == list(AUTOMATION_STAGES)
    assert payload["automation"]["provider_calls_this_cycle"] == 0
    assert payload["automation"]["hardware_submission_allowed"] is False
    assert [row["state"] for row in payload["public_lifecycle"]] == list(
        PUBLIC_LIFECYCLE_STATES
    )
    assert payload["telegram_brief"]["paragraph_count"] == 2
    assert payload["telegram_brief"]["telegram_send_allowed"] is False
    assert len((runtime / "qadam_quantum_edge_wave_g_events.jsonl").read_text().splitlines()) == len(
        AUTOMATION_STAGES
    )
    assert (site / "status/quantum-edge-wave-g.json").exists()
    validate_wave_g_payload(payload)


def test_candidate_budget_holds_excess_records():
    artifacts = _artifacts()
    second = _pattern("candidate:second")
    artifacts["wave_f"]["pattern_recognition"]["candidates"].append(second)
    artifacts["hybrid_candidates"].append(
        {
            "candidate_id": second["candidate_id"],
            "contract_fixture_only": False,
            "empirical_evidence_count": 80,
        }
    )
    artifacts["evaluations"].append(_evaluation(second["candidate_id"]))
    artifacts["operational_context"]["candidates"][second["candidate_id"]] = _operational_context()

    admitted, rejected = build_validated_edge_admissions(
        artifacts,
        generated_at=GENERATED_AT,
        budgets=WaveGBudgets(max_candidates_per_cycle=1),
    )

    assert len(admitted) == 1
    assert len(rejected) == 1
    assert "daily candidate review budget exhausted" in rejected[0]["blockers"]


def test_payload_rejects_authority_escalation(tmp_path: Path):
    runtime = tmp_path / "runtime"
    _write_runtime(runtime, _artifacts())
    payload = run_wave_g_cycle(
        runtime,
        generated_at=GENERATED_AT,
        evidence_date="2026-07-12",
    )
    tampered = deepcopy(payload)
    tampered["authority"]["direct_broker_call_allowed"] = True
    with pytest.raises(ValueError, match="wave_g_authority_escalated"):
        validate_wave_g_payload(tampered)


def test_quantum_and_pattern_modules_have_no_direct_broker_path():
    assert validate_wave_g_broker_boundary(ROOT) == []
