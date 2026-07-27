"""OR-19 fail-closed operator-ready edge-engine certification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_operator_ready_edge_engine_certification.v1"
PHASE_ID = "OR-19"

CERTIFICATION_ARTIFACT = "qadam_operator_ready_edge_engine_certification.json"
CHECK_ARTIFACT = "qadam_operator_ready_edge_engine_checks.json"

ARTIFACTS = {
    "phase_status": "qadam_operator_ready_phase_status.json",
    "source_capabilities": "qadam_source_provider_capabilities_checks.json",
    "or3_readiness": "qadam_or3_acquisition_readiness.json",
    "provider_backfill": "qadam_provider_backfill_checks.json",
    "point_in_time": "qadam_point_in_time_evidence_checks.json",
    "historical_gaps": "qadam_historical_gap_resolution_checks.json",
    "backtest_recertification": "qadam_backtest_recertification.json",
    "score_tape": "qadam_pattern_score_tape_checks.json",
    "forward_labels": "qadam_forward_labels_checks.json",
    "backtest": "qadam_statistical_backtest_checks.json",
    "contract_audit": "qadam_certification_contract_audit.json",
    "nonlinear": "qadam_nonlinear_quantum_value_checks.json",
    "edges": "qadam_edge_registry_checks.json",
    "foundry": "qadam_strategy_foundry_v3_checks.json",
    "akber": "qadam_akber_filter_v3_checks.json",
    "shadow": "qadam_forward_shadow_checks.json",
    "risk": "qadam_portfolio_risk_engine_checks.json",
    "router": "qadam_router_v3_paperops_checks.json",
    "release": "qadam_research_lock_release_readiness.json",
    "lifecycle": "qadam_paper_lineage_and_proof_checks.json",
    "dashboard": "qadam_operator_dashboard_checks.json",
    "dashboard_freshness": "qadam_operator_dashboard_freshness.json",
    "communications": "qadam_operator_communications_mirror.json",
    "anti_slop": "qsase_dashboard_anti_slop_audit.json",
    "service": "qadam_operator_service_checks.json",
    "service_status": "qadam_operator_service_status.json",
    "service_soak": "qadam_operator_soak_v2.json",
    "permanent_reliability": "qadam_permanent_operator_reliability_certification.json",
    "repair_queue": "qadam_operator_repair_queue.json",
    "lock": "qadam_long_backtest_lock.json",
}

GROUP_ORDER = (
    "canonical_truth",
    "research_operations",
    "evidence_and_edge",
    "akber_shadow_and_portfolio",
    "router_and_paperops",
    "lifecycle_and_proof",
    "operator_experience",
    "universal_negative_safety",
)


@dataclass(frozen=True, kw_only=True)
class CertificationCheck:
    check_id: str
    label: str
    passed: bool
    observed: Any
    expected: str
    evidence_artifact: str
    blocker: str | None = None
    not_applicable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "label": self.label,
            "passed": self.passed,
            "observed": self.observed,
            "expected": self.expected,
            "evidence_artifact": f"data/runtime/{self.evidence_artifact}",
            "credit_basis": "measured_field_or_cross_artifact_invariant",
            "existence_only_credit": False,
            "not_applicable": self.not_applicable,
            "blocker": None if self.passed else self.blocker,
        }


def _check(
    check_id: str,
    label: str,
    passed: bool,
    observed: Any,
    expected: str,
    evidence_key: str,
    blocker: str,
    *,
    not_applicable: bool = False,
) -> CertificationCheck:
    return CertificationCheck(
        check_id=check_id,
        label=label,
        passed=bool(passed),
        observed=observed,
        expected=expected,
        evidence_artifact=ARTIFACTS[evidence_key],
        blocker=blocker,
        not_applicable=not_applicable,
    )


def _freshness_state(payload: dict[str, Any], artifact_name: str) -> str:
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    expected = f"data/runtime/{artifact_name}"
    record = next((item for item in records if item.get("artifact") == expected), {})
    return str(record.get("freshness_state") or "missing")


def _operator_service_process_is_running(service: dict[str, Any]) -> bool:
    """Keep process health separate from the real-session readiness gate."""

    return service.get("service_installed") is True and service.get("service_running") is True


def _group(group_id: str, checks: list[CertificationCheck]) -> dict[str, Any]:
    rows = [check.to_dict() for check in checks]
    failed = [row for row in rows if not row["passed"]]
    return {
        "group_id": group_id,
        "status": "passed" if not failed else "blocked",
        "passed": not failed,
        "check_count": len(rows),
        "passed_check_count": len(rows) - len(failed),
        "failed_check_count": len(failed),
        "checks": rows,
        "blockers": [
            {
                "check_id": row["check_id"],
                "reason": row["blocker"],
                "observed": row["observed"],
                "expected": row["expected"],
            }
            for row in failed
        ],
    }


def _load_inputs(settings: Settings | None = None) -> dict[str, dict[str, Any]]:
    runtime = runtime_dir(settings)
    return {key: read_json(runtime / filename) for key, filename in ARTIFACTS.items()}


def build_operator_ready_certification(
    settings: Settings | None = None,
    *,
    mode: str = "full",
) -> dict[str, Any]:
    inputs = _load_inputs(settings)
    phase_status = inputs["phase_status"]
    phases = phase_status.get("phases") if isinstance(phase_status.get("phases"), dict) else {}
    source = inputs["source_capabilities"]
    or3_readiness = inputs["or3_readiness"]
    backfill = inputs["provider_backfill"]
    point_in_time = inputs["point_in_time"]
    historical_gaps = inputs["historical_gaps"]
    backtest_recertification = inputs["backtest_recertification"]
    score_tape = inputs["score_tape"]
    labels = inputs["forward_labels"]
    backtest = inputs["backtest"]
    contract_audit = inputs["contract_audit"]
    nonlinear = inputs["nonlinear"]
    edges = inputs["edges"]
    foundry = inputs["foundry"]
    akber = inputs["akber"]
    shadow = inputs["shadow"]
    risk = inputs["risk"]
    router = inputs["router"]
    release = inputs["release"]
    lifecycle = inputs["lifecycle"]
    dashboard = inputs["dashboard"]
    dashboard_freshness = inputs["dashboard_freshness"]
    communications = inputs["communications"]
    anti_slop = inputs["anti_slop"]
    service = inputs["service"]
    service_status = inputs["service_status"]
    service_soak = inputs["service_soak"]
    permanent_reliability = inputs["permanent_reliability"]
    repair_queue = inputs["repair_queue"]
    lock = inputs["lock"]
    legacy_soak_complete = bool(
        service_soak.get("soak_complete") is True
        or service_soak.get("multi_session_soak_complete") is True
    )
    soak_session_count = int(
        service_soak.get("completed_real_session_count")
        or service_soak.get("real_elapsed_session_count")
        or 0
    )

    prior_phase_states = {
        phase: phases.get(phase, {}).get("state") for phase in phases if phase != PHASE_ID
    }
    prior_phase_evidence_present = (
        all(
            state in {"passed", "evidence_maturing", "superseded_by_reviewed_amendment"}
            for state in prior_phase_states.values()
        )
        and phases.get("OR-17", {}).get("state") == "passed"
        and phases.get("OR-18", {}).get("state") in {"passed", "evidence_maturing"}
    )
    taxonomy_counts = {
        "registered_sources": source.get("registered_source_count"),
        "operational_sources": source.get("operational_state_count"),
        "backfill_sources": backfill.get("source_count"),
        "backfill_instruments": backfill.get("instrument_count"),
        "readiness_sources": or3_readiness.get("source_count"),
        "readiness_instruments": or3_readiness.get("instrument_count"),
    }
    taxonomy_consistent = (
        taxonomy_counts["registered_sources"]
        == taxonomy_counts["operational_sources"]
        == taxonomy_counts["backfill_sources"]
        == taxonomy_counts["readiness_sources"]
        and taxonomy_counts["backfill_instruments"] == taxonomy_counts["readiness_instruments"]
        and int(taxonomy_counts["backfill_instruments"] or 0) > 0
    )
    lock_state_agrees = (
        lock.get("status") == "active"
        and release.get("research_lock_active") is True
        and release.get("release_effective") is False
        and dashboard.get("runtime_state") == "research-only"
        and service.get("paperops_watch_only") is True
    )
    stale_count = int(dashboard.get("stale_count") or 0) + int(dashboard.get("missing_count") or 0)
    canonical_truth = _group(
        "canonical_truth",
        [
            _check(
                "research.or2r_acquisition_ready",
                "OR-2R connection truth and acquisition readiness passed before OR-3",
                or3_readiness.get("status") == "ready"
                and or3_readiness.get("or3_start_allowed") is True
                and or3_readiness.get("pilot_status") == "passed"
                and int(or3_readiness.get("pilot_provider_row_count") or 0) > 0,
                {
                    "status": or3_readiness.get("status"),
                    "or3_start_allowed": or3_readiness.get("or3_start_allowed"),
                    "pilot_status": or3_readiness.get("pilot_status"),
                    "operator_actions": or3_readiness.get("operator_action_count"),
                },
                "ready with a real provider-backed pilot and no unresolved acquisition actions",
                "or3_readiness",
                "OR-3 remains blocked by provider selection, licensing, budget, or acquisition-readiness work.",
            ),
            _check(
                "canonical.certification_contracts_current",
                "Provider, point-in-time, and backtest certification contracts agree",
                contract_audit.get("status") == "passed"
                and int(contract_audit.get("validation_error_count") or 0) == 0,
                {
                    "status": contract_audit.get("status"),
                    "validation_errors": contract_audit.get("validation_errors"),
                },
                "contract audit passed with zero validation errors",
                "contract_audit",
                "Certification inputs use incompatible fields or terminal-state semantics.",
            ),
            _check(
                "canonical.source_taxonomy_consistent",
                "Source and instrument counts use one taxonomy",
                taxonomy_consistent,
                taxonomy_counts,
                "registered, operational, and backfill source counts agree; instruments are classified",
                "source_capabilities",
                "Source or instrument taxonomy counts still disagree.",
            ),
            _check(
                "canonical.prior_phase_evidence_recorded",
                "All earlier phases have checker-backed state",
                prior_phase_evidence_present,
                {
                    "OR-17": phases.get("OR-17", {}).get("state"),
                    "OR-18": phases.get("OR-18", {}).get("state"),
                },
                "OR-17 and OR-18 passed; all earlier phases passed or are honestly evidence-maturing",
                "phase_status",
                "One or more prior phase states are absent or unsupported.",
            ),
            _check(
                "canonical.runtime_state_agrees",
                "Lock, release, dashboard, and service agree",
                lock_state_agrees,
                {
                    "lock": lock.get("status"),
                    "release_effective": release.get("release_effective"),
                    "dashboard": dashboard.get("runtime_state"),
                    "paperops_watch_only": service.get("paperops_watch_only"),
                },
                "active research lock, research-only dashboard, watch-only PaperOps, no effective release",
                "lock",
                "The canonical runtime surfaces disagree about whether execution is released.",
            ),
            _check(
                "canonical.paper_trial_calendar_preserved",
                "30-day paper growth trial calendar is not simulated",
                lock.get("paper_growth_trial_calendar_advance_allowed") is False
                and service_soak.get("simulated_elapsed_time_used") is False,
                {
                    "calendar_advance_allowed": lock.get(
                        "paper_growth_trial_calendar_advance_allowed"
                    ),
                    "simulated_elapsed_time": service_soak.get("simulated_elapsed_time_used"),
                },
                "false for calendar backfill and simulated elapsed time",
                "lock",
                "A research or soak artifact would alter real trial time.",
            ),
            _check(
                "canonical.required_artifacts_fresh",
                "Required operator artifacts are fresh",
                stale_count == 0,
                {"stale_or_missing_count": stale_count},
                "0 stale or missing monitored artifacts",
                "dashboard_freshness",
                "Monitored artifacts remain stale or missing and cannot support current decisions.",
            ),
        ],
    )

    heartbeat_state = _freshness_state(
        dashboard_freshness, "qadam_research_supervisor_heartbeat.json"
    )
    research_operations = _group(
        "research_operations",
        [
            _check(
                "research.supervisor_live_and_fresh",
                "Research supervisor is running with a fresh heartbeat",
                service_status.get("service_running") is True and heartbeat_state == "fresh",
                {
                    "service_running": service_status.get("service_running"),
                    "heartbeat_freshness": heartbeat_state,
                },
                "service running and heartbeat fresh",
                "service_status",
                "The unattended service is not running or its research heartbeat is stale.",
            ),
            _check(
                "research.sources_and_instruments_classified",
                "Every source and instrument is classified",
                taxonomy_consistent
                and int(source.get("operational_state_count") or 0) > 0
                and int(backfill.get("instrument_count") or 0) > 0,
                taxonomy_counts,
                "all registered sources and the trading universe have operational classifications",
                "source_capabilities",
                "Source or trading-universe classification is incomplete.",
            ),
            _check(
                "research.provider_history_acquired",
                "Provider-backed historical acquisition has one terminal state per partition",
                backfill.get("provider_history_acquisition_contract_complete") is True
                and backfill.get("or3_acceptance_passed") is True
                and int(backfill.get("provider_row_count") or 0) > 0
                and int(backfill.get("remaining_partition_count") or 0) == 0
                and (
                    int(backfill.get("completed_partition_count") or 0)
                    + int(backfill.get("unavailable_classified_partition_count") or 0)
                )
                == int(backfill.get("total_partition_count") or -1),
                {
                    "provider_rows": backfill.get("provider_row_count"),
                    "acquired_partitions": backfill.get("completed_partition_count"),
                    "classified_unavailable_partitions": backfill.get(
                        "unavailable_classified_partition_count"
                    ),
                    "remaining_partitions": backfill.get("remaining_partition_count"),
                    "total_partitions": backfill.get("total_partition_count"),
                },
                "provider rows > 0 and every planned partition acquired or honestly classified unavailable",
                "provider_backfill",
                "Historical acquisition still contains an unfinished or unclassified partition.",
            ),
            _check(
                "research.required_sources_fresh",
                "A usable fresh source set is present without unresolved acquisition defects",
                int(source.get("fresh_scoring_eligible_count") or 0) > 0
                and int(source.get("blocking_repair_request_count") or 0) == 0,
                {
                    "fresh_scoring_eligible": source.get("fresh_scoring_eligible_count"),
                    "blocking_repairs": source.get("blocking_repair_request_count"),
                    "visible_nonblocking_repairs": source.get("nonblocking_repair_request_count"),
                },
                "fresh scoring-eligible sources > 0 and blocking repair requests = 0",
                "source_capabilities",
                "A provider required by the current scoring set still needs repair.",
            ),
            _check(
                "research.no_critical_resource_block",
                "No critical operator repair is open",
                int(repair_queue.get("critical_request_count") or 0) == 0,
                repair_queue.get("critical_request_count"),
                "0 critical repair requests",
                "repair_queue",
                "A critical resource, provider, or service repair remains open.",
            ),
        ],
    )

    evidence_and_edge = _group(
        "evidence_and_edge",
        [
            _check(
                "edge.historical_gaps_terminal_and_typed",
                "Historical provider partitions and legacy gaps are terminally classified",
                historical_gaps.get("acceptance_passed") is True
                and int(historical_gaps.get("provider_partition_remaining_count") or 0) == 0
                and int(historical_gaps.get("legacy_rows_mutated_or_backfilled") or 0) == 0,
                {
                    "provider_partitions_remaining": historical_gaps.get(
                        "provider_partition_remaining_count"
                    ),
                    "legacy_gaps_visible": historical_gaps.get(
                        "legacy_missing_or_ineligible_count"
                    ),
                    "legacy_rows_mutated": historical_gaps.get("legacy_rows_mutated_or_backfilled"),
                },
                "all provider partitions terminal; legacy gaps typed and never fabricated",
                "historical_gaps",
                "Historical acquisition or typed gap resolution is incomplete.",
            ),
            _check(
                "edge.backtest_recertified",
                "Frozen statistical protocol is recertified after provider alignment",
                backtest_recertification.get("research_protocol_valid") is True
                and int(backtest_recertification.get("leakage_violation_count") or 0) == 0
                and int(backtest_recertification.get("holdout_tuning_violation_count") or 0) == 0,
                {
                    "status": backtest_recertification.get("status"),
                    "validated_edges": backtest_recertification.get("validated_edge_count"),
                    "leakage_violations": backtest_recertification.get("leakage_violation_count"),
                },
                "research protocol valid with zero leakage and holdout tuning violations",
                "backtest_recertification",
                "The provider-backed backtest has not been safely recertified.",
            ),
            _check(
                "edge.point_in_time_leakage_clear",
                "Point-in-time alignment has no eligible leakage violations",
                int(point_in_time.get("eligible_leakage_violation_count") or 0) == 0,
                point_in_time.get("eligible_leakage_violation_count"),
                "0 eligible leakage violations",
                "point_in_time",
                "Point-in-time leakage remains in eligible evidence.",
            ),
            _check(
                "edge.typed_evidence_complete",
                "Provider-backed point-in-time evidence is complete enough for historical scoring",
                int(point_in_time.get("eligible_forward_score_input_count") or 0) > 0
                and int(point_in_time.get("provider_alignment_record_count") or 0) > 0
                and int(point_in_time.get("eligible_leakage_violation_count") or 0) == 0,
                {
                    "current_trade_context_complete": point_in_time.get(
                        "typed_evidence_completed_count"
                    ),
                    "eligible_score_inputs": point_in_time.get(
                        "eligible_forward_score_input_count"
                    ),
                    "provider_alignment_records": point_in_time.get(
                        "provider_alignment_record_count"
                    ),
                    "current_trade_context_gaps": point_in_time.get("typed_evidence_gap_count"),
                },
                "provider alignment and eligible historical score inputs > 0 with zero leakage",
                "point_in_time",
                "Provider-backed historical evidence is not yet safe to score point in time.",
            ),
            _check(
                "edge.score_tape_empirical",
                "Point-in-time score tape contains provider-backed rows",
                score_tape.get("empirical_score_tape_complete") is True
                and int(score_tape.get("score_tape_row_count") or 0) > 0,
                score_tape.get("score_tape_row_count"),
                "provider-backed score tape rows > 0",
                "score_tape",
                "No empirical point-in-time score tape rows have accumulated.",
            ),
            _check(
                "edge.forward_labels_empirical",
                "Forward labels exist and remain separated from scores",
                labels.get("empirical_labels_complete") is True
                and int(labels.get("label_count") or 0) > 0
                and int(labels.get("score_label_order_violation_count") or 0) == 0,
                {
                    "labels": labels.get("label_count"),
                    "order_violations": labels.get("score_label_order_violation_count"),
                },
                "labels > 0 and score/label order violations = 0",
                "forward_labels",
                "Outcome labels have not matured from real forward windows.",
            ),
            _check(
                "edge.walk_forward_and_holdout_complete",
                "Walk-forward and untouched-holdout tests exist",
                backtest.get("empirical_backtest_complete") is True
                and int(backtest.get("fold_result_count") or backtest.get("fold_count") or 0) > 0
                and int(backtest.get("untouched_holdout_result_count") or 0) > 0
                and int(backtest.get("holdout_tuning_violation_count") or 0) == 0,
                {
                    "folds": backtest.get("fold_result_count") or backtest.get("fold_count"),
                    "untouched_holdout_results": backtest.get("untouched_holdout_result_count"),
                    "holdout_tuning_violations": backtest.get("holdout_tuning_violation_count"),
                },
                "folds and untouched holdout results > 0; holdout tuning violations = 0",
                "backtest",
                "The empirical walk-forward or untouched-holdout test is incomplete.",
            ),
            _check(
                "edge.negative_controls_clean",
                "Negative controls executed and did not become apparent edges",
                int(backtest.get("negative_control_executed_count") or 0) > 0
                and int(backtest.get("negative_control_validated_count") or 0) == 0
                and int(backtest.get("negative_control_promotion_gate_breach_count") or 0) == 0,
                {
                    "executed": backtest.get("negative_control_executed_count"),
                    "statistically_positive": backtest.get(
                        "negative_control_statistically_positive_count"
                    ),
                    "promotion_gate_breaches": backtest.get(
                        "negative_control_promotion_gate_breach_count"
                    ),
                    "validated": backtest.get("negative_control_validated_count"),
                },
                "negative controls executed > 0; promotion-gate breaches = 0; validated = 0",
                "backtest",
                "A negative control survived the ordinary promotion gates or was improperly validated.",
            ),
            _check(
                "edge.validated_edge_exists",
                "At least one edge passes frozen out-of-sample promotion policy",
                int(backtest.get("validated_edge_count") or 0) > 0
                and edges.get("edge_validated_certification_passed") is True,
                {
                    "validated_edges": backtest.get("validated_edge_count"),
                    "registry_certified": edges.get("edge_validated_certification_passed"),
                },
                "validated edge count > 0 and registry certification passed",
                "edges",
                "No edge has positive validated out-of-sample evidence under the frozen policy.",
            ),
            _check(
                "edge.quantum_claim_honest",
                "Quantum/nonlinear contribution is measured against a classical baseline",
                int(nonlinear.get("classical_baseline_missing_count") or 0) == 0
                and (
                    int(nonlinear.get("measured_comparison_count") or 0) > 0
                    or nonlinear.get("quantum_usefulness_score") is None
                )
                and nonlinear.get("hardware_submission_attempted") is False,
                {
                    "measured_comparisons": nonlinear.get("measured_comparison_count"),
                    "usefulness_score": nonlinear.get("quantum_usefulness_score"),
                    "hardware_submission_attempted": nonlinear.get("hardware_submission_attempted"),
                },
                "measured incremental value or an explicit not-yet-measurable state; no authority",
                "nonlinear",
                "Quantum usefulness is being overstated or lacks its classical baseline.",
            ),
        ],
    )

    no_router_setup = int(router.get("setup_count") or 0) == 0
    akber_shadow_portfolio = _group(
        "akber_shadow_and_portfolio",
        [
            _check(
                "akber.complete_context_for_router_eligible_setups",
                "Every Router-eligible setup has complete six-stage Akber context",
                no_router_setup
                or (
                    int(akber.get("input_count") or 0) == int(router.get("setup_count") or 0)
                    and int(akber.get("result_count") or 0) == int(router.get("setup_count") or 0)
                ),
                {
                    "router_setups": router.get("setup_count"),
                    "akber_inputs": akber.get("input_count"),
                    "akber_results": akber.get("result_count"),
                },
                "one complete Akber input and result per Router-eligible setup",
                "akber",
                "One or more Router-eligible setups lack complete Akber context.",
                not_applicable=no_router_setup,
            ),
            _check(
                "akber.historical_contribution_measured",
                "Akber replay and ablation show whether the filter adds value",
                akber.get("net_historical_contribution_measurable") is True
                and int(akber.get("historical_replay_count") or 0) > 0
                and int(akber.get("ablation_count") or 0) > 0,
                {
                    "replays": akber.get("historical_replay_count"),
                    "ablations": akber.get("ablation_count"),
                    "measurable": akber.get("net_historical_contribution_measurable"),
                },
                "historical replays and ablations > 0 with measurable net contribution",
                "akber",
                "Akber has no empirical replay or ablation evidence yet.",
            ),
            _check(
                "shadow.real_elapsed_evidence",
                "Forward shadow evidence uses real elapsed time",
                shadow.get("promotion_ready") is True
                and int(shadow.get("outcome_count") or 0) > 0
                and float(shadow.get("real_elapsed_days") or 0.0) > 0.0,
                {
                    "outcomes": shadow.get("outcome_count"),
                    "real_elapsed_days": shadow.get("real_elapsed_days"),
                    "service_running": shadow.get("shadow_service_running"),
                },
                "real forward outcomes and elapsed days > 0; promotion policy passed",
                "shadow",
                "No eligible hypothesis has accumulated real-time forward shadow evidence.",
            ),
            _check(
                "portfolio.frozen_risk_policy_valid",
                "Frozen portfolio-risk policy is valid and non-authoritative",
                risk.get("status") == "passed"
                and risk.get("policy_version")
                and int(risk.get("risk_approval_created_count") or 0) == 0
                and int(risk.get("execution_approval_created_count") or 0) == 0,
                {
                    "status": risk.get("status"),
                    "policy_version": risk.get("policy_version"),
                    "risk_approvals_created": risk.get("risk_approval_created_count"),
                },
                "valid frozen policy; no risk or execution approval created",
                "risk",
                "Portfolio risk policy or its authority boundary is invalid.",
            ),
        ],
    )

    router_and_paperops = _group(
        "router_and_paperops",
        [
            _check(
                "router.exactly_one_state_per_setup",
                "Every setup has exactly one Router state",
                router.get("status") == "passed"
                and int(router.get("decision_count") or 0) == int(router.get("setup_count") or 0),
                {"setups": router.get("setup_count"), "decisions": router.get("decision_count")},
                "decision count equals setup count and checker passed",
                "router",
                "Router state is missing or duplicated for at least one setup.",
                not_applicable=no_router_setup,
            ),
            _check(
                "router.clean_handoffs_only",
                "Only clean paper-review candidates reach PaperOps handoff",
                int(router.get("handoff_count") or 0)
                <= int(router.get("paper_review_candidate_count") or 0)
                and int(router.get("paper_order_created_count") or 0) == 0,
                {
                    "paper_review_candidates": router.get("paper_review_candidate_count"),
                    "handoffs": router.get("handoff_count"),
                    "orders_created": router.get("paper_order_created_count"),
                },
                "handoffs do not exceed clean candidates and handoffs create no orders",
                "router",
                "An unclean setup reached handoff or the handoff created an order.",
            ),
            _check(
                "router.release_readiness_recommended",
                "Research lock release is recommended only after all readiness gates",
                release.get("release_recommended") is True,
                {
                    "release_recommended": release.get("release_recommended"),
                    "nonpassing_phases": release.get("nonpassing_phases"),
                },
                "release_recommended=true after empirical and shadow gates pass",
                "release",
                "The guarded release checker still holds because evidence phases are nonpassing.",
            ),
            _check(
                "router.no_premature_release",
                "Research lock has not been released prematurely",
                release.get("release_effective") is False and lock.get("status") == "active",
                {"release_effective": release.get("release_effective"), "lock": lock.get("status")},
                "release_effective=false while readiness is incomplete",
                "release",
                "The research lock was released before certification.",
            ),
            _check(
                "router.guarded_paper_route_only",
                "Guarded Alpaca Paper is the only permitted broker-write boundary",
                router.get("live_capital_enabled") is False
                and int(router.get("broker_write_count") or 0) == 0,
                {
                    "live_capital": router.get("live_capital_enabled"),
                    "broker_writes": router.get("broker_write_count"),
                },
                "live capital false and unauthorized broker writes = 0",
                "router",
                "An unauthorized or live-capital route is visible.",
            ),
        ],
    )

    lifecycle_and_proof = _group(
        "lifecycle_and_proof",
        [
            _check(
                "lifecycle.no_ambiguous_orders",
                "No paper order has an ambiguous lifecycle",
                int(lifecycle.get("ambiguous_order_count") or 0) == 0,
                lifecycle.get("ambiguous_order_count"),
                "0 ambiguous orders",
                "lifecycle",
                "At least one mirrored paper order lacks a deterministic lifecycle state.",
            ),
            _check(
                "lifecycle.origin_class_complete",
                "Every broker record has an origin class",
                lifecycle.get("every_record_has_origin_class") is True,
                lifecycle.get("every_record_has_origin_class"),
                "true",
                "lifecycle",
                "A broker record could be confused with Qadam-origin proof.",
            ),
            _check(
                "proof.mirror_backfill_never_credited",
                "Mirror and historical records receive no paper proof ledger credit",
                int(lifecycle.get("mirror_record_backfill_proof_credit_count") or 0) == 0,
                lifecycle.get("mirror_record_backfill_proof_credit_count"),
                "0",
                "lifecycle",
                "A mirror or historical record received proof credit.",
            ),
            _check(
                "proof.no_unauthorized_credit",
                "No certification, backtest, or shadow result grants proof credit",
                int(lifecycle.get("proof_credit_created_count") or 0) == 0
                and int(shadow.get("proof_credit_count") or 0) == 0,
                {
                    "lifecycle_proof_credit": lifecycle.get("proof_credit_created_count"),
                    "shadow_proof_credit": shadow.get("proof_credit_count"),
                },
                "0 proof-credit side effects",
                "lifecycle",
                "A non-eligible record created paper proof ledger credit.",
            ),
        ],
    )

    messages = (
        communications.get("latest_messages")
        if isinstance(communications.get("latest_messages"), list)
        else []
    )
    message_lengths = [len(str(message.get("body") or "")) for message in messages]
    telegram_quality = (
        communications.get("telegram_live_send_allowed") is False
        and communications.get("telegram_command_path_enabled") is False
        and all(0 < length <= 280 for length in message_lengths)
    )
    operator_experience = _group(
        "operator_experience",
        [
            _check(
                "operator.dashboard_truth_and_parity",
                "Dashboard truth, route, and portfolio parity checks pass",
                dashboard.get("status") == "passed"
                and dashboard.get("portfolio_values_agree") is True
                and int(dashboard.get("protected_route_count") or 0) == 13
                and int(dashboard.get("raw_score_probability_violation_count") or 0) == 0,
                {
                    "status": dashboard.get("status"),
                    "portfolio_values_agree": dashboard.get("portfolio_values_agree"),
                    "routes": dashboard.get("protected_route_count"),
                    "score_probability_violations": dashboard.get(
                        "raw_score_probability_violation_count"
                    ),
                },
                "dashboard checker passed, parity true, 13 routes, no probability misuse",
                "dashboard",
                "The operator dashboard truth contract is not satisfied.",
            ),
            _check(
                "operator.dashboard_freshness",
                "Dashboard labels current evidence as fresh",
                stale_count == 0,
                {"stale_or_missing": stale_count},
                "0 stale or missing monitored artifacts",
                "dashboard_freshness",
                "The dashboard is honest but still reports stale upstream evidence.",
            ),
            _check(
                "operator.telegram_quality_and_safety",
                "Telegram notes are short, specific, notify-only, and command-disabled",
                telegram_quality,
                {
                    "message_lengths": message_lengths,
                    "live_send_allowed": communications.get("telegram_live_send_allowed"),
                    "command_path_enabled": communications.get("telegram_command_path_enabled"),
                },
                "1-280 characters, no live send, no command path",
                "communications",
                "Operator communications are too long, unsafe, or command-capable.",
            ),
            _check(
                "operator.anti_slop",
                "Dashboard anti-slop checks pass",
                anti_slop.get("status") == "anti_slop_passed"
                and int(anti_slop.get("error_count") or 0) == 0,
                {"status": anti_slop.get("status"), "errors": anti_slop.get("error_count")},
                "anti_slop_passed with 0 errors",
                "anti_slop",
                "Dashboard repetition, generic prose, or authority drift remains.",
            ),
            _check(
                "operator.service_running",
                "Explicit unattended service is installed and running",
                _operator_service_process_is_running(service),
                {
                    "operational_ready": service.get("operational_ready"),
                    "installed": service.get("service_installed"),
                    "running": service.get("service_running"),
                },
                "installed and running are true; operational readiness is evaluated separately",
                "service",
                "The explicit operator service is not installed or is not running.",
            ),
            _check(
                "operator.legacy_seven_session_soak_complete",
                "Legacy seven-session operator preflight is complete",
                legacy_soak_complete
                and soak_session_count >= 7
                and service_soak.get("simulated_elapsed_time_used") is False,
                {
                    "complete": legacy_soak_complete,
                    "real_sessions": soak_session_count,
                    "simulated_elapsed_time": service_soak.get("simulated_elapsed_time_used"),
                },
                "preflight complete after at least 7 real sessions with no simulated time",
                "service_soak",
                "The legacy seven-session operator preflight has not completed.",
            ),
            _check(
                "operator.permanent_reliability_certified",
                "Permanent operator reliability certification passed",
                permanent_reliability.get("status") == "passed"
                and permanent_reliability.get("permanent_reliability_certified") is True,
                {
                    "status": permanent_reliability.get("status"),
                    "implementation_complete": permanent_reliability.get("implementation_complete"),
                    "soak_status": permanent_reliability.get("soak", {}).get("status"),
                },
                "passed after the PORR implementation and contiguous real-time soak",
                "permanent_reliability",
                "The permanent reliability implementation or its real-time soak is incomplete.",
            ),
            _check(
                "operator.no_critical_repairs",
                "No unresolved critical operator repair remains",
                int(repair_queue.get("critical_request_count") or 0) == 0,
                repair_queue.get("critical_request_count"),
                "0",
                "repair_queue",
                "A critical repair request remains open.",
            ),
        ],
    )

    broker_write_total = sum(
        int(payload.get("broker_write_count") or 0)
        for payload in (
            source,
            or3_readiness,
            backfill,
            point_in_time,
            score_tape,
            labels,
            backtest,
            nonlinear,
            edges,
            foundry,
            akber,
            shadow,
            risk,
            router,
            lifecycle,
            dashboard,
            service,
        )
    )
    order_side_effect_total = sum(
        int(payload.get(key) or 0)
        for payload, key in (
            (edges, "order_created_count"),
            (foundry, "order_created_count"),
            (akber, "order_created_count"),
            (shadow, "paper_order_created_count"),
            (risk, "paper_order_created_count"),
            (router, "paper_order_created_count"),
            (lifecycle, "paper_order_created_count"),
            (dashboard, "paper_order_created_count"),
            (service, "paper_order_created_count"),
        )
    )
    safety = _group(
        "universal_negative_safety",
        [
            _check(
                "safety.live_capital_disabled",
                "Live capital and live endpoints remain disabled",
                lock.get("live_capital_enabled") is False
                and router.get("live_capital_enabled") is False,
                {
                    "lock": lock.get("live_capital_enabled"),
                    "router": router.get("live_capital_enabled"),
                },
                "false everywhere",
                "lock",
                "Live capital is enabled in a protected artifact.",
            ),
            _check(
                "safety.no_unauthorized_broker_writes",
                "Unauthorized broker-write count is zero",
                broker_write_total == 0,
                broker_write_total,
                "0",
                "router",
                "A research, model, dashboard, or service component recorded a broker write.",
            ),
            _check(
                "safety.no_order_side_effects",
                "Research and certification artifacts create no orders",
                order_side_effect_total == 0,
                order_side_effect_total,
                "0",
                "router",
                "A non-PaperOps research or certification component created an order.",
            ),
            _check(
                "safety.models_non_authoritative",
                "LLM, nonlinear, and quantum layers have no order authority",
                nonlinear.get("hardware_submission_attempted") is False
                and int(risk.get("execution_approval_created_count") or 0) == 0,
                {
                    "quantum_hardware_submission": nonlinear.get("hardware_submission_attempted"),
                    "execution_approvals": risk.get("execution_approval_created_count"),
                },
                "no hardware execution submission and no execution approvals",
                "nonlinear",
                "A model or quantum layer acquired execution authority.",
            ),
            _check(
                "safety.public_surfaces_command_disabled",
                "Dashboard and Telegram command paths are disabled",
                dashboard.get("command_path_enabled") is False
                and communications.get("telegram_command_path_enabled") is False
                and communications.get("telegram_live_send_allowed") is False,
                {
                    "dashboard_command": dashboard.get("command_path_enabled"),
                    "telegram_command": communications.get("telegram_command_path_enabled"),
                    "telegram_send": communications.get("telegram_live_send_allowed"),
                },
                "false for dashboard commands, Telegram commands, and live send",
                "communications",
                "A public surface can create commands or live sends.",
            ),
            _check(
                "safety.no_simulated_elapsed_time",
                "No elapsed-time gate is simulated",
                service_soak.get("simulated_elapsed_time_used") is False
                and shadow.get("historical_replay_credit_count") == 0,
                {
                    "soak_simulated": service_soak.get("simulated_elapsed_time_used"),
                    "historical_shadow_credit": shadow.get("historical_replay_credit_count"),
                },
                "false and 0",
                "service_soak",
                "Historical or synthetic time received real-time gate credit.",
            ),
            _check(
                "safety.no_unauthorized_proof_credit",
                "Backtest, shadow, fixture, and mirror records receive no proof credit",
                int(shadow.get("proof_credit_count") or 0) == 0
                and int(lifecycle.get("mirror_record_backfill_proof_credit_count") or 0) == 0
                and int(lifecycle.get("proof_credit_created_count") or 0) == 0,
                {
                    "shadow": shadow.get("proof_credit_count"),
                    "mirror": lifecycle.get("mirror_record_backfill_proof_credit_count"),
                    "created": lifecycle.get("proof_credit_created_count"),
                },
                "0 for every non-eligible proof class",
                "lifecycle",
                "A non-Qadam-origin or non-closed record received proof credit.",
            ),
            _check(
                "safety.no_forced_trade",
                "No forced-trade behavior exists",
                order_side_effect_total == 0
                and int(foundry.get("candidate_created_count") or 0) == 0
                and lock.get("paper_order_creation_allowed") is False,
                {
                    "order_side_effects": order_side_effect_total,
                    "foundry_candidates_created": foundry.get("candidate_created_count"),
                    "lock_order_creation_allowed": lock.get("paper_order_creation_allowed"),
                },
                "no side effects, no forced candidate, lock denies order creation",
                "lock",
                "A trade or candidate was forced through an incomplete evidence path.",
            ),
        ],
    )

    groups = {
        group["group_id"]: group
        for group in (
            canonical_truth,
            research_operations,
            evidence_and_edge,
            akber_shadow_portfolio,
            router_and_paperops,
            lifecycle_and_proof,
            operator_experience,
            safety,
        )
    }
    research_operational = canonical_truth["passed"] and research_operations["passed"]
    edge_validated = research_operational and evidence_and_edge["passed"]
    paper_operator_ready = (
        edge_validated
        and akber_shadow_portfolio["passed"]
        and router_and_paperops["passed"]
        and lifecycle_and_proof["passed"]
        and operator_experience["passed"]
        and safety["passed"]
    )
    performance_proven = (
        paper_operator_ready
        and int(lifecycle.get("qadam_origin_complete_lineage_count") or 0) > 0
        and int(lifecycle.get("proof_eligible_count") or 0) > 0
    )
    blockers = [
        {
            "group": group_id,
            **blocker,
        }
        for group_id in GROUP_ORDER
        for blocker in groups[group_id]["blockers"]
    ]
    certification = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_edge_engine_certification",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "mode": mode,
        "status": "passed" if paper_operator_ready else "evidence_maturing",
        "certification_state": (
            "paper_operator_ready" if paper_operator_ready else "blocked_evidence_maturing"
        ),
        "certification_passed": paper_operator_ready,
        "implementation_ready": True,
        "certification_levels": {
            "research_operational": research_operational,
            "edge_validated": edge_validated,
            "paper_operator_ready": paper_operator_ready,
            "paper_performance_proven": performance_proven,
        },
        "groups": groups,
        "group_count": len(groups),
        "passed_group_count": sum(group["passed"] for group in groups.values()),
        "blocked_group_count": sum(not group["passed"] for group in groups.values()),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "top_blockers": blockers[:12],
        "paper_trial": {
            "name": "30-day paper growth trial",
            "resume_recommended": paper_operator_ready,
            "resume_allowed_by_certification": False,
            "explicit_operator_lock_release_required": True,
            "calendar_backfill_allowed": False,
            "simulated_elapsed_time_allowed": False,
        },
        "paper_proof_ledger": {
            "proof_eligible_count": int(lifecycle.get("proof_eligible_count") or 0),
            "proof_credit_created_count": int(lifecycle.get("proof_credit_created_count") or 0),
            "mirror_backfill_credit_count": int(
                lifecycle.get("mirror_record_backfill_proof_credit_count") or 0
            ),
        },
        "research_lock_release_recommended": paper_operator_ready,
        "research_lock_release_performed": False,
        "paper_trial_resume_allowed": False,
        "existence_only_credit_count": 0,
        "guaranteed_profit_claimed": False,
        "performance_claim": "No guaranteed return is claimed. Paper performance requires real Qadam-origin closed outcomes.",
        "source_artifacts": {
            key: f"data/runtime/{filename}" for key, filename in ARTIFACTS.items()
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    return certification


def validate_operator_ready_certification(certification: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    groups = certification.get("groups") if isinstance(certification.get("groups"), dict) else {}
    if tuple(groups) != GROUP_ORDER:
        errors.append("operator_certification_group_order_or_membership_invalid")
    for group_id in GROUP_ORDER:
        group = groups.get(group_id) if isinstance(groups.get(group_id), dict) else {}
        rows = group.get("checks") if isinstance(group.get("checks"), list) else []
        expected_pass = bool(rows) and all(row.get("passed") is True for row in rows)
        if group.get("passed") is not expected_pass:
            errors.append(f"operator_certification_group_result_mismatch:{group_id}")
        for row in rows:
            if row.get("existence_only_credit") is not False:
                errors.append(f"operator_certification_existence_only_credit:{row.get('check_id')}")
            if row.get("passed") is False and not row.get("blocker"):
                errors.append(
                    f"operator_certification_failed_check_without_blocker:{row.get('check_id')}"
                )
    levels = certification.get("certification_levels", {})
    if levels.get("paper_performance_proven") and not levels.get("paper_operator_ready"):
        errors.append("operator_certification_performance_without_operator_readiness")
    if levels.get("paper_operator_ready") and not levels.get("edge_validated"):
        errors.append("operator_certification_operator_ready_without_edge")
    if levels.get("edge_validated") and not levels.get("research_operational"):
        errors.append("operator_certification_edge_without_research_operations")
    if certification.get("certification_passed") is not (
        levels.get("paper_operator_ready") is True
    ):
        errors.append("operator_certification_pass_state_mismatch")
    if certification.get("paper_trial_resume_allowed") is not False:
        errors.append("operator_certification_granted_trial_resume_authority")
    if certification.get("research_lock_release_performed") is not False:
        errors.append("operator_certification_released_research_lock")
    if certification.get("guaranteed_profit_claimed") is not False:
        errors.append("operator_certification_guaranteed_profit_claim")
    if certification.get("existence_only_credit_count") != 0:
        errors.append("operator_certification_existence_only_credit_nonzero")
    if (
        certification.get("paper_order_created_count") != 0
        or certification.get("broker_write_count") != 0
    ):
        errors.append("operator_certification_execution_side_effect")
    safety = groups.get("universal_negative_safety", {})
    if safety.get("passed") is not True:
        errors.append("operator_certification_negative_safety_probe_failed")
    errors.extend(
        validate_authority(certification.get("authority", {}), prefix="operator_certification")
    )
    return unique_errors(errors)


def build_and_write_operator_ready_certification(
    settings: Settings | None = None,
    *,
    mode: str = "full",
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    certification = build_operator_ready_certification(settings, mode=mode)
    errors = validate_operator_ready_certification(certification)
    certification["implementation_ready"] = not errors
    certification["validation_error_count"] = len(errors)
    certification["validation_errors"] = errors
    store = AtomicArtifactStore(runtime)
    store.write_json(CERTIFICATION_ARTIFACT, certification)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_ready_edge_engine_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "checker_implementation_ready": not errors,
        "certification_state": certification["certification_state"],
        "certification_passed": certification["certification_passed"],
        "research_operational": certification["certification_levels"]["research_operational"],
        "edge_validated": certification["certification_levels"]["edge_validated"],
        "paper_operator_ready": certification["certification_levels"]["paper_operator_ready"],
        "paper_performance_proven": certification["certification_levels"][
            "paper_performance_proven"
        ],
        "passed_group_count": certification["passed_group_count"],
        "blocked_group_count": certification["blocked_group_count"],
        "blocker_count": certification["blocker_count"],
        "paper_trial_resume_allowed": certification["paper_trial_resume_allowed"],
        "research_lock_release_performed": certification["research_lock_release_performed"],
        "existence_only_credit_count": certification["existence_only_credit_count"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return certification, checks, errors
