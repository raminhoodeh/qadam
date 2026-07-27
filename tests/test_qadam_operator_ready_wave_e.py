from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from orchestrator.config import Settings
from orchestrator.qadam_dynamic_plan import PHASE_ORDER, program_status
from orchestrator.qadam_operator_dashboard import (
    DEFAULT_ROUTE,
    ROUTE_ORDER,
    _optional_float,
    build_operator_dashboard_state,
)
from orchestrator.qadam_operator_ready_certification import (
    _operator_service_process_is_running,
    build_operator_ready_certification,
    validate_operator_ready_certification,
)
from orchestrator.qadam_operator_service import (
    FAILURE_CLASSES,
    SOAK_SCENARIOS,
    OperatorServiceLease,
    build_operator_service_state,
    classify_failure,
    retry_policy,
)


EXPECTED_ROUTES = (
    "system/team",
    "fund/portfolio",
    "fund/timeline",
    "observe/sources",
    "observe/universe",
    "patterns/findings",
    "patterns/nonlinear",
    "decide/strategies",
    "decide/decision",
    "trade/orders",
    "learn/outcomes",
    "learn/improvements",
    "system/overview",
)

EXPECTED_JOURNEY_ROUTES = EXPECTED_ROUTES[1:-1]


def test_operator_dashboard_preserves_protected_route_contract() -> None:
    state = build_operator_dashboard_state()
    contract = state["view_model"]["navigation_contract"]
    assert DEFAULT_ROUTE == "fund/portfolio"
    assert ROUTE_ORDER == EXPECTED_ROUTES
    assert tuple(contract["route_order"]) == EXPECTED_ROUTES
    assert tuple(contract["journey_route_order"]) == EXPECTED_JOURNEY_ROUTES
    assert contract["contract_version"] == "qadam_protected_decision_flow.v5"
    assert contract["route_count"] == 13
    assert contract["previous_next_journey_required"] is False
    assert contract["lifecycle_timeline_required"] is True
    assert contract["lifecycle_stage_count"] == 10
    assert contract["cross_cutting_routes_in_journey"] is False
    modules = {
        module["module_id"]: {view["view_id"]: view["label"] for view in module["views"]}
        for module in contract["modules"]
    }
    assert modules["fund"]["timeline"] == "Trading History"
    assert modules["patterns"]["findings"] == "Pattern Recognition"
    assert modules["patterns"]["nonlinear"] == "Quantum Edge"
    assert contract["pinned_context"][0]["view_id"] == "team"
    assert contract["standalone_cross_cutting"][0] == {
        "module_id": "system",
        "view_id": "overview",
        "label": "System",
        "description": "Full operating picture",
        "journey_stage": False,
    }
    assert contract["legacy_route_aliases"]["system/activity"] == "system/overview"
    assert contract["legacy_route_aliases"]["system/health"] == "system/overview"
    assert contract["legacy_route_aliases"]["learn/replay"] == "learn/improvements"
    assert contract["legacy_route_aliases"]["learn/briefs"] == "learn/outcomes"
    assert "fund/holdings" not in state["view_model"]["views"]
    assert "current_portfolio" in state["view_model"]["views"]["fund/portfolio"]
    assert "decide/intents" not in state["view_model"]["views"]
    assert "trade_intents" in state["view_model"]["views"]["decide/decision"]
    assert state["view_model"]["views"]["system/team"]["journey_stage"] is False
    assert (
        state["view_model"]["views"]["system/overview"]["artifact_type"] == "qadam_system_overview"
    )
    assert state["view_model"]["end_to_end_lifecycle"]["stage_count"] == 10
    assert state["view_model"]["end_to_end_lifecycle"]["single_global_current_stage"] is False


