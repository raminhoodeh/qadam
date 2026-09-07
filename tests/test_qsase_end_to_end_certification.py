import copy
from dataclasses import replace

import pytest

from orchestrator.config import Settings

from orchestrator.qsase_end_to_end_certification import (
    EXTERNAL_CHECKS_TO_RUN,
    build_qsase_end_to_end_certification,
    build_recursive_improvement_contract_audit,
    validate_negative_qsase_certification_probes,
    validate_qsase_end_to_end_certification,
)


def _passing_check_results():
    return [
        {
            "script": script,
            "status": "passed",
            "passed": True,
            "returncode": 0,
            "stdout_tail": [f"{script}=ok"],
            "stderr_tail": [],
        }
        for script in EXTERNAL_CHECKS_TO_RUN
    ]


@pytest.fixture
def isolated_settings(tmp_path):
    return replace(Settings.from_env(), runtime_dir=tmp_path)


def test_qsase_certification_refuses_missing_runtime_even_with_passing_external_checks(isolated_settings):
    payload = build_qsase_end_to_end_certification(isolated_settings, check_results=_passing_check_results())

    assert validate_qsase_end_to_end_certification(payload)
    assert payload["certified"] is False
    assert payload["phase_count"] == 16
    assert payload["failed_phase_count"] > 0
    assert payload["required_artifact_count"] > payload["present_artifact_count"]
    assert payload["required_check_count"] == payload["passed_check_count"]
    assert payload["authority_violation_count"] == 0
    assert payload["lineage_gap_count"] > 0
    assert payload["dashboard_slop_failure_count"] > 0
    assert payload["telegram_quality_failure_count"] > 0
    assert payload["paperops_boundary_failure_count"] > 0
    assert payload["proof_boundary_failure_count"] > 0
    assert payload["calendar_boundary_failure_count"] > 0
    assert payload["live_capital_enabled"] is False
    assert payload["broker_write_count"] == 0
    assert payload["paper_order_created_outside_paperops_count"] == 0
    assert payload["proof_credit_allowed"] is False


def test_qsase_certification_missing_paperops_cannot_pass_empty_lineage(isolated_settings):
    payload = build_qsase_end_to_end_certification(isolated_settings, check_results=_passing_check_results())

    assert payload["source_price_lineage"]["status"] == "source_price_lineage_failed"
    assert payload["strategy_lineage"]["status"] == "strategy_lineage_failed"
    assert payload["paperops_compatibility"]["status"] != "paperops_compatibility_pass"
    assert payload["paperops_compatibility"]["errors"]
    assert payload["certified"] is False
    assert payload["proof_boundary"]["status"] == "proof_boundary_failed"
    assert payload["calendar_boundary"]["status"] == "calendar_boundary_failed"
    assert payload["dashboard_visibility"]["status"] == "dashboard_visibility_failed"
    assert payload["telegram_quality"]["status"] == "telegram_quality_failed"
    assert payload["negative_safety_probes"]["status"] == "negative_probes_pass"
    assert payload["recursive_improvement_contract"]["status"] == "recursive_improvement_contract_blocked"


def test_qsase_certification_rejects_hard_safety_probe():
    payload = build_qsase_end_to_end_certification(check_results=_passing_check_results())
    probe = copy.deepcopy(payload)
    probe["live_capital_enabled"] = True

    assert "live_capital_enabled_must_be_false" in validate_qsase_end_to_end_certification(probe)
    assert validate_negative_qsase_certification_probes() == []


def test_qsase_recursive_improvement_contract_is_proposal_only():
    audit = build_recursive_improvement_contract_audit()

    assert audit["status"] == "recursive_improvement_contract_ready"
    assert audit["proposal_only"] is True
    assert audit["applied_update_count"] == 0
    assert audit["errors"] == []
