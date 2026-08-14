#!/usr/bin/env python3
"""Certify Qadam's compounding evidence graph implementation.

Implementation integrity, empirical edge validation and elapsed real-market
trial time are deliberately reported as separate states. This checker may
refresh deterministic research projections, but it cannot create authority,
orders, broker writes, proof credit or simulated elapsed time.
"""

from __future__ import annotations

from collections import Counter
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_qeg_common import (  # noqa: E402
    ACTIONABILITY_QUEUE_ARTIFACT,
    ACTIVE_DISCOVERY_FUNNEL_ARTIFACT,
    CERTIFICATION_ARTIFACT,
    CLAIM_SUMMARY_ARTIFACT,
    EXPERIMENT_BRIDGE_ARTIFACT,
    EXPERIMENT_SUMMARY_ARTIFACT,
    GRAPH_HEALTH_ARTIFACT,
    GRAPH_MANIFEST_ARTIFACT,
    MULTI_SETUP_ARTIFACT,
    OUTCOME_LEARNING_ARTIFACT,
    PAPER_ADMISSION_ARTIFACT,
    PATTERN_CANDIDATES_ARTIFACT,
    PHASE_IDS,
    QEG_DASHBOARD_ARTIFACT,
    QEG_RELIABILITY_ARTIFACT,
    QEG_TELEGRAM_ARTIFACT,
    QEG_TRIAL_ARTIFACT,
    QUANTUM_CHALLENGER_ARTIFACT,
    REFERENCE_SUMMARY_ARTIFACT,
    STRATEGY_VERSIONS_ARTIFACT,
    qeg_authority,
    write_phase_status,
)
from orchestrator.qadam_temporal_graph_contracts import (  # noqa: E402
    validate_negative_probes,
    validate_record,
)
from orchestrator.qadam_temporal_graph_store import (  # noqa: E402
    TemporalGraphStore,
    validate_store,
)

PHASE_CHECKS = (
    "scripts/check_qadam_qeg_baseline.py",
    "scripts/check_qadam_temporal_graph_contracts.py",
    "scripts/check_qadam_temporal_graph_store.py",
    "scripts/check_qadam_claim_reference_registry.py",
    "scripts/check_qadam_temporal_graph_ingestion.py",
    "scripts/check_qadam_experiment_memory.py",
    "scripts/check_qadam_graph_research_fanout.py",
    "scripts/check_qadam_graph_pattern_discovery.py",
    "scripts/check_qadam_actionability_queue.py",
    "scripts/check_qadam_graph_experiment_bridge.py",
    "scripts/check_qadam_graph_quantum_challenger.py",
    "scripts/check_qadam_strategy_foundry_v4.py",
    "scripts/check_qadam_paper_strategy_admission.py",
    "scripts/check_qadam_graph_active_discovery.py",
    "scripts/check_qadam_multi_setup_paperops.py",
    "scripts/check_qadam_graph_outcome_learning.py",
    "scripts/check_qadam_strategy_challenger_tournament.py",
    "scripts/check_qadam_qeg_dashboard.py",
    "scripts/check_qadam_qeg_telegram.py",
    "scripts/check_qadam_qeg_operator_reliability.py",
)

FORBIDDEN_TRUE_FLAGS = (
    "automatic_code_mutation_allowed",
    "automatic_risk_envelope_expansion_allowed",
    "broker_write_allowed",
    "execution_approval_allowed",
    "graph_can_create_strategy_authority",
    "graph_can_create_trade_authority",
    "graph_can_satisfy_source_quorum_alone",
    "live_broker_endpoint_allowed",
    "live_capital_enabled",
    "paper_growth_trial_calendar_advance_allowed",
    "paper_order_allowed",
    "proof_credit_allowed",
    "risk_approval_allowed",
    "simulated_elapsed_time_allowed",
    "telegram_command_path_enabled",
    "telegram_live_send_allowed",
    "telegram_trade_command_enabled",
    "trade_candidate_creation_allowed",
)


