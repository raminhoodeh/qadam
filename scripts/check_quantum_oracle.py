#!/usr/bin/env python3
"""Validate the Phase 3 quantum/classical oracle scaffold."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    QUANTUM_ORACLE_JOB_TYPES,
    QUANTUM_ORACLE_SCHEMA_VERSION,
    QuantumOracleStore,
    quantum_oracle_summary,
    quantum_providers,
    run_quantum_oracle_sample,
)

REQUIRED_RESULT_FIELDS = {
    "ambiguity_score",
    "backend",
    "boundary",
    "confidence_delta",
    "created_at",
    "execution_allowed",
    "hardware_provider",
    "hardware_submission_allowed",
    "hardware_submitted",
    "instrument_focus",
    "job_id",
    "job_type",
    "local_validation_status",
    "paper_order_allowed",
    "pattern_score",
    "recommendation",
    "required_next_steps",
    "result_id",
    "schema_version",
    "simulator_status",
    "source_ref",
    "status",
    "trade_candidate_created",
}

REQUIRED_JOB_FIELDS = {
    "average_trust_score",
    "boundary",
    "created_at",
    "evidence_item_count",
    "execution_allowed",
    "hardware_submission_allowed",
    "instrument_focus",
    "job_id",
    "job_type",
    "local_validation_required",
    "missing_correlation_count",
    "paper_order_allowed",
    "schema_version",
    "signal_confidence",
    "source_count",
    "source_ref",
}


def main() -> int:
    settings = Settings.from_env()
    result = run_quantum_oracle_sample(settings=settings)
    summary = quantum_oracle_summary(settings)
    rows = QuantumOracleStore(settings=settings).read(limit=max(1, result["result_count"]))
    providers = quantum_providers(settings)

    print("quantum_oracle_status=" + result["status"])
    print(f"quantum_oracle_schema_version={result['schema_version']}")
    print(f"quantum_oracle_job_count={result['job_count']}")
    print(f"quantum_oracle_result_count={result['result_count']}")
    print("quantum_oracle_backend=" + result["backend"])
    print(f"quantum_oracle_store_status={summary['status']}")
    print(f"quantum_oracle_store_result_count={summary['result_count']}")
    print(f"quantum_oracle_hardware_submitted_count={result['hardware_submitted_count']}")
    print(f"quantum_oracle_hardware_submission_allowed_count={result['hardware_submission_allowed_count']}")
    print(f"quantum_oracle_execution_allowed_count={result['execution_allowed_count']}")
    print(f"quantum_oracle_paper_order_allowed_count={result['paper_order_allowed_count']}")
    print(f"quantum_oracle_trade_candidate_created_count={result['trade_candidate_created_count']}")
    print(f"quantum_oracle_qiskit_aer_available={summary['qiskit_aer_available']}")
    print(f"quantum_provider_count={len(providers)}")
    print("quantum_oracle_boundary=" + result["boundary"])

    if result["status"] != "ok":
        return 1
    if result["schema_version"] != QUANTUM_ORACLE_SCHEMA_VERSION:
        print("quantum_oracle_schema_version_mismatch=true")
        return 1
    if result["job_count"] != len(QUANTUM_ORACLE_JOB_TYPES):
        print("quantum_oracle_job_count_mismatch=true")
        return 1
    if result["hardware_submitted_count"] != 0:
        print("quantum_oracle_hardware_submitted=true")
        return 1
    if result["hardware_submission_allowed_count"] != 0:
        print("quantum_oracle_hardware_submission_allowed=true")
        return 1
    if result["execution_allowed_count"] != 0:
        print("quantum_oracle_execution_allowed=true")
        return 1
    if result["paper_order_allowed_count"] != 0:
        print("quantum_oracle_paper_order_allowed=true")
        return 1
    if result["trade_candidate_created_count"] != 0:
        print("quantum_oracle_trade_candidate_created=true")
        return 1

    for row in rows:
        job = row.get("job", {})
        oracle_result = row.get("result", {})
        missing_job = sorted(REQUIRED_JOB_FIELDS - set(job))
        missing_result = sorted(REQUIRED_RESULT_FIELDS - set(oracle_result))
        if missing_job:
            print("quantum_oracle_job_fields_missing=" + ",".join(missing_job))
            return 1
        if missing_result:
            print("quantum_oracle_result_fields_missing=" + ",".join(missing_result))
            return 1
        if job["job_type"] not in QUANTUM_ORACLE_JOB_TYPES:
            print("quantum_oracle_invalid_job_type=" + str(job["job_type"]))
            return 1
        if oracle_result["hardware_submitted"] is not False:
            print("quantum_oracle_result_submitted_hardware=true")
            return 1
        if oracle_result["hardware_submission_allowed"] is not False:
            print("quantum_oracle_result_hardware_submission_allowed=true")
            return 1
        if oracle_result["execution_allowed"] is not False:
            print("quantum_oracle_result_execution_allowed=true")
            return 1
        if oracle_result["paper_order_allowed"] is not False:
            print("quantum_oracle_result_paper_order_allowed=true")
            return 1
        if oracle_result["trade_candidate_created"] is not False:
            print("quantum_oracle_result_created_candidate=true")
            return 1
        if "cannot originate trades" not in oracle_result["boundary"]:
            print("quantum_oracle_boundary_weak=true")
            return 1

    print("quantum_oracle_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