def test_system_overview_separates_infrastructure_health_from_operating_mode() -> None:
    state = build_operator_dashboard_state()
    overview = state["view_model"]["views"]["system/overview"]
    assert overview["diagnostic_contract_version"] == "qadam_system_diagnostics.v2"
    assert overview["overall_health"]["state"] in {"healthy", "degraded"}
    assert overview["operating_mode"]["is_infrastructure_failure"] is False
    assert overview["operating_mode"]["state"] in {
        "research-only",
        "paper-operational",
        "blocked",
    }
    domains = overview["infrastructure_domains"]
    assert {domain["domain_id"] for domain in domains} == {
        "host",
        "runtime",
        "data",
        "storage",
        "research",
        "paper_broker",
        "communications",
        "deployment",
    }
    monitoring_gaps = [domain for domain in domains if domain["tone"] == "unmonitored"]
    assert len(monitoring_gaps) == overview["overall_health"]["monitoring_gap_count"]
    assert all(domain["status"] != "Healthy" for domain in monitoring_gaps)
    incidents = overview["root_cause_incidents"]["rows"]
    assert overview["root_cause_incidents"]["total_count"] == len(incidents)
    assert len({incident["incident_id"] for incident in incidents}) == len(incidents)
    assert all(
        "research lock" not in f"{incident['title']} {incident['summary']}".lower()
        and "validated edge" not in f"{incident['title']} {incident['summary']}".lower()
        for incident in incidents
    )
    services = overview["services_schedules_jobs"]["services"]
    automation = overview["services_schedules_jobs"]
    assert automation["service_count"] == len(services)
    assert (
        automation["scheduled_count"] + automation["policy_paused_count"]
        == automation["service_count"]
    )
    if automation["running_count_known"] is False:
        assert automation["running_count"] is None
    else:
        assert automation["running_count"] <= automation["scheduled_count"]
    assert all(
        service["diagnostic_state"]
        in {"running", "stopped", "paused_by_policy", "state_unverified"}
        for service in services
    )
    assert all(
        service["tone"] == "policy"
        for service in services
        if service["diagnostic_state"] == "paused_by_policy"
    )
    deployment = next(domain for domain in domains if domain["domain_id"] == "deployment")
    if overview["operating_mode"]["state"] == "research-only":
        assert deployment["tone"] != "degraded"
    incident_ids = {incident["incident_id"] for incident in incidents}
    assert not {
        "operator_service_stopped",
        "operating_evidence_overdue",
    }.issubset(incident_ids)
    coverage = overview["technical_diagnostics"]["monitoring_coverage"]
    assert coverage["unmonitored_domain_count"] == len(monitoring_gaps)
    assert coverage["monitoring_gap_count"] == len(coverage["gaps"])
    operator_check_state = overview["overall_health"]["operator_service_check_state"]
    if operator_check_state != "fresh":
        assert overview["overall_health"]["state"] == "degraded"
        assert "operator_service_stopped" not in incident_ids
        assert "operating_evidence_overdue" in incident_ids
        assert all(
            service["diagnostic_state"]
            in {
                "state_unverified",
                "paused_by_policy",
            }
            for service in services
        )
    elif not state["view_model"]["runtime_state"]["operator_service"]["running"]:
        assert "operator_service_stopped" in incident_ids


def test_system_overview_preserves_missing_and_zero_disk_evidence() -> None:
    assert _optional_float(None) is None
    assert _optional_float("") is None
    assert _optional_float("not-a-number") is None
    assert _optional_float(False) is None
    assert _optional_float(0) == 0.0
    assert _optional_float("12.5") == 12.5


def test_operator_dashboard_keeps_scores_honest_and_patterns_distinct() -> None:
    state = build_operator_dashboard_state()
    pattern = state["view_model"]["compatibility_sections"]["pattern_intelligence"]
    findings = pattern["findings"]
    identities = {finding.get("pattern_id") for finding in findings}
    assert len(identities) == len(findings)
    assert all(finding["raw_pattern_score_is_probability"] is False for finding in findings)
    assert state["truth"]["pattern_truth"]["raw_pattern_score_displayed_as_probability_count"] == 0


def test_operator_communications_are_short_notify_only_and_non_authoritative() -> None:
    state = build_operator_dashboard_state()
    communications = state["communications"]
    assert communications["telegram_live_send_allowed"] is False
    assert communications["telegram_command_path_enabled"] is False
    assert communications["broker_write_count"] == 0
    assert communications["proof_credit_allowed"] is False
    assert communications["latest_messages"][0]["quality_passed"] is True
    assert communications["latest_messages"][0]["human_style"]["status"] == "human"
    assert communications["deduplication"]["material_change_required_for_repeat"] is True
    assert all(0 < len(message["body"]) <= 280 for message in communications["latest_messages"])