def _run_phase_check(script: str) -> dict[str, Any]:
    completed = subprocess.run(
        (str(ROOT / ".venv/bin/python"), str(ROOT / script)),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return {
        "script": script,
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _unique(rows: list[dict[str, Any]], key: str) -> bool:
    values = [str(row.get(key)) for row in rows if row.get(key)]
    return len(values) == len(set(values))


def _authority_errors(value: Any, path: str = "root") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        authority = value.get("authority")
        if isinstance(authority, dict):
            for key in FORBIDDEN_TRUE_FLAGS:
                if authority.get(key) is not False:
                    errors.append(f"{path}.authority.{key}")
        for key, child in value.items():
            if key != "authority":
                errors.extend(_authority_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_authority_errors(child, f"{path}[{index}]"))
    return errors


def _group(group_id: str, title: str, errors: list[str], details: dict[str, Any]) -> dict[str, Any]:
    clean = sorted(set(errors))
    return {
        "group_id": group_id,
        "title": title,
        "status": "passed" if not clean else "blocked",
        "passed": not clean,
        "errors": clean,
        "details": details,
    }


def build_certification(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    phase_results = [_run_phase_check(script) for script in PHASE_CHECKS]
    phase_errors = [f"phase_checker_failed:{row['script']}" for row in phase_results if not row["passed"]]

    baseline = read_json(runtime / "qadam_qeg_baseline.json")
    manifest = read_json(runtime / GRAPH_MANIFEST_ARTIFACT)
    health = read_json(runtime / GRAPH_HEALTH_ARTIFACT)
    claims = read_json(runtime / CLAIM_SUMMARY_ARTIFACT)
    references = read_json(runtime / REFERENCE_SUMMARY_ARTIFACT)
    memory = read_json(runtime / EXPERIMENT_SUMMARY_ARTIFACT)
    patterns = read_json(runtime / PATTERN_CANDIDATES_ARTIFACT)
    actionability = read_json(runtime / ACTIONABILITY_QUEUE_ARTIFACT)
    bridge = read_json(runtime / EXPERIMENT_BRIDGE_ARTIFACT)
    quantum = read_json(runtime / QUANTUM_CHALLENGER_ARTIFACT)
    versions = read_json(runtime / STRATEGY_VERSIONS_ARTIFACT)
    admission = read_json(runtime / PAPER_ADMISSION_ARTIFACT)
    funnel = read_json(runtime / ACTIVE_DISCOVERY_FUNNEL_ARTIFACT)
    multi_setup = read_json(runtime / MULTI_SETUP_ARTIFACT)
    learning = read_json(runtime / OUTCOME_LEARNING_ARTIFACT)
    tournament = read_json(runtime / "qadam_strategy_challenger_tournament.json")
    dashboard = read_json(runtime / QEG_DASHBOARD_ARTIFACT)
    telegram = read_json(runtime / QEG_TELEGRAM_ARTIFACT)
    reliability = read_json(runtime / QEG_RELIABILITY_ARTIFACT)
    trial = read_json(runtime / QEG_TRIAL_ARTIFACT)
    statistical = read_json(runtime / "qadam_statistical_backtest_checks.json")
    nonlinear = read_json(runtime / "qadam_nonlinear_quantum_value_checks.json")
    operator = read_json(runtime / "qadam_operator_service_status.json")

    store = TemporalGraphStore(active)
    graph_records = list(store.iter_events())
    node_ids = {
        str(row.get("node_id"))
        for row in graph_records
        if row.get("record_kind") == "node" and row.get("node_id")
    }
    dangling = sorted({
        str(row.get(endpoint))
        for row in graph_records
        if row.get("record_kind") == "edge"
        for endpoint in ("from_node_id", "to_node_id")
        if row.get(endpoint) and str(row.get(endpoint)) not in node_ids
    })
    contract_errors = [error for row in graph_records for error in validate_record(row)]

    pattern_rows = _rows(patterns, "candidates")
    queue_rows = _rows(actionability, "rows")
    experiment_rows = _rows(bridge, "experiments")
    comparison_rows = _rows(quantum, "comparisons")
    version_rows = _rows(versions, "versions")
    admission_rows = _rows(admission, "decisions")
    evaluation_rows = _rows(funnel, "evaluations")
    learning_rows = _rows(learning, "records")
    tournament_rows = _rows(tournament, "tournaments")

    groups: list[dict[str, Any]] = []
    groups.append(_group(
        "01", "Ontology And Provenance",
        contract_errors + (
            ["graph_record_missing_source_artifact"]
            if any(not row.get("source_artifact") for row in graph_records) else []
        ),
        {"graph_record_count": len(graph_records), "record_type_counts": dict(Counter(row.get("record_kind") for row in graph_records))},
    ))
    temporal_errors = list(validate_negative_probes())
    if any(not row.get("preregistered_before_outcome") for row in experiment_rows):
        temporal_errors.append("experiment_not_preregistered_before_outcome")
    if any(row.get("holdout_read_allowed") is not False for row in experiment_rows):
        temporal_errors.append("preregistered_holdout_not_sealed")
    groups.append(_group(
        "02", "Temporal Leakage And Point-In-Time Queries", temporal_errors,
        {"preregistered_experiment_count": len(experiment_rows), "point_in_time_cutoff_count": sum(bool(row.get("point_in_time_query_cutoff")) for row in experiment_rows)},
    ))
    store_errors = list(validate_store(active))
    if dangling:
        store_errors.append("dangling_graph_endpoint")
    if health.get("status") != "healthy" or int(health.get("event_validation_error_count") or 0):
        store_errors.append("graph_health_not_clean")
    groups.append(_group(
        "03", "Graph Rebuild And Storage Safety", store_errors,
        {"node_count": manifest.get("node_count"), "edge_count": manifest.get("edge_count"), "dangling_endpoint_count": len(dangling), "graph_health": health.get("status")},
    ))
    claim_errors: list[str] = []
    if int(claims.get("market_evidence_eligible_count") or 0) or int(claims.get("source_quorum_credit_count") or 0):
        claim_errors.append("unreviewed_claim_granted_market_evidence")
    if int(references.get("source_quorum_credit_count") or 0) or references.get("full_text_fetch_attempted") is not False:
        claim_errors.append("reference_registry_authority_or_fetch_violation")
    groups.append(_group(
        "04", "Claim And Reference Truth", claim_errors,
        {"claim_count": claims.get("claim_count"), "reference_count": references.get("reference_count"), "source_quorum_credit_count": 0},
    ))
    universe_errors: list[str] = []
    if baseline.get("source_count") != 41:
        universe_errors.append("source_universe_not_41")
    if baseline.get("instrument_count") != 19:
        universe_errors.append("trading_universe_not_19")
    scope = patterns.get("full_universe_search_scope") or {}
    if scope.get("source_count") != 41 or scope.get("instrument_count") != 19 or scope.get("pair_count") != 779:
        universe_errors.append("pattern_search_scope_mismatch")
    groups.append(_group("05", "Source And Universe Reconciliation", universe_errors, {"source_count": 41, "instrument_count": 19, "pair_count": 779}))

    experiment_errors: list[str] = []
    if int(memory.get("memory_record_count") or 0) <= 0:
        experiment_errors.append("experiment_memory_empty")
    if not _unique(experiment_rows, "experiment_id") or not _unique(experiment_rows, "attempt_fingerprint"):
        experiment_errors.append("duplicate_current_experiment_identity")
    if any(row.get("historical_result_created") or row.get("current_trigger_created") for row in experiment_rows):
        experiment_errors.append("preregistration_bridge_created_current_result")
    groups.append(_group(
        "06", "Experiment Memory And Novelty", experiment_errors,
        {"memory_record_count": memory.get("memory_record_count"), "negative_result_count": memory.get("negative_result_count"), "current_experiment_count": len(experiment_rows)},
    ))
    pattern_errors: list[str] = []
    if not pattern_rows or not _unique(pattern_rows, "pattern_relationship_id"):
        pattern_errors.append("pattern_identity_missing_or_duplicate")
    if patterns.get("patterns_are_not_strategies") is not True:
        pattern_errors.append("pattern_strategy_boundary_missing")
    if actionability.get("research_rank_separate_from_actionability") is not True or actionability.get("queue_continues_after_first_hold") is not True:
        pattern_errors.append("actionability_queue_contract_invalid")
    groups.append(_group(
        "07", "Pattern Discovery And Actionability", pattern_errors,
        {"pattern_count": len(pattern_rows), "actionability_row_count": len(queue_rows), "ready_for_preregistered_experiment_count": actionability.get("ready_for_preregistered_experiment_count")},
    ))
    backtest_errors: list[str] = []
    if statistical.get("status") != "passed" or int(statistical.get("holdout_tuning_violation_count") or 0):
        backtest_errors.append("statistical_backtest_or_holdout_failed")
    if int(statistical.get("false_discovery_adjusted_result_count") or 0) <= 0 or int(statistical.get("negative_control_executed_count") or 0) <= 0:
        backtest_errors.append("false_discovery_or_negative_control_missing")
    if int(statistical.get("negative_control_promotion_gate_breach_count") or 0):
        backtest_errors.append("negative_control_promotion_breach")
    groups.append(_group(
        "08", "Backtest And False-Discovery Controls", backtest_errors,
        {"registered_experiment_count": bridge.get("backtest_registry_experiment_count"), "attempted_hypothesis_count": statistical.get("attempted_hypothesis_count"), "validated_edge_count": statistical.get("validated_edge_count")},
    ))
    quantum_errors: list[str] = []
    if quantum.get("status") != "passed" or not comparison_rows:
        quantum_errors.append("quantum_challenger_missing_or_blocked")
    if int(nonlinear.get("classical_baseline_missing_count") or 0) or int(nonlinear.get("holdout_tuning_violation_count") or 0):
        quantum_errors.append("quantum_classical_fairness_failed")
    if any(row.get("quantum_is_trade_approval") is True for row in comparison_rows):
        quantum_errors.append("quantum_trade_authority_violation")
    groups.append(_group(
        "09", "Quantum And Classical Fairness", quantum_errors,
        {"comparison_count": len(comparison_rows), "quantum_value_state": quantum.get("quantum_value_state"), "useful_quantum_comparison_count": nonlinear.get("useful_quantum_comparison_count")},
    ))
    strategy_errors: list[str] = []
    if versions.get("status") != "passed" or admission.get("status") != "passed":
        strategy_errors.append("strategy_foundry_or_admission_blocked")
    if not _unique(version_rows, "strategy_version_id") or not _unique(admission_rows, "admission_decision_id"):
        strategy_errors.append("duplicate_strategy_or_admission_identity")
    if int(admission.get("admitted_count") or 0) > len(version_rows):
        strategy_errors.append("admission_without_strategy_version")
    groups.append(_group(
        "10", "Strategy Admission And Rollback", strategy_errors,
        {"strategy_version_count": len(version_rows), "admitted_strategy_count": admission.get("admitted_count"), "rejection_count": versions.get("rejection_count")},
    ))
    akber_errors: list[str] = []
    if funnel.get("status") != "passed" or int(funnel.get("available_evidence_reported_missing_due_to_contract_shape_count") or 0):
        akber_errors.append("akber_evidence_fit_contract_failed")
    required_hard_fields = {
        "current_price", "spread", "liquidity", "positive_expectancy_after_costs",
        "invalidation", "route", "risk_capacity",
    }
    if not required_hard_fields.issubset(set(funnel.get("hard_fields_never_substituted") or [])):
        akber_errors.append("hard_akber_field_substitution_detected")
    if not _unique(evaluation_rows, "evaluation_id"):
        akber_errors.append("duplicate_akber_evaluation_identity")
    groups.append(_group(
        "11", "Akber Evidence Fit", akber_errors,
        {"evaluated_count": funnel.get("evaluated_count"), "akber_entered_count": funnel.get("akber_entered_count"), "akber_pass_count": funnel.get("akber_pass_count")},
    ))
    routing_errors: list[str] = []
    if multi_setup.get("status") != "passed" or multi_setup.get("canonical_wrapper") != "scripts/run_paperops_autonomous_pass.py":
        routing_errors.append("noncanonical_or_blocked_paperops_route")
    if multi_setup.get("canonical_wrapper_only") is not True or multi_setup.get("qeg_parallel_order_route_created") is not False:
        routing_errors.append("parallel_order_route_violation")
    if int(multi_setup.get("broker_write_count") or 0) or multi_setup.get("paper_order_created_by_audit") is not False:
        routing_errors.append("multi_setup_audit_created_execution")
    groups.append(_group(
        "12", "Multi-Setup Risk, Router And PaperOps", routing_errors,
        {"decision_count": multi_setup.get("decision_count"), "handoff_count": multi_setup.get("handoff_count"), "canonical_wrapper": multi_setup.get("canonical_wrapper")},
    ))
    learning_errors: list[str] = []
    if learning.get("status") != "passed" or tournament.get("status") != "passed":
        learning_errors.append("learning_or_challenger_tournament_blocked")
    if int(tournament.get("automatic_promotion_count") or 0):
        learning_errors.append("automatic_strategy_promotion_detected")
    groups.append(_group(
        "13", "Outcome And Learning Lineage", learning_errors,
        {"learning_record_count": len(learning_rows), "matured_record_count": learning.get("matured_record_count"), "tournament_count": len(tournament_rows)},
    ))
    visibility_errors: list[str] = []
    if dashboard.get("status") != "current" or dashboard.get("read_only") is not True or dashboard.get("command_disabled") is not True:
        visibility_errors.append("dashboard_projection_boundary_failed")
    if telegram.get("delivery_attempted") is not False or telegram.get("telegram_command_path_enabled") is not False:
        visibility_errors.append("telegram_boundary_failed")
    groups.append(_group(
        "14", "Dashboard And Telegram Quality", visibility_errors,
        {"dashboard_status": dashboard.get("status"), "telegram_status": telegram.get("status"), "material_changed": telegram.get("material_changed")},
    ))
    reliability_errors: list[str] = []
    if reliability.get("status") != "passed" or reliability.get("graph_health") != "healthy":
        reliability_errors.append("qeg_reliability_not_passed")
    if operator.get("implementation_ready") is not True or operator.get("operational_ready") is not True or operator.get("observation_ready") is not True:
        reliability_errors.append("operator_not_observation_ready")
    if int(operator.get("open_circuit_count") or 0) or int((operator.get("repair_queue") or {}).get("open_request_count") or 0):
        reliability_errors.append("operator_circuit_or_repair_open")
    if int(trial.get("simulated_elapsed_day_count") or 0) or int(trial.get("backfilled_elapsed_day_count") or 0) or trial.get("paper_growth_trial_calendar_advanced") is not False:
        reliability_errors.append("real_market_trial_calendar_violation")
    groups.append(_group(
        "15", "Reliability And Unattended Recovery", reliability_errors,
        {"operator_service_count": operator.get("service_count"), "open_circuit_count": operator.get("open_circuit_count"), "repair_request_count": (operator.get("repair_queue") or {}).get("open_request_count"), "real_market_days": trial.get("completed_real_market_day_count"), "target_real_market_days": trial.get("target_real_market_days")},
    ))

    qeg_payloads = {
        "patterns": patterns,
        "actionability": actionability,
        "bridge": bridge,
        "quantum": quantum,
        "versions": versions,
        "admission": admission,
        "funnel": funnel,
        "multi_setup": multi_setup,
        "learning": learning,
        "tournament": tournament,
        "dashboard": dashboard,
        "telegram": telegram,
        "reliability": reliability,
        "trial": trial,
    }
    authority_errors = [
        error
        for name, payload in qeg_payloads.items()
        for error in _authority_errors(payload, name)
    ]
    count_errors: list[str] = []
    for name, payload in qeg_payloads.items():
        for key in ("paper_order_created_count", "broker_write_count", "proof_credit_created_count"):
            if int(payload.get(key) or 0):
                count_errors.append(f"{name}.{key}")
    groups.append(_group(
        "16", "Paper-Only And Live-Capital Negative Probes",
        authority_errors + count_errors,
        {"negative_authority_error_count": len(authority_errors), "execution_count_error_count": len(count_errors), "live_capital_enabled": False},
    ))

    group_errors = [f"group_blocked:{group['group_id']}:{error}" for group in groups for error in group["errors"]]
    errors = sorted(set([*phase_errors, *group_errors]))
    implementation_certified = not errors
    real_days = int(trial.get("completed_real_market_day_count") or 0)
    target_days = int(trial.get("target_real_market_days") or 5)
    trial_complete = real_days >= target_days and trial.get("status") == "active_discovery_trial_complete"
    empirical_edge_validated = int(statistical.get("validated_edge_count") or 0) > 0
    if not implementation_certified:
        certification_state = "implementation_incomplete"
    elif trial_complete:
        certification_state = "operating_as_designed"
    else:
        certification_state = "active_discovery_trial_running"

    phase_status = write_phase_status(
        "QEG-16",
        status="passed" if implementation_certified else "blocked",
        implementation_complete=implementation_certified,
        empirical_state=certification_state,
        artifacts=[CERTIFICATION_ARTIFACT],
        blockers=errors,
        settings=active,
    )
    payload = {
        "schema_version": "qadam_compounding_evidence_graph_certification.v1",
        "artifact_type": "qadam_compounding_evidence_graph_certification",
        "generated_at": now_iso(),
        "status": "passed" if implementation_certified else "blocked",
        "implementation_certified": implementation_certified,
        "certification_state": certification_state,
        "operating_as_designed": implementation_certified and trial_complete,
        "empirical_edge_validated": empirical_edge_validated,
        "profitability_proven": False,
        "trial_complete": trial_complete,
        "completed_real_market_day_count": real_days,
        "target_real_market_day_count": target_days,
        "phase_checker_count": len(phase_results),
        "phase_checker_pass_count": sum(row["passed"] for row in phase_results),
        "certification_group_count": len(groups),
        "passed_group_count": sum(group["passed"] for group in groups),
        "blocked_group_count": sum(not group["passed"] for group in groups),
        "phase_implementation_complete_count": phase_status.get("implementation_complete_phase_count"),
        "phase_count": len(PHASE_IDS),
        "groups": groups,
        "phase_check_results": phase_results,
        "blockers": errors,
        "paper_order_forced": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "paper_growth_trial_calendar_advanced": False,
        "authority": qeg_authority(governed_projection=True),
    }
    write_json_atomic(runtime / CERTIFICATION_ARTIFACT, payload)
    return payload, errors


def main() -> int:
    payload, errors = build_certification()
    print(f"status={payload['status']}")
    print(f"implementation_certified={payload['implementation_certified']}")
    print(f"certification_state={payload['certification_state']}")
    print(f"operating_as_designed={payload['operating_as_designed']}")
    print(f"empirical_edge_validated={payload['empirical_edge_validated']}")
    print(f"phase_checker_pass_count={payload['phase_checker_pass_count']}/{payload['phase_checker_count']}")
    print(f"passed_group_count={payload['passed_group_count']}/{payload['certification_group_count']}")
    print(f"real_market_days={payload['completed_real_market_day_count']}/{payload['target_real_market_day_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
