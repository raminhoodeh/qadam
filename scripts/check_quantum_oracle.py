#!/usr/bin/env python3
"""Validate the Phase 3 quantum/classical oracle scaffold."""

from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.intelligence import EvidenceItem, build_evidence_trail  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    QUANTUM_ORACLE_JOB_TYPES,
    QUANTUM_ORACLE_SCHEMA_VERSION,
    QUANTUM_ORACLE_SHOTS,
    QuantumOracleStore,
    quantum_local_simulator_status,
    quantum_oracle_input_contract,
    quantum_oracle_summary,
    quantum_provider_readiness,
    quantum_providers,
    run_quantum_oracle_sample,
    validate_quantum_local_simulator_status,
    validate_quantum_oracle_input_contract,
    validate_quantum_oracle_output_routing,
    validate_quantum_provider_readiness,
    validate_quantum_scheduler_dry_run,
)
from orchestrator.signal_integrity import (  # noqa: E402
    SignalIntegrityReviewStore,
    build_signal_integrity_review,
)

REQUIRED_RESULT_FIELDS = {
    "ambiguity_score",
    "backend",
    "backend_status",
    "boundary",
    "circuit_blueprint",
    "confidence_delta",
    "created_at",
    "execution_allowed",
    "hardware_scheduler_enabled",
    "hardware_provider",
    "hardware_submission_allowed",
    "hardware_submitted",
    "input_fingerprint",
    "instrument_focus",
    "job_id",
    "job_type",
    "local_validation_status",
    "local_simulation_mode",
    "measurement_counts",
    "output_routing",
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
    "validation_checks",
}