def test_operator_failure_taxonomy_and_retry_policy_fail_closed() -> None:
    observed = {
        classify_failure(message, status_code=429 if scenario == "provider_429" else None)
        for scenario, message, _expected in SOAK_SCENARIOS
    }
    assert observed.issubset(set(FAILURE_CLASSES))
    for scenario, message, expected in SOAK_SCENARIOS:
        failure_class = classify_failure(
            message, status_code=429 if scenario == "provider_429" else None
        )
        assert failure_class == expected
        policy = retry_policy(failure_class)
        assert policy["paperops_retry_allowed"] is False
        assert policy["broker_write_retry_allowed"] is False
        assert policy["code_edit_allowed"] is False
    assert retry_policy("code_defect")["automatic_retry_allowed"] is False
    assert retry_policy("safety_violation")["automatic_retry_allowed"] is False


def test_operator_service_lease_prevents_duplicate_instances(tmp_path) -> None:
    first = OperatorServiceLease(tmp_path)
    second = OperatorServiceLease(tmp_path)
    acquired, _reason = first.acquire()
    assert acquired is True
    duplicate, duplicate_reason = second.acquire()
    assert duplicate is False
    assert duplicate_reason == "active_operator_service_lease_exists"
    assert first.release() is True
    third = OperatorServiceLease(tmp_path)
    reacquired, _reason = third.acquire()
    assert reacquired is True
    assert third.release() is True


def test_operator_service_probes_do_not_fake_a_real_soak(tmp_path) -> None:
    settings = replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        data_root=str(tmp_path.parent),
    )
    state = build_operator_service_state(settings)
    soak = state["soak"]
    assert soak["all_interruption_probes_passed"] is True
    assert soak["interruption_probe_count"] == len(SOAK_SCENARIOS)
    assert soak["simulated_elapsed_time_used"] is False
    assert soak["multi_session_soak_complete"] is False
    assert "real_soak_complete" not in state["status"]["readiness"]
    assert state["status"]["readiness"]["legacy_seven_session_soak_complete"] is False
    assert state["status"]["readiness"]["permanent_reliability_status"] == "not_run"
    assert state["status"]["readiness"]["permanent_reliability_certified"] is False
    assert all(record["probe_only"] is True for record in soak["scenarios"])
    assert all(record["broker_write_count"] == 0 for record in soak["scenarios"])


def test_operator_service_process_health_is_separate_from_soak_readiness() -> None:
    assert _operator_service_process_is_running(
        {
            "service_installed": True,
            "service_running": True,
            "operational_ready": False,
        }
    )
    assert not _operator_service_process_is_running(
        {
            "service_installed": True,
            "service_running": False,
            "operational_ready": False,
        }
    )


def test_operator_certification_separates_research_from_edge_readiness() -> None:
    certification = build_operator_ready_certification()
    levels = certification["certification_levels"]
    assert certification["certification_passed"] is False
    assert levels["research_operational"] is (
        certification["groups"]["canonical_truth"]["passed"]
        and certification["groups"]["research_operations"]["passed"]
    )
    assert levels["edge_validated"] is False
    assert levels["paper_operator_ready"] is False
    assert levels["paper_performance_proven"] is False
    assert certification["existence_only_credit_count"] == 0
    assert certification["paper_trial_resume_allowed"] is False
    assert certification["research_lock_release_performed"] is False
    assert certification["groups"]["universal_negative_safety"]["passed"] is True


def test_operator_certification_rejects_forged_readiness() -> None:
    certification = build_operator_ready_certification()
    forged = deepcopy(certification)
    forged["certification_passed"] = True
    forged["certification_levels"]["paper_operator_ready"] = True
    errors = validate_operator_ready_certification(forged)
    assert "operator_certification_operator_ready_without_edge" in errors


def test_wave_e_status_remains_evidence_maturing_until_or19_passes() -> None:
    phases = {phase: {"state": "passed"} for phase in PHASE_ORDER}
    for phase in ("OR-3", "OR-6", "OR-7", "OR-8", "OR-9", "OR-12", "OR-13", "OR-16", "OR-19"):
        phases[phase]["state"] = "evidence_maturing"
    assert program_status(phases) == "wave_e_evidence_maturing"
