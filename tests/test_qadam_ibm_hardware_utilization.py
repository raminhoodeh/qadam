from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_ibm_hardware_utilization import (
    build_followup_artifact,
    build_utilization_artifact,
    validate_followup_artifact,
    validate_utilization_artifact,
)


def _result() -> dict:
    return {
        "status": "completed",
        "provider_status": "SUCCESS",
        "experiment_id": "ibm-full-history-surprise-discovery-v1",
        "hardware_manifest_hash": "a" * 64,
        "receipt_hash": "b" * 64,
        "input_envelope": {
            "canonical_source_count": 41,
            "canonical_instrument_count": 19,
            "historically_scored_source_count": 5,
            "score_plane_instrument_count": 17,
            "paired_score_label_row_count": 40_126,
            "prototype_audit": {"prototype_count": 32},
        },
        "research_candidates": [
            {
                "candidate_id": "discovery-candidate:test",
                "research_question": "Does the relationship persist?",
                "feature_pair": ["causal_mapping_strength", "market_flow"],
                "structural_score": 0.291437885662,
            }
        ],
    }


def _provider_usage() -> dict:
    return {
        "plan": "open",
        "provider_job_reference_count": 122,
        "unique_ibm_workload_count": 1,
        "circuit_count": 122,
        "total_shots": 31_232,
        "quantum_seconds": 28,
        "workload_statuses": ["DONE"],
        "provider_execution_timestamp": "2026-07-20T11:52:15.305721+00:00",
        "submitted_at": "2026-07-20T11:48:48.347379+00:00",
        "completed_at": "2026-07-20T11:55:39.311405+00:00",
        "account_usage_consumed_seconds": 28,
        "account_usage_limit_seconds": 600,
        "account_usage_remaining_seconds": 572,
        "cost_usd": 0.0,
        "cost_state": "no_incremental_charge_open_plan",
        "billing_fields_exposed_by_fire_opal_result": False,
        "source": "qctrl_receipt_plus_ibm_quantum_platform_readback",
    }


def _rejected_validation() -> dict:
    return {
        "status": "tested_rejected_no_predictive_value",
        "candidate_id": "discovery-candidate:test",
        "hardware_receipt_hash": "b" * 64,
        "content_hash": "c" * 64,
        "split": {
            "holdout_start_at": "2026-04-01T00:00:00+00:00",
            "holdout_end_at": "2026-06-30T00:00:00+00:00",
        },
        "models": {
            "additive_classical": {
                "holdout_metrics": {
                    "trade_count": 913,
                    "mean_net_return": 0.00647,
                }
            },
            "hardware_originated_interaction": {
                "holdout_metrics": {
                    "trade_count": 418,
                    "mean_net_return": 0.00975,
                }
            },
        },
        "comparison": {
            "interaction_minus_baseline_mean_net_return_per_opportunity": -0.000663,
            "multiple_testing_adjusted_p_value": 1.0,
        },
        "verdict": {
            "label": "The IBM finding did not survive the historical predictive test.",
            "plain_english": "The simpler classical explanation remained preferable.",
            "historical_survivor": False,
            "rejection_reasons": [
                "interaction_did_not_beat_additive_classical_baseline"
            ],
            "next_action": "retain_as_rejected_research_evidence_no_strategy_change",
        },
    }


def test_builds_exact_cost_runtime_and_followup_contract() -> None:
    utilization = build_utilization_artifact(
        _result(), _provider_usage(), generated_at="2026-07-20T12:30:00+00:00"
    )
    assert utilization["cost"]["billed_cost"] == 0.0
    assert utilization["timing"]["ibm_quantum_seconds"] == 28
    assert utilization["timing"]["provider_turnaround_seconds"] == 410.964026
    assert utilization["workload"]["unique_ibm_workload_count"] == 1
    assert utilization["workload"]["circuit_count"] == 122
    assert validate_utilization_artifact(utilization) == []

    followup = build_followup_artifact(
        _result(), utilization, generated_at="2026-07-20T12:30:00+00:00"
    )
    assert followup["status"] == "validation_program_active"
    assert followup["candidate_count"] == 1
    assert followup["candidates"][0]["hardware_repeat"][
        "automatic_paid_rerun_allowed"
    ] is False
    assert followup["current_strategy_impact_count"] == 0
    assert validate_followup_artifact(followup) == []


def test_rejected_historical_validation_closes_downstream_programme() -> None:
    utilization = build_utilization_artifact(
        _result(), _provider_usage(), generated_at="2026-07-20T12:30:00+00:00"
    )
    followup = build_followup_artifact(
        _result(),
        utilization,
        generated_at="2026-07-20T12:31:00+00:00",
        validation=_rejected_validation(),
    )

    assert followup["status"] == "validation_program_complete_no_edge"
    assert followup["next_autonomous_action"] == "none_historical_candidate_rejected"
    candidate = followup["candidates"][0]
    assert candidate["lifecycle_state"] == "historically_tested_not_predictive"
    assert candidate["historical_validation"]["status"] == (
        "tested_rejected_no_predictive_value"
    )
    assert candidate["automatic_research_steps"][3]["state"] == (
        "closed_after_historical_rejection"
    )
    assert candidate["automatic_research_steps"][4]["state"] == (
        "closed_no_strategy_change"
    )
    assert validate_followup_artifact(followup) == []


def test_fail_closed_if_hardware_candidate_is_promoted() -> None:
    utilization = build_utilization_artifact(
        _result(), _provider_usage(), generated_at="2026-07-20T12:30:00+00:00"
    )
    followup = build_followup_artifact(
        _result(), utilization, generated_at="2026-07-20T12:30:00+00:00"
    )
    unsafe = deepcopy(followup)
    unsafe["candidates"][0]["trade_candidate_created"] = True
    unsafe["content_hash"] = "invalid"
    assert "candidate_boundary_breach:trade_candidate_created" in validate_followup_artifact(
        unsafe
    )