REQUIRED_JOB_FIELDS = {
    "average_trust_score",
    "boundary",
    "created_at",
    "evidence_item_count",
    "execution_allowed",
    "hardware_submission_allowed",
    "input_contract",
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


def _quantum_oracle_ready_signal() -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    evidence = (
        EvidenceItem(
            evidence_id="q3_6:yahoo:smh",
            source="market.yahoo_finance",
            event_type="market_price_confirmation",
            summary="SMH supplemental Yahoo Finance market confirmation for Head of Quant input-contract probe.",
            trust_score=0.72,
            observed_at=now,
            raw_ref="q3_6_contract_probe",
        ),
        EvidenceItem(
            evidence_id="q3_6:alpaca:smh",
            source="market.alpaca_readonly",
            event_type="market_price_confirmation",
            summary="SMH independent read-only market confirmation for Head of Quant input-contract probe.",
            trust_score=0.76,
            observed_at=now,
            raw_ref="q3_6_contract_probe",
        ),
        EvidenceItem(
            evidence_id="q3_6:rss:semiconductors",
            source="news.rss",
            event_type="news_observation",
            summary="Semiconductor supply-chain catalyst remains a shadow-only review item.",
            trust_score=0.74,
            observed_at=now,
            raw_ref="q3_6_contract_probe",
        ),
    )
    return {
        "schema_version": 1,
        "signal_id": "q3_6_quantum_oracle_input_probe",
        "status": "shadow_only",
        "title": "Q3-6 Head of Quant input-contract probe",
        "instrument_focus": "semiconductors",
        "thesis": "Synthetic upstream Signal Integrity review for oracle input-contract validation only.",
        "confidence": 0.71,
        "invalidation": "Synthetic probe only; no execution authority exists.",
        "evidence_trail": build_evidence_trail(evidence).to_dict(),
        "generated_by": "q3_6_oracle_input_contract_probe",
        "execution_allowed": False,
        "created_at": now,
    }


def _seed_quantum_oracle_ready_review(settings: Settings) -> dict[str, Any]:
    review = build_signal_integrity_review(_quantum_oracle_ready_signal())
    store = SignalIntegrityReviewStore(settings=settings)
    store.write(review)
    return review.to_dict()


def main() -> int:
    settings = Settings.from_env()
    seeded_review = _seed_quantum_oracle_ready_review(settings)
    seeded_input_contract = quantum_oracle_input_contract(seeded_review)
    validate_quantum_oracle_input_contract(seeded_input_contract)
    result = run_quantum_oracle_sample(settings=settings)
    summary = quantum_oracle_summary(settings)
    rows = QuantumOracleStore(settings=settings).read(limit=max(1, result["result_count"]))
    providers = quantum_providers(settings)
    local_simulator = quantum_local_simulator_status()
    validate_quantum_local_simulator_status(local_simulator)
    provider_readiness = quantum_provider_readiness(settings)
    validate_quantum_provider_readiness(provider_readiness)
    scheduler_dry_run = summary["scheduler_dry_run"]
    validate_quantum_scheduler_dry_run(scheduler_dry_run)

    print("quantum_oracle_status=" + result["status"])
    print(f"quantum_oracle_schema_version={result['schema_version']}")
    print(f"quantum_oracle_job_count={result['job_count']}")
    print(f"quantum_oracle_result_count={result['result_count']}")
    print("quantum_oracle_backend=" + result["backend"])
    print(f"quantum_oracle_backend_status={summary['latest_backend_status']}")
    print(f"quantum_oracle_local_simulation_mode={summary['latest_local_simulation_mode']}")
    print(f"quantum_oracle_cadence={summary['cadence']}")
    print(f"quantum_oracle_next_due_at={summary['next_due_at']}")
    print(f"quantum_oracle_store_status={summary['status']}")
    print(f"quantum_oracle_store_result_count={summary['result_count']}")
    print(f"quantum_oracle_hardware_submitted_count={result['hardware_submitted_count']}")
    print(f"quantum_oracle_hardware_submission_allowed_count={result['hardware_submission_allowed_count']}")
    print(f"quantum_oracle_hardware_scheduler_enabled_count={result['hardware_scheduler_enabled_count']}")
    print(f"quantum_oracle_execution_allowed_count={result['execution_allowed_count']}")
    print(f"quantum_oracle_paper_order_allowed_count={result['paper_order_allowed_count']}")
    print(f"quantum_oracle_trade_candidate_created_count={result['trade_candidate_created_count']}")
    print(f"quantum_oracle_qiskit_aer_available={summary['qiskit_aer_available']}")
    print(f"quantum_oracle_qiskit_available={summary['qiskit_available']}")
    print(f"quantum_local_simulator_status={local_simulator['status']}")
    print(f"quantum_local_simulator_selected_backend={local_simulator['selected_backend']}")
    print(f"quantum_local_simulator_qiskit_dependencies={local_simulator['qiskit_dependencies_available']}")
    print(f"quantum_local_simulator_fallback_available={local_simulator['classical_fallback_available']}")
    print(f"quantum_local_simulator_required_job_count={local_simulator['required_job_count']}")
    print(f"quantum_oracle_input_contract_status={seeded_input_contract['status']}")
    print(f"quantum_oracle_input_source_type={seeded_input_contract['source_type']}")
    print(f"quantum_oracle_input_market_confirmation_status={seeded_input_contract['market_confirmation_status']}")
    print(f"quantum_oracle_input_yahoo_finance_role={seeded_input_contract['yahoo_finance_role']}")
    print(f"quantum_oracle_input_yahoo_only_market_confirmation={seeded_input_contract['yahoo_only_market_confirmation']}")
    print(
        "quantum_oracle_input_durable_evidence_status="
        f"{seeded_input_contract['durable_evidence_context']['status']}"
    )
    latest_output_routing = summary.get("latest_output_routing", {})
    print(f"quantum_oracle_output_routing_status={summary.get('latest_output_routing_status')}")
    print(f"quantum_oracle_output_route_type={summary.get('latest_output_route_type')}")
    print(f"quantum_oracle_output_storage_type={summary.get('latest_output_storage_type')}")
    print(f"quantum_oracle_output_annotation_target={summary.get('latest_output_annotation_target')}")
    if isinstance(latest_output_routing, dict):
        print(f"quantum_oracle_output_trade_candidate_created_count={latest_output_routing.get('trade_candidate_created_count')}")
        print(f"quantum_oracle_output_risk_approval_count={latest_output_routing.get('risk_approval_count')}")
        print(
            "quantum_oracle_output_execution_policy_approval_count="
            f"{latest_output_routing.get('execution_policy_approval_count')}"
        )
        print(
            "quantum_oracle_output_staged_paper_order_created_count="
            f"{latest_output_routing.get('staged_paper_order_created_count')}"
        )
        print(
            "quantum_oracle_output_broker_reconciliation_write_count="
            f"{latest_output_routing.get('broker_reconciliation_write_count')}"
        )
        print(
            "quantum_oracle_output_paper_submit_receipt_created_count="
            f"{latest_output_routing.get('paper_submit_receipt_created_count')}"
        )
    print(f"quantum_scheduler_dry_run_status={scheduler_dry_run['status']}")
    print(f"quantum_scheduler_due={scheduler_dry_run['due']}")
    print(f"quantum_scheduler_next_due_at={scheduler_dry_run['next_due_at']}")
    print(f"quantum_scheduler_enabled={scheduler_dry_run['scheduler_enabled']}")
    print(f"quantum_scheduler_would_queue_job_count={scheduler_dry_run['would_queue_job_count']}")
    print(f"quantum_scheduler_jobs_queued_count={scheduler_dry_run['jobs_queued_count']}")
    print(f"quantum_scheduler_jobs_submitted_count={scheduler_dry_run['jobs_submitted_count']}")
    print(f"quantum_scheduler_hardware_scheduler_enabled_count={scheduler_dry_run['hardware_scheduler_enabled_count']}")
    print(f"quantum_provider_count={len(providers)}")
    print(f"quantum_provider_readiness_status={provider_readiness['status']}")
    print(f"quantum_provider_readiness_qctrl_configured={provider_readiness['qctrl_configured']}")
    print(f"quantum_provider_call_allowed_count={provider_readiness['provider_call_allowed_count']}")
    print(f"quantum_provider_hardware_submission_allowed_count={provider_readiness['hardware_submission_allowed_count']}")
    hardware_stubs = provider_readiness["hardware_provider_stubs"]
    print(f"quantum_hardware_provider_stubs_status={hardware_stubs['status']}")
    print(f"quantum_hardware_provider_count={hardware_stubs['provider_count']}")
    print(f"quantum_hardware_provider_missing_credentials_count={hardware_stubs['missing_credentials_count']}")
    print(
        "quantum_hardware_provider_configured_policy_blocked_count="
        f"{hardware_stubs['configured_policy_blocked_count']}"
    )
    print(f"quantum_hardware_submission_allowed_count={hardware_stubs['hardware_submission_allowed_count']}")
    print(f"quantum_hardware_submitted_count={hardware_stubs['hardware_submitted_count']}")
    qctrl = provider_readiness["qctrl_readiness"]
    print(f"qctrl_readiness_status={qctrl['status']}")
    print(f"qctrl_credential_configured={qctrl['credential_configured']}")
    print(f"qctrl_sdk_package_importable={qctrl['sdk_package_importable']}")
    print(f"qctrl_live_probe_enabled={qctrl['live_probe_enabled']}")
    print(f"qctrl_provider_call_count={qctrl['provider_call_count']}")
    print(f"qctrl_optimization_job_submitted={qctrl['optimization_job_submitted']}")
    print("quantum_oracle_boundary=" + result["boundary"])

    if result["status"] != "ok":
        return 1
    if result["schema_version"] != QUANTUM_ORACLE_SCHEMA_VERSION:
        print("quantum_oracle_schema_version_mismatch=true")
        return 1
    if result["job_count"] != len(QUANTUM_ORACLE_JOB_TYPES):
        print("quantum_oracle_job_count_mismatch=true")
        return 1
    if result["job_count"] != local_simulator["required_job_count"]:
        print("quantum_local_simulator_job_count_mismatch=true")
        return 1
    if result["hardware_submitted_count"] != 0:
        print("quantum_oracle_hardware_submitted=true")
        return 1
    if result["hardware_submission_allowed_count"] != 0:
        print("quantum_oracle_hardware_submission_allowed=true")
        return 1
    if result["hardware_scheduler_enabled_count"] != 0:
        print("quantum_oracle_hardware_scheduler_enabled=true")
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
    if summary.get("latest_input_contract_status") != "accepted":
        print("quantum_oracle_latest_input_contract_not_accepted=true")
        return 1
    if summary.get("latest_input_source_type") != "signal_integrity_review":
        print("quantum_oracle_latest_input_source_invalid=true")
        return 1
    if summary.get("latest_market_confirmation_status") != "market_confirmation_corroboration_available":
        print("quantum_oracle_latest_market_confirmation_invalid=true")
        return 1
    if summary.get("latest_yahoo_only_market_confirmation") is not False:
        print("quantum_oracle_latest_yahoo_only_market_confirmation=true")
        return 1
    if not isinstance(latest_output_routing, dict):
        print("quantum_oracle_latest_output_routing_invalid=true")
        return 1
    try:
        validate_quantum_oracle_output_routing(latest_output_routing)
    except ValueError as exc:
        print("quantum_oracle_latest_output_routing_rejected=" + str(exc))
        return 1
    if summary.get("latest_output_route_type") != "shadow_annotation":
        print("quantum_oracle_latest_output_route_invalid=true")
        return 1
    if summary.get("latest_output_storage_type") != "oracle_review_result":
        print("quantum_oracle_latest_output_storage_invalid=true")
        return 1
    if scheduler_dry_run["scheduler_enabled"] is not False:
        print("quantum_scheduler_enabled=true")
        return 1
    if scheduler_dry_run["background_automation_created"] is not False:
        print("quantum_scheduler_background_automation_created=true")
        return 1
    if scheduler_dry_run["recurring_job_created"] is not False:
        print("quantum_scheduler_recurring_job_created=true")
        return 1
    if scheduler_dry_run["jobs_queued_count"] != 0:
        print("quantum_scheduler_jobs_queued=true")
        return 1
    if scheduler_dry_run["jobs_submitted_count"] != 0:
        print("quantum_scheduler_jobs_submitted=true")
        return 1
    if scheduler_dry_run["hardware_scheduler_enabled_count"] != 0:
        print("quantum_scheduler_hardware_scheduler_enabled=true")
        return 1
    if scheduler_dry_run["hardware_submission_allowed_count"] != 0:
        print("quantum_scheduler_hardware_submission_allowed=true")
        return 1
    if provider_readiness["provider_count"] != len(providers):
        print("quantum_provider_readiness_count_mismatch=true")
        return 1
    if provider_readiness["qctrl_configured"] is not True:
        print("quantum_provider_readiness_qctrl_not_configured=true")
        return 1
    if provider_readiness["provider_call_allowed_count"] != 0:
        print("quantum_provider_readiness_provider_call_allowed=true")
        return 1
    if provider_readiness["hardware_submission_allowed_count"] != 0:
        print("quantum_provider_readiness_hardware_allowed=true")
        return 1
    if hardware_stubs["provider_count"] != 2:
        print("quantum_hardware_provider_count_mismatch=true")
        return 1
    if hardware_stubs["explicit_hardware_policy_approval_present"] is not False:
        print("quantum_hardware_policy_approval_present=true")
        return 1
    if hardware_stubs["hardware_submission_allowed_count"] != 0:
        print("quantum_hardware_submission_allowed=true")
        return 1
    if hardware_stubs["hardware_submitted_count"] != 0:
        print("quantum_hardware_submitted=true")
        return 1
    if hardware_stubs["hardware_scheduler_enabled_count"] != 0:
        print("quantum_hardware_scheduler_enabled=true")
        return 1
    if hardware_stubs["submitting_backend_implemented_count"] != 0:
        print("quantum_hardware_submitting_backend_implemented=true")
        return 1
    if qctrl["credential_configured"] is not True:
        print("qctrl_credential_missing=true")
        return 1
    if qctrl["live_probe_enabled"] is not False:
        print("qctrl_live_probe_enabled=true")
        return 1
    if qctrl["provider_call_count"] != 0:
        print("qctrl_provider_call_count_nonzero=true")
        return 1
    if qctrl["optimization_job_submitted"] is not False:
        print("qctrl_optimization_job_submitted=true")
        return 1
    if qctrl["hardware_job_submitted"] is not False:
        print("qctrl_hardware_job_submitted=true")
        return 1
    if qctrl["recommendation_authority"] is not False:
        print("qctrl_recommendation_authority=true")
        return 1

    seen_job_types = set()
    for row in rows:
        job = row.get("job", {})
        oracle_result = row.get("result", {})
        missing_job = sorted(REQUIRED_JOB_FIELDS - set(job))
        missing_result = sorted(REQUIRED_RESULT_FIELDS - set(oracle_result))
        if missing_job:
            print("quantum_oracle_job_fields_missing=" + ",".join(missing_job))
            return 1
        input_contract = job.get("input_contract", {})
        if not isinstance(input_contract, dict):
            print("quantum_oracle_job_input_contract_invalid=true")
            return 1
        try:
            validate_quantum_oracle_input_contract(input_contract)
        except ValueError as exc:
            print("quantum_oracle_job_input_contract_rejected=" + str(exc))
            return 1
        if input_contract.get("source_type") != "signal_integrity_review":
            print("quantum_oracle_job_input_source_invalid=true")
            return 1
        if input_contract.get("yahoo_only_market_confirmation") is not False:
            print("quantum_oracle_job_yahoo_only_market_confirmation=true")
            return 1
        output_routing = oracle_result.get("output_routing", {})
        if not isinstance(output_routing, dict):
            print("quantum_oracle_result_output_routing_invalid=true")
            return 1
        try:
            validate_quantum_oracle_output_routing(output_routing)
        except ValueError as exc:
            print("quantum_oracle_result_output_routing_rejected=" + str(exc))
            return 1
        if output_routing.get("recommendation_class") != oracle_result.get("recommendation"):
            print("quantum_oracle_result_output_recommendation_mismatch=true")
            return 1
        if missing_result:
            print("quantum_oracle_result_fields_missing=" + ",".join(missing_result))
            return 1
        if job["job_type"] not in QUANTUM_ORACLE_JOB_TYPES:
            print("quantum_oracle_invalid_job_type=" + str(job["job_type"]))
            return 1
        seen_job_types.add(job["job_type"])
        if oracle_result["schema_version"] != QUANTUM_ORACLE_SCHEMA_VERSION:
            print("quantum_oracle_result_schema_mismatch=true")
            return 1
        if oracle_result["backend"] not in {"classical_fallback", "qiskit_aer_local"}:
            print("quantum_oracle_result_backend_invalid=" + str(oracle_result["backend"]))
            return 1
        if oracle_result["backend_status"] not in {"ok", "degraded_classical_fallback"}:
            print("quantum_oracle_result_backend_status_invalid=" + str(oracle_result["backend_status"]))
            return 1
        if oracle_result["local_simulation_mode"] not in {
            "deterministic_classical_shadow",
            "qiskit_aer_local_circuit",
        }:
            print("quantum_oracle_result_local_simulation_mode_invalid=true")
            return 1
        if oracle_result["hardware_submitted"] is not False:
            print("quantum_oracle_result_submitted_hardware=true")
            return 1
        if oracle_result["hardware_provider"] is not None:
            print("quantum_oracle_result_hardware_provider_selected=true")
            return 1
        if oracle_result["hardware_submission_allowed"] is not False:
            print("quantum_oracle_result_hardware_submission_allowed=true")
            return 1
        if oracle_result["hardware_scheduler_enabled"] is not False:
            print("quantum_oracle_result_hardware_scheduler_enabled=true")
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
        if len(str(oracle_result["input_fingerprint"])) != 64:
            print("quantum_oracle_input_fingerprint_invalid=true")
            return 1
        if not oracle_result["circuit_blueprint"]:
            print("quantum_oracle_circuit_blueprint_missing=true")
            return 1
        if not oracle_result["measurement_counts"]:
            print("quantum_oracle_measurement_counts_missing=true")
            return 1
        if sum(oracle_result["measurement_counts"].values()) != QUANTUM_ORACLE_SHOTS:
            print("quantum_oracle_measurement_counts_shot_mismatch=true")
            return 1
        if oracle_result["circuit_blueprint"].get("shots") != QUANTUM_ORACLE_SHOTS:
            print("quantum_oracle_circuit_shots_mismatch=true")
            return 1
        if any(not str(value).startswith("pass") for value in oracle_result["validation_checks"].values()):
            print("quantum_oracle_validation_checks_not_passed=true")
            return 1
        if "cannot originate trades" not in oracle_result["boundary"]:
            print("quantum_oracle_boundary_weak=true")
            return 1
    if seen_job_types != QUANTUM_ORACLE_JOB_TYPES:
        print("quantum_oracle_job_types_missing=" + ",".join(sorted(QUANTUM_ORACLE_JOB_TYPES - seen_job_types)))
        return 1

    print("quantum_oracle_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
