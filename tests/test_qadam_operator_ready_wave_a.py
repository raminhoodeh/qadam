from __future__ import annotations

from pathlib import Path

from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_dynamic_plan import PHASE_ORDER, program_status
from orchestrator.qadam_point_in_time_evidence import (
    build_eligibility_graph,
    build_forward_coverage,
)
from orchestrator.qadam_research_supervisor import (
    ResearchSupervisor,
    build_job,
    stable_job_id,
    validate_job,
)


def test_research_job_identity_is_stable_and_execution_types_fail_closed() -> None:
    values = {
        "job_type": "source_acquisition",
        "source": "un_comtrade",
        "provider": "un_comtrade",
        "instrument": None,
        "date_partition": "2025",
        "requested_granularity": "annual",
    }
    assert stable_job_id(**values) == stable_job_id(**values)
    valid = build_job(**values).to_dict()
    assert validate_job(valid) == []
    unsafe = {**valid, "job_type": "broker_order_submit"}
    errors = validate_job(unsafe)
    assert any("research_job_type_forbidden" in error for error in errors)
    assert any("research_job_execution_token_forbidden" in error for error in errors)


def test_dynamic_status_exposes_maturing_wave_a_evidence() -> None:
    phases = {phase: {"state": "not_started"} for phase in PHASE_ORDER}
    for phase in PHASE_ORDER[:8]:
        phases[phase]["state"] = "passed"
    phases["OR-0"]["state"] = "passed"
    phases["OR-1"]["state"] = "passed"
    phases["OR-2"]["state"] = "passed"
    phases["OR-3"]["state"] = "evidence_maturing"
    phases["OR-4"]["state"] = "passed"
    assert program_status(phases) == "wave_a_evidence_maturing"


def test_research_supervisor_resume_deduplicates_manifest(tmp_path: Path) -> None:
    supervisor = ResearchSupervisor(tmp_path)
    job = build_job(
        job_type="price_acquisition",
        provider="read_only_provider",
        instrument="TEST",
        date_partition="2025",
        requested_granularity="1d",
        status="interrupted",
    ).to_dict()
    supervisor.write_jobs([job, dict(job)])
    assert [record["job_id"] for record in supervisor.resumable_jobs()] == [job["job_id"]]


def test_relationship_graph_distinguishes_causal_and_duplicate_clusters() -> None:
    sources = [
        {"source_key": "acled", "source_family": "conflict"},
        {"source_key": "ais_or_shipping", "source_family": "market_context_taxonomy"},
    ]
    instruments = [
        {"symbol": "CL=F", "market_family": "crude_oil"},
        {"symbol": "SMH", "market_family": "semiconductors"},
    ]
    operational = {
        "acled": {"raw_scoring_eligible": True, "source_quorum_eligible": True},
        "ais_or_shipping": {"raw_scoring_eligible": False, "source_quorum_eligible": False},
    }
    graph = build_eligibility_graph(sources, instruments, operational)
    by_pair = {(record["source_key"], record["instrument"]): record for record in graph}
    assert by_pair[("acled", "CL=F")]["mapping_class"] == "causal_strategy_mapping"
    assert by_pair[("ais_or_shipping", "CL=F")]["mapping_class"] == "causal_strategy_mapping"
    assert by_pair[("ais_or_shipping", "CL=F")]["live_scoring_eligible"] is False
    assert by_pair[("ais_or_shipping", "CL=F")]["source_independence_cluster_id"] != "ais_or_shipping"


def test_forward_outcome_at_decision_is_quarantined() -> None:
    eligibility = [
        {
            "relationship_id": "relationship:test",
            "source_key": "acled",
            "instrument": "CL=F",
            "mapping_class": "causal_strategy_mapping",
            "historical_research_eligible": True,
            "source_independence_cluster_id": "source-cluster:test",
        }
    ]
    timestamp = "2026-01-01T00:00:00+00:00"
    memory = [
        {
            "memory_record_id": "memory:test",
            "matrix_row_ids": ["matrix:test"],
            "event_timestamp": timestamp,
            "source_available_at": timestamp,
            "decision_timestamp": timestamp,
            "as_of_timestamp": timestamp,
            "outcome_available_at": timestamp,
            "feature_availability": {
                "feature_timestamp": timestamp,
                "forbidden_future_features_detected": False,
            },
            "forward_outcomes": {"window": "1d_forward", "outcome_available": True},
            "source_snapshot": {"source_name": "acled"},
            "market_snapshot": {"instrument": "CL=F", "price": 1.0},
            "provenance": [{"artifact": "fixture"}],
        }
    ]
    coverage, leakage = build_forward_coverage(memory, eligibility)
    assert coverage["eligible_forward_score_input_count"] == 0
    assert leakage["quarantined_input_record_count"] == 1
    assert leakage["leakage_violation_count"] == 0
    assert leakage["authority"] == authority_flags()
