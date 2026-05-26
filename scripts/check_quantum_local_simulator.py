#!/usr/bin/env python3
"""Validate the Phase 3 local quantum simulator track without writing results."""

from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intelligence import EvidenceItem, build_evidence_trail  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    QUANTUM_ORACLE_JOB_TYPES,
    QUANTUM_ORACLE_SCHEMA_VERSION,
    QUANTUM_ORACLE_SHOTS,
    build_quantum_oracle_job,
    quantum_local_simulator_status,
    run_quantum_oracle_job,
    validate_quantum_local_simulator_status,
    validate_quantum_oracle_input_contract,
    validate_quantum_oracle_result,
)
from orchestrator.signal_integrity import build_signal_integrity_review  # noqa: E402


def _sample_review() -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    evidence = (
        EvidenceItem(
            evidence_id="q3_2:yahoo:smh",
            source="market.yahoo_finance",
            event_type="market_price_confirmation",
            summary="SMH supplemental Yahoo Finance market confirmation for local simulator probe.",
            trust_score=0.72,
            observed_at=now,
            raw_ref="q3_2_local_simulator_probe",
        ),
        EvidenceItem(
            evidence_id="q3_2:alpaca:smh",
            source="market.alpaca_readonly",
            event_type="market_price_confirmation",
            summary="SMH independent read-only market confirmation for local simulator probe.",
            trust_score=0.76,
            observed_at=now,
            raw_ref="q3_2_local_simulator_probe",
        ),
        EvidenceItem(
            evidence_id="q3_2:rss:semiconductors",
            source="news.rss",
            event_type="news_observation",
            summary="Semiconductor catalyst remains shadow-only context for simulator validation.",
            trust_score=0.74,
            observed_at=now,
            raw_ref="q3_2_local_simulator_probe",
        ),
    )
    signal = {
        "schema_version": 1,
        "signal_id": "q3_2_local_simulator_input_probe",
        "status": "shadow_only",
        "title": "Q3-2 local simulator input-contract probe",
        "review_id": "q3_2_local_simulator_check",
        "instrument_focus": "macro_watchlist",
        "thesis": "Synthetic upstream Signal Integrity review for local simulator validation only.",
        "confidence": 0.71,
        "invalidation": "Synthetic probe only; no execution authority exists.",
        "evidence_trail": build_evidence_trail(evidence).to_dict(),
        "generated_by": "q3_2_local_simulator_probe",
        "execution_allowed": False,
        "created_at": now,
    }
    return build_signal_integrity_review(signal).to_dict()


def main() -> int:
    simulator = quantum_local_simulator_status()
    validate_quantum_local_simulator_status(simulator)
    review = _sample_review()
    jobs = tuple(build_quantum_oracle_job(review, job_type=job_type) for job_type in sorted(QUANTUM_ORACLE_JOB_TYPES))
    results = tuple(run_quantum_oracle_job(job) for job in jobs)

    print("quantum_local_simulator_check_status=ok")
    print(f"quantum_local_simulator_schema_version={simulator['schema_version']}")
    print(f"quantum_local_simulator_status={simulator['status']}")
    print(f"quantum_local_simulator_selected_backend={simulator['selected_backend']}")
    print(f"quantum_local_simulator_qiskit_available={simulator['qiskit_available']}")
    print(f"quantum_local_simulator_qiskit_aer_available={simulator['qiskit_aer_available']}")
    print(f"quantum_local_simulator_qiskit_dependencies={simulator['qiskit_dependencies_available']}")
    print(f"quantum_local_simulator_fallback_available={simulator['classical_fallback_available']}")
    print(f"quantum_local_simulator_required_job_count={simulator['required_job_count']}")
    print(f"quantum_local_simulator_output_schema_version={simulator['output_schema_version']}")

    if simulator["required_job_count"] != len(QUANTUM_ORACLE_JOB_TYPES):
        print("quantum_local_simulator_job_count_mismatch=true")
        return 1
    if set(simulator["expected_job_types"]) != QUANTUM_ORACLE_JOB_TYPES:
        print("quantum_local_simulator_job_types_mismatch=true")
        return 1
    if simulator["classical_fallback_available"] is not True:
        print("quantum_local_simulator_fallback_unavailable=true")
        return 1
    if simulator["output_schema_version"] != QUANTUM_ORACLE_SCHEMA_VERSION:
        print("quantum_local_simulator_schema_mismatch=true")
        return 1

    seen_job_types: set[str] = set()
    for job, result in zip(jobs, results):
        validate_quantum_oracle_result(result)
        validate_quantum_oracle_input_contract(job.input_contract)
        seen_job_types.add(job.job_type)
        print(
            "quantum_local_simulator_result="
            f"{job.job_type},{result.backend},{result.backend_status},{result.local_simulation_mode}"
        )
        if result.schema_version != QUANTUM_ORACLE_SCHEMA_VERSION:
            print("quantum_local_simulator_result_schema_mismatch=true")
            return 1
        if result.backend not in {"classical_fallback", "qiskit_aer_local"}:
            print("quantum_local_simulator_backend_invalid=" + result.backend)
            return 1
        if result.backend_status not in {"ok", "degraded_classical_fallback"}:
            print("quantum_local_simulator_backend_status_invalid=" + result.backend_status)
            return 1
        if result.hardware_provider is not None:
            print("quantum_local_simulator_hardware_provider_selected=true")
            return 1
        if result.hardware_submission_allowed or result.hardware_submitted:
            print("quantum_local_simulator_hardware_submission_enabled=true")
            return 1
        if result.hardware_scheduler_enabled:
            print("quantum_local_simulator_hardware_scheduler_enabled=true")
            return 1
        if result.execution_allowed or result.paper_order_allowed or result.trade_candidate_created:
            print("quantum_local_simulator_execution_authority_enabled=true")
            return 1
        if result.circuit_blueprint.get("shots") != QUANTUM_ORACLE_SHOTS:
            print("quantum_local_simulator_circuit_shots_mismatch=true")
            return 1
        if sum(result.measurement_counts.values()) != QUANTUM_ORACLE_SHOTS:
            print("quantum_local_simulator_measurement_count_mismatch=true")
            return 1
        if any(not str(value).startswith("pass") for value in result.validation_checks.values()):
            print("quantum_local_simulator_validation_checks_not_passed=true")
            return 1

    if seen_job_types != QUANTUM_ORACLE_JOB_TYPES:
        print("quantum_local_simulator_missing_jobs=" + ",".join(sorted(QUANTUM_ORACLE_JOB_TYPES - seen_job_types)))
        return 1

    print("quantum_local_simulator_result_count=" + str(len(results)))
    print("quantum_local_simulator_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
